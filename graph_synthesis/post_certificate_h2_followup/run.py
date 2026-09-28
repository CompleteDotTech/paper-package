"""Execute the separate, frozen transactional fault-injection follow-up."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

from graph_synthesis.post_certificate.methods import DependencyGraph
from graph_synthesis.post_certificate.run import make_connected_dag, make_modular_dag

ROOT = Path(__file__).resolve().parent
SEED = 20260929


def affected_nodes(graph: DependencyGraph, primitive: int) -> set[int]:
    seen: set[int] = set()
    frontier = [primitive]
    while frontier:
        for child in graph.reverse[frontier.pop()]:
            if child not in seen:
                seen.add(child)
                frontier.append(child)
    return seen


def exception_name(call, *, suppress_fault: bool = False) -> str | None:
    try:
        call()
    except Exception as exc:
        if suppress_fault and isinstance(exc, RuntimeError) and str(exc) == 'injected evaluation failure':
            return None
        return type(exc).__name__
    return None


def execute(*, suppress_fault: bool = False) -> dict:
    rng = random.Random(SEED)
    accepted = []
    injections = []
    stale = []
    malformed = []
    unaffected = []
    cycles = []
    connected = []
    local_evaluations = 0

    for graph_index in range(64):
        graph = make_modular_dag(rng)
        primitives = {i: bool(rng.getrandbits(1)) for i in range(64)}
        values = graph.full_recompute(primitives)
        revision = 0
        for transaction_index in range(5):
            module = rng.randrange(8)
            count = rng.randint(1, 4)
            selected = rng.sample(range(module * 8, (module + 1) * 8), count)
            changes = {p: not values[p] for p in selected}
            new_values, new_revision, evaluations = graph.transact(
                values, revision, changes, expected_revision=revision
            )
            recomputed = graph.full_recompute({i: new_values[i] for i in range(64)})
            passed = new_values == recomputed and new_revision == revision + 1
            accepted.append({'graph_index': graph_index, 'transaction_index': transaction_index,
                             'primitive_ids': selected, 'evaluations': evaluations, 'passed': passed})
            local_evaluations += evaluations
            values, revision = new_values, new_revision

        primitive = next(p for p in range(64) if affected_nodes(graph, p))
        closure = affected_nodes(graph, primitive)
        fail_node = min(closure)
        before = dict(values)
        changes = {primitive: not values[primitive]}
        caught = exception_name(
            lambda: graph.transact(values, revision, changes,
                                   expected_revision=revision, fail_node=fail_node),
            suppress_fault=suppress_fault,
        )
        injections.append({'graph_index': graph_index, 'primitive': primitive,
                           'fail_node': fail_node, 'affected_closure_size': len(closure),
                           'exception': caught, 'passed': caught == 'RuntimeError'
                           and values == before and revision == 5})
        caught = exception_name(lambda: graph.transact(
            values, revision, changes, expected_revision=revision - 1))
        stale.append({'graph_index': graph_index, 'exception': caught,
                      'passed': caught == 'RuntimeError' and values == before and revision == 5})
        caught = exception_name(lambda: graph.transact(
            values, revision, {64: True}, expected_revision=revision))
        malformed.append({'graph_index': graph_index, 'exception': caught,
                          'passed': caught == 'ValueError' and values == before and revision == 5})

    for control_index in range(64):
        graph = DependencyGraph(2, {2: ('xor', (0,))})
        primitives = {i: bool(rng.getrandbits(1)) for i in range(2)}
        values = graph.full_recompute(primitives)
        new_values, revision, evaluations = graph.transact(
            values, 0, {1: not values[1]}, expected_revision=0)
        recomputed = graph.full_recompute({i: new_values[i] for i in range(2)})
        unaffected.append({'control_index': control_index, 'primitive': 1,
                           'affected_closure_size': len(affected_nodes(graph, 1)),
                           'evaluations': evaluations, 'passed': revision == 1
                           and evaluations == 0 and new_values == recomputed
                           and values == graph.full_recompute(primitives)})

    for control_index in range(8):
        first = 1 + 2 * control_index
        second = first + 1
        caught = exception_name(lambda: DependencyGraph(1, {
            first: ('xor', (second,)), second: ('xor', (first,))}))
        cycles.append({'control_index': control_index, 'exception': caught,
                       'passed': caught == 'ValueError'})

    for control_index in range(16):
        graph = make_connected_dag()
        primitives = {j: bool((j + control_index) % 2) for j in range(64)}
        values = graph.full_recompute(primitives)
        new_values, revision, evaluations = graph.transact(
            values, 0, {0: not values[0]}, expected_revision=0)
        recomputed = graph.full_recompute({j: new_values[j] for j in range(64)})
        connected.append({'control_index': control_index, 'evaluations': evaluations,
                          'saving': 1 - evaluations / 256,
                          'passed': revision == 1 and new_values == recomputed})

    reduction = 1 - local_evaluations / (320 * 256)
    groups = {'accepted': accepted, 'affected_injection': injections,
              'stale_revision': stale, 'malformed_update': malformed,
              'unaffected_noop': unaffected, 'cycle_rejection': cycles,
              'connected_boundary': connected}
    counts = {name: {'passed': sum(bool(row['passed']) for row in rows), 'total': len(rows)}
              for name, rows in groups.items()}
    target = all(counts[name]['passed'] == counts[name]['total']
                 for name in groups if name != 'connected_boundary')
    target = target and reduction >= .80
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (ROOT / 'PROTOCOL.md', Path(__file__))}
    return {'schema_version': 1, 'seed': SEED, 'protocol_commit': 'f0d39d568c66175ffba0f023e6eb36c5fbad39e0',
            'source_sha256': hashes, 'original_h2_result': {'passed': 63, 'total': 64, 'primary_target_met': False},
            'counts': counts, 'local_evaluations': local_evaluations,
            'full_recompute_evaluations': 320 * 256, 'evaluation_reduction': reduction,
            'connected_mean_reduction': sum(row['saving'] for row in connected) / 16,
            'primary_target_met': target, 'controls': groups}


def render(result: dict) -> str:
    lines = ['# Transactional fault-injection follow-up', '',
             'This is a separate precommitted study. The original PR #33 H2 result remains **failed (63/64)**.', '',
             f"New conjunction: **{'met' if result['primary_target_met'] else 'not met'}**.", '',
             '| Endpoint | Passed / total |', '|---|---:|']
    for name, count in result['counts'].items():
        lines.append(f"| {name.replace('_', ' ')} | {count['passed']}/{count['total']} |")
    lines += ['', f"Local derived evaluations: {result['local_evaluations']:,} / "
              f"{result['full_recompute_evaluations']:,} full recomputation evaluations "
              f"({result['evaluation_reduction']:.2%} reduction).",
              f"Connected control mean saving: {result['connected_mean_reduction']:.2%}; reported separately.", '',
              'Affected injections require an actual derived dependency and an exception. '
              'Unaffected primitive updates correctly commit without derived evaluation. '
              'This measures in-memory behavior only; it does not establish crash durability, '
              'concurrency isolation, semantic accuracy, or wall-clock performance.', '',
              'See [the frozen protocol](PROTOCOL.md) and [all control records](results.json).', '']
    return '\n'.join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = execute()
    output = json.dumps(result, sort_keys=True, indent=2) + '\n'
    report = render(result)
    if args.check:
        if (ROOT / 'results.json').read_text(encoding='utf-8') != output:
            raise SystemExit('Saved result differs from frozen replay')
        if (ROOT / 'RESULTS.md').read_text(encoding='utf-8') != report:
            raise SystemExit('Saved report differs from frozen replay')
    else:
        (ROOT / 'results.json').write_text(output, encoding='utf-8')
        (ROOT / 'RESULTS.md').write_text(report, encoding='utf-8')
    print(json.dumps({'target_met': result['primary_target_met'], 'counts': result['counts']}))


if __name__ == '__main__':
    main()
