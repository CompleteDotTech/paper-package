from __future__ import annotations

import argparse, json, random, sys
from pathlib import Path
from itertools import combinations

from .methods import (
    max_sum_elimination, brute_force_optimum, DependencyGraph,
    query_resilience, brute_force_resilience,
    select_interval_minimax, oracle_interval_worst,
)

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).with_name('results.json')
SEED=20260923
BASELINE='9d2e4a60a6c79e616ab1d352cd5da9fe414e6c98'
PROTOCOL_COMMIT='8187cc4e4b98e40f3146ce787b71f262b62b3abd'


def k_tree_graph(rng,n,k):
    edges=set()
    initial=tuple(range(k+1))
    for a,b in combinations(initial,2): edges.add((a,b))
    kcliques={tuple(c) for c in combinations(initial,k)}
    for v in range(k+1,n):
        base=rng.choice(sorted(kcliques))
        for a in base: edges.add(tuple(sorted((a,v))))
        clique=tuple(sorted(base+(v,)))
        for c in combinations(clique,k): kcliques.add(tuple(c))
    return sorted(edges)


def h1(rng):
    failures=[]; perm_fail=0; state_sum=0; full_sum=0; solved=0
    cases=[]
    for i in range(160):
        n=rng.randint(8,16); k=rng.randint(1,min(4,n-1))
        edges=k_tree_graph(rng,n,k)
        weights=[rng.randint(1,19) for _ in range(n)]
        got=max_sum_elimination(weights,edges)
        want,_=brute_force_optimum(weights,edges)
        if got.status!='solved' or got.objective!=want:
            failures.append({'case':i,'n':n,'k':k,'status':got.status,'got':got.objective,'want':want,'width':got.induced_width})
        else: solved+=1
        if n>=12:
            state_sum+=got.factor_states; full_sum+=(1<<n)
        if i<64:
            base=(got.objective,got.selected,got.induced_width)
            for j in range(8):
                sh=list(edges); random.Random(SEED+i*100+j).shuffle(sh)
                g=max_sum_elimination(weights,sh)
                if (g.objective,g.selected,g.induced_width)!=base: perm_fail+=1
        cases.append({'n':n,'k':k,'width':got.induced_width,'objective':got.objective,'states':got.factor_states})
    large=[]
    for n in [33,65,129,257,385,513,769,1025]:
        edges=[]
        for i in range(n):
            if i+1<n: edges.append((i,i+1))
            if i+2<n: edges.append((i,i+2))
        got=max_sum_elimination([1]*n,edges)
        expected=(n+2)//3
        large.append({'n':n,'objective':got.objective,'expected':expected,'width':got.induced_width,'states':got.factor_states,'status':got.status})
        if got.status!='solved' or got.objective!=expected: failures.append({'large_n':n,'got':got.objective,'expected':expected,'status':got.status})
    controls=[]
    for n in [6,7,8,9,10]:
        edges=list(combinations(range(n),2)); got=max_sum_elimination([1]*n,edges)
        controls.append({'n':n,'status':got.status,'width':got.induced_width})
        if got.status!='staged': failures.append({'control_n':n,'status':got.status,'width':got.induced_width})
    saving=1-(state_sum/full_sum)
    target=(not failures and perm_fail==0 and saving>=.90)
    return {'primary_target_met':target,'small_cases':160,'small_solved':solved,'failures':failures,'permutation_failures':perm_fail,
            'large':large,'controls':controls,'counted_factor_states':state_sum,'full_assignment_count':full_sum,'state_reduction':saving,
            'case_width_histogram':{str(w):sum(1 for c in cases if c['width']==w) for w in sorted({c['width'] for c in cases})}}


def make_modular_dag(rng):
    P=64; defs={}
    for m in range(8):
        prim=list(range(m*8,(m+1)*8))
        prior=[]
        for j in range(32):
            node=P+m*32+j
            candidates=prim+prior
            depn=2 if len(candidates)<3 else rng.choice([2,2,3])
            deps=tuple(sorted(rng.sample(candidates,depn)))
            op=rng.choice(['and','or','xor'])
            defs[node]=(op,deps); prior.append(node)
    return DependencyGraph(P,defs)


