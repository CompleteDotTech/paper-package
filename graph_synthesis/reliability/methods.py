"""Opt-in, bounded research methods. No service requests or production writes."""
from __future__ import annotations
from collections import defaultdict, deque
from functools import lru_cache
import math

POSITIVE = frozenset({'SUPPORTS', 'REFUTES'})


def small_key(row):
    base = row['views']['base1']
    return base['label'], bool(base['score'] is not None and base['score'] >= .90)


def fit_small(development):
    if not development or any(r['split'] != 'development' for r in development):
        raise ValueError('Nonempty development-only fit required')
    accepted = [r for r in development if r['views']['base1']['label'] in POSITIVE]
    prior = (1 + sum(r['views']['base1']['label'] != r['gold'] for r in accepted))/(len(accepted)+2)
    counts = defaultdict(lambda: [0, 0])
    for row in accepted:
        counts[small_key(row)][0] += row['views']['base1']['label'] != row['gold']
        counts[small_key(row)][1] += 1
    return {'prior': prior, 'bins': {repr(k): {'wrong': w, 'n': n, 'risk': (w+2*prior)/(n+2)}
                                    for k, (w, n) in sorted(counts.items())}}


def assign_small(features, fit):
    return [{'id': r['id'], 'group': r['group'],
             'risk': fit['bins'].get(repr(small_key(r)), {}).get('risk', fit['prior'])}
            for r in features if r['views']['base1']['label'] in POSITIVE]


def group_risks(candidates, multiplier=1.):
    if not math.isfinite(multiplier) or multiplier <= 0:
        raise ValueError('Positive finite risk multiplier required')
    grouped = defaultdict(list)
    for row in candidates:
        p = row['risk']
        if type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1:
            raise ValueError('Finite risk in [0,1] required')
        grouped[row['group']].append(p)
    return {g: 1-math.prod(1-p for p in ps)**multiplier for g, ps in sorted(grouped.items())}


def canonical(proofs):
    """Canonical monotone DNF, removing duplicates and redundant supersets."""
    unique = sorted({tuple(sorted(set(p))) for p in proofs}, key=lambda p: (len(p), p))
    kept = []
    for proof in unique:
        if not any(set(old).issubset(proof) for old in kept):
            kept.append(proof)
    return tuple(sorted(kept))


def proof_components(proofs):
    todo = set(proofs)
    result = []
    while todo:
        start = min(todo)
        todo.remove(start)
        group, atoms = [start], set(start)
        while True:
            linked = {p for p in todo if atoms.intersection(p)}
            if not linked:
                break
            todo -= linked
            group.extend(sorted(linked))
            atoms.update(a for p in linked for a in p)
        result.append(tuple(sorted(group)))
    return result


def validate_proofs(proofs, probabilities):
    if any(not isinstance(a, str) or not a for a in probabilities):
        raise ValueError('Nonempty string primitive IDs required')
    if any(type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1 for p in probabilities.values()):
        raise ValueError('Finite primitive probabilities in [0,1] required')
    if any(not p or any(not isinstance(a, str) or a not in probabilities for a in p) for p in proofs):
        raise ValueError('Nonempty proofs over declared primitives required')


def lineage_bounds(proofs, probabilities):
    """Duplicate-only shared-component bounds used as the earlier comparator."""
    validate_proofs(proofs, probabilities)
    unique = tuple(sorted({tuple(sorted(set(p))) for p in proofs}))
    bounds = []
    for group in proof_components(unique):
        values = [math.prod(probabilities[a] for a in p) for p in group]
        bounds.append((max(values), min(1., sum(values))))
    return {'lower': 1-math.prod(1-lo for lo, hi in bounds),
            'upper': 1-math.prod(1-hi for lo, hi in bounds)}


class _BudgetExceeded(Exception):
    pass


