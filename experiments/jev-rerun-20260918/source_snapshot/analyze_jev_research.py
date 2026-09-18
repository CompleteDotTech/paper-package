"""Offline, denominator-explicit analysis of a frozen same-model Jev run.

This module never reads credentials, calls a service, or trains a model. The only
fitted quantity is a scalar temperature using the separate calibration split.
"""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path

from pgc.evaluation import (
    ER_LABELS, RELATION_LABELS, EvaluationResult, LOG_LOSS_EPSILON,
    json_safe, summarize_results, validate_distribution,
)


LABELS = {"relation_support": RELATION_LABELS, "entity_resolution": ER_LABELS}
BASELINES = {"relation_support": "baseline_choice", "entity_resolution": "baseline_noul"}
SEED = 20260917


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


def _evaluated(row):
    labels = LABELS[row["task"]]
    eligible = row["gold_label"] in labels
    if not eligible and not (row["task"] == "entity_resolution" and row["gold_label"] == "uncertain"):
        raise ValueError(f"Unknown gold label: {row['gold_label']!r}")
    error, validation_error, distribution = row.get("error"), None, {}
    if row.get("execution_mode") != "real":
        error = error or "Prediction is not marked as real execution"
    if not error:
        try:
            distribution = validate_distribution(row.get("distribution"), labels)
        except (ValueError, TypeError) as exc:
            validation_error = str(exc)
            error = validation_error
    predicted = max(distribution, key=distribution.get) if not error else "ERROR"
    confidence = distribution[predicted] if not error else None
    return EvaluationResult(
        example_id=row["id"], backend_name=row["arm"], backend_version="jev-recorded",
        decision_primitive=row["arm"], distribution=distribution, confidence=confidence,
        gold_label=row["gold_label"], predicted_label=predicted,
        correct=bool(eligible and not error and predicted == row["gold_label"]),
        predicted_confidence=confidence or 0.0, latency_ms=None, tokens_used=None,
        labels=list(labels), semantic_eligible=eligible, service_success=not bool(error),
        error=str(error) if error else None, raw_error=row.get("error"),
        validation_error=validation_error, execution_mode=row.get("execution_mode", "unknown"),
        raw_distribution=row.get("distribution"),
    )


def summarize_records(rows):
    """Score one task; failures remain in accuracy, recall and F1 denominators."""
    rows = list(rows)
    if not rows:
        return {"n_examples": 0, "n_semantic_examples": 0, "n_errors": 0,
                "n_semantic_service_success": 0, "accuracy": None,
                "operational_accuracy": None, "conditional_accuracy": None,
                "macro_f1": None, "brier_score": None, "log_loss": None,
                "false_merge_rate": None, "probability_score_denominator": 0,
                "confusion": {}, "semantic_coverage": None}
    if len({r["task"] for r in rows}) != 1:
        raise ValueError("A summary cannot mix task label contracts")
    results = [_evaluated(row) for row in rows]
    summary = summarize_results(results, LABELS[rows[0]["task"]])
    # A shared API batch must never be billed once per prediction.
    for key in ("total_input_tokens", "total_output_tokens", "total_tokens", "tokens_per_example"):
        summary.pop(key, None)
    summary.pop("token_usage_denominator", None)
    summary["usage_source"] = "calls.jsonl only; no prediction-level token accounting"
    summary["errors"] = dict(Counter(r.error for r in results if r.error))
    if rows[0]["task"] == "entity_resolution":
        negative = [r for r in results if r.gold_label == "different"]
        summary["false_merge_count"] = sum(r.predicted_label == "same" for r in negative)
        summary["false_merge_denominator"] = len(negative)
        summary["false_merge_rate"] = summary["false_merge_count"] / len(negative) if negative else None
        summary["negative_service_errors"] = sum(not r.service_success for r in negative)
    return summary


