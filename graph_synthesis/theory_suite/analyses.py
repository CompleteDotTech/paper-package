"""T01--T06: exploratory analyses of exact archived observations."""
from __future__ import annotations
from collections import defaultdict
import math
from pathlib import Path
import random
from typing import Any

from graph_synthesis.core import components, digest
from graph_synthesis.recorded import BASELINES, LABELS, RecordedJev
from graph_synthesis.study import read_scores
from .methods import (admit_budget, cascade_predict, conformal_fit, fit_cascade,
                      macro_f1, prediction_set, projected_precision, review_selection)

SEED = 20260918
BOOTSTRAPS = 500
FEW = "fewshot_contract"


def endpoints(task: str, row: dict[str, Any]) -> tuple[str, str]:
    if task == "relation_support":
        return "document:" + row["document_id"], "claim:" + row["claim_id"]
    return "record:" + row["entity_1"], "record:" + row["entity_2"]


def purge_groups(calibration: list[dict], evaluation: list[dict]) -> tuple[list[dict], dict]:
    all_rows = calibration + evaluation
    nodes = {n for row in all_rows for n in row["endpoints"]}
    groups = components(nodes, [row["endpoints"] for row in all_rows])
    blocked = {groups[row["endpoints"][0]] for row in evaluation}
    # Group construction never inspects gold labels or score values.
    for row in all_rows:
        row["group"] = groups[row["endpoints"][0]]
    retained = [row for row in calibration if row["group"] not in blocked]
    return retained, {"calibration_original_rows": len(calibration), "calibration_retained_rows": len(retained),
                      "calibration_purged_rows": len(calibration) - len(retained),
                      "calibration_retained_components": len({r["group"] for r in retained}),
                      "evaluation_rows": len(evaluation), "evaluation_components": len(blocked),
                      "overlap_after_purge": len({r["group"] for r in retained} & blocked),
                      "retained_calibration_ids_sha256": digest(sorted(r["id"] for r in retained))}


def load(root: Path) -> tuple[RecordedJev, dict, dict]:
    backend = RecordedJev(root)
    data, audit = {}, {}
    for task in LABELS:
        data[task] = {}
        for arm in (BASELINES[task], FEW):
            splits = {}
            for split in ("calibration", "evaluation"):
                rows = []
                for r in read_scores(backend, task, arm, split):
                    call = backend.calls[r["decision"].call_id]
                    tokens = call["tokens_used"]["input"]
                    if type(tokens) is not int or tokens < 0:
                        raise ValueError("Missing or invalid recorded token count")
                    rows.append({"id": r["id"], "gold": r["gold"], "label": r["label"], "score": r["score"],
                                 "probabilities": dict(r["decision"].probabilities), "error": bool(r["decision"].error),
                                 "input_tokens": tokens, "endpoints": endpoints(task, r["row"]),
                                 "call_id": r["decision"].call_id})
                splits[split] = rows
            splits["calibration"], description = purge_groups(splits["calibration"], splits["evaluation"])
            data[task][arm] = splits
            if task in audit and audit[task] != description:
                raise ValueError("Primary arms do not have identical source grouping")
            audit[task] = description
    return backend, data, audit


def features(rows: list[dict]) -> list[dict]:
    """Positive candidate inference inputs, deliberately excluding gold."""
    keys = ("id", "label", "score", "probabilities", "error", "input_tokens", "endpoints", "group")
    return [{k: r[k] for k in keys} for r in rows]


def positive(row: dict) -> bool:
    return not row["error"] and row["label"] in {"same", "SUPPORTS", "REFUTES"}


def edge_metrics(rows: list[dict], accepted: set[str] | None = None) -> dict:
    accepted = {r["id"] for r in rows if positive(r)} if accepted is None else accepted
    if not accepted <= {r["id"] for r in rows if positive(r)}:
        raise ValueError("Only valid positive candidates can be emitted")
    picked = [r for r in rows if r["id"] in accepted]
    correct = sum(r["label"] == r["gold"] for r in picked)
    groups = {r["group"] for r in picked}
    bad_groups = {r["group"] for r in picked if r["label"] != r["gold"]}
    mass: dict[str, float] = defaultdict(float)
    for r in picked:
        mass[r["group"]] += 1 - r["score"]
    return {"accepted": len(picked), "correct": correct, "wrong": len(picked) - correct,
            "precision": correct / len(picked) if picked else None,
            "nonempty_components": len(groups), "any_error_components": len(bad_groups),
            "component_error_frequency": len(bad_groups) / len(groups) if groups else None,
            "maximum_claimed_risk_mass": max(mass.values(), default=0.0)}


