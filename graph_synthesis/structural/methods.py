"""Gold-free selection and bounded exact algorithms for exploratory research."""
from __future__ import annotations
from collections import Counter, defaultdict
from functools import lru_cache
from itertools import combinations
import math
from ..adaptive.methods import POSITIVE, components
from ..risk_control.methods import independent_set, validate_review
from ..followup.methods import proof_bounds, validate_probability


def feature(row):
    answer = row['views']['base1']
    return {'id': row['id'], 'group': row['group'], 'label': answer['label'], 'score': answer['score']}


def rank_bin(row):
    score = row['score']
    if row['label'] not in POSITIVE or score is None or not math.isfinite(score) or not 0 <= score <= 1:
        raise ValueError('A valid positive prediction is required')
    return row['label'] + ':' + str(0 if score < .9 else 1 if score < .99 else 2)


def fit_rank(rows, *, balanced=True):
    if not rows or any(r['split'] != 'development' for r in rows):
        raise ValueError('Only nonempty development data may fit ranking')
    positives = [r for r in rows if r['label'] in POSITIVE]
    counts = Counter(r['group'] for r in positives)
    bins = defaultdict(lambda: [0., 0.])
    for row in positives:
        weight = 1/counts[row['group']] if balanced else 1.
        bins[rank_bin(row)][0] += weight * (row['label'] == row['gold'])
        bins[rank_bin(row)][1] += weight
    global_mean = (1+sum(v[0] for v in bins.values())) / (2+sum(v[1] for v in bins.values()))
    return {'balanced': balanced, 'global_mean': global_mean,
            'bins': {key: {'correct_weight': c, 'total_weight': n, 'reliability': (c+4*global_mean)/(n+4)}
                     for key, (c, n) in sorted(bins.items())},
            'fit_ids': sorted(r['id'] for r in rows), 'fit_groups': sorted({r['group'] for r in rows})}


def select_rank(rows, k, fit=None, *, diverse=False):
    if type(k) is not int or k < 0 or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Nonnegative integer budget and unique IDs required')
    pool = [dict(r) for r in rows if r['label'] in POSITIVE]
    for row in pool:
        rank_bin(row)
    if fit is not None and diverse:
        raise ValueError('Ranking and diversity are separate frozen policies')
    chosen, counts = [], Counter()
    while pool and len(chosen) < k:
        def key(r):
            value = r['score']
            if diverse:
                value /= 1+counts[r['group']]
            elif fit is not None:
                value = fit['bins'].get(rank_bin(r), {}).get('reliability', fit['global_mean'])
            return (-value, -r['score'], r['id'])
        row = min(pool, key=key)
        chosen.append(row['id']); counts[row['group']] += 1; pool.remove(row)
    return sorted(chosen)


def contamination_bounds(candidates, selected, sensitivity=.75):
    validate_review(candidates, 0, sensitivity)
    groups = defaultdict(list)
    for row in candidates:
        groups[row['group']].append(row['risk'] * (1-sensitivity if row['id'] in selected else 1))
    return {'lower': sum(max(v) for _, v in sorted(groups.items())),
            'independent': sum(1-math.prod(1-x for x in v) for _, v in sorted(groups.items())),
            'upper': sum(min(1., sum(v)) for _, v in sorted(groups.items()))}


def robust_review(candidates, budget, sensitivity=.75):
    """Exact allocation for the sum-of-group union upper bound, not true risk."""
    validate_review(candidates, budget, sensitivity)
    budget = min(budget, len(candidates))
    groups = defaultdict(list)
    for row in candidates:
        groups[row['group']].append(row)
    dp = {0: (0., ())}
    for group in sorted(groups):
        rows = sorted(groups[group], key=lambda r: (-r['risk'], r['id']))
        options = []
        for k in range(min(budget, len(rows))+1):
            ids = tuple(sorted(r['id'] for r in rows[:k]))
            options.append((contamination_bounds(rows, set(ids), sensitivity)['upper'], ids))
        nxt = {}
        for used, (loss, ids) in sorted(dp.items()):
            for count, (extra, added) in enumerate(options):
                if used+count <= budget:
                    candidate = (loss+extra, tuple(sorted(ids+added)))
                    if used+count not in nxt or candidate < nxt[used+count]:
                        nxt[used+count] = candidate
        dp = nxt
    return list(dp[budget][1])


