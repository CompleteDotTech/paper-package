"""Bounded research methods, with gold-free inference and explicit fallbacks."""
from __future__ import annotations
from collections import ChainMap, defaultdict, deque
from copy import deepcopy
import math

from ..reliability.methods import (POSITIVE, canonical, exact_lineage, graph_input,
                                   components, solve_component, aggregate)


def probability(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError('Finite probability in [0,1] required')
    return value


def group_features(rows):
    grouped = defaultdict(list)
    for row in rows:
        base = row['views']['base1']
        if base['label'] in POSITIVE:
            grouped[row['group']].append(base)
    return {g: (int(len(items) >= 2), int(any(x['score'] is None or x['score'] < .90 for x in items)))
            for g, items in sorted(grouped.items())}


def source_truth(rows):
    truth = {}
    for row in rows:
        label = row['views']['base1']['label']
        if label in POSITIVE:
            truth[row['group']] = max(truth.get(row['group'], 0), int(label != row['gold']))
    return truth


def fit_source(rows, alpha):
    if not rows or any(r['split'] != 'development' for r in rows) or type(alpha) is not int or alpha not in (1, 4, 16):
        raise ValueError('Development-only fit and frozen shrinkage required')
    features, truth = group_features(rows), source_truth(rows)
    prior = (1 + sum(truth.values())) / (2 + len(truth))
    counts = defaultdict(lambda: [0, 0])
    for group, key in features.items():
        counts[key][0] += truth[group]
        counts[key][1] += 1
    return {'alpha': alpha, 'prior': prior, 'fit_groups': sorted({r['group'] for r in rows}),
            'accepted_groups': len(truth), 'cells': {repr(k): {'wrong': w, 'n': n,
            'risk': (w + alpha * prior) / (n + alpha)} for k, (w, n) in sorted(counts.items())}}


def predict_source(rows, fit):
    if any('gold' in row for row in rows):
        raise ValueError('Inference must not receive gold labels')
    return {g: fit['cells'].get(repr(key), {}).get('risk', fit['prior'])
            for g, key in group_features(rows).items()}


def validate_risks(rows):
    ids = set()
    for row in rows:
        if row['id'] in ids:
            raise ValueError('Duplicate review candidate')
        ids.add(row['id'])
        probability(row['risk'])


def review_options(rows, setup, sensitivity):
    validate_risks(rows)
    if type(setup) is not int or setup < 0:
        raise ValueError('Nonnegative integer source setup required')
    probability(sensitivity)
    groups = defaultdict(list)
    for row in rows:
        groups[row['group']].append(row)
    options = {}
    for group, items in sorted(groups.items()):
        items.sort(key=lambda r: (-r['risk'], r['id']))
        no_review_clean = math.prod(1-r['risk'] for r in items)
        choices = [{'cost': 0, 'benefit': 0., 'ids': []}]
        for k in range(1, len(items)+1):
            clean = math.prod(1-r['risk']*(1-sensitivity if j < k else 1) for j, r in enumerate(items))
            choices.append({'cost': setup+k, 'benefit': clean-no_review_clean,
                            'ids': sorted(r['id'] for r in items[:k])})
        options[group] = choices
    return options


def knapsack(options, budget):
    """Exact multiple-choice DP; ties prefer lower cost then lexicographic IDs."""
    if type(budget) is not int or budget < 0:
        raise ValueError('Nonnegative integer budget required')
    table = {0: (0., ())}
    for group in sorted(options):
        choices = options[group]
        if not choices or not any(x['cost'] == 0 and x['benefit'] == 0 and not x['ids'] for x in choices):
            raise ValueError('Each group needs a zero-cost no-review option')
        if any(type(x['cost']) is not int or x['cost'] < 0 or not math.isfinite(x['benefit']) for x in choices):
            raise ValueError('Invalid review option')
        updated = {}
        for spent, (benefit, ids) in sorted(table.items()):
            for option in choices:
                cost = spent + option['cost']
                if cost > budget:
                    continue
                candidate = (benefit+option['benefit'], tuple(sorted(ids+tuple(option['ids']))))
                old = updated.get(cost)
                if old is None or candidate[0] > old[0] or (candidate[0] == old[0] and candidate[1] < old[1]):
                    updated[cost] = candidate
        table = updated
    cost, (value, ids) = min(table.items(), key=lambda pair: (-pair[1][0], pair[0], pair[1][1]))
    return {'selected': list(ids), 'spent': cost, 'predicted_benefit': value}


def budgeted_greedy(rows, budget, setup):
    from ..adaptive.methods import review_order
    validate_risks(rows)
    if type(budget) is not int or budget < 0 or type(setup) is not int or setup < 0:
        raise ValueError('Nonnegative integer costs required')
    by_id = {r['id']: r for r in rows}
    opened, selected, spent = set(), [], 0
    for key in review_order(rows, group_aware=True):
        group = by_id[key]['group']
        cost = 1 + (0 if group in opened else setup)
        if spent + cost <= budget:
            opened.add(group)
            selected.append(key)
            spent += cost
    return {'selected': sorted(selected), 'spent': spent}


def normalize_proofs(proofs, probabilities):
    terms = []
    for proof in proofs:
        if isinstance(proof, (str, bytes)):
            raise ValueError('A proof must be a collection of primitive IDs')
        term = tuple(proof)
        if any(not isinstance(a, str) or not a or a not in probabilities for a in term):
            raise ValueError('Unknown or invalid primitive ID')
        terms.append(term)
    return canonical(terms)


def frontier_probability(proofs, probabilities, *, width_cap=12, state_cap=65536):
    """Exact monotone DNF probability under supplied independent primitives.

    Caps apply to frontier evaluation, not to validation or the prior fallback.
    An empty disjunction is false; a disjunction with an empty term is true.
    """
    if type(width_cap) is not int or not 0 <= width_cap <= 12 or type(state_cap) is not int or not 1 <= state_cap <= 65536:
        raise ValueError('Caps may only tighten the frozen limits')
    if any(not isinstance(a, str) or not a for a in probabilities):
        raise ValueError('Nonempty string primitive IDs required')
    for p in probabilities.values():
        probability(p)
    terms = normalize_proofs(proofs, probabilities)
    if not terms or () in terms:
        p = float(bool(terms))
        return {'lower': p, 'upper': p, 'exact': True, 'method': 'constant', 'width': 0, 'transitions': 0}
    atoms = sorted({a for t in terms for a in t})
    index = {a: i for i, a in enumerate(atoms)}
    transitions, width = 0, 0
    def fallback(reason):
        old = exact_lineage(terms, probabilities)
        return {**old, 'method': 'previous_fallback', 'reason': reason, 'width': width, 'transitions': transitions}
    if len(atoms) > 256 or len(terms) > 1024:
        return fallback('input_cap')
    ends = defaultdict(list)
    last_use = list(range(len(atoms)))
    for term in terms:
        last = max(index[a] for a in term)
        ends[last].append(sum(1 << index[a] for a in term))
        for a in term:
            last_use[index[a]] = max(last_use[index[a]], last)
    masks = [sum(1 << j for j in range(i+1) if last_use[j] > i) for i in range(len(atoms))]
    width = max(m.bit_count() for m in masks)
    if width > width_cap:
        return fallback('width_cap')
    states, success = {0: 1.}, 0.
    for i, atom in enumerate(atoms):
        updated = defaultdict(float)
        for mask, mass in sorted(states.items()):
            for yes, chance in ((False, 1-probabilities[atom]), (True, probabilities[atom])):
                if not mass or not chance:
                    continue
                if transitions >= state_cap:
                    return fallback('state_cap')
                transitions += 1
                extended = mask | (1 << i) if yes else mask
                value = mass * chance
                if any(extended & proof == proof for proof in ends[i]):
                    success += value
                else:
                    updated[extended & masks[i]] += value
        states = updated
    p = min(1., max(0., success))
    return {'lower': p, 'upper': p, 'exact': True, 'method': 'frontier', 'width': width, 'transitions': transitions}


class WorkLimit(Exception):
    """A bounded algorithm must delegate rather than certify partial work."""


def bipartition(adj, nodes):
    color = {}
    for root in sorted(nodes):
        if root in color:
            continue
        color[root] = 0
        queue = deque([root])
        while queue:
            u = queue.popleft()
            for v in sorted(adj[u]):
                if v not in nodes:
                    continue
                if v not in color:
                    color[v] = 1-color[u]
                    queue.append(v)
                elif color[v] == color[u]:
                    return None
    return {k for k, c in color.items() if c == 0}


def flow_network(weights, adj, left):
    keys = sorted(weights)
    index = {k: i+1 for i, k in enumerate(keys)}
    source, sink = 0, len(keys)+1
    capacity = {}
    infinity = sum(weights.values())+1
    for k in keys:
        if k in left:
            capacity[source, index[k]] = weights[k]
            for other in sorted(adj[k]):
                capacity[index[k], index[other]] = infinity
        else:
            capacity[index[k], sink] = weights[k]
    return keys, capacity, source, sink


def maximum_flow(capacity, source, sink, inspection_cap):
    """Deterministic integer Dinic implementation; certificates are checked separately."""
    residual = dict(capacity)
    adjacency = defaultdict(set)
    for u, v in capacity:
        residual.setdefault((v, u), 0)
        adjacency[u].add(v)
        adjacency[v].add(u)
    adjacency = {u: sorted(vs) for u, vs in adjacency.items()}
    inspected, value = 0, 0
    def touch():
        nonlocal inspected
        inspected += 1
        if inspected > inspection_cap:
            raise WorkLimit('Residual inspection cap')
    while True:
        level, queue = {source: 0}, deque([source])
        while queue:
            u = queue.popleft()
            for v in adjacency.get(u, []):
                touch()
                if residual[u, v] > 0 and v not in level:
                    level[v] = level[u]+1
                    queue.append(v)
        if sink not in level:
            break
        cursor = defaultdict(int)
        def send(u, bound):
            if u == sink:
                return bound
            neighbors = adjacency.get(u, [])
            while cursor[u] < len(neighbors):
                v = neighbors[cursor[u]]
                touch()
                if level.get(v) == level[u]+1 and residual[u, v] > 0:
                    sent = send(v, min(bound, residual[u, v]))
                    if sent:
                        residual[u, v] -= sent
                        residual[v, u] += sent
                        return sent
                cursor[u] += 1
            return 0
        while True:
            sent = send(source, sum(capacity.values())+1)
            if not sent:
                break
            value += sent
    reachable, queue = {source}, deque([source])
    while queue:
        u = queue.popleft()
        for v in adjacency.get(u, []):
            touch()
            if residual[u, v] > 0 and v not in reachable:
                reachable.add(v)
                queue.append(v)
    flow = [[u, v, capacity[u, v]-residual[u, v]] for u, v in sorted(capacity)
            if capacity[u, v] != residual[u, v]]
    return value, reachable, flow, inspected


def verify_certificate(weights, edges, result):
    """Verify feasibility plus equality of primal/dual objective, not solver internals."""
    try:
        adj = graph_input(weights, edges)
        cert = result['certificate']
        keys, left = sorted(weights), set(cert['left'])
        if cert['nodes'] != keys or not left <= set(keys) or len(left) != len(cert['left']):
            return False
        if any((a in left) == (b in left) for a in keys for b in adj[a]):
            return False
        _, capacities, source, sink = flow_network(weights, adj, left)
        net, seen = defaultdict(int), set()
        for u, v, value in cert['flow']:
            if type(u) is not int or type(v) is not int or type(value) is not int:
                return False
            if (u, v) not in capacities or (u, v) in seen or not 0 <= value <= capacities[u, v]:
                return False
            seen.add((u, v))
            net[u] -= value
            net[v] += value
        total = cert['flow_value']
        if type(total) is not int or total < 0 or net[source] != -total or net[sink] != total:
            return False
        if any(net[i] for i in range(1, len(keys)+1)):
            return False
        chosen = set(result['selected'])
        if type(result['utility']) is not int or len(chosen) != len(result['selected']) or not chosen <= set(keys) or result['staged']:
            return False
        cover = set(keys)-chosen
        return (set(cert['cover']) == cover and len(cert['cover']) == len(cover)
                and all(a in cover or b in cover for a in keys for b in adj[a])
                and sum(weights[k] for k in cover) == total
                and result['utility'] == sum(weights[k] for k in chosen))
    except (ValueError, KeyError, TypeError):
        return False


def solve_conflicts(weights, edges, *, inspection_cap=2000000):
    if type(inspection_cap) is not int or not 1 <= inspection_cap <= 2000000:
        raise ValueError('Inspection cap may only tighten the frozen maximum')
    adj = graph_input(weights, edges)
    solutions = []
    for nodes in components(adj):
        left = bipartition(adj, nodes) if len(nodes) <= 256 else None
        if left is None:
            solutions.append(solve_component(weights, adj, nodes))
            continue
        local_w = {k: weights[k] for k in sorted(nodes)}
        local_a = {k: adj[k] for k in sorted(nodes)}
        keys, caps, source, sink = flow_network(local_w, local_a, left)
        try:
            value, reachable, flow, scans = maximum_flow(caps, source, sink, inspection_cap)
        except WorkLimit:
            fallback = solve_component(weights, adj, nodes)
            solutions.append({**fallback, 'fallback_reason': 'flow_work_cap'})
            continue
        selected = [k for i, k in enumerate(keys, 1) if (k in left) == (i in reachable)]
        certificate = {'nodes': keys, 'left': sorted(left), 'flow': flow, 'flow_value': value,
                       'cover': sorted(set(keys)-set(selected))}
        result = {'selected': selected, 'staged': [], 'utility': sum(local_w[k] for k in selected),
                  'method': 'bipartite_flow', 'certificate': certificate, 'residual_inspections': scans}
        local_edges = [(a, b) for a in local_a for b in local_a[a] if a < b]
        if not verify_certificate(local_w, local_edges, result):
            raise AssertionError('Internal flow/cover certificate failure')
        solutions.append(result)
    return {**aggregate(solutions), 'components': solutions}


class LineageCache:
    """Sequential in-memory, revision-checked deltas; not a database transaction."""
    def __init__(self, facts, probabilities):
        if any(not isinstance(a, str) or not a for a in probabilities):
            raise ValueError('Invalid primitive ID')
        for p in probabilities.values():
            probability(p)
        self._probabilities = dict(probabilities)
        self._facts, self._values, self._index = {}, {}, defaultdict(set)
        self.revision, self.evaluations, self.index_touches = 0, 0, 0
        for key, proofs in sorted(facts.items()):
            self.set_fact(key, proofs, self.revision)
        self.revision = 0

    def _check(self, revision):
        if type(revision) is not int or revision != self.revision:
            raise ValueError('Stale or invalid revision')

    def _evaluate(self, terms, probabilities):
        dependencies = sorted({a for term in terms for a in term})
        result = frontier_probability(terms, {a: probabilities[a] for a in dependencies})
        return {k: result[k] for k in ('lower', 'upper', 'exact')}

    def update_probabilities(self, changes, revision):
        self._check(revision)
        if any(a not in self._probabilities for a in changes):
            raise ValueError('Unknown primitive')
        for p in changes.values():
            probability(p)
        changed = {a: p for a, p in changes.items() if self._probabilities[a] != p}
        affected = set()
        touches = 0
        for atom in sorted(changed):
            affected.update(self._index.get(atom, ()))
            touches += 1+len(self._index.get(atom, ()))
        overlay = ChainMap(changed, self._probabilities)
        updates = {key: self._evaluate(self._facts[key], overlay) for key in sorted(affected)}
        # All validation and potentially failing evaluation precede state mutation.
        self._probabilities.update(changed)
        self._values.update(updates)
        self.evaluations += len(updates)
        self.index_touches += touches
        self.revision += 1
        return self.revision

    def set_fact(self, key, proofs, revision):
        self._check(revision)
        if not isinstance(key, str) or not key:
            raise ValueError('Nonempty fact ID required')
        terms = normalize_proofs(proofs, self._probabilities)
        value = self._evaluate(terms, self._probabilities)
        old_deps = {a for t in self._facts.get(key, ()) for a in t}
        new_deps = {a for t in terms for a in t}
        for a in sorted(old_deps-new_deps):
            self._index[a].remove(key)
            if not self._index[a]:
                del self._index[a]
        for a in sorted(new_deps-old_deps):
            self._index[a].add(key)
        self._facts[key], self._values[key] = terms, value
        self.evaluations += 1
        self.index_touches += len(old_deps ^ new_deps)
        self.revision += 1
        return self.revision

    def remove_fact(self, key, revision):
        self._check(revision)
        if key not in self._facts:
            raise ValueError('Unknown fact')
        deps = {a for t in self._facts[key] for a in t}
        for a in sorted(deps):
            self._index[a].remove(key)
            if not self._index[a]:
                del self._index[a]
        del self._facts[key], self._values[key]
        self.index_touches += len(deps)
        self.revision += 1
        return self.revision

    def snapshot(self):
        return deepcopy({'revision': self.revision, 'probabilities': self._probabilities,
                         'facts': {k: [list(t) for t in ts] for k, ts in sorted(self._facts.items())},
                         'values': self._values, 'index': {a: sorted(ks) for a, ks in sorted(self._index.items())}})
