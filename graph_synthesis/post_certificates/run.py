"""Execute the frozen post-certificate suite with no service calls."""
from __future__ import annotations

import argparse
from itertools import combinations
import json
import math
from pathlib import Path
import random
import socket
import statistics
from unittest.mock import patch

import numpy as np

from . import methods
from ..adaptive.run import load, INPUT
from ..certificates import risk, lineage, graphs
from ..certificates.run import experiment_lineage, independent_sets, valid_repair
from ..reliability.run import calibration, proper_scores

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SEED = 20260923
DRAWS = 4000
BASELINE_COMMIT = "9d2e4a60a6c79e616ab1d352cd5da9fe414e6c98"
PROTOCOL_COMMIT = "f923e8d41ca5953d9793fadcc3730cfe9fc70b3a"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def normalized(value):
    return json.loads(json.dumps(value, sort_keys=True, allow_nan=False))


def bootstrap(deltas):
    values = np.asarray(deltas, dtype=float)
    rng = np.random.default_rng(SEED)
    sample = values[rng.integers(0, len(values), size=(DRAWS, len(values)))].mean(axis=1)
    return {"point": float(values.mean()), "95": np.quantile(sample, [.025, .975]).tolist(),
            "99": np.quantile(sample, [.005, .995]).tolist(), "groups": len(values), "draws": DRAWS}


def choose_weight(rows):
    if not rows:
        raise ValueError("Need development folds")
    grid = []
    for i in range(11):
        w = i / 10
        brier = statistics.mean((w*r["feature"] + (1-w)*r["random"] - r["truth"])**2 for r in rows)
        grid.append({"weight": w, "brier": brier})
    best = min(grid, key=lambda r: (r["brier"], abs(r["weight"]-.5), r["weight"]))
    return best["weight"], grid


def experiment_stack(development, test):
    feature = calibration(development, test)
    feature_folds = {r["group"]: r for r in feature["folds"]}
    folds = []
    for group in sorted({r["group"] for r in development}):
        held = [r for r in development if r["group"] == group]
        exposure = risk.counts(held)
        if not exposure or group not in feature_folds:
            continue
        training = [r for r in development if r["group"] != group]
        fitted = risk.fit(training)
        random_p = risk.predict(exposure, fitted)[group]
        folds.append({"group": group, "n": exposure[group], "feature": feature_folds[group]["probability"],
                      "random": random_p, "truth": feature_folds[group]["truth"]})
    global_w, global_grid = choose_weight(folds)
    weights = {"global": global_w}
    grids = {"global": global_grid}
    for name, predicate in (("singleton", lambda r: r["n"] == 1), ("multi", lambda r: r["n"] > 1)):
        subset = [r for r in folds if predicate(r)]
        if len(subset) >= 8:
            weights[name], grids[name] = choose_weight(subset)
        else:
            weights[name], grids[name] = global_w, []

    fitted = risk.fit(development)
    exposure = risk.counts(test)
    actual = risk.counts(test, truth=True)
    truth = {g: int(v["k"] > 0) for g, v in actual.items()}
    random_pred = risk.predict(exposure, fitted)
    feature_pred = {r["group"]: r["baseline"] for r in feature["group_predictions"]}
    if set(random_pred) != set(feature_pred) or set(truth) != set(random_pred):
        raise ValueError("H1 group denominator mismatch")
    stacked = {}
    rows = []
    for g in sorted(truth):
        stratum = "singleton" if exposure[g] == 1 else "multi"
        w = weights[stratum]
        p = w * feature_pred[g] + (1-w) * random_pred[g]
        stacked[g] = p
        rows.append({"group": g, "n": exposure[g], "stratum": stratum, "weight": w, "feature": feature_pred[g],
                     "random": random_pred[g], "stacked": p, "truth": truth[g]})
    scores = {"feature": proper_scores(feature_pred, truth), "random_effects": proper_scores(random_pred, truth),
              "stacked": proper_scores(stacked, truth)}
    primary = (scores["stacked"]["brier"] <= scores["feature"]["brier"] + 1e-15
               and scores["stacked"]["brier"] <= .97 * scores["random_effects"]["brier"] + 1e-15
               and abs(scores["stacked"]["bias"]) <= .03)
    return {"primary_target_met": primary, "weights": weights, "grids": grids, "folds": folds,
            "fold_counts": {"all": len(folds), "singleton": sum(r["n"] == 1 for r in folds), "multi": sum(r["n"] > 1 for r in folds)},
            "test_counts": {"groups": len(rows), "singleton": sum(r["n"] == 1 for r in rows), "multi": sum(r["n"] > 1 for r in rows)},
            "scores": scores, "predictions": rows,
            "paired_vs_feature": bootstrap([(stacked[g]-truth[g])**2-(feature_pred[g]-truth[g])**2 for g in sorted(truth)]),
            "paired_vs_random": bootstrap([(stacked[g]-truth[g])**2-(random_pred[g]-truth[g])**2 for g in sorted(truth)])}


