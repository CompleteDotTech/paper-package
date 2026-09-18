"""Bounded uncertainty/grounding prototypes with explicit assumption boundaries."""
from __future__ import annotations
from collections import defaultdict, deque
from functools import lru_cache
from itertools import combinations
import math
from typing import Iterable, Mapping

EPS = 1e-8


def identifiers(values: Iterable[str]) -> tuple[str, ...]:
    values = tuple(values)
    if any(not isinstance(x, str) or not x for x in values):
        raise ValueError('Identifiers must be nonempty strings')
    return tuple(sorted(set(values)))


def probabilities(values: Mapping[str, float]) -> dict[str, float]:
    identifiers(values)
    if not values:
        raise ValueError('At least one primitive is required')
    result = {}
    for key in sorted(values):
        x = values[key]
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or not 0 <= x <= 1:
            raise ValueError('Probabilities must be finite numbers in [0,1]')
        result[key] = float(x)
    return result


def dnf(proofs: Iterable[Iterable[str]], atoms: Iterable[str]) -> tuple[tuple[str, ...], ...]:
    known = set(atoms)
    terms = set()
    for proof in proofs:
        if isinstance(proof, str):
            raise ValueError('A proof must be a collection, not a string')
        term = identifiers(proof)
        if not term or not set(term) <= known:
            raise ValueError('Empty proof or unknown primitive')
        terms.add(term)
    ordered = sorted(terms, key=lambda t: (len(t), t))
    minimal = []
    for term in ordered:
        if not any(set(other) <= set(term) for other in minimal):
            minimal.append(term)
    return tuple(minimal)


def holds(proofs: Iterable[Iterable[str]], active: set[str]) -> bool:
    return any(set(term) <= active for term in proofs)


def world_table(p: Mapping[str, float]):
    p = probabilities(p)
    atoms = tuple(p)
    if len(atoms) > 8:
        raise ValueError('World enumeration cap exceeded')
    worlds = [set(a for i, a in enumerate(atoms) if mask & (1 << i)) for mask in range(1 << len(atoms))]
    mass = [math.prod(p[a] if a in world else 1-p[a] for a in atoms) for world in worlds]
    return atoms, worlds, mass


def independent_probability(proofs, p):
    terms = dnf(proofs, p)
    _, worlds, mass = world_table(p)
    return sum(m for w, m in zip(worlds, mass) if holds(terms, w))


def frechet_bounds(proofs, p):
    p = probabilities(p)
    terms = dnf(proofs, p)
    lower = max((max(0.0, sum(p[a] for a in term)-len(term)+1) for term in terms), default=0.0)
    upper = min(1.0, sum(min(p[a] for a in term) for term in terms))
    return {'lower': lower, 'upper': upper, 'mode': 'analytic-dependence-free'}


def credal_bounds(proofs, p):
    """Numerical possible-world LP; dual residual repair plus outward tolerance.

    This is not a formal real-arithmetic certificate. Incorrect marginals remain
    incorrect premises. Atom-cap/solver failures return dependence-free bounds.
    """
    p = probabilities(p)
    terms = dnf(proofs, p)
    fallback = frechet_bounds(terms, p)
    used = sorted({a for term in terms for a in term})
    if not used:
        return {'lower': 0.0, 'upper': 0.0, 'mode': 'constant-false'}
    if len(used) > 8:
        return dict(fallback, reason='atom-cap')
    import numpy as np
    from scipy.optimize import linprog
    worlds = [set(a for i, a in enumerate(used) if mask & (1 << i)) for mask in range(1 << len(used))]
    A = np.array([[1.0]*len(worlds)] + [[float(a in w) for w in worlds] for a in used])
    b = np.array([1.0]+[p[a] for a in used])
    c = np.array([float(holds(terms, w)) for w in worlds])
    try:
        answers = [linprog(obj, A_eq=A, b_eq=b, bounds=(0, None), method='highs') for obj in (c, -c)]
        if any(not ans.success or not np.all(np.isfinite(ans.x)) for ans in answers):
            return dict(fallback, reason='solver-status')
        residual = max(float(np.max(np.abs(A@ans.x-b))) for ans in answers)
        if residual > EPS or any(float(np.min(ans.x)) < -EPS for ans in answers):
            return dict(fallback, reason='solver-residual')
        dual_bounds = []
        for obj, ans in zip((c, -c), answers):
            y = np.asarray(ans.eqlin.marginals)
            if not np.all(np.isfinite(y)):
                return dict(fallback, reason='invalid-dual')
            # Normalization fixes total mass to one, so subtracting the largest
            # dual constraint violation repairs its objective bound.
            violation = max(0.0, float(np.max(A.T@y-obj)))
            dual_bounds.append(float(b@y)-violation-EPS)
        lower = max(fallback['lower'], dual_bounds[0], 0.0)
        upper = min(fallback['upper'], -dual_bounds[1], 1.0)
        if lower > upper:
            return dict(fallback, reason='inconsistent-numerical-bounds')
        return {'lower': lower, 'upper': upper, 'mode': 'numerical-LP',
                'raw_lower': float(answers[0].fun), 'raw_upper': -float(answers[1].fun),
                'primal_residual': residual, 'worlds': len(worlds)}
    except (ValueError, RuntimeError, ArithmeticError):
        return dict(fallback, reason='solver-exception')


