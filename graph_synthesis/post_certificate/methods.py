from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations, product
from math import inf
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple, FrozenSet, Set

NEG_INF = -10**30


@dataclass(frozen=True)
class Factor:
    scope: Tuple[int, ...]
    table: Mapping[Tuple[int, ...], int]

    def value(self, assignment: Mapping[int, int]) -> int:
        key = tuple(assignment[v] for v in self.scope)
        return self.table[key]


@dataclass
class EliminationResult:
    status: str
    objective: int | None
    selected: Tuple[int, ...]
    order: Tuple[int, ...]
    induced_width: int
    factor_states: int


def _scope_graph(n: int, factors: Sequence[Factor]) -> List[Set[int]]:
    adj=[set() for _ in range(n)]
    for f in factors:
        for a,b in combinations(f.scope,2):
            adj[a].add(b); adj[b].add(a)
    return adj


def min_fill_order(n: int, factors: Sequence[Factor]) -> Tuple[List[int], int]:
    adj=_scope_graph(n,factors)
    active=set(range(n))
    order=[]; width=0
    while active:
        best=None
        for v in active:
            neigh=sorted(adj[v] & active)
            fill=0
            for i,a in enumerate(neigh):
                aa=adj[a]
                for b in neigh[i+1:]:
                    if b not in aa:
                        fill+=1
            key=(fill,len(neigh),v)
            if best is None or key<best[0]:
                best=(key,v,neigh)
        _,v,neigh=best
        width=max(width,len(neigh))
        for i,a in enumerate(neigh):
            for b in neigh[i+1:]:
                adj[a].add(b); adj[b].add(a)
        active.remove(v)
        order.append(v)
    return order,width


def max_sum_elimination(
    weights: Sequence[int],
    forbidden_scopes: Sequence[Sequence[int]],
    *, width_cap: int=4,
    state_cap: int=250_000,
) -> EliminationResult:
    n=len(weights)
    factors: List[Factor]=[]
    for v,w in enumerate(weights):
        factors.append(Factor((v,),{(0,):0,(1,):int(w)}))
    for raw in forbidden_scopes:
        scope=tuple(sorted(set(raw)))
        if len(scope)<2:
            raise ValueError('forbidden scope must have at least 2 vertices')
        table={bits:(NEG_INF if all(bits) else 0) for bits in product((0,1), repeat=len(scope))}
        factors.append(Factor(scope,table))
    # Exact fast path for the long path/triangle-chain fixtures used by the
    # protocol: every non-unary scope lies inside a three-vertex sliding
    # window, so 0..n-1 is the same endpoint-first min-fill elimination.
    nonunary=[f.scope for f in factors if len(f.scope)>1]
    if n>64 and nonunary and all(max(s)-min(s)<=2 for s in nonunary):
        order=list(range(n)); width=max(max(s)-min(s) for s in nonunary)
    else:
        order,width=min_fill_order(n,factors)
    if width>width_cap:
        return EliminationResult('staged',None,tuple(),tuple(order),width,0)
    work=list(factors)
    back=[]
    states=0
    for v in order:
        touched=[f for f in work if v in f.scope]
        work=[f for f in work if v not in f.scope]
        union=sorted({x for f in touched for x in f.scope if x!=v})
        if len(union)>width_cap:
            return EliminationResult('staged',None,tuple(),tuple(order),max(width,len(union)),states)
        choices={}
        new_table={}
        for bits in product((0,1), repeat=len(union)):
            base=dict(zip(union,bits))
            vals=[]
            for xv in (0,1):
                a=dict(base); a[v]=xv
                score=0
                for f in touched:
                    fv=f.value(a)
                    if fv<=NEG_INF:
                        score=NEG_INF; break
                    score+=fv
                vals.append(score)
                states+=1
            # deterministic tie: prefer selected only when strictly better
            if vals[1]>vals[0]:
                best=1; val=vals[1]
            else:
                best=0; val=vals[0]
            choices[bits]=best
            new_table[bits]=val
            if states>state_cap:
                return EliminationResult('staged',None,tuple(),tuple(order),width,states)
        back.append((v,tuple(union),choices))
        work.append(Factor(tuple(union),new_table))
    total=0
    for f in work:
        if f.scope:
            raise AssertionError('nonconstant factor remains')
        total+=f.table[()]
    assignment={}
    for v,scope,choices in reversed(back):
        key=tuple(assignment[x] for x in scope)
        assignment[v]=choices[key]
    selected=tuple(v for v in range(n) if assignment.get(v,0))
    # direct feasibility
    for scope in forbidden_scopes:
        if all(assignment.get(v,0) for v in scope):
            raise AssertionError('returned infeasible assignment')
    obj=sum(weights[v] for v in selected)
    if obj!=total:
        raise AssertionError((obj,total))
    return EliminationResult('solved',obj,selected,tuple(order),width,states)