def bootstrap(rows: list[dict], statistic, seed: int = SEED) -> list[float]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["group"]].append(row)
    groups = [grouped[k] for k in sorted(grouped)]
    rng = random.Random(seed)
    values = []
    for _ in range(BOOTSTRAPS):
        draw = [row for _ in groups for row in groups[rng.randrange(len(groups))]]
        value = statistic(draw)
        if value is not None:
            values.append(value)
    values.sort()
    return [values[int(.025 * (len(values) - 1))], values[int(.975 * (len(values) - 1))]] if values else []


def t01(task: str, arms: dict) -> dict:
    labels = LABELS[task]
    fit = conformal_fit(arms[FEW]["calibration"], labels, split="calibration")
    rows = arms[FEW]["evaluation"]
    accepted, covered, set_sizes = set(), [], defaultdict(int)
    for r in rows:
        choices = prediction_set(r["probabilities"], labels, fit, error=r["error"])
        set_sizes[str(len(choices))] += 1
        covered.append({"group": r["group"], "covered": r["gold"] in choices})
        if len(choices) == 1 and choices[0] == r["label"] and positive(r):
            accepted.add(r["id"])
    baseline, selected = edge_metrics(rows), edge_metrics(rows, accepted)
    groups = {r["group"] for r in covered}
    missed = {r["group"] for r in covered if not r["covered"]}
    retention = selected["correct"] / baseline["correct"] if baseline["correct"] else 0.0
    return {"fit": fit, "baseline": baseline, "contract": selected, "correct_edge_retention": retention,
            "set_size_counts": dict(set_sizes), "row_label_coverage": sum(r["covered"] for r in covered) / len(rows),
            "all_labels_covered_component_fraction": 1 - len(missed) / len(groups),
            "target_met": selected["wrong"] < baseline["wrong"] and retention >= .8,
            "interpretation": "Exploratory archived-label coverage, not independent conformal validation."}


def t02(task: str, arms: dict) -> dict:
    base, few = arms[BASELINES[task]]["evaluation"], arms[FEW]["evaluation"]
    rows = []
    for a, b in zip(base, few):
        if a["id"] != b["id"]:
            raise ValueError("Paired observation mismatch")
        rows.append({"group": a["group"], "a": a["label"] != a["gold"], "b": b["label"] != b["gold"],
                     "same_wrong": a["label"] == b["label"] != a["gold"]})
    n = len(rows)
    ea, eb = sum(r["a"] for r in rows), sum(r["b"] for r in rows)
    both = sum(r["a"] and r["b"] for r in rows)
    def excess(rs):
        return sum(r["a"] and r["b"] for r in rs) / len(rs) - sum(r["a"] for r in rs) * sum(r["b"] for r in rs) / len(rs)**2
    denominator = math.sqrt(ea * eb * (n - ea) * (n - eb))
    ci = bootstrap(rows, excess)
    return {"n": n, "baseline_errors": ea, "fewshot_errors": eb, "both_wrong": both,
            "same_wrong_label": sum(r["same_wrong"] for r in rows), "independent_expected_double_faults": ea * eb / n,
            "double_fault_excess": excess(rows), "descriptive_component_bootstrap_95": ci,
            "phi": (n * both - ea * eb) / denominator if denominator else None,
            "oracle_router_accuracy_upper_bound": 1 - both / n,
            "best_observed_accuracy": 1 - min(ea, eb) / n,
            "target_met": excess(rows) > 0, "interval_excludes_zero": bool(ci and ci[0] > 0)}


def t03(task: str, arms: dict) -> dict:
    label = "same" if task == "entity_resolution" else "SUPPORTS"
    output = {}
    for arm in (BASELINES[task], FEW):
        rows = arms[arm]["evaluation"]
        tp = sum(r["label"] == r["gold"] == label for r in rows)
        fp = sum(r["label"] == label and r["gold"] != label for r in rows)
        pos = sum(r["gold"] == label for r in rows)
        neg = len(rows) - pos
        tpr, fpr = tp / pos, fp / neg
        observed = tp / (tp + fp) if tp + fp else None
        grid = {str(p): projected_precision(tpr, fpr, p) for p in (.01, .05, .1, .5)}
        output[arm] = {"label": label, "tp": tp, "fp": fp, "gold_positive": pos, "gold_negative": neg,
                       "tpr": tpr, "fpr": fpr, "observed_prevalence": pos / len(rows), "observed_precision": observed,
                       "projected_precision": grid,
                       "target_met": observed is not None and grid["0.01"] is not None and observed - grid["0.01"] >= .1}
    return {"arms": output, "assumption": "Conditional rates and negative-class mixture remain fixed; not deployment observations."}


