"""Bounded, opt-in methods with explicit supplied-model assumptions.

Inference/selection functions accept no evaluation labels. No network or graph
persistence is performed. Unsupported structure is staged, never certified.
"""
from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from itertools import product
import math

from ..reliability.methods import (
    canonical, components, exact_lineage, graph_input, lineage_bounds,
    solve_component, validate_proofs,
)


def probability(p):
    if type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1:
        raise ValueError('Finite probability in [0,1] required')
    return float(p)


def source_mixture(proofs, sources, primitives):
    """Marginalize a supplied binary-source model, not inferred source truth."""
    proofs = [tuple(p) for p in proofs]
    if any(not isinstance(k, str) or not k for k in sources):
        raise ValueError('Nonempty string source IDs required')
    for p in sources.values():
        probability(p)
    for row in primitives.values():
        if set(row) != {'source', 'p0', 'p1'} or row['source'] not in sources:
            raise ValueError('Each primitive needs a declared source and p0/p1')
        probability(row['p0']); probability(row['p1'])
    marginal = {a: (1-sources[r['source']])*r['p0']+sources[r['source']]*r['p1']
                for a, r in primitives.items()}
    validate_proofs(proofs, marginal)
    if len(sources) > 8 or len(primitives) > 16:
        return {'lower': 0., 'upper': 1., 'exact': False, 'reason': 'input_cap', 'assignments': 0}
    keys = sorted(sources)
    lower = upper = 0.
    exact = True
    for bits in product((0, 1), repeat=len(keys)):
        state = dict(zip(keys, bits))
        mass = math.prod(sources[s] if state[s] else 1-sources[s] for s in keys)
        conditional = {a: r['p1'] if state[r['source']] else r['p0'] for a, r in primitives.items()}
        value = exact_lineage(proofs, conditional)
        lower += mass*value['lower']; upper += mass*value['upper']
        exact = exact and value['exact']
    return {'lower': min(1., max(0., lower)), 'upper': min(1., max(0., upper)),
            'exact': exact, 'reason': 'exact' if exact else 'conditional_state_cap',
            'assignments': 1 << len(keys)}


@dataclass(frozen=True)
class Diagram:
    """Children precede parents; IDs 0 and 1 are Boolean terminals."""
    proofs: tuple
    atoms: tuple
    nodes: tuple
    root: int | None
    states: int
    reason: str

    def evaluate(self, probabilities):
        validate_proofs(self.proofs, probabilities)
        if set(probabilities) != set(self.atoms):
            raise ValueError('Exactly the compiled primitive set is required')
        if self.root is None:
            bounds = ({'lower': 0., 'upper': 1.} if self.reason == 'input_cap'
                      else lineage_bounds(self.proofs, probabilities))
            return {**bounds, 'exact': False, 'reason': self.reason, 'node_visits': 0}
        values = [0., 1.]
        for atom, low, high in self.nodes:
            p = probabilities[atom]
            values.append((1-p)*values[low]+p*values[high])
        value = min(1., max(0., values[self.root]))
        return {'lower': value, 'upper': value, 'exact': True, 'reason': 'exact',
                'node_visits': len(self.nodes)}


def compile_lineage(proofs, *, state_cap=32768):
    """Iterative state-bounded ROBDD compilation; no atom-count tractability claim."""
    if type(state_cap) is not int or not 1 <= state_cap <= 32768:
        raise ValueError('Residual-state cap must be in [1,32768]')
    original = tuple(tuple(p) for p in proofs)
    if any(not isinstance(a, str) or not a for p in original for a in p):
        raise ValueError('Nonempty string primitive IDs required')
    atoms = tuple(sorted({a for p in original for a in p}))
    validate_proofs(original, {a: .5 for a in atoms})
    if len(atoms) > 512 or len(original) > 4096:
        return Diagram(original, atoms, (), None, 0, 'input_cap')
    terms = canonical(original)
    freq = Counter(a for p in terms for a in p)
    order = {a: i for i, a in enumerate(sorted(atoms, key=lambda a: (-freq[a], a)))}
    values, expansion, unique, nodes = {}, {}, {}, []
    stack = [(terms, False)]
    seen = set()
    while stack:
        dnf, after = stack.pop()
        if dnf in values:
            continue
        if not after:
            if len(seen) >= state_cap:
                return Diagram(terms, atoms, (), None, len(seen), 'state_cap')
            seen.add(dnf)
            if not dnf:
                values[dnf] = 0
                continue
            if () in dnf:
                values[dnf] = 1
                continue
            atom = min({a for p in dnf for a in p}, key=order.__getitem__)
            low = canonical(p for p in dnf if atom not in p)
            high = canonical(tuple(a for a in p if a != atom) for p in dnf)
            expansion[dnf] = (atom, low, high)
            stack.extend([(dnf, True), (high, False), (low, False)])
        else:
            atom, low, high = expansion.pop(dnf)
            lo, hi = values[low], values[high]
            if lo == hi:
                values[dnf] = lo
            else:
                key = (atom, lo, hi)
                if key not in unique:
                    unique[key] = len(nodes)+2
                    nodes.append(key)
                values[dnf] = unique[key]
    return Diagram(terms, atoms, tuple(nodes), values[terms], len(seen), 'exact')


