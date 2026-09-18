"""Run the five frozen assumption-aware tests with inference/network disabled."""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path
import random
import socket
from unittest.mock import patch
from .methods import DeltaTree, GroundedRules, exposure_order, frechet, invariant_repairs, lineage_envelope

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASELINE = 'a62a3257645d8e35cd4e45be53bfa9511d27724b'
PROTOCOL = '82ee57229570bb9f7299e0418a5f9b959c25d59f'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n', encoding='utf-8', newline='\n')


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if type(value) is float:
        return round(value, 12)
    return value


def finite_probability(proofs, probabilities):
    atoms = sorted(probabilities)
    total = 0.
    for mask in range(1 << len(atoms)):
        live = {a for i, a in enumerate(atoms) if mask & (1 << i)}
        if any(set(p) <= live for p in proofs):
            total += math.prod(probabilities[a] if a in live else 1-probabilities[a] for a in atoms)
    return total


def h1():
    rng = random.Random(20260922)
    fixtures, containment, false_admit, invariance, witness_failures = [], 0, 0, 0, 0
    for case in range(128):
        n = rng.randrange(2, 7)
        atoms = [f'a{i}' for i in range(n)]
        masses = [rng.randrange(0, 21) for _ in range(1 << n)]
        if not sum(masses):
            masses[0] = 1
        joint = [x/sum(masses) for x in masses]
        marginals = {a: sum(p for m, p in enumerate(joint) if m & (1 << i)) for i, a in enumerate(atoms)}
        pairs = [(a, b, sum(p for m, p in enumerate(joint) if m & (1 << i) and m & (1 << j)))
                 for i, a in enumerate(atoms) for j, b in enumerate(atoms) if i < j]
        proofs = [sorted(rng.sample(atoms, rng.randrange(1, min(3, n)+1))) for _ in range(rng.randrange(1, 9))]
        truth = sum(p for m, p in enumerate(joint) if any(all(m & (1 << atoms.index(a)) for a in proof) for proof in proofs))
        simple = frechet(proofs, marginals)
        proposed = lineage_envelope(proofs, marginals)
        pairwise = lineage_envelope(proofs, marginals, pairs)
        for result, constraints in ((proposed, []), (pairwise, pairs)):
            containment += not result['optimized'] or not result['lower']-1e-7 <= truth <= result['upper']+1e-7
            false_admit += result['lower'] >= .95 and truth < .95-1e-7
            if result['optimized']:
                # Independently verify saved extremal distributions, not only solver flags.
                for witness in result['witnesses']:
                    bad = abs(sum(witness)-1) > 1e-7 or min(witness) < -1e-7
                    for i, atom in enumerate(atoms):
                        bad |= abs(sum(p for m, p in enumerate(witness) if m & (1 << i))-marginals[atom]) > 1e-7
                    for a, b, p in constraints:
                        bad |= abs(sum(v for m, v in enumerate(witness) if m & (1 << atoms.index(a)) and m & (1 << atoms.index(b)))-p) > 1e-7
                    witness_failures += bad
        for copies in (1, 2, 5, 20):
            alt = lineage_envelope(list(reversed(proofs))*copies, dict(reversed(list(marginals.items()))))
            invariance += max(abs(alt[k]-proposed[k]) for k in ('lower', 'upper')) > 1e-7
        fixtures.append({'case': case, 'joint_masses': joint, 'marginals': marginals, 'pairwise_constraints': pairs,
                         'proofs': proofs, 'truth': truth, 'frechet': simple, 'marginal_lp': proposed, 'pairwise_lp': pairwise,
                         'independent_point': finite_probability(proofs, marginals)})
    width = lambda key: sum(f[key]['upper']-f[key]['lower'] for f in fixtures)/len(fixtures)
    base_width, new_width = width('frechet'), width('marginal_lp')
    shared = {'truth': .8, 'independent_point': finite_probability([['a'], ['b']], {'a': .8, 'b': .8}),
              'marginal_lp': lineage_envelope([['a'], ['b']], {'a': .8, 'b': .8}),
              'correct_shared_id': lineage_envelope([['a'], ['a']], {'a': .8})}
    controls = {'shared_source': shared,
                'exclusive': lineage_envelope([['a'], ['b']], {'a': .5, 'b': .5}, [('a', 'b', 0.)]),
                'incoherent': lineage_envelope([['a']], {'a': .8, 'b': .8}, [('a', 'b', .1)]),
                'cap': lineage_envelope([['a0']], {f'a{i}': .8 for i in range(9)}),
                'zero_one': lineage_envelope([['a', 'b']], {'a': 0., 'b': 1.}),
                'empty': lineage_envelope([], {}), 'tautology': lineage_envelope([[]], {})}
    control_ok = (shared['independent_point'] >= .95 and shared['marginal_lp']['lower'] < .95
                  and controls['exclusive']['lower'] >= .95 and not controls['incoherent']['optimized']
                  and not controls['cap']['optimized'] and controls['zero_one']['upper'] <= 1e-7
                  and controls['empty']['upper'] == 0 and controls['tautology']['lower'] >= 1-1e-7)
    reduction = 1-new_width/base_width if base_width else 0.
    return {'primary_target_met': not containment and not false_admit and not invariance and not witness_failures and control_ok and reduction >= .10,
            'cases': 128, 'containment_checks': 256, 'containment_failures': int(containment), 'false_admissions': int(false_admit),
            'invariance_checks': 512, 'invariance_failures': int(invariance), 'witness_failures': int(witness_failures),
            'frechet_mean_width': base_width, 'marginal_mean_width': new_width, 'pairwise_mean_width': width('pairwise_lp'),
            'relative_width_reduction': reduction, 'controls_ok': bool(control_ok), 'controls': controls, 'fixtures': fixtures}


