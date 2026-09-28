"""Run the frozen certificate suite without service calls; keep timings separate."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path
import platform
import random
import socket
import statistics
import sys
import time
from unittest.mock import patch
import numpy as np
from . import risk, lineage, graphs
from ..adaptive.run import load
from ..reliability.run import calibration, proper_scores
from ..reliability.methods import solve_graph as prior_solve

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SEED = 20260922
PROTOCOL_COMMIT = 'bc70b76621daca198b3b97eb4f698b17d4c40a0b'
BASELINE_COMMIT = 'a62a3257645d8e35cd4e45be53bfa9511d27724b'
DRAWS = 4000


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalized(value):
    return json.loads(json.dumps(value, sort_keys=True, allow_nan=False))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n', encoding='utf-8', newline='\n')


def interval(deltas):
    values = np.asarray(deltas, dtype=float)
    rng = np.random.default_rng(SEED)
    sample = values[rng.integers(0, len(values), size=(DRAWS, len(values)))].mean(axis=1)
    return {'point': float(values.mean()), '95': np.quantile(sample, [.025, .975]).tolist(),
            '99': np.quantile(sample, [.005, .995]).tolist(), 'groups': len(values), 'draws': DRAWS}


def experiment_risk(development, test):
    fitted = risk.fit(development)
    exposure = risk.counts(test)
    actual = risk.counts(test, truth=True)
    truth = {g: int(v['k'] > 0) for g, v in actual.items()}
    proposed = risk.predict(exposure, fitted)
    independent = risk.predict(exposure, fitted, independent=True)
    previous = calibration(development, test)
    scores = {'pooled_independent': proper_scores(independent, truth), 'random_effects': proper_scores(proposed, truth),
              'prior_features': previous['baseline'], 'prior_multiplier': previous['proposed']}
    folds = []
    for group in sorted({r['group'] for r in development}):
        fit = risk.fit([r for r in development if r['group'] != group])
        held = risk.counts([r for r in development if r['group'] == group])
        folds.append({'held_group': group, 'fit_groups': fit['fit_groups'], 'mu': fit['mu'], 'rho': fit['rho'],
                      'prediction': risk.predict(held, fit)})
    new, old = scores['random_effects'], scores['pooled_independent']
    return {'primary_target_met': new['brier'] <= .9 * old['brier'] and abs(new['bias']) <= .03
            and new['brier'] <= scores['prior_features']['brier'],
            'fit': fitted, 'test_exposures': exposure, 'test_counts': actual, 'scores': scores,
            'prior_multiplier': previous['multiplier'], 'leave_group_out': folds,
            'test_singleton_groups': sum(n == 1 for n in exposure.values()),
            'group_predictions': [{'group': g, 'truth': truth[g], 'n': exposure[g], 'random_effects': proposed[g],
                                   'pooled_independent': independent[g]} for g in sorted(truth)],
            'paired_brier': interval([(proposed[g] - truth[g])**2 - (independent[g] - truth[g])**2 for g in sorted(truth)]),
            'brier_relative_improvement': 1 - new['brier'] / old['brier']}


def formula_holds(world, proofs, positions):
    return any(all(world & (1 << positions[a]) for a in proof) for proof in proofs)


def experiment_lineage():
    rng = random.Random(SEED + 2)
    cases, grid, controls = [], [], []
    failures = 0
    widths, narrower = [], []
    for i in range(128):
        n = rng.randrange(2, 7)
        names = [f'a{j}' for j in range(n)]
        pos = {a: j for j, a in enumerate(names)}
        masses = [rng.randrange(1, 100) for _ in range(1 << n)]
        total = sum(masses)
        joint = [v / total for v in masses]
        probabilities = {a: sum(v for world, v in enumerate(joint) if world & (1 << j)) for a, j in pos.items()}
        proofs = [sorted(rng.sample(names, rng.randrange(1, min(3, n) + 1))) for _ in range(rng.randrange(1, 7))]
        actual = sum(v for world, v in enumerate(joint) if formula_holds(world, proofs, pos))
        pair = sorted(rng.sample(names, 2))
        pair_p = sum(v for world, v in enumerate(joint) if all(world & (1 << pos[a]) for a in pair))
        base = lineage.bounds(proofs, probabilities)
        informed = lineage.bounds(proofs, probabilities, [(pair, pair_p)])
        shuffled = lineage.bounds(list(reversed(proofs)) * 3, dict(reversed(list(probabilities.items()))))
        errors = []
        for key, value in [('marginals', base), ('joint', informed)]:
            if not value['certified'] or not value['lower'] - 1e-8 <= actual <= value['upper'] + 1e-8:
                errors.append(key + '_containment')
        if informed['upper'] - informed['lower'] > base['upper'] - base['lower'] + 1e-8:
            errors.append('constraint_widening')
        if any(abs(base[k] - shuffled[k]) > 1e-8 for k in ('lower', 'upper')):
            errors.append('duplicate_invariance')
        failures += len(errors)
        widths.append(base['upper'] - base['lower'])
        narrower.append(informed['upper'] - informed['lower'])
        cases.append({'id': i, 'probabilities': probabilities, 'proofs': proofs, 'actual_joint': joint, 'truth': actual,
                      'pair_constraint': [pair, pair_p], 'marginals': base, 'with_joint': informed, 'errors': errors})
    for p in (0., .2, .5, .8, 1.):
        for q in (0., .2, .5, .8, 1.):
            for kind, proofs, expected in [('OR', [['a'], ['b']], (max(p, q), min(1., p + q))),
                                           ('AND', [['a', 'b']], (max(0., p + q - 1), min(p, q)))]:
                result = lineage.bounds(proofs, {'a': p, 'b': q})
                ok = result['certified'] and all(abs(result[k] - want) <= 1e-8 for k, want in zip(('lower', 'upper'), expected))
                failures += int(not ok)
                grid.append({'p': p, 'q': q, 'kind': kind, 'expected': expected, 'result': result, 'ok': ok})
    prevented, recovered, withheld = 0, 0, 0
    for i in range(20):
        p = .8 + .005 * i
        naive = 1 - (1 - p)**2
        robust = lineage.bounds([['a'], ['b']], {'a': p, 'b': p})
        correlated = lineage.bounds([['a'], ['b']], {'a': p, 'b': p}, [(['a', 'b'], p)])
        independent = lineage.bounds([['a'], ['b']], {'a': p, 'b': p}, [(['a', 'b'], p * p)])
        blocked = naive >= .95 and p < .95 and robust['lower'] < .95
        recovered_here = independent['certified'] and independent['lower'] >= .95
        prevented += int(blocked)
        recovered += int(recovered_here)
        withheld += int(naive >= .95 and robust['lower'] < .95)
        ok = blocked and correlated['upper'] < .95 and recovered_here
        failures += int(not ok)
        controls.append({'p': p, 'correlated_truth': p, 'independence_assumed': naive, 'unknown_dependence': robust,
                         'known_correlation': correlated, 'known_independence': independent, 'ok': ok})
    infeasible = lineage.bounds([['a']], {'a': .8}, [(['a'], .7)])
    capacity = lineage.bounds([['a0']], {f'a{i}': .5 for i in range(11)})
    bad_input = lineage.bounds([['a']], {'a': .99})
    failures += int(infeasible['certified'] or capacity['certified'])
    return {'primary_target_met': failures == 0 and prevented == 20, 'failures': failures, 'random_cases': cases,
            'frechet_grid': grid, 'dependence_controls': controls, 'false_admissions_prevented': prevented,
            'known_independence_admissions_recovered': recovered, 'independent_true_admissions_withheld_without_joint': withheld,
            'mean_width_marginals': statistics.mean(widths), 'mean_width_with_joint': statistics.mean(narrower),
            'infeasible_control': infeasible, 'capacity_control': capacity,
            'wrong_marginal_control': {'actual_probability': .5, 'supplied_probability': .99, 'result': bad_input,
                                       'false_admission_under_wrong_premise': bad_input['lower'] >= .95}}


def independent_sets(weights, edges):
    """Independent exhaustive oracle: no use of the proposed optimizer."""
    keys = sorted(weights)
    if len(keys) > 12:
        raise ValueError('Finite oracle cap exceeded')
    index = {k: i for i, k in enumerate(keys)}
    masks = [(1 << index[a]) | (1 << index[b]) for a, b in edges]
    answers = []
    for mask in range(1 << len(keys)):
        if all(mask & pair != pair for pair in masks):
            selected = [k for i, k in enumerate(keys) if mask & (1 << i)]
            answers.append((sum(weights[k] for k in selected), selected))
    return answers


def valid_repair(weights, edges, selected, threshold):
    chosen = set(selected)
    return len(chosen) == len(selected) and chosen <= set(weights) and not any(a in chosen and b in chosen for a, b in edges) and sum(weights[k] for k in chosen) >= threshold


def certificate_checks(weights, edges, result):
    checks = []
    for c in result['components']:
        if c['method'] == 'bipartite_flow':
            nodes = set(c['certificate']['vertex_order'])
            w = {k: weights[k] for k in nodes}
            e = [(a, b) for a, b in edges if a in nodes and b in nodes]
            checks.append(graphs.verify_flow(w, e, c))
    return all(checks)


def experiment_graphs():
    rng = random.Random(SEED + 3)
    cases, general, large = [], [], []
    failures = 0
    for i in range(128):
        n = rng.randrange(2, 11)
        left = rng.randrange(1, n)
        w = {f'v{j}': rng.randrange(10) for j in range(n)}
        e = [(f'v{a}', f'v{b}') for a in range(left) for b in range(left, n) if rng.random() < .45]
        oracle = max(v for v, _ in independent_sets(w, e))
        result = graphs.solve(w, e)
        reordered = graphs.solve(dict(reversed(list(w.items()))), list(reversed(e)) * 3)
        ok = result['utility'] == oracle and not result['staged'] and valid_repair(w, e, result['selected'], oracle) and certificate_checks(w, e, result) and result == reordered
        failures += int(not ok)
        cases.append({'id': i, 'weights': w, 'edges': e, 'oracle': oracle, 'result': result, 'ok': ok})
        all_edges = [(a, b) for a, b in combinations(w, 2) if rng.random() < .35]
        old, new = prior_solve(w, all_edges), graphs.solve(w, all_edges)
        optimum = max(v for v, _ in independent_sets(w, all_edges))
        ok = new['utility'] >= old['utility'] and new['utility'] == optimum and not new['staged']
        failures += int(not ok)
        general.append({'weights': w, 'edges': all_edges, 'oracle': optimum, 'prior_utility': old['utility'], 'new_utility': new['utility'], 'ok': ok})
    for n in (32, 64, 128, 256):
        half = n // 2
        w = {**{f'l{i:04}': 3 for i in range(half)}, **{f'r{i:04}': 2 for i in range(half)}}
        e = [(f'l{i:04}', f'r{j:04}') for i in range(half) for j in range(half)]
        oracle = 3 * half
        old, new = prior_solve(w, e), graphs.solve(w, e)
        ok = new['utility'] == oracle and not new['staged'] and certificate_checks(w, e, new)
        failures += int(not ok)
        large.append({'kind': 'complete_bipartite', 'n': n, 'edges': len(e), 'oracle': oracle, 'prior_utility': old['utility'], 'prior_staged': len(old['staged']), 'result': new, 'ok': ok})
    for n in (512, 1024, 2048):
        w = {f'v{i:04}': 1 for i in range(n)}
        e = [(f'v{i:04}', f'v{(i + 1) % n:04}') for i in range(n)]
        old, new = prior_solve(w, e), graphs.solve(w, e)
        ok = new['utility'] == n // 2 and not new['staged'] and certificate_checks(w, e, new)
        failures += int(not ok)
        large.append({'kind': 'even_cycle', 'n': n, 'edges': len(e), 'oracle': n // 2, 'prior_utility': old['utility'], 'prior_staged': len(old['staged']), 'result': new, 'ok': ok})
    n = 2050
    cap_w = {f'v{i:04}': 1 for i in range(n)}
    cap_e = [(f'v{i:04}', f'v{(i + 1) % n:04}') for i in range(n)]
    vertex_cap = graphs.solve(cap_w, cap_e)
    w = {**{f'l{i}': 1 for i in range(224)}, **{f'r{i}': 1 for i in range(224)}}
    e = [(f'l{i}', f'r{j}') for i in range(224) for j in range(224)]
    edge_cap = graphs.solve(w, e)
    w = {f'v{i:02}': 1 for i in range(17)}
    odd = graphs.solve(w, [(f'v{i:02}', f'v{(i + 1) % 17:02}') for i in range(17)])
    dense = graphs.solve(w, list(combinations(w, 2)))
    false = graphs.solve({'false': 9, 'true': 8}, [('false', 'true')])
    controls_ok = len(vertex_cap['staged']) == 2050 and len(edge_cap['staged']) == 448 and odd['utility'] == 8 and len(dense['staged']) == 17
    failures += int(not controls_ok)
    return {'primary_target_met': failures == 0 and all(x['ok'] for x in large), 'failures': failures,
            'random_bipartite': cases, 'general_small': general, 'large': large,
            'controls': {'vertex_cap_staged': len(vertex_cap['staged']), 'edge_cap_staged': len(edge_cap['staged']),
                         'edge_cap_edges': len(e), 'odd_cycle_utility': odd['utility'], 'dense_staged': len(dense['staged']),
                         'false_priority_selected': false['selected']}}


def experiment_queries():
    rng = random.Random(SEED + 4)
    cases, totals = [], {'exact': Counter(), 'tolerant': Counter()}
    failures, point_false_certainty = 0, 0
    for i in range(128):
        n = rng.randrange(2, 11)
        w = {f'v{j}': rng.randrange(10) for j in range(n)}
        e = [(a, b) for a, b in combinations(w, 2) if rng.random() < .3]
        q = sorted(rng.sample(list(w), rng.randrange(min(3, n) + 1)))
        all_repairs = independent_sets(w, e)
        optimum = max(v for v, _ in all_repairs)
        trials = []
        for name, epsilon in [('exact', 0), ('tolerant', math.floor(.05 * optimum))]:
            repairs = [selected for v, selected in all_repairs if v >= optimum - epsilon]
            truth = [set(q) <= set(s) for s in repairs]
            oracle = 'certain' if all(truth) else 'ambiguous' if any(truth) else 'impossible'
            result = graphs.query(w, e, q, epsilon=epsilon)
            ok = result['classification'] == oracle
            if oracle in ('certain', 'ambiguous'):
                witness = result.get('possible_repair', [])
                ok = ok and valid_repair(w, e, witness, optimum - epsilon) and set(q) <= set(witness)
            if oracle == 'ambiguous':
                witness = result.get('counterexample')
                ok = ok and witness is not None and valid_repair(w, e, witness, optimum - epsilon) and not set(q) <= set(witness)
            failures += int(not ok)
            point_false_certainty += int(name == 'exact' and result.get('single_optimum_answer', False) and oracle != 'certain')
            totals[name][oracle] += 1
            trials.append({'name': name, 'epsilon': epsilon, 'oracle': oracle, 'admissible_repair_count': len(repairs), 'result': result, 'ok': ok})
        failures += int(trials[1]['oracle'] == 'certain' and trials[0]['oracle'] != 'certain')
        cases.append({'id': i, 'weights': w, 'edges': e, 'required': q, 'optimum': optimum, 'trials': trials})
    w, e = {'a': 1, 'b': 1}, [('a', 'b')]
    chosen = graphs.solve(w, e)['selected'][0]
    tie = graphs.query(w, e, [chosen])
    bad_truth = graphs.query({'false': 9, 'true': 8}, [('false', 'true')], ['false'])
    failures += int(tie['classification'] != 'ambiguous' or not tie['single_optimum_answer'])
    return {'primary_target_met': failures == 0, 'failures': failures, 'cases': cases,
            'counts': {k: {label: v[label] for label in ('certain', 'ambiguous', 'impossible')} for k, v in totals.items()},
            'random_single_optimum_false_certainty': point_false_certainty, 'tie_control': tie,
            'false_priority_control': {'semantic_truth': False, 'result': bad_truth}}


def path_components(count, size=8):
    w = {f'g{i:04}v{j:02}': 1 for i in range(count) for j in range(size)}
    e = [(f'g{i:04}v{j:02}', f'g{i:04}v{j + 1:02}') for i in range(count) for j in range(size - 1)]
    return w, e


def workload(count, updates, *, size=8):
    w, e = path_components(count, size)
    commands = [{'kind': 'weight', 'node': f'g{i % count:04}v{i % size:02}', 'value': 2 + i // count} for i in range(updates)]
    return w, e, commands


def apply_reference(w, e, command):
    """Independent full snapshot mutation oracle, not a DeltaIndex operation."""
    w, e = dict(w), {tuple(sorted(pair)) for pair in e}
    kind = command['kind']
    if kind in ('weight', 'insert_vertex'):
        w[command['node']] = command['value']
    elif kind == 'delete_vertex':
        del w[command['node']]
        e = {pair for pair in e if command['node'] not in pair}
    elif kind == 'insert_edge':
        e.add(tuple(sorted((command['a'], command['b']))))
    else:
        e.remove(tuple(sorted((command['a'], command['b']))))
    return w, sorted(e)


def paired_work(w, e, commands):
    local, full = graphs.DeltaIndex(w, e), graphs.DeltaIndex(w, e, rescan_all=True)
    failures, steps = 0, []
    cold = {'local': local.total_work, 'full': full.total_work}
    for command in commands:
        ld, fd = local.update(command), full.update(command)
        ok = local.snapshot() == full.snapshot()
        failures += int(not ok)
        steps.append({'command': command, 'local_work': ld['work'], 'full_work': fd['work'], 'utility': ld['utility'], 'ok': ok})
    return {'vertices': len(w), 'edges': len(e), 'updates': len(commands), 'cold': cold, 'steps': steps, 'failures': failures,
            'local_work': local.total_work, 'full_work': full.total_work, 'saving': 1 - local.total_work / full.total_work}


def experiment_delta():
    rng = random.Random(SEED + 5)
    cases, failures, invalid_changes = [], 0, 0
    operation_counts = Counter()
    for trial in range(32):
        w = {f'v{i:02}': rng.randrange(10) for i in range(8)}
        e = [(a, b) for a, b in combinations(w, 2) if rng.random() < .15]
        original_w, original_e = dict(w), list(e)
        local = graphs.DeltaIndex(w, e)
        events = []
        for step in range(20):
            kind = ('weight', 'insert_edge', 'delete_edge', 'insert_vertex', 'delete_vertex')[step % 5]
            if kind == 'insert_edge':
                options = sorted(set(combinations(sorted(w), 2)) - {tuple(sorted(x)) for x in e})
                if options:
                    a, b = rng.choice(options)
                    cmd = {'kind': kind, 'a': a, 'b': b}
                else:
                    kind = 'weight'
            if kind == 'delete_edge':
                if e:
                    a, b = rng.choice(e)
                    cmd = {'kind': kind, 'a': a, 'b': b}
                else:
                    kind = 'weight'
            if kind == 'weight':
                cmd = {'kind': kind, 'node': rng.choice(sorted(w)), 'value': rng.randrange(10)}
            elif kind == 'insert_vertex':
                cmd = {'kind': kind, 'node': f'new{step:02}', 'value': rng.randrange(10)}
            elif kind == 'delete_vertex':
                cmd = {'kind': kind, 'node': rng.choice(sorted(w))}
            delta = local.update(cmd)
            w, e = apply_reference(w, e, cmd)
            expected = graphs.solve(w, e)
            snapshot = local.snapshot()
            ok = snapshot['weights'] == w and snapshot['edges'] == [list(pair) for pair in sorted(tuple(sorted(pair)) for pair in e)] and local.summary() == {k: expected[k] for k in ('selected', 'staged', 'utility')}
            failures += int(not ok)
            operation_counts[kind] += 1
            events.append({'command': cmd, 'delta': delta, 'oracle': {k: expected[k] for k in ('selected', 'staged', 'utility')}, 'ok': ok})
        before = local.snapshot()
        try:
            local.update({'kind': 'weight', 'node': next(iter(w)), 'value': -1})
            invalid_changes += 1
        except ValueError:
            invalid_changes += int(local.snapshot() != before)
        cases.append({'trial': trial, 'weights': original_w, 'edges': original_e, 'events': events})
    w, e, commands = workload(512, 128)
    locality = paired_work(w, e, commands)
    w, e, commands = workload(1, 128, size=64)
    connected = paired_work(w, e, commands)
    w, e = path_components(2, 4)
    bridge_commands = [{'kind': 'insert_edge', 'a': 'g0000v03', 'b': 'g0001v00'},
                       {'kind': 'delete_edge', 'a': 'g0000v03', 'b': 'g0001v00'},
                       {'kind': 'insert_edge', 'a': 'g0000v03', 'b': 'g0001v00'},
                       {'kind': 'delete_vertex', 'node': 'g0000v03'}]
    bridges = paired_work(w, e, bridge_commands)
    failures += locality['failures'] + connected['failures'] + bridges['failures'] + invalid_changes
    return {'primary_target_met': failures == 0 and locality['saving'] >= .75, 'failures': failures,
            'random_cases': cases, 'mutations': sum(operation_counts.values()), 'operation_counts': dict(operation_counts),
            'invalid_state_changes': invalid_changes, 'local_workload': locality, 'connected_control': connected, 'bridge_control': bridges,
            'metric_boundary': 'Declared graph-element passes for copy, validation, discovery, solver input, operation validation and publication; excludes sorting, optimizer-internal and certificate-check work. Not total CPU work.'}


def timing_experiment():
    import scipy
    cases = []
    for count in (16, 64, 256, 512):
        w, e, commands = workload(count, 64)
        samples = {'local': [], 'full': []}
        for repetition in range(3):
            engines = {}
            for policy in (('local', 'full') if repetition % 2 == 0 else ('full', 'local')):
                start = time.perf_counter()
                engine = graphs.DeltaIndex(w, e, rescan_all=policy == 'full')
                for cmd in commands:
                    engine.update(cmd)
                samples[policy].append(time.perf_counter() - start)
                engines[policy] = engine
            if engines['local'].snapshot() != engines['full'].snapshot():
                raise ValueError('Timing policies disagree')
        cases.append({'components': count, 'vertices': len(w), 'updates': len(commands), 'seconds': samples,
                      'median_seconds': {k: statistics.median(v) for k, v in samples.items()}})
    return {'python': sys.version, 'platform': platform.platform(), 'numpy': np.__version__, 'scipy': scipy.__version__,
            'clock': 'perf_counter; cold construction plus updates; full snapshot comparison outside both timing boundaries',
            'repetitions': 3, 'cases': cases, 'qualification': 'Single-host in-memory measurements; not a service or durable database benchmark.'}


def execute():
    rows, calls, verification = load()
    development = [r for r in rows if r['split'] == 'development']
    test = [r for r in rows if r['split'] == 'test']
    dev_groups, test_groups = {r['group'] for r in development}, {r['group'] for r in test}
    if (len(development), len(test), len(dev_groups), len(test_groups)) != (73, 263, 40, 149) or dev_groups & test_groups or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Source-group split or record identity changed')
    source_paths = sorted(p for p in HERE.rglob('*') if p.is_file() and (p.suffix == '.py' or p.name in ('PROTOCOL.md', 'requirements.txt')))
    inputs = ROOT / 'experiments/jev-multicall-20260918'
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in source_paths}
    for name in ('artifact-manifest.json', 'calls.jsonl', 'predictions.json'):
        p = inputs / name
        hashes[p.relative_to(ROOT).as_posix()] = sha(p)
    for p in (ROOT / 'graph_synthesis/reliability/methods.py', ROOT / 'graph_synthesis/reliability/run.py', ROOT / 'graph_synthesis/adaptive/run.py'):
        hashes[p.relative_to(ROOT).as_posix()] = sha(p)
    result = {'protocol_commit': PROTOCOL_COMMIT, 'baseline_commit': BASELINE_COMMIT, 'seed': SEED,
              'fresh_service_calls': 0, 'evidence_class': 'H1 reused saved-response forecasts; H2-H5 controlled algorithms',
              'development': {'n': len(development), 'groups': len(dev_groups)}, 'test': {'n': len(test), 'groups': len(test_groups)},
              'input_verification': verification, 'sha256': hashes}
    for name, function in [('H1', lambda: experiment_risk(development, test)), ('H2', experiment_lineage),
                           ('H3', experiment_graphs), ('H4', experiment_queries), ('H5', experiment_delta)]:
        result[name] = function()
        print(name + ': ' + ('target met' if result[name]['primary_target_met'] else 'target not met'), flush=True)
    return normalized(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--timings', action='store_true')
    args = parser.parse_args()
    def blocked(*args, **kwargs):
        raise RuntimeError('No network calls are permitted in this benchmark')
    with patch.object(socket.socket, 'connect', blocked), patch.object(socket.socket, 'connect_ex', blocked), patch.object(socket, 'create_connection', blocked):
        result = execute()
        if args.check:
            from ..verify import compare_json
            changes = compare_json(json.loads((HERE / 'results.json').read_text(encoding='utf-8')), result)
            print('Replay verified; floating-point roundoff entries:', len(changes))
        else:
            write(HERE / 'results.json', result)
        if args.timings:
            if args.check:
                parser.error('Timings are separate from deterministic replay')
            write(HERE / 'timings.json', timing_experiment())
    print(json.dumps({'status': 'reproduced' if args.check else 'executed', 'targets': {k: result[k]['primary_target_met'] for k in ('H1', 'H2', 'H3', 'H4', 'H5')}, 'fresh_service_calls': 0}))


if __name__ == '__main__':
    main()
