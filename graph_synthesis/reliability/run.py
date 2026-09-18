"""Execute the frozen reliability suite with network access disabled."""
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

from .methods import (POSITIVE, fit_small, assign_small, group_risks, lineage_bounds,
                      exact_lineage, solve_graph, IncrementalSolver)

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SEED = 20260921
PROTOCOL_COMMIT = '19fdb341f8f3d281eeffbd9984f9d8287a468a6c'
BASELINE_COMMIT = '338981392c77f4771cdbb58a9f8c90fd723da64a'
DRAWS = 4000


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n', encoding='utf-8', newline='\n')


def features(rows):
    return [{k: row[k] for k in ('id', 'group', 'views')} for row in rows]


def truth_by_group(rows):
    result = {}
    for r in rows:
        label = r['views']['base1']['label']
        if label in POSITIVE:
            result[r['group']] = max(result.get(r['group'], 0), int(label != r['gold']))
    return result


def proper_scores(probabilities, truth):
    if set(probabilities) != set(truth) or not truth:
        raise ValueError('Require identical nonempty group denominators')
    groups = sorted(truth)
    return {'n': len(groups), 'brier': sum((probabilities[g]-truth[g])**2 for g in groups)/len(groups),
            'log_loss': -sum(truth[g]*math.log(max(1e-12, probabilities[g]))+(1-truth[g])*math.log(max(1e-12,1-probabilities[g])) for g in groups)/len(groups),
            'mean_predicted': sum(probabilities.values())/len(groups),
            'mean_observed': sum(truth.values())/len(groups),
            'bias': (sum(probabilities.values())-sum(truth.values()))/len(groups)}


def mean_interval(deltas):
    import numpy as np
    values = np.asarray(deltas, dtype=float)
    if not len(values):
        raise ValueError('Nonempty paired units required')
    rng = np.random.default_rng(SEED)
    sample = values[rng.integers(0, len(values), size=(DRAWS, len(values)))].mean(axis=1)
    return {'point': float(values.mean()), '95': [float(x) for x in np.quantile(sample, [.025,.975])],
            '99': [float(x) for x in np.quantile(sample, [.005,.995])], 'groups': len(values), 'draws': DRAWS}


def calibration(development, test):
    from ..adaptive.methods import fit_risk, assign_risks
    folds = []
    for group in sorted({r['group'] for r in development}):
        training = [r for r in development if r['group'] != group]
        held = [r for r in development if r['group'] == group]
        fitted = fit_risk(training, split='development')
        probabilities = group_risks(assign_risks(features(held), fitted))
        truth = truth_by_group(held)
        if probabilities:
            folds.append({'group': group, 'probability': probabilities[group], 'truth': truth[group],
                          'fit_groups': sorted({r['group'] for r in training})})
    if not folds:
        raise ValueError('No accepted development groups for calibration')
    candidates = []
    for k in (.25,.5,.75,1.,1.5,2.,3.,4.):
        loss = sum((1-(1-r['probability'])**k-r['truth'])**2 for r in folds)/len(folds)
        candidates.append({'multiplier': k, 'brier': loss})
    chosen = min(candidates, key=lambda r: (r['brier'], abs(r['multiplier']-1), r['multiplier']))['multiplier']
    fitted = fit_risk(development, split='development')
    risks = assign_risks(features(test), fitted)
    base, proposed, truth = group_risks(risks), group_risks(risks, chosen), truth_by_group(test)
    baseline_scores, new_scores = proper_scores(base, truth), proper_scores(proposed, truth)
    deltas = [(proposed[g]-truth[g])**2-(base[g]-truth[g])**2 for g in sorted(truth)]
    return {'primary_target_met': new_scores['brier'] <= .9*baseline_scores['brier'] and abs(new_scores['bias']) <= .03,
            'fit': fitted, 'multiplier': chosen, 'folds': folds, 'grid': candidates,
            'baseline': baseline_scores, 'proposed': new_scores, 'paired_brier': mean_interval(deltas),
            'group_predictions': [{'group': g, 'truth': truth[g], 'baseline': base[g], 'proposed': proposed[g]} for g in sorted(truth)]}


def contamination_vector(test, selected):
    contaminated = set()
    for r in test:
        label = r['views']['base1']['label']
        if label in POSITIVE and label != r['gold'] and r['id'] not in selected:
            contaminated.add(r['group'])
    return {g: int(g in contaminated) for g in sorted({r['group'] for r in test})}


