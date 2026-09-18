"""Five bounded experimental mechanisms, with gold-free execution interfaces."""
from __future__ import annotations
from collections import Counter, defaultdict, deque
from fractions import Fraction
import heapq
from itertools import combinations
import math
from typing import Mapping, Sequence

import numpy as np

from ..followup.methods import supported, semantic_collision, conflict
from ..reliability.methods import graph_input, components, solve_component, aggregate

LABELS = ('SUPPORTS', 'REFUTES', 'NOT_ENOUGH_INFO')
POSITIVE = frozenset(LABELS[:2])


def vector(value: Mapping) -> np.ndarray | None:
    """Operational failures stay failures; malformed probabilities are rejected."""
    if value.get('status') == 'error' or value.get('label') == 'ERROR':
        return None
    probabilities = value.get('probabilities')
    if not isinstance(probabilities, Mapping) or set(probabilities) != set(LABELS):
        raise ValueError('Require the exact three-class probability contract')
    if any(type(probabilities[k]) not in (int, float) for k in LABELS):
        raise ValueError('Probabilities must be finite numbers, not booleans')
    p = np.array([probabilities[k] for k in LABELS], dtype=float)
    if not np.all(np.isfinite(p)) or np.any(p < 0) or np.any(p > 1) or abs(p.sum()-1) > 1e-6:
        raise ValueError('Invalid probability vector')
    if value.get('label') not in LABELS:
        raise ValueError('Valid output requires a known label')
    return p


def simplex_fit(confusion: Sequence, observed: Sequence, prior: Sequence, ridge: float = .01) -> list[float]:
    """Convex quadratic solved independently on each nonempty simplex face."""
    c, m, p = map(lambda x: np.asarray(x, dtype=float), (confusion, observed, prior))
    if c.shape != (3,3) or m.shape != (3,) or p.shape != (3,):
        raise ValueError('Three-class arrays required')
    if (not all(np.all(np.isfinite(a)) for a in (c,m,p)) or np.any(c < 0)
            or np.any(m < 0) or np.any(p < 0) or not np.allclose(c.sum(axis=0),1)
            or not np.isclose(m.sum(),1) or not np.isclose(p.sum(),1)
            or type(ridge) not in (float,int) or not math.isfinite(ridge) or ridge <= 0):
        raise ValueError('Invalid simplex fit inputs')
    h, b = c.T@c + ridge*np.eye(3), c.T@m + ridge*p
    candidates = []
    for mask in range(1,8):
        active = [i for i in range(3) if mask & (1 << i)]
        sub = h[np.ix_(active,active)]
        kkt = np.block([[sub, np.ones((len(active),1))], [np.ones((1,len(active))), np.zeros((1,1))]])
        solution = np.linalg.solve(kkt, np.r_[b[active],1.])[:-1]
        if np.min(solution) < -1e-10:
            continue
        q = np.zeros(3); q[active] = np.maximum(solution,0)
        q /= q.sum()
        objective = float(np.sum((c@q-m)**2) + ridge*np.sum((q-p)**2))
        candidates.append((objective, mask, q))
    return min(candidates, key=lambda x:(x[0],x[1]))[2].tolist()


def fit_shift(development: Sequence[Mapping], target: Sequence[Mapping]) -> dict:
    if not development or any(r.get('split') != 'development' for r in development):
        raise ValueError('Nonempty development-only fit required')
    if any('gold' in r for r in target):
        raise ValueError('Target estimator must not receive gold labels')
    counts = np.ones((3,3)); source = np.ones(3)
    valid_dev = 0
    for r in development:
        if r.get('gold') not in LABELS:
            raise ValueError('Unknown development class')
        p = vector(r['prediction'])
        if p is None: continue
        y, pred = LABELS.index(r['gold']), LABELS.index(r['prediction']['label'])
        counts[pred,y] += 1; source[y] += 1; valid_dev += 1
    valid_target = [r for r in target if vector(r['prediction']) is not None]
    if not valid_dev or not valid_target:
        raise ValueError('No valid development or target outputs')
    c, source = counts/counts.sum(axis=0), source/source.sum()
    m = np.array([sum(r['prediction']['label'] == k for r in valid_target) for k in LABELS])/len(valid_target)
    rank = int(np.linalg.matrix_rank(c))
    q = source.tolist() if rank < 3 else simplex_fit(c,m,source)
    return {'source_prior': source.tolist(), 'target_prior': q, 'confusion':c.tolist(),
            'target_predicted_frequency':m.tolist(), 'rank':rank,
            'fallback': 'unchanged_unidentifiable' if rank < 3 else None,
            'valid_development': valid_dev, 'valid_target':len(valid_target),
            'fit_ids': sorted(r['id'] for r in development),
            'target_ids': sorted(r['id'] for r in target)}