def exact_lineage(proofs, probabilities, *, atom_cap=16, state_cap=32768):
    """Shannon-expand small components; never certify a truncated result."""
    validate_proofs(proofs, probabilities)
    if type(atom_cap) is not int or not 1 <= atom_cap <= 16 or type(state_cap) is not int or not 1 <= state_cap <= 32768:
        raise ValueError('Caps exceed the frozen safety bounds')
    outputs = []
    for group in proof_components(canonical(proofs)):
        atoms = {a for p in group for a in p}
        states = 0
        @lru_cache(maxsize=None)
        def visit(dnf):
            nonlocal states
            if states >= state_cap:
                raise _BudgetExceeded
            states += 1
            if not dnf:
                return 0.
            if () in dnf:
                return 1.
            frequencies = defaultdict(int)
            for term in dnf:
                for a in term:
                    frequencies[a] += 1
            atom = min(frequencies, key=lambda a: (-frequencies[a], a))
            yes = canonical(tuple(a for a in p if a != atom) for p in dnf)
            no = canonical(p for p in dnf if atom not in p)
            value = probabilities[atom]*visit(yes)+(1-probabilities[atom])*visit(no)
            return min(1., max(0., value))
        exact, reason = False, 'atom_cap'
        if len(atoms) <= atom_cap:
            try:
                probability = visit(group)
                exact, reason = True, 'exact'
            except _BudgetExceeded:
                reason = 'state_cap'
        if exact:
            lower = upper = probability
        else:
            fallback = lineage_bounds(group, probabilities)
            lower, upper = fallback['lower'], fallback['upper']
        outputs.append({'atoms': len(atoms), 'proofs': len(group), 'lower': lower, 'upper': upper,
                        'states': states, 'exact': exact, 'reason': reason})
    return {'lower': 1-math.prod(1-g['lower'] for g in outputs),
            'upper': 1-math.prod(1-g['upper'] for g in outputs),
            'exact': all(g['exact'] for g in outputs), 'components': outputs,
            'states': sum(g['states'] for g in outputs)}


def graph_input(weights, edges):
    if any(not isinstance(k, str) or not k for k in weights):
        raise ValueError('Unique nonempty string vertex IDs required')
    if any(type(w) is not int or w < 0 for w in weights.values()):
        raise ValueError('Nonnegative integer priorities required')
    adj = {k: set() for k in weights}
    for edge in edges:
        if len(edge) != 2:
            raise ValueError('Each edge must have two endpoints')
        a, b = edge
        if a not in adj or b not in adj or a == b:
            raise ValueError('Unknown endpoint or self conflict')
        adj[a].add(b)
        adj[b].add(a)
    return {k: frozenset(adj[k]) for k in sorted(adj)}


def components(adj):
    todo = set(adj)
    groups = []
    while todo:
        root = min(todo)
        todo.remove(root)
        group, stack = {root}, [root]
        while stack:
            node = stack.pop()
            new = todo.intersection(adj[node])
            todo -= new
            group |= new
            stack.extend(sorted(new))
        groups.append(frozenset(group))
    return groups


def choose(a, b):
    return a if a[0] > b[0] or (a[0] == b[0] and a[1] < b[1]) else b


def combine(items):
    items = list(items)
    return sum(item[0] for item in items), tuple(sorted(k for item in items for k in item[1]))


def core_nodes(adj, nodes):
    remaining = set(nodes)
    degree = {k: len(adj[k].intersection(remaining)) for k in remaining}
    queue = deque(sorted(k for k in remaining if degree[k] <= 1))
    while queue:
        k = queue.popleft()
        if k not in remaining:
            continue
        remaining.remove(k)
        for other in sorted(adj[k].intersection(remaining)):
            degree[other] -= 1
            if degree[other] == 1:
                queue.append(other)
    return remaining


def cutset(adj, group, cap):
    remaining, removed = set(group), []
    while True:
        core = core_nodes(adj, remaining)
        if not core:
            return tuple(removed)
        if len(removed) >= cap:
            return None
        node = min(core, key=lambda k: (-len(adj[k].intersection(core)), k))
        remaining.remove(node)
        removed.append(node)