def review_input(candidates, budget):
    if type(budget) is not int or not 0 <= budget <= 160:
        raise ValueError('Integer effort budget in [0,160] required')
    ids = set()
    groups = defaultdict(list)
    for r in candidates:
        if set(r) != {'id', 'group', 'risk', 'cost', 'detect', 'false_remove'}:
            raise ValueError('Review selector accepts only the declared feature fields')
        if not isinstance(r['id'], str) or not r['id'] or r['id'] in ids:
            raise ValueError('Unique nonempty candidate IDs required')
        if not isinstance(r['group'], str) or not r['group']:
            raise ValueError('Nonempty source-group IDs required')
        ids.add(r['id'])
        for k in ('risk', 'detect', 'false_remove'):
            probability(r[k])
        if type(r['cost']) is not int or not 1 <= r['cost'] <= 8:
            raise ValueError('Integer proxy cost in [1,8] required')
        groups[r['group']].append(dict(r))
    return {g: sorted(rows, key=lambda r: r['id']) for g, rows in sorted(groups.items())}


def group_review_gain(rows, selected):
    original_clean = math.prod(1-r['risk'] for r in rows)
    updated_clean = math.prod(1-r['risk']*(1-r['detect']*(r['id'] in selected)) for r in rows)
    good_loss = sum((1-r['risk'])*r['false_remove'] for r in rows if r['id'] in selected)
    return updated_clean-original_clean-good_loss


def review_gain(candidates, selected):
    groups = review_input(candidates, 0)
    return sum(group_review_gain(rows, selected) for rows in groups.values())


def _better(a, b):
    """Choose gain then deterministic ID ordering; costs resolved by caller."""
    return a if a[0] > b[0]+1e-12 or (abs(a[0]-b[0]) <= 1e-12 and a[1] < b[1]) else b


def optimal_review(candidates, budget):
    groups = review_input(candidates, budget)
    dp = {0: (0., ())}
    staged = []
    for g, rows in groups.items():
        options = {0: (0., ())}
        if len(rows) > 12:
            staged.append(g)
        else:
            for mask in range(1, 1 << len(rows)):
                picked = tuple(r['id'] for i, r in enumerate(rows) if mask & (1 << i))
                cost = sum(r['cost'] for i, r in enumerate(rows) if mask & (1 << i))
                if cost <= budget:
                    candidate = (group_review_gain(rows, set(picked)), picked)
                    options[cost] = _better(candidate, options.get(cost, (-math.inf, ())))
        new = {}
        for cost, (gain, selected) in dp.items():
            for extra, (benefit, picked) in options.items():
                if cost+extra <= budget:
                    candidate = (gain+benefit, tuple(sorted(selected+picked)))
                    new[cost+extra] = _better(candidate, new.get(cost+extra, (-math.inf, ())))
        dp = new
    cost, (gain, selected) = min(dp.items(), key=lambda kv: (-round(kv[1][0], 12), kv[0], kv[1][1]))
    return {'selected': list(selected), 'cost': cost, 'modeled_gain': gain, 'staged_groups': staged}


def ratio_review(candidates, budget):
    groups = review_input(candidates, budget)
    selected, spent = set(), 0
    while True:
        choices = []
        for row in candidates:
            if row['id'] in selected or spent+row['cost'] > budget:
                continue
            group = groups[row['group']]
            gain = group_review_gain(group, selected | {row['id']})-group_review_gain(group, selected)
            choices.append((gain/row['cost'], row['id'], row['cost']))
        if not choices:
            break
        gain, key, cost = min(choices, key=lambda x: (-x[0], x[1]))
        if gain <= 1e-12:
            break
        selected.add(key); spent += cost
    return {'selected': sorted(selected), 'cost': spent, 'modeled_gain': review_gain(candidates, selected)}