def canonical(proofs):
    """Absorb A AND B whenever the disjunction already includes A."""
    clauses = sorted({tuple(sorted(set(p))) for p in proofs}, key=lambda p: (len(p), p))
    kept = []
    for clause in clauses:
        if not any(set(prior) <= set(clause) for prior in kept):
            kept.append(clause)
    return tuple(sorted(kept))


def lineage_probability(proofs, probabilities, *, max_states=4096):
    if type(max_states) is not int or not 1 <= max_states <= 4096:
        raise ValueError('State limit must be an integer in [1,4096]')
    for atom, probability in probabilities.items():
        if not isinstance(atom, str) or not atom:
            raise ValueError('Atoms must be nonempty strings')
        validate_probability(probability)
    if any(not p or any(a not in probabilities for a in p) for p in proofs):
        raise ValueError('Nonempty proofs over supplied atoms required')
    bounds = proof_bounds(proofs, probabilities)
    states = 0
    class Exhausted(Exception):
        pass
    @lru_cache(maxsize=None)
    def solve(formula):
        nonlocal states
        if states >= max_states:
            raise Exhausted
        states += 1
        if not formula:
            return 0.
        if () in formula:
            return 1.
        occurrences = Counter(a for clause in formula for a in clause)
        atom = min(occurrences, key=lambda a: (-occurrences[a], a))
        yes = canonical(tuple(a for a in clause if a != atom) for clause in formula)
        no = canonical(clause for clause in formula if atom not in clause)
        p = probabilities[atom]
        if p == 0:
            return solve(no)
        if p == 1:
            return solve(yes)
        return p*solve(yes)+(1-p)*solve(no)
    status = 'exact'
    probability = None
    if len(probabilities) > 256 or len(proofs) > 512:
        status = 'input_limit'
    else:
        try:
            probability = solve(canonical(proofs))
        except Exhausted:
            status = 'state_limit'
    return {'status': status, 'probability': probability, 'states': states,
            'lower': probability if probability is not None else bounds['lower'],
            'upper': probability if probability is not None else bounds['upper'], 'prior_bounds': bounds}


def induced(adjacency, vertices):
    return {v: set(adjacency[v]) & set(vertices) for v in sorted(vertices)}


def feedback_cutset(adjacency, cap=4):
    """Greedy bounded discovery; failure does not prove minimum cutset > cap."""
    remaining, cutset = set(adjacency), []
    while True:
        core = set(remaining)
        while True:
            leaves = {v for v in core if len(adjacency[v] & core) < 2}
            if not leaves:
                break
            core -= leaves
        if not core:
            return cutset
        if len(cutset) >= cap:
            return None
        vertex = min(core, key=lambda v: (-len(adjacency[v] & core), v))
        cutset.append(vertex); remaining.remove(vertex)


def cutset_independent_set(adjacency, weights):
    prior = independent_set(adjacency, weights)  # validates shape and types
    selected, staged, routes = [], [], []
    for group in components(sorted(adjacency), lambda a, b: b in adjacency[a]):
        graph = induced(adjacency, group)
        cut = feedback_cutset(graph) if len(group) <= 256 else None
        if cut is None:
            result = independent_set(graph, {v: weights[v] for v in group})
            selected.extend(result['selected']); staged.extend(result['staged'])
            routes.append({'size': len(group), 'algorithm': 'prior_fallback', 'cutset': None})
            continue
        remainder, best = set(group)-set(cut), (0, ())
        for mask in range(1 << len(cut)):
            chosen = {v for i, v in enumerate(cut) if mask & (1 << i)}
            if any(b in graph[a] for a, b in combinations(chosen, 2)):
                continue
            excluded = set().union(*(graph[v] for v in chosen)) if chosen else set()
            available = remainder-excluded
            result = independent_set(induced(graph, available), {v: weights[v] for v in available})
            if result['staged']:
                raise AssertionError('A verified feedback set must leave a forest')
            ids = tuple(sorted(chosen | set(result['selected'])))
            candidate = (sum(weights[v] for v in ids), ids)
            if candidate[0] > best[0] or candidate[0] == best[0] and candidate[1] < best[1]:
                best = candidate
        selected.extend(best[1]); routes.append({'size': len(group), 'algorithm': 'cutset_forest', 'cutset': sorted(cut)})
    result = {'selected': sorted(selected), 'staged': sorted(staged),
              'rejected': sorted(set(adjacency)-set(selected)-set(staged)),
              'utility': sum(weights[v] for v in selected), 'routes': routes}
    if result['utility'] < prior['utility']:
        raise AssertionError('No prior-solver utility regression is permitted')
    return result
