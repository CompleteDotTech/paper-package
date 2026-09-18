"""Second-order research mechanisms derived from the dependence-aware certificate study."""
from __future__ import annotations

from itertools import combinations
import math
import numpy as np
from scipy.optimize import linprog

from ..reliability.methods import graph_input
from ..certificates import graphs

PAD = 1e-7


def _staged(reason, atoms=0):
    return {"status": reason, "certified": False, "lower": 0.0, "upper": 1.0, "atoms": atoms}


def interval_lineage_bounds(proofs, intervals, *, atom_cap=10):
    """Extremal monotone-DNF probability under interval-valued atom marginals."""
    try:
        if type(atom_cap) is not int or not 0 <= atom_cap <= 10:
            return _staged("invalid_atom_cap")
        if not isinstance(intervals, dict) or any(not isinstance(a, str) or not a for a in intervals):
            return _staged("invalid_intervals")
        atoms = sorted(intervals)
        bounds = {}
        for a in atoms:
            pair = intervals[a]
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                return _staged("invalid_intervals", len(atoms))
            lo, hi = pair
            if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (lo, hi)):
                return _staged("invalid_intervals", len(atoms))
            lo, hi = float(lo), float(hi)
            if not 0 <= lo <= hi <= 1:
                return _staged("invalid_intervals", len(atoms))
            bounds[a] = (lo, hi)
        if len(atoms) > atom_cap:
            return _staged("capacity_staged", len(atoms))

        def term(value):
            if isinstance(value, str):
                raise ValueError
            result = tuple(sorted(set(value)))
            if any(a not in bounds for a in result):
                raise ValueError
            return result

        terms = sorted({term(p) for p in proofs})
        if len(terms) > 256:
            return _staged("capacity_staged", len(atoms))
        positions = {a: i for i, a in enumerate(atoms)}
        worlds = np.arange(1 << len(atoms), dtype=np.int64)

        def indicator(term_atoms):
            mask = sum(1 << positions[a] for a in term_atoms)
            return ((worlds & mask) == mask).astype(float)

        objective = np.zeros(len(worlds))
        for p in terms:
            objective = np.maximum(objective, indicator(p))

        eq = np.ones((1, len(worlds)))
        eq_target = np.array([1.0])
        ub_rows, ub_targets = [], []
        atom_vectors = {}
        for a in atoms:
            vec = indicator((a,))
            atom_vectors[a] = vec
            lo, hi = bounds[a]
            ub_rows.extend([vec, -vec])
            ub_targets.extend([hi, -lo])
        aub = np.asarray(ub_rows, dtype=float) if ub_rows else None
        bub = np.asarray(ub_targets, dtype=float) if ub_targets else None

        solutions = []
        for sign in (1.0, -1.0):
            result = linprog(sign * objective, A_ub=aub, b_ub=bub, A_eq=eq, b_eq=eq_target,
                             bounds=(0, None), method="highs",
                             options={"dual_feasibility_tolerance": 1e-9, "primal_feasibility_tolerance": 1e-9})
            if not result.success or result.x is None:
                return _staged("infeasible_or_solver_staged", len(atoms))
            x = np.asarray(result.x, dtype=float)
            if not np.isfinite(x).all() or float(np.min(x)) < -1e-8 or abs(float(x.sum()) - 1.0) > 1e-7:
                return _staged("residual_staged", len(atoms))
            marginals = {a: float(atom_vectors[a] @ x) for a in atoms}
            if any(marginals[a] < bounds[a][0] - 1e-7 or marginals[a] > bounds[a][1] + 1e-7 for a in atoms):
                return _staged("residual_staged", len(atoms))
            value = float(objective @ x)
            solutions.append({"value": value, "support": [[int(i), float(v)] for i, v in enumerate(x) if v > 1e-12],
                              "marginals": marginals})
        lo = max(0.0, solutions[0]["value"] - PAD)
        hi = min(1.0, solutions[1]["value"] + PAD)
        if lo > hi + 1e-7:
            return _staged("numeric_inconsistency", len(atoms))
        return {"status": "bounded", "certified": True, "lower": lo, "upper": hi, "atoms": len(atoms),
                "worlds": len(worlds), "min": solutions[0], "max": solutions[1],
                "assumption": "Every supplied marginal interval contains the true atom probability; numerical LP bounds are outward padded."}
    except (TypeError, ValueError, KeyError, OverflowError):
        return _staged("invalid_input")


