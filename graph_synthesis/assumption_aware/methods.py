"""Bounded research algorithms. No inference requests, network access or graph writes."""
from __future__ import annotations
from collections import defaultdict, deque
import math
from typing import Mapping, Sequence


def canonical(proofs):
    items = sorted({tuple(sorted(set(p))) for p in proofs}, key=lambda p: (len(p), p))
    return tuple(p for i, p in enumerate(items) if not any(set(q) <= set(p) for q in items[:i]))


def probability_input(proofs, marginals, pairs=()):
    if any(not isinstance(k, str) or not k for k in marginals):
        raise ValueError('Nonempty string primitive IDs required')
    if any(type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1 for p in marginals.values()):
        raise ValueError('Finite primitive marginals in [0,1] required')
    proofs = canonical(proofs)
    if any(a not in marginals for p in proofs for a in p):
        raise ValueError('Unknown proof primitive')
    checked = {}
    for a, b, p in pairs:
        if a == b or a not in marginals or b not in marginals:
            raise ValueError('Distinct known pair endpoints required')
        if type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1:
            raise ValueError('Finite pair probability in [0,1] required')
        key = tuple(sorted((a, b)))
        if key in checked and checked[key] != p:
            raise ValueError('Contradictory duplicate pair constraint')
        checked[key] = float(p)
    return proofs, [(a, b, p) for (a, b), p in sorted(checked.items())]


def frechet(proofs, marginals):
    proofs, _ = probability_input(proofs, marginals)
    if not proofs:
        return {'lower': 0., 'upper': 0.}
    lows = [max(0., sum(marginals[a] for a in p)-len(p)+1) for p in proofs]
    highs = [min((marginals[a] for a in p), default=1.) for p in proofs]
    return {'lower': max(lows), 'upper': min(1., sum(highs))}


def lineage_envelope(proofs, marginals, pairs=(), *, atom_cap=8, maxiter=10000):
    """Numerically verified dual bounds, NOT an exact-arithmetic safety certificate.

    Normalization permits correcting a dual inequality residual by subtracting
    its maximum from the normalization multiplier. Failed verification stages.
    """
    import numpy as np
    from scipy.optimize import linprog
    if type(atom_cap) is not int or not 0 <= atom_cap <= 8 or type(maxiter) is not int or maxiter < 1:
        raise ValueError('Bounded nonnegative atom cap and positive iteration cap required')
    proofs, pairs = probability_input(proofs, marginals, pairs)
    fallback = frechet(proofs, marginals)
    atoms = sorted(marginals)
    if len(atoms) > atom_cap:
        return {**fallback, 'status': 'atom_cap', 'optimized': False, 'worlds': 0}
    worlds = np.asarray([[int(bool(mask & (1 << i))) for i in range(len(atoms))]
                         for mask in range(1 << len(atoms))], dtype=float)
    position = {a: i for i, a in enumerate(atoms)}
    matrix = [np.ones(len(worlds)), *[worlds[:, i] for i in range(len(atoms))]]
    rhs = [1., *[marginals[a] for a in atoms]]
    for a, b, p in pairs:
        matrix.append(worlds[:, position[a]] * worlds[:, position[b]])
        rhs.append(p)
    matrix, rhs = np.asarray(matrix), np.asarray(rhs)
    event = np.asarray([int(any(all(row[position[a]] for a in p) for p in proofs)) for row in worlds], dtype=float)
    bounds, residuals, witnesses = [], [], []
    for objective in (event, -event):
        fit = linprog(objective, A_eq=matrix, b_eq=rhs, bounds=(0, None), method='highs',
                      options={'maxiter': maxiter, 'primal_feasibility_tolerance': 1e-9, 'dual_feasibility_tolerance': 1e-9})
        if not fit.success:
            return {'lower': 0., 'upper': 1., 'status': 'infeasible_or_solver_limit', 'optimized': False, 'worlds': len(worlds)}
        primal = max(float(np.max(np.abs(matrix @ fit.x-rhs))), max(0., -float(min(fit.x))))
        dual = np.asarray(fit.eqlin.marginals)
        violation = max(0., float(np.max(matrix.T @ dual-objective)))
        certified = float(rhs @ dual)-violation-2e-8
        gap = float(objective @ fit.x)-certified
        if primal > 1e-7 or gap < -1e-7 or gap > 1e-6 or not math.isfinite(certified):
            return {'lower': 0., 'upper': 1., 'status': 'verification_failed', 'optimized': False, 'worlds': len(worlds)}
        bounds.append(certified)
        residuals.append({'primal': round(primal, 12), 'dual': round(violation, 12), 'gap': round(gap, 10)})
        witnesses.append([round(float(x), 10) for x in fit.x])
    low, high = max(fallback['lower'], bounds[0], 0.), min(fallback['upper'], -bounds[1], 1.)
    if low > high+1e-7:
        return {'lower': 0., 'upper': 1., 'status': 'verification_failed', 'optimized': False, 'worlds': len(worlds)}
    return {'lower': low, 'upper': high, 'status': 'numerically_verified', 'optimized': True,
            'worlds': len(worlds), 'residuals': residuals, 'witnesses': witnesses}


