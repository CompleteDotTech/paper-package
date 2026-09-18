"""Gold-free policy execution and explicitly calibration-only fitting.

All methods are opt-in research components. Probabilistic proof bounds require
supplied independent primitive-event probabilities, not uncalibrated Jev scores.
"""
from __future__ import annotations

from collections import defaultdict
from itertools import product
import hashlib
import math
from typing import Mapping, Sequence

POSITIVE = frozenset({'same', 'SUPPORTS', 'REFUTES'})
THRESHOLDS = (0, .5, .7, .85, .9, .95, .99, 1, 1.000001)
TEMPERATURES = (.25, .5, .75, 1, 1.5, 2, 3, 4, 6, 8)
SHRINKAGES = (0, .25, .5, .75, 1)


def validate_probability(p: float) -> float:
    if isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) or not 0 <= p <= 1:
        raise ValueError('Finite probability in [0,1] required')
    return float(p)


def transform(p: Mapping[str, float], temperature: float = 1, weight: float = 1) -> dict:
    if not p or not math.isfinite(temperature) or temperature <= 0:
        raise ValueError('Nonempty distribution and positive finite temperature required')
    validate_probability(weight)
    values = {k: validate_probability(v) for k, v in p.items()}
    if abs(sum(values.values()) - 1) > 1e-8:
        raise ValueError('Distribution must sum to one')
    if temperature == 1 or weight == 0:
        return values
    logits = {k: math.log(max(v, 1e-15)) / temperature for k, v in values.items()}
    peak = max(logits.values())
    exps = {k: math.exp(v - peak) for k, v in logits.items()}
    total = sum(exps.values())
    return {k: (1-weight)*values[k] + weight*exps[k]/total for k in values}


def loss(p: Mapping[str, float], gold: str) -> tuple[float, float]:
    if gold not in p:
        raise ValueError('Gold must belong to task vocabulary')
    return (-math.log(max(p[gold], 1e-15)), sum((v - (k == gold))**2 for k, v in p.items()))


def losses(rows: Sequence[Mapping], temperature: float = 1, weight: float = 1) -> dict:
    valid = [r for r in rows if not r['error']]
    scores = [loss(transform(r['probabilities'], temperature, weight), r['gold']) for r in valid]
    return {'n': len(valid), 'errors': len(rows)-len(valid),
            'log_loss': sum(v[0] for v in scores)/len(scores) if scores else None,
            'brier': sum(v[1] for v in scores)/len(scores) if scores else None}


def fit_guard(rows: Sequence[Mapping], *, split: str) -> dict:
    if split != 'calibration' or not rows:
        raise ValueError('Only nonempty calibration data may fit a policy')
    valid = [r for r in rows if not r['error']]
    halves = [[r for r in valid if int(hashlib.sha256(r['group'].encode()).hexdigest(), 16) % 2 == i]
              for i in range(2)]
    fit, guard = halves
    identity = {'temperature': 1, 'weight': 0, 'status': 'identity_fallback',
                'fit_n': len(fit), 'guard_n': len(guard)}
    if not fit or not guard:
        return identity
    temperature = min(TEMPERATURES, key=lambda t: (losses(fit, t)['log_loss'], abs(t-1), t))
    raw = losses(guard)
    grid = [{'weight': w, **losses(guard, temperature, w)} for w in SHRINKAGES]
    eligible = [r for r in grid if r['brier'] <= raw['brier'] + 1e-12]
    selected = min(eligible, key=lambda r: (r['log_loss'], r['weight']))
    return {'temperature': temperature, 'weight': selected['weight'], 'status': 'fitted',
            'fit_n': len(fit), 'guard_n': len(guard), 'guard_grid': grid,
            'fit_groups': sorted({r['group'] for r in fit}),
            'guard_groups': sorted({r['group'] for r in guard})}


def features(rows: Sequence[Mapping]) -> list[dict]:
    keys = ('id', 'label', 'score', 'error', 'input_tokens')
    return [{k: r[k] for k in keys} for r in rows]


def route(base: Sequence[Mapping], few: Sequence[Mapping], positive_threshold: float,
          negative_threshold: float, *, direct: bool = False) -> tuple[list[str], int, int]:
    if len(base) != len(few) or any(not math.isfinite(t) or t < 0 for t in (positive_threshold, negative_threshold)):
        raise ValueError('Aligned arrays and nonnegative finite thresholds required')
    predictions, tokens, escalations = [], 0, 0
    for a, b in zip(base, few):
        if a['id'] != b['id']:
            raise ValueError('Misaligned candidates')
        for r in (a, b):
            if type(r['input_tokens']) is not int or r['input_tokens'] < 0:
                raise ValueError('Nonnegative recorded token count required')
        fallback = direct or a['error'] or a['score'] < (positive_threshold if a['label'] in POSITIVE else negative_threshold)
        predictions.append(b['label'] if fallback else a['label'])
        tokens += (0 if direct else a['input_tokens']) + (b['input_tokens'] if fallback else 0)
        escalations += bool(fallback and not direct)
    return predictions, tokens, escalations


def edges(gold: Sequence[str], predictions: Sequence[str]) -> dict:
    if len(gold) != len(predictions):
        raise ValueError('Aligned gold and predictions required')
    accepted = [i for i, p in enumerate(predictions) if p in POSITIVE]
    correct = sum(predictions[i] == gold[i] for i in accepted)
    possible = sum(g in POSITIVE for g in gold)
    return {'accepted': len(accepted), 'correct': correct, 'wrong': len(accepted)-correct,
            'precision': correct/len(accepted) if accepted else None,
            'recall': correct/possible if possible else None,
            'gold_positive': possible, 'operational_errors': sum(p == 'ERROR' for p in predictions)}