def select_arms(rows):
    """Select the best nonbaseline on development only, even if baseline wins."""
    grouped = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if row["split"] == "development" and row.get("repeat", 0) == 0:
            grouped[row["task"]][row["arm"]].append(row)
    selections = {}
    for task, arms in grouped.items():
        baseline = BASELINES[task]
        if baseline not in arms:
            raise ValueError(f"Development baseline is missing for {task}")
        expected_ids = {r["id"] for r in arms[baseline]}
        ranking = []
        for arm, records in arms.items():
            if len(records) != len(expected_ids) or {r["id"] for r in records} != expected_ids:
                raise ValueError("Development arms must have identical, unique example IDs")
            score = summarize_records(records)
            ranking.append({"arm": arm, **{k: score[k] for k in
                            ("macro_f1", "brier_score", "accuracy", "n_errors", "n_examples", "probability_score_denominator")}})
        ranking.sort(key=lambda r: (-(r["macro_f1"] if r["macro_f1"] is not None else -1),
                                    r["brier_score"] if r["brier_score"] is not None else math.inf, r["arm"]))
        alternatives = [r for r in ranking if r["arm"] != baseline]
        if not alternatives:
            raise ValueError(f"No development alternatives for {task}")
        baseline_score = next(r for r in ranking if r["arm"] == baseline)
        selections[task] = {"baseline": baseline, "selected": alternatives[0]["arm"],
                            "selection_split": "development", "ranking": ranking,
                            "selected_beats_baseline_development_macro_f1": alternatives[0]["macro_f1"] > baseline_score["macro_f1"],
                            "rule": "highest operational macro F1, then lowest full-sum Brier, then stable arm name; best alternative even if below baseline"}
    return selections


def temperature_scale(distribution, temperature):
    """Softmax(log(clipped probability)/T); this is not access to model logits."""
    if not math.isfinite(temperature) or not .05 <= temperature <= 20:
        raise ValueError("Temperature must be in [0.05, 20]")
    probabilities = validate_distribution(distribution, tuple(distribution))
    logits = {k: math.log(max(v, LOG_LOSS_EPSILON)) / temperature for k, v in probabilities.items()}
    largest = max(logits.values())
    weights = {k: math.exp(v - largest) for k, v in logits.items()}
    return {k: v / sum(weights.values()) for k, v in weights.items()}


def fit_temperature(rows):
    """Fit only valid calibration outputs, reporting every excluded error."""
    rows = list(rows)
    if any(r["split"] != "calibration" for r in rows):
        raise ValueError("Temperature fitting accepts calibration rows only")
    if len({(r["task"], r["arm"]) for r in rows}) > 1:
        raise ValueError("Fit each task and arm independently")
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Calibration IDs must be unique")
    valid = [r for r in rows if (lambda p: p.service_success and p.semantic_eligible)(_evaluated(r))]
    labels = LABELS[rows[0]["task"]] if rows else ()
    fit_counts = Counter(r["gold_label"] for r in valid)
    info = {"n_calibration_rows": len(rows), "n_fit_rows": len(valid),
            "n_excluded_rows": len(rows) - len(valid), "fit_ids_sha256": _digest(sorted(r["id"] for r in valid)),
            "fit_ids": sorted(r["id"] for r in valid), "fit_class_counts": dict(fit_counts),
            "missing_fit_classes": [label for label in labels if not fit_counts[label]],
            "n_clipped_probability_coordinates": sum(p < LOG_LOSS_EPSILON for r in valid for p in r["distribution"].values()),
            "bounds": [.05, 20], "probability_clip": LOG_LOSS_EPSILON,
            "objective": "calibration-only log loss on log clipped probabilities; no underlying model training"}
    if not valid:
        return {**info, "temperature": None, "calibration_log_loss_before": None,
                "calibration_log_loss_after": None, "boundary_fit": None, "status": "unavailable_no_valid_calibration"}
    def objective(log_t):
        return sum(-math.log(max(temperature_scale(r["distribution"], math.exp(log_t))[r["gold_label"]],
                                LOG_LOSS_EPSILON)) for r in valid) / len(valid)
    # The scalar inverse-temperature objective is convex. Golden-section search
    # in log temperature is unimodal and keeps this utility dependency-light.
    lo, hi = math.log(.05), math.log(20)
    ratio = (math.sqrt(5) - 1) / 2
    left, right = hi - ratio * (hi - lo), lo + ratio * (hi - lo)
    fl, fr = objective(left), objective(right)
    for _ in range(80):
        if fl < fr:
            hi, right, fr = right, left, fl
            left = hi - ratio * (hi - lo)
            fl = objective(left)
        else:
            lo, left, fl = left, right, fr
            right = lo + ratio * (hi - lo)
            fr = objective(right)
    candidates = (0.0, math.log(.05), math.log(20), (lo + hi) / 2)
    chosen = min(candidates, key=objective)
    temperature = min(20.0, max(.05, math.exp(chosen)))
    return {**info, "temperature": temperature, "calibration_log_loss_before": objective(0),
            "calibration_log_loss_after": objective(math.log(temperature)),
            "boundary_fit": "lower" if math.isclose(temperature, .05, abs_tol=1e-7) else "upper" if math.isclose(temperature, 20, abs_tol=1e-7) else None,
            "status": "fitted"}