def apply_shift(target: Sequence[Mapping], fit: Mapping) -> list[dict]:
    if any('gold' in r for r in target):
        raise ValueError('Prediction execution must not receive gold')
    source, target_prior = np.asarray(fit['source_prior'],dtype=float), np.asarray(fit['target_prior'],dtype=float)
    if (source.shape != (3,) or target_prior.shape != (3,) or not np.all(np.isfinite(source))
            or not np.all(np.isfinite(target_prior)) or np.any(source <= 0) or np.any(target_prior < 0)
            or not np.isclose(source.sum(),1) or not np.isclose(target_prior.sum(),1)):
        raise ValueError('Invalid fitted priors')
    ratio = target_prior / source
    output = []
    for r in target:
        p = vector(r['prediction'])
        if fit.get('fallback'):
            output.append({'id':r['id'], **dict(r['prediction'])})
            continue
        if p is None:
            output.append({'id':r['id'], 'label':'ERROR', 'score':None, 'status':'error'})
            continue
        q = p * ratio
        if not np.isfinite(q.sum()) or q.sum() <= 0:
            output.append({'id':r['id'], 'label':'ABSTAIN', 'score':None, 'status':'abstain'})
            continue
        q /= q.sum(); index = int(np.argmax(q))
        output.append({'id':r['id'], 'label':LABELS[index], 'score':float(q[index]),
                       'status':'ok', 'probabilities':dict(zip(LABELS,q.tolist()))})
    return output


def rational(value) -> Fraction:
    if isinstance(value, bool) or not isinstance(value,(int,float,Fraction)):
        raise ValueError('Finite numeric probability required')
    if isinstance(value,float) and not math.isfinite(value):
        raise ValueError('Finite numeric probability required')
    q = value if isinstance(value,Fraction) else Fraction(str(value))
    if not 0 <= q <= 1: raise ValueError('Probability outside [0,1]')
    return q


def proof_input(proofs: Sequence[Sequence[str]], marginals: Mapping) -> tuple:
    if any(not isinstance(k,str) or not k for k in marginals):
        raise ValueError('Nonempty atom IDs required')
    p = {k:rational(v) for k,v in sorted(marginals.items())}
    family = set()
    for proof in proofs:
        if isinstance(proof,(str,bytes)) or not proof or any(a not in p for a in proof):
            raise ValueError('Nonempty proofs using known atoms required')
        family.add(tuple(sorted(set(proof))))
    family = tuple(sorted(q for q in family if not any(set(r) < set(q) for r in family)))
    return family,p


def generic_bounds(proofs, p):
    if not proofs: return Fraction(0),Fraction(0)
    lower = max(max(Fraction(0),sum(p[a] for a in proof)-(len(proof)-1)) for proof in proofs)
    upper = min(Fraction(1),sum(min(p[a] for a in proof) for proof in proofs))
    return lower,upper


def dependence_bounds(proofs: Sequence[Sequence[str]], marginals: Mapping, *, atom_cap: int = 8,
                      solver=None) -> dict:
    """Rationally checked dual bounds valid without primitive independence.

    Numerical LPs only propose dual coefficients. Every inequality is checked
    with exact fractions; an outward constant correction restores feasibility.
    Floating summaries are not the admission certificate.
    """
    if type(atom_cap) is not int or not 0 <= atom_cap <= 8:
        raise ValueError('Atom cap must be an integer in [0,8]')
    family,p = proof_input(proofs,marginals)
    atoms = sorted({a for proof in family for a in proof})
    lower,upper = generic_bounds(family,p)
    route, certificates = ('empty' if not family else 'frechet_fallback'), []
    if family and len(atoms) <= atom_cap:
        worlds = [[int(mask & (1 << i) != 0) for i in range(len(atoms))] for mask in range(1 << len(atoms))]
        truth = [int(any(all(world[atoms.index(a)] for a in proof) for proof in family)) for world in worlds]
        columns = [[1]+world for world in worlds]
        b = [Fraction(1)]+[p[a] for a in atoms]
        a_eq = np.asarray(columns,dtype=float).T
        if solver is None:
            from scipy.optimize import linprog
            solver = linprog
        try:
            for sign in (1,-1):
                result = solver(np.asarray(truth,dtype=float)*sign, A_eq=a_eq,
                                b_eq=np.asarray(b,dtype=float), bounds=(0,None), method='highs')
                if not result.success:
                    raise ArithmeticError('LP did not complete')
                y = [Fraction(float(v)).limit_denominator(1_000_000) for v in result.eqlin.marginals]
                if len(y) != len(b): raise ArithmeticError('Malformed LP dual')
                violation = max(Fraction(0), max(sum(v*c for v,c in zip(y,col))-sign*t for col,t in zip(columns,truth)))
                y[0] -= violation
                if any(sum(v*c for v,c in zip(y,col)) > sign*t for col,t in zip(columns,truth)):
                    raise ArithmeticError('Unverified dual')
                bound = sum(v*x for v,x in zip(y,b))
                certificates.append({'sign':sign, 'dual':[str(x) for x in y], 'value':str(bound),
                                     'outward_correction':str(violation), 'worlds_checked':len(worlds)})
            lower = max(lower,Fraction(certificates[0]['value']))
            upper = min(upper,-Fraction(certificates[1]['value']))
            if lower > upper: raise ArithmeticError('Contradictory bounds')
            route = 'verified_dual_lp'
        except (ArithmeticError, ValueError, TypeError, AttributeError, RuntimeError, OverflowError):
            lower,upper = generic_bounds(family,p)
            route,certificates = 'frechet_solver_fallback',[]
    return {'lower':float(lower), 'upper':float(upper), 'lower_rational':str(lower),
            'upper_rational':str(upper), 'admit_095':lower >= Fraction(19,20),
            'route':route, 'atoms':atoms, 'proofs':[list(x) for x in family], 'certificates':certificates}


