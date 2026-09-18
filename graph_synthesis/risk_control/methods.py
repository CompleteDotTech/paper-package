"""Gold-free execution, development-only fitting, and bounded exact optimizers."""
from __future__ import annotations
from collections import defaultdict
from itertools import combinations
import math
from typing import Mapping, Sequence

from ..multicall import CHECKS, prediction
from ..adaptive.methods import POSITIVE, charged, components, optimize_batch
from ..followup.methods import supported, conflict

PENALTIES = (0., .01, .05, .1, .25, .5, 1.)
THRESHOLDS = (0., .90, .95, .99, 1.)


def abstain(reason: str) -> dict:
    return {'status': 'abstain', 'label': 'ABSTAIN', 'score': None, 'reason': reason}


def development_only(rows: Sequence[Mapping], split: str) -> None:
    if split != 'development' or not rows or any(r['split'] != split for r in rows):
        raise ValueError('Nonempty development rows required; test labels cannot fit policies')


def route_key(answer: Mapping) -> str:
    return answer['label'] + ':' + str(answer['score'] is not None and answer['score'] >= .90)


def edge_utility(answer: Mapping, gold: str) -> int:
    return (1 if answer['label'] == gold else -5) if answer['label'] in POSITIVE else 0


def route(calls: Mapping, fit: Mapping) -> dict:
    if fit['mode'] == 'direct_rich':
        return charged(prediction(calls['base1']), ['base1'], calls)
    small = prediction(calls['contrastive'])
    sites = ['contrastive']
    escalate = small['status'] != 'ok' or fit['actions'].get(route_key(small), True)
    if escalate:
        sites.append('base1')
    return charged(prediction(calls['base1']) if escalate else small, sites, calls)


def fit_router(rows: Sequence[Mapping], panels: Mapping, *, split: str) -> dict:
    development_only(rows, split)
    gains = [edge_utility(r['views']['base1'], r['gold']) - edge_utility(r['views']['contrastive'], r['gold']) for r in rows]
    prior = sum(gains)/len(gains)
    bins = defaultdict(list)
    for row, gain in zip(rows, gains):
        bins[route_key(row['views']['contrastive'])].append((gain, panels[row['id']]['base1']['tokens_used']['input']))
    fitted = {key: {'n': len(v), 'advantage': (sum(x[0] for x in v) + 2*prior)/(len(v)+2),
                    'rich_tokens': sum(x[1] for x in v)/len(v)} for key, v in sorted(bins.items())}
    def measure(policy):
        answers = [(route(panels[r['id']], policy), r['gold']) for r in rows]
        return {'correct': sum(a['label'] in POSITIVE and a['label'] == g for a,g in answers),
                'wrong': sum(a['label'] in POSITIVE and a['label'] != g for a,g in answers),
                'tokens': sum(a['input_tokens'] for a,g in answers)}
    direct = {'mode': 'direct_rich', 'actions': {}, 'penalty': None}
    reference = measure(direct)
    candidates = [{**direct, 'development': reference}]
    for penalty in PENALTIES:
        policy = {'mode': 'learned', 'penalty': penalty,
                  'actions': {key: b['advantage'] > penalty*b['rich_tokens']/1000 for key,b in fitted.items()}}
        policy['development'] = measure(policy)
        candidates.append(policy)
    feasible = [p for p in candidates if p['development']['correct'] >= .98*reference['correct'] and p['development']['wrong'] <= reference['wrong']]
    chosen = min(feasible, key=lambda p: (p['development']['tokens'], p['mode'], -1 if p['penalty'] is None else p['penalty']))
    return {**chosen, 'bins': fitted, 'prior': prior, 'candidates': candidates,
            'fit_ids': sorted(r['id'] for r in rows), 'fit_groups': sorted({r['group'] for r in rows})}


def binomial_upper(k: int, n: int, alpha: float) -> float:
    """One-sided Clopper-Pearson bound, via inversion; no asymptotic normal CI."""
    if type(k) is not int or type(n) is not int or not 0 <= k <= n or not 0 < alpha < 1:
        raise ValueError('Require integer 0 <= k <= n and 0 < alpha < 1')
    if n == 0 or k == n:
        return 1.
    lo, hi = 0., 1.
    for _ in range(80):
        p = (lo+hi)/2
        cdf = sum(math.comb(n,i)*p**i*(1-p)**(n-i) for i in range(k+1))
        if cdf > alpha:
            lo = p
        else:
            hi = p
    return hi


