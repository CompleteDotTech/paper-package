"""Read saved research artifacts and independently verify their internal consistency.

Standard library only: no backend imports, model calls, downloads, GPU operations,
or result rewrites. The sole output is results/research/validation.json.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RELATION = ("SUPPORTS", "REFUTES", "NOT_ENOUGH_INFO")
ENTITY = ("same", "different")
HISTORICAL = {
    "benchmark_relation_support_50_results.json": "605c4b162d3ed5e76bbece6ac8a68dfbad0726d6d88dec6e37d540ab6c0831a6",
    "benchmark_entity_resolution_100_results.json": "1cea5de3052e9bd1c8e5e1b043392b0f17c060e2f76dc53e3b1617b355489d14",
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def same_number(actual, expected, label):
    if expected is None:
        require(actual is None, f"{label}: expected null, got {actual}")
    else:
        require(isinstance(actual, (int, float)) and math.isfinite(actual)
                and math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9),
                f"{label}: saved {actual}, recomputed {expected}")


def probabilities(distribution, labels):
    require(isinstance(distribution, dict) and set(distribution) == set(labels), "Probability labels differ from task contract")
    require(all(type(p) in (int, float) and math.isfinite(p) and 0 <= p <= 1 for p in distribution.values()),
            "Nonfinite, nonnumeric or out-of-range probability")
    require(math.isclose(sum(distribution.values()), 1.0, rel_tol=0, abs_tol=1e-6), "Probabilities do not sum to one")


def check_logits(logits, mapping, temperature, distribution):
    require(math.isfinite(temperature) and temperature > 0, "Invalid temperature")
    require(len(logits) == len(distribution) and all(math.isfinite(x) for x in logits), "Invalid saved logits")
    values = [value / temperature for value in logits]
    maximum = max(values)
    weights = [math.exp(value - maximum) for value in values]
    for index, weight in enumerate(weights):
        same_number(distribution[mapping[str(index)]], weight / sum(weights), "Logit-derived probability")


def recompute(rows, summary, labels, expected_count, expected_modes=None):
    require(len(rows) == expected_count, "Unexpected record count")
    ids = [row.get("id", row.get("example_id")) for row in rows]
    require(None not in ids and len(set(ids)) == len(ids), "Missing or duplicate example ID")
    confusion = {gold: {pred: 0 for pred in (*labels, "ERROR")} for gold in labels}
    brier, losses, correct, confidence, excluded = [], [], [], [], []
    for row in rows:
        probabilities(row["distribution"], labels)
        require(not row.get("error") and not row.get("raw_error") and not row.get("validation_error"), "Saved response has an error")
        require(row.get("service_success", True), "Saved response marked unsuccessful")
        if expected_modes is not None:
            require(row.get("execution_mode") in expected_modes, "Unexpected recorded execution mode")
        prediction = max(labels, key=row["distribution"].get)
        require(prediction == row["predicted_label"], "Prediction is not canonical argmax")
        eligible = row["gold_label"] in labels
        if "semantic_eligible" in row:
            require(row["semantic_eligible"] == eligible, "Incorrect semantic eligibility")
        if not eligible:
            require(row["gold_label"] == "uncertain", "Unexpected excluded gold label")
            require(not row.get("correct", False), "Uncertain gold receives correctness credit")
            require(row.get("brier_score") is None and row.get("log_loss") is None, "Uncertain gold has a probability score")
            excluded.append(row)
            continue
        hit = prediction == row["gold_label"]
        if "correct" in row:
            require(row["correct"] == hit, "Stored correctness differs from exact match")
        confusion[row["gold_label"]][prediction] += 1
        value = sum((row["distribution"][label] - float(label == row["gold_label"])) ** 2 for label in labels)
        loss = -math.log(max(row["distribution"][row["gold_label"]], 1e-15))
        if "brier_score" in row:
            same_number(row["brier_score"], value, "Per-row full-sum Brier")
        if "log_loss" in row:
            same_number(row["log_loss"], loss, "Per-row clipped log loss")
        brier.append(value)
        losses.append(loss)
        correct.append(hit)
        confidence.append(row["distribution"][prediction])
    count = len(correct)
    require(count > 0, "No semantically scored examples")
    per_class = []
    recalls = []
    for label in labels:
        tp = confusion[label][label]
        actual = sum(confusion[label].values())
        predicted = sum(confusion[gold][label] for gold in labels)
        per_class.append(2 * tp / (actual + predicted) if actual + predicted else 0.0)
        if actual:
            recalls.append(tp / actual)
    ece = 0.0
    for bin_index in range(10):
        indexes = [index for index, conf in enumerate(confidence) if min(9, int(conf * 10)) == bin_index]
        if indexes:
            ece += abs(sum(confidence[i] for i in indexes) - sum(correct[i] for i in indexes)) / count
    calculated = {"accuracy": sum(correct) / count, "brier_score": sum(brier) / count,
                  "log_loss": sum(losses) / count, "macro_f1": sum(per_class) / len(labels),
                  "balanced_accuracy": sum(recalls) / len(recalls), "ece_10_bins": ece}
    for key, value in calculated.items():
        same_number(summary[key], value, key)
    require(summary["confusion"] == confusion, "Saved confusion matrix differs")
    require(summary["n_examples"] == len(rows), "Summary count mismatch")
    require(summary["n_semantic_examples"] == count, "Semantic denominator mismatch")
    require(summary["probability_score_denominator"] == count, "Probability score denominator mismatch")
    require(summary["n_excluded_gold"] == len(excluded), "Excluded gold count mismatch")
    require(summary["n_errors"] == 0, "Summary claims inference errors")
    return {"records": len(rows), "semantic_records": count, "excluded_uncertain": len(excluded),
            "accuracy": calculated["accuracy"], "full_sum_brier": calculated["brier_score"]}


class Verifier:
    def __init__(self, root):
        self.root, self.checks, self.input_hashes = root, [], {}

    def read(self, relative):
        path = self.root / relative
        data = path.read_bytes()
        self.input_hashes[str(relative)] = hashlib.sha256(data).hexdigest()
        return json.loads(data)

    def check(self, name, function):
        try:
            detail = function()
            self.checks.append({"check": name, "status": "pass", "detail": detail})
        except Exception as exc:
            self.checks.append({"check": name, "status": "fail", "error": f"{type(exc).__name__}: {exc}"})


def check_splits(splits, manifest, kind, expected_evaluation_count):
    require(digest(splits) == manifest["splits_sha256"], "Prepared split content hash differs from manifest")
    seen_ids, seen_groups, seen_entities = set(), set(), set()
    counts = {}
    for name in ("train", "calibration", "evaluation"):
        rows = splits[name]
        ids = {row["id"] for row in rows}
        groups = {row["group"] for row in rows}
        require(len(ids) == len(rows) and not ids & seen_ids, f"Duplicate/cross-split row IDs in {name}")
        require(not groups & seen_groups, f"Group leakage into {name}")
        if kind == "scifact":
            entities = {"document:" + row["document_id"] for row in rows} | {"text:" + digest(row["evidence"]) for row in rows}
        else:
            entities = {entity for row in rows for entity in row["identity_groups"]}
            if name != "train":
                require(sum(len(set(row["identity_groups"])) for row in rows) == len(entities), f"Repeated held-out identity within {name}")
        require(not entities & seen_entities, f"Document/identity leakage into {name}")
        observed = {"rows": len(rows), "labels": dict(Counter(row["gold_label"] for row in rows)),
                    "groups": len(groups), "row_ids_sha256": digest([row["id"] for row in rows])}
        require(observed == manifest["split_summary"][name], f"Split summary mismatch for {name}")
        counts[name] = len(rows)
        seen_ids.update(ids)
        seen_groups.update(groups)
        seen_entities.update(entities)
    require(counts["evaluation"] == expected_evaluation_count, "Unexpected evaluation size")
    return {"counts": counts, "split_sha256": manifest["splits_sha256"], "group_and_entity_or_document_disjoint": True}


def match_evaluation(rows, prepared):
    expected = {row["id"]: row["gold_label"] for row in prepared}
    actual = {row.get("id", row.get("example_id")): row["gold_label"] for row in rows}
    require(actual == expected and len(rows) == len(expected), "Saved evaluated IDs/gold labels differ from prepared evaluation")


def check_advanced(artifact):
    require(artifact["manifest"]["execution_mode"] == "synthetic" and artifact["manifest"]["model"] is None,
            "Advanced experiments are not marked synthetic")
    require(artifact["manifest"]["api_calls"] == 0, "Unexpected API calls")
    for name in ("evidence", "identity", "dependencies", "routing"):
        require(artifact[name]["execution_mode"] == "synthetic", f"Missing synthetic tag: {name}")
    splits = []

    def visit(value):
        if isinstance(value, dict):
            if "episodes" in value and "name" in value:
                splits.append(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(artifact)
    expected = artifact["manifest"]["evaluation_episodes_per_condition"]
    evaluation = [split for split in splits if split["name"].endswith("evaluation")]
    require(len(evaluation) == 13 and expected == 300, "Unexpected advanced evaluation conditions/count")
    require(all(split["episodes"] == expected for split in evaluation), "Synthetic condition episode count differs")
    require(len({split["episode_ids_sha256"] for split in splits}) == len(splits), "Synthetic split ID hashes collide")
    return {"execution_mode": "synthetic", "evaluation_conditions": len(evaluation), "episodes_per_condition": expected,
            "api_calls": 0, "raw_episode_outcomes_available_for_recomputation": False}


def check_compiler(artifact):
    require(artifact["execution_mode"] == "mock" and artifact["neural_or_api_execution"] is False, "Compiler probes incorrectly tagged")
    scenarios = artifact["scenarios"]
    require(len(scenarios) == 11 and len({row["scenario"] for row in scenarios}) == 11, "Unexpected compiler scenario count")
    for row in scenarios:
        require(row["status"] == row["expected_status"], f"Unexpected status: {row['scenario']}")
        if row["new_committed_mutations"] == 0:
            require(row["unchanged_snapshot"], f"Failed/no-op attempt changed snapshot: {row['scenario']}")
    comparison = artifact["quality_comparison"]
    rows = {row["id"]: row for row in comparison["frozen_rows"]}
    require(len(rows) == 7, "Unexpected frozen candidate count")
    for row in rows.values():
        probabilities(row["distribution"], RELATION)
    for table in (comparison["same_candidate_pool"], comparison["matched_committed_count"]):
        for name in ("confidence_only_positive", "typed_actions"):
            metric = table[name]
            selected = metric["committed_ids"]
            require(len(selected) == len(set(selected)) == metric["committed"], "Compiler commit count differs")
            correct = sum(rows[key]["gold"] == "SUPPORTS" for key in selected)
            require(correct == metric["correct_committed"] and len(selected) - correct == metric["false_committed"], "Compiler quality counts differ")
            same_number(metric["committed_precision"], correct / len(selected), "Compiler committed precision")
    matched = comparison["matched_committed_count"]
    require(matched["typed_actions"]["committed"] == matched["confidence_only_positive"]["committed"], "Matched-count comparison is unmatched")
    require(comparison["typed_provenance_entries"] == comparison["same_candidate_pool"]["typed_actions"]["committed"], "Compiler provenance/commit counts differ")
    return {"execution_mode": "mock", "scenarios": len(scenarios), "frozen_candidates": len(rows), "neural_or_api_execution": False}


def check_real_compiler_smoke(artifact):
    require(artifact["execution_mode"] == "real" and artifact["all_integration_assertions_passed"] is True,
            "Real compiler smoke assertions/mode failed")
    require(len(artifact["cases"]) == 2 and len({row["id"] for row in artifact["cases"]}) == 2,
            "Unexpected real compiler smoke case count")
    require(artifact["model_metadata"]["model_revision"] == artifact["revision"], "Resolved smoke model revision differs")
    for row in artifact["cases"]:
        probabilities(row["distribution"], RELATION)
        require(row["execution_mode"] == "real" and not row["errors"] and row["integration_assertions_passed"],
                "Smoke case contains an error/non-real response")
        require(max(row["distribution"], key=row["distribution"].get) == row["selected_class"] == row["expected_class"],
                "Smoke selected outcome differs from expectation/argmax")
        positive = row["selected_class"] == "SUPPORTS"
        require(row["transaction_status"] == ("committed" if positive else "no_op"), "Smoke polarity/transaction mismatch")
        require(len(row["edges_after"]) == row["provenance_entries_after"] == row["atomic_transaction_entries_after"] == int(positive),
                "Smoke graph/provenance/transaction counts differ")
    return {"execution_mode": "real", "manually_constructed_cases": 2, "all_recorded_assertions_passed": True,
            "held_out_generalization_evaluation": False}


def verify(root=ROOT, output=None):
    verifier = Verifier(root)
    for filename, expected in HISTORICAL.items():
        def historical(filename=filename, expected=expected):
            actual = hashlib.sha256((root / filename).read_bytes()).hexdigest()
            require(actual == expected, "Historical benchmark bytes changed")
            verifier.input_hashes[filename] = actual
            return {"sha256": actual, "unchanged": True}
        verifier.check("historical:" + filename, historical)
    manifests = verifier.read("results/research/data_manifest.json")
    prepared = {}
    for name, count in (("scifact", 339), ("entity_resolution", 413)):
        prepared[name] = verifier.read(f".cache/research-data/{name}-prepared.json")
        verifier.check("splits:" + name, lambda name=name, count=count: check_splits(prepared[name], manifests[name], name, count))

    nli = verifier.read("results/research/nli_results.json")
    require(nli["data_manifest"]["splits_sha256"] == manifests["scifact"]["splits_sha256"], "NLI data manifest differs")
    require(nli["model"]["execution_mode"] == "real", "NLI model execution mode is not real")
    require(nli["model"]["label_mapping"] == {"0": "REFUTES", "1": "SUPPORTS", "2": "NOT_ENOUGH_INFO"}, "Unexpected NLI checkpoint labels")
    for name, rows in nli["predictions"].items():
        def nli_arm(name=name, rows=rows):
            match_evaluation(rows, prepared["scifact"]["evaluation"])
            for row in rows:
                require(row["canonical_logits"] == [row["raw_logits"][index] for index in (1, 0, 2)],
                        "NLI raw-to-canonical label mapping differs")
                check_logits(row["canonical_logits"], {str(i): label for i, label in enumerate(RELATION)},
                             nli["metrics"][name]["temperature"], row["distribution"])
            return recompute(rows, nli["metrics"][name], RELATION, 339, {"real"})
        verifier.check("nli:" + name, nli_arm)
    prior_rows = [{**row, "distribution": nli["train_prior"], "predicted_label": max(nli["train_prior"], key=nli["train_prior"].get)}
                  for row in prepared["scifact"]["evaluation"]]
    verifier.check("nli:train_prior", lambda: recompute(prior_rows, nli["metrics"]["train_prior"], RELATION, 339))

    er = verifier.read("results/research/er_results.json")
    require(er["data_manifest"]["splits_sha256"] == manifests["entity_resolution"]["splits_sha256"], "ER data manifest differs")
    for name, arm in er["arms"].items():
        def er_arm(name=name, arm=arm):
            rows = arm["predictions"]
            match_evaluation(rows, prepared["entity_resolution"]["evaluation"])
            if name.startswith("er-"):
                for row in rows:
                    require(row["metadata"]["local_checkpoint_sha256"].get("model.safetensors"), "Neural ER checkpoint hash missing")
                    raw = row["raw_output"]
                    require(raw["label_mapping"] == {"0": "different", "1": "same"}, "Unexpected ER checkpoint labels")
                    check_logits(raw["logits"], raw["label_mapping"], row["metadata"]["temperature"], row["distribution"])
            return recompute(rows, arm["summary"], ENTITY, 413, {"real"})
        verifier.check("er:" + name, er_arm)

    fixtures = verifier.read("results/research/fixture_diagnostics.json")
    require(fixtures["manifest"]["api_calls"] == 0, "Fixture diagnostics contain API calls")
    for task, labels, count in (("relation_support", RELATION, 50), ("entity_resolution", ENTITY, 100)):
        for name, arm in fixtures[task]["arms"].items():
            def fixture_arm(task=task, labels=labels, count=count, arm=arm):
                rows = arm["results"]
                checked = recompute(rows, arm["summary"], labels, count, {"real"})
                for row in rows:
                    response = arm["responses"][row["request_data"]["request_id"]]
                    require(response["execution_mode"] == row["execution_mode"] and response["distribution"] == row["distribution"], "Fixture response/result mismatch")
                if task == "entity_resolution":
                    require(checked["excluded_uncertain"] == 12 and checked["semantic_records"] == 88, "ER fixture uncertainty denominator differs")
                    require(arm["uncertain_diagnostics"]["truth_metrics"] is None, "Uncertain fixture has truth metrics")
                return checked
            verifier.check(f"fixture:{task}:{name}", fixture_arm)
    verifier.check("advanced:synthetic_tags_counts", lambda: check_advanced(verifier.read("results/research/advanced_experiments.json")))
    verifier.check("compiler:mock_tags_counts", lambda: check_compiler(verifier.read("results/research/compiler_results.json")))
    verifier.check("compiler:real_integration_smoke", lambda: check_real_compiler_smoke(verifier.read("results/research/real_compiler_smoke.json")))

    failed = [check["check"] for check in verifier.checks if check["status"] != "pass"]
    result = {
        "schema_version": 1, "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if not failed else "fail", "passed_checks": len(verifier.checks) - len(failed),
        "failed_checks": failed, "checks": verifier.checks, "input_sha256": verifier.input_hashes,
        "verifier_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "model_calls": 0, "network_calls": 0, "gpu_used": False,
        "limitations": [
            "Checks saved records and prepared data; execution_mode is recorded provenance, not independently authenticated proof of model execution.",
            "Recomputes point metrics and logits/probabilities, not bootstrap confidence intervals or model training.",
            "Checks declared groups/documents/identities and exact prepared hashes; does not establish absence of all semantic near-duplicates or pretraining contamination.",
            "Synthetic episode outcomes are not stored individually, so their aggregate quality estimates cannot be independently recomputed here.",
            "Compiler artifact checks verify recorded outcomes/counts; runtime behavior is covered by separate compiler tests, not rerun by this verifier.",
            "Checkpoint hash presence is verified; weights are not loaded or rehashed, and monetary cost/latency measurements are not independently repeated.",
            "Historical execution source hashes are not required to equal later CLI/reporting code; this does not rewrite execution provenance.",
            "Historical intermediate archive and partial artifacts are not treated as current headline results.",
        ],
    }
    destination = output or root / "results/research/validation.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": result["status"], "passed_checks": result["passed_checks"], "failed_checks": failed,
                      "output": str(destination)}))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(args.root.resolve(), args.output)
    raise SystemExit(0 if result["status"] == "pass" else 1)