def repair_oracle(weights, edges, queries=()):
    """Independent combinations enumeration retaining *every* optimum."""
    nodes = sorted(weights)
    if len(nodes) > 16:
        raise ValueError('Independent oracle cap')
    optima, best = [], -1
    for count in range(len(nodes)+1):
        for chosen in combinations(nodes, count):
            chosen = set(chosen)
            if any(a in chosen and b in chosen for a, b in edges):
                continue
            value = sum(weights[k] for k in chosen)
            if value > best:
                best, optima = value, [chosen]
            elif value == best:
                optima.append(chosen)
    core = set.intersection(*optima)
    answers = [all(bool(set(q) & s) if kind == 'OR' else set(q) <= s for s in optima) for kind, q in queries]
    return {'utility': best, 'forced': sorted(core), 'queries': answers, 'optimum_count': len(optima)}


def h2():
    rng = random.Random(20260923)
    fixtures, failures, invariance, unique, unique_fail = [], 0, 0, 0, 0
    for case in range(128):
        weights = {f'n{i}': rng.randrange(6) for i in range(rng.randrange(4, 11))}
        edges = [e for e in combinations(weights, 2) if rng.random() < .3]
        queries = [(kind, sorted(rng.sample(list(weights), rng.randrange(1, min(len(weights), 3)+1))))
                   for kind in ('OR', 'AND') for _ in range(4)]
        oracle = repair_oracle(weights, edges, queries)
        got = invariant_repairs(weights, edges, queries)
        bad = got['status'] != 'complete' or any(got[k] != oracle[k] for k in ('utility', 'forced', 'queries'))
        failures += bad
        alt = invariant_repairs(dict(reversed(list(weights.items()))), list(reversed(edges))*2, queries)
        invariance += alt != got
        if oracle['optimum_count'] == 1:
            unique += 1
            unique_fail += got['forced'] != got['selected']
        fixtures.append({'case': case, 'weights': weights, 'edges': edges, 'queries': queries, 'oracle': oracle, 'proposed': got})
    weights = {f'p{i:02d}{s}': 1 for i in range(32) for s in ('a', 'b')}
    edges = [(f'p{i:02d}a', f'p{i:02d}b') for i in range(32)]
    pairs = invariant_repairs(weights, edges, [('OR', e) for e in edges]+[('AND', e) for e in edges])
    false = invariant_repairs({'false': 9, 'true': 8}, [('false', 'true')], [('OR', ['false'])])
    staged = invariant_repairs({str(i): 1 for i in range(17)}, list(combinations(map(str, range(17)), 2)))
    pair_ok = not pairs['forced'] and pairs['queries'] == [True]*32+[False]*32 and len(pairs['selected']) == 32
    baseline_selected = sum(len(f['proposed']['selected']) for f in fixtures)
    return {'primary_target_met': not failures and not invariance and unique > 0 and not unique_fail and pair_ok and staged['status'] == 'unknown',
            'cases': 128, 'oracle_failures': int(failures), 'invariance_failures': int(invariance),
            'unique_optimum_cases': unique, 'unique_retention_failures': int(unique_fail),
            'baseline_selected': baseline_selected, 'forced_assertions': sum(len(f['proposed']['forced']) for f in fixtures),
            'oracle_calls': sum(f['proposed']['oracle_calls'] for f in fixtures), 'pairs_control': pairs,
            'false_priority_control': false, 'staging_control': staged, 'fixtures': fixtures}