def review(development, test):
    from ..adaptive.methods import fit_risk, assign_risks, review_order
    from ..adaptive.run import review_outcome
    fit = fit_small(development)
    richer_fit = fit_risk(development, split='development')
    # Small-policy execution is physically given only base1, not the compact view.
    cheap_features = [{'id': r['id'], 'group': r['group'], 'views': {'base1': r['views']['base1']}} for r in test]
    candidates = {'single_view': assign_small(cheap_features, fit), 'two_view': assign_risks(features(test), richer_fit)}
    orders = {k: review_order(v, group_aware=True) for k, v in candidates.items()}
    budgets = []
    for budget in (10,20,30,40):
        policies = {}
        for name, order in orders.items():
            selected = set(order[:budget])
            policies[name] = {'selected': sorted(selected), 'primary': review_outcome(test, selected),
                              'sensitivity': [{'sensitivity': s, 'false_removal': f, **review_outcome(test, selected, s, f)}
                                              for s in (.5,.75,1.) for f in (0.,.01,.05)]}
        budgets.append({'budget': budget, 'policies': policies})
    costs = {'single_view': sum(r['arms']['single']['input_tokens'] for r in test),
             'two_view': sum(r['arms']['single']['input_tokens']+r['arms']['contrastive']['input_tokens'] for r in test)}
    primary = budgets[1]['policies']
    a, b = primary['single_view']['primary'], primary['two_view']['primary']
    av = contamination_vector(test, set(primary['single_view']['selected']))
    bv = contamination_vector(test, set(primary['two_view']['selected']))
    saving = 1-costs['single_view']/costs['two_view']
    return {'primary_target_met': a['expected_contaminated_groups'] <= b['expected_contaminated_groups'] and a['expected_correct_edges'] >= b['expected_correct_edges'] and saving >= .25,
            'fit': fit, 'richer_fit': richer_fit, 'budgets': budgets, 'feature_tokens': costs, 'token_saving': saving,
            'paired_contamination_rate': mean_interval([av[g]-bv[g] for g in av])}


def probability_oracle(proofs, probabilities):
    """Independent finite assignment enumeration, not Shannon recursion."""
    atoms = sorted(probabilities)
    if len(atoms) > 16:
        raise ValueError('Oracle cap exceeded')
    total = 0.
    for mask in range(1 << len(atoms)):
        assignment = {a: bool(mask & (1 << i)) for i, a in enumerate(atoms)}
        if any(all(assignment[a] for a in proof) for proof in proofs):
            total += math.prod(probabilities[a] if assignment[a] else 1-probabilities[a] for a in atoms)
    return total