def brute_force_optimum(weights: Sequence[int], forbidden_scopes: Sequence[Sequence[int]]) -> Tuple[int,Tuple[int,...]]:
    n=len(weights); best=-1; best_sel=tuple()
    for mask in range(1<<n):
        ok=True
        for scope in forbidden_scopes:
            if all((mask>>v)&1 for v in scope):
                ok=False; break
        if not ok: continue
        score=sum(weights[v] for v in range(n) if (mask>>v)&1)
        sel=tuple(v for v in range(n) if (mask>>v)&1)
        if score>best or (score==best and sel<best_sel):
            best=score; best_sel=sel
    return best,best_sel


@dataclass
class DependencyGraph:
    primitive_count: int
    definitions: Dict[int, Tuple[str, Tuple[int,...]]]

    def __post_init__(self):
        self.total_nodes=self.primitive_count+len(self.definitions)
        self.reverse={i:set() for i in range(self.total_nodes)}
        for node,(op,deps) in self.definitions.items():
            for d in deps:
                self.reverse[d].add(node)
        self.derived_order=tuple(sorted(self.definitions))

    @staticmethod
    def eval_op(op: str, vals: Sequence[bool]) -> bool:
        if op=='and': return all(vals)
        if op=='or': return any(vals)
        if op=='xor':
            x=False
            for v in vals: x ^= bool(v)
            return x
        raise ValueError(op)

    def full_recompute(self, primitive_values: Mapping[int,bool]) -> Dict[int,bool]:
        values={i:bool(primitive_values[i]) for i in range(self.primitive_count)}
        for node in self.derived_order:
            op,deps=self.definitions[node]
            values[node]=self.eval_op(op,[values[d] for d in deps])
        return values

    def transact(self, values: Mapping[int,bool], revision: int, changes: Mapping[int,bool], *, expected_revision: int, fail_node: int|None=None):
        if expected_revision!=revision:
            raise RuntimeError('stale revision')
        for p,v in changes.items():
            if not isinstance(p,int) or p<0 or p>=self.primitive_count or not isinstance(v,bool):
                raise ValueError('malformed update')
        overlay=dict(values)
        changed=[]
        for p,v in changes.items():
            if overlay[p]!=v:
                overlay[p]=v; changed.append(p)
        affected=set()
        frontier=list(changed)
        while frontier:
            x=frontier.pop()
            for y in self.reverse[x]:
                if y not in affected:
                    affected.add(y); frontier.append(y)
        evals=0
        for node in self.derived_order:
            if node not in affected: continue
            if fail_node is not None and node==fail_node:
                raise RuntimeError('injected evaluation failure')
            op,deps=self.definitions[node]
            overlay[node]=self.eval_op(op,[overlay[d] for d in deps])
            evals+=1
        return overlay,revision+1,evals


def _normalize_clauses(clauses: Iterable[Iterable[int]]) -> Tuple[FrozenSet[int],...]:
    xs=sorted({frozenset(c) for c in clauses}, key=lambda s:(len(s),tuple(sorted(s))))
    out=[]
    for c in xs:
        if not c:
            return (frozenset(),)
        if any(d.issubset(c) for d in out):
            continue
        out.append(c)
    return tuple(out)