def make_connected_dag():
    P=64; defs={}
    for j in range(256):
        node=P+j
        if j==0: deps=(0,1)
        else: deps=(P+j-1, 1+(j%63))
        defs[node]=('xor' if j%3==0 else ('or' if j%3==1 else 'and'),deps)
    return DependencyGraph(P,defs)


def h2(rng):
    mismatches=0; accepted=0; local_evals=0; full_evals=0
    failure_atomic=0; stale_atomic=0; malformed_atomic=0
    for gi in range(128):
        g=make_modular_dag(rng)
        prim={i:bool(rng.getrandbits(1)) for i in range(64)}
        values=g.full_recompute(prim); rev=0
        for t in range(5):
            m=rng.randrange(8); ks=rng.randint(1,4); ps=rng.sample(range(m*8,(m+1)*8),ks)
            changes={p:not values[p] for p in ps}
            newv,newrev,ev=g.transact(values,rev,changes,expected_revision=rev)
            newprim={i:newv[i] for i in range(64)}
            full=g.full_recompute(newprim)
            if newv!=full: mismatches+=1
            values,rev=newv,newrev; accepted+=1; local_evals+=ev; full_evals+=256
        if gi<64:
            before=dict(values); brevis=rev
            p=gi%64; changes={p:not values[p]}
            # choose an affected derived node
            affected=[]; stack=[p]; seen=set()
            while stack:
                x=stack.pop()
                for y in g.reverse[x]:
                    if y not in seen: seen.add(y); affected.append(y); stack.append(y)
            fail=affected[len(affected)//2] if affected else None
            try: g.transact(values,rev,changes,expected_revision=rev,fail_node=fail)
            except RuntimeError: pass
            if values==before and rev==brevis: failure_atomic+=1
            try: g.transact(values,rev,changes,expected_revision=rev-1)
            except RuntimeError: pass
            if values==before and rev==brevis: stale_atomic+=1
            try: g.transact(values,rev,{64:True},expected_revision=rev)
            except ValueError: pass
            if values==before and rev==brevis: malformed_atomic+=1
    connected=[]
    for i in range(16):
        g=make_connected_dag(); prim={j:bool((j+i)%2) for j in range(64)}; values=g.full_recompute(prim)
        newv,_,ev=g.transact(values,0,{0:not values[0]},expected_revision=0)
        ok=(newv==g.full_recompute({j:newv[j] for j in range(64)}))
        connected.append({'evaluations':ev,'full':256,'correct':ok,'saving':1-ev/256})
        if not ok: mismatches+=1
    saving=1-local_evals/full_evals
    target=(mismatches==0 and failure_atomic==64 and stale_atomic==64 and malformed_atomic==64 and saving>=.80)
    return {'primary_target_met':target,'accepted_transactions':accepted,'snapshot_mismatches':mismatches,'local_evaluations':local_evals,
            'full_recompute_evaluations':full_evals,'evaluation_reduction':saving,'failure_atomic_controls':failure_atomic,
            'stale_revision_controls':stale_atomic,'malformed_controls':malformed_atomic,'connected_controls':connected,
            'connected_mean_reduction':sum(x['saving'] for x in connected)/len(connected)}


def h3(rng):
    failures=[]; solved=0
    for i in range(160):
        n=rng.randint(4,12); atoms=list(range(n)); costs={a:rng.randint(1,9) for a in atoms}
        clauses=[]
        for _ in range(rng.randint(2,10)):
            size=rng.randint(1,min(4,n)); clauses.append(tuple(sorted(rng.sample(atoms,size))))
        got=query_resilience(clauses,costs); want,wset=brute_force_resilience(clauses,costs)
        if got['status']!='solved' or got['cost']!=want:
            failures.append({'case':i,'status':got['status'],'got':got['cost'],'want':want})
        else: solved+=1
        if got['status']=='solved':
            dele=set(got['delete'])
            if not all(set(c)&dele for c in clauses): failures.append({'case':i,'witness':'does not falsify'})
            if sum(costs[a] for a in dele)!=got['cost']: failures.append({'case':i,'witness':'cost mismatch'})
    large=[]
    for m in [256,384,512,768,1024,1280,1536,2048]:
        clauses=[]; costs={}; expected=0
        for j in range(m):
            a=2*j; b=a+1; ca=1+(j%7); cb=2+((j*3)%7); costs[a]=ca; costs[b]=cb
            clauses.append((a,b)); expected+=min(ca,cb)
        got=query_resilience(clauses,costs)
        large.append({'proof_components':m,'atoms':2*m,'cost':got['cost'],'expected':expected,'status':got['status']})
        if got['status']!='solved' or got['cost']!=expected: failures.append({'large':m,'got':got['cost'],'expected':expected,'status':got['status']})
    controls=[]
    for j in range(6):
        atoms=19+j; clauses=[(i,i+1) for i in range(atoms-1)]; costs={i:1 for i in range(atoms)}
        got=query_resilience(clauses,costs)
        controls.append({'atoms':atoms,'status':got['status']})
        if got['status']!='staged': failures.append({'control_atoms':atoms,'status':got['status']})
    return {'primary_target_met':not failures,'small_cases':160,'small_solved':solved,'failures':failures,'large':large,'controls':controls}


def random_query_fixture(rng):
    intervals={}
    for a in range(6):
        lo=rng.uniform(.03,.75); hi=rng.uniform(lo,min(.97,lo+rng.uniform(.03,.35)))
        intervals[a]=(round(lo,5),round(hi,5))
    queries=[]
    for _ in range(rng.randint(1,3)):
        q=[]
        for _ in range(rng.randint(1,3)):
            q.append(tuple(sorted(rng.sample(range(6),rng.randint(1,3)))))
        queries.append(q)
    return intervals,queries


def engineered_interval_fixture(i):
    # midpoint favors 0/1; worst-case variance favors 2/3
    e=(i%7)*0.001
    intervals={0:(.39+e,.41+e),1:(.41-e,.43-e),2:(.05,.50),3:(.10,.50),4:(.01,.05),5:(.94,.98)}
    queries=[[(a,)] for a in range(6)]
    return intervals,queries


def h4(rng):
    fixtures=[]; discrepancies=0; worse=0; strict=0; random_strict=0; engineered_strict=0
    for i in range(96):
        intervals,queries=random_query_fixture(rng)
        fixtures.append(('random',intervals,queries))
    for i in range(32): fixtures.append(('engineered',*engineered_interval_fixture(i)))
    samples=[]
    for kind,intervals,queries in fixtures:
        got=select_interval_minimax(queries,intervals,2)
        om=oracle_interval_worst(queries,intervals,got['minimax'])
        op=oracle_interval_worst(queries,intervals,got['midpoint'])
        if abs(om-got['minimax_worst'])>1e-10 or abs(op-got['midpoint_worst'])>1e-10: discrepancies+=1
        if om>op+1e-12: worse+=1
        if om<op-1e-12:
            strict+=1
            if kind=='random': random_strict+=1
            else: engineered_strict+=1
        if len(samples)<12: samples.append({'kind':kind,'minimax':list(got['minimax']),'midpoint':list(got['midpoint']),'minimax_worst':om,'midpoint_worst':op})
    point_controls=0
    for i in range(16):
        p={a:round(rng.uniform(.05,.95),5) for a in range(6)}; intervals={a:(v,v) for a,v in p.items()}
        queries=[[(a,)] for a in range(6)]
        got=select_interval_minimax(queries,intervals,2)
        if got['minimax']==got['midpoint'] and abs(got['minimax_worst']-got['midpoint_worst'])<1e-12: point_controls+=1
    target=(discrepancies==0 and worse==0 and strict>=26 and point_controls==16)
    return {'primary_target_met':target,'fixtures':128,'oracle_discrepancies':discrepancies,'worse_than_midpoint':worse,
            'strict_improvements':strict,'strict_fraction':strict/128,'random_strict':random_strict,'engineered_strict':engineered_strict,
            'degenerate_point_controls':point_controls,'samples':samples}


def h5(rng):
    failures=[]; perm_fail=0; solved=0
    for i in range(160):
        n=rng.randint(8,14); weights=[rng.randint(1,19) for _ in range(n)]; scopes=[]
        for j in range(n-1):
            if rng.random()<.35: scopes.append((j,j+1))
        for j in range(n-2):
            if rng.random()<.55: scopes.append((j,j+1,j+2))
        if not scopes: scopes=[(0,1,2)]
        got=max_sum_elimination(weights,scopes); want,_=brute_force_optimum(weights,scopes)
        if got.status!='solved' or got.objective!=want:
            failures.append({'case':i,'status':got.status,'got':got.objective,'want':want,'width':got.induced_width})
        else: solved+=1
        if i<64:
            base=(got.objective,got.selected,got.induced_width)
            for j in range(8):
                sh=list(scopes); random.Random(SEED+7000+i*100+j).shuffle(sh)
                g=max_sum_elimination(weights,sh)
                if (g.objective,g.selected,g.induced_width)!=base: perm_fail+=1
    large=[]
    for n in [64,128,256,512,768,1024,1536,2048]:
        scopes=[(i,i+1,i+2) for i in range(n-2)]
        got=max_sum_elimination([1]*n,scopes)
        expected=n-(n//3)
        pair=set()
        for s in scopes:
            for a,b in combinations(s,2): pair.add((a,b))
        projected=max_sum_elimination([1]*n,sorted(pair))
        large.append({'n':n,'objective':got.objective,'expected':expected,'pairwise_projection':projected.objective,'width':got.induced_width,'states':got.factor_states})
        if got.status!='solved' or got.objective!=expected or projected.objective is None or got.objective<=projected.objective:
            failures.append({'large_n':n,'got':got.objective,'expected':expected,'projected':projected.objective})
    controls=[]
    for n in [6,7,8,9,10]:
        got=max_sum_elimination([1]*n,[tuple(range(n))])
        controls.append({'arity':n,'status':got.status,'width':got.induced_width})
        if got.status!='staged': failures.append({'control_arity':n,'status':got.status,'width':got.induced_width})
    target=(not failures and perm_fail==0)
    return {'primary_target_met':target,'small_cases':160,'small_solved':solved,'failures':failures,'permutation_failures':perm_fail,'large':large,'controls':controls}


def execute():
    rng=random.Random(SEED)
    result={'baseline_commit':BASELINE,'protocol_commit':PROTOCOL_COMMIT,'seed':SEED,'fresh_jev_calls':0,'new_scientific_documents':0}
    result['H1']=h1(rng); result['H2']=h2(rng); result['H3']=h3(rng); result['H4']=h4(rng); result['H5']=h5(rng)
    result['targets_met']={k:result[k]['primary_target_met'] for k in ['H1','H2','H3','H4','H5']}
    return result


def canonical(obj): return json.dumps(obj,sort_keys=True,indent=2)+"\n"


def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--check',action='store_true'); ap.add_argument('--output',default=str(OUT)); args=ap.parse_args(argv)
    got=execute(); text=canonical(got); path=Path(args.output)
    if args.check:
        if not path.exists(): print('missing results',file=sys.stderr); return 2
        old=path.read_text(encoding='utf-8')
        if old!=text:
            print('results mismatch',file=sys.stderr); return 3
        print(json.dumps(got['targets_met'],sort_keys=True)); return 0
    path.write_text(text,encoding='utf-8',newline='\n')
    print(json.dumps(got['targets_met'],sort_keys=True))
    return 0

if __name__=='__main__': raise SystemExit(main())
