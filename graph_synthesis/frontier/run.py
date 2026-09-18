"""Execute frozen frontier tests offline; retain unfavorable target outcomes."""
from __future__ import annotations
import argparse
from collections import defaultdict
from itertools import combinations, product
import hashlib
import json
import math
from pathlib import Path
import random
import socket
from unittest.mock import patch

from .methods import (source_mixture, compile_lineage, optimal_review, ratio_review,
                      packed_review, review_gain, solve_frontier, verify_certificate,
                      PathOptimizer)
from ..reliability.methods import (POSITIVE, fit_small, assign_small, exact_lineage,
                                  solve_graph, graph_input)
from ..reliability.run import probability_oracle

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SEED = 20260922
BASELINE = 'a62a3257645d8e35cd4e45be53bfa9511d27724b'
PROTOCOL = 'ef8fc308d0a50cd37a6cdd3b7546e050093349c8'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')


def joint_oracle(proofs, sources, primitives):
    """Enumerate complete joint worlds, independent of conditional DNF evaluation."""
    ss, aa = sorted(sources), sorted(primitives)
    total = 0.
    for bits in product((False, True), repeat=len(ss)+len(aa)):
        state = dict(zip(ss, bits[:len(ss)]))
        truth = dict(zip(aa, bits[len(ss):]))
        if not any(all(truth[a] for a in p) for p in proofs):
            continue
        mass = math.prod(sources[s] if state[s] else 1-sources[s] for s in ss)
        for a in aa:
            row = primitives[a]
            p = row['p1'] if state[row['source']] else row['p0']
            mass *= p if truth[a] else 1-p
        total += mass
    return total


def independent_marginals(sources, primitives):
    return {a: (1-sources[r['source']])*r['p0']+sources[r['source']]*r['p1'] for a, r in primitives.items()}


def source_benchmark():
    rng = random.Random(SEED)
    fixtures, failures, invariant, false_admissions, prior_false = [], 0, 0, 0, 0
    for case in range(96):
        atoms = [f'a{i}' for i in range(rng.randrange(2,9))]
        sources = {f's{i}': rng.choice([.2,.5,.8,.95]) for i in range(rng.randrange(1,4))}
        primitives = {a: {'source': rng.choice(sorted(sources)), 'p0': rng.choice([0.,.1,.3]),
                          'p1': rng.choice([.6,.9,1.])} for a in atoms}
        proofs = [sorted(rng.sample(atoms, rng.randrange(1,min(4,len(atoms))+1))) for _ in range(rng.randrange(1,11))]
        oracle = joint_oracle(proofs, sources, primitives)
        got = source_mixture(proofs, sources, primitives)
        prior = exact_lineage(proofs, independent_marginals(sources, primitives))
        failures += not got['exact'] or abs(got['lower']-oracle) > 1e-12
        false_admissions += got['lower'] >= .95 and oracle < .95-1e-12
        prior_false += prior['lower'] >= .95 and oracle < .95-1e-12
        for copies in (1,2,5):
            permuted = source_mixture(list(reversed(proofs))*copies, sources, primitives)
            invariant += permuted != got
        fixtures.append({'case': case, 'sources': sources, 'primitives': primitives, 'proofs': proofs,
                         'oracle': oracle, 'proposed': got, 'independent_marginals': prior})
    sources = {'shared': .8}
    atoms = {a: {'source': 'shared', 'p0': 0., 'p1': 1.} for a in ('a','b')}
    controls = []
    for name, proofs in [('OR', [['a'],['b']]), ('AND', [['a','b']])]:
        controls.append({'query': name, 'oracle': .8, 'proposed': source_mixture(proofs,sources,atoms),
                         'independent_marginals': exact_lineage(proofs,{'a':.8,'b':.8})})
    missed = source_mixture([['a'],['b']], {'s1':.8,'s2':.8},
                           {'a':{'source':'s1','p0':0.,'p1':1.}, 'b':{'source':'s2','p0':0.,'p1':1.}})
    prevented = controls[0]['independent_marginals']['lower'] >= .95 and controls[0]['proposed']['upper'] < .95
    return {'primary_target_met': not failures and not invariant and not false_admissions and prevented,
            'fixtures': fixtures, 'oracle_failures': int(failures), 'invariance_failures': int(invariant),
            'invariance_checks': 288, 'false_admissions': int(false_admissions),
            'prior_false_admissions_random': int(prior_false), 'paired_controls': controls,
            'mean_absolute_error_prior': sum(abs(f['independent_marginals']['lower']-f['oracle']) for f in fixtures)/96,
            'mean_absolute_error_proposed': sum(abs(f['proposed']['lower']-f['oracle']) for f in fixtures)/96,
            'misspecified_source_control': {'supplied_result':missed, 'actual_probability':.8,
                                            'note':'Two declared latent sources actually share one unmodeled cause; the new method still gives 0.96.'}}