def _incidence_components(clauses: Sequence[FrozenSet[int]]) -> List[Tuple[FrozenSet[int],Tuple[FrozenSet[int],...]]]:
    atoms=set().union(*clauses) if clauses else set()
    adj={a:set() for a in atoms}
    for c in clauses:
        for a in c:
            adj[a].update(c-{a})
    comps=[]; seen=set()
    for a in sorted(atoms):
        if a in seen: continue
        stack=[a]; seen.add(a); comp=set()
        while stack:
            x=stack.pop(); comp.add(x)
            for y in adj[x]:
                if y not in seen: seen.add(y); stack.append(y)
        cclauses=tuple(c for c in clauses if c & comp)
        comps.append((frozenset(comp),cclauses))
    return comps


def _disjoint_clause_lb(clauses: Sequence[FrozenSet[int]], costs: Mapping[int,int]) -> int:
    used=set(); lb=0
    for c in sorted(clauses,key=lambda x:(len(x),min(costs[a] for a in x))):
        if c.isdisjoint(used):
            lb+=min(costs[a] for a in c)
            used.update(c)
    return lb


def _solve_hitting_component(clauses: Sequence[FrozenSet[int]], costs: Mapping[int,int]) -> Tuple[int,Set[int]]:
    clauses=_normalize_clauses(clauses)
    best_cost=10**18; best_set:set[int]=set()
    memo={}
    def rec(cs: Tuple[FrozenSet[int],...], chosen: FrozenSet[int], cost: int):
        nonlocal best_cost,best_set
        if not cs:
            if cost<best_cost or (cost==best_cost and tuple(sorted(chosen))<tuple(sorted(best_set))):
                best_cost=cost; best_set=set(chosen)
            return
        key=cs
        old=memo.get(key)
        if old is not None and old<=cost:
            return
        memo[key]=cost
        if cost+_disjoint_clause_lb(cs,costs)>=best_cost:
            return
        # forced singleton first, else shortest cheapest clause
        target=min(cs,key=lambda c:(len(c),sum(costs[a] for a in c),tuple(sorted(c))))
        for a in sorted(target,key=lambda x:(costs[x],x)):
            nc=tuple(c for c in cs if a not in c)
            rec(_normalize_clauses(nc), chosen|frozenset((a,)), cost+costs[a])
    rec(tuple(clauses),frozenset(),0)
    return best_cost,best_set


def query_resilience(clauses: Sequence[Sequence[int]], costs: Mapping[int,int], *, component_cap:int=18):
    norm=_normalize_clauses(clauses)
    if not norm:
        return {'status':'already_false','cost':0,'delete':tuple()}
    if norm==(frozenset(),):
        return {'status':'unstageable_true','cost':None,'delete':tuple()}
    total=0; chosen=set()
    for atoms,cc in _incidence_components(norm):
        if len(atoms)>component_cap:
            return {'status':'staged','cost':None,'delete':tuple()}
        c,s=_solve_hitting_component(cc,costs)
        total+=c; chosen.update(s)
    delete=tuple(sorted(chosen))
    # witness: all clauses hit
    if any(set(c).isdisjoint(chosen) for c in norm):
        raise AssertionError('invalid deletion witness')
    return {'status':'solved','cost':total,'delete':delete}


def brute_force_resilience(clauses: Sequence[Sequence[int]], costs: Mapping[int,int]):
    atoms=sorted(set().union(*(set(c) for c in clauses)))
    best=10**18; best_set=tuple()
    for mask in range(1<<len(atoms)):
        chosen={atoms[i] for i in range(len(atoms)) if (mask>>i)&1}
        if all(set(c)&chosen for c in clauses):
            cost=sum(costs[a] for a in chosen)
            sel=tuple(sorted(chosen))
            if cost<best or (cost==best and sel<best_set):
                best=cost; best_set=sel
    return best,best_set


def _condition_dnf(clauses: Tuple[Tuple[int,...],...], atom:int, value:int) -> Tuple[Tuple[int,...],...]:
    out=[]
    if value:
        for c in clauses:
            if atom in c:
                nc=tuple(x for x in c if x!=atom)
                if not nc: return (tuple(),)
                out.append(nc)
            else:
                out.append(c)
    else:
        for c in clauses:
            if atom not in c: out.append(c)
    # remove duplicates and supersets
    sets=_normalize_clauses(out)
    return tuple(tuple(sorted(s)) for s in sets)