def pair_probability(case, pair):
    atoms = sorted(case["probabilities"])
    pos = {a: i for i, a in enumerate(atoms)}
    return sum(v for world, v in enumerate(case["actual_joint"]) if all(world & (1 << pos[a]) for a in pair))


def experiment_constraint_acquisition():
    source = experiment_lineage()
    cases = []
    containment_failures = widening_failures = 0
    base_widths, greedy_widths, lex_widths = [], [], []
    for case in source["random_cases"]:
        atoms = sorted(case["probabilities"])
        pairs = list(combinations(atoms, 2))
        pair_values = {pair: pair_probability(case, pair) for pair in pairs}
        base = lineage.bounds(case["proofs"], case["probabilities"])
        current, selected, steps = base, [], []
        remaining = set(pairs)
        for _ in range(min(3, len(remaining))):
            candidates = []
            for pair in sorted(remaining):
                constraints = [(list(p), pair_values[p]) for p in selected + [pair]]
                result = lineage.bounds(case["proofs"], case["probabilities"], constraints)
                candidates.append((result["upper"]-result["lower"], pair, result))
            width, pair, result = min(candidates, key=lambda x: (x[0], x[1]))
            if width > current["upper"]-current["lower"] + 1e-8:
                widening_failures += 1
            selected.append(pair)
            remaining.remove(pair)
            steps.append({"pair": list(pair), "probability": pair_values[pair], "result": result})
            current = result
        lex_pairs = pairs[:3]
        lex = lineage.bounds(case["proofs"], case["probabilities"], [(list(p), pair_values[p]) for p in lex_pairs])
        truth = case["truth"]
        if not current["lower"] - 1e-8 <= truth <= current["upper"] + 1e-8:
            containment_failures += 1
        base_widths.append(base["upper"]-base["lower"])
        greedy_widths.append(current["upper"]-current["lower"])
        lex_widths.append(lex["upper"]-lex["lower"])
        cases.append({"id": case["id"], "truth": truth, "base": base, "greedy": current, "lexicographic": lex,
                      "selected": [list(p) for p in selected], "steps": steps})
    means = {"marginal": statistics.mean(base_widths), "greedy": statistics.mean(greedy_widths),
             "lexicographic": statistics.mean(lex_widths)}
    primary = (containment_failures == 0 and widening_failures == 0
               and means["greedy"] <= .75 * means["marginal"] + 1e-12
               and means["greedy"] <= .90 * means["lexicographic"] + 1e-12)
    return {"primary_target_met": primary, "cases": cases, "means": means,
            "containment_failures": containment_failures, "widening_failures": widening_failures,
            "budget": 3, "source_fixture_count": len(cases)}


def exhaustive_oracle(weights, edges):
    return max(independent_sets(weights, edges), key=lambda x: (x[0], tuple(x[1])))[0]