def _calibrated(rows, temperature):
    if temperature is None:
        return None
    return [{**r, "distribution": temperature_scale(r["distribution"], temperature)}
            if _evaluated(r).service_success else dict(r) for r in rows]


def paired_bootstrap(baseline_rows, selected_rows, task, resamples=2000, seed=SEED):
    """Paired group bootstrap with operational errors and common-valid Brier."""
    import numpy as np

    if resamples < 1:
        raise ValueError("resamples must be positive")
    maps = [{r["id"]: r for r in rows} for rows in (baseline_rows, selected_rows)]
    if any(len(mapping) != len(rows) for mapping, rows in zip(maps, (baseline_rows, selected_rows))):
        raise ValueError("Paired comparison requires unique IDs")
    if set(maps[0]) != set(maps[1]):
        raise ValueError("Paired comparison requires identical IDs; missing predictions cannot be dropped")
    pairs = [(maps[0][key], maps[1][key]) for key in sorted(maps[0])]
    for a, b in pairs:
        if a["task"] != task or b["task"] != task or a["gold_label"] != b["gold_label"] or a["group"] != b["group"]:
            raise ValueError("Paired task, gold and group annotations must agree")
    pairs = [(a, b) for a, b in pairs if a["gold_label"] in LABELS[task]]
    info = {"difference": "selected minus baseline", "resamples": resamples, "seed": seed,
            "n_pairs": len(pairs), "unit": "claim/document connected component" if task == "relation_support" else "entity-disjoint row",
            "interval": "paired percentile 95%; conditional on fixed selection and fitted temperatures; no multiplicity correction",
            "brier_population": "common valid paired responses; operational metrics retain errors"}
    if not pairs:
        return {**info, "n_groups": 0, "n_brier_pairs": 0, "metrics": {}}
    group_keys = [a["group"] if task == "relation_support" else a["id"] for a, _ in pairs]
    groups = sorted(set(group_keys))
    indexes = {g: i for i, g in enumerate(groups)}
    labels = LABELS[task]
    width = len(labels)
    # n, correct, common-valid Brier sum/count, then K x (K+1) confusion.
    statistics = np.zeros((2, len(groups), 4 + width * (width + 1)))
    for (a, b), group in zip(pairs, group_keys):
        evaluated = [_evaluated(a), _evaluated(b)]
        common_valid = all(r.service_success for r in evaluated)
        for arm, record in enumerate(evaluated):
            slot = statistics[arm, indexes[group]]
            slot[:4] += [1, record.correct, record.brier_score() if common_valid else 0, int(common_valid)]
            predicted = labels.index(record.predicted_label) if record.service_success else width
            slot[4 + labels.index(record.gold_label) * (width + 1) + predicted] += 1
    def ratio(numerator, denominator):
        return np.divide(numerator, denominator, out=np.full_like(numerator, np.nan, dtype=float), where=denominator != 0)
    def metrics(total):
        confusion = total[..., 4:].reshape((*total.shape[:-1], width, width + 1))
        true_positive = np.diagonal(confusion[..., :width], axis1=-2, axis2=-1)
        denominator = confusion.sum(axis=-1) + confusion[..., :width].sum(axis=-2)
        f1 = np.divide(2 * true_positive, denominator, out=np.zeros_like(true_positive), where=denominator != 0).mean(axis=-1)
        output = {"accuracy": ratio(total[..., 1], total[..., 0]), "macro_f1": f1,
                  "brier_score": ratio(total[..., 2], total[..., 3])}
        if task == "entity_resolution":
            output["false_merge_rate"] = ratio(confusion[..., labels.index("different"), labels.index("same")],
                                               confusion[..., labels.index("different"), :].sum(axis=-1))
        return output
    draws = np.random.default_rng(seed).integers(0, len(groups), size=(resamples, len(groups)))
    sampled = [metrics(statistics[arm, draws].sum(axis=1)) for arm in (0, 1)]
    points = [metrics(statistics[arm].sum(axis=0)) for arm in (0, 1)]
    comparisons = {}
    for metric in points[0]:
        difference = float(points[1][metric] - points[0][metric])
        values = sampled[1][metric] - sampled[0][metric]
        finite = values[np.isfinite(values)]
        comparisons[metric] = {"difference": difference if math.isfinite(difference) else None,
                               "ci95": np.quantile(finite, [.025, .975]).tolist() if len(finite) else None,
                               "valid_resamples": len(finite),
                               "direction": "higher is better" if metric in {"accuracy", "macro_f1"} else "lower is better"}
    return {**info, "n_groups": len(groups), "n_brier_pairs": int(statistics[0, :, 3].sum()), "metrics": comparisons}


