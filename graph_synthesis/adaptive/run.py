"""Reproduce five frozen exploratory improvements without new service requests."""
from __future__ import annotations
import argparse
from collections import defaultdict
from contextlib import redirect_stdout
from io import StringIO
from itertools import combinations
import hashlib
import json
import math
from pathlib import Path
import random
import socket
from unittest.mock import patch

import numpy as np
from ..analyze_multicall import group_vectors, scores, verify
from ..multicall import decisions, prediction, read, rows
from ..verify import compare_json
from .methods import (POSITIVE, VIEWS, compact_route, safe_targeted, fit_clusters,
                      ensemble, fit_risk, assign_risks, review_order, optimize_batch, greedy_batch)

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
INPUT = ROOT / 'experiments/jev-multicall-20260918'
SEED = 20260919
DRAWS = 4000
PROTOCOL_COMMIT = '8c404bc997dad7a2b01b453429f566e47dfd3b2f'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n', encoding='utf-8', newline='\n')


def load():
    manifest = read(INPUT / 'artifact-manifest.json')['files']
    for name, expected in manifest.items():
        if sha(INPUT / name) != expected:
            raise ValueError('Archived input hash mismatch: '+name)
    with redirect_stdout(StringIO()):
        verification = verify(INPUT)
    calls = rows(INPUT / 'calls.jsonl')
    lookup = defaultdict(dict)
    for call in calls:
        lookup[call['id']][call['site']] = call
    values = read(INPUT / 'predictions.json')
    for row in values:
        if decisions(lookup[row['id']]) != row['arms']:
            raise ValueError('Raw decision mismatch')
        row['views'] = {key: prediction(lookup[row['id']][key]) for key in VIEWS}
    return values, lookup, verification


def summary(data, arm, selected=None):
    groups = sorted({r['group'] for r in data})
    value = scores(group_vectors(data, arm, groups, selected).sum(axis=0))
    # Normalize NumPy scalar rates before strict JSON-type replay comparison.
    value = {key: item.item() if isinstance(item, np.generic) else item for key, item in value.items()}
    contaminated = set()
    for row in data:
        label = row['arms'][arm]['label']
        if label in POSITIVE and label != row['gold'] and (selected is None or row['id'] in selected):
            contaminated.add(row['group'])
    return {**value, 'contaminated_groups': len(contaminated), 'groups': len(groups)}


def select(data, arm, k):
    return {r['id'] for r in sorted((r for r in data if r['arms'][arm]['label'] in POSITIVE),
            key=lambda r: (-r['arms'][arm]['score'], r['id']))[:k]}


def intervals(data, arm, baseline='single', selections=None):
    groups = sorted({r['group'] for r in data})
    weights = np.random.default_rng(SEED).multinomial(len(groups), np.full(len(groups), 1/len(groups)), size=DRAWS)
    def observations(name):
        values = weights @ group_vectors(data, name, groups, None if selections is None else selections[name])
        with np.errstate(divide='ignore', invalid='ignore'):
            return {'precision': values[:, 3]/values[:, 2], 'recall': values[:, 3]/values[:, 4],
                    'correct_edge_rate': values[:, 3]/values[:, 0],
                    'wrong_edge_rate': (values[:, 2]-values[:, 3])/values[:, 0],
                    'accuracy': values[:, 1]/values[:, 0]}
    a, b = observations(arm), observations(baseline)
    result = {}
    for key in a:
        delta = a[key]-b[key]
        valid = delta[np.isfinite(delta)]
        result[key] = {'draws': len(valid), '95': [float(x) for x in np.quantile(valid, [.025,.975])] if len(valid) else None,
                       '99': [float(x) for x in np.quantile(valid, [.005,.995])] if len(valid) else None}
    return result


def review_outcome(data, selected, sensitivity=1., false_removal=0.):
    if not 0 <= sensitivity <= 1 or not 0 <= false_removal <= 1:
        raise ValueError('Reviewer probabilities must lie in [0,1]')
    groups = defaultdict(list)
    correct, wrong, reviewed_correct = 0, 0, 0
    for row in data:
        label = row['views']['base1']['label']
        if label not in POSITIVE:
            continue
        if label == row['gold']:
            correct += 1
            reviewed_correct += row['id'] in selected
        else:
            groups[row['group']].append(row['id'])
            wrong += 1-sensitivity if row['id'] in selected else 1
    contaminated = sum(1. if any(key not in selected for key in keys) else 1-sensitivity**len(keys) for keys in groups.values())
    return {'expected_correct_edges': correct-false_removal*reviewed_correct,
            'expected_wrong_edges': wrong, 'expected_contaminated_groups': contaminated,
            'reviewed_correct': reviewed_correct, 'reviewed': len(selected)}


