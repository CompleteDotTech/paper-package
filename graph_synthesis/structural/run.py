"""Execute the frozen five-hypothesis study; network access is forbidden."""
from __future__ import annotations
import argparse
from collections import defaultdict
from itertools import combinations
import hashlib
import json
import math
from pathlib import Path
import random
import socket
from unittest.mock import patch
import numpy as np
from ..adaptive.run import load, summary, review_outcome
from ..adaptive.methods import POSITIVE, fit_risk, assign_risks
from ..risk_control.methods import optimal_review, independent_set
from ..followup.methods import exact_probability
from ..verify import compare_json
from .methods import (feature, fit_rank, select_rank, contamination_bounds, robust_review,
                      lineage_probability, cutset_independent_set)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SEED = 20260921
PROTOCOL_COMMIT = '466c3dadffee223d67eb06e2ad1032155fc84430'


def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n', encoding='utf-8', newline='\n')


def measure(rows, selected):
    result = summary(rows, 'single', set(selected))
    result['represented_groups'] = len({r['group'] for r in rows if r['id'] in selected})
    return result


def intervals(rows, selected, baseline):
    groups = sorted({r['group'] for r in rows})
    weights = np.random.default_rng(SEED).multinomial(len(groups), np.full(len(groups), 1/len(groups)), size=4000)
    def values(ids):
        array = []
        for group in groups:
            subset = [r for r in rows if r['group'] == group and r['id'] in ids]
            correct = sum(r['views']['base1']['label'] == r['gold'] for r in subset)
            array.append([len(subset), correct, int(correct < len(subset)), int(bool(subset))])
        x = weights @ np.array(array)
        return {'precision': x[:, 1]/x[:, 0], 'contaminated_group_fraction': x[:, 2]/len(groups),
                'represented_group_fraction': x[:, 3]/len(groups)}
    a, b = values(set(selected)), values(set(baseline))
    return {key: {'95': np.quantile(a[key]-b[key], [.025, .975]).tolist(),
                  '99': np.quantile(a[key]-b[key], [.005, .995]).tolist()} for key in a}


def acceptance(development, test):
    training = [{**feature(r), 'gold': r['gold'], 'split': r['split']} for r in development]
    features = [feature(r) for r in test]
    fit, unweighted = fit_rank(training), fit_rank(training, balanced=False)
    budgets = []
    for k in (100, 125, 145):
        ids = {'raw': select_rank(features, k), 'balanced': select_rank(features, k, fit),
               'unweighted': select_rank(features, k, unweighted), 'diverse': select_rank(features, k, diverse=True)}
        if any(len(x) != k for x in ids.values()):
            raise ValueError('Insufficient positive candidates for the frozen budget')
        budgets.append({'k': k, 'policies': {name: {'selected': keys, **measure(test, keys)} for name, keys in ids.items()},
                        'intervals_vs_raw': {name: intervals(test, keys, ids['raw']) for name, keys in ids.items() if name != 'raw'}})
    one, base = budgets[2]['policies']['balanced'], budgets[2]['policies']['raw']
    two, reference = budgets[0]['policies']['diverse'], budgets[0]['policies']['raw']
    natural = summary(test, 'single')
    return {'fit': fit, 'unweighted_fit': unweighted, 'budgets': budgets, 'natural_single': natural,
            'H1': {'primary_target_met': one['wrong_edges'] <= .8*base['wrong_edges'] and
                   one['correct_edges'] >= .95*natural['correct_edges'] and one['represented_groups'] >= base['represented_groups'],
                   'correct_retention': one['correct_edges']/natural['correct_edges']},
            'H2': {'primary_target_met': two['represented_groups'] >= 1.1*reference['represented_groups'] and
                   two['correct_edges'] >= .98*reference['correct_edges'] and two['contaminated_groups'] <= reference['contaminated_groups']}}


