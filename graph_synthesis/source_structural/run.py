"""Execute the frozen source/structure suite with network access blocked."""
from __future__ import annotations
import argparse
from collections import defaultdict
from copy import deepcopy
import hashlib
from itertools import combinations, product
import json
import math
from pathlib import Path
import random
import socket
from unittest.mock import patch

from .methods import (POSITIVE, group_features, source_truth, fit_source, predict_source,
                      review_options, knapsack, budgeted_greedy, frontier_probability,
                      solve_conflicts, verify_certificate, LineageCache)
from ..reliability.methods import fit_small, assign_small, exact_lineage, solve_graph
from ..reliability.run import proper_scores, probability_oracle, independent_set_oracle, calibration as previous_calibration

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASELINE_COMMIT = 'a62a3257645d8e35cd4e45be53bfa9511d27724b'
PROTOCOL_COMMIT = 'b92009c6c36d87d9f3cbf0c92c2dad9f9615d726'
SEED, DRAWS = 20260922, 4000


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n', encoding='utf-8', newline='\n')


def normalized(value):
    return json.loads(json.dumps(value, sort_keys=True, allow_nan=False))


def feature_only(rows):
    return [{'id': r['id'], 'group': r['group'], 'views': {'base1': r['views']['base1']}} for r in rows]


def interval(deltas):
    import numpy as np
    values = np.asarray(deltas, dtype=float)
    if not len(values):
        raise ValueError('Paired groups required')
    rng = np.random.default_rng(SEED)
    draws = values[rng.integers(0, len(values), size=(DRAWS, len(values)))].mean(axis=1)
    return {'point': float(values.mean()), '95': [float(x) for x in np.quantile(draws, [.025, .975])],
            '99': [float(x) for x in np.quantile(draws, [.005, .995])], 'groups': len(values), 'draws': DRAWS}


def source_benchmark(development, test):
    folds = []
    for group in sorted(source_truth(development)):
        training = [r for r in development if r['group'] != group]
        held = [r for r in development if r['group'] == group]
        predictions = {str(a): predict_source(feature_only(held), fit_source(training, a))[group] for a in (1, 4, 16)}
        folds.append({'group': group, 'truth': source_truth(held)[group], 'predictions': predictions,
                      'fit_groups': sorted({r['group'] for r in training})})
    grid = [{'alpha': a, 'brier': sum((f['predictions'][str(a)]-f['truth'])**2 for f in folds)/len(folds)} for a in (1, 4, 16)]
    alpha = min(grid, key=lambda r: (r['brier'], -r['alpha']))['alpha']
    fit = fit_source(development, alpha)
    proposed = predict_source(feature_only(test), fit)
    truth = source_truth(test)
    previous = previous_calibration(development, test)
    comparators = {name: {r['group']: r[key] for r in previous['group_predictions']}
                   for name, key in (('raw_product', 'baseline'), ('scaled_product', 'proposed'))}
    scores = {k: proper_scores(ps, truth) for k, ps in comparators.items()}
    scores['direct_source'] = proper_scores(proposed, truth)
    new = scores['direct_source']
    return {'primary_target_met': new['brier'] <= .9*min(scores[k]['brier'] for k in comparators) and abs(new['bias']) <= .03,
            'fit': fit, 'folds': folds, 'grid': grid, 'alpha': alpha, 'previous_multiplier': previous['multiplier'], 'scores': scores,
            'paired_brier': {k: interval([(proposed[g]-truth[g])**2-(ps[g]-truth[g])**2 for g in sorted(truth)]) for k, ps in comparators.items()},
            'groups': [{'group': g, 'features': list(group_features(feature_only(test))[g]), 'truth': truth[g],
                        'direct_source': proposed[g], **{k: ps[g] for k, ps in comparators.items()}} for g in sorted(truth)]}


def evaluate_review(rows, selected, sensitivity, false_removal, correlated=False):
    selected = set(selected)
    wrong = defaultdict(list)
    correct_total = correct_reviewed = wrong_total = wrong_reviewed = 0
    for row in rows:
        label = row['views']['base1']['label']
        if label not in POSITIVE:
            continue
        reviewed = row['id'] in selected
        if label == row['gold']:
            correct_total += 1
            correct_reviewed += reviewed
        else:
            wrong[row['group']].append(reviewed)
            wrong_total += 1
            wrong_reviewed += reviewed
    contamination = {}
    for group in sorted({r['group'] for r in rows}):
        states = wrong[group]
        contamination[group] = (0. if not states else 1. if not all(states)
                                else 1-sensitivity if correlated else 1-sensitivity**len(states))
    return {'expected_contaminated_groups': sum(contamination.values()),
            'expected_wrong_edges': wrong_total-sensitivity*wrong_reviewed,
            'expected_correct_removed': false_removal*correct_reviewed,
            'expected_correct_retained': correct_total-false_removal*correct_reviewed,
            'reviewed_wrong': wrong_reviewed, 'reviewed_correct': correct_reviewed,
            'group_contamination': contamination}


