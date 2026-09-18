"""Opt-in conflict solvers, repair-relative queries and an in-memory delta index.

Weights and conflict edges are supplied, not semantic truth. The public mutation
API maintains its invariant; callers must not modify underscore-prefixed state.
"""
from __future__ import annotations
from collections import deque
from . import risk  # Keeps this package importable without a network dependency.
from ..reliability.methods import graph_input, solve_component as old_component

VERTEX_CAP = 2048
EDGE_CAP = 50000


def groups(adj):
    seen, result = set(), []
    for root in sorted(adj):
        if root in seen:
            continue
        group, queue = set(), deque([root])
        seen.add(root)
        while queue:
            node = queue.popleft()
            group.add(node)
            for other in sorted(adj[node]):
                if other not in seen:
                    seen.add(other)
                    queue.append(other)
        result.append(frozenset(group))
    return result


def coloring(adj, group):
    colors = {}
    for root in sorted(group):
        if root in colors:
            continue
        colors[root], queue = 0, deque([root])
        while queue:
            node = queue.popleft()
            for other in sorted(adj[node]):
                if other not in group:
                    raise ValueError('Component is not closed under adjacency')
                if other in colors:
                    if colors[other] == colors[node]:
                        return None
                else:
                    colors[other] = 1 - colors[node]
                    queue.append(other)
    return colors


def network(weights, adj, group, colors):
    keys = sorted(group)
    index = {k: i for i, k in enumerate(keys)}
    source, sink, large = len(keys), len(keys) + 1, sum(weights[k] for k in keys) + 1
    arcs = []
    for k in keys:
        if colors[k] == 0:
            arcs.append((source, index[k], weights[k]))
            arcs.extend((index[k], index[b], large) for b in sorted(adj[k]))
        else:
            arcs.append((index[k], sink, weights[k]))
    return keys, source, sink, sorted(arcs)


def max_flow(arcs, n, source, sink):
    """Integer Edmonds-Karp; returns primal flow and reachable-cut witnesses."""
    residual = [dict() for _ in range(n)]
    for a, b, cap in arcs:
        residual[a][b] = cap
        residual[b][a] = 0
    adjacency = [sorted(row) for row in residual]
    total, searches = 0, 0
    while True:
        parent, queue = {source: None}, deque([source])
        searches += 1
        while queue and sink not in parent:
            a = queue.popleft()
            for b in adjacency[a]:
                if residual[a][b] > 0 and b not in parent:
                    parent[b] = a
                    queue.append(b)
        if sink not in parent:
            break
        b, amount = sink, None
        while b != source:
            a = parent[b]
            amount = residual[a][b] if amount is None else min(amount, residual[a][b])
            b = a
        b = sink
        while b != source:
            a = parent[b]
            residual[a][b] -= amount
            residual[b][a] += amount
            b = a
        total += amount
    return total, sorted(parent), [[a, b, cap, cap - residual[a][b]] for a, b, cap in arcs], searches


def verify_flow(weights, edges, result):
    """Independently check the claimed network, feasible flow and matching cut."""
    try:
        adj = graph_input(weights, edges)
        colors = coloring(adj, frozenset(adj))
        if colors is None:
            return False
        keys, source, sink, expected = network(weights, adj, frozenset(adj), colors)
        cert = result['certificate']
        if cert['vertex_order'] != keys or len(cert['arcs']) != len(expected):
            return False
        balance = [0] * (len(keys) + 2)
        for want, got in zip(expected, cert['arcs']):
            if len(got) != 4 or tuple(got[:3]) != want or any(type(x) is not int for x in got):
                return False
            a, b, cap, flow = got
            if not 0 <= flow <= cap:
                return False
            balance[a] -= flow
            balance[b] += flow
        reach = set(cert['reachable'])
        if source not in reach or sink in reach or not reach <= set(range(len(keys) + 2)):
            return False
        value = cert['flow']
        if type(value) is not int or value < 0 or balance[source] != -value or balance[sink] != value:
            return False
        if any(balance[i] for i in range(len(keys))):
            return False
        cut = sum(cap for a, b, cap in expected if a in reach and b not in reach)
        if cut != value:
            return False
        selected = set(result['selected'])
        wanted = {k for i, k in enumerate(keys) if (colors[k] == 0 and i in reach) or (colors[k] == 1 and i not in reach)}
        if selected != wanted or len(selected) != len(result['selected']) or result['staged']:
            return False
        if any(a in selected and b in selected for a, b in edges):
            return False
        utility = sum(weights[k] for k in selected)
        return utility == result['utility'] == sum(weights.values()) - value
    except (KeyError, TypeError, ValueError, IndexError):
        return False