def threshold_gate(answer: Mapping, threshold: float | None) -> dict:
    if threshold is None:
        return {**abstain('no_nontrivial_certificate'), 'sites': [], 'input_tokens': 0, 'unknown_usage_calls': 0}
    if not 0 <= threshold <= 1:
        raise ValueError('Threshold must lie in [0,1]')
    if answer['label'] in POSITIVE and answer['score'] < threshold:
        return {**answer, **abstain('below_group_risk_threshold')}
    return dict(answer)


def fit_gate(rows: Sequence[Mapping], *, split: str) -> dict:
    development_only(rows, split)
    groups = sorted({r['group'] for r in rows})
    candidates = []
    for threshold in THRESHOLDS:
        accepted = [r for r in rows if threshold_gate(r['arms']['safe_targeted'], threshold)['label'] in POSITIVE]
        wrong = {r['group'] for r in accepted if r['arms']['safe_targeted']['label'] != r['gold']}
        bound = binomial_upper(len(wrong),len(groups),.05/len(THRESHOLDS))
        candidates.append({'threshold':threshold, 'groups':len(groups), 'wrong_groups':len(wrong),
                           'accepted':len(accepted), 'upper':bound, 'qualifies':bool(accepted) and bound <= .15})
    feasible = [r for r in candidates if r['qualifies']]
    selected = min(feasible,key=lambda r: (-r['accepted'],r['threshold'])) if feasible else None
    return {'threshold': None if selected is None else selected['threshold'], 'nontrivial':selected is not None,
            'candidates':candidates, 'alpha_per_policy':.05/len(THRESHOLDS), 'group_risk_target':.15,
            'fit_ids': sorted(r['id'] for r in rows), 'fit_groups':groups,
            'guarantee': 'Diagnostic only: reused data do not establish prospective independence/exchangeability.'}


def qualifier_veto(calls: Mapping, *, veto: bool = True) -> dict:
    base = prediction(calls['base1'])
    if base['label'] != 'SUPPORTS':
        return charged(base,['base1'],calls)
    sites = ['base1','checks']
    check = calls['checks']
    if check.get('error'):
        return charged({'status':'error','label':'ERROR','score':None,'reason':'invalid_checks'},sites,calls)
    answers = check['response']['answers']
    choices = {'MATCH','MISMATCH','UNRESOLVED','NOT_APPLICABLE'}
    if set(answers) != set(CHECKS):
        raise ValueError('Checks must contain every declared dimension')
    for answer in answers.values():
        p = answer['probabilities']
        if set(p) != choices or any(type(x) not in (int,float) or not math.isfinite(x) or not 0 <= x <= 1 for x in p.values()) or not math.isclose(sum(p.values()),1,abs_tol=1e-6):
            raise ValueError('Invalid check vector: never normalize it')
    mismatches = sorted(k for k in CHECKS if answers[k]['probabilities']['MISMATCH'] >= .90)
    answer = {**abstain('qualifier_mismatch'), 'dimensions':mismatches} if veto and mismatches else base
    return charged(answer,sites,calls)


def validate_review(candidates, budget, sensitivity):
    if type(budget) is not int or budget < 0 or not 0 <= sensitivity <= 1:
        raise ValueError('Nonnegative integer budget and valid sensitivity required')
    if len({r['id'] for r in candidates}) != len(candidates):
        raise ValueError('Unique review IDs required')
    if any(type(r['risk']) not in (float,int) or not math.isfinite(r['risk']) or not 0 <= r['risk'] <= 1 for r in candidates):
        raise ValueError('Risks must be finite in [0,1]')


def model_contamination(candidates, selected, sensitivity=.75):
    groups = defaultdict(list)
    for r in candidates:
        groups[r['group']].append(1-r['risk'] + (sensitivity*r['risk'] if r['id'] in selected else 0))
    return sum(1-math.prod(values) for _,values in sorted(groups.items()))


def greedy_review(candidates, budget, sensitivity=.75):
    validate_review(candidates,budget,sensitivity)
    selected = set()
    for _ in range(min(budget,len(candidates))):
        key = min((r['id'] for r in candidates if r['id'] not in selected),
                  key=lambda key:(model_contamination(candidates,selected|{key},sensitivity),key))
        selected.add(key)
    return sorted(selected)