def review_benchmark(development, test):
    fit = fit_small(development)
    risks = assign_small(feature_only(test), fit)
    scenarios = []
    for budget, setup, sensitivity in product((20, 40, 80), (0, 1, 2, 5), (.5, .75, 1.)):
        selections = {'greedy': budgeted_greedy(risks, budget, setup),
                      'source_batch': knapsack(review_options(risks, setup, sensitivity), budget)}
        for false_removal in (0., .01, .05):
            policies = {name: {**selection, 'evaluation': evaluate_review(test, selection['selected'], sensitivity, false_removal),
                               'correlated_detection': evaluate_review(test, selection['selected'], sensitivity, false_removal, True)}
                        for name, selection in selections.items()}
            scenarios.append({'budget': budget, 'setup': setup, 'sensitivity': sensitivity,
                              'false_removal': false_removal, 'policies': policies})
    primary = next(r for r in scenarios if (r['budget'], r['setup'], r['sensitivity'], r['false_removal']) == (40, 2, .75, .01))
    a, b = [primary['policies'][k]['evaluation'] for k in ('source_batch', 'greedy')]
    rng, fixtures, failures = random.Random(SEED), [], 0
    for case in range(64):
        candidates = [{'id': f'g{g}e{i}', 'group': f'g{g}', 'risk': rng.choice([0., .05, .2, .5, .9])}
                      for g in range(rng.randrange(1, 6)) for i in range(rng.randrange(1, 4))]
        budget, setup = rng.randrange(1, 9), rng.randrange(4)
        options = review_options(candidates, setup, .75)
        exact = knapsack(options, budget)
        feasible = [(sum(o['benefit'] for o in choice), sum(o['cost'] for o in choice))
                    for choice in product(*(options[g] for g in sorted(options))) if sum(o['cost'] for o in choice) <= budget]
        optimum = max(x[0] for x in feasible)
        failures += abs(exact['predicted_benefit']-optimum) > 1e-12 or exact['spent'] > budget
        fixtures.append({'case': case, 'candidates': candidates, 'setup': setup, 'budget': budget, 'result': exact, 'oracle_benefit': optimum})
    by_id = {r['id']: r for r in risks}
    budget_failures = 0
    for row in scenarios:
        for result in row['policies'].values():
            ids = result['selected']
            actual_cost = len(ids)+row['setup']*len({by_id[k]['group'] for k in ids})
            budget_failures += actual_cost != result['spent'] or actual_cost > row['budget']
    return {'primary_target_met': b['expected_contaminated_groups']-a['expected_contaminated_groups'] >= .5
            and a['expected_correct_removed'] <= b['expected_correct_removed']+.1 and not failures and not budget_failures,
            'fit': fit, 'risks': risks, 'primary': primary, 'scenarios': scenarios, 'oracle_fixtures': fixtures,
            'oracle_failures': int(failures), 'budget_failures': int(budget_failures),
            'feature_input_tokens': sum(r['arms']['single']['input_tokens'] for r in test),
            'paired_contamination_rate': interval([a['group_contamination'][g]-b['group_contamination'][g] for g in sorted(a['group_contamination'])]),
            'cost_note': 'Setup-plus-edge units are hypothetical. Feature tokens are recorded separately; no human-time or dollar costs are inferred.'}


def chain_oracle(n, p=.1, cycle=False):
    """Independent no-adjacent-success recurrence (condition on the first bit)."""
    if not cycle:
        a, b = 1., 0.
        for _ in range(n):
            a, b = (a+b)*(1-p), a*p
        return 1-a-b
    total = 0.
    for first in (0, 1):
        a, b = ((1-p), 0.) if not first else (0., p)
        for _ in range(n-1):
            a, b = (a+b)*(1-p), a*p
        total += a + (0. if first else b)
    return 1-total