def summarize_usage(calls, manifest):
    """Count each recorded invocation once, including failed attempts and retries."""
    ids = [r["call_id"] for r in calls]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate call IDs would make billing ambiguous")
    valid, latency = [], []
    for call in calls:
        usage = call.get("tokens_used")
        if isinstance(usage, dict) and all(type(usage.get(k)) is int and usage[k] >= 0 for k in ("input", "output")):
            valid.append(usage)
        value = call.get("latency_ms")
        if isinstance(value, (int, float)) and math.isfinite(value) and value >= 0:
            latency.append(value)
    totals = {k: sum(r[k] for r in valid) for k in ("input", "output")}
    attempts = [r.get("metadata", {}).get("attempts", 1) for r in calls]
    extra_attempts = sum(max(0, n - 1) for n in attempts)
    ordered_latency = sorted(latency)
    def quantile(fraction):
        if not ordered_latency:
            return None
        index = (len(ordered_latency) - 1) * fraction
        low, high = math.floor(index), math.ceil(index)
        return ordered_latency[low] + (ordered_latency[high] - ordered_latency[low]) * (index - low)
    prices = manifest.get("unit_prices_usd_per_million_tokens", {})
    prices_valid = all(type(prices.get(k)) in (int, float) and math.isfinite(prices[k]) and prices[k] >= 0 for k in ("input", "output"))
    estimate = sum(totals[k] * prices[k] / 1_000_000 for k in totals) if prices_valid and valid else None
    return {"n_calls": len(calls), "n_http_attempts": sum(attempts), "n_retries": extra_attempts,
            "unknown_usage_attempts": sum(r.get("unknown_usage_attempts", max(0, n - int(isinstance(r.get("tokens_used"), dict)))) for r, n in zip(calls, attempts)),
            "budget_input_token_charge": sum(r.get("budget_input_token_charge", (r.get("tokens_used") or {}).get("input", 0)) for r in calls),
            "n_questions_in_recorded_payloads": sum(len(r.get("payload", {}).get("questions", {})) for r in calls),
            "n_calls_with_usage": len(valid), "n_calls_missing_usage": len(calls) - len(valid),
            "reported_input_tokens": totals["input"] if valid else None,
            "reported_output_tokens": totals["output"] if valid else None,
            "reported_total_tokens": sum(totals.values()) if valid else None,
            "n_failed_calls": sum(bool(r.get("error")) for r in calls),
            "execution_modes": dict(Counter(r.get("execution_mode", "unknown") for r in calls)),
            "sum_call_latency_ms": sum(latency) if latency else None,
            "mean_call_latency_ms": sum(latency) / len(latency) if latency else None,
            "latency_denominator": len(latency), "call_latency_percentiles_ms": {"p50": quantile(.5), "p90": quantile(.9), "p95": quantile(.95), "p99": quantile(.99)},
            "recorded_stage_wall_seconds": sum(s.get("driver_wall_seconds", 0) for s in manifest.get("stages", [])),
            "unit_prices_usd_per_million_tokens": prices or None,
            "estimated_usd_for_reported_usage": estimate,
            "estimate_complete": bool(calls) and len(valid) == len(calls) and prices_valid and extra_attempts == 0,
            "invoice_verified": False,
            "note": "Reported usage summed once per logical calls.jsonl entry; shared batches are never multiplied by prediction count. HTTP attempts/retries are counted separately; usage absent from retry responses is unknown. USD is a unit-price estimate, not a verified invoice. Missing usage is unknown; summed call latency is not parallel wall time."}


