"""Bounded possible-world LP; no independence assumption or Jev-score semantics."""
from __future__ import annotations
import math
import numpy as np
from scipy.optimize import linprog

PAD = 1e-9


def _probability(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError('Supplied probabilities must be finite reals in [0,1]')
    return float(value)


def _stage(reason, atoms):
    return {'status': reason, 'certified': False, 'lower': 0.0, 'upper': 1.0, 'atoms': atoms}


def bounds(proofs, probabilities, joints=(), *, atom_cap=10):
    """Extremal probability of a monotone DNF given marginals/conjunctions.

    joints contains (atom_sequence, probability) pairs. These are assertions
    supplied by the caller, not inferred dependencies. Empty DNF is false and
    an empty conjunction is true. Over-budget/failed LPs cannot admit a fact.
    """
    if type(atom_cap) is not int or not 0 <= atom_cap <= 10:
        raise ValueError('Atom cap must be an integer in [0,10]')
    if any(not isinstance(k, str) or not k for k in probabilities):
        raise ValueError('Nonempty string atom IDs required')
    atoms = sorted(probabilities)
    marginals = {a: _probability(probabilities[a]) for a in atoms}
    def term(value):
        if isinstance(value, str):
            raise ValueError('A proof must be an atom sequence, not a string')
        result = tuple(sorted(set(value)))
        if any(a not in marginals for a in result):
            raise ValueError('Unknown proof atom')
        return result
    terms = sorted({term(p) for p in proofs})
    constraints = sorted((term(p), _probability(v)) for p, v in joints)
    if len(atoms) > atom_cap or len(terms) > 256 or len(constraints) > 256:
        return _stage('capacity_staged', len(atoms))
    positions = {a: i for i, a in enumerate(atoms)}
    worlds = np.arange(1 << len(atoms), dtype=np.int64)
    def indicator(p):
        mask = sum(1 << positions[a] for a in p)
        return ((worlds & mask) == mask).astype(float)
    objective = np.zeros(len(worlds))
    for p in terms:
        objective = np.maximum(objective, indicator(p))
    matrix = np.array([np.ones(len(worlds))] + [indicator((a,)) for a in atoms] + [indicator(p) for p, _ in constraints])
    target = np.array([1.0] + [marginals[a] for a in atoms] + [v for _, v in constraints])
    solutions = []
    for sign in (1, -1):
        c = sign * objective
        result = linprog(c, A_eq=matrix, b_eq=target, bounds=(0, None), method='highs',
                         options={'dual_feasibility_tolerance': 1e-9, 'primal_feasibility_tolerance': 1e-9})
        if not result.success:
            return _stage('infeasible_constraints' if result.status == 2 else 'solver_staged', len(atoms))
        x, dual = np.asarray(result.x), np.asarray(result.eqlin.marginals)
        if not np.isfinite(x).all() or not np.isfinite(dual).all():
            return _stage('nonfinite_staged', len(atoms))
        residual = float(np.max(np.abs(matrix @ x - target)))
        if residual > 1e-7 or float(np.min(x)) < -1e-9:
            return _stage('residual_staged', len(atoms))
        # For any feasible world vector z, sum(z)=1, z>=0:
        # c.z >= target.dual + min(0, min(c - A.T.dual)).
        # This corrects a numerically imperfect dual using the simplex mass.
        slack = float(min(0.0, np.min(c - matrix.T @ dual)))
        padding = PAD * (1.0 + float(np.abs(dual).sum()))
        lower_dual = float(target @ dual) + slack - padding
        solutions.append({'signed_primal': float(c @ x), 'dual_lower': lower_dual,
                          'residual': residual, 'padding': padding, 'dual': dual.tolist(),
                          'support': [[int(i), float(v)] for i, v in enumerate(x) if v > 0]})
    lo, hi = max(0.0, solutions[0]['dual_lower']), min(1.0, -solutions[1]['dual_lower'])
    if not math.isfinite(lo + hi) or lo > hi + 1e-8:
        return _stage('inconsistent_numerics_staged', len(atoms))
    return {'status': 'bounded', 'certified': True, 'lower': lo, 'upper': hi, 'atoms': len(atoms),
            'worlds': len(worlds), 'constraints': len(target), 'min': solutions[0], 'max': solutions[1],
            'assumption': 'Bounds conditional on exact supplied constraints; outward-padded floating-point dual bounds, not formal interval arithmetic.'}