def chain_fixture(n, cycle=False):
    keys = [f'a{i:03d}' for i in range(n)]
    proofs = [[keys[i], keys[i+1]] for i in range(n-1)]
    if cycle:
        proofs.append([keys[-1], keys[0]])
    return proofs, {a: .1 for a in keys}


def lineage_benchmark():
    rng = random.Random(SEED)
    fixtures, failures, invariance, false_admissions = [], 0, 0, 0
    for case in range(192):
        n = rng.randrange(2, 11)
        keys = [f'a{i:02d}' for i in range(n)]
        probabilities = {a: rng.choice([0., .02, .1, .5, .8, .99, 1.]) for a in keys}
        proofs = [sorted(rng.sample(keys, rng.randrange(1, min(n, 4)+1))) for _ in range(rng.randrange(1, 16))]
        oracle = probability_oracle(proofs, probabilities)
        result = frontier_probability(proofs, probabilities)
        failures += not result['exact'] or abs(result['lower']-oracle) > 1e-12
        false_admissions += result['lower'] >= .95 and oracle < .95-1e-12
        for copies in (1, 2, 5, 10):
            permuted = frontier_probability([list(reversed(p)) for p in reversed(proofs)]*copies, dict(reversed(list(probabilities.items()))))
            invariance += permuted != result
        fixtures.append({'case': case, 'probabilities': probabilities, 'proofs': proofs, 'oracle': oracle,
                         'previous': exact_lineage(proofs, probabilities), 'proposed': result})
    large = []
    for kind in ('path', 'cycle'):
        for n in (17, 32, 64, 128, 256):
            proofs, probabilities = chain_fixture(n, kind == 'cycle')
            result = frontier_probability(proofs, probabilities)
            previous = exact_lineage(proofs, probabilities)
            oracle = chain_oracle(n, cycle=kind == 'cycle')
            large.append({'kind': kind, 'n': n, 'proofs': proofs, 'probabilities': probabilities,
                          'oracle': oracle, 'previous': previous, 'proposed': result})
    large_failures = sum(not r['proposed']['exact'] or abs(r['proposed']['lower']-r['oracle']) > 1e-12 for r in large)
    dense_p = {f'a{i:03d}': .1 for i in range(17)}
    dense_proofs = list(combinations(dense_p, 2))
    dense = {'result': frontier_probability(dense_proofs, dense_p), 'oracle': 1-.9**17-17*.1*.9**16}
    proofs, probabilities = chain_fixture(257)
    over_cap = frontier_probability(proofs, probabilities)
    short, ps = chain_fixture(8)
    state_cap = frontier_probability(short, ps, state_cap=1)
    constants = [frontier_probability([], {}), frontier_probability([[]], {}), frontier_probability([['a']], {'a': 0.}), frontier_probability([['a']], {'a': 1.})]
    controls_ok = (not dense['result']['exact'] and dense['result']['lower'] <= dense['oracle'] <= dense['result']['upper']
                   and over_cap.get('reason') == 'input_cap' and state_cap.get('reason') == 'state_cap'
                   and all(abs(r['lower']-p) < 1e-12 for r, p in zip(constants, (0., 1., 0., 1.))))
    tightened = sum(r['previous']['upper']-r['previous']['lower'] > r['proposed']['upper']-r['proposed']['lower']+1e-12 for r in large)
    return {'primary_target_met': not failures and not invariance and not false_admissions and not large_failures and tightened > 0 and controls_ok,
            'fixtures': fixtures, 'random_cases': len(fixtures), 'oracle_failures': int(failures), 'invariance_checks': 768,
            'invariance_failures': int(invariance), 'false_admissions': int(false_admissions), 'large': large,
            'large_failures': int(large_failures), 'tightened_large': tightened, 'dense_control': dense,
            'input_cap_control': over_cap, 'state_cap_control': state_cap, 'constant_controls': constants,
            'false_independence_control': {'actual_source_probability': .8,
                 'shared': frontier_probability([['a'], ['a']], {'a': .8}),
                 'falsely_split': frontier_probability([['a'], ['b']], {'a': .8, 'b': .8})}}


def consistent(result, edges):
    selected = set(result['selected'])
    return not any(a in selected and b in selected for a, b in edges)


def certificates_ok(result, weights, edges):
    return all(verify_certificate({k: weights[k] for k in c['certificate']['nodes']},
                   [(a, b) for a, b in edges if a in c['certificate']['nodes'] and b in c['certificate']['nodes']], c)
               for c in result['components'] if c['method'] == 'bipartite_flow')