def repeatability_report(rows, calls):
    call_map = {r["call_id"]: r for r in calls}
    grouped = defaultdict(dict)
    for row in rows:
        if row["split"] in {"evaluation", "repeatability"}:
            key, repeat = (row["task"], row["arm"], row["id"]), row.get("repeat", 0)
            if repeat in grouped[key]:
                raise ValueError("Duplicate repeatability example/repeat")
            grouped[key][repeat] = row
    output = defaultdict(list)
    for (task, arm, identity), repeats in grouped.items():
        if len(repeats) < 2:
            continue
        comparisons = []
        numbers = sorted(repeats)
        for i, first in enumerate(numbers):
            for second in numbers[i + 1:]:
                a, b = repeats[first], repeats[second]
                first_ids, second_ids = set(a.get("call_ids", [])), set(b.get("call_ids", []))
                all_ids = first_ids | second_ids
                known = bool(first_ids and second_ids) and all(k in call_map for k in all_ids)
                explicitly_cached = any(call_map[k].get("metadata", {}).get("cache_hit") or
                                        call_map[k].get("metadata", {}).get("cached") for k in all_ids if k in call_map)
                fresh = known and not first_ids.intersection(second_ids) and not explicitly_cached and all(
                    call_map[k].get("execution_mode") == "real" for k in all_ids)
                first_hashes = sorted(call_map[k].get("request_sha256") or "" for k in first_ids if k in call_map)
                second_hashes = sorted(call_map[k].get("request_sha256") or "" for k in second_ids if k in call_map)
                same_payload = known and bool(first_hashes) and all(first_hashes) and first_hashes == second_hashes
                provenance = "fresh_recorded_calls" if fresh else (
                    "cached_or_reused_calls" if first_ids.intersection(second_ids) or explicitly_cached else "unverified_call_provenance")
                if fresh and not same_payload:
                    provenance = "fresh_calls_payload_different_or_unverified"
                ea, eb = _evaluated(a), _evaluated(b)
                valid = ea.service_success and eb.service_success
                comparisons.append({"first_repeat": first, "second_repeat": second,
                                    "provenance": provenance, "both_valid": valid,
                                    "same_complete_payload": same_payload,
                                    "exact_distribution_match": ea.distribution == eb.distribution if valid else None,
                                    "argmax_agreement": ea.predicted_label == eb.predicted_label if valid else None,
                                    "total_variation": sum(abs(ea.distribution[k] - eb.distribution[k]) for k in LABELS[task]) / 2 if valid else None,
                                    "max_coordinate_change": max(abs(ea.distribution[k] - eb.distribution[k]) for k in LABELS[task]) if valid else None,
                                    "first_error": ea.error, "second_error": eb.error})
        output[(task, arm)].append({"id": identity, "repeats": numbers, "comparisons": comparisons,
                                   "round_call_ids": {str(n): repeats[n].get("call_ids", []) for n in numbers},
                                   "round_metrics": {str(n): summarize_records([repeats[n]]) for n in numbers},
                                   "all_three_fresh_labels_identical": {0, 1, 2}.issubset(numbers) and
                                   all(c["provenance"] == "fresh_recorded_calls" and c["both_valid"] and c["argmax_agreement"] for c in comparisons)})
    reports = []
    for (task, arm), examples in sorted(output.items()):
        comparisons = [c for e in examples for c in e["comparisons"]]
        fresh = [c for c in comparisons if c["provenance"] == "fresh_recorded_calls"]
        valid = [c for c in fresh if c["both_valid"]]
        referenced = {identity for example in examples for identities in example["round_call_ids"].values() for identity in identities}
        timestamps = sorted(call_map[identity]["created_at"] for identity in referenced if identity in call_map and call_map[identity].get("created_at"))
        reports.append({"task": task, "arm": arm, "n_examples": len(examples),
                        "n_examples_with_initial_plus_two_repeats": sum({0, 1, 2}.issubset(e["repeats"]) for e in examples),
                        "n_pairwise_comparisons": len(comparisons), "n_fresh_comparisons": len(fresh),
                        "n_valid_fresh_comparisons": len(valid), "n_fresh_comparisons_with_error": len(fresh) - len(valid),
                        "provenance_counts": dict(Counter(c["provenance"] for c in comparisons)),
                        "exact_distribution_matches": sum(c["exact_distribution_match"] for c in valid),
                        "argmax_flips": sum(not c["argmax_agreement"] for c in valid),
                        "n_examples_with_all_three_fresh_labels_identical": sum(e["all_three_fresh_labels_identical"] for e in examples),
                        "classification_agreement": sum(c["argmax_agreement"] for c in valid) / len(valid) if valid else None,
                        "max_total_variation": max((c["total_variation"] for c in valid), default=None),
                        "mean_total_variation": sum(c["total_variation"] for c in valid) / len(valid) if valid else None,
                        "max_coordinate_change": max((c["max_coordinate_change"] for c in valid), default=None),
                        "recorded_utc_window": [timestamps[0], timestamps[-1]] if timestamps else None,
                        "examples": examples,
                        "note": "Fresh means distinct recorded real call IDs, not proof of provider internals. Identical probabilities do not establish caching. Cached replay is excluded from fresh-repeat agreement."})
    return reports