def fit_edge_route(base: Sequence[Mapping], few: Sequence[Mapping], *, split: str) -> dict:
    if split != 'calibration' or not base:
        raise ValueError('Only nonempty calibration data may fit routing')
    gold = [r['gold'] for r in base]
    bf, ff = features(base), features(few)
    reference = edges(gold, [r['label'] for r in few])
    grid = []
    for direct, pt, nt in [(True, 0, 0)] + [(False, a, b) for a in THRESHOLDS for b in THRESHOLDS]:
        pred, tokens, count = route(bf, ff, pt, nt, direct=direct)
        m = edges(gold, pred)
        eligible = (m['wrong'] <= reference['wrong'] and m['correct'] >= .98*reference['correct']
                    and (reference['precision'] is None or
                         m['precision'] is not None and m['precision'] >= reference['precision']-1e-12))
        grid.append({'direct': direct, 'positive_threshold': pt, 'negative_threshold': nt,
                     'input_tokens': tokens, 'escalations': count, 'eligible': eligible, **m})
    winner = min((r for r in grid if r['eligible']),
                 key=lambda r: (r['input_tokens'], not r['direct'], r['positive_threshold'], r['negative_threshold']))
    return {'policy': {k: winner[k] for k in ('direct', 'positive_threshold', 'negative_threshold')},
            'reference': reference, 'calibration_winner': winner, 'grid': grid}


def stable_ids(old: Sequence[Mapping], new: Sequence[Mapping]) -> set[str]:
    if len(old) != len(new) or any(a['id'] != b['id'] for a, b in zip(old, new)):
        raise ValueError('Aligned old and new candidates required')
    return {b['id'] for a, b in zip(old, new)
            if not a['error'] and not b['error'] and a['label'] == b['label'] and b['label'] in POSITIVE}


def supported(a: Mapping) -> bool:
    for key in ('subject', 'predicate', 'object', 'scope'):
        if not isinstance(a.get(key), str) or not a[key]:
            return False
    if type(a.get('polarity')) is not int or a['polarity'] not in (-1, 1):
        return False
    if 'start' not in a or 'end' not in a:
        return False
    if any(a[k] is not None and type(a[k]) is not int for k in ('start', 'end')):
        return False
    return a['start'] is None or a['end'] is None or a['start'] < a['end']


def semantic_collision(a: Mapping, b: Mapping, functional: frozenset[str]) -> bool:
    if (a['subject'], a['predicate']) != (b['subject'], b['predicate']):
        return False
    return ((a['object'] == b['object'] and a['polarity'] != b['polarity']) or
            (a['predicate'] in functional and a['object'] != b['object'] and a['polarity'] == b['polarity'] == 1))


def conflict(a: Mapping, b: Mapping, functional: frozenset[str] = frozenset()) -> str:
    """Three-way result. Unknown is staged, never silently treated as no conflict."""
    if not supported(a) or not supported(b):
        return 'unknown'
    if a['scope'] != b['scope'] or not semantic_collision(a, b, functional):
        return 'clear'
    start = max(-math.inf if a['start'] is None else a['start'], -math.inf if b['start'] is None else b['start'])
    end = min(math.inf if a['end'] is None else a['end'], math.inf if b['end'] is None else b['end'])
    return 'conflict' if start < end else 'clear'


def proof_bounds(proofs: Sequence[Sequence[str]], probabilities: Mapping[str, float]) -> dict:
    """Bounds for OR of AND proofs; primitive events must be independent.

    Sharing a primitive creates dependence between proofs. Disjoint atom sets
    define independent components, but NOT independent proofs within a component.
    """
    for p in probabilities.values():
        validate_probability(p)
    unique = sorted({tuple(sorted(set(p))) for p in proofs})
    if any(not p or any(a not in probabilities for a in p) for p in unique):
        raise ValueError('Nonempty proofs with known primitive atoms required')
    if not unique:
        return {'lower': 0., 'upper': 0., 'components': 0, 'unique_proofs': 0}
    components = []
    todo = set(range(len(unique)))
    while todo:
        group = {min(todo)}
        todo -= group
        atoms = set(unique[next(iter(group))])
        while True:
            extra = {i for i in todo if atoms.intersection(unique[i])}
            if not extra:
                break
            group |= extra
            todo -= extra
            atoms.update(a for i in extra for a in unique[i])
        components.append(sorted(group))
    bounds = []
    for group in components:
        p = [math.prod(probabilities[a] for a in unique[i]) for i in group]
        bounds.append((max(p), min(1., sum(p))))
    return {'lower': 1-math.prod(1-p[0] for p in bounds),
            'upper': 1-math.prod(1-p[1] for p in bounds),
            'components': len(components), 'unique_proofs': len(unique)}


def exact_probability(proofs: Sequence[Sequence[str]], probabilities: Mapping[str, float]) -> float:
    """Bounded exhaustive oracle, separate from the component-bounds algorithm."""
    if len(probabilities) > 12:
        raise ValueError('Exact oracle limited to 12 primitive events')
    for p in probabilities.values():
        validate_probability(p)
    if any(not p or not set(p) <= probabilities.keys() for p in proofs):
        raise ValueError('Unknown or empty proof')
    atoms = sorted(probabilities)
    total = 0.
    for outcomes in product((False, True), repeat=len(atoms)):
        active = {a for a, yes in zip(atoms, outcomes) if yes}
        if any(set(p) <= active for p in proofs):
            total += math.prod(probabilities[a] if yes else 1-probabilities[a] for a, yes in zip(atoms, outcomes))
    return total