def exposure(group):
    return 1+int(hashlib.sha256(('query-exposure-v1:'+group).encode()).hexdigest(), 16)%10


def review_outcome(rows, selected, weights, sensitivity=1.):
    from ..reliability.methods import POSITIVE
    wrong = defaultdict(list)
    correct = 0
    for row in rows:
        label = row['views']['base1']['label']
        if label in POSITIVE:
            if label == row['gold']:
                correct += 1
            else:
                wrong[row['group']].append(row['id'])
    values = {}
    for group in sorted(weights):
        ids = wrong[group]
        values[group] = 1. if any(i not in selected for i in ids) else 1-sensitivity**len(ids)
    return {'weighted_exposure': sum(weights[g]*v for g, v in values.items()),
            'contaminated_groups': sum(values.values()), 'correct_retained': correct, 'group_vector': values}


def weighted_interval(a, b, weights):
    import numpy as np
    groups = sorted(weights)
    delta = np.asarray([(a[g]-b[g])*weights[g] for g in groups])
    mass = np.asarray([weights[g] for g in groups], dtype=float)
    ids = np.random.default_rng(20260924).integers(0, len(groups), (4000, len(groups)))
    sample = delta[ids].sum(axis=1)/mass[ids].sum(axis=1)
    return {'point': float(delta.sum()/mass.sum()), '95': list(map(float, np.quantile(sample, [.025, .975]))),
            '99': list(map(float, np.quantile(sample, [.005, .995]))), 'groups': len(groups), 'draws': 4000}


def h3(development, test):
    from ..reliability.methods import fit_small, assign_small
    from ..adaptive.methods import review_order
    fitted = fit_small(development)
    features = [{'id': r['id'], 'group': r['group'], 'views': {'base1': r['views']['base1']}} for r in test]
    candidates = assign_small(features, fitted)
    base = review_order(candidates, group_aware=True)
    groups = sorted({r['group'] for r in test})
    primary = {g: exposure(g) for g in groups}
    panels = []
    for name, weights in [('primary', primary), ('uniform', {g: 1 for g in groups}), ('reversed', {g: 11-primary[g] for g in groups})]:
        order = exposure_order(candidates, weights)
        budgets = []
        for budget in (10, 20, 30, 40):
            outcomes = {}
            for key, selected in [('baseline', set(base[:budget])), ('proposed', set(order[:budget]))]:
                outcomes[key] = {'selected': sorted(selected), 'primary': review_outcome(test, selected, weights),
                                 'sensitivity': [{'detection': s, **review_outcome(test, selected, weights, s)} for s in (.5, .75, 1.)]}
            budgets.append({'budget': budget, 'policies': outcomes})
        panels.append({'name': name, 'exposures': weights, 'order': order, 'budgets': budgets})
    panel = panels[0]['budgets'][1]['policies']
    a, b = panel['proposed']['primary'], panel['baseline']['primary']
    improvement = 1-a['weighted_exposure']/b['weighted_exposure'] if b['weighted_exposure'] else 0.
    return {'primary_target_met': improvement >= .10 and a['contaminated_groups'] <= b['contaminated_groups'] and a['correct_retained'] >= b['correct_retained'],
            'fit': fitted, 'risks': candidates, 'baseline_order': base, 'panels': panels,
            'weighted_reduction': improvement, 'baseline_primary': b, 'proposed_primary': a,
            'uniform_matches_baseline': panels[1]['order'] == base,
            'paired_weighted_rate': weighted_interval(a['group_vector'], b['group_vector'], primary),
            'same_acquisition_tokens': sum(r['arms']['single']['input_tokens'] for r in test),
            'note': 'Synthetic exposure workload and perfect-review simulation on reused captured data; no observed query or reviewer outcomes.'}