def optimal_review(candidates, budget, sensitivity=.75):
    """Exact group-budget DP under explicitly supplied independent edge risks."""
    validate_review(candidates,budget,sensitivity)
    budget = min(budget,len(candidates))
    groups = defaultdict(list)
    for r in candidates:
        groups[r['group']].append(r)
    dp = {0:(0.,())}
    for group in sorted(groups):
        values = sorted(groups[group],key=lambda r:(-r['risk'],r['id']))
        options = []
        for k in range(min(budget,len(values))+1):
            ids = tuple(sorted(r['id'] for r in values[:k]))
            options.append((model_contamination(values,set(ids),sensitivity),ids))
        nxt = {}
        for used,(loss,ids) in sorted(dp.items()):
            for k,(extra,added) in enumerate(options):
                if used+k > budget:
                    continue
                candidate = (loss+extra,tuple(sorted(ids+added)))
                old = nxt.get(used+k)
                if old is None or candidate < old:
                    nxt[used+k] = candidate
        dp = nxt
    return list(dp[budget][1])


def independent_set(adjacency: Mapping[str,set], weights: Mapping[str,int], *, limit=256) -> dict:
    """Solve forests exactly; enumerate small cycles; stage unsupported components.

    Deterministic component-local ties; no claim of global lexicographic optimality.
    """
    if type(limit) is not int or not 1 <= limit <= 256:
        raise ValueError('Limit must be an integer in [1,256]')
    if set(adjacency) != set(weights) or any(type(w) is not int or w < 0 for w in weights.values()):
        raise ValueError('Require nonnegative integer weights for every vertex')
    for v,neighbours in adjacency.items():
        if v in neighbours or not set(neighbours) <= set(adjacency) or any(v not in adjacency[w] for w in neighbours):
            raise ValueError('Adjacency must be symmetric and loop-free')
    selected,staged,routes = [],[],[]
    def best(a,b):
        return a if a[0] > b[0] or a[0] == b[0] and a[1] < b[1] else b
    for group in components(sorted(adjacency),lambda a,b:b in adjacency[a]):
        edge_count = sum(len(adjacency[v]) for v in group)//2
        if len(group) > limit or (edge_count != len(group)-1 and len(group)>16):
            staged.extend(group); routes.append({'size':len(group),'edges':edge_count,'algorithm':'stage'})
            continue
        if edge_count == len(group)-1:
            parent = {group[0]:None}; order = [group[0]]
            for v in order:
                for w in sorted(adjacency[v]):
                    if w != parent[v]:
                        parent[w] = v; order.append(w)
            dp = {}
            for v in reversed(order):
                include=(weights[v],(v,));exclude=(0,())
                for w in sorted(adjacency[v]):
                    if parent.get(w) != v:
                        continue
                    yes,no = dp[w]
                    include=(include[0]+no[0],tuple(sorted(include[1]+no[1])))
                    child=best(yes,no)
                    exclude=(exclude[0]+child[0],tuple(sorted(exclude[1]+child[1])))
                dp[v]=(include,exclude)
            chosen = best(*dp[group[0]])[1]; algorithm='forest_dp'
        else:
            optimum = (0,())
            for mask in range(1<<len(group)):
                subset = tuple(v for i,v in enumerate(group) if mask & (1<<i))
                if any(b in adjacency[a] for a,b in combinations(subset,2)):
                    continue
                optimum = best(optimum,(sum(weights[v] for v in subset),subset))
            chosen=optimum[1];algorithm='enumeration'
        selected.extend(chosen);routes.append({'size':len(group),'edges':edge_count,'algorithm':algorithm})
    return {'selected':sorted(selected),'staged':sorted(staged),
            'rejected':sorted(set(adjacency)-set(selected)-set(staged)),
            'utility':sum(weights[v] for v in selected),'routes':routes}


def forest_batch(assertions: Sequence[Mapping], *, limit=256) -> dict:
    if any(not isinstance(r.get('id'),str) or not r['id'] for r in assertions) or len({r['id'] for r in assertions}) != len(assertions):
        raise ValueError('Nonempty unique assertion IDs required')
    valid = {r['id']:r for r in assertions if supported(r) and type(r.get('weight')) is int and r['weight']>=0}
    adjacency = {key:set() for key in valid}
    for a,b in combinations(sorted(valid),2):
        if conflict(valid[a],valid[b],frozenset({'located_in'})) == 'conflict':
            adjacency[a].add(b);adjacency[b].add(a)
    result=independent_set(adjacency,{key:r['weight'] for key,r in valid.items()},limit=limit)
    result['staged']=sorted(result['staged']+[r['id'] for r in assertions if r['id'] not in valid])
    return result
