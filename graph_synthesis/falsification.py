"""Post-hoc falsification panels on authentic saved Jev decisions; no network."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import random
from typing import Any

from .core import components, digest
from .recorded import BASELINES, RecordedJev
from .study import read_scores

ACTIONS = {"relation_support": ("SUPPORTS", "REFUTES"), "entity_resolution": ("same",)}
LOSS_LEVELS = (0, .1, .25, .5, .75)
PREVALENCES = (.01, .05, .1, .25, .5, .75, .9)


def ratio(a: float, b: float) -> float | None:
    return a / b if b else None


def quantile(values: list[float], p: float) -> float | None:
    if not 0 <= p <= 1:
        raise ValueError("Quantile must be in [0,1]")
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * p
    low = math.floor(index)
    high = math.ceil(index)
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)


def validate_pair(left: list[dict], right: list[dict]) -> None:
    for rows in (left, right):
        if len({r["id"] for r in rows}) != len(rows):
            raise ValueError("Duplicate observation IDs")
    a, b = ({r["id"]: r for r in rows} for rows in (left, right))
    if a.keys() != b.keys():
        raise ValueError("Unpaired observation IDs")
    if any(a[k]["gold"] != b[k]["gold"] or a[k]["row"] != b[k]["row"] for k in a):
        raise ValueError("Paired arms must use identical candidates and labels")


def endpoint_pairs(rows: list[dict], task: str) -> list[tuple[str, str]]:
    if task not in ACTIONS:
        raise ValueError("Unknown task")
    if task == "relation_support":
        return [("document:" + r["row"]["document_id"], "claim:" + r["row"]["claim_id"]) for r in rows]
    return [("record:" + r["row"]["entity_1"], "record:" + r["row"]["entity_2"]) for r in rows]


def component_groups(rows: list[dict], task: str) -> dict[str, str]:
    """Candidate graph components, independent of labels, scores and acceptance."""
    pairs = endpoint_pairs(rows, task)
    roots = components({x for pair in pairs for x in pair}, pairs)
    return {r["id"]: roots[pair[0]] for r, pair in zip(rows, pairs)}


def quality(rows: list[dict], actions: tuple[str, ...]) -> dict[str, Any]:
    accepted = [r for r in rows if r["label"] in actions]
    correct = sum(r["label"] == r["gold"] for r in accepted)
    gold = sum(r["gold"] in actions for r in rows)
    return {"candidates": len(rows), "accepted": len(accepted), "correct": correct,
            "wrong": len(accepted) - correct, "gold_positive": gold,
            "precision": ratio(correct, len(accepted)), "recall": ratio(correct, gold),
            "operational_errors": sum(r["label"] == "ERROR" for r in rows)}


def component_quality(rows: list[dict], actions: tuple[str, ...], groups: dict[str, str]) -> dict:
    buckets = defaultdict(list)
    for r in rows:
        buckets[groups[r["id"]]].append(r)
    records = []
    for group, items in sorted(buckets.items()):
        q = quality(items, actions)
        records.append({"component": group, **q,
                        "contaminated": q["wrong"] > 0,
                        "complete_and_clean": q["gold_positive"] > 0 and q["wrong"] == 0
                        and q["correct"] == q["gold_positive"]})
    active = sum(r["accepted"] > 0 for r in records)
    contaminated = sum(r["contaminated"] for r in records)
    eligible = sum(r["gold_positive"] > 0 for r in records)
    complete = sum(r["complete_and_clean"] for r in records)
    return {"components": len(records), "active_components": active,
            "empty_components": len(records) - active, "contaminated_components": contaminated,
            "contamination_among_active": ratio(contaminated, active),
            "gold_positive_components": eligible, "complete_and_clean_components": complete,
            "complete_and_clean_fraction": ratio(complete, eligible), "by_component": records}


def paired_component_bootstrap(left: list[dict], right: list[dict], task: str,
                               draws: int = 2000) -> dict:
    validate_pair(left, right)
    if type(draws) is not int or draws < 1:
        raise ValueError("Positive bootstrap draw count required")
    groups = component_groups(left, task)
    a = component_quality(left, ACTIONS[task], groups)["by_component"]
    b = component_quality(right, ACTIONS[task], groups)["by_component"]
    differences = {"precision": [], "complete_and_clean_fraction": []}
    rng = random.Random(2026091808)
    for _ in range(draws if a else 0):
        selected = [rng.randrange(len(a)) for _ in a]
        for metric, numerator, denominator in (
                ("precision", "correct", "accepted"),
                ("complete_and_clean_fraction", "complete_and_clean", "eligible")):
            values = []
            for records in (a, b):
                num = sum(records[i][numerator] for i in selected)
                den = sum((records[i]["gold_positive"] > 0) if denominator == "eligible"
                          else records[i][denominator] for i in selected)
                values.append(ratio(num, den))
            if all(v is not None for v in values):
                differences[metric].append(values[1] - values[0])
    return {"kind": "exploratory_pointwise_paired_component_bootstrap",
            "direction": "fewshot_minus_generic", "draws": draws, "components": len(a),
            "assumption": "Observed endpoint components are independent sampling units; hidden dependence is unmeasured.",
            "metrics": {k: {"valid_draws": len(v), "lower": quantile(v, .025),
                             "upper": quantile(v, .975)} for k, v in differences.items()}}


def joint_errors(left: list[dict], right: list[dict]) -> dict:
    validate_pair(left, right)
    other = {r["id"]: r for r in right}
    pairs = [(r, other[r["id"]]) for r in left
             if r["label"] != "ERROR" and other[r["id"]]["label"] != "ERROR"]
    n = len(pairs)
    first = sum(a["label"] != a["gold"] for a, _ in pairs)
    second = sum(b["label"] != b["gold"] for _, b in pairs)
    joint = sum(a["label"] != a["gold"] and b["label"] != b["gold"] for a, b in pairs)
    agreement = sum(a["label"] == b["label"] for a, b in pairs)
    wrong_agreement = sum(a["label"] == b["label"] and a["label"] != a["gold"] for a, b in pairs)
    expected = ratio(first * second, n)
    return {"common_success": n, "excluded_operational_rows": len(left) - n,
            "generic_errors": first, "fewshot_errors": second, "both_wrong": joint,
            "agree": agreement, "agree_wrong": wrong_agreement,
            "agreement_error_fraction": ratio(wrong_agreement, agreement),
            "expected_joint_errors_under_independence": expected,
            "observed_to_independent_joint_ratio": ratio(joint, expected) if expected is not None else None,
            "interpretation": "Descriptive dependence diagnostic, not a hypothesis test or independent corroboration."}


def source_key(r: dict, task: str) -> str:
    return r["row"]["document_id"] if task == "relation_support" else r["row"]["entity_1"]


def surviving_ids(rows: list[dict], task: str, loss: float, seed: int) -> set[str]:
    if task not in ACTIONS or not 0 <= loss <= 1:
        raise ValueError("Invalid task or loss fraction")
    sources = {source_key(r, task) for r in rows}
    ordered = sorted(sources, key=lambda key: (digest([seed, key]), key))
    removed = set(ordered[:math.floor(len(ordered) * loss)])
    return {r["id"] for r in rows if source_key(r, task) not in removed}


def candidate_loss(arms: dict[str, list[dict]], task: str, seeds: int = 100) -> list[dict]:
    if type(seeds) is not int or seeds < 1:
        raise ValueError("Positive seed count required")
    reference = next(iter(arms.values()))
    for rows in arms.values():
        validate_pair(reference, rows)
    gold = sum(r["gold"] in ACTIONS[task] for r in reference)
    result = []
    for loss in LOSS_LEVELS:
        totals = {arm: [] for arm in arms}
        ceilings, retained, masks = [], [], []
        for seed in range(seeds):
            keep = surviving_ids(reference, task, loss, seed)
            masks.append(digest(sorted(keep)))
            retained.append(len(keep))
            ceilings.append(ratio(sum(r["id"] in keep and r["gold"] in ACTIONS[task]
                                      for r in reference), gold))
            for arm, rows in arms.items():
                totals[arm].append(ratio(sum(r["id"] in keep and r["label"] in ACTIONS[task]
                                            and r["label"] == r["gold"] for r in rows), gold))
        def summary(values):
            valid = [v for v in values if v is not None]
            return {"mean": ratio(sum(valid), len(valid)), "p05": quantile(valid, .05),
                    "p95": quantile(valid, .95)}
        result.append({"loss_fraction": loss, "seeds": seeds, "original_gold_positive": gold,
                       "mask_digest": digest(masks), "retained_candidates": summary(retained),
                       "surviving_gold_oracle_recall": summary(ceilings),
                       "arm_recall": {arm: summary(values) for arm, values in totals.items()}})
    return result


def prevalence_projection(rows: list[dict], action: str) -> dict:
    positive = sum(r["gold"] == action for r in rows)
    tp = sum(r["gold"] == action and r["label"] == action for r in rows)
    fp = sum(r["gold"] != action and r["label"] == action for r in rows)
    tpr, fpr = ratio(tp, positive), ratio(fp, len(rows) - positive)
    projections = []
    for p in PREVALENCES:
        ppv = None if tpr is None or fpr is None else ratio(tpr * p, tpr * p + fpr * (1 - p))
        projections.append({"prevalence": p, "projected_precision": ppv})
    return {"action": action, "positive_n": positive, "negative_n": len(rows) - positive,
            "true_positive": tp, "false_positive": fp, "sensitivity": tpr, "false_positive_rate": fpr,
            "kind": "analytical_label_shift_projection_with_fixed_empirical_rates",
            "uncertainty": "No interval or extrapolation guarantee; zero observed FPs is not zero true risk.",
            "projections": projections}


def zero_error_sample_size(risk: float, alpha: float = .05) -> int:
    if not 0 < risk < 1 or not 0 < alpha < 1:
        raise ValueError("Risk and alpha must be strictly between zero and one")
    return math.ceil(math.log(alpha) / math.log1p(-risk))


def run(repository: Path, *, draws: int = 2000, seeds: int = 100) -> dict:
    backend = RecordedJev(repository)
    result = {"schema_version": 1, "base_commit": "e11ca93be83e4f9c73401bcecd3275e18da21901",
              "classification": "post_hoc_frozen_inference_diagnostics", "fresh_model_calls": 0,
              "source_hashes": backend.hashes, "tasks": {},
              "planning": {str(r): zero_error_sample_size(r) for r in (.01, .001)},
              "planning_assumptions": "One preselected policy, independent representative accepted actions, zero errors, one-sided alpha=.05; not a deployment qualification."}
    for task, baseline in BASELINES.items():
        arms = {name: read_scores(backend, task, arm, "evaluation")
                for name, arm in (("generic", baseline), ("fewshot", "fewshot_contract"))}
        groups = component_groups(arms["generic"], task)
        panels = {}
        for name, rows in arms.items():
            c = component_quality(rows, ACTIONS[task], groups)
            c["component_accounting_hash"] = digest(c.pop("by_component"))
            certain = [r for r in rows if r["score"] == 1 and r["label"] in ACTIONS[task]]
            panels[name] = {"positive_actions": list(ACTIONS[task]), "quality": quality(rows, ACTIONS[task]),
                            "components": c,
                            "score_one_actions": {k: v for k, v in quality(certain, ACTIONS[task]).items()
                                                  if k in {"accepted", "correct", "wrong", "precision"}},
                            "score_one_wrong_ids": sorted(r["id"] for r in certain if r["label"] != r["gold"]),
                            "prevalence": [prevalence_projection(rows, a) for a in ACTIONS[task]]}
        result["tasks"][task] = {"recorded": panels, "joint_errors": joint_errors(*arms.values()),
            "paired_components": paired_component_bootstrap(*arms.values(), task, draws),
            "candidate_loss_kind": "synthetic_candidate_availability_intervention_no_rescoring",
            "loss_unit": "document_id" if task == "relation_support" else "left_record_id",
            "candidate_loss": candidate_loss(arms, task, seeds),
            "accept_none_control": {"accepted": 0, "wrong": 0, "precision": None, "recall": 0.0,
                                    "interpretation": "Safety without useful construction; not a model baseline."}}
    from .stress_mechanisms import run_mechanisms
    result["mechanisms"] = run_mechanisms()
    return result


def render_report(result: dict) -> str:
    lines = ["# Additional graph-synthesis falsification results", "",
             "Generated from exact archived Jev responses plus explicitly synthetic interventions.",
             "No fresh Jev, LLM, KARMA, or independent-corpus run is represented here.", "",
             "## Recorded positive-action and component quality", "",
             "Identity counts only `same`; relationship counts `SUPPORTS` and `REFUTES`.",
             "Components use all candidate endpoints, including unaccepted pairs.", "",
             "| Task | Arm | Correct / accepted | Wrong | Complete clean / gold-positive components | Contaminated / active components |",
             "|---|---|---:|---:|---:|---:|"]
    for task, panels in result["tasks"].items():
        for arm, data in panels["recorded"].items():
            q, c = data["quality"], data["components"]
            lines.append(f"| {task} | {arm} | {q['correct']} / {q['accepted']} | {q['wrong']} | {c['complete_and_clean_components']} / {c['gold_positive_components']} | {c['contaminated_components']} / {c['active_components']} |")
    lines += ["", "## Shared errors and certainty", ""]
    for task, panels in result["tasks"].items():
        j = panels["joint_errors"]
        lines.append(f"- {task}: {j['both_wrong']} shared errors among {j['common_success']} common-success rows; {j['agree_wrong']} wrong-label agreements. Independence would predict {j['expected_joint_errors_under_independence']:.3f} shared errors from the marginal rates. This is descriptive, not a significance test.")
        for arm, data in panels["recorded"].items():
            q = data["score_one_actions"]
            lines.append(f"  - {arm}: score exactly 1.0 yields {q['wrong']} wrong positive actions out of {q['accepted']} accepted. Identifiers are in results.json.")
        lines.append(f"  - Paired component-bootstrap intervals (few-shot minus generic): `{json.dumps(panels['paired_components']['metrics'], sort_keys=True)}`.")
    lines += ["", "## Candidate loss (original gold denominator)", "",
              "Seeded, nested source-removal masks are shared across arms. Ranges in JSON are intervention percentiles, not confidence intervals.", "",
              "| Task | Source loss | Generic mean recall | Few-shot mean recall | Surviving-gold oracle ceiling |",
              "|---|---:|---:|---:|---:|"]
    for task, panels in result["tasks"].items():
        for row in panels["candidate_loss"]:
            def percent(x):
                return "undefined" if x is None else f"{100*x:.2f}%"
            lines.append(f"| {task} | {row['loss_fraction']:.0%} | {percent(row['arm_recall']['generic']['mean'])} | {percent(row['arm_recall']['fewshot']['mean'])} | {percent(row['surviving_gold_oracle_recall']['mean'])} |")
    lines += ["", "## Mechanism witnesses (NOT Jev measurements)", "",
              "```json", json.dumps(result["mechanisms"], indent=2, sort_keys=True), "```", "",
              "## Interpretation", "",
              "Passing regression tests means these measurements and counterexamples reproduce; it does not mean every stress scenario is safe. Schema validation cannot establish truth. The current runtime compares qualifier dictionaries exactly, not temporal interval overlap. Repair requires explicit dependencies and source-withdrawal policy.", "",
              f"Zero errors require at least {result['planning']['0.01']} independent accepted actions for a 1% error bound or {result['planning']['0.001']} for 0.1%, at one-sided 95% confidence for one preselected policy. The current results do not qualify a policy.", "",
              "Prevalence projections in results.json assume unchanged empirical TPR/FPR and are not new domain-shift observations. All bootstrap intervals are exploratory, pointwise, and conditional on observed component independence.", "",
              "Fresh semantic challenges, full-document extraction, independently adjudicated data, matched-cost structured LLM/NLI/graph-ML baselines and a fidelity-audited KARMA comparison remain necessary. No superiority or autonomous deployment claim follows.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("experiments/falsification/results.json"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = run(root)
    text = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    report = render_report(result)
    report_path = args.output.with_name("RESULTS.md")
    if args.check:
        from .verify import compare_json
        changes = compare_json(json.loads(args.output.read_text(encoding="utf-8")), result)
        if report_path.read_text(encoding="utf-8") != report:
            raise ValueError("Generated report differs from committed reference")
        print(json.dumps({"roundoff_differences": len(changes), "reproduced": True}))
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        report_path.write_text(report, encoding="utf-8")
        print(f"Wrote {args.output} and {report_path}; fresh_model_calls=0")


if __name__ == "__main__":
    main()