def t04(task: str, arms: dict) -> dict:
    rows = arms[FEW]["evaluation"]
    eligible = [r for r in rows if positive(r)]
    fixed = edge_metrics(rows, {r["id"] for r in eligible if r["score"] >= .95})
    bounded = edge_metrics(rows, admit_budget(features(eligible)))
    retention = bounded["correct"] / fixed["correct"] if fixed["correct"] else 0.0
    high_errors = sum(r["score"] == 1 and r["label"] != r["gold"] for r in eligible)
    return {"fixed_095_gate": fixed, "raw_score_component_budget": bounded,
            "correct_edge_retention": retention, "wrong_edges_at_probability_one": high_errors,
            "target_met": bounded["accepted"] > 0 and bounded["component_error_frequency"] <= .05 and retention >= .8,
            "interpretation": "A sum of unvalidated model error scores is not a valid probability bound."}


def t05(task: str, arms: dict) -> dict:
    rows = [r for r in arms[FEW]["evaluation"] if positive(r)]
    count = math.ceil(.1 * len(rows))
    def utility(reviewed):
        remaining_wrong = [r for r in rows if r["label"] != r["gold"] and r["id"] not in reviewed]
        tainted = {n for r in remaining_wrong for n in r["endpoints"]}
        clean = sum(r["label"] == r["gold"] and not (set(r["endpoints"]) & tainted) for r in rows)
        return {"clean_correct_edges": clean, "remaining_wrong": len(remaining_wrong), "tainted_nodes": len(tainted)}
    initial = utility(set())
    plain = utility(review_selection(features(rows), count, topology=False))
    topological = utility(review_selection(features(rows), count, topology=True))
    rng = random.Random(SEED)
    controls = [utility(set(rng.sample([r["id"] for r in rows], count))) for _ in range(128)]
    return {"candidate_edges": len(rows), "review_budget": count, "before": initial,
            "uncertainty_review": plain, "topological_review": topological,
            "random_mean_clean_correct_edges": sum(r["clean_correct_edges"] for r in controls) / len(controls),
            "target_met": topological["clean_correct_edges"] > plain["clean_correct_edges"],
            "interpretation": "Perfect, equal-cost reviewer counterfactual; no human or additional Jev review was executed."}


def t06(task: str, arms: dict) -> dict:
    base, few = arms[BASELINES[task]], arms[FEW]
    if not base["calibration"]:
        return {"status": "not_identifiable_no_purged_calibration", "target_met": False}
    fit = fit_cascade(features(base["calibration"]), features(few["calibration"]),
                      [r["gold"] for r in base["calibration"]], LABELS[task], split="calibration")
    predictions, tokens, escalated = cascade_predict(features(base["evaluation"]), features(few["evaluation"]), fit["threshold"])
    gold = [r["gold"] for r in base["evaluation"]]
    reference = macro_f1(gold, [r["label"] for r in few["evaluation"]], LABELS[task])
    actual = macro_f1(gold, predictions, LABELS[task])
    full_cost = sum(r["input_tokens"] for r in few["evaluation"])
    ratio = tokens / full_cost
    routed_rows = []
    for a, b in zip(base["evaluation"], few["evaluation"]):
        routed_rows.append(b if a["error"] or a["score"] < fit["threshold"] else a)
    return {"fit": fit, "evaluation_n": len(gold), "escalations": escalated,
            "cascade_macro_f1": actual, "fewshot_macro_f1": reference, "macro_f1_difference": actual - reference,
            "cascade_input_tokens": tokens, "all_fewshot_input_tokens": full_cost, "input_token_ratio": ratio,
            "cascade_edges": edge_metrics(routed_rows), "fewshot_edges": edge_metrics(few["evaluation"]),
            "target_met": ratio <= .8 and actual >= reference - .01 - 1e-12,
            "interpretation": "Retrospective counterfactual token accounting; no fresh inference, latency, or invoice measurement."}


def run_recorded(data: dict) -> dict:
    functions = (t01, t02, t03, t04, t05, t06)
    return {f"T{i:02d}": {task: fn(task, arms) for task, arms in data.items()} for i, fn in enumerate(functions, 1)}
