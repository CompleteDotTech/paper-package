"""Execute the frozen five-mechanism study; network disabled during replay."""
from __future__ import annotations
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
from itertools import combinations
import json
from pathlib import Path
import platform
import random
import socket
import statistics
import sys
import time
from unittest.mock import patch

import numpy as np
from .methods import (LABELS,POSITIVE,fit_shift,apply_shift,simplex_fit,dependence_bounds,
    minimal_repair,greedy_repair,bipartite_solve,pairwise_conflicts,indexed_conflicts)

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASELINE_COMMIT = 'a62a3257645d8e35cd4e45be53bfa9511d27724b'
PROTOCOL_COMMIT = 'b2a5ccbda2f511cf76aad4e3348a7a67fb1aabad'
SEED = 20260922
DRAWS = 4000


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8',newline='\n')


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def summary(rows,predictions,selected=None):
    gold = {r['id']:r['gold'] for r in rows}
    positive = [p for p in predictions if p['label'] in POSITIVE and (selected is None or p['id'] in selected)]
    correct = sum(p['label'] == gold[p['id']] for p in positive)
    denominator = sum(r['gold'] in POSITIVE for r in rows)
    return {'candidates':len(rows),'accepted':len(positive),'correct':correct,'wrong':len(positive)-correct,
            'gold_positive':denominator,'recall':correct/denominator if denominator else None,
            'precision':correct/len(positive) if positive else None,
            'errors':sum(p['label']=='ERROR' for p in predictions),
            'abstentions':sum(p['label']=='ABSTAIN' for p in predictions)}


def top_ids(predictions,k):
    return sorted(p['id'] for p in sorted((p for p in predictions if p['label'] in POSITIVE),key=lambda p:(-p['score'],p['id']))[:k])


def bootstrap(rows,baseline,proposed,selections):
    groups = sorted({r['group'] for r in rows}); truth = {r['id']:r for r in rows}
    vectors = {}
    for name,preds in [('baseline',baseline),('proposed',proposed)]:
        v = np.zeros((len(groups),4)); gi={g:i for i,g in enumerate(groups)}
        for p in preds:
            r=truth[p['id']]; i=gi[r['group']]; v[i,0]+=1
            if p['label'] in POSITIVE and p['id'] in selections[name]:
                v[i,1]+=1; v[i,2]+=p['label']==r['gold']; v[i,3]+=p['label']!=r['gold']
        vectors[name]=v
    weights=np.random.default_rng(SEED).multinomial(len(groups),np.full(len(groups),1/len(groups)),size=DRAWS)
    a,b=weights@vectors['proposed'],weights@vectors['baseline']
    with np.errstate(divide='ignore',invalid='ignore'):
        values={'wrong_edge_rate':a[:,3]/a[:,0]-b[:,3]/b[:,0], 'precision':a[:,2]/a[:,1]-b[:,2]/b[:,1]}
    return {k:{'95':np.quantile(v[np.isfinite(v)],[.025,.975]).tolist(),
               '99':np.quantile(v[np.isfinite(v)],[.005,.995]).tolist(),'draws':int(np.isfinite(v).sum())} for k,v in values.items()}


def shift_benchmark(development,test):
    dev=[{'id':r['id'],'split':r['split'],'gold':r['gold'],'prediction':r['views']['base1']} for r in development]
    features=[{'id':r['id'],'prediction':r['views']['base1']} for r in test]
    fit=fit_shift(dev,features); proposed=apply_shift(features,fit)
    baseline=[{'id':r['id'],**r['prediction']} for r in features]
    natural={name:summary(test,p) for name,p in [('baseline',baseline),('proposed',proposed)]}
    k=min(x['accepted'] for x in natural.values())
    selections={name:top_ids(p,k) for name,p in [('baseline',baseline),('proposed',proposed)]}
    matched={name:summary(test,p,set(selections[name])) for name,p in [('baseline',baseline),('proposed',proposed)]}
    source=np.full(3,1/3); c=np.full((3,3),.1)+.7*np.eye(3); truth=np.array([.1,.2,.7])
    controls=[]
    for name,matrix in [('label_shift',c),('conditional_shift',np.roll(c,1,axis=1))]:
        observed=matrix@truth; estimate=simplex_fit(c,observed,source)
        controls.append({'kind':name,'development_confusion':c.tolist(),'target_confusion':matrix.tolist(),
                         'true_target_prior':truth.tolist(),'estimated_prior':estimate,
                         'l1_prior_error':float(np.abs(np.array(estimate)-truth).sum())})
    gold = {r['id']:r['gold'] for r in test}
    correct_ids = {name:{p['id'] for p in preds if p['label'] in POSITIVE and p['label'] == gold[p['id']]}
                   for name,preds in [('baseline',baseline),('proposed',proposed)]}
    retained_ids = sorted(correct_ids['baseline'] & correct_ids['proposed'])
    lost_ids = sorted(correct_ids['baseline'] - correct_ids['proposed'])
    retention = len(retained_ids)/len(correct_ids['baseline']) if correct_ids['baseline'] else None
    return {'primary_target_met':retention is not None and retention>=.98 and matched['proposed']['wrong'] <= .8*matched['baseline']['wrong'] and matched['proposed']['wrong']<matched['baseline']['wrong'],
            'fit':fit,'natural':natural,'matched':matched,'matched_k':k,'correct_retention':retention,
            'retained_baseline_correct_ids':retained_ids,'lost_baseline_correct_ids':lost_ids,
            'selected_ids':selections,'predictions':{'baseline':baseline,'proposed':proposed},
            'observed_test_prior':[sum(r['gold']==k for r in test)/len(test) for k in LABELS],
            'observed_valid_test_prior':[sum(r['gold']==k and r['views']['base1']['status']=='ok' for r in test)/fit['valid_target'] for k in LABELS],
            'recorded_input_tokens':sum(r['arms']['single']['input_tokens'] for r in test),
            'bootstrap':bootstrap(test,baseline,proposed,{k:set(v) for k,v in selections.items()}),'controls':controls}


