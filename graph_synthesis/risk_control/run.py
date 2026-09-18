"""Execute the five frozen risk-control hypotheses without network/service calls."""
from __future__ import annotations
import argparse
from collections import defaultdict
from itertools import combinations
import hashlib
import json
from pathlib import Path
import random
import socket
from unittest.mock import patch
import numpy as np

from ..adaptive.run import load, summary, select, review_outcome, assertion, oracle_optimum, oracle_valid
from ..adaptive.methods import (POSITIVE, compact_route, safe_targeted, fit_risk, assign_risks,
                                review_order, optimize_batch, greedy_batch)
from ..analyze_multicall import group_vectors
from ..followup.methods import conflict
from ..verify import compare_json
from .methods import (fit_router, route, fit_gate, threshold_gate, qualifier_veto,
                      optimal_review, greedy_review, model_contamination, forest_batch, independent_set)

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
INPUT=ROOT/'experiments/jev-multicall-20260918'
SEED=20260920
DRAWS=4000
PROTOCOL_COMMIT='12b74f2772ba50f4b40e76b39a4ac0bf980802e4'
SOURCE_HASHES={
 'plan.json':'ea19a67662404c0dedcd5e88a2226720eeb03ea314a02abdff8406b4a80b058c',
 'calls.jsonl':'7e628ea16e8b6e3561060a752c03451f7426253fbb5496b2c2ff9a09c13e8187',
 'predictions.json':'8372542d67c3365c1374467700b2f21fc220c274d549ae3e1f070a2d8df58c7a',
 'results.json':'bebe29d34bd0a77ba06e88e5f99b4328e76a96b9f884d69ca56f065b1cf29d5a'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8',newline='\n')


def paired(data,arm,baseline='single',selections=None):
    groups=sorted({r['group'] for r in data})
    weights=np.random.default_rng(SEED).multinomial(len(groups),np.full(len(groups),1/len(groups)),size=DRAWS)
    def values(name):
        x=weights @ group_vectors(data,name,groups,None if selections is None else selections[name])
        with np.errstate(divide='ignore',invalid='ignore'):
            return {'precision':x[:,3]/x[:,2], 'recall':x[:,3]/x[:,4], 'wrong_edge_rate':(x[:,2]-x[:,3])/x[:,0]}
    a,b=values(arm),values(baseline); result={}
    for metric in a:
        delta=a[metric]-b[metric];valid=delta[np.isfinite(delta)]
        result[metric]={'draws':len(valid),'95':[float(x) for x in np.quantile(valid,[.025,.975])] if len(valid) else None,
                        '99':[float(x) for x in np.quantile(valid,[.005,.995])] if len(valid) else None}
    return result


def independent_review_loss(candidates,selected,sensitivity=.75):
    # Separate subset oracle: compute the probability of all remaining edges being correct.
    total=0.
    for group in sorted({r['group'] for r in candidates}):
        clean=1.
        for row in candidates:
            if row['group']==group:
                remaining_error=row['risk']*(1-sensitivity) if row['id'] in selected else row['risk']
                clean*=1-remaining_error
        total+=1-clean
    return total


def review_experiment(development,test):
    fit=fit_risk(development,split='development')
    candidates=assign_risks([{k:r[k] for k in ('id','group','views')} for r in test],fit)
    prior_order=review_order(candidates,group_aware=True)
    budgets=[]
    for budget in (10,20,30,40):
        selections={'greedy':greedy_review(candidates,budget,.75), 'optimal':optimal_review(candidates,budget,.75),
                    'prior_ideal_greedy':prior_order[:budget]}
        policies={}
        for name,keys in selections.items():
            selected=set(keys)
            policies[name]={'selected':sorted(selected),'model_contamination':model_contamination(candidates,selected,.75),
                            'primary':review_outcome(test,selected,.75,.05),
                            'sensitivity':[{'sensitivity':s,'false_removal':f,**review_outcome(test,selected,s,f)}
                                           for s in (.5,.75,1.) for f in (0.,.01,.05)]}
        budgets.append({'budget':budget,'policies':policies})
    rng=random.Random(SEED);fixtures=[];failures=0
    for case in range(64):
        rows=[{'id':str(i),'group':str(rng.randrange(3)),'risk':rng.randrange(1,10)/10} for i in range(8)]
        chosen=optimal_review(rows,3,.75)
        optimum=min(independent_review_loss(rows,set(keys)) for keys in combinations([r['id'] for r in rows],3))
        value=independent_review_loss(rows,set(chosen))
        failures+=abs(value-optimum)>1e-12
        fixtures.append({'case':case,'candidates':rows,'selected':chosen,'oracle_loss':optimum,'loss':value})
    counter=[{'id':'a','group':'A','risk':.9},{'id':'b','group':'A','risk':.9},{'id':'c','group':'B','risk':.2}]
    counter_selections={name:fn(counter,2,.75) for name,fn in [('greedy',greedy_review),('optimal',optimal_review)]}
    primary=budgets[1]['policies'];a,b=primary['optimal']['primary'],primary['greedy']['primary']
    model_pass=all(x['policies']['optimal']['model_contamination'] <= x['policies']['greedy']['model_contamination']+1e-12 for x in budgets)
    return {'fit':fit,'risks':candidates,'budgets':budgets,'oracle_fixtures':fixtures,'oracle_failures':int(failures),
            'algorithm_target_met':not failures and model_pass,
            'primary_target_met':a['expected_contaminated_groups'] < b['expected_contaminated_groups']-1e-12 and a['expected_correct_edges'] >= b['expected_correct_edges']-1e-12,
            'counterexample':{'candidates':counter,'selections':counter_selections,
                              'losses':{name:independent_review_loss(counter,set(keys)) for name,keys in counter_selections.items()}},
            'risk_feature_input_tokens':sum(r['arms']['single']['input_tokens']+r['arms']['contrastive']['input_tokens'] for r in test)}


def large_fixture(kind,n):
    if kind=='star':
        return [assertion('center',0,n,'center',15)]+[assertion(f'leaf{i:03}',i,i+1,'leaf',1) for i in range(n-1)]
    if kind=='path':
        return [assertion(f'v{i:03}',i,i+2,str(i),1+(7*i)%11) for i in range(n)]
    raise ValueError('Unknown fixture kind')


def large_oracle(kind,rows):
    if kind=='star':
        return max(rows[0]['weight'],sum(r['weight'] for r in rows[1:]))
    # Analytic path optimum, distinct from generic forest traversal.
    before,last=0,0
    for row in rows:
        before,last=last,max(last,before+row['weight'])
    return last


def graph_experiment():
    rng=random.Random(SEED);fixtures=[];failures=0;permutation_failures=0;unweighted_failures=0
    for case in range(64):
        rows=[]
        for i in range(8):
            start=rng.randrange(4)
            rows.append(assertion(str(i),start,rng.randrange(start+1,8),str(rng.randrange(3)),rng.randrange(1,10),
                                  scope=rng.choice(['A','A','B']),polarity=rng.choice([1,1,-1])))
        actual=forest_batch(rows);old=optimize_batch(rows);optimum=oracle_optimum(rows)
        chosen=[r for r in rows if r['id'] in actual['selected']]
        bad=not oracle_valid(chosen) or actual['utility'] != optimum or actual['utility']<old['utility'] or bool(actual['staged'])
        failures+=bad
        unweighted=[{**r,'weight':1} for r in rows]
        u=forest_batch(unweighted)
        unweighted_failures+=u['utility']!=oracle_optimum(unweighted) or not oracle_valid([r for r in unweighted if r['id'] in u['selected']])
        for shift in range(1,8):
            permutation_failures+=forest_batch(rows[shift:]+rows[:shift]) != actual
        permutation_failures+=forest_batch(list(reversed(rows))) != actual
        fixtures.append({'case':case,'assertions':rows,'forest':actual,'prior':old,'oracle_utility':optimum})
    large=[]
    for kind in ('star','path'):
        for n in (17,32,64,128,256):
            rows=large_fixture(kind,n);actual=forest_batch(rows);prior=optimize_batch(rows);greedy=greedy_batch(rows,priority=True)
            optimum=large_oracle(kind,rows);chosen=[r for r in rows if r['id'] in actual['selected']]
            valid=all(conflict(a,b,frozenset({'located_in'}))=='clear' for a,b in combinations(chosen,2))
            large.append({'kind':kind,'n':n,'assertions_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest(),
                          'forest':actual,'prior':prior,'greedy':greedy,'oracle_utility':optimum,'consistent':valid,
                          'target_met':valid and actual['utility']==optimum and optimum>0 and not actual['staged']})
    cycle={str(i):{str((i-1)%17),str((i+1)%17)} for i in range(17)}
    misleading=[assertion('false',0,2,'B',9),assertion('true',0,2,'A',8)]
    return {'random_cases':64,'fixtures':fixtures,'oracle_failures':int(failures),
            'unweighted_oracle_cases':64,'unweighted_oracle_failures':int(unweighted_failures),
            'permutation_checks':512,'permutation_failures':int(permutation_failures),'large':large,
            'primary_target_met':not failures and not unweighted_failures and not permutation_failures and all(r['target_met'] for r in large),
            'odd_cycle_control':independent_set(cycle,{str(i):1 for i in range(17)}),
            'over_limit_control':forest_batch(large_fixture('star',257)),
            'semantic_control':{'assertions':misleading,'semantic_truth':['true'],'selected':forest_batch(misleading),
                                'note':'A false high-priority assertion is still selected; optimization is not truth.'}}


def execute():
    for name,expected in SOURCE_HASHES.items():
        if sha(INPUT/name)!=expected:
            raise ValueError('Frozen protocol input mismatch: '+name)
    values,panels,audit=load()
    development=[r for r in values if r['split']=='development'];test=[r for r in values if r['split']=='test']
    if {r['group'] for r in development}&{r['group'] for r in test}:
        raise ValueError('Development/test source groups overlap')
    for row in values:
        calls=panels[row['id']]
        row['arms'].update({'safe_targeted':safe_targeted(calls),'compact_confidence':compact_route(calls,disagreement=False),
                            'compact_disagreement':compact_route(calls), 'qualifier_veto':qualifier_veto(calls),
                            'invalid_only':qualifier_veto(calls,veto=False)})
    router=fit_router(development,panels,split='development');gate=fit_gate(development,split='development')
    for row in values:
        row['arms']['value_route']=route(panels[row['id']],router)
        row['arms']['group_gate']=threshold_gate(row['arms']['safe_targeted'],gate['threshold'])
    names=('single','contrastive','targeted','safe_targeted','compact_confidence','compact_disagreement','value_route','group_gate','invalid_only','qualifier_veto')
    observed={name:summary(test,name) for name in names}
    base=observed['single'];h1=observed['value_route'];h2=observed['group_gate'];h3=observed['qualifier_veto']
    k=min(base['accepted'],h3['accepted']);selections={name:select(test,name,k) for name in ('single','qualifier_veto')}
    matched={name:summary(test,name,keys) for name,keys in selections.items()}
    nonempty_groups={r['group'] for r in test if r['arms']['group_gate']['label'] in POSITIVE}
    vetoed=[r for r in test if r['arms']['qualifier_veto'].get('reason')=='qualifier_mismatch']
    result={'schema_version':1,'baseline_commit':'88f271a92e901039877f906894e65ee55bc6962e','protocol_commit':PROTOCOL_COMMIT,
            'protocol_sha256':sha(HERE/'PROTOCOL.md'),'fresh_service_calls':0,
            'source_hashes':{(INPUT/name).relative_to(ROOT).as_posix():value for name,value in SOURCE_HASHES.items()},
            'input_verification':audit,'development':{'n':len(development),'groups':len({r['group'] for r in development})},
            'test':{'n':len(test),'groups':len({r['group'] for r in test})},'observed':observed,
            'bootstrap':{'draws':DRAWS,'seed':SEED,'note':'Paired source-group percentile; fixed fits and matched ID sets; exploratory, not simultaneous.'},
            'H1':{'fit':router,'token_saving':1-h1['input_tokens']/base['input_tokens'],'correct_retention':h1['correct_edges']/base['correct_edges'],
                  'primary_target_met':h1['input_tokens']<=.60*base['input_tokens'] and h1['correct_edges']>=.98*base['correct_edges'] and h1['wrong_edges']<=base['wrong_edges'],
                  'paired_vs_single':paired(test,'value_route')},
            'H2':{'fit':gate,'all_group_contamination':h2['contaminated_groups']/h2['groups'],
                  'nonempty_groups':len(nonempty_groups),'conditional_contamination':h2['contaminated_groups']/len(nonempty_groups) if nonempty_groups else None,
                  'correct_retention':h2['correct_edges']/base['correct_edges'],
                  'primary_target_met':gate['nontrivial'] and h2['correct_edges']>=.90*base['correct_edges'] and h2['contaminated_groups']/h2['groups']<=.15},
            'H3':{'matched_k':k,'matched':matched,'selected_ids':{name:sorted(keys) for name,keys in selections.items()},
                  'valid_vetoes':len(vetoed),'correct_edges_vetoed':sum(r['gold']=='SUPPORTS' for r in vetoed),
                  'invalid_checks':sum(r['arms']['qualifier_veto'].get('reason')=='invalid_checks' for r in test),
                  'primary_target_met':matched['qualifier_veto']['wrong_edges']<=.80*matched['single']['wrong_edges'] and h3['correct_edges']>=.95*base['correct_edges'] and h3['input_tokens']<=1.5*base['input_tokens'],
                  'paired_vs_single':paired(test,'qualifier_veto'), 'matched_intervals':paired(test,'qualifier_veto',selections=selections)},
            'H4':review_experiment(development,test),'H5':graph_experiment()}
    predictions=[{k:r[k] for k in ('id','group','split','gold','arms')} for r in values]
    return result,predictions


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('Network forbidden')),patch.object(socket,'create_connection',side_effect=RuntimeError('Network forbidden')):
        result,predictions=execute()
    for name,value in [('results.json',result),('predictions.json',predictions)]:
        if args.check:
            compare_json(read(HERE/name),value)
        else:
            write(HERE/name,value)
    print(json.dumps({'status':'reproduced' if args.check else 'executed','targets':{f'H{i}':result[f'H{i}']['primary_target_met'] for i in range(1,6)},'fresh_service_calls':0}))


if __name__=='__main__':main()