def lineage_benchmark():
    rng = random.Random(SEED)
    fixtures, failures, invariant_failures, false_admissions = [], 0, 0, 0
    for case in range(128):
        n = rng.randrange(2,9)
        atoms = [f'a{i}' for i in range(n)]
        probs = {a: rng.choice([.2,.5,.8,.95,.99]) for a in atoms}
        proofs = [sorted(rng.sample(atoms, rng.randrange(1,min(n,4)+1))) for _ in range(rng.randrange(1,11))]
        truth = probability_oracle(proofs, probs)
        bounds, exact = lineage_bounds(proofs, probs), exact_lineage(proofs, probs)
        failures += not exact['exact'] or abs(exact['lower']-truth) > 1e-12 or abs(exact['upper']-truth) > 1e-12
        false_admissions += exact['lower'] >= .95 and truth < .95-1e-12
        for copies in (1,2,5,20):
            invariant_failures += exact_lineage(list(reversed(proofs))*copies, probs) != exact
        fixtures.append({'case': case, 'probabilities': probs, 'proofs': proofs, 'oracle': truth,
                         'bounds': bounds, 'exact': exact})
    fan_probs = {'shared': .99, **{f'p{i}': .5 for i in range(8)}}
    fan_proofs = [['shared', f'p{i}'] for i in range(8)]
    fan = {'probabilities': fan_probs, 'proofs': fan_proofs, 'oracle': .99*(1-.5**8),
           'bounds': lineage_bounds(fan_proofs, fan_probs), 'exact': exact_lineage(fan_proofs, fan_probs)}
    recovered = fan['bounds']['lower'] < .95 <= fan['exact']['lower'] and fan['oracle'] >= .95
    over_probs = {'shared': .99, **{f'p{i}': .5 for i in range(16)}}
    over_proofs = [['shared',f'p{i}'] for i in range(16)]
    over = exact_lineage(over_proofs, over_probs)
    limited = exact_lineage(fan_proofs, fan_probs, state_cap=1)
    disjoint_probs = {f'd{i}': .5 for i in range(40)}
    disjoint_proofs = [[f'd{i}',f'd{i+1}'] for i in range(0,40,2)]
    disjoint = exact_lineage(disjoint_proofs, disjoint_probs)
    control = {'true_probability': .8, 'correct_shared_lineage': exact_lineage([['a'],['a']], {'a': .8}),
               'incorrect_independence_input': exact_lineage([['a1'],['a2']], {'a1':.8,'a2':.8}),
               'note': 'Renaming one shared source as two independent primitives falsely yields 0.96; lineage is a required supplied assumption.'}
    fallback_valid = not over['exact'] and over['lower'] <= .99*(1-.5**16) <= over['upper'] and not limited['exact'] and limited['lower'] <= fan['oracle'] <= limited['upper']
    return {'primary_target_met': not failures and not invariant_failures and not false_admissions and recovered and fallback_valid,
            'cases': len(fixtures), 'fixtures': fixtures, 'oracle_failures': int(failures),
            'invariance_checks': 128*4, 'invariance_failures': int(invariant_failures), 'false_admissions': int(false_admissions),
            'mean_baseline_width': sum(f['bounds']['upper']-f['bounds']['lower'] for f in fixtures)/len(fixtures),
            'mean_exact_width': sum(f['exact']['upper']-f['exact']['lower'] for f in fixtures)/len(fixtures),
            'fan': fan, 'recovered_admission': bool(recovered), 'over_cap': over, 'state_cap': limited,
            'disjoint_40_atoms': {'result': disjoint, 'oracle': 1-.75**20}, 'incorrect_lineage_control': control}


def independent_set_oracle(weights, edges):
    """Independent combinations enumeration over supplied conflicting pairs."""
    keys = sorted(weights)
    if len(keys) > 16:
        raise ValueError('Finite graph oracle cap exceeded')
    best = 0
    for count in range(len(keys)+1):
        for chosen in combinations(keys, count):
            members = set(chosen)
            if not any(a in members and b in members for a, b in edges):
                best = max(best, sum(weights[k] for k in chosen))
    return best


def is_consistent(result, edges):
    selected = set(result['selected'])
    return not any(a in selected and b in selected for a, b in edges)


def priority_greedy(weights, edges):
    neighbors = defaultdict(set)
    for a, b in edges:
        neighbors[a].add(b)
        neighbors[b].add(a)
    chosen = set()
    for key in sorted(weights, key=lambda k: (-weights[k], k)):
        if not neighbors[key].intersection(chosen):
            chosen.add(key)
    return {'selected': sorted(chosen), 'utility': sum(weights[k] for k in chosen)}