def joint_truth(proofs,atoms,masses):
    """Direct supplied joint table evaluation, not the LP or dual verifier."""
    total=Fraction(0)
    for mask,mass in enumerate(masses):
        active={a for i,a in enumerate(atoms) if mask & (1<<i)}
        if any(set(proof)<=active for proof in proofs): total+=mass
    return total


def lineage_benchmark():
    from ..reliability.methods import exact_lineage
    rng=random.Random(SEED); fixtures=[]; exclusions=false_admissions=invariance=0
    for case in range(128):
        n=rng.randrange(2,7); atoms=[f'a{i}' for i in range(n)]
        weights=[rng.randrange(0,11) for _ in range(1<<n)]; total=sum(weights)
        if not total: weights[0]=1; total=1
        masses=[Fraction(v,total) for v in weights]
        p={a:sum((mass for mask,mass in enumerate(masses) if mask&(1<<i)),Fraction(0)) for i,a in enumerate(atoms)}
        proofs=[sorted(rng.sample(atoms,rng.randrange(1,min(n,3)+1))) for _ in range(rng.randrange(1,9))]
        actual=joint_truth(proofs,atoms,masses); got=dependence_bounds(proofs,p)
        exclusions+=not Fraction(got['lower_rational'])<=actual<=Fraction(got['upper_rational'])
        false_admissions+=got['admit_095'] and actual<Fraction(19,20)
        invariance+=dependence_bounds(list(reversed(proofs))*3,dict(reversed(list(p.items()))))!=got
        independent=exact_lineage(proofs,{k:float(v) for k,v in p.items()})
        fixtures.append({'case':case,'atoms':atoms,'joint_integer_weights':weights,'marginals':{k:str(v) for k,v in p.items()},
                         'proofs':proofs,'truth':str(actual),'proposed':got,'independent':independent})
    analytical=[]; failures=0
    grid=[Fraction(0),Fraction(1,5),Fraction(1,2),Fraction(4,5),Fraction(19,20),Fraction(1)]
    for p in grid:
        for q in grid:
            for mode,proofs,lo,hi in [('AND',[['a','b']],max(0,p+q-1),min(p,q)),('OR',[['a'],['b']],max(p,q),min(1,p+q))]:
                got=dependence_bounds(proofs,{'a':p,'b':q})
                failures+=abs(got['lower']-float(lo))>1e-8 or abs(got['upper']-float(hi))>1e-8
                analytical.append({'mode':mode,'p':str(p),'q':str(q),'oracle':[str(lo),str(hi)],'proposed':got})
    control={'proofs':[['a'],['b']],'marginals':{'a':.8,'b':.8},'actual_truth':.8}
    control['independent']=exact_lineage(control['proofs'],control['marginals'])
    control['proposed']=dependence_bounds(control['proofs'],control['marginals'])
    prevented=control['independent']['lower']>=.95 and not control['proposed']['admit_095']
    bad=dependence_bounds([['a']],{'a':.99})
    return {'primary_target_met':not (exclusions or false_admissions or failures or invariance) and prevented,
            'fixtures':fixtures,'analytical':analytical,'interval_exclusions':int(exclusions),'false_admissions':int(false_admissions),
            'analytical_failures':int(failures),'invariance_failures':int(invariance),'correlation_control':control,
            'invalid_marginal_control':{'actual_truth':.8,'claimed_marginal':.99,'proposed':bad,'incorrect_admission':bad['admit_095']},
            'cap_control':dependence_bounds([[f'a{i}'] for i in range(9)],{f'a{i}':.8 for i in range(9)}),
            'mean_width':sum(r['proposed']['upper']-r['proposed']['lower'] for r in fixtures)/len(fixtures)}