def review_experiment(development, test):
    fit = fit_risk(development, split='development')
    candidates = assign_risks([{k: r[k] for k in ('id', 'group', 'views')} for r in test], fit)
    budgets = []
    for budget in (10, 20, 30, 40):
        policies = {}
        for name, fn in [('independent', optimal_review), ('robust', robust_review)]:
            ids = fn(candidates, budget, .75)
            policies[name] = {'selected': ids, 'modeled': contamination_bounds(candidates, set(ids)),
                              'observed': review_outcome(test, set(ids), .75, .05),
                              'sensitivity': [{'sensitivity': s, 'false_removal': f, **review_outcome(test, set(ids), s, f)}
                                              for s in (.5, .75, 1.) for f in (0., .01, .05)]}
        budgets.append({'budget': budget, 'policies': policies})
    rng = random.Random(SEED)
    fixtures, failures, distributions, bound_failures = [], 0, [], 0
    for case in range(64):
        rows = [{'id': str(i), 'group': str(rng.randrange(3)), 'risk': rng.randrange(1, 10)/10} for i in range(8)]
        chosen = robust_review(rows, 3)
        def oracle(ids):
            return sum(min(1., sum(r['risk']*(.25 if r['id'] in ids else 1.) for r in rows if r['group'] == g))
                       for g in sorted({r['group'] for r in rows}))
        optimum = min(oracle(set(ids)) for ids in combinations([r['id'] for r in rows], 3))
        actual = oracle(set(chosen))
        failures += abs(actual-optimum) > 1e-12
        fixtures.append({'case': case, 'rows': rows, 'selected': chosen, 'oracle': optimum, 'actual': actual})
        mass = [rng.randrange(1, 20) for _ in range(16)]; total = sum(mass)
        distribution = [x/total for x in mass]
        marginals = [sum(p for mask, p in enumerate(distribution) if mask & (1 << i)) for i in range(4)]
        values = [{'id': str(i), 'group': 'g', 'risk': p} for i, p in enumerate(marginals)]
        observed = 0.
        for mask, p in enumerate(distribution):
            bad = {str(i) for i in range(4) if mask & (1 << i)}
            observed += p*(1 if bad-{'0', '1'} else 1-.75**len(bad))
        bounds = contamination_bounds(values, {'0', '1'})
        bound_failures += not bounds['lower']-1e-12 <= observed <= bounds['upper']+1e-12
        distributions.append({'mass': distribution, 'marginals': marginals, 'bounds': bounds, 'true_residual_union': observed})
    a, b = budgets[1]['policies']['robust'], budgets[1]['policies']['independent']
    return {'fit': fit, 'risks': candidates, 'budgets': budgets, 'oracle_fixtures': fixtures, 'oracle_failures': failures,
            'joint_distributions': distributions, 'bound_failures': bound_failures,
            'miscalibrated_control': {'supplied_marginals': [.01]*4, 'upper': .04, 'true_union': 1.},
            'risk_feature_input_tokens': sum(r['arms']['single']['input_tokens']+r['arms']['contrastive']['input_tokens'] for r in test),
            'primary_target_met': a['observed']['expected_contaminated_groups'] < b['observed']['expected_contaminated_groups']-1e-12 and
             a['observed']['expected_correct_edges'] >= b['observed']['expected_correct_edges']-1e-12 and
             a['modeled']['upper'] <= b['modeled']['upper']+1e-12,
            'algorithm_target_met': not failures and not bound_failures}


def lineage_experiment():
    rng = random.Random(SEED)
    fixtures, failures, invariance_failures, recovered, false_admissions = [], 0, 0, 0, 0
    for case in range(128):
        probabilities = {f'a{i}': rng.randrange(1, 10)/10 for i in range(8)}
        proofs = [rng.sample(list(probabilities), rng.randrange(1, 5)) for _ in range(rng.randrange(1, 10))]
        actual = lineage_probability(proofs, probabilities)
        oracle = exact_probability(proofs, probabilities)
        failures += actual['status'] != 'exact' or abs(actual['probability']-oracle) > 1e-10
        for copies in (1, 2, 5, 20):
            other = lineage_probability(list(reversed(proofs))*copies, probabilities)
            invariance_failures += other['status'] != 'exact' or abs(other['probability']-oracle) > 1e-10
        recovered += oracle >= .95 and actual['prior_bounds']['lower'] < .95 and actual['lower'] >= .95
        false_admissions += actual['lower'] >= .95 and oracle < .95-1e-10
        fixtures.append({'case': case, 'proofs': proofs, 'probabilities': probabilities, 'actual': actual, 'oracle': oracle})
    large = []
    for n in (8, 16, 32, 64, 96, 128, 192, 256):
        probabilities = {'hub': .99, **{f'x{i:03}': .5 for i in range(n-1)}}
        proofs = [['hub', f'x{i:03}'] for i in range(n-1)]
        actual = lineage_probability(proofs, probabilities)
        oracle = .99*(1-.5**(n-1))
        recovered += oracle >= .95 and actual['prior_bounds']['lower'] < .95 and actual['lower'] >= .95
        false_admissions += actual['lower'] >= .95 and oracle < .95-1e-10
        large.append({'atoms': n, 'proofs': proofs, 'probabilities': probabilities, 'actual': actual, 'oracle': oracle})
    budget_control = lineage_probability([['a', 'b'], ['b', 'c']], {'a': .5, 'b': .5, 'c': .5}, max_states=1)
    corrupt = lineage_probability([['a'], ['alias_a']], {'a': .9, 'alias_a': .9})
    large_failures = sum(r['actual']['status'] != 'exact' or abs(r['actual']['probability']-r['oracle']) > 1e-10 for r in large)
    return {'fixtures': fixtures, 'oracle_failures': failures, 'invariance_checks': 128*4, 'invariance_failures': invariance_failures,
            'large': large, 'large_failures': large_failures, 'recovered_admissions': recovered, 'false_admissions': false_admissions,
            'state_limit_control': budget_control, 'corrupt_lineage_control': {'reported': corrupt, 'true_probability': .9},
            'primary_target_met': not failures and not invariance_failures and not large_failures and recovered > 0 and not false_admissions}