def dnf_probability_shannon(clauses: Sequence[Sequence[int]], probs: Mapping[int,float]) -> float:
    norm=tuple(tuple(sorted(s)) for s in _normalize_clauses(clauses))
    @lru_cache(maxsize=None)
    def rec(cs: Tuple[Tuple[int,...],...]) -> float:
        if not cs: return 0.0
        if cs==(tuple(),): return 1.0
        atoms=sorted({a for c in cs for a in c})
        a=atoms[0]; p=probs[a]
        return p*rec(_condition_dnf(cs,a,1))+(1-p)*rec(_condition_dnf(cs,a,0))
    return rec(norm)


def dnf_probability_worlds(clauses: Sequence[Sequence[int]], probs: Mapping[int,float], fixed: Mapping[int,int]|None=None) -> float:
    fixed=dict(fixed or {})
    atoms=sorted(set(probs)-set(fixed))
    total=0.0
    for bits in product((0,1),repeat=len(atoms)):
        ass={**fixed,**dict(zip(atoms,bits))}
        pw=1.0
        for a,b in zip(atoms,bits):
            p=probs[a]; pw*=p if b else (1-p)
        truth=any(all(ass.get(a,0) for a in c) for c in clauses)
        if truth: total+=pw
    return total


def expected_residual_variance(queries: Sequence[Sequence[Sequence[int]]], probs: Mapping[int,float], review: Sequence[int], *, method='shannon') -> float:
    review=tuple(review)
    total=0.0
    for obs in product((0,1), repeat=len(review)):
        fixed=dict(zip(review,obs))
        pobs=1.0
        for a,b in fixed.items():
            p=probs[a]; pobs*=p if b else (1-p)
        if pobs==0: continue
        for q in queries:
            cond=[]
            forced_true=False
            for c in q:
                impossible=False; rem=[]
                for a in c:
                    if a in fixed:
                        if not fixed[a]: impossible=True; break
                    else: rem.append(a)
                if not impossible:
                    if not rem: forced_true=True; break
                    cond.append(rem)
            if forced_true:
                qp=1.0
            elif not cond:
                qp=0.0
            else:
                if method=='shannon':
                    qp=dnf_probability_shannon(cond,probs)
                else:
                    qp=dnf_probability_worlds(cond,probs)
            total+=pobs*qp*(1-qp)
    return total


def select_interval_minimax(queries, intervals: Mapping[int,Tuple[float,float]], budget:int=2):
    atoms=tuple(sorted(intervals))
    candidates=list(combinations(atoms,budget))
    endpoints=[]
    for bits in product((0,1),repeat=len(atoms)):
        endpoints.append({a:intervals[a][bits[i]] for i,a in enumerate(atoms)})
    worst={}
    for r in candidates:
        vals=[expected_residual_variance(queries,p,r,method='shannon') for p in endpoints]
        worst[r]=max(vals)
    minimax=min(candidates,key=lambda r:(worst[r],r))
    mid={a:(lo+hi)/2 for a,(lo,hi) in intervals.items()}
    point_obj={r:expected_residual_variance(queries,mid,r,method='shannon') for r in candidates}
    midpoint=min(candidates,key=lambda r:(point_obj[r],r))
    return {'minimax':minimax,'minimax_worst':worst[minimax], 'midpoint':midpoint,'midpoint_worst':worst[midpoint], 'all_worst':worst}


def oracle_interval_worst(queries, intervals: Mapping[int,Tuple[float,float]], review: Sequence[int]) -> float:
    atoms=tuple(sorted(intervals)); worst=0.0
    for bits in product((0,1),repeat=len(atoms)):
        p={a:intervals[a][bits[i]] for i,a in enumerate(atoms)}
        v=expected_residual_variance(queries,p,review,method='world')
        worst=max(worst,v)
    return worst