def batching_report(rows):
    grouped = defaultdict(dict)
    for row in rows:
        condition = row.get("condition")
        if row["split"] == "batching" or (row["split"] == "development" and condition == "batched"):
            if condition in {"batched", "separate"}:
                key = (row["task"], row["arm"], row["id"])
                if condition in grouped[key]:
                    raise ValueError("Duplicate batching condition")
                grouped[key][condition] = row
    output = defaultdict(list)
    for (task, arm, identity), conditions in grouped.items():
        if set(conditions) != {"batched", "separate"}:
            continue
        a, b = (_evaluated(conditions[c]) for c in ("batched", "separate"))
        valid = a.service_success and b.service_success
        output[(task, arm)].append({"id": identity, "both_valid": valid,
                                  "argmax_agreement": a.predicted_label == b.predicted_label if valid else None,
                                  "exact_distribution_match": a.distribution == b.distribution if valid else None,
                                  "total_variation": sum(abs(a.distribution[k] - b.distribution[k]) for k in LABELS[task]) / 2 if valid else None,
                                  "max_coordinate_change": max(abs(a.distribution[k] - b.distribution[k]) for k in LABELS[task]) if valid else None,
                                  "batched_error": a.error, "separate_error": b.error})
    reports = []
    for (task, arm), pairs in sorted(output.items()):
        valid = [p for p in pairs if p["both_valid"]]
        reports.append({"task": task, "arm": arm, "n_pairs": len(pairs), "pairs": pairs,
                        "n_errors": len(pairs) - len(valid), "n_valid_pairs": len(valid),
                        "classification_agreement": sum(p["argmax_agreement"] for p in valid) / len(valid) if valid else None,
                        "exact_distribution_matches": sum(p["exact_distribution_match"] for p in valid),
                        "mean_total_variation": sum(p["total_variation"] for p in valid) / len(valid) if valid else None,
                        "max_total_variation": max((p["total_variation"] for p in valid), default=None),
                        "max_coordinate_change": max((p["max_coordinate_change"] for p in valid), default=None)})
    return reports


def validate_completeness(directory, rows, manifest, selections):
    """Audit against frozen IDs, not merely the observed prediction denominator."""
    plan_path = directory / "plan.json"
    if not plan_path.exists():
        return {"status": "unverified_no_frozen_plan", "complete": False, "checks": []}
    actual_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    if manifest.get("plan_sha256") != actual_hash:
        raise ValueError("Frozen plan SHA256 does not match manifest")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    completed = {s["stage"] for s in manifest.get("stages", [])}
    observed = defaultdict(dict)
    for row in rows:
        key = (row["task"], row["split"], row["arm"], row.get("repeat", 0))
        if row["id"] in observed[key]:
            raise ValueError("Duplicate prediction ID in a planned split/arm/repeat")
        observed[key][row["id"]] = row
    checks, expected_keys = [], set()
    for task, data in plan["tasks"].items():
        all_arms = tuple(plan["question_specs"][task])
        chosen = selections.get(task)
        retained = (chosen["baseline"], chosen["selected"]) if chosen else ()
        stages = [("development", 0, data["development"], all_arms, "development")]
        stages.extend((split, 0, data[split], retained, split) for split in ("calibration", "evaluation", "fixtures"))
        stages.extend(("repeatability", repeat, [r for r in data["evaluation"] if r["id"] in data["repeatability_ids"]],
                       retained, "fresh_repeat_" + str(repeat)) for repeat in (1, 2))
        stages.append(("batching", 0, [r for r in data["development"] if r["id"] in data["batching_ids"]],
                       tuple(a for a in all_arms if a != "fewshot_contract"), "batching"))
        for split, repeat, expected, arms, stage in stages:
            for arm in arms:
                key = (task, split, arm, repeat)
                expected_keys.add(key)
                actual = observed[key]
                expected_ids = {r["id"] for r in expected}
                if set(actual) - expected_ids:
                    raise ValueError(f"Unexpected prediction IDs for {key}")
                for planned in expected:
                    row = actual.get(planned["id"])
                    if row is not None and any(row[k] != planned[k] for k in ("gold_label", "group")):
                        raise ValueError(f"Prediction gold/group differs from frozen plan: {key}")
                missing = sorted(expected_ids - set(actual))
                if missing and stage in completed:
                    raise ValueError(f"Completed stage {stage} is missing {len(missing)} predictions for {task}/{arm}")
                checks.append({"task": task, "split": split, "arm": arm, "repeat": repeat,
                               "expected": len(expected), "observed": len(actual), "missing_ids": missing})
    if set(observed) - expected_keys:
        raise ValueError("Predictions contain an unplanned task/split/arm/repeat")
    complete = set(selections) == set(plan["tasks"]) and all(not c["missing_ids"] for c in checks)
    return {"status": "complete" if complete else "partial", "complete": complete,
            "plan_sha256": actual_hash, "checks": checks}


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _fmt(value):
    return "N/A" if value is None else f"{value:.4f}"