def repair_input(target, protected, costs):
    if any(not isinstance(k,str) or not k or type(v) is not int or v <= 0 for k,v in costs.items()):
        raise ValueError('Named sources with positive integer costs required')
    dummy = {k:1 for k in costs}
    t,_ = proof_input(target,dummy)
    p = [proof_input(fact,dummy)[0] for fact in protected]
    return t,p


def survives(proofs, removed):
    return any(not set(proof).intersection(removed) for proof in proofs)


def minimal_repair(target, protected, costs, *, atom_cap=16, state_cap=65536):
    """Bounded branch-on-unhit-proof search; proposals only, no graph writes."""
    if type(atom_cap) is not int or not 0 <= atom_cap <= 16 or type(state_cap) is not int or state_cap < 1 or state_cap > 65536:
        raise ValueError('Invalid repair bounds')
    target,protected = repair_input(target,protected,costs)
    if len(costs) > atom_cap:
        return {'status':'staged', 'removed':[], 'cost':None, 'states':0}
    best, visited, exhausted = None,set(),False
    def search(removed):
        nonlocal best,exhausted
        key = tuple(sorted(removed))
        if key in visited: return
        if len(visited) >= state_cap:
            exhausted = True; return
        visited.add(key)
        cost = sum(costs[a] for a in key)
        if best is not None and cost > best[0]: return
        if any(not survives(fact,removed) for fact in protected): return
        unhit = [proof for proof in target if not set(proof).intersection(removed)]
        if not unhit:
            candidate = (cost,key)
            if best is None or candidate < best: best = candidate
            return
        proof = min(unhit,key=lambda q:(len(q),q))
        for atom in sorted(proof,key=lambda a:(costs[a],a)):
            search(removed|{atom})
    search(set())
    if exhausted: return {'status':'staged','removed':[],'cost':None,'states':len(visited)}
    if best is None: return {'status':'infeasible','removed':[],'cost':None,'states':len(visited)}
    return {'status':'optimal','removed':list(best[1]),'cost':best[0],'states':len(visited)}


def greedy_repair(target, protected, costs):
    target,protected = repair_input(target,protected,costs)
    removed = set()
    if any(not survives(fact,removed) for fact in protected):
        return {'status':'dead_end','removed':[],'cost':None}
    while any(not set(p).intersection(removed) for p in target):
        unhit = [p for p in target if not set(p).intersection(removed)]
        choices = [a for a in costs if a not in removed and any(a in p for p in unhit)
                   and all(survives(fact,removed|{a}) for fact in protected)]
        if not choices: return {'status':'dead_end','removed':sorted(removed),'cost':None}
        atom = min(choices,key=lambda a:(-Fraction(sum(a in p for p in unhit),costs[a]),a))
        removed.add(atom)
    return {'status':'feasible','removed':sorted(removed),'cost':sum(costs[a] for a in removed)}


def bipartition(adj, group):
    color = {}
    for root in sorted(group):
        if root in color: continue
        color[root] = 0; queue = deque([root])
        while queue:
            v = queue.popleft()
            for u in sorted(adj[v]):
                if u not in color:
                    color[u] = 1-color[v]; queue.append(u)
                elif color[u] == color[v]: return None
    return color