def repair_oracle(target,protected,costs):
    """Independent full subset enumeration; does not use search helpers."""
    keys=sorted(costs); best=None
    for mask in range(1<<len(keys)):
        removed=tuple(k for i,k in enumerate(keys) if mask&(1<<i)); active=set(keys)-set(removed)
        if any(set(proof)<=active for proof in target): continue
        if any(not any(set(proof)<=active for proof in fact) for fact in protected): continue
        score=(sum(costs[k] for k in removed),removed)
        if best is None or score<best: best=score
    return {'status':'infeasible','cost':None,'removed':[]} if best is None else {'status':'optimal','cost':best[0],'removed':list(best[1])}


def repair_benchmark():
    rng=random.Random(SEED); fixtures=[]; failures=regressions=improved=feasible=0
    atoms=[f'a{i}' for i in range(8)]
    def proof(): return sorted(rng.sample(atoms,rng.randrange(1,4)))
    for case in range(128):
        costs={a:rng.randrange(1,10) for a in atoms}
        target=[proof() for _ in range(rng.randrange(3,9))]
        protected=[[proof() for _ in range(rng.randrange(1,4))] for _ in range(rng.randrange(4))]
        got=minimal_repair(target,protected,costs); baseline=greedy_repair(target,protected,costs); oracle=repair_oracle(target,protected,costs)
        failures+=any(got[k]!=oracle[k] for k in ('status','cost','removed'))
        if oracle['status']=='optimal':
            feasible+=1
            regressions+=baseline['status']=='feasible' and got['cost']>baseline['cost']
            improved+=baseline['status']!='feasible' or got['cost']<baseline['cost']
        fixtures.append({'case':case,'costs':costs,'target':target,'protected':protected,'proposed':got,'greedy':baseline,'oracle':oracle})
    costs=dict(a=2,b=2,c=2,d=3,e=3); target=[['a','b'],['a','c'],['b','d'],['c','e']]
    trap={'target':target,'costs':costs,'proposed':minimal_repair(target,[],costs),'greedy':greedy_repair(target,[],costs),'oracle':repair_oracle(target,[],costs)}
    return {'primary_target_met':not(failures or regressions) and feasible>0 and improved/feasible>=.05,
            'fixtures':fixtures,'oracle_failures':int(failures),'cost_regressions':int(regressions),'feasible_cases':feasible,
            'improved_cases':improved,'improved_fraction':improved/feasible if feasible else None,'greedy_trap':trap,
            'infeasible_control':minimal_repair([['a']],[[['a']]],{'a':1}),
            'state_cap_control':minimal_repair(target,[],costs,state_cap=1)}


def graph_oracle(weights,edges):
    keys=sorted(weights); best=0
    for mask in range(1<<len(keys)):
        chosen={k for i,k in enumerate(keys) if mask&(1<<i)}
        if all(not(a in chosen and b in chosen) for a,b in edges): best=max(best,sum(weights[k] for k in chosen))
    return best


def priority_greedy(weights,edges):
    adj={k:set() for k in weights}
    for a,b in edges: adj[a].add(b);adj[b].add(a)
    chosen=set()
    for k in sorted(weights,key=lambda k:(-weights[k],k)):
        if not chosen.intersection(adj[k]): chosen.add(k)
    return {'selected':sorted(chosen),'utility':sum(weights[k] for k in chosen)}


