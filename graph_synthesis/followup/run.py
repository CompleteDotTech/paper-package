"""Execute five offline, falsifiable follow-up benchmarks and write evidence.

Run from the repository root: python -B -m graph_synthesis.followup.run [--check]
Fitting never consumes rerun evaluation labels. This is exploratory reuse of
already inspected data, not fresh inference or independent confirmation.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
import hashlib
from itertools import product
import json
import math
from pathlib import Path
import random

from graph_synthesis.core import digest
from graph_synthesis.recorded import BASELINES, LABELS, input_state, payload_for, parse_answer
from graph_synthesis.theory_suite.analyses import load as load_original, purge_groups
from graph_synthesis.theory_suite.methods import fit_cascade, macro_f1
from .methods import (POSITIVE, conflict, edges, exact_probability, features,
                      fit_edge_route, fit_guard, loss, losses, proof_bounds, route,
                      semantic_collision, stable_ids, supported, transform)

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SEED, BOOTSTRAPS = 20260918, 1000
FEW = 'fewshot_contract'
SOURCE_HASHES = {
 'reproduction/results/jev/run-20260918/plan.json':'7ed8622f2022b263f3d0b9cda413b4caafe50ebcf0589b05b886dbd615987040',
 'reproduction/results/jev/run-20260918/predictions.jsonl':'2a5778db45583a7fca3f7a385846fb712f395e6b2b2510d914377c5862e959f2',
 'reproduction/results/jev/run-20260918/calls.jsonl':'4833a5919647b483f67668357e36ba5df334acdee2a628a64c5d7d7ce412ad83',
 'experiments/jev-rerun-20260918/plan.json':'009a5591488a93c709a6033c3414a4103e5d431d16871369b2c374ebac6c6942',
 'experiments/jev-rerun-20260918/predictions.jsonl':'9fc0f0a345f6fbbd311759a5143c1d1be62313b72e26acd54e3ae289e040d76f',
 'experiments/jev-rerun-20260918/calls.jsonl':'0eb3121cb20bd643eb14241079d5368c246ef63e522573b10c845a8927ea91a8',
}


def load_data(root: Path = ROOT) -> tuple[dict, dict]:
    for path, expected in SOURCE_HASHES.items():
        if hashlib.sha256((root/path).read_bytes()).hexdigest() != expected:
            raise ValueError('Changed pinned input: '+path)
    backend, old, audit = load_original(root)
    folder = root/'experiments/jev-rerun-20260918'
    plan = json.loads((folder/'plan.json').read_text(encoding='utf-8'))
    records = [json.loads(l) for l in (folder/'predictions.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
    call_rows = [json.loads(l) for l in (folder/'calls.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
    calls = {r['call_id']: r for r in call_rows}
    if len(calls) != len(call_rows) or plan['model'] != backend.plan['model']:
        raise ValueError('Duplicate calls or model mismatch')
    selected = [r for r in records if r['split'] in ('calibration','evaluation')]
    index = {(r['task'],r['arm'],r['split'],r['id']):r for r in selected}
    if len(index) != len(selected):
        raise ValueError('Duplicate primary predictions')
    new = {}
    for task, arms in old.items():
        new[task] = {}
        for arm, splits in arms.items():
            new[task][arm] = {}
            for split, rows in splits.items():
                if plan['tasks'][task][split] != backend.plan['tasks'][task][split]:
                    raise ValueError('Old/rerun input or gold mismatch')
                inputs = {r['id']: r for r in plan['tasks'][task][split]}
                parsed = []
                for old_row in rows:
                    r = index[task, arm, split, old_row['id']]
                    if r['repeat'] != 0 or r['condition'] != 'batched' or r['execution_mode'] != 'real' or len(r['call_ids']) != 1:
                        raise ValueError('Ambiguous primary observation')
                    call = calls[r['call_ids'][0]]
                    payload = payload_for(plan, task, arm, input_state(task, inputs[r['id']]))
                    if call['payload'] != payload or call['execution_mode'] != 'real' or call['error'] != r['error']:
                        raise ValueError('Payload/error provenance mismatch')
                    if r['gold_label'] != old_row['gold']:
                        raise ValueError('Gold mismatch')
                    values = {} if r['error'] else parse_answer(call['response'], task, arm, plan['model'])
                    if values != r['distribution']:
                        raise ValueError('Raw response does not reconstruct')
                    tokens = call['tokens_used']['input']
                    if type(tokens) is not int or tokens < 0:
                        raise ValueError('Invalid usage')
                    label = max(LABELS[task], key=values.get) if values else 'ERROR'
                    parsed.append({**old_row, 'probabilities': values, 'label': label,
                                   'score': max(values.values()) if values else 0.,
                                   'error': bool(r['error']), 'input_tokens': tokens,
                                   'call_id': call['call_id']})
                new[task][arm][split] = parsed
    return {'original':old, 'rerun':new}, audit


def bootstrap_means(rows: list[dict], names: tuple[str,...]) -> dict:
    grouped = defaultdict(list)
    for r in rows:
        grouped[r['group']].append(r)
    keys = sorted(grouped)
    rng = random.Random(SEED)
    sums = {k:[sum(r[n] for r in grouped[k]) for n in names] for k in keys}
    values = {n:[] for n in names}
    for _ in range(BOOTSTRAPS):
        sample = [keys[rng.randrange(len(keys))] for _ in keys]
        count = sum(len(grouped[k]) for k in sample)
        for i,n in enumerate(names):
            values[n].append(sum(sums[k][i] for k in sample)/count)
    result = {}
    for n in names:
        v = sorted(values[n])
        result[n] = [v[int(.025*(len(v)-1))],v[int(.975*(len(v)-1))]]
    return result


def h1(data: dict) -> dict:
    results = {}
    for task in LABELS:
        results[task] = {}
        for arm in (BASELINES[task],FEW):
            fit = fit_guard(data['original'][task][arm]['calibration'], split='calibration')
            t,w = fit['temperature'],fit['weight']
            runs = {}
            for name, all_data in data.items():
                rows = all_data[task][arm]['evaluation']
                raw,temp,guard = losses(rows),losses(rows,t),losses(rows,t,w)
                differences = []
                flips = 0
                for r in rows:
                    if r['error']:
                        continue
                    p = transform(r['probabilities'],t,w)
                    flips += max(LABELS[task],key=p.get) != r['label']
                    a,b = loss(r['probabilities'],r['gold']),loss(p,r['gold'])
                    differences.append({'group':r['group'],'log_loss':b[0]-a[0],'brier':b[1]-a[1]})
                runs[name] = {'raw':raw,'temperature_only':temp,'guarded':guard,
                              'argmax_flips':flips,
                              'guarded_minus_raw_descriptive_95':bootstrap_means(differences,('log_loss','brier')),
                              'target_met':guard['log_loss'] < raw['log_loss']-1e-12 and guard['brier'] <= raw['brier']+1e-12 and flips == 0}
            results[task][arm] = {'fit':fit,'runs':runs}
    return {'tasks':results, 'primary_target_met':results['relation_support'][FEW]['runs']['rerun']['target_met']}


def h2(data: dict) -> dict:
    results = {}
    for task in LABELS:
        cal = data['original'][task]
        base,few = cal[BASELINES[task]]['calibration'],cal[FEW]['calibration']
        fit = fit_edge_route(base,few,split='calibration')
        macro = fit_cascade(features(base),features(few),[r['gold'] for r in base],LABELS[task],split='calibration')
        runs = {}
        for name,d in data.items():
            b,f = d[task][BASELINES[task]]['evaluation'],d[task][FEW]['evaluation']
            gold = [r['gold'] for r in b]
            policies = {'baseline':dict(positive_threshold=0,negative_threshold=0),
                        'fewshot':dict(positive_threshold=0,negative_threshold=0,direct=True),
                        'macro_cascade':dict(positive_threshold=macro['threshold'],negative_threshold=macro['threshold']),
                        'edge_cascade':fit['policy']}
            reports = {}
            policy_predictions = {}
            for policy,args in policies.items():
                if policy == 'baseline':
                    pred,tokens,count = [r['label'] for r in b],sum(r['input_tokens'] for r in b),0
                else:
                    pred,tokens,count = route(features(b),features(f),**args)
                policy_predictions[policy] = pred
                reports[policy] = {**edges(gold,pred),'macro_f1':macro_f1(gold,pred,LABELS[task]),
                                   'input_tokens':tokens,'escalations':count}
            a,c = reports['fewshot'],reports['edge_cascade']
            paired = []
            pf,pe = policy_predictions['fewshot'],policy_predictions['edge_cascade']
            for row,gold_label,x,y in zip(b,gold,pf,pe):
                paired.append({'group':row['group'],
                    'correct_edge_rate':int(y in POSITIVE and y==gold_label)-int(x in POSITIVE and x==gold_label),
                    'wrong_edge_rate':int(y in POSITIVE and y!=gold_label)-int(x in POSITIVE and x!=gold_label)})
            reports['paired_vs_fewshot'] = {
                'different_labels':sum(x!=y for x,y in zip(pf,pe)),
                'introduced_wrong_edges':sum(x not in POSITIVE or x==g for x,y,g in zip(pf,pe,gold) if y in POSITIVE and y!=g),
                'descriptive_95_rate_difference':bootstrap_means(paired,('correct_edge_rate','wrong_edge_rate'))}
            reports['input_token_saving'] = 1-c['input_tokens']/a['input_tokens']
            reports['correct_edge_retention'] = c['correct']/a['correct'] if a['correct'] else None
            reports['target_met'] = c['input_tokens'] <= .8*a['input_tokens'] and c['correct'] >= .98*a['correct'] and c['wrong'] <= a['wrong']
            runs[name] = reports
        results[task] = {'fit':fit,'macro_fit':macro,'runs':runs}
    return {'tasks':results,'primary_target_met':results['relation_support']['runs']['rerun']['target_met']}


def h3(data: dict) -> dict:
    results = {}
    for task in LABELS:
        results[task] = {}
        for arm in (BASELINES[task],FEW):
            old,new = data['original'][task][arm]['evaluation'],data['rerun'][task][arm]['evaluation']
            accepted = stable_ids(features(old),features(new))
            positive = [r for r in new if r['label'] in POSITIVE and not r['error']]
            ranked = sorted(positive,key=lambda r:(-r['score'],r['id']))[:len(accepted)]
            stable = [r for r in new if r['id'] in accepted]
            def metric(rows):
                keep = {r['id'] for r in rows}
                return edges([r['gold'] for r in new],
                             [r['label'] if r['id'] in keep or r['error'] else 'STAGE' for r in new])
            a,b,c = metric(positive),metric(stable),metric(ranked)
            expected = len(accepted)*a['wrong']/a['accepted'] if a['accepted'] else 0
            pairs = [(o,n) for o,n in zip(old,new) if not o['error'] and not n['error']]
            both_wrong = sum(o['label'] != o['gold'] and n['label'] != n['gold'] for o,n in pairs)
            same_wrong = sum(o['label'] == n['label'] != n['gold'] for o,n in pairs)
            results[task][arm] = {'rerun_all':a,'stable':b,'confidence_matched':c,
                'random_matched_expected_wrong':expected,'common_valid_pairs':len(pairs),
                'both_wrong':both_wrong,'same_wrong':same_wrong,
                'stable_wrong_score_one':sum(r['label'] != r['gold'] and r['score'] == 1 for r in stable),
                'accepted_ids_sha256':digest(sorted(accepted)),
                'correct_edge_retention':b['correct']/a['correct'] if a['correct'] else None,
                'two_run_input_tokens':sum(r['input_tokens'] for r in old+new),
                'one_run_input_tokens':sum(r['input_tokens'] for r in new),
                'primary_target_met':b['correct'] >= .95*a['correct'] and b['wrong'] < c['wrong'] and b['wrong'] < expected}
    return {'tasks':results,'primary_target_met':results['relation_support'][FEW]['primary_target_met']}


def h4() -> dict:
    intervals = [(a,b) for a in (None,-3,-1,0,1,3) for b in (None,0,2,4,6)
                 if a is None or b is None or a < b]
    counts = {k:{'missed_conflicts':0,'false_conflicts':0} for k in ('exact_qualifier','qualifier_blind','interval_scope')}
    cases = []
    for (s1,e1),(s2,e2),scope,kind in product(intervals,intervals,('same','other'),('polarity','functional','different_subject','benign')):
        a = dict(subject='S',predicate='P',object='O',scope='adult',polarity=1,start=s1,end=e1)
        b = dict(subject='S',predicate='P',object='O',scope='adult' if scope=='same' else 'child',polarity=-1,start=s2,end=e2)
        if kind == 'functional':
            b.update(object='O2',polarity=1)
        if kind == 'different_subject':
            b['subject']='S2'
        if kind == 'benign':
            b['polarity']=1
        functional = frozenset({'P'}) if kind == 'functional' else frozenset()
        # Independent oracle: explicit truth conditions and integer instants;
        # bounds lie in [-3,6], so [-10,10] also witnesses unbounded intersections.
        logically_opposed = ((a['subject']==b['subject'] and a['predicate']==b['predicate']) and
                             ((a['object']==b['object'] and a['polarity'] != b['polarity']) or
                              (kind=='functional' and a['object']!=b['object'] and a['polarity']==b['polarity']==1)))
        simultaneous = any((s1 is None or s1<=t) and (e1 is None or t<e1) and
                           (s2 is None or s2<=t) and (e2 is None or t<e2) for t in range(-10,11))
        truth = logically_opposed and a['scope']==b['scope'] and simultaneous
        outcomes = {'exact_qualifier':semantic_collision(a,b,functional) and (a['scope'],s1,e1)==(b['scope'],s2,e2),
                    'qualifier_blind':semantic_collision(a,b,functional),
                    'interval_scope':conflict(a,b,functional)=='conflict'}
        for name,value in outcomes.items():
            counts[name]['missed_conflicts'] += bool(truth and not value)
            counts[name]['false_conflicts'] += bool(value and not truth)
        cases.append({'kind':kind,'scope':scope,'a':[s1,e1],'b':[s2,e2],'gold_conflict':truth})
    example = dict(subject='S',predicate='P',object='O',scope='adult',polarity=1,start=0,end=2)
    malformed = [{**example,'scope':None},{**example,'start':'yesterday'}, {**example,'end':0},
                 {**example,'polarity':True}, {k:v for k,v in example.items() if k!='start'}]
    staged = sum(conflict(r,example)=='unknown' for r in malformed)
    return {'supported_cases':len(cases),'true_conflicts':sum(c['gold_conflict'] for c in cases),
            'strategies':counts,'unknown_cases':len(malformed),'unknown_staged':staged,
            'case_sha256':digest(cases),
            'primary_target_met':not any(counts['interval_scope'].values()) and staged==len(malformed),
            'limitation':'Finite controlled qualifier validation; no text extraction or Jev classification tested.'}


def h5() -> dict:
    templates = ((('a',),), (('a',),('b',)), (('a','b'),('a','c')),
                 (('a',),('a','b')), (('a','b'),('b','c'),('a','c')),
                 (('a','b'),('c',)))
    counts = {k:{'false_high_admissions':0,'correct_high_admissions':0} for k in ('naive_or','dedup_or','lineage_lower')}
    rows,failures,noninvariant = [],0,0
    for pa,pb,pc,proofs in product((.2,.5,.8,.95),(.2,.5,.8,.95),(.2,.5,.8,.95),templates):
        probabilities = dict(a=pa,b=pb,c=pc)
        exact = exact_probability(proofs,probabilities)
        base = proof_bounds(proofs,probabilities)
        for copies in (1,2,5,20):
            repeated = list(proofs)*copies
            bounds = proof_bounds(repeated,probabilities)
            failures += not bounds['lower']-1e-12 <= exact <= bounds['upper']+1e-12
            noninvariant += bounds != base
            naive = 1-math.prod(1-math.prod(probabilities[a] for a in p) for p in repeated)
            dedup = 1-math.prod(1-math.prod(probabilities[a] for a in p) for p in sorted(set(proofs)))
            for name,value in [('naive_or',naive),('dedup_or',dedup),('lineage_lower',bounds['lower'])]:
                if value >= .95-1e-12:
                    counts[name]['correct_high_admissions' if exact>=.95-1e-12 else 'false_high_admissions'] += 1
            rows.append({'copies':copies,'exact':exact,'naive':naive,'dedup':dedup,**bounds})
    # Negative control: a and b falsely declared independent aliases for the same
    # Bernoulli(.8) event. No algorithm using only that metadata can recover truth.
    corrupt = proof_bounds([['a'],['b']],{'a':.8,'b':.8})
    return {'cases':len(rows),'parameter_settings':len(rows)//4,
            'bound_violations':failures,'duplicate_invariance_failures':noninvariant,
            'strategies':counts,'mean_interval_width':sum(r['upper']-r['lower'] for r in rows)/len(rows),
            'max_interval_width':max(r['upper']-r['lower'] for r in rows),
            'known_high_probability_cases':sum(r['exact']>=.95-1e-12 for r in rows),
            'duplication_grid':[{'copies':n,'naive_mean':sum(r['naive'] for r in rows if r['copies']==n)/(len(rows)//4),
                                 'exact_mean':sum(r['exact'] for r in rows if r['copies']==n)/(len(rows)//4),
                                 'lower_mean':sum(r['lower'] for r in rows if r['copies']==n)/(len(rows)//4)} for n in (1,2,5,20)],
            'negative_control':{'supplied_lower':corrupt['lower'],'actual_probability':.8,'false_admission':corrupt['lower']>=.95},
            'case_sha256':digest(clean(rows)),
            'primary_target_met':failures==noninvariant==counts['lineage_lower']['false_high_admissions']==0 and counts['naive_or']['false_high_admissions']>0,
            'limitation':'Supplied independent primitive events and correct lineage required; Jev scores are not certified probabilities.'}


def clean(x):
    if isinstance(x,float):
        if not math.isfinite(x):
            raise ValueError('Nonfinite result')
        return round(x,12)
    if isinstance(x,dict):
        return {k:clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):
        return [clean(v) for v in x]
    return x


def run(root: Path = ROOT) -> dict:
    data,audit = load_data(root)
    return clean({'schema_version':1,'base_commit':'1e03d0e7dfbf0b0deb1e39ecf133e66e05be141b',
                  'protocol_commit':'49975b97464ce4ee8e5c67250d6690aaebeaea73','seed':SEED,'bootstrap_replicates':BOOTSTRAPS,
                  'fresh_service_calls':0,'model':'jev-1.13.0','source_sha256':SOURCE_HASHES,
                  'source_separation':audit,'H1':h1(data),'H2':h2(data),'H3':h3(data),'H4':h4(),'H5':h5()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args = parser.parse_args()
    from .report import render
    result = run()
    outputs = {HERE/'results.json':json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n',
               HERE/'RESULTS.md':render(result)}
    for path,text in outputs.items():
        if args.check:
            if path.suffix == '.json':
                from graph_synthesis.verify import compare_json
                compare_json(json.loads(path.read_text(encoding='utf-8')),json.loads(text))
            elif path.read_text(encoding='utf-8') != text:
                raise ValueError('Report drift: '+str(path))
        else:
            path.write_text(text,encoding='utf-8')
    print(json.dumps({'verified':args.check,'fresh_service_calls':0,
                      'primary_targets':{k:result[k]['primary_target_met'] for k in ('H1','H2','H3','H4','H5')}},indent=2))


if __name__ == '__main__':
    main()