def grid_fixture(side):
    weights = {f'r{i:02d}c{j:02d}': 1 for i in range(side) for j in range(side)}
    edges = []
    for i in range(side):
        for j in range(side):
            a = f'r{i:02d}c{j:02d}'
            if i+1 < side:
                edges.append((a, f'r{i+1:02d}c{j:02d}'))
            if j+1 < side:
                edges.append((a, f'r{i:02d}c{j+1:02d}'))
    return weights, edges, (side*side+1)//2


def complete_fixture(side):
    weights = {**{f'L{i:03d}': 3 for i in range(side)}, **{f'R{i:03d}': 5 for i in range(side)}}
    edges = [(f'L{i:03d}', f'R{j:03d}') for i in range(side) for j in range(side)]
    return weights, edges, 5*side


def conflict_benchmark():
    rng = random.Random(SEED)
    fixtures, failures, invariance = [], 0, 0
    for case in range(192):
        n = rng.randrange(4, 12)
        weights = {f'n{i:02d}': rng.randrange(10) for i in range(n)}
        keys = list(weights)
        edges = [(a, b) for i, a in enumerate(keys) for j, b in enumerate(keys) if i < j and rng.random() < .35
                 and (case % 2 or (i < n//2 <= j))]
        result, previous = solve_conflicts(weights, edges), solve_graph(weights, edges)
        oracle = independent_set_oracle(weights, edges)
        failures += (result['utility'] != oracle or result['utility'] < previous['utility'] or not consistent(result, edges)
                     or bool(result['staged']) or not certificates_ok(result, weights, edges))
        for shift in (1, 2, 3, 4):
            ordered = keys[shift:]+keys[:shift]
            invariance += solve_conflicts({k: weights[k] for k in ordered}, [(b, a) for a, b in reversed(edges)]) != result
        fixtures.append({'case': case, 'weights': weights, 'edges': edges, 'oracle': oracle, 'previous': previous, 'proposed': result})
    large = []
    for kind, sizes in (('grid', (5, 6, 8, 12, 16)), ('complete_bipartite', (9, 16, 32, 64, 128))):
        for size in sizes:
            w, es, oracle = grid_fixture(size) if kind == 'grid' else complete_fixture(size)
            proposed, previous = solve_conflicts(w, es), solve_graph(w, es)
            large.append({'kind': kind, 'size': size, 'n': len(w), 'weights': w, 'edges': es, 'oracle': oracle,
                          'proposed': proposed, 'previous': previous, 'certificates_valid': certificates_ok(proposed, w, es),
                          'consistent': consistent(proposed, es)})
    large_failures = sum(r['proposed']['utility'] != r['oracle'] or bool(r['proposed']['staged']) or not r['certificates_valid'] or not r['consistent'] for r in large)
    improved = sum(r['proposed']['utility'] > r['previous']['utility'] for r in large)
    dense_keys = [f'd{i:02d}' for i in range(17)]
    dense = solve_conflicts({k: 1 for k in dense_keys}, list(combinations(dense_keys, 2)))
    w, es, _ = complete_fixture(9)
    cap_control = solve_conflicts(w, es, inspection_cap=1)
    cw, ce, _ = complete_fixture(2)
    valid = solve_conflicts(cw, ce)['components'][0]
    damaged = deepcopy(valid)
    damaged['certificate']['flow_value'] += 1
    rejected = not verify_certificate(cw, ce, damaged)
    semantic = solve_conflicts({'false': 9, 'true': 8}, [('false', 'true')])
    return {'primary_target_met': not failures and not invariance and not large_failures and improved >= 4 and rejected,
            'fixtures': fixtures, 'random_cases': len(fixtures), 'oracle_failures': int(failures), 'invariance_checks': 768,
            'invariance_failures': int(invariance), 'large': large, 'large_failures': int(large_failures), 'improved_large': improved,
            'dense_nonbipartite_control': dense, 'work_cap_control': cap_control, 'damaged_certificate_rejected': rejected,
            'semantic_control': {'result': semantic, 'gold_true': ['true'], 'note': 'A false assertion wins under false supplied priorities.'}}


def full_lineage(facts, probabilities):
    values = {}
    for key, proofs in sorted(facts.items()):
        deps = sorted({a for term in proofs for a in term})
        result = frontier_probability(proofs, {a: probabilities[a] for a in deps})
        values[key] = {k: result[k] for k in ('lower', 'upper', 'exact')}
    return values


def cache_correct(cache, facts, probabilities):
    snap = cache.snapshot()
    expected = full_lineage(facts, probabilities)
    index = defaultdict(set)
    for key, terms in facts.items():
        # Canonical removal of redundant proofs can remove redundant dependencies.
        from .methods import normalize_proofs
        for term in normalize_proofs(terms, probabilities):
            for atom in term:
                index[atom].add(key)
    return (snap['values'] == expected and snap['probabilities'] == probabilities
            and snap['index'] == {a: sorted(ks) for a, ks in sorted(index.items())}), expected


def cache_benchmark():
    rng = random.Random(SEED)
    fixtures, failures = [], 0
    for case in range(32):
        ps = {f'a{i:02d}': .9 for i in range(12)}
        keys = sorted(ps)
        make = lambda: [sorted(rng.sample(keys, rng.randrange(1, 4))) for _ in range(rng.randrange(1, 4))]
        facts = {f'f{i}': make() for i in range(8)}
        initial = deepcopy({'facts': facts, 'probabilities': ps})
        cache, events = LineageCache(facts, ps), []
        for step in range(20):
            if step % 5 in (0, 4):
                changes = {a: (0. if step % 5 == 4 else rng.choice([0., .1, .5, .9, 1.])) for a in rng.sample(keys, 2)}
                mutation = {'kind': 'probabilities', 'changes': changes}
                cache.update_probabilities(changes, cache.revision)
                ps.update(changes)
            elif step % 5 in (1, 3):
                key = rng.choice(sorted(facts)) if step % 5 == 1 else f'new{step}'
                proofs = make()
                mutation = {'kind': 'set_fact', 'id': key, 'proofs': proofs}
                cache.set_fact(key, proofs, cache.revision)
                facts[key] = proofs
            else:
                key = rng.choice(sorted(facts))
                mutation = {'kind': 'remove_fact', 'id': key}
                cache.remove_fact(key, cache.revision)
                del facts[key]
            correct, expected = cache_correct(cache, facts, ps)
            failures += not correct or cache.revision != step+1
            events.append({'step': step, 'mutation': mutation, 'revision': cache.revision, 'actual': cache.snapshot()['values'],
                           'full': expected, 'evaluations_cumulative': cache.evaluations, 'index_touches_cumulative': cache.index_touches})
        fixtures.append({'case': case, 'initial': initial, 'events': events})
    # Explicit event sequence: revoke, change proof, remove, reinsert, recover source.
    ps, facts = {'a': .9, 'b': .8}, {'f': [['a']]}
    cache, controls = LineageCache(facts, ps), []
    for kind, arg in [('revoke', 0.), ('replace', [['b']]), ('remove', None), ('reinsert', [['a', 'b']]), ('recover', .9)]:
        if kind in ('revoke', 'recover'):
            cache.update_probabilities({'a': arg}, cache.revision); ps['a'] = arg
        elif kind == 'remove':
            cache.remove_fact('f', cache.revision); del facts['f']
        else:
            cache.set_fact('f', arg, cache.revision); facts['f'] = arg
        correct, expected = cache_correct(cache, facts, ps)
        failures += not correct
        controls.append({'kind': kind, 'actual': cache.snapshot()['values'], 'full': expected})
    atomic = []
    def attempt(name, action):
        before = (cache.snapshot(), cache.evaluations, cache.index_touches)
        rejected = False
        try:
            action()
        except (ValueError, RuntimeError):
            rejected = True
        passed = rejected and before == (cache.snapshot(), cache.evaluations, cache.index_touches)
        atomic.append({'case': name, 'rejected_without_mutation': passed})
        return passed
    attempt('stale_revision', lambda: cache.update_probabilities({'a': .1}, cache.revision-1))
    attempt('invalid_probability', lambda: cache.update_probabilities({'a': float('nan')}, cache.revision))
    attempt('unknown_source', lambda: cache.update_probabilities({'unknown': .5}, cache.revision))
    attempt('invalid_proof', lambda: cache.set_fact('f', [['unknown']], cache.revision))
    attempt('unknown_fact', lambda: cache.remove_fact('missing', cache.revision))
    with patch.object(cache, '_evaluate', side_effect=RuntimeError('Injected precommit calculation failure')):
        attempt('calculation_failure', lambda: cache.update_probabilities({'a': .1}, cache.revision))
        attempt('proof_calculation_failure', lambda: cache.set_fact('f', [['b']], cache.revision))
    def workload(global_source=False):
        ps = {f'f{i:03d}{a}': .9 for i in range(128) for a in ('a', 'b', 'c')}
        if global_source:
            ps['shared'] = .9
        facts = {f'f{i:03d}': [[('shared' if global_source else f'f{i:03d}a'), f'f{i:03d}b'],
                            [('shared' if global_source else f'f{i:03d}b'), f'f{i:03d}c']] for i in range(128)}
        engine = LineageCache(facts, ps)
        full_evaluations = len(facts)
        wrong = 0
        updates = 16 if global_source else 256
        events = []
        for step in range(updates):
            atom = 'shared' if global_source else f'f{step%128:03d}a'
            p = (0. if step % 2 == 0 else .5) if global_source else (0. if step < 128 else .5)
            engine.update_probabilities({atom: p}, engine.revision)
            ps[atom] = p
            correct, _ = cache_correct(engine, facts, ps)
            wrong += not correct
            full_evaluations += len(facts)
            events.append({'step': step, 'atom': atom, 'probability': p, 'incremental_evaluations': engine.evaluations,
                           'full_evaluations': full_evaluations, 'index_touches': engine.index_touches})
        return {'facts': len(facts), 'updates': updates, 'includes_cold_build': True, 'mismatches': int(wrong),
                'incremental_evaluations': engine.evaluations, 'full_evaluations': full_evaluations,
                'saving': 1-engine.evaluations/full_evaluations, 'index_touches': engine.index_touches, 'events': events}
    local, global_control = workload(), workload(True)
    atomic_failures = sum(not r['rejected_without_mutation'] for r in atomic)
    return {'primary_target_met': not failures and not atomic_failures and not local['mismatches'] and not global_control['mismatches'] and local['saving'] >= .9,
            'mutation_cases': 640, 'mismatches': int(failures), 'fixtures': fixtures, 'explicit_controls': controls,
            'atomic_controls': atomic, 'atomic_failures': atomic_failures, 'local_workload': local, 'global_source_control': global_control,
            'work_boundary': 'Fact reevaluations and dependency-index touches only; no total CPU, latency, disk I/O, concurrency or durability claim.'}


def execute():
    from ..adaptive.run import load, INPUT
    values, calls, audit = load()
    development = [r for r in values if r['split'] == 'development']
    test = [r for r in values if r['split'] == 'test']
    if len({r['id'] for r in values}) != len(values):
        raise ValueError('Duplicate candidate IDs')
    if (len(development), len(test)) != (73, 263) or {r['group'] for r in development} & {r['group'] for r in test}:
        raise ValueError('Frozen split or source separation changed')
    return {'schema_version': 1, 'baseline_commit': BASELINE_COMMIT, 'protocol_commit': PROTOCOL_COMMIT,
            'protocol_sha256': sha(HERE/'PROTOCOL.md'), 'seed': SEED, 'fresh_service_calls': 0,
            'evidence': 'H1 reused saved predictions; H2 simulated review; H3-H5 controlled algorithms. No independent semantic test.',
            'development': {'n': len(development), 'groups': len({r['group'] for r in development})},
            'test': {'n': len(test), 'groups': len({r['group'] for r in test})}, 'input_verification': audit,
            'source_hashes': {(INPUT/name).relative_to(ROOT).as_posix(): sha(INPUT/name) for name in ('plan.json', 'calls.jsonl', 'predictions.json', 'results.json')},
            'bootstrap': {'draws': DRAWS, 'seed': SEED, 'note': 'Paired fixed-fit source-group intervals; descriptive, non-simultaneous, repeated evaluation data.'},
            'H1': source_benchmark(development, test), 'H2': review_benchmark(development, test),
            'H3': lineage_benchmark(), 'H4': conflict_benchmark(), 'H5': cache_benchmark()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    with patch.object(socket.socket, 'connect', side_effect=RuntimeError('Network forbidden in source/structure replay')), patch.object(socket, 'create_connection', side_effect=RuntimeError('Network forbidden in source/structure replay')):
        result = normalized(execute())
    if args.check:
        from ..verify import compare_json
        compare_json(json.loads((HERE/'results.json').read_text(encoding='utf-8')), result)
    else:
        write(HERE/'results.json', result)
    print(json.dumps({'status': 'reproduced' if args.check else 'executed',
          'targets': {f'H{i}': result[f'H{i}']['primary_target_met'] for i in range(1, 6)}, 'fresh_service_calls': 0}))


if __name__ == '__main__':
    main()