def flow_benchmark():
    from ..reliability.methods import solve_graph
    rng=random.Random(SEED); fixtures=[]; failures=regressions=invariance=0
    for case in range(128):
        n=rng.randrange(4,11); keys=[f'n{i}' for i in range(n)]; middle=n//2
        w={k:rng.randrange(0,10) for k in keys}; e=[(a,b) for a in keys[:middle] for b in keys[middle:] if rng.random()<.5]
        got=bipartite_solve(w,e); old=solve_graph(w,e); oracle=graph_oracle(w,e)
        failures+=got['utility']!=oracle or any(a in got['selected'] and b in got['selected'] for a,b in e)
        regressions+=got['utility']<old['utility']
        invariance+=bipartite_solve(dict(reversed(list(w.items()))),[(b,a) for a,b in reversed(e)]*2)!=got
        fixtures.append({'case':case,'weights':w,'edges':e,'proposed':got,'previous':old,'oracle':oracle})
    general=[]
    for case in range(32):
        w={f'g{i}':rng.randrange(1,10) for i in range(8)};e=[p for p in combinations(w,2) if rng.random()<.5]
        got=bipartite_solve(w,e); old=solve_graph(w,e); oracle=graph_oracle(w,e)
        failures+=got['utility']!=oracle;regressions+=got['utility']<old['utility']
        general.append({'case':case,'weights':w,'edges':e,'proposed':got,'previous':old,'oracle':oracle})
    large=[]
    for left,right in [(8,9),(16,16),(32,32),(64,64),(128,128)]:
        w={**{f'L{i:03d}':2 for i in range(left)},**{f'R{i:03d}':3 for i in range(right)}}
        e=[(a,b) for a in w if a[0]=='L' for b in w if b[0]=='R']
        got=bipartite_solve(w,e);old=solve_graph(w,e);oracle=max(2*left,3*right)
        failures+=got['utility']!=oracle or bool(got['staged']);regressions+=got['utility']<old['utility']
        large.append({'left':left,'right':right,'vertices':left+right,'edges':len(e),'weights_rule':'left=2; right=3',
                      'proposed':got,'previous':old,'greedy':priority_greedy(w,e),'oracle':oracle})
    return {'primary_target_met':not(failures or regressions or invariance) and all(r['proposed']['utility']>0 for r in large),
            'fixtures':fixtures,'general_controls':general,'large':large,'oracle_failures':int(failures),
            'utility_regressions':int(regressions),'invariance_failures':int(invariance),
            'semantic_control':bipartite_solve({'false':9,'true':8},[('false','true')]),
            'dense_nonbipartite_control':bipartite_solve({str(i):1 for i in range(17)},list(combinations([str(i) for i in range(17)],2)))}


def assertion(i,**kw):
    return {'id':str(i),'subject':'s','predicate':'located_in','object':'o','scope':'g','polarity':1,'start':0,'end':2,**kw}


def sparse_rows(n=2048):
    return [assertion(f'{k:04d}',subject=f's{k//16:03d}',object=f'o{k%2}',start=k%16,end=k%16+3) for k in range(n)]


def dense_rows(): return [assertion(f'{k:03d}',object=f'o{k}',start=0,end=10) for k in range(256)]


def integer_conflicts(rows):
    """Independent finite-time semantics on bounded fixtures, not interval math."""
    edges=set()
    for instant in range(-5,10):
        active=[r for r in rows if r['start']<=instant<r['end']]
        for a,b in combinations(active,2):
            if (a['subject'],a['predicate'],a['scope'])!=(b['subject'],b['predicate'],b['scope']):continue
            opposite=a['object']==b['object'] and a['polarity']!=b['polarity']
            functional=a['predicate']=='located_in' and a['object']!=b['object'] and a['polarity']==b['polarity']==1
            if opposite or functional: edges.add(tuple(sorted((a['id'],b['id']))))
    return [list(e) for e in sorted(edges)]


def index_benchmark():
    rng=random.Random(SEED);fixtures=[];failures=invariance=integer_failures=0
    for case in range(128):
        rows=[]
        for i in range(rng.randrange(3,17)):
            start=rng.randrange(-4,5);end=start+rng.randrange(1,5)
            rows.append(assertion(f'a{i}',subject=rng.choice(['s0','s1']),object=rng.choice(['a','b','c']),
                                  predicate=rng.choice(['located_in','p']),scope=rng.choice(['g0','g1']),
                                  polarity=rng.choice([-1,1]),start=start,end=end))
        bounded=indexed_conflicts(rows);oracle=integer_conflicts(rows)
        integer_failures+=bounded['edges']!=oracle
        for i in range(len(rows)):
            if i%7==0:rows[i]['start']=None
            if i%11==0:rows[i]['end']=None
        rows.append(assertion('invalid',scope=None))
        a,b=pairwise_conflicts(rows),indexed_conflicts(rows)
        failures+=a['edges']!=b['edges'] or a['staged']!=b['staged']
        invariance+=indexed_conflicts(list(reversed(rows)))!=b
        fixtures.append({'case':case,'rows':rows,'pairwise':a,'indexed':b,'bounded_oracle':oracle,'bounded_indexed':bounded['edges']})
    sparse=[]
    for n in (256,512,1024,2048):
        rows=sparse_rows(n);a,b=pairwise_conflicts(rows),indexed_conflicts(rows)
        mismatch=a['edges']!=b['edges'] or a['staged']!=b['staged'];failures+=mismatch
        sparse.append({'n':n,'baseline_checks':a['pair_checks'],'indexed_checks':b['pair_checks'],
                       'edge_count':len(a['edges']),'edges_sha256':digest(a['edges']),'mismatch':mismatch,
                       'saving':1-b['pair_checks']/a['pair_checks']})
    a,b=pairwise_conflicts(dense_rows()),indexed_conflicts(dense_rows())
    mismatch=a['edges']!=b['edges'] or a['staged']!=b['staged'];failures+=mismatch
    dense={'n':256,'baseline_checks':a['pair_checks'],'indexed_checks':b['pair_checks'],'edge_count':len(a['edges']),
           'edges_sha256':digest(a['edges']),'mismatch':mismatch,'saving':1-b['pair_checks']/a['pair_checks']}
    return {'primary_target_met':not(failures or integer_failures or invariance) and sparse[-1]['saving']>=.95,
            'fixtures':fixtures,'pairwise_failures':int(failures),'integer_oracle_failures':int(integer_failures),
            'invariance_failures':int(invariance),'sparse':sparse,'dense':dense}