def invariant_repairs(weights, edges, queries=(), *, call_cap=1024, vertex_cap=1024):
    """Certificates concern *all maximum-priority repairs*, not factual truth."""
    from ..reliability.methods import graph_input, solve_graph
    if type(call_cap) is not int or not 1 <= call_cap <= 1024 or type(vertex_cap) is not int or not 1 <= vertex_cap <= 1024:
        raise ValueError('Positive bounded resource caps required')
    edges = list(edges)
    graph_input(weights, edges)
    queries = [(kind, tuple(sorted(set(members)))) for kind, members in queries]
    if any(kind not in ('OR', 'AND') or any(k not in weights for k in members) for kind, members in queries):
        raise ValueError('Known query kind and vertices required')
    unknown = {'status': 'unknown', 'forced': [], 'selected': [], 'utility': None,
               'queries': [None]*len(queries), 'oracle_calls': 0}
    if len(weights) > vertex_cap:
        return unknown
    count = 0
    def solve(forbidden):
        nonlocal count
        if count >= call_cap:
            return None
        count += 1
        kept = {k: w for k, w in weights.items() if k not in forbidden}
        result = solve_graph(kept, [e for e in edges if all(k in kept for k in e)])
        return None if result['staged'] else result
    base = solve(set())
    if base is None:
        return {**unknown, 'oracle_calls': count}
    forced, complete = set(), True
    for key in base['selected']:
        other = solve({key})
        if other is None:
            complete = False
        elif other['utility'] < base['utility']:
            forced.add(key)
    answers = []
    for kind, members in queries:
        if kind == 'AND':
            answers.append(True if set(members) <= forced else False if complete else None)
        else:
            other = solve(set(members))
            answers.append(None if other is None else other['utility'] < base['utility'])
    return {'status': 'complete' if complete and None not in answers else 'partial',
            'forced': sorted(forced), 'selected': base['selected'], 'utility': base['utility'],
            'queries': answers, 'oracle_calls': count}


def exposure_order(candidates: Sequence[Mapping], exposures: Mapping[str, float]) -> list[str]:
    """Same group-product gain and ID tie rule as PR #17, weighted by exposure."""
    if len({r['id'] for r in candidates}) != len(candidates):
        raise ValueError('Unique review IDs required')
    for row in candidates:
        p, w = row['risk'], exposures.get(row['group'])
        if type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1:
            raise ValueError('Invalid review risk')
        if type(w) not in (int, float) or not math.isfinite(w) or w <= 0:
            raise ValueError('Positive finite exposure for each group required')
    todo, order = {r['id']: r for r in candidates}, []
    while todo:
        def gain(row):
            return exposures[row['group']]*row['risk']*math.prod(1-r['risk'] for r in todo.values()
                       if r['group'] == row['group'] and r['id'] != row['id'])
        winner = min(todo, key=lambda key: (-gain(todo[key]), key))
        order.append(winner)
        del todo[winner]
    return order