def make_review_candidates(test, fitted, s0, f):
    # Explicitly strip gold, all compact views, and evaluation outcomes.
    features = [{'id':r['id'], 'group':r['group'], 'views':{'base1':r['views']['base1']}} for r in test]
    assigned = assign_small(features, fitted)
    costs = {r['id']: min(8,1+int(r['arms']['single']['input_tokens'])//1000) for r in test}
    return [{**r,'cost':costs[r['id']], 'detect':s0/(1+.05*(costs[r['id']]-1)), 'false_remove':f} for r in assigned]


def review_outcome(test, candidates, selected):
    # Gold is used here only, AFTER fixed review IDs have been selected.
    lookup = {r['id']:r for r in candidates}
    grouped = defaultdict(list)
    for r in test:
        grouped[r['group']].append(r)
    outcomes = []
    for g, rows in sorted(grouped.items()):
        wrong = [r for r in rows if r['views']['base1']['label'] in POSITIVE and r['views']['base1']['label'] != r['gold']]
        correct = [r for r in rows if r['views']['base1']['label'] in POSITIVE and r['views']['base1']['label'] == r['gold']]
        clean = math.prod(lookup[r['id']]['detect'] if r['id'] in selected else 0. for r in wrong)
        loss = sum(lookup[r['id']]['false_remove'] for r in correct if r['id'] in selected)
        outcomes.append({'group':g, 'contaminated':1-clean, 'correct_removed':loss,
                         'wrong_remaining':sum(1-lookup[r['id']]['detect']*(r['id'] in selected) for r in wrong),
                         'correct_retained':len(correct)-loss})
    return {'expected_contaminated_groups':sum(r['contaminated'] for r in outcomes),
            'expected_correct_removed':sum(r['correct_removed'] for r in outcomes),
            'expected_wrong_remaining':sum(r['wrong_remaining'] for r in outcomes),
            'expected_correct_retained':sum(r['correct_retained'] for r in outcomes),
            'groups':outcomes}


def paired_interval(a, b):
    import numpy as np
    x = np.array([r['contaminated'] for r in a['groups']])-np.array([r['contaminated'] for r in b['groups']])
    rng = np.random.default_rng(SEED)
    draws = x[rng.integers(0,len(x),size=(4000,len(x)))].mean(axis=1)
    return {'point_rate_difference':float(x.mean()), '95':[float(v) for v in np.quantile(draws,[.025,.975])],
            '99':[float(v) for v in np.quantile(draws,[.005,.995])], 'groups':len(x), 'draws':4000}


def review_oracle(candidates, budget):
    best = 0.
    for mask in range(1 << len(candidates)):
        chosen = [r for i,r in enumerate(candidates) if mask & (1 << i)]
        if sum(r['cost'] for r in chosen) > budget:
            continue
        selected = {r['id'] for r in chosen}
        # Independent direct expected-contamination calculation, not DP options.
        groups = defaultdict(list)
        for row in candidates:
            groups[row['group']].append(row)
        gain = 0.
        for rows in groups.values():
            q0 = 1-math.prod(1-r['risk'] for r in rows)
            q1 = 1-math.prod(1-r['risk']*(1-r['detect'] if r['id'] in selected else 1) for r in rows)
            gain += q0-q1
        gain -= sum((1-r['risk'])*r['false_remove'] for r in chosen)
        best = max(best,gain)
    return best


def review_benchmark(development, test):
    from ..adaptive.methods import review_order
    fitted = fit_small(development)
    scenarios = []
    primary = None
    for s0 in (.5,.75,1.):
        for false in (0.,.01,.05):
            candidates = make_review_candidates(test,fitted,s0,false)
            order = review_order([{'id':r['id'],'group':r['group'],'risk':r['risk']} for r in candidates], group_aware=True)
            for budget in (20,40,80,160):
                plans = {'packed_prior':packed_review(candidates,budget,order), 'ratio_greedy':ratio_review(candidates,budget),
                         'optimal':optimal_review(candidates,budget), 'no_review':{'selected':[],'cost':0,'modeled_gain':0.}}
                policies = {name:{**plan,'outcome':review_outcome(test,candidates,set(plan['selected']))} for name,plan in plans.items()}
                item = {'s0':s0,'false_remove':false,'budget':budget,'policies':policies}
                scenarios.append(item)
                if s0 == .75 and false == .01 and budget == 40:
                    primary = item
    p = primary['policies']; target = True
    for baseline in ('packed_prior','ratio_greedy'):
        target &= p['optimal']['outcome']['expected_contaminated_groups'] <= .95*p[baseline]['outcome']['expected_contaminated_groups']
        target &= p['optimal']['outcome']['expected_correct_removed'] <= p[baseline]['outcome']['expected_correct_removed']+.25
    rng = random.Random(SEED)
    fixtures, failures = [], 0
    for case in range(64):
        candidates = [{'id':str(i),'group':str(rng.randrange(3)),'risk':rng.choice([.05,.2,.5,.8]),
                       'cost':rng.randrange(1,5),'detect':rng.choice([.5,.75,1.]),'false_remove':rng.choice([0.,.01,.05])}
                      for i in range(rng.randrange(2,9))]
        budget = rng.randrange(1,15)
        got, oracle = optimal_review(candidates,budget), review_oracle(candidates,budget)
        failures += abs(got['modeled_gain']-oracle) > 1e-10
        fixtures.append({'case':case,'candidates':candidates,'budget':budget,'proposed':got,'oracle_gain':oracle})
    misleading = [{'id':'actually_correct','group':'g1','risk':.9,'cost':1,'detect':1.,'false_remove':.05},
                  {'id':'actually_wrong','group':'g2','risk':.01,'cost':1,'detect':1.,'false_remove':.05}]
    return {'primary_target_met':bool(target and not failures),'fit':fitted,'primary':primary,'scenarios':scenarios,
            'paired':{k:paired_interval(p['optimal']['outcome'],p[k]['outcome']) for k in ('packed_prior','ratio_greedy')},
            'primary_features':make_review_candidates(test,fitted,.75,.01),'oracle_fixtures':fixtures,'oracle_failures':int(failures),
            'wrong_risk_control':{'features':misleading,'plan':optimal_review(misleading,1),
                                  'actually_correct':['actually_correct'],'actually_wrong':['actually_wrong']},
            'assumptions':'Proxy effort; supplied cost-dependent detection and false-removal probabilities; independent reviewer detections. No observed human review.'}


def chain_oracle(probabilities):
    no_previous, previous = 1., 0.
    for p in probabilities:
        no_previous, previous = (no_previous+previous)*(1-p), no_previous*p
    return 1-no_previous-previous


def diagram_benchmark():
    rng = random.Random(SEED)
    fixtures, failures, invariance = [], 0, 0
    for case in range(128):
        atoms = [f'a{i}' for i in range(rng.randrange(2,11))]
        proofs = [sorted(rng.sample(atoms,rng.randrange(1,min(4,len(atoms))+1))) for _ in range(rng.randrange(1,11))]
        diagram = compile_lineage(proofs)
        assignments = []
        for repeat in range(5):
            probs = {a:rng.choice([0.,.2,.5,.8,.95,1.]) for a in diagram.atoms}
            got = diagram.evaluate(probs); truth = probability_oracle(proofs,probs)
            failures += not got['exact'] or abs(got['lower']-truth) > 1e-12
            assignments.append({'probabilities':probs,'oracle':truth,'proposed':got})
        invariance += compile_lineage(list(reversed(proofs))*2) != diagram
        fixtures.append({'case':case,'proofs':proofs,'states':diagram.states,'nodes':len(diagram.nodes),'assignments':assignments})
    large = []
    for kind in ('fan','chain'):
        for n in (17,32,64,128,256):
            atoms = [f'a{i:03d}' for i in range(n)]
            if kind == 'fan':
                probs = {a:(.99 if i == 0 else .5) for i,a in enumerate(atoms)}
                proofs = [[atoms[0],a] for a in atoms[1:]]
                oracle = .99*(1-.5**(n-1))
            else:
                probs = {a:.5 for a in atoms}
                proofs = [[a,b] for a,b in zip(atoms,atoms[1:])]
                oracle = chain_oracle(list(probs.values()))
            diagram = compile_lineage(proofs)
            got = diagram.evaluate(probs); prior = exact_lineage(proofs,probs)
            failures += not got['exact'] or abs(got['lower']-oracle) > 1e-12 or prior['exact']
            large.append({'kind':kind,'n':n,'nodes':len(diagram.nodes),'states':diagram.states,'oracle':oracle,'proposed':got,'prior':prior})
    atoms = [f'a{i:03d}' for i in range(128)]
    proofs = [[a,b] for a,b in zip(atoms,atoms[1:])]
    diagram = compile_lineage(proofs)
    probs = {a:.5 for a in atoms}
    updates = []
    for step in range(64):
        atom = rng.choice(atoms); probs[atom] = rng.choice([.1,.3,.7,.9])
        got = diagram.evaluate(probs); oracle = chain_oracle([probs[a] for a in atoms])
        failures += not got['exact'] or abs(got['lower']-oracle) > 1e-12
        updates.append({'atom':atom,'probability':probs[atom],'oracle':oracle,'proposed':got})
    capped = compile_lineage([['a','b'],['b','c']],state_cap=1).evaluate({'a':.5,'b':.5,'c':.5})
    cap_truth = probability_oracle([['a','b'],['b','c']],{'a':.5,'b':.5,'c':.5})
    failures += capped['exact'] or not capped['lower'] <= cap_truth <= capped['upper']
    return {'primary_target_met':not failures and not invariance, 'oracle_failures':int(failures),'invariance_failures':int(invariance),
            'fixtures':fixtures,'large':large,'reuse':{'compilations':1,'states':diagram.states,'nodes':len(diagram.nodes),'updates':updates,
                                                     'evaluation_node_visits':sum(x['proposed']['node_visits'] for x in updates)},
            'state_cap_control':{'proposed':capped,'oracle':cap_truth}}


def independent_set_oracle(weights,edges):
    keys = sorted(weights); best = 0
    for mask in range(1 << len(keys)):
        chosen = {k for i,k in enumerate(keys) if mask & (1 << i)}
        if any(a in chosen and b in chosen for a,b in edges):
            continue
        best = max(best,sum(weights[k] for k in chosen))
    return best


def greedy_graph(weights, edges):
    adj = graph_input(weights,edges); chosen = set()
    for k in sorted(weights,key=lambda k:(-weights[k],k)):
        if not adj[k].intersection(chosen):
            chosen.add(k)
    return {'selected':sorted(chosen),'utility':sum(weights[k] for k in chosen)}


def graph_case(weights, edges):
    got = solve_frontier(weights,edges); prior = solve_graph(weights,edges)
    certificate_errors = 0
    for component in got['components']:
        if component['method'] == 'bipartite_min_cut':
            keys = set(component['certificate']['keys'])
            w = {k:weights[k] for k in keys}; e = [(a,b) for a,b in edges if a in keys and b in keys]
            certificate_errors += not verify_certificate(w,e,component)
    return {'weights':weights,'edges':edges,'proposed':got,'prior':prior,'greedy':greedy_graph(weights,edges),
            'certificate_errors':int(certificate_errors)}


def graph_benchmark():
    rng = random.Random(SEED)
    small, failures, certificate_errors, regression = [], 0, 0, 0
    for case in range(192):
        n = rng.randrange(2,13); keys = [f'v{i:02d}' for i in range(n)]
        weights = {k:rng.randrange(11) for k in keys}
        edges = [(a,b) for i,a in enumerate(keys) for j,b in enumerate(keys) if i < j and rng.random() < .35 and (case >= 128 or (i < n//2 <= j))]
        item = graph_case(weights,edges); oracle = independent_set_oracle(weights,edges)
        item.update({'case':case,'kind':'bipartite' if case < 128 else 'general','oracle':oracle})
        failures += item['proposed']['utility'] != oracle
        certificate_errors += item['certificate_errors']; regression += item['proposed']['utility'] < item['prior']['utility']
        small.append(item)
    large = []
    for n in (18,32,64,128,256):
        left,right = [f'l{i:03d}' for i in range(n//2)],[f'r{i:03d}' for i in range(n//2)]
        w = {k:(1 if k[0]=='l' else 2) for k in left+right}; e = [(a,b) for a in left for b in right]
        item = graph_case(w,e); oracle = n
        item.update({'kind':'complete_bipartite','n':n,'oracle':oracle})
        failures += item['proposed']['utility'] != oracle or bool(item['proposed']['staged'])
        certificate_errors += item['certificate_errors']; large.append(item)
    for rows,cols in ((4,8),(8,8),(8,16),(16,16)):
        key = lambda i,j:f'g{i:02d}_{j:02d}'
        w = {key(i,j):1 for i in range(rows) for j in range(cols)}
        e = [(key(i,j),key(a,b)) for i in range(rows) for j in range(cols) for a,b in ((i+1,j),(i,j+1)) if a < rows and b < cols]
        item = graph_case(w,e); oracle = rows*cols//2
        item.update({'kind':'grid','n':rows*cols,'rows':rows,'cols':cols,'oracle':oracle})
        failures += item['proposed']['utility'] != oracle or bool(item['proposed']['staged'])
        certificate_errors += item['certificate_errors']; large.append(item)
    false_control = solve_frontier({'false':9,'true':8},[('false','true')])
    clique_w = {str(i):1 for i in range(17)}
    clique = solve_frontier(clique_w,list(combinations(clique_w,2)))
    return {'primary_target_met':not failures and not certificate_errors and not regression,
            'oracle_failures':int(failures),'certificate_errors':int(certificate_errors),'prior_regressions':int(regression),
            'small':small,'large':large,'false_priority_control':false_control,'odd_clique_control':clique}


def linear_path_oracle(weights, order):
    skip, take = 0, -math.inf
    for key in order:
        skip,take = max(skip,take),skip+weights[key]
    return max(skip,take)


def path_case(n, count, rng):
    keys = [f'v{i:04d}' for i in range(n)]
    weights = {k:rng.randrange(21) for k in keys}; initial = dict(weights)
    edges = list(zip(keys,keys[1:]))
    engine = PathOptimizer(weights,edges)
    failures, witness_visits = 0, 0
    def check():
        nonlocal failures,witness_visits
        chosen = engine.selected(); witness_visits += engine.witness_visits
        oracle = linear_path_oracle(weights,keys)
        failures += engine.utility != oracle or sum(weights[k] for k in chosen) != oracle or any(a in chosen and b in chosen for a,b in edges)
        return {'oracle':oracle,'proposed_utility':engine.utility,'witness_sha256':hashlib.sha256('\n'.join(chosen).encode()).hexdigest(),
                'selected_count':len(chosen),'witness_visits':engine.witness_visits,'transition_candidates':engine.last_transitions}
    cold = check(); updates = []
    for step in range(count):
        key, weight = rng.choice(keys),rng.randrange(21)
        weights[key] = weight; engine.update(key,weight)
        updates.append({'vertex':key,'weight':weight,**check()})
    full = 3*n*(count+1)
    return {'n':n,'initial_weights':initial,'edges':edges,'cold':cold,'updates':updates,'mismatches':int(failures),
            'segment_transition_candidates':engine.transitions,'full_transition_candidates':full,
            'saving':1-engine.transitions/full,'validation_visits_cold':engine.validation_visits,
            'witness_visits_all_outputs':witness_visits}


def path_benchmark():
    rng = random.Random(SEED)
    small = [path_case(rng.randrange(1,65),16,rng) for _ in range(64)]
    large = path_case(1024,256,rng)
    failures = sum(c['mismatches'] for c in small)+large['mismatches']
    return {'primary_target_met':not failures and large['saving'] >= .90,'mismatches':failures,'small':small,'large':large,
            'boundary':'Fixed path, weight-only updates. Full witness decoding remains linear. Not total runtime, database I/O, or graph-emission speedup.'}


def execute():
    from ..adaptive.run import load, INPUT
    rows, calls, audit = load()
    development = [r for r in rows if r['split']=='development']; test = [r for r in rows if r['split']=='test']
    if (len(development),len(test)) != (73,263) or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Frozen input shape or unique IDs changed')
    devgroups, testgroups = {r['group'] for r in development},{r['group'] for r in test}
    if devgroups & testgroups:
        raise ValueError('Development/evaluation source leakage')
    result = {'schema_version':1,'baseline_commit':BASELINE,'protocol_commit':PROTOCOL,'protocol_sha256':sha(HERE/'PROTOCOL.md'),
              'seed':SEED,'fresh_service_calls':0,'development':{'n':len(development),'groups':len(devgroups)},
              'evaluation':{'n':len(test),'groups':len(testgroups)},'input_audit':audit,
              'source_hashes':{(INPUT/n).relative_to(ROOT).as_posix():sha(INPUT/n) for n in ('plan.json','calls.jsonl','predictions.json','results.json')},
              'code_hashes':{p.relative_to(ROOT).as_posix():sha(p) for p in (HERE/'methods.py',HERE/'run.py',HERE.parent/'reliability/methods.py',HERE.parent/'adaptive/run.py')},
              'evidence':'H2 saved-response replay plus assumed noisy review; H1/H3/H4/H5 controlled algorithms. No independent semantic-accuracy evidence.'}
    for key,fn in [('H1',source_benchmark),('H2',lambda:review_benchmark(development,test)),('H3',diagram_benchmark),('H4',graph_benchmark),('H5',path_benchmark)]:
        result[key] = fn()
        print(key, 'target',result[key]['primary_target_met'],flush=True)
    return json.loads(json.dumps(result,sort_keys=True,allow_nan=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--check',action='store_true'); args = parser.parse_args()
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('Network forbidden')), patch.object(socket,'create_connection',side_effect=RuntimeError('Network forbidden')):
        result = execute()
    if args.check:
        from ..verify import compare_json
        compare_json(json.loads((HERE/'results.json').read_text(encoding='utf-8')),result)
    else:
        write(HERE/'results.json',result)
    print(json.dumps({'status':'reproduced' if args.check else 'executed','targets':{k:result[k]['primary_target_met'] for k in ('H1','H2','H3','H4','H5')},'fresh_service_calls':0}))


if __name__ == '__main__':
    main()
