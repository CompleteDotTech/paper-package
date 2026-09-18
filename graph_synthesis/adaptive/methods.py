"""Gold-free policy execution, development-only fitting, bounded graph optimization."""
from __future__ import annotations
from collections import Counter, defaultdict
from itertools import combinations
import math
from typing import Mapping, Sequence

from ..multicall import LABELS, prediction
from ..followup.methods import conflict, supported

POSITIVE = frozenset({'SUPPORTS', 'REFUTES'})
VIEWS = ('base1', 'base2', 'base3', 'blind1', 'blind2', 'structured', 'contrastive')


def charged(answer: Mapping, sites: Sequence[str], calls: Mapping) -> dict:
    """Attach physical-call accounting without counting a shared call twice."""
    sites = list(dict.fromkeys(sites))
    tokens = 0
    for site in sites:
        usage = calls[site].get('tokens_used')
        if usage is None or type(usage.get('input')) is not int or usage['input'] < 0:
            raise ValueError('Complete nonnegative recorded input usage required')
        tokens += usage['input']
    return {**answer, 'sites': sites, 'input_tokens': tokens, 'unknown_usage_calls': 0}


def compact_route(calls: Mapping, *, disagreement: bool = True) -> dict:
    small = prediction(calls['contrastive'])
    sites = ['contrastive']
    if disagreement:
        other = prediction(calls['blind1'])
        sites.append('blind1')
        escalate = small['status'] != 'ok' or other['status'] != 'ok' or small['label'] != other['label']
    else:
        escalate = small['status'] != 'ok' or small['score'] < .90
    if escalate:
        sites.append('base1')
    return charged(prediction(calls['base1']) if escalate else small, sites, calls)


def safe_targeted(calls: Mapping) -> dict:
    """Never authorize a downstream judgment with an invalid prerequisite."""
    base = prediction(calls['base1'])
    if base['status'] != 'ok':
        return charged(prediction(calls['contrastive']), ['base1', 'contrastive'], calls)
    sites = ['base1', 'checks']
    if calls['checks'].get('error'):
        return charged(base, sites, calls)
    final = prediction(calls['adjudicate'])
    sites.append('adjudicate')
    return charged(final if final['status'] == 'ok' else base, sites, calls)


def components(vertices: Sequence, adjacent) -> list[list]:
    remaining = set(vertices)
    groups = []
    while remaining:
        root = min(remaining)
        remaining.remove(root)
        group, queue = {root}, [root]
        while queue:
            node = queue.pop()
            linked = {other for other in remaining if adjacent(node, other)}
            remaining -= linked
            group |= linked
            queue.extend(sorted(linked))
        groups.append(sorted(group))
    return groups


def fit_clusters(development: Sequence[Mapping], *, split: str) -> dict:
    if split != 'development' or not development or any(r['split'] != split for r in development):
        raise ValueError('Fit only on nonempty development rows')
    errors = {view: {r['id']: r['views'][view]['label'] for r in development
                     if r['views'][view]['label'] != r['gold']} for view in VIEWS}
    pairwise = []
    joins = set()
    for a, b in combinations(VIEWS, 2):
        union = set(errors[a]) | set(errors[b])
        same = sum(errors[a][key] == errors[b][key] for key in set(errors[a]) & set(errors[b]))
        similarity = same / len(union) if union else 0.
        pairwise.append({'left': a, 'right': b, 'same_wrong': same, 'error_union': len(union), 'similarity': similarity})
        if union and similarity >= .80:
            joins.add(frozenset((a, b)))
    return {'clusters': components(VIEWS, lambda a, b: frozenset((a, b)) in joins),
            'pairwise': pairwise, 'fit_ids': sorted(r['id'] for r in development),
            'fit_groups': sorted({r['group'] for r in development}), 'threshold': .80}


def ensemble(calls: Mapping, clusters: Sequence[Sequence[str]]) -> dict:
    flat = [view for group in clusters for view in group]
    if not clusters or any(not group for group in clusters) or sorted(flat) != sorted(VIEWS):
        raise ValueError('Clusters must partition the declared views exactly')
    averages = []
    for group in clusters:
        valid = [prediction(calls[k]) for k in group if not calls[k].get('error')]
        if not valid:
            return charged({'status': 'error', 'label': 'ERROR', 'score': None}, VIEWS, calls)
        averages.append({k: sum(v['probabilities'][k] for v in valid) / len(valid) for k in LABELS})
    votes = Counter(max(LABELS, key=lambda k: p[k]) for p in averages)
    winner = max(LABELS, key=lambda k: votes[k])
    strict = votes[winner] > len(clusters) / 2
    corroborated = winner not in POSITIVE or votes[winner] >= 2
    answer = {'status': 'abstain', 'label': 'ABSTAIN', 'score': None}
    if strict and corroborated:
        answer = {'status': 'ok', 'label': winner,
                  'score': sum(p[winner] for p in averages) / len(averages)}
    return charged(answer, VIEWS, calls)