def cycle(n, weighted=False):
    ids = [f'v{i:03}' for i in range(n)]
    adjacency = {v: {ids[(i-1) % n], ids[(i+1) % n]} for i, v in enumerate(ids)}
    weights = {v: 1+(7*i) % 11 if weighted else 1 for i, v in enumerate(ids)}
    return adjacency, weights


def cycle_oracle(weights):
    def path(sequence):
        before, last = 0, 0
        for value in sequence:
            before, last = last, max(last, before+value)
        return last
    values = [weights[v] for v in sorted(weights)]
    return max(path(values[1:]), values[0]+path(values[2:-1]))


def graph_experiment():
    rng = random.Random(SEED)
    fixtures, failures, permutation_failures = [], 0, 0
    for case in range(128):
        ids = [f'v{i}' for i in range(10)]
        graph = {v: set() for v in ids}
        for a, b in combinations(ids, 2):
            if rng.random() < .22:
                graph[a].add(b); graph[b].add(a)
        weights = {v: rng.randrange(0, 10) for v in ids}
        actual, prior = cutset_independent_set(graph, weights), independent_set(graph, weights)
        optimum = 0
        for mask in range(1 << len(ids)):
            selected = [v for i, v in enumerate(ids) if mask & (1 << i)]
            if all(b not in graph[a] for a, b in combinations(selected, 2)):
                optimum = max(optimum, sum(weights[v] for v in selected))
        consistent = all(b not in graph[a] for a, b in combinations(actual['selected'], 2))
        failures += not consistent or actual['utility'] != optimum or bool(actual['staged']) or actual['utility'] < prior['utility']
        for order in (list(reversed(ids)), ids[3:]+ids[:3]):
            permutation_failures += actual != cutset_independent_set({v: graph[v] for v in order}, {v: weights[v] for v in order})
        fixtures.append({'case': case, 'adjacency': {k: sorted(v) for k, v in graph.items()}, 'weights': weights,
                         'actual': actual, 'prior': prior, 'oracle': optimum})
    large = []
    for weighted in (False, True):
        for n in (17, 24, 32, 48, 64, 96, 128, 256):
            graph, weights = cycle(n, weighted)
            actual, prior = cutset_independent_set(graph, weights), independent_set(graph, weights)
            large.append({'n': n, 'weighted': weighted, 'weights': weights, 'actual': actual, 'prior': prior, 'oracle': cycle_oracle(weights)})
    clique = {str(i): {str(j) for j in range(17) if i != j} for i in range(17)}
    limit_graph, limit_weights = cycle(257)
    false_control = cutset_independent_set({'false': {'true'}, 'true': {'false'}}, {'false': 9, 'true': 8})
    large_failures = sum(r['actual']['utility'] != r['oracle'] or bool(r['actual']['staged']) for r in large)
    return {'fixtures': fixtures, 'oracle_failures': failures, 'permutation_checks': 256, 'permutation_failures': permutation_failures,
            'large': large, 'large_failures': large_failures, 'clique_control': cutset_independent_set(clique, {v: 1 for v in clique}),
            'oversized_control': cutset_independent_set(limit_graph, limit_weights),
            'false_priority_control': {'actual': false_control, 'truth': ['true']},
            'primary_target_met': not failures and not permutation_failures and not large_failures}


def execute():
    rows, calls, verification = load()
    development = [r for r in rows if r['split'] == 'development']
    test = [r for r in rows if r['split'] == 'test']
    assert not {r['group'] for r in development} & {r['group'] for r in test}
    rank = acceptance(development, test)
    source = ROOT/'experiments/jev-multicall-20260918'
    return {'schema_version': 1, 'baseline_commit': '338981392c77f4771cdbb58a9f8c90fd723da64a',
            'protocol_commit': PROTOCOL_COMMIT, 'seed': SEED, 'fresh_service_calls': 0,
            'evidence': 'Previously inspected saved-response replay; simulated reviewers; controlled exact algorithms. No production change.',
            'source_hashes': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in [source/name for name in ('plan.json', 'calls.jsonl', 'predictions.json', 'results.json')]},
            'verification': verification, 'development': {'n': len(development), 'groups': len({r['group'] for r in development})},
            'test': {'n': len(test), 'groups': len({r['group'] for r in test})},
            'acceptance': rank, 'H1': rank['H1'], 'H2': rank['H2'], 'H3': review_experiment(development, test),
            'H4': lineage_experiment(), 'H5': graph_experiment()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    with patch.object(socket, 'create_connection', side_effect=RuntimeError('Network disabled during benchmark')):
        result = execute()
    if args.check:
        expected = json.loads((HERE/'results.json').read_text(encoding='utf-8'))
        errors = compare_json(result, expected)
        if errors:
            raise SystemExit('\n'.join(errors[:20]))
    else:
        write(HERE/'results.json', result)
    print(json.dumps({'replay_verified': args.check, 'hypotheses': {f'H{i}': result[f'H{i}']['primary_target_met'] for i in range(1, 6)}}, indent=2))

if __name__ == '__main__':
    main()