def packed_review(candidates, budget, order):
    review_input(candidates, budget)
    rows = {r['id']: r for r in candidates}
    if len(order) != len(set(order)) or set(order) != set(rows):
        raise ValueError('Review order must cover exactly the feature candidates')
    selected, cost = set(), 0
    for key in order:
        if cost+rows[key]['cost'] <= budget:
            selected.add(key); cost += rows[key]['cost']
    return {'selected': sorted(selected), 'cost': cost, 'modeled_gain': review_gain(candidates, selected)}


def bipartition(adj):
    color = {}
    for start in sorted(adj):
        if start in color:
            continue
        color[start] = 0
        queue = deque([start])
        while queue:
            a = queue.popleft()
            for b in sorted(adj[a]):
                if b not in color:
                    color[b] = 1-color[a]; queue.append(b)
                elif color[b] == color[a]:
                    return None
    return color


def _network(weights, adj, color):
    keys = sorted(weights)
    index = {k: i for i, k in enumerate(keys)}
    source, sink = len(keys), len(keys)+1
    infinity = sum(weights.values())+1
    arcs = {}
    for key in keys:
        if color[key] == 0:
            arcs[source, index[key]] = weights[key]
            for other in sorted(adj[key]):
                arcs[index[key], index[other]] = infinity
        else:
            arcs[index[key], sink] = weights[key]
    return keys, source, sink, arcs


def bipartite_optimum(weights, edges):
    adj = graph_input(weights, edges)
    color = bipartition(adj)
    if color is None or len(weights) > 512:
        raise ValueError('Bipartite solver requires at most 512 vertices')
    keys, source, sink, arcs = _network(weights, adj, color)
    residual = defaultdict(dict)
    for (a, b), capacity in arcs.items():
        residual[a][b] = capacity; residual[b][a] = 0
    flow, augmentations = 0, 0
    while True:
        parent = {source: None}; queue = deque([source])
        while queue and sink not in parent:
            a = queue.popleft()
            for b in sorted(residual[a]):
                if residual[a][b] > 0 and b not in parent:
                    parent[b] = a; queue.append(b)
        if sink not in parent:
            reachable = set(parent)
            break
        amount = sum(weights.values())+1
        node = sink
        while node != source:
            a = parent[node]; amount = min(amount, residual[a][node]); node = a
        node = sink
        while node != source:
            a = parent[node]; residual[a][node] -= amount; residual[node][a] += amount; node = a
        flow += amount; augmentations += 1
    cover = [k for i, k in enumerate(keys) if (color[k] == 0 and i not in reachable) or (color[k] == 1 and i in reachable)]
    selected = sorted(set(keys)-set(cover))
    certificate = {'keys': keys, 'source': source, 'sink': sink, 'reachable': sorted(reachable),
                   'arcs': [{'u': a, 'v': b, 'capacity': cap, 'flow': cap-residual[a][b]} for (a, b), cap in sorted(arcs.items())],
                   'flow_value': flow, 'cover': cover}
    return {'selected': selected, 'staged': [], 'utility': sum(weights[k] for k in selected),
            'method': 'bipartite_min_cut', 'certificate': certificate, 'augmentations': augmentations}


def verify_certificate(weights, edges, result):
    """Check a primal/dual witness without calling an optimizer or residual BFS."""
    try:
        adj = graph_input(weights, edges)
        color = bipartition(adj)
        if color is None:
            return False
        keys, source, sink, expected = _network(weights, adj, color)
        cert = result['certificate']
        if cert['keys'] != keys or cert['source'] != source or cert['sink'] != sink:
            return False
        arcs = cert['arcs']
        if len(arcs) != len(expected) or {(a['u'], a['v']) for a in arcs} != set(expected):
            return False
        balance = defaultdict(int)
        for a in arcs:
            key, f = (a['u'], a['v']), a['flow']
            if type(f) is not int or a['capacity'] != expected[key] or not 0 <= f <= expected[key]:
                return False
            balance[a['u']] -= f; balance[a['v']] += f
        value = cert['flow_value']
        if type(value) is not int or value < 0 or balance[source] != -value or balance[sink] != value:
            return False
        if any(balance[i] for i in range(len(keys))):
            return False
        reach = set(cert['reachable'])
        if source not in reach or sink in reach or not reach <= set(range(len(keys)+2)):
            return False
        cut = sum(cap for (a, b), cap in expected.items() if a in reach and b not in reach)
        if cut != value:
            return False
        cover = {k for i, k in enumerate(keys) if (color[k] == 0 and i not in reach) or (color[k] == 1 and i in reach)}
        selected = result['selected']
        if set(cert['cover']) != cover or len(selected) != len(set(selected)) or set(selected) != set(keys)-cover:
            return False
        if any(b in selected for a in selected for b in adj[a]):
            return False
        return result['utility'] == sum(weights[k] for k in selected) == sum(weights.values())-value
    except (KeyError, TypeError, ValueError):
        return False