def review_experiment(development, test):
    fit = fit_risk(development, split='development')
    features = [{k: row[k] for k in ('id', 'group', 'views')} for row in test]
    candidates = assign_risks(features, fit)
    orders = {name: review_order(candidates, group_aware=flag) for name, flag in [('individual', False), ('group', True)]}
    budgets = []
    for budget in (10,20,30,40):
        policies = {}
        for name, order in orders.items():
            selected = set(order[:budget])
            policies[name] = {'selected': sorted(selected), 'primary': review_outcome(test, selected),
                              'sensitivity': [{'sensitivity': s, 'false_removal': f, **review_outcome(test, selected, s, f)}
                                              for s in (.5,.75,1.) for f in (0.,.01,.05)]}
        budgets.append({'budget': budget, 'policies': policies})
    primary = budgets[1]['policies']
    a, b = primary['group']['primary'], primary['individual']['primary']
    return {'fit': fit, 'risks': candidates, 'budgets': budgets,
            'risk_feature_input_tokens': sum(r['arms']['single']['input_tokens']+r['arms']['contrastive']['input_tokens'] for r in test),
            'primary_target_met': a['expected_contaminated_groups'] < b['expected_contaminated_groups'] and a['expected_correct_edges'] >= b['expected_correct_edges']}


def oracle_valid(assertions):
    """Independent finite truth-table oracle; never calls the conflict guard."""
    for instant in range(8):
        active = [r for r in assertions if r['start'] <= instant < r['end']]
        for a, b in combinations(active, 2):
            if (a['subject'],a['predicate'],a['scope']) != (b['subject'],b['predicate'],b['scope']):
                continue
            if a['object'] == b['object'] and a['polarity'] != b['polarity']:
                return False
            if a['predicate'] == 'located_in' and a['object'] != b['object'] and a['polarity'] == b['polarity'] == 1:
                return False
    return True


def oracle_optimum(assertions):
    best = 0
    for mask in range(1 << len(assertions)):
        subset = [r for i, r in enumerate(assertions) if mask & (1 << i)]
        if oracle_valid(subset):
            best = max(best, sum(r['weight'] for r in subset))
    return best


def assertion(key, start, end, obj, weight, **kwargs):
    return {'id': key, 'subject': 'S', 'predicate': 'located_in', 'object': obj, 'scope': 'A',
            'polarity': 1, 'start': start, 'end': end, 'weight': weight, **kwargs}


def graph_experiment():
    rng = random.Random(SEED)
    fixtures = []
    failures, permutation_failures, improvements = 0, 0, 0
    for case in range(128):
        values = []
        for i in range(8):
            start = rng.randrange(4)
            values.append(assertion(str(i), start, rng.randrange(start+1,8), str(rng.randrange(3)), rng.randrange(1,10),
                                    scope=rng.choice(['A','A','A','B']), polarity=rng.choice([1,1,1,-1])))
        optimal = optimize_batch(values)
        ordered, greedy = greedy_batch(values, priority=False), greedy_batch(values, priority=True)
        actual = [r for r in values if r['id'] in optimal['selected']]
        truth = oracle_optimum(values)
        failures += not oracle_valid(actual) or optimal['utility'] != truth or optimal['utility'] < greedy['utility']
        improvements += optimal['utility'] > greedy['utility']
        for shift in range(1,8):
            permutation_failures += optimize_batch(values[shift:]+values[:shift]) != optimal
        permutation_failures += optimize_batch(list(reversed(values))) != optimal
        fixtures.append({'case': case, 'assertions': values, 'joint': optimal, 'priority_greedy': greedy,
                         'input_greedy': ordered, 'oracle_utility': truth})
    counter = [assertion('wide',0,2,'B',5),assertion('early',0,1,'A',3),assertion('late',1,2,'A',3)]
    misleading = [assertion('false',0,2,'B',9), assertion('true',0,2,'A',8)]
    oversized = [assertion(str(i),0,2,str(i),1) for i in range(17)]
    return {'random_cases': 128, 'fixtures': fixtures, 'oracle_failures': int(failures),
            'permutation_checks': 128*8, 'permutation_failures': int(permutation_failures),
            'strict_improvements': int(improvements), 'primary_target_met': not failures and not permutation_failures and improvements >= .10*128,
            'counterexample': {'assertions': counter, 'joint': optimize_batch(counter), 'priority_greedy': greedy_batch(counter, priority=True)},
            'misleading_weight_control': {'assertions': misleading, 'joint': optimize_batch(misleading),
                                         'semantic_truth': ['true'], 'note': 'High-priority false evidence wins; consistency is not truth.'},
            'oversized': optimize_batch(oversized)}