def _markdown(result):
    lines = ["# Jev same-model research results", "",
             "This compares Jev request formulations and probability post-processing using the same service. It does not establish a general benchmark win or compare newly trained models.", "",
             "Arm selection uses development macro F1, then Brier, then arm name. Scalar temperatures use calibration labels only; held-out evaluation and fixtures are not used for fitting. Service errors count as operational failures. Probabilistic scores use valid responses; vendor-reported confidence is not ground truth.", ""]
    for task, detail in result["tasks"].items():
        lines += [f"## {task}", "", f"Baseline: `{detail['selection']['baseline']}`. Selected alternative: `{detail['selection']['selected']}`.", "",
                  "| Development arm | Accuracy | Macro F1 | Brier | Probability N | Errors |",
                  "|---|---:|---:|---:|---:|---:|"]
        for row in detail["selection"]["ranking"]:
            lines.append(f"| {row['arm']} | {_fmt(row['accuracy'])} | {_fmt(row['macro_f1'])} | {_fmt(row['brier_score'])} | {row['probability_score_denominator']} | {row['n_errors']} |")
        lines += ["", f"Selected alternative beats baseline on development macro F1: {detail['selection']['selected_beats_baseline_development_macro_f1']}.", "",
                  "| Split | Arm | Calibration | N | Errors | Accuracy | Macro F1 | Brier | Log loss | False merge |",
                  "|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
        for split, arms in detail["scores"].items():
            for arm, versions in arms.items():
                for version, score in versions.items():
                    if score is not None:
                        lines.append(f"| {split} | {arm} | {version} | {score['n_examples']} | {score['n_errors']} | {_fmt(score['accuracy'])} | {_fmt(score['macro_f1'])} | {_fmt(score['brier_score'])} | {_fmt(score['log_loss'])} | {_fmt(score.get('false_merge_rate'))} |")
        lines += ["", "Evaluation paired differences are selected minus baseline. Intervals condition on the fixed development choice and fitted temperatures; multiple comparisons are not corrected.", "",
                  "| Version | Metric | Difference | 95% interval | Paired Brier N |",
                  "|---|---|---:|---|---:|"]
        for version, comparison in detail["evaluation_comparisons"].items():
            if comparison is None:
                continue
            for metric, score in comparison["metrics"].items():
                interval = score["ci95"]
                ci = f"[{_fmt(interval[0])}, {_fmt(interval[1])}]" if interval else "N/A"
                lines.append(f"| {version} | {metric} | {_fmt(score['difference'])} | {ci} | {comparison['n_brier_pairs']} |")
        lines += ["", "Calibration fits:", ""]
        for arm, fit in detail["calibration"].items():
            lines.append(f"- `{arm}`: T={_fmt(fit['temperature'])}, {fit['n_fit_rows']}/{fit['n_calibration_rows']} calibration responses; calibration log loss {_fmt(fit['calibration_log_loss_before'])} to {_fmt(fit['calibration_log_loss_after'])}.")
        lines += ["", detail["conclusion"], ""]
    lines += ["## Fresh repeatability", ""]
    if not result["repeatability"]:
        lines += ["No paired fresh-repeat evidence available.", ""]
    for report in result["repeatability"]:
        lines.append(f"- {report['task']} / `{report['arm']}`: {report['n_examples']} examples, {report['n_valid_fresh_comparisons']} valid fresh pairwise comparisons, agreement {_fmt(report['classification_agreement'])}, {report['argmax_flips']} argmax flips, maximum total variation {_fmt(report['max_total_variation'])}; {report['n_fresh_comparisons_with_error']} fresh comparisons contain errors. Provenance: {report['provenance_counts']}.")
    lines += ["", "Fresh calls are identified by distinct recorded call IDs. Exact repeated outputs alone do not prove either service determinism or caching; local cached replays are not fresh-repeat evidence.", "", "## Usage and limitations", ""]
    usage = result["usage"]
    lines += [f"Recorded invocations: {usage['n_calls']}; usage reported for {usage['n_calls_with_usage']}. Input tokens: {usage['reported_input_tokens']}; output tokens: {usage['reported_output_tokens']}. Estimated USD for reported usage: {_fmt(usage['estimated_usd_for_reported_usage'])}. Invoice verified: no.", "", usage["note"], "",
              f"Frozen-plan completeness: {result['completeness']['status']}.", "",
              "Full input predictions, requests and responses remain in `predictions.jsonl` and `calls.jsonl`; hashes and manifest are recorded in `results.json`. Fixture scores are diagnostic, not independent natural-data evidence. Bootstrap intervals reflect sampled evaluation groups, not model-selection uncertainty. Positive-temperature calibration preserves argmax and therefore cannot itself improve accuracy.", ""]
    if result["batching"]:
        lines += ["Batching comparisons are descriptive and available in `results.json`; they do not establish a general batching-invariance guarantee.", ""]
    return "\n".join(lines)


def analyze(directory):
    directory = Path(directory)
    paths = {name: directory / name for name in ("manifest.json", "predictions.jsonl", "calls.jsonl")}
    manifest = json.loads(paths["manifest.json"].read_text(encoding="utf-8"))
    rows, calls = _read_jsonl(paths["predictions.jsonl"]), _read_jsonl(paths["calls.jsonl"])
    selected = select_arms(rows)
    recorded_selection = manifest.get("selection", {})
    for task, selection in selected.items():
        if task in recorded_selection and any(recorded_selection[task].get(k) != selection[k] for k in ("baseline", "selected")):
            raise ValueError("Manifest selection differs from development-only selection")
    completeness = validate_completeness(directory, rows, manifest, selected)
    calibration_path = directory / "calibration.json"
    frozen_calibration = None
    if calibration_path.exists():
        if manifest.get("calibration_sha256") != hashlib.sha256(calibration_path.read_bytes()).hexdigest():
            raise ValueError("Frozen calibration SHA256 differs from manifest")
        frozen_calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
    tasks = {}
    for task, selection in selected.items():
        arms = (selection["baseline"], selection["selected"])
        subset = lambda split, arm: [r for r in rows if r["task"] == task and r["split"] == split and r["arm"] == arm and r.get("repeat", 0) == 0]
        fits = {arm: fit_temperature(subset("calibration", arm)) for arm in arms}
        if frozen_calibration is not None and fits != frozen_calibration["fits"].get(task):
            raise ValueError("Recomputed calibration differs from frozen pre-evaluation fit")
        scores, evaluation, calibrated_predictions = {}, {}, []
        for split in ("development", "calibration", "evaluation", "fixtures"):
            scores[split] = {}
            for arm in arms:
                raw = subset(split, arm)
                adjusted = _calibrated(raw, fits[arm]["temperature"])
                scores[split][arm] = {"raw": summarize_records(raw),
                                     "calibrated": summarize_records(adjusted) if adjusted is not None else None}
                if split == "evaluation":
                    evaluation[arm] = {"raw": raw, "calibrated": adjusted}
                if split in {"evaluation", "fixtures"} and adjusted is not None:
                    calibrated_predictions.extend({**r, "calibration_temperature": fits[arm]["temperature"]} for r in adjusted)
        comparisons = {}
        for version in ("raw", "calibrated"):
            a, b = (evaluation[arm][version] for arm in arms)
            comparisons[version] = paired_bootstrap(a, b, task) if a is not None and b is not None else None
        primary = comparisons["raw"]["metrics"].get("macro_f1", {})
        ci = primary.get("ci95")
        conclusion = ("The raw selected alternative improves macro F1 with a paired 95% interval above zero on this evaluation split."
                      if ci and ci[0] > 0 else "The raw selected alternative lowers macro F1 with a paired 95% interval below zero on this evaluation split."
                      if ci and ci[1] < 0 else "No resolved improvement in raw operational macro F1: the paired interval includes zero or evidence is unavailable.")
        tasks[task] = {"selection": selection, "calibration": fits, "scores": scores,
                       "evaluation_comparisons": comparisons, "calibrated_predictions": calibrated_predictions,
                       "conclusion": conclusion if completeness["complete"] else "Incomplete or unverified frozen-plan coverage. " + conclusion}
    result = {"schema_version": 1, "analysis": "same-model Jev formulations and calibration; no underlying model training",
              "manifest": manifest, "input_sha256": {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()},
              "n_prediction_records": len(rows), "completeness": completeness, "tasks": tasks, "usage": summarize_usage(calls, manifest),
              "repeatability": repeatability_report(rows, calls), "batching": batching_report(rows),
              "metric_notes": ["Operational accuracy and macro F1 retain errors as failed predictions.",
                               "Full-sum multiclass Brier and log loss use valid eligible responses; paired Brier uses common valid responses.",
                               "ER uncertain fixture labels are explicitly excluded from semantic scores, never relabeled.",
                               "All error records are retained in the original JSONL files.",
                               "No evaluation or fixture labels are used in arm selection or temperature fitting."]}
    (directory / "results.json").write_text(json.dumps(json_safe(result), indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    (directory / "RESULTS.md").write_text(_markdown(result), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.run_dir)
    print(json.dumps({"tasks": {k: v["conclusion"] for k, v in result["tasks"].items()}, "usage": result["usage"]}, indent=2))


if __name__ == "__main__":
    main()