def graph_input(weights, edges):
    nodes = identifiers(weights)
    if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in weights.values()):
        raise ValueError('Priorities must be nonnegative integers')
    adjacency = {x: set() for x in nodes}
    for edge in edges:
        if isinstance(edge, str) or len(edge) != 2:
            raise ValueError('Each conflict has two endpoints')
        a, b = edge
        if a not in adjacency or b not in adjacency or a == b:
            raise ValueError('Unknown endpoint or self-conflict')
        adjacency[a].add(b); adjacency[b].add(a)
    return nodes, adjacency


def skeptical_repair(weights, edges):
    """All-optima backbone on <=16-vertex connected components, otherwise stage."""
    nodes, adj = graph_input(weights, edges)
    remaining = set(nodes)
    components = []
    while remaining:
        component = set(); stack = [min(remaining)]
        while stack:
            v = stack.pop()
            if v not in component:
                component.add(v); stack.extend(sorted(adj[v]-component, reverse=True))
        remaining -= component; components.append(sorted(component))
    selected, necessary, possible, excluded, staged = [], [], [], [], []
    witnesses = {}; total = 0; states = 0
    for comp in components:
        if len(comp) > 16:
            staged.extend(comp); continue
        n = len(comp); index = {a: i for i, a in enumerate(comp)}
        masks = [sum(1 << index[b] for b in adj[a]) for a in comp]
        @lru_cache(None)
        def optimum(mask):
            if not mask:
                return 0, ()
            bit = mask & -mask; i = bit.bit_length()-1
            score0, set0 = optimum(mask ^ bit)
            score1, set1 = optimum(mask & ~bit & ~masks[i])
            score1 += weights[comp[i]]; set1 = tuple(sorted(set1+(comp[i],)))
            if score1 > score0 or (score1 == score0 and set1 < set0):
                return score1, set1
            return score0, set0
        full = (1 << n)-1
        best, chosen = optimum(full); total += best; selected.extend(chosen)
        for i, node in enumerate(comp):
            without, witness0 = optimum(full & ~(1 << i))
            inc, witness1 = optimum(full & ~(1 << i) & ~masks[i])
            inc += weights[node]; witness1 = tuple(sorted(witness1+(node,)))
            if inc == best:
                possible.append(node)
            else:
                excluded.append(node)
            if without < best:
                necessary.append(node)
            elif inc == best:
                witnesses[node] = {'component': comp, 'include': list(witness1), 'exclude': list(witness0)}
        states += optimum.cache_info().currsize
    for entry in witnesses.values():
        outside = set(selected)-set(entry['component'])
        entry['include'] = sorted(outside | set(entry['include']))
        entry['exclude'] = sorted(outside | set(entry['exclude']))
    return {'selected': sorted(selected), 'necessary': sorted(necessary), 'possible': sorted(possible),
            'excluded': sorted(excluded), 'staged': sorted(staged), 'witnesses': witnesses,
            'utility': None if staged else total, 'solved_utility': total, 'states': states}


def query_loss(queries, p, reviewed):
    """Sum of expected conditional variances under supplied independent inputs."""
    atoms, worlds, mass = world_table(p)
    terms = [dnf(q, atoms) for q in queries]
    reviewed = identifiers(reviewed)
    if not set(reviewed) <= set(atoms):
        raise ValueError('Review contains unknown atoms')
    groups = {}
    for world, m in zip(worlds, mass):
        observation = tuple(a in world for a in reviewed)
        entry = groups.setdefault(observation, [0.0, [0.0]*len(terms)])
        entry[0] += m
        for j, query in enumerate(terms):
            entry[1][j] += m*holds(query, world)
    return max(0.0, sum(s-s*s/m for m, sums in groups.values() if m > 0 for s in sums))


