"""Source-count random effects; forecasting never receives evaluation labels."""
from __future__ import annotations
from collections import defaultdict
import math

POSITIVE = frozenset(('SUPPORTS', 'REFUTES'))
RHO_GRID = (0.0, 0.01, 0.05, 0.1, 0.2, 0.4, 0.6, 0.8)


def counts(rows, *, truth=False):
    """Return accepted exposure, optionally training/evaluation error counts."""
    out = defaultdict(lambda: {'n': 0, 'k': 0})
    for row in rows:
        label = row['views']['base1']['label']
        if label in POSITIVE:
            value = out[row['group']]
            value['n'] += 1
            if truth:
                value['k'] += int(label != row['gold'])
    return {g: v if truth else v['n'] for g, v in sorted(out.items())}


def contamination(n, mu, rho):
    if type(n) is not int or n < 0:
        raise ValueError('Exposure must be a nonnegative integer')
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in (mu, rho)):
        raise ValueError('Finite real parameters required')
    if not 0 <= mu <= 1 or not 0 <= rho < 1:
        raise ValueError('Require mu in [0,1] and rho in [0,1)')
    if n == 0 or mu == 0:
        return 0.0
    if mu == 1:
        return 1.0
    if rho == 0:
        return -math.expm1(n * math.log1p(-mu))
    a, b = mu * (1 / rho - 1), (1 - mu) * (1 / rho - 1)
    log_zero = math.lgamma(b + n) - math.lgamma(a + b + n) + math.lgamma(a + b) - math.lgamma(b)
    return min(1.0, max(0.0, -math.expm1(log_zero)))


def log_mass(k, n, mu, rho):
    combinatorial = math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
    if rho == 0:
        return combinatorial + k * math.log(mu) + (n - k) * math.log1p(-mu)
    a, b = mu * (1 / rho - 1), (1 - mu) * (1 / rho - 1)
    return (combinatorial + math.lgamma(a + k) + math.lgamma(b + n - k)
            - math.lgamma(a + b + n) - math.lgamma(a) - math.lgamma(b) + math.lgamma(a + b))


def fit(development):
    development = list(development)
    if not development or any(r.get('split') != 'development' for r in development):
        raise ValueError('Fit accepts nonempty development rows only')
    grouped = counts(development, truth=True)
    n = sum(v['n'] for v in grouped.values())
    if not n:
        raise ValueError('No accepted development edges')
    wrong = sum(v['k'] for v in grouped.values())
    mu = (wrong + 0.5) / (n + 1)
    grid = [{'rho': rho, 'log_likelihood': sum(log_mass(v['k'], v['n'], mu, rho) for v in grouped.values())}
            for rho in RHO_GRID]
    best = min(grid, key=lambda v: (-v['log_likelihood'], v['rho']))
    return {'mu': mu, 'rho': best['rho'], 'grid': grid, 'accepted_edges': n, 'wrong_edges': wrong,
            'fit_groups': sorted({r['group'] for r in development}), 'counts': grouped}


def predict(exposures, model, *, independent=False):
    """Only group IDs and counts are consumed, never responses or gold."""
    return {g: contamination(n, model['mu'], 0.0 if independent else model['rho'])
            for g, n in sorted(exposures.items())}