def component(weights, adj, group):
    colors = coloring(adj, group)
    if colors is None:
        return old_component(weights, adj, group)
    n_edges = sum(len(adj[k]) for k in group) // 2
    if len(group) > VERTEX_CAP or n_edges > EDGE_CAP:
        return {'selected': [], 'staged': sorted(group), 'utility': 0, 'method': 'capacity_staged'}
    keys, source, sink, arcs = network(weights, adj, group, colors)
    value, reach_list, flows, searches = max_flow(arcs, len(keys) + 2, source, sink)
    reach = set(reach_list)
    selected = [k for i, k in enumerate(keys) if (colors[k] == 0 and i in reach) or (colors[k] == 1 and i not in reach)]
    result = {'selected': selected, 'staged': [], 'utility': sum(weights[k] for k in selected), 'method': 'bipartite_flow',
              'certificate': {'vertex_order': keys, 'arcs': flows, 'reachable': reach_list, 'flow': value, 'searches': searches}}
    local_w = {k: weights[k] for k in keys}
    local_e = [(a, b) for a in keys for b in sorted(adj[a]) if a < b]
    if not verify_flow(local_w, local_e, result):
        raise ArithmeticError('Flow/cover certificate did not verify')
    return result


def aggregate(solutions):
    solutions = list(solutions)
    return {'selected': sorted(k for s in solutions for k in s['selected']),
            'staged': sorted(k for s in solutions for k in s['staged']),
            'utility': sum(s['utility'] for s in solutions)}


def solve(weights, edges):
    edges = list(edges)
    adj = graph_input(weights, edges)
    values = [component(weights, adj, g) for g in groups(adj)]
    return {**aggregate(values), 'components': values}


def forced(weights, edges, *, include=(), exclude=()):
    adj = graph_input(weights, edges)
    chosen, removed = set(include), set(exclude)
    if not chosen | removed <= set(weights):
        raise ValueError('Unknown forced vertex')
    if chosen & removed or any(adj[a] & chosen for a in chosen):
        return None
    removed |= chosen
    for node in chosen:
        removed.update(adj[node])
    w = {k: v for k, v in weights.items() if k not in removed}
    e = [(a, b) for a, b in edges if a in w and b in w]
    result = solve(w, e)
    return {**result, 'selected': sorted(chosen | set(result['selected'])),
            'utility': result['utility'] + sum(weights[k] for k in chosen)}


def query(weights, edges, required, *, epsilon=0):
    """Classify a conjunction relative to ALL weight-tolerant independent sets."""
    if type(epsilon) is not int or epsilon < 0:
        raise ValueError('Epsilon must be a nonnegative integer')
    if isinstance(required, str):
        raise ValueError('Required vertices must be a sequence')
    required = sorted(set(required))
    if len(required) > 8:
        return {'classification': 'unsupported', 'reason': 'query_capacity'}
    if not set(required) <= set(weights):
        raise ValueError('Unknown query vertex')
    edges = list(edges)
    base = solve(weights, edges)
    if base['staged']:
        return {'classification': 'unsupported', 'reason': 'base_staged'}
    threshold = base['utility'] - epsilon
    possible = forced(weights, edges, include=required)
    record = {'optimum': base['utility'], 'epsilon': epsilon, 'threshold': threshold,
              'single_optimum_answer': set(required) <= set(base['selected']), 'required': required,
              'counterexample': None, 'possible_repair': None, 'exclusions': []}
    if possible is not None and possible['staged']:
        return {**record, 'classification': 'unsupported', 'reason': 'forced_in_staged'}
    if possible is None or possible['utility'] < threshold:
        return {**record, 'classification': 'impossible'}
    record['possible_repair'] = possible['selected']
    for node in required:
        alternative = forced(weights, edges, exclude=[node])
        if alternative['staged']:
            return {**record, 'classification': 'unsupported', 'reason': 'forced_out_staged'}
        record['exclusions'].append({'excluded': node, 'utility': alternative['utility']})
        if alternative['utility'] >= threshold and record['counterexample'] is None:
            record['counterexample'] = alternative['selected']
    return {**record, 'classification': 'ambiguous' if record['counterexample'] is not None else 'certain'}