def solve_frontier(weights, edges):
    adj = graph_input(weights, edges)
    solutions = []
    for group in components(adj):
        w = {k: weights[k] for k in sorted(group)}
        sub = {k: adj[k] for k in sorted(group)}
        if len(group) <= 512 and bipartition(sub) is not None:
            e = [(a, b) for a in sorted(sub) for b in sorted(sub[a]) if a < b]
            solutions.append(bipartite_optimum(w, e))
        else:
            solutions.append(solve_component(weights, adj, group))
    return {'selected': sorted(k for s in solutions for k in s['selected']),
            'staged': sorted(k for s in solutions for k in s['staged']),
            'utility': sum(s['utility'] for s in solutions), 'components': solutions}


NEG = -math.inf
IDENTITY = ((0, NEG), (NEG, 0))


def _matrix(weight):
    return ((0, 0), (weight, NEG))


def _compose(right, left):
    return tuple(tuple(max(right[i][k]+left[k][j] for k in (0, 1)) for j in (0, 1)) for i in (0, 1))


class PathOptimizer:
    """Fixed-path utility maintenance; witness materialization is NOT logarithmic."""
    def __init__(self, weights, edges):
        adj = graph_input(weights, edges)
        if not weights or any(len(a) > 2 for a in adj.values()) or len(components(adj)) != 1 or sum(map(len, adj.values())) != 2*(len(weights)-1):
            raise ValueError('A nonempty connected path is required; topology changes require rebuild')
        start = min(k for k in adj if len(adj[k]) <= 1)
        order, prev, node = [], None, start
        while node is not None:
            order.append(node)
            following = sorted(adj[node]-({prev} if prev is not None else set()))
            prev, node = node, following[0] if following else None
        self.order = tuple(order)
        self.index = {k: i for i, k in enumerate(order)}
        self.weights = dict(weights)
        self.size = 1 << (len(order)-1).bit_length()
        self.tree = [IDENTITY]*(2*self.size)
        for i, key in enumerate(order):
            self.tree[self.size+i] = _matrix(weights[key])
        for node in range(self.size-1, 0, -1):
            self.tree[node] = _compose(self.tree[2*node+1], self.tree[2*node])
        self.transitions = 8*(self.size-1)
        self.last_transitions = self.transitions
        self.validation_visits = len(weights)+sum(map(len, adj.values()))
        self.witness_visits = 0

    @property
    def utility(self):
        return max(self.tree[1][0][0], self.tree[1][1][0])

    def update(self, key, weight):
        if key not in self.index or type(weight) is not int or weight < 0:
            raise ValueError('Existing vertex and nonnegative integer weight required')
        self.last_transitions = 0
        if self.weights[key] == weight:
            return self.utility
        node = self.size+self.index[key]
        self.weights[key] = weight
        self.tree[node] = _matrix(weight)
        node //= 2
        while node:
            self.tree[node] = _compose(self.tree[2*node+1], self.tree[2*node])
            self.last_transitions += 8
            node //= 2
        self.transitions += self.last_transitions
        return self.utility

    def selected(self):
        end = 0 if self.tree[1][0][0] >= self.tree[1][1][0] else 1
        stack = [(1, 0, end)]
        result, visits = [], 0
        while stack:
            node, initial, final = stack.pop(); visits += 1
            if node >= self.size:
                index = node-self.size
                if index < len(self.order) and final:
                    result.append(self.order[index])
            else:
                left, right = self.tree[2*node], self.tree[2*node+1]
                middle = max((0, 1), key=lambda k: (right[final][k]+left[k][initial], -k))
                stack.extend([(2*node+1, middle, final), (2*node, initial, middle)])
        self.witness_visits = visits
        return sorted(result)