def experiment_near_bipartite():
    rng = random.Random(SEED + 3)
    small, failures, invariance_failures = [], 0, 0
    for case in range(128):
        n = rng.randrange(6, 13)
        s = rng.randrange(1, min(4, n-2))
        sep = [f"s{i}" for i in range(s)]
        residual = [f"v{i}" for i in range(n-s)]
        split = max(1, len(residual)//2)
        left, right = residual[:split], residual[split:]
        weights = {v: rng.randrange(10) for v in sep + residual}
        edges = [(a, b) for a in left for b in right if rng.random() < .35]
        edges += [(a, b) for a in sep for b in residual if rng.random() < .35]
        edges += [(a, b) for a, b in combinations(sep, 2) if rng.random() < .25]
        oracle = exhaustive_oracle(weights, edges)
        result = methods.near_bipartite_solve(weights, edges, sep)
        reordered = methods.near_bipartite_solve(dict(reversed(list(weights.items()))), list(reversed(edges))*2, list(reversed(sep)))
        ok = not result["staged"] and result["utility"] == oracle and valid_repair(weights, edges, result["selected"], oracle)
        failures += int(not ok)
        invariance_failures += int(result["utility"] != reordered["utility"] or result["selected"] != reordered["selected"])
        small.append({"id": case, "weights": weights, "edges": edges, "separator": sep, "oracle": oracle, "result": result, "ok": ok})

    large = []
    for n in (512, 1024, 2048):
        weights = {f"v{i:04}": 1 for i in range(n)}
        weights["apex"] = 3
        edges = [(f"v{i:04}", f"v{(i+1)%n:04}") for i in range(n)]
        edges += [("apex", "v0000"), ("apex", "v0001")]
        result = methods.near_bipartite_solve(weights, edges, ["apex"])
        prior = graphs.solve(weights, edges)
        expected = n//2 + 2
        ok = result["utility"] == expected and not result["staged"] and len(prior["staged"]) == n+1
        failures += int(not ok)
        large.append({"residual_vertices": n, "expected": expected, "result_utility": result["utility"],
                      "prior_staged": len(prior["staged"]), "ok": ok})
    invalid = methods.near_bipartite_solve({"a":1,"b":1,"c":1}, [("a","b"),("b","c"),("c","a")], [])
    malformed = methods.near_bipartite_solve({str(i):1 for i in range(6)}, [], [str(i) for i in range(5)])
    controls_ok = bool(invalid["staged"]) and bool(malformed["staged"])
    failures += int(not controls_ok)
    return {"primary_target_met": failures == 0 and invariance_failures == 0 and all(r["ok"] for r in large),
            "small": small, "small_failures": failures - int(not controls_ok) - sum(int(not r["ok"]) for r in large),
            "invariance_failures": invariance_failures, "large": large,
            "controls": {"non_transversal": invalid, "over_cap": malformed, "ok": controls_ok}}


def witness_ok(weights, edges, selected, threshold, include=None, exclude=None):
    selected = list(selected or [])
    if not valid_repair(weights, edges, selected, threshold):
        return False
    chosen = set(selected)
    return (include is None or include in chosen) and (exclude is None or exclude not in chosen)


def experiment_query_index():
    rng = random.Random(SEED + 4)
    cases, mismatches, witness_failures = [], 0, 0
    baseline_calls = index_calls = query_count = 0
    actual_baseline_calls = 0
    for case in range(128):
        n = rng.randrange(4, 11)
        weights = {f"v{i}": rng.randrange(10) for i in range(n)}
        edges = [(a, b) for a, b in combinations(weights, 2) if rng.random() < .28]
        index = methods.build_margin_index(weights, edges)
        if index["status"] != "indexed":
            raise AssertionError("Small H4 fixture unexpectedly staged")
        index_calls += index["solve_calls"]
        trials = []
        epsilons = sorted({0, 1, 2, math.floor(.05*index["optimum"]), math.floor(.10*index["optimum"])})
        for v in sorted(weights):
            for epsilon in epsilons:
                query_count += 1
                baseline_calls += 3
                old = graphs.query(weights, edges, [v], epsilon=epsilon)
                actual_baseline_calls += 2 if old["classification"] == "impossible" else 3
                new = methods.query_margin(index, v, epsilon)
                same = old["classification"] == new["classification"]
                mismatches += int(not same)
                threshold = index["optimum"] - epsilon
                ok = same
                if new["classification"] in ("certain", "ambiguous"):
                    ok = ok and witness_ok(weights, edges, new["possible_repair"], threshold, include=v)
                if new["classification"] == "ambiguous":
                    ok = ok and witness_ok(weights, edges, new["counterexample"], threshold, exclude=v)
                witness_failures += int(not ok)
                trials.append({"vertex": v, "epsilon": epsilon, "old": old["classification"], "new": new["classification"], "ok": ok})
        cases.append({"id": case, "n": n, "optimum": index["optimum"], "epsilons": epsilons, "trials": trials,
                      "index_solve_calls": index["solve_calls"]})
    saving = 1 - index_calls / baseline_calls
    conservative_saving = 1 - index_calls / actual_baseline_calls
    return {"primary_target_met": mismatches == 0 and witness_failures == 0 and saving >= .70,
            "cases": cases, "queries": query_count, "mismatches": mismatches, "witness_failures": witness_failures,
            "baseline_solve_calls_frozen": baseline_calls, "baseline_solve_calls_actual_control": actual_baseline_calls,
            "index_solve_calls": index_calls, "saving": saving, "conservative_saving": conservative_saving}


def fact_truth(proofs, joint, atoms):
    pos = {a: i for i, a in enumerate(atoms)}
    return sum(v for world, v in enumerate(joint)
               if any(all(world & (1 << pos[a]) for a in proof) for proof in proofs))


def experiment_interval_marginals():
    rng = random.Random(SEED + 5)
    cases, containment_failures = [], 0
    interval_widths, point_widths = [], []
    for case in range(128):
        n = rng.randrange(2, 7)
        atoms = [f"a{i}" for i in range(n)]
        masses = [rng.randrange(1, 100) for _ in range(1 << n)]
        total = sum(masses)
        joint = [v/total for v in masses]
        marginals = {a: sum(v for world, v in enumerate(joint) if world & (1 << i)) for i, a in enumerate(atoms)}
        proofs = [sorted(rng.sample(atoms, rng.randrange(1, min(3,n)+1))) for _ in range(rng.randrange(1, 7))]
        truth = fact_truth(proofs, joint, atoms)
        intervals, points = {}, {}
        for a in atoms:
            radius = rng.uniform(.02, .10)
            lo, hi = max(0., marginals[a]-radius), min(1., marginals[a]+radius)
            points[a] = min(hi, max(lo, marginals[a] + rng.uniform(-.9*radius, .9*radius)))
            intervals[a] = [lo, hi]
        interval_result = methods.interval_lineage_bounds(proofs, intervals)
        point_result = methods.exact_point_bounds(proofs, points)
        ok = interval_result["certified"] and interval_result["lower"]-1e-7 <= truth <= interval_result["upper"]+1e-7
        containment_failures += int(not ok)
        interval_widths.append(interval_result["upper"]-interval_result["lower"])
        point_widths.append(point_result["upper"]-point_result["lower"])
        cases.append({"id": case, "proofs": proofs, "truth": truth, "true_marginals": marginals, "intervals": intervals,
                      "point_estimates": points, "interval_result": interval_result, "point_result": point_result, "ok": ok})

    controls, prevented = [], 0
    for i in range(20):
        actual = .80 + .007*i
        point = .97 + .001*i
        intervals = {"a": [max(0., actual-.01), min(1., point+.005)]}
        exact = methods.exact_point_bounds([["a"]], {"a": point})
        robust = methods.interval_lineage_bounds([["a"]], intervals)
        blocked = exact["lower"] >= .95 and actual < .95 and robust["lower"] < .95
        prevented += int(blocked)
        controls.append({"actual": actual, "point": point, "interval": intervals["a"], "point_result": exact,
                         "interval_result": robust, "prevented": blocked})
    malformed = [
        methods.interval_lineage_bounds([["a"]], {"a": [.8, .7]}),
        methods.interval_lineage_bounds([["a"]], {"a": [float("nan"), .9]}),
        methods.interval_lineage_bounds([["a"]], {"a": [-.1, .9]}),
        methods.interval_lineage_bounds([["missing"]], {"a": [.1, .9]}),
        methods.interval_lineage_bounds([["a0"]], {f"a{i}":[.1,.9] for i in range(11)})
    ]
    malformed_certifying = sum(int(r.get("certified", False)) for r in malformed)
    means = {"point_width": statistics.mean(point_widths), "interval_width": statistics.mean(interval_widths)}
    return {"primary_target_met": containment_failures == 0 and prevented == 20 and malformed_certifying == 0,
            "cases": cases, "containment_failures": containment_failures, "controls": controls,
            "false_admissions_prevented": prevented, "malformed": malformed,
            "malformed_certifying": malformed_certifying, "means": means}


def execute():
    values, calls, audit = load()
    development = [r for r in values if r["split"] == "development"]
    test = [r for r in values if r["split"] == "test"]
    if (len(development), len(test)) != (73, 263):
        raise ValueError("Frozen input split changed")
    if {r["group"] for r in development}.intersection(r["group"] for r in test):
        raise ValueError("Source-group leakage")
    result = {"schema_version": 1, "baseline_commit": BASELINE_COMMIT, "protocol_commit": PROTOCOL_COMMIT,
              "fresh_service_calls": 0, "seed": SEED,
              "evidence": "H1 saved-response reuse; H2-H5 controlled algorithmic fixtures. No independent semantic generalization.",
              "input_verification": audit,
              "development": {"n": len(development), "groups": len({r["group"] for r in development})},
              "test": {"n": len(test), "groups": len({r["group"] for r in test})},
              "H1": experiment_stack(development, test),
              "H2": experiment_constraint_acquisition(),
              "H3": experiment_near_bipartite(),
              "H4": experiment_query_index(),
              "H5": experiment_interval_marginals()}
    return normalized(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    with patch.object(socket.socket, "connect", side_effect=RuntimeError("Network forbidden in post-certificate replay")), \
         patch.object(socket, "create_connection", side_effect=RuntimeError("Network forbidden in post-certificate replay")):
        result = execute()
    if args.check:
        from ..verify import compare_json
        compare_json(json.loads((HERE/"results.json").read_text(encoding="utf-8")), result)
    else:
        write(HERE/"results.json", result)
    print(json.dumps({"status": "reproduced" if args.check else "executed",
                      "targets": {k: result[k]["primary_target_met"] for k in ("H1","H2","H3","H4","H5")},
                      "fresh_service_calls": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