def execute():
    values, calls, audit = load()
    development = [r for r in values if r['split']=='development']
    test = [r for r in values if r['split']=='test']
    fitted = fit_clusters(development, split='development')
    for row in values:
        panel = calls[row['id']]
        row['arms'].update({'compact_disagreement': compact_route(panel), 'compact_confidence': compact_route(panel, disagreement=False),
                            'safe_targeted': safe_targeted(panel), 'flat_vote': ensemble(panel, [[v] for v in VIEWS]),
                            'capped_vote': ensemble(panel, fitted['clusters'])})
    names = ('single','contrastive','targeted','repeat_vote','compact_confidence','compact_disagreement','safe_targeted','flat_vote','capped_vote')
    observed = {name: summary(test, name) for name in names}
    k = min(observed[name]['accepted'] for name in ('single','flat_vote','capped_vote'))
    selections = {name: select(test,name,k) for name in ('single','flat_vote','capped_vote')}
    matched = {name: summary(test,name,selected) for name,selected in selections.items()}
    base, one, two = observed['single'], observed['compact_disagreement'], observed['safe_targeted']
    three, flat = matched['capped_vote'], matched['flat_vote']
    result = {'schema_version': 1, 'baseline_commit': 'a1555ade897a570be811039f4760ef17e55b793a',
              'protocol_commit': PROTOCOL_COMMIT, 'fresh_service_calls': 0,
              'evidence': 'Exploratory saved-response replay, counterfactual token accounting, simulated review and finite graph oracles; not new inference',
              'source_hashes': {str((INPUT/name).relative_to(ROOT)): sha(INPUT/name) for name in ('plan.json','calls.jsonl','predictions.json','results.json')},
              'protocol_sha256': sha(HERE/'PROTOCOL.md'), 'input_verification': audit,
              'development': {'n':len(development),'groups':len({r['group'] for r in development})},
              'test': {'n':len(test),'groups':len({r['group'] for r in test})},
              'observed': observed, 'bootstrap': {'draws': DRAWS,'seed': SEED,'type':'paired source-group percentile, fixed policies and fixed matched ID sets; exploratory'},
              'H1': {'primary_target_met': one['input_tokens'] <= .60*base['input_tokens'] and one['correct_edges'] >= .98*base['correct_edges'] and one['wrong_edges'] <= base['wrong_edges'],
                     'token_saving':1-one['input_tokens']/base['input_tokens'], 'correct_retention':one['correct_edges']/base['correct_edges'],
                     'paired_vs_single': intervals(test,'compact_disagreement')},
              'H2': {'primary_target_met': two['errors'] <= .25*observed['targeted']['errors'] and two['correct_edges'] >= .98*base['correct_edges'] and two['wrong_edges'] <= base['wrong_edges'],
                     'error_reduction':1-two['errors']/observed['targeted']['errors'] if observed['targeted']['errors'] else None,
                     'paired_vs_single':intervals(test,'safe_targeted')},
              'H3': {'fit':fitted,'matched_k':k,'matched':matched,'selected_ids':{name:sorted(keys) for name,keys in selections.items()},
                     'primary_target_met':three['wrong_edges'] <= .80*flat['wrong_edges'] and observed['capped_vote']['correct_edges'] >= .95*base['correct_edges'],
                     'paired_vs_flat': intervals(test,'capped_vote','flat_vote',selections)},
              'H4':review_experiment(development,test), 'H5':graph_experiment()}
    predictions = [{k: row[k] for k in ('id','group','split','gold','arms')} for row in values]
    return result, predictions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('Network forbidden in adaptive replay')), patch.object(socket,'create_connection',side_effect=RuntimeError('Network forbidden in adaptive replay')):
        result, predictions = execute()
    outputs = {'results.json': result, 'predictions.json': predictions}
    if args.check:
        for name, value in outputs.items():
            compare_json(read(HERE/name),value)
    else:
        for name, value in outputs.items():
            write(HERE/name,value)
    print(json.dumps({'status':'reproduced' if args.check else 'executed', 'targets':{key:result[key]['primary_target_met'] for key in ('H1','H2','H3','H4','H5')}, 'fresh_service_calls':0}))


if __name__ == '__main__':
    main()