def full_tree(weights, edges):
    """Cold independent adjacency/tree-DP reference; no cached DeltaTree state."""
    adj = {k: [] for k in weights}
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    def recurse(key, parent):
        pairs = [recurse(c, key) for c in adj[key] if c != parent]
        return weights[key]+sum(x[1] for x in pairs), sum(max(x) for x in pairs)
    return max(recurse(min(weights), None))


def feasible_selection(selected, weights, edges, value):
    return sum(weights[k] for k in selected) == value and not any(a in selected and b in selected for a, b in edges)


def tree_workload(kind):
    rng = random.Random(20260925)
    weights = {f'v{i:03d}': rng.randrange(1, 10) for i in range(255)}
    nodes = list(weights)
    edges = [(nodes[(i-1)//2 if kind == 'balanced' else i-1], nodes[i]) for i in range(1, 255)]
    engine = DeltaTree(weights, edges)
    initial = dict(weights)
    visits = messages = full = len(weights)
    engine.selected()
    reconstruction = engine.reconstruction_visits
    failures, events = 0, []
    for step in range(256):
        key, weight = rng.choice(nodes), rng.randrange(1, 10)
        weights[key] = weight
        value = engine.update(key, weight)
        oracle = full_tree(weights, edges)
        selected = engine.selected()
        failures += value != oracle or not feasible_selection(selected, weights, edges, value)
        visits += engine.visits
        messages += engine.messages
        full += len(weights)
        reconstruction += engine.reconstruction_visits
        events.append({'step': step, 'id': key, 'weight': weight, 'value': value, 'oracle': oracle,
                       'selected': selected, 'ancestor_visits': engine.visits, 'changed_messages': engine.messages})
    return {'kind': kind, 'vertices': 255, 'updates': 256, 'initial_weights': initial, 'edges': edges,
            'failures': int(failures), 'full_dp_visits': full, 'incremental_dp_visits': visits, 'changed_messages': messages,
            'dp_saving': 1-visits/full, 'reconstruction_visits_each_policy': reconstruction,
            'dp_plus_reconstruction_saving': 1-(visits+reconstruction)/(full+reconstruction), 'events': events}


def h4():
    rng = random.Random(20260925)
    fixtures, failures = [], 0
    for case in range(128):
        weights = {f'n{i}': rng.randrange(1, 10) for i in range(rng.randrange(2, 11))}
        nodes = list(weights)
        edges = [(nodes[rng.randrange(i)], nodes[i]) for i in range(1, len(nodes))]
        initial = dict(weights)
        engine = DeltaTree(weights, edges)
        events = []
        for step in range(8):
            key, weight = rng.choice(nodes), rng.randrange(10)
            weights[key] = weight
            got, oracle = engine.update(key, weight), repair_oracle(weights, edges)['utility']
            selected = engine.selected()
            failures += got != oracle or not feasible_selection(selected, weights, edges, got)
            events.append({'id': key, 'weight': weight, 'value': got, 'oracle': oracle, 'selected': selected})
        fixtures.append({'case': case, 'initial_weights': initial, 'edges': edges, 'events': events})
    balanced, path = tree_workload('balanced'), tree_workload('path')
    engine = DeltaTree({'a': 1, 'b': 2}, [('a', 'b')])
    before = (dict(engine.weights), engine.utility, engine.selected())
    rejected = []
    for call in (lambda: engine.update('a', -1), lambda: engine.update('a', float('nan')),
                 lambda: engine.update('absent', 2), lambda: engine.change_structure([('a', 'c')])):
        try:
            call()
            rejected.append(False)
        except ValueError:
            rejected.append(before == (dict(engine.weights), engine.utility, engine.selected()))
    engine.update('a', 1)
    same = engine.visits == 0
    return {'primary_target_met': not failures and not balanced['failures'] and not path['failures'] and all(rejected) and same and balanced['dp_saving'] >= .75,
            'small_cases': 128, 'small_updates': 1024, 'small_failures': int(failures), 'balanced': balanced, 'path_control': path,
            'invalid_updates_atomic': rejected, 'same_value_zero_visits': same, 'fixtures': fixtures,
            'work_boundary': 'Fixed tree, validated once. DP message visits and O(n) selected-set reconstruction reported separately; no end-to-end latency claim.'}


def scan_closure(external, rules):
    """Independent cold least fixed point with actual short-circuit body checks."""
    active, inspections, passes = set(external), 0, 0
    while True:
        changed = False
        passes += 1
        for head, body in rules:
            ok = True
            for fact in body:
                inspections += 1
                if fact not in active:
                    ok = False
                    break
            if ok and head not in active:
                active.add(head)
                changed = True
        if not changed:
            return {'closure': sorted(active), 'dependency_inspections': inspections, 'passes': passes}


def rule_workload(dense=False):
    if dense:
        facts = [f'n{i:02d}' for i in range(16)]
        rules = [(a, [b]) for a in facts for b in facts if a != b]
        roots, updates = [facts[0]], 16
    else:
        facts = [f'c{i:02d}n{j}' for i in range(64) for j in range(9)]
        rules = [(f'c{i:02d}n{j}', [f'c{i:02d}n{j-1}']) for i in range(64) for j in range(8, 0, -1)]
        roots, updates = [f'c{i:02d}n0' for i in range(64)], 128
    engine = GroundedRules(facts, rules)
    external = set(roots)
    work, full, counters, failures = engine.index_inspections, 0, 0, 0
    events = []
    for step in range(updates+1):
        if step:
            key = roots[(step-1) % len(roots)]
            external.symmetric_difference_update({key})
        got, oracle = engine.update(external), scan_closure(external, rules)
        failures += got['closure'] != oracle['closure']
        work += got['dependency_inspections']
        full += oracle['dependency_inspections']
        counters += got['counter_initializations']
        events.append({'step': step, 'external': sorted(external), 'proposed': got, 'oracle': oracle})
    return {'rules': rules, 'facts': facts, 'updates': updates, 'events': events, 'failures': int(failures),
            'indexed_inspections_including_index_build': work, 'full_scan_inspections': full,
            'counter_initializations': counters, 'saving': 1-work/full if full else 0.}


def h5():
    rng = random.Random(20260926)
    fixtures, failures = [], 0
    for case in range(128):
        facts = [f'f{i}' for i in range(rng.randrange(4, 13))]
        rules = [(rng.choice(facts), sorted(rng.sample(facts, rng.randrange(1, min(3, len(facts))+1))))
                 for _ in range(rng.randrange(1, 21))]
        engine = GroundedRules(facts, rules)
        external = set(rng.sample(facts, rng.randrange(len(facts)+1)))
        initial = sorted(external)
        engine.update(external)
        events = []
        for step in range(8):
            external.symmetric_difference_update({rng.choice(facts)})
            got, oracle = engine.update(external), scan_closure(external, rules)
            failures += got['closure'] != oracle['closure']
            events.append({'external': sorted(external), 'proposed': got, 'oracle': oracle})
        fixtures.append({'case': case, 'facts': facts, 'rules': rules, 'initial_external': initial, 'events': events})
    rules = [('b', ['a']), ('a', ['b'])]
    engine = GroundedRules(['a', 'b', 'c'], rules+[('a', ['c'])])
    pure = engine.update([])
    seeded = engine.update(['a'])
    withdrawn = engine.update([])
    alternate = engine.update(['c'])
    unsafe = scan_closure(set(seeded['closure'])-{'a'}, rules)
    wrong = GroundedRules(['false_source', 'false_conclusion'], [('false_conclusion', ['false_source'])]).update(['false_source'])
    local, dense = rule_workload(), rule_workload(True)
    control_ok = not pure['closure'] and not withdrawn['closure'] and seeded['closure'] == ['a', 'b'] and alternate['closure'] == ['a', 'b', 'c']
    return {'primary_target_met': not failures and not local['failures'] and not dense['failures'] and control_ok and local['saving'] >= .75,
            'random_cases': 128, 'random_updates': 1024, 'closure_failures': int(failures), 'local': local, 'dense_control': dense,
            'controls': {'ungrounded_cycle': pure, 'seeded_cycle': seeded, 'withdrawn_cycle': withdrawn,
                         'alternate_ground': alternate, 'unsafe_warm_start': unsafe, 'wrong_external_source': wrong},
            'fixtures': fixtures, 'work_boundary': 'Cold recomputation per update. Index construction and dependency occurrence inspections counted; rule-counter initialization is separate. No distributed or incremental-deletion complexity claim.'}


def execute():
    from ..adaptive.run import load, INPUT
    values, _, audit = load()
    development = [r for r in values if r['split'] == 'development']
    test = [r for r in values if r['split'] == 'test']
    if len({r['id'] for r in values}) != len(values) or (len(development), len(test)) != (73, 263):
        raise ValueError('Frozen input identity/count mismatch')
    if {r['group'] for r in development} & {r['group'] for r in test}:
        raise ValueError('Source-group leakage')
    result = {'schema_version': 1, 'baseline_commit': BASELINE, 'protocol_commit': PROTOCOL,
              'protocol_sha256': sha(HERE/'PROTOCOL.md'), 'fresh_service_calls': 0,
              'source_hashes': {(INPUT/name).relative_to(ROOT).as_posix(): sha(INPUT/name)
                                for name in ('plan.json', 'calls.jsonl', 'predictions.json', 'results.json')},
              'implementation_sha256': {f'graph_synthesis/assumption_aware/{name}': sha(HERE/name) for name in ('methods.py', 'run.py')},
              'input_verification': audit,
              'development': {'n': len(development), 'groups': len({r['group'] for r in development})},
              'test': {'n': len(test), 'groups': len({r['group'] for r in test})},
              'evidence': 'H3 captured-response scoring with synthetic exposure and idealized review; H1/H2/H4/H5 controlled algorithms. No new semantic validation.'}
    for name, call in [('H1', h1), ('H2', h2), ('H3', lambda: h3(development, test)), ('H4', h4), ('H5', h5)]:
        result[name] = call()
        print(f"{name}: target {'met' if result[name]['primary_target_met'] else 'NOT met'}", flush=True)
    return clean(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    with (patch.object(socket.socket, 'connect', side_effect=RuntimeError('Network forbidden')),
         patch.object(socket.socket, 'connect_ex', side_effect=RuntimeError('Network forbidden')),
         patch.object(socket, 'create_connection', side_effect=RuntimeError('Network forbidden'))):
        result = execute()
    if args.check:
        from ..verify import compare_json
        compare_json(json.loads((HERE/'results.json').read_text(encoding='utf-8')), result)
    else:
        write(HERE/'results.json', result)
    print(json.dumps({'status': 'reproduced' if args.check else 'executed', 'targets': {f'H{i}': result[f'H{i}']['primary_target_met'] for i in range(1, 6)}, 'fresh_service_calls': 0}))


if __name__ == '__main__':
    main()