def exact_point_bounds(proofs, probabilities):
    return interval_lineage_bounds(proofs, {a: (p, p) for a, p in probabilities.items()})


def near_bipartite_solve(weights, edges, separator, *, separator_cap=4):
    """Exact MWIS by conditioning on a verified small separator whose removal is bipartite."""
    try:
        edges = [tuple(e) for e in edges]
        adj = graph_input(weights, edges)
        if isinstance(separator, str):
            raise ValueError
        sep = tuple(sorted(set(separator)))
        if len(sep) > separator_cap or any(v not in weights for v in sep):
            return {"selected": [], "staged": sorted(weights), "utility": 0, "status": "separator_staged", "branches": []}
        residual_nodes = [v for v in weights if v not in sep]
        residual_weights = {v: weights[v] for v in residual_nodes}
        residual_edges = [(a, b) for a, b in edges if a in residual_weights and b in residual_weights]
        radj = graph_input(residual_weights, residual_edges)
        if any(graphs.coloring(radj, g) is None for g in graphs.groups(radj)):
            return {"selected": [], "staged": sorted(weights), "utility": 0, "status": "not_transversal", "branches": []}

        best = None
        branches = []
        for mask in range(1 << len(sep)):
            chosen = {sep[i] for i in range(len(sep)) if mask & (1 << i)}
            if any(b in adj[a] for a, b in combinations(sorted(chosen), 2)):
                continue
            blocked = set(sep)
            for v in chosen:
                blocked.update(adj[v])
            rw = {v: w for v, w in weights.items() if v not in blocked}
            re = [(a, b) for a, b in edges if a in rw and b in rw]
            residual = graphs.solve(rw, re)
            if residual["staged"]:
                branches.append({"chosen_separator": sorted(chosen), "status": "residual_staged"})
                continue
            selected = sorted(chosen | set(residual["selected"]))
            utility = sum(weights[v] for v in selected)
            branch = {"chosen_separator": sorted(chosen), "selected": selected, "utility": utility,
                      "residual_components": residual["components"], "status": "solved"}
            branches.append(branch)
            if best is None or utility > best["utility"] or (utility == best["utility"] and tuple(selected) < tuple(best["selected"])):
                best = branch
        if best is None:
            return {"selected": [], "staged": sorted(weights), "utility": 0, "status": "residual_staged", "branches": branches}
        return {"selected": best["selected"], "staged": [], "utility": best["utility"], "status": "solved",
                "separator": list(sep), "branches": branches}
    except (TypeError, ValueError, KeyError, ArithmeticError):
        return {"selected": [], "staged": sorted(weights) if isinstance(weights, dict) else [], "utility": 0,
                "status": "invalid_input", "branches": []}


def build_margin_index(weights, edges):
    base = graphs.solve(weights, edges)
    if base["staged"]:
        return {"status": "staged", "optimum": None, "entries": {}, "solve_calls": 1}
    entries = {}
    for v in sorted(weights):
        inc = graphs.forced(weights, edges, include=[v])
        exc = graphs.forced(weights, edges, exclude=[v])
        if inc is None or inc["staged"] or exc["staged"]:
            return {"status": "staged", "optimum": base["utility"], "entries": entries, "solve_calls": 1 + 2 * len(entries)}
        entries[v] = {"include_utility": inc["utility"], "include_witness": inc["selected"],
                      "exclude_utility": exc["utility"], "exclude_witness": exc["selected"]}
    return {"status": "indexed", "optimum": base["utility"], "entries": entries, "solve_calls": 1 + 2 * len(entries)}


def query_margin(index, vertex, epsilon=0):
    if index.get("status") != "indexed" or vertex not in index["entries"] or type(epsilon) is not int or epsilon < 0:
        return {"classification": "unsupported"}
    threshold = index["optimum"] - epsilon
    entry = index["entries"][vertex]
    record = {"threshold": threshold, "optimum": index["optimum"], "epsilon": epsilon, "required": [vertex],
              "possible_repair": None, "counterexample": None}
    if entry["include_utility"] < threshold:
        return {**record, "classification": "impossible"}
    record["possible_repair"] = entry["include_witness"]
    if entry["exclude_utility"] < threshold:
        return {**record, "classification": "certain"}
    record["counterexample"] = entry["exclude_witness"]
    return {**record, "classification": "ambiguous"}