def timings():
    import scipy
    results=[]
    for name,rows in [('sparse_2048',sparse_rows()),('dense_256',dense_rows())]:
        samples={'pairwise':[],'indexed':[]}
        # Alternate order to reduce systematic warmup/order bias; not a service benchmark.
        for repeat in range(5):
            for method in (('pairwise','indexed') if repeat%2==0 else ('indexed','pairwise')):
                fn=pairwise_conflicts if method=='pairwise' else indexed_conflicts
                start=time.perf_counter();got=fn(rows);elapsed=time.perf_counter()-start
                samples[method].append(elapsed)
        results.append({'workload':name,'n':len(rows),'seconds':samples,
                        'median_seconds':{k:statistics.median(v) for k,v in samples.items()},
                        'edges':len(got['edges']),'scope':'Validation, grouping/sorting, candidate checks and edge-list construction included; input generation and I/O excluded.'})
    return {'python':sys.version,'platform':platform.platform(),'numpy':np.__version__,'scipy':scipy.__version__,
            'samples_per_method':5,'results':results,'note':'Host-specific elapsed measurements, not service latency, invoices or a universal speedup. Not compared byte-for-byte during replay.'}


def execute():
    from ..adaptive.run import load,INPUT
    values,_,audit=load();ids=[r['id'] for r in values]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate candidate IDs')
    dev=[r for r in values if r['split']=='development'];test=[r for r in values if r['split']=='test']
    if {r['group'] for r in dev}.intersection(r['group'] for r in test):raise ValueError('Source-group leakage')
    if (len(dev),len(test))!=(73,263):raise ValueError('Frozen split changed')
    return {'schema_version':1,'baseline_commit':BASELINE_COMMIT,'protocol_commit':PROTOCOL_COMMIT,'fresh_service_calls':0,
            'evidence':'H1 recorded-response exploratory adaptation; H2-H5 controlled algorithms. Not new semantic observations.',
            'source_hashes':{(INPUT/name).relative_to(ROOT).as_posix():sha(INPUT/name) for name in ('plan.json','calls.jsonl','predictions.json','results.json')},
            'implementation_hashes':{f'graph_synthesis/novel_mechanisms/{name}':sha(HERE/name) for name in ('methods.py','run.py')},
            'input_verification':audit,'development':{'n':len(dev),'groups':len({r['group'] for r in dev})},
            'test':{'n':len(test),'groups':len({r['group'] for r in test})},'seed':SEED,'bootstrap_draws':DRAWS,
            'H1':shift_benchmark(dev,test),'H2':lineage_benchmark(),'H3':repair_benchmark(),'H4':flow_benchmark(),'H5':index_benchmark()}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');parser.add_argument('--timings',action='store_true')
    args=parser.parse_args()
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('Network forbidden')),patch.object(socket,'create_connection',side_effect=RuntimeError('Network forbidden')):
        result=json.loads(json.dumps(execute(),allow_nan=False))
        if args.check:
            from ..verify import compare_json
            tolerance=compare_json(json.loads((HERE/'results.json').read_text(encoding='utf-8')),result)
        else:write(HERE/'results.json',result);tolerance=None
        if args.timings:write(HERE/'timings.json',timings())
    print(json.dumps({'status':'reproduced' if args.check else 'executed','targets':{f'H{i}':result[f'H{i}']['primary_target_met'] for i in range(1,6)},'fresh_service_calls':0,'roundoff':tolerance}))


if __name__=='__main__':main()