def risk_key(row: Mapping) -> tuple:
    base, small = row['views']['base1'], row['views']['contrastive']
    return base['label'], bool(base['score'] is not None and base['score'] >= .90), base['label'] != small['label']


def fit_risk(development: Sequence[Mapping], *, split: str) -> dict:
    if split != 'development' or not development or any(r['split'] != split for r in development):
        raise ValueError('Fit only on nonempty development rows')
    accepted = [r for r in development if r['views']['base1']['label'] in POSITIVE]
    rate = (1 + sum(r['views']['base1']['label'] != r['gold'] for r in accepted)) / (len(accepted) + 2)
    counts = defaultdict(lambda: [0, 0])
    for row in accepted:
        counts[risk_key(row)][0] += row['views']['base1']['label'] != row['gold']
        counts[risk_key(row)][1] += 1
    return {'prior': rate, 'bins': {repr(key): {'wrong': w, 'n': n, 'risk': (w + 2*rate)/(n+2)}
                                   for key, (w, n) in sorted(counts.items())}}


def assign_risks(features: Sequence[Mapping], fit: Mapping) -> list[dict]:
    return [{'id': r['id'], 'group': r['group'],
             'risk': fit['bins'].get(repr(risk_key(r)), {}).get('risk', fit['prior'])}
            for r in features if r['views']['base1']['label'] in POSITIVE]


def review_order(candidates: Sequence[Mapping], *, group_aware: bool) -> list[str]:
    if len({r['id'] for r in candidates}) != len(candidates):
        raise ValueError('Unique review IDs required')
    if any(type(r['risk']) not in (float, int) or not math.isfinite(r['risk']) or not 0 <= r['risk'] <= 1 for r in candidates):
        raise ValueError('Review risks must be finite values in [0,1]')
    todo = {r['id']: r for r in candidates}
    order = []
    while todo:
        def gain(row):
            value = row['risk']
            if group_aware:
                value *= math.prod(1-r['risk'] for r in todo.values() if r['group'] == row['group'] and r['id'] != row['id'])
            return value
        winner = min(todo, key=lambda key: (-gain(todo[key]), key))
        order.append(winner)
        del todo[winner]
    return order


def optimize_batch(assertions: Sequence[Mapping], *, limit: int = 16) -> dict:
    """Exact priority optimization of supported bounded conflict components.

    Exponential in component size. Unsupported and over-limit components are
    staged; the default GraphStore and semantic judgments are never changed.
    """
    if type(limit) is not int or not 1 <= limit <= 16:
        raise ValueError('Component limit must be an integer in [1,16]')
    if any(not isinstance(r.get('id'), str) or not r['id'] for r in assertions) or len({r['id'] for r in assertions}) != len(assertions):
        raise ValueError('Nonempty unique assertion IDs required')
    valid, staged = {}, []
    for row in assertions:
        weight = row.get('weight')
        if not supported(row) or type(weight) not in (float, int) or not math.isfinite(weight) or weight < 0:
            staged.append(row['id'])
        else:
            valid[row['id']] = row
    collision = lambda a, b: conflict(valid[a], valid[b], frozenset({'located_in'})) == 'conflict'
    groups = components(sorted(valid), collision)
    selected = []
    for group in groups:
        if len(group) > limit:
            staged.extend(group)
            continue
        pairs = [(i, j) for i, a in enumerate(group) for j, b in enumerate(group) if i < j and collision(a, b)]
        best, best_weight = (), -1.
        for mask in range(1 << len(group)):
            if any(mask & (1 << i) and mask & (1 << j) for i, j in pairs):
                continue
            chosen = tuple(group[i] for i in range(len(group)) if mask & (1 << i))
            weight = sum(valid[k]['weight'] for k in chosen)
            if weight > best_weight or weight == best_weight and chosen < best:
                best, best_weight = chosen, weight
        selected.extend(best)
    return {'selected': sorted(selected), 'staged': sorted(staged),
            'utility': sum(valid[k]['weight'] for k in selected), 'components': [len(g) for g in groups]}


def greedy_batch(assertions: Sequence[Mapping], *, priority: bool) -> dict:
    rows = sorted(assertions, key=lambda r: (-r['weight'], r['id'])) if priority else list(assertions)
    chosen = []
    for row in rows:
        if supported(row) and all(conflict(row, old, frozenset({'located_in'})) == 'clear' for old in chosen):
            chosen.append(row)
    return {'selected': sorted(r['id'] for r in chosen), 'utility': sum(r['weight'] for r in chosen)}