def review_plan(queries, p, budget):
    p = probabilities(p)
    if len(p) > 8 or isinstance(budget, bool) or not isinstance(budget, int) or not 0 <= budget <= len(p):
        raise ValueError('Unsupported atom count or review budget')
    terms = [dnf(q, p) for q in queries]
    scores = [{'reviewed': list(subset), 'loss': query_loss(terms, p, subset)}
              for subset in combinations(sorted(p), budget)]
    best = min(scores, key=lambda x: (round(x['loss'], 12), x['reviewed']))
    return dict(best, candidates=scores)


def retraction_input(facts, target, protected, costs):
    atoms = identifiers(costs)
    if not atoms or any(isinstance(x, bool) or not isinstance(x, int) or x <= 0 for x in costs.values()):
        raise ValueError('Withdrawal costs must be positive integers')
    identifiers(facts); protected = identifiers(protected)
    if target not in facts or not set(protected) <= set(facts):
        raise ValueError('Unknown target or protected conclusion')
    terms = {f: dnf(proof, atoms) for f, proof in facts.items()}
    if any(not proof for proof in terms.values()):
        raise ValueError('Every supplied conclusion must initially have a proof')
    return atoms, terms, protected


def retraction_plan(facts, target, protected, costs):
    """Propose staging candidate commitments, never delete underlying evidence."""
    atoms, terms, protected = retraction_input(facts, target, protected, costs)
    if len(atoms) > 14:
        return {'status': 'staged-cap', 'removed': None}
    best = None; best_removed = None; seen = set()
    def search(removed):
        nonlocal best, best_removed
        key = tuple(sorted(removed))
        if key in seen:
            return
        seen.add(key)
        active = set(atoms)-removed
        if any(not holds(terms[f], active) for f in protected):
            return
        lost = sorted(f for f in terms if f != target and f not in protected and not holds(terms[f], active))
        cost = sum(costs[a] for a in removed)
        if best is not None and (len(lost), cost) > best[:2]:
            return
        unhit = [term for term in terms[target] if not set(term) & removed]
        if not unhit:
            objective = (len(lost), cost, len(removed), key)
            if best is None or objective < best:
                best, best_removed = objective, key
            return
        for atom in min(unhit, key=lambda term: (len(term), term)):
            search(removed | {atom})
    search(set())
    if best is None:
        return {'status': 'infeasible', 'removed': None, 'states': len(seen)}
    return {'status': 'exact', 'removed': list(best_removed), 'collateral': best[0],
            'cost': best[1], 'count': best[2], 'states': len(seen)}


def horn_input(bases, rules):
    base = set(identifiers(bases)); canonical = set()
    for head, body in rules:
        identifiers([head])
        if isinstance(body, str):
            raise ValueError('Rule body must be a collection')
        body = identifiers(body)
        if not body:
            raise ValueError('Use explicit base assertions, not empty rule bodies')
        canonical.add((head, body))
    return base, sorted(canonical)


def grounded(bases, rules):
    """Least fixed point of finite ground positive rules using grounded events."""
    base, rules = horn_input(bases, rules)
    active = set(base); queue = deque(sorted(base)); consumers = defaultdict(list)
    remaining = []
    for i, (_, body) in enumerate(rules):
        remaining.append(len(body))
        for atom in body:
            consumers[atom].append(i)
    visits = 0; witnesses = {}
    while queue:
        atom = queue.popleft()
        for i in consumers[atom]:
            visits += 1; remaining[i] -= 1
            head, body = rules[i]
            if remaining[i] == 0 and head not in active:
                active.add(head); witnesses[head] = list(body); queue.append(head)
    return {'active': sorted(active), 'body_visits': visits, 'witnesses': witnesses,
            'body_incidences': sum(len(body) for _, body in rules)}


def support_prune(previous, bases, rules):
    """Deliberately naive comparator: local support can retain unfounded cycles."""
    base, rules = horn_input(bases, rules)
    active = set(previous) | base
    while True:
        supported = base | {head for head, body in rules if set(body) <= active}
        remove = active-supported
        if not remove:
            return sorted(active)
        active -= remove