def forest_optimum(weights, adj, nodes):
    nodes = set(nodes)
    if core_nodes(adj, nodes):
        raise ValueError('Forest solver received a cycle')
    unseen = set(nodes)
    answers = []
    while unseen:
        root = min(unseen)
        parent, order = {root: None}, [root]
        unseen.remove(root)
        for node in order:
            for child in sorted(adj[node].intersection(unseen)):
                parent[child] = node
                unseen.remove(child)
                order.append(child)
        table = {}
        for node in reversed(order):
            children = [k for k in adj[node].intersection(nodes) if parent.get(k) == node]
            yes = combine([(weights[node], (node,))]+[table[k][0] for k in sorted(children)])
            no = combine(choose(*table[k]) for k in sorted(children))
            table[node] = (no, yes)
        answers.append(choose(*table[root]))
    return combine(answers)


def exhaustive_optimum(weights, adj, group):
    keys = sorted(group)
    if len(keys) > 16:
        raise ValueError('Exhaustive component limit exceeded')
    pairmasks = [(1 << i) | (1 << j) for i, a in enumerate(keys) for j, b in enumerate(keys) if i < j and b in adj[a]]
    best = (0, ())
    for mask in range(1 << len(keys)):
        if any(mask & p == p for p in pairmasks):
            continue
        selected = tuple(k for i, k in enumerate(keys) if mask & (1 << i))
        best = choose(best, (sum(weights[k] for k in selected), selected))
    return best


def solve_component(weights, adj, group, max_cut=4):
    if len(group) > 256:
        return {'selected': [], 'staged': sorted(group), 'utility': 0, 'method': 'size_staged', 'cutset': []}
    cut = cutset(adj, group, max_cut)
    if cut is None:
        if len(group) > 16:
            return {'selected': [], 'staged': sorted(group), 'utility': 0, 'method': 'cutset_staged', 'cutset': []}
        best = exhaustive_optimum(weights, adj, group)
        method = 'enumeration'
    else:
        best = (0, ())
        for mask in range(1 << len(cut)):
            picked = tuple(sorted(k for i, k in enumerate(cut) if mask & (1 << i)))
            if any(b in adj[a] for i, a in enumerate(picked) for b in picked[i+1:]):
                continue
            excluded = set(cut)
            for node in picked:
                excluded.update(adj[node])
            forest = forest_optimum(weights, adj, set(group)-excluded)
            best = choose(best, combine([(sum(weights[k] for k in picked), picked), forest]))
        method = 'cutset' if cut else 'forest'
    return {'selected': list(best[1]), 'staged': [], 'utility': best[0], 'method': method, 'cutset': list(cut or ())}


def aggregate(solutions):
    solutions = list(solutions)
    return {'selected': sorted(k for s in solutions for k in s['selected']),
            'staged': sorted(k for s in solutions for k in s['staged']),
            'utility': sum(s['utility'] for s in solutions)}


def solve_graph(weights, edges, *, max_cut=4):
    if type(max_cut) is not int or not 0 <= max_cut <= 4:
        raise ValueError('Cycle cut cap must be an integer in [0,4]')
    adj = graph_input(weights, edges)
    solutions = [solve_component(weights, adj, group, max_cut) for group in components(adj)]
    return {**aggregate(solutions), 'components': solutions}


class IncrementalSolver:
    """Validate/detect changes globally; reuse only identical component states."""
    def __init__(self, weights, edges):
        self.weights, self.adj, self.cache = {}, {}, {}
        self.solver_vertices = 0
        self.update(weights, edges)

    def update(self, weights, edges):
        adj = graph_input(weights, edges)  # Validate before altering any stored state.
        cache, visits = {}, 0
        for group in components(adj):
            unchanged = group in self.cache and all(self.weights.get(k) == weights[k] and self.adj.get(k) == adj[k] for k in group)
            if unchanged:
                cache[group] = self.cache[group]
            else:
                cache[group] = solve_component(weights, adj, group)
                visits += len(group)
        self.weights, self.adj, self.cache = dict(weights), adj, cache
        self.solver_vertices = visits
        return aggregate(cache.values())