def cycle_fixture(n, wheel=False):
    weights = {f'v{i:03d}': 1 for i in range(n)}
    nodes = sorted(weights)
    rim = nodes[1:] if wheel else nodes
    edges = [(rim[i], rim[(i+1)%len(rim)]) for i in range(len(rim))]
    if wheel:
        weights[nodes[0]] = 5
        edges += [(nodes[0], k) for k in rim]
    return weights, edges, max(5,len(rim)//2) if wheel else n//2


def graph_benchmark():
    rng = random.Random(SEED)
    fixtures, failures, permutations = [], 0, 0
    for case in range(128):
        n = rng.randrange(5,11)
        weights = {f'n{i:02d}': rng.randrange(10) for i in range(n)}
        edges = [(a,b) for a,b in combinations(weights,2) if rng.random() < .3]
        oracle = independent_set_oracle(weights, edges)
        result = solve_graph(weights, edges)
        old = solve_graph(weights, edges, max_cut=0)
        failures += result['utility'] != oracle or not is_consistent(result, edges) or result['utility'] < old['utility'] or bool(result['staged'])
        for shift in range(1,5):
            keys = list(weights)[shift:]+list(weights)[:shift]
            permutations += solve_graph({k:weights[k] for k in keys}, list(reversed(edges))) != result
        fixtures.append({'case': case, 'weights': weights, 'edges': edges, 'oracle': oracle,
                         'proposed': result, 'previous_policy': old, 'greedy': priority_greedy(weights, edges)})
    large = []
    for kind in ('cycle','wheel'):
        for n in (17,32,64,128,256):
            weights, edges, oracle = cycle_fixture(n, kind == 'wheel')
            result = solve_graph(weights, edges)
            old = solve_graph(weights, edges, max_cut=0)
            large.append({'kind': kind, 'n': n, 'oracle': oracle, 'proposed': result,
                          'previous_policy': old, 'greedy': priority_greedy(weights, edges),
                          'consistent': is_consistent(result, edges)})
    large_failures = sum(r['proposed']['utility'] != r['oracle'] or bool(r['proposed']['staged']) or not r['consistent'] for r in large)
    dense = solve_graph({str(i):1 for i in range(17)}, list(combinations([str(i) for i in range(17)],2)))
    misleading = solve_graph({'false':9,'true':8}, [('false','true')])
    return {'primary_target_met': not failures and not permutations and not large_failures and len(dense['staged']) == 17,
            'cases':128, 'fixtures':fixtures,'oracle_failures':int(failures), 'permutation_checks':512,
            'permutation_failures':int(permutations), 'large':large,'large_failures':int(large_failures),
            'dense_control':dense, 'misleading_priority_control': {'result': misleading, 'semantic_truth':['true']},
            'baseline_note':'Faithful forest/<=16-enumeration staging policy reimplementation, not an external solver.'}


def digest_state(weights, edges):
    return hashlib.sha256(json.dumps({'weights':weights,'edges':sorted(sorted(e) for e in edges)},sort_keys=True).encode()).hexdigest()


def incremental_benchmark():
    rng = random.Random(SEED)
    fixtures, failures = [], 0
    for case in range(64):
        weights = {f'n{i:02d}': rng.randrange(1,10) for i in range(16)}
        edges = {tuple(sorted((f'n{i:02d}',f'n{i+1:02d}'))) for i in range(15) if i != 7}
        initial = {'weights':dict(weights), 'edges':sorted(edges)}
        engine = IncrementalSolver(weights, edges)
        events = []
        for step in range(10):
            keys = sorted(weights)
            action = step % 5
            if action == 0:
                key = rng.choice(keys)
                weights[key] += 1
                mutation = {'kind':'weight','id':key,'weight':weights[key]}
            elif action == 1:
                a,b = next((a,b) for a,b in combinations(keys,2) if (a,b) not in edges)
                edges.add((a,b))
                mutation = {'kind':'insert_edge','edge':[a,b]}
            elif action == 2:
                edge = rng.choice(sorted(edges))
                edges.remove(edge)
                mutation = {'kind':'delete_edge','edge':list(edge)}
            elif action == 3:
                key = f'new{step}'
                weights[key] = rng.randrange(1,10)
                edge = tuple(sorted((key,rng.choice(keys))))
                edges.add(edge)
                mutation = {'kind':'insert_vertex','id':key,'weight':weights[key],'edge':list(edge)}
            else:
                key = rng.choice(keys)
                del weights[key]
                edges = {e for e in edges if key not in e}
                mutation = {'kind':'delete_vertex','id':key}
            actual = engine.update(weights, edges)
            full = solve_graph(weights, edges)
            reference = {k:full[k] for k in ('selected','staged','utility')}
            failures += actual != reference
            events.append({'step':step, 'mutation':mutation, 'state_sha256':digest_state(weights,edges),
                           'incremental':actual,'full':reference,'solver_vertices':engine.solver_vertices,'full_vertices':len(weights)})
        fixtures.append({'case':case,'initial':initial,'events':events})
    # Deliberate bridge merge, split and vertex deletion, separate from random cases.
    w = {str(i):1 for i in range(6)}
    e = [('0','1'),('1','2'),('3','4'),('4','5')]
    engine = IncrementalSolver(w,e)
    bridge = []
    for action in ('merge','split','delete'):
        if action == 'merge': e.append(('2','3'))
        elif action == 'split': e.remove(('2','3'))
        else:
            del w['1']
            e = [pair for pair in e if '1' not in pair]
        got, full = engine.update(w,e), solve_graph(w,e)
        expected = {k:full[k] for k in ('selected','staged','utility')}
        failures += got != expected
        bridge.append({'action':action,'incremental':got,'full':expected,'solver_vertices':engine.solver_vertices})
    w = {f'c{c:02d}n{i}':1 for c in range(64) for i in range(8)}
    e = [(f'c{c:02d}n{i}',f'c{c:02d}n{i+1}') for c in range(64) for i in range(7)]
    engine = IncrementalSolver(w,e)
    local_visits = full_visits = len(w)
    for step in range(128):
        w[f'c{step%64:02d}n{step%8}'] += 1
        got = engine.update(w,e)
        full = solve_graph(w,e)
        failures += got != {k:full[k] for k in ('selected','staged','utility')}
        local_visits += engine.solver_vertices
        full_visits += len(w)
    w = {f's{i:02d}':1 for i in range(64)}
    e = [(f's{i:02d}',f's{i+1:02d}') for i in range(63)]
    engine = IncrementalSolver(w,e)
    stress_local = stress_full = len(w)
    for step in range(16):
        w[f's{step:02d}'] += 1
        got, full = engine.update(w,e), solve_graph(w,e)
        failures += got != {k:full[k] for k in ('selected','staged','utility')}
        stress_local += engine.solver_vertices
        stress_full += len(w)
    saving = 1-local_visits/full_visits
    return {'primary_target_met': not failures and saving >= .75, 'mutation_cases':640,
            'fixtures':fixtures,'mismatches':int(failures), 'bridge_controls':bridge,
            'local_workload':{'components':64,'vertices_per_component':8,'updates':128,'includes_cold_build':True,
                              'incremental_solver_vertices':local_visits,'full_solver_vertices':full_visits,'saving':saving},
            'connected_control':{'vertices':64,'updates':16,'incremental_solver_vertices':stress_local,'full_solver_vertices':stress_full,
                                 'saving':1-stress_local/stress_full},
            'work_boundary':'All snapshots are validated and components discovered globally; only solver-submitted vertices are counted. No wall-clock speedup is inferred.'}


def execute():
    from ..adaptive.run import load, INPUT
    values, calls, audit = load()
    ids = [r['id'] for r in values]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate source candidate ID')
    development = [r for r in values if r['split'] == 'development']
    test = [r for r in values if r['split'] == 'test']
    if {r['group'] for r in development}.intersection(r['group'] for r in test):
        raise ValueError('Source group leakage')
    if (len(development),len(test)) != (73,263):
        raise ValueError('Frozen input split changed')
    return {'schema_version':1,'baseline_commit':BASELINE_COMMIT,'protocol_commit':PROTOCOL_COMMIT,
            'protocol_sha256':sha(HERE/'PROTOCOL.md'),'fresh_service_calls':0,
            'evidence':'H1 saved-response risk scoring; H2 simulated review; H3-H5 controlled algorithms. No independent semantic generalization.',
            'source_hashes':{(INPUT/name).relative_to(ROOT).as_posix():sha(INPUT/name) for name in ('plan.json','calls.jsonl','predictions.json','results.json')},
            'input_verification':audit, 'development':{'n':len(development),'groups':len({r['group'] for r in development})},
            'test':{'n':len(test),'groups':len({r['group'] for r in test})},
            'bootstrap':{'draws':DRAWS,'seed':SEED,'note':'Paired source-group percentile intervals; fixed fits/selections; exploratory and non-simultaneous.'},
            'H1':calibration(development,test),'H2':review(development,test),'H3':lineage_benchmark(),
            'H4':graph_benchmark(),'H5':incremental_benchmark()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args = parser.parse_args()
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('Network forbidden in reliability replay')), patch.object(socket,'create_connection',side_effect=RuntimeError('Network forbidden in reliability replay')):
        result = execute()
    if args.check:
        from ..verify import compare_json
        compare_json(json.loads((HERE/'results.json').read_text(encoding='utf-8')),result)
    else:
        write(HERE/'results.json',result)
    print(json.dumps({'status':'reproduced' if args.check else 'executed',
                      'targets':{k:result[k]['primary_target_met'] for k in ('H1','H2','H3','H4','H5')},'fresh_service_calls':0}))


if __name__ == '__main__':
    main()