class DeltaIndex:
    """Prepare affected-component replacements, then publish; not a database.

    rescan_all=True is the full-snapshot comparator using the identical solver.
    Work counts explicit element passes, NOT optimizer-internal operations.
    Audit materialization via snapshot() is deliberately separate from update().
    """
    def __init__(self, weights, edges, *, rescan_all=False):
        adj = graph_input(weights, edges)
        self._weights, self._adj, self._which, self._solutions = {}, {}, {}, {}
        self._selected, self._staged, self._utility = set(), set(), 0
        self.rescan_all = bool(rescan_all)
        self.total_work = 0
        prepared = self._prepare(dict(weights), {k: set(v) for k, v in adj.items()})
        self.last_work = self._publish(set(), prepared, operation_visits=0)

    @staticmethod
    def _prepare(weights, adj):
        # Validation is local to the replacement scope, not the entire store.
        edges = [(a, b) for a in sorted(adj) for b in sorted(adj[a]) if a < b]
        clean = graph_input(weights, edges)
        solutions = {tuple(sorted(g)): component(weights, clean, g) for g in groups(clean)}
        volume = len(weights) + sum(len(v) for v in adj.values())
        work = {'copy': volume, 'validation': volume, 'discovery': volume, 'solver_input': volume}
        return weights, {k: set(v) for k, v in clean.items()}, solutions, work

    def _publish(self, old_groups, prepared, *, operation_visits):
        w, adj, solutions, work = prepared
        old_nodes = {k for g in old_groups for k in g}
        old_s = {k for g in old_groups for k in self._solutions[g]['selected']}
        old_t = {k for g in old_groups for k in self._solutions[g]['staged']}
        old_utility = sum(self._solutions[g]['utility'] for g in old_groups)
        new = aggregate(solutions.values())
        new_s, new_t = set(new['selected']), set(new['staged'])
        # No validation/solver operation after this publication boundary.
        for g in old_groups:
            del self._solutions[g]
        for k in old_nodes:
            del self._weights[k], self._adj[k], self._which[k]
        self._weights.update(w)
        self._adj.update(adj)
        self._solutions.update(solutions)
        for g in solutions:
            for k in g:
                self._which[k] = g
        self._selected.difference_update(old_s)
        self._selected.update(new_s)
        self._staged.difference_update(old_t)
        self._staged.update(new_t)
        self._utility += new['utility'] - old_utility
        work = {**work, 'operation_validation': operation_visits,
                'publication': len(old_nodes) + len(w) + len(old_s) + len(new_s) + len(old_t) + len(new_t)}
        self.total_work += sum(work.values())
        self.last_delta = {'selected_added': sorted(new_s - old_s), 'selected_removed': sorted(old_s - new_s),
                           'staged_added': sorted(new_t - old_t), 'staged_removed': sorted(old_t - new_t),
                           'utility': self._utility, 'work': work}
        return work

    def update(self, command):
        schemas = {'weight': {'kind', 'node', 'value'}, 'insert_vertex': {'kind', 'node', 'value'},
                   'delete_vertex': {'kind', 'node'}, 'insert_edge': {'kind', 'a', 'b'}, 'delete_edge': {'kind', 'a', 'b'}}
        if not isinstance(command, dict) or command.get('kind') not in schemas or set(command) != schemas[command['kind']]:
            raise ValueError('Malformed mutation')
        kind = command['kind']
        if kind in ('weight', 'insert_vertex', 'delete_vertex'):
            node = command['node']
            if not isinstance(node, str) or not node:
                raise ValueError('Nonempty vertex ID required')
            if kind == 'insert_vertex':
                if node in self._weights:
                    raise ValueError('Vertex already exists')
                touched = set()
            else:
                if node not in self._weights:
                    raise ValueError('Unknown vertex')
                touched = {self._which[node]}
            if kind != 'delete_vertex' and (type(command['value']) is not int or command['value'] < 0):
                raise ValueError('Nonnegative integer priority required')
        else:
            a, b = command['a'], command['b']
            if not all(isinstance(k, str) and k in self._weights for k in (a, b)) or a == b:
                raise ValueError('Invalid edge endpoints')
            present = b in self._adj[a]
            if present == (kind == 'insert_edge'):
                raise ValueError('Edge insertion/deletion precondition failed')
            touched = {self._which[a], self._which[b]}
        if self.rescan_all:
            touched = set(self._solutions)
        nodes = {k for g in touched for k in g}
        w = {k: self._weights[k] for k in nodes}
        adj = {k: set(self._adj[k]) for k in nodes}
        if kind == 'weight':
            w[node] = command['value']
        elif kind == 'insert_vertex':
            w[node], adj[node] = command['value'], set()
        elif kind == 'delete_vertex':
            for other in adj[node]:
                adj[other].remove(node)
            del w[node], adj[node]
        elif kind == 'insert_edge':
            adj[a].add(b)
            adj[b].add(a)
        else:
            adj[a].remove(b)
            adj[b].remove(a)
        prepared = self._prepare(w, adj)
        self.last_work = self._publish(touched, prepared, operation_visits=3)
        return self.last_delta.copy()

    def summary(self):
        return {'selected': sorted(self._selected), 'staged': sorted(self._staged), 'utility': self._utility}

    def snapshot(self):
        return {'weights': dict(self._weights), 'edges': [[a, b] for a in sorted(self._adj) for b in sorted(self._adj[a]) if a < b],
                **self.summary()}