def flow_component(weights, adj, group, color):
    """Integer Edmonds-Karp; returned cover certifies the supplied objective."""
    keys = sorted(group); index = {k:i+2 for i,k in enumerate(keys)}
    residual = [defaultdict(int) for _ in range(len(keys)+2)]
    capacity = {}
    def edge(u,v,c):
        residual[u][v] += c; residual[v][u] += 0; capacity[u,v] = c
    total = sum(weights[k] for k in keys)
    for k in keys:
        edge(0,index[k],weights[k]) if color[k] == 0 else edge(index[k],1,weights[k])
    for a in keys:
        if color[a] == 0:
            for b in sorted(adj[a]): edge(index[a],index[b],total+1)
    flow, augmentations = 0,0
    while True:
        parent = {0:None}; queue = deque([0])
        while queue and 1 not in parent:
            u = queue.popleft()
            for v in sorted(residual[u]):
                if v not in parent and residual[u][v] > 0:
                    parent[v] = u; queue.append(v)
        if 1 not in parent: break
        v, amount = 1,total+1
        while parent[v] is not None:
            u = parent[v]; amount = min(amount,residual[u][v]); v = u
        v = 1
        while parent[v] is not None:
            u = parent[v]; residual[u][v] -= amount; residual[v][u] += amount; v = u
        flow += amount; augmentations += 1
    reachable = {0}; queue = deque([0])
    while queue:
        u = queue.popleft()
        for v in sorted(residual[u]):
            if v not in reachable and residual[u][v] > 0:
                reachable.add(v); queue.append(v)
    cover = [k for k in keys if (color[k] == 0 and index[k] not in reachable) or (color[k] == 1 and index[k] in reachable)]
    selected = sorted(set(keys)-set(cover))
    cut = sum(c for (u,v),c in capacity.items() if u in reachable and v not in reachable)
    if sum(weights[k] for k in cover) != flow or flow != cut or any(b in adj[a] for a,b in combinations(selected,2)):
        raise ArithmeticError('Invalid flow/cover solution')
    return {'selected':selected,'staged':[],'utility':total-flow,'method':'bipartite_flow',
            'cover':cover,'flow':flow,'cut_capacity':cut,'augmentations':augmentations,
            'vertex_order':keys,'flow_edges':[[u,v,c-residual[u][v],c] for (u,v),c in sorted(capacity.items()) if c-residual[u][v]>0]}


def bipartite_solve(weights: Mapping[str,int], edges: Sequence) -> dict:
    adj = graph_input(weights,edges)
    solutions = []
    for group in components(adj):
        color = bipartition(adj,group)
        if color is not None and len(group) <= 256:
            solutions.append(flow_component(weights,adj,group,color))
        else:
            solutions.append(solve_component(weights,adj,group))
    return {**aggregate(solutions),'components':solutions}


def assertion_input(assertions):
    if any(not isinstance(r.get('id'),str) or not r['id'] for r in assertions) or len({r['id'] for r in assertions}) != len(assertions):
        raise ValueError('Nonempty unique assertion IDs required')
    valid = sorted((r for r in assertions if supported(r)),key=lambda r:r['id'])
    staged = sorted(r['id'] for r in assertions if not supported(r))
    return valid,staged


def pairwise_conflicts(assertions: Sequence[Mapping], *, functional=frozenset({'located_in'})) -> dict:
    valid,staged = assertion_input(assertions)
    edges = [sorted((a['id'],b['id'])) for a,b in combinations(valid,2) if conflict(a,b,functional) == 'conflict']
    return {'edges':sorted(edges),'staged':staged,'pair_checks':len(valid)*(len(valid)-1)//2,'validated_rows':len(assertions)}


def indexed_conflicts(assertions: Sequence[Mapping], *, functional=frozenset({'located_in'})) -> dict:
    valid,staged = assertion_input(assertions)
    groups = defaultdict(list)
    for row in valid: groups[row['subject'],row['predicate'],row['scope']].append(row)
    edges,checks = [],0
    for key in sorted(groups):
        active,expiry = {},[]
        for row in sorted(groups[key],key=lambda r:(-math.inf if r['start'] is None else r['start'],r['id'])):
            start = -math.inf if row['start'] is None else row['start']
            while expiry and expiry[0][0] <= start:
                _,old = heapq.heappop(expiry); del active[old]
            for old in active.values():
                checks += 1
                if semantic_collision(old,row,functional): edges.append(sorted((old['id'],row['id'])))
            active[row['id']] = row
            heapq.heappush(expiry,(math.inf if row['end'] is None else row['end'],row['id']))
    return {'edges':sorted(edges),'staged':staged,'pair_checks':checks,'validated_rows':len(assertions)}