class DeltaTree:
    """Fixed validated tree; O(height) weight updates and O(n) reconstruction."""
    def __init__(self, weights, edges):
        from ..reliability.methods import graph_input
        self.weights = dict(weights)
        adj = graph_input(weights, edges)
        if not 1 <= len(adj) <= 4096 or sum(map(len, adj.values())) != 2*(len(adj)-1):
            raise ValueError('A nonempty tree of at most 4096 vertices is required')
        self.root = min(adj)
        self.parent, self.order = {self.root: None}, [self.root]
        self.children = {k: [] for k in adj}
        for key in self.order:
            for child in sorted(adj[key]):
                if child == self.parent[key]:
                    continue
                if child in self.parent:
                    raise ValueError('Cycle')
                self.parent[child] = key
                self.children[key].append(child)
                self.order.append(child)
        if len(self.order) != len(adj):
            raise ValueError('Disconnected tree')
        self.inc, self.exc, self.sum_exc, self.sum_best = {}, {}, {}, {}
        for key in reversed(self.order):
            self.sum_exc[key] = sum(self.exc[c] for c in self.children[key])
            self.sum_best[key] = sum(max(self.inc[c], self.exc[c]) for c in self.children[key])
            self.inc[key] = weights[key]+self.sum_exc[key]
            self.exc[key] = self.sum_best[key]
        self.visits = self.messages = len(weights)
        self.reconstruction_visits = 0

    @property
    def utility(self):
        return max(self.inc[self.root], self.exc[self.root])

    def update(self, key, weight):
        if key not in self.weights or type(weight) is not int or weight < 0:
            raise ValueError('Known vertex and nonnegative integer weight required')
        self.visits = self.messages = 0
        if self.weights[key] == weight:
            return self.utility
        self.weights[key] = weight
        while key is not None:
            self.visits += 1
            old = self.inc[key], self.exc[key]
            new = self.weights[key]+self.sum_exc[key], self.sum_best[key]
            if new == old:
                break
            self.messages += 1
            self.inc[key], self.exc[key] = new
            parent = self.parent[key]
            if parent is not None:
                self.sum_exc[parent] += new[1]-old[1]
                self.sum_best[parent] += max(new)-max(old)
            key = parent
        return self.utility

    def change_structure(self, *args, **kwargs):
        raise ValueError('Structural updates are unsupported; build a newly validated tree')

    def selected(self):
        selected, stack = set(), [(self.root, False)]
        self.reconstruction_visits = 0
        while stack:
            key, blocked = stack.pop()
            self.reconstruction_visits += 1
            take = not blocked and self.inc[key] > self.exc[key]
            if take:
                selected.add(key)
            stack.extend((c, take) for c in self.children[key])
        return sorted(selected)


class GroundedRules:
    """Ground positive Horn closure from external facts, never old derived facts."""
    def __init__(self, facts, rules):
        if isinstance(facts, str):
            raise ValueError('Fact universe must be a collection')
        self.facts = frozenset(facts)
        if len(self.facts) > 4096 or any(not isinstance(k, str) or not k for k in self.facts):
            raise ValueError('At most 4096 nonempty fact IDs required')
        self.rules, seen = [], set()
        for head, body in rules:
            if isinstance(body, str):
                raise ValueError('Body must be a collection of fact IDs')
            body = frozenset(body)
            if head not in self.facts or not body <= self.facts:
                raise ValueError('Unknown rule fact')
            item = (head, tuple(sorted(body)))
            if item not in seen:
                self.rules.append(item)
                seen.add(item)
            if len(self.rules) > 8192:
                raise ValueError('Rule cap exceeded')
        self.index = defaultdict(list)
        self.index_inspections = sum(len(body) for _, body in self.rules)
        if self.index_inspections > 65536:
            raise ValueError('Dependency cap exceeded')
        for i, (_, body) in enumerate(self.rules):
            for fact in body:
                self.index[fact].append(i)
        self.current = frozenset()
        self.external = frozenset()

    def update(self, external):
        if isinstance(external, str):
            raise ValueError('External facts must be a collection')
        external = frozenset(external)
        if not external <= self.facts:
            raise ValueError('Unknown external fact')
        # Validate first; a failed update cannot alter any stored state.
        grounded = set(external)
        remaining = [len(body) for _, body in self.rules]
        for i, (head, _) in enumerate(self.rules):
            if remaining[i] == 0:
                grounded.add(head)
        todo = deque(sorted(grounded))
        inspections = activations = 0
        while todo:
            fact = todo.popleft()
            for i in self.index[fact]:
                inspections += 1
                remaining[i] -= 1
                if remaining[i] == 0:
                    activations += 1
                    head = self.rules[i][0]
                    if head not in grounded:
                        grounded.add(head)
                        todo.append(head)
        result = {'closure': sorted(grounded), 'added': sorted(grounded-self.current),
                  'removed': sorted(self.current-grounded), 'dependency_inspections': inspections,
                  'rule_activations': activations, 'counter_initializations': len(remaining)}
        self.current, self.external = frozenset(grounded), external
        return result
