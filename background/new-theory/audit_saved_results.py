"""Audit saved benchmark records without importing pgc or invoking any backend.

Measurements describe the saved run only, not model performance on a new run.
The ER label adapter is a diagnostic counterfactual, not a rerun. The binary
Brier score uses only answerable rows with a valid two-class distribution and
reports its denominator; it does not manufacture an uncertainty probability.
Fallback-compatible ranges are clues, never proof of the backend execution mode.
Usage: python audit_saved_results.py --output audit_snapshot.json
"""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path


FILES = (
    ("benchmark_relation_support_50_results.json", ("true", "false")),
    ("benchmark_entity_resolution_100_results.json", ("same", "different")),
)


def fraction(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator,
            "value": numerator / denominator if denominator else None}


def is_error(row):
    return row["predicted_label"] == "ERROR" or bool(row.get("error"))


def valid_binary(distribution, labels):
    return (
        set(distribution) == set(labels)
        and all(isinstance(p, (float, int)) and math.isfinite(p) and 0 <= p <= 1
                for p in distribution.values())
        and math.isclose(sum(distribution.values()), 1.0, abs_tol=1e-9)
    )


def diagnostics(rows, labels, adapter=None):
    """Recompute labels and valid binary Brier without using stored correctness."""
    adapter = adapter or {}
    answerable = [r for r in rows if r["gold_label"] in labels]
    prediction = lambda r: adapter.get(r["predicted_label"], r["predicted_label"])
    confusion = defaultdict(Counter)
    for row in rows:
        confusion[row["gold_label"]][prediction(row)] += 1
    scored = []
    for row in answerable:
        original = row.get("distribution", {})
        distribution = {adapter.get(label, label): p for label, p in original.items()}
        if len(distribution) != len(original) or is_error(row):
            continue
        if valid_binary(distribution, labels):
            scored.append((distribution[labels[0]] - (row["gold_label"] == labels[0])) ** 2)
    return {
        "strict_exact_accuracy": fraction(sum(not is_error(r) and prediction(r) == r["gold_label"] for r in rows), len(rows)),
        "answerable_exact_accuracy": fraction(sum(not is_error(r) and prediction(r) == r["gold_label"] for r in answerable), len(answerable)),
        "confusion": {gold: dict(counts) for gold, counts in sorted(confusion.items())},
        "binary_brier_answerable": {
            "definition": "mean((p(first_binary_label) - indicator(gold == first_binary_label)) ** 2)",
            "first_binary_label": labels[0],
            "valid_distribution_rows": len(scored),
            "answerable_rows": len(answerable),
            "excluded_answerable_rows": len(answerable) - len(scored),
            "value": sum(scored) / len(scored) if scored else None,
        },
    }


def provenance(rows, backend, labels):
    # Existing files omit execution mode. Do not infer it from a backend name.
    mode_keys = ("execution_mode", "backend_mode", "is_mock", "fallback_used")
    marker_count = sum(any(key in row for key in mode_keys) for row in rows)
    result = {
        "rows_with_explicit_mode_marker": marker_count,
        "rows_without_explicit_mode_marker": len(rows) - marker_count,
        "error_rows": sum(is_error(row) for row in rows),
        "nonerror_rows_without_explicit_mode_marker": sum(
            not is_error(row) and not any(key in row for key in mode_keys) for row in rows),
        "rows_with_saved_error_message": sum(bool(row.get("error")) for row in rows),
        "rows_with_backend_version": sum(bool(row.get("backend_version")) for row in rows),
        "rows_with_model_revision": sum(bool(row.get("model_revision")) for row in rows),
    }
    if backend.startswith("specialist-"):
        compatible = sum(
            valid_binary(row.get("distribution", {}), labels)
            and 0.3 <= row["distribution"][labels[0]] <= 0.9
            and isinstance(row.get("latency_ms"), (int, float))
            and 50 <= row["latency_ms"] <= 150
            for row in rows
        )
        result["rows_compatible_with_current_random_fallback_ranges"] = compatible
        result["interpretation"] = (
            "Current specialist fallback samples p in [0.3, 0.9] and synthetic latency in [50, 150] ms. "
            "Compatibility is circumstantial; execution mode is not recoverable from these records."
        )
    return result


def audit_file(path, labels):
    content = path.read_bytes()
    saved = json.loads(content)
    grouped = defaultdict(list)
    gold_by_example = {}
    seen = set()
    for row in saved["raw_results"]:
        key = (row["backend"], row["example_id"])
        if key in seen:
            raise ValueError(f"Duplicate backend/example row: {key}")
        seen.add(key)
        example_id = row["example_id"]
        if example_id in gold_by_example and gold_by_example[example_id] != row["gold_label"]:
            raise ValueError(f"Conflicting gold labels: {example_id}")
        gold_by_example[example_id] = row["gold_label"]
        grouped[row["backend"]].append(row)
    if any(len(rows) != len(gold_by_example) for rows in grouped.values()):
        raise ValueError("Backend coverage differs; audit requires matched saved examples")
    counts = Counter(gold_by_example.values())
    answerable_counts = Counter({label: count for label, count in counts.items() if label in labels})
    max_all = max(counts.values())
    max_answerable = max(answerable_counts.values())
    backends = {}
    for backend, rows in grouped.items():
        result = diagnostics(rows, labels)
        result.update({
            "rows": len(rows),
            "saved_reported_accuracy": saved["backends"][backend]["accuracy"],
            "saved_reported_brier_not_standard_multiclass_brier": saved["backends"][backend]["brier_score"],
            "saved_correct_count": sum(bool(row["correct"]) for row in rows),
            "saved_correct_but_not_exact_count": sum(bool(row["correct"]) and row["predicted_label"] != row["gold_label"] for row in rows),
            "uncertain_gold_rows": sum(row["gold_label"] == "uncertain" for row in rows),
            "error_rows_credited_correct": sum(is_error(row) and bool(row["correct"]) for row in rows),
            "empty_distribution_rows": sum(not row.get("distribution") for row in rows),
            "provenance": provenance(rows, backend, labels),
        })
        if labels == ("same", "different"):
            result["label_adapter_diagnostic"] = {
                "status": "Counterfactual recoding of saved outputs only; no inference or rerun",
                "adapter": {"true": "same", "false": "different"},
                **diagnostics(rows, labels, {"true": "same", "false": "different"}),
            }
        backends[backend] = result
    return {
        "source_path": str(path.resolve()),
        "sha256": hashlib.sha256(content).hexdigest(),
        "saved_timestamp": saved.get("timestamp"),
        "example_count": len(gold_by_example),
        "raw_row_count": len(saved["raw_results"]),
        "gold_label_counts": dict(sorted(counts.items())),
        "majority_baselines": {
            "status": "Descriptive baselines using observed evaluation-set class counts; not fitted deployment predictors",
            "strict_all_labels": {"labels_tied_for_majority": sorted(k for k, v in counts.items() if v == max_all), **fraction(max_all, len(gold_by_example))},
            "answerable_binary": {"labels_tied_for_majority": sorted(k for k, v in answerable_counts.items() if v == max_answerable), **fraction(max_answerable, sum(answerable_counts.values()))},
        },
        "backends": backends,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent.parent / "typed-probabilistic-graph-compiler")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().with_name("audit_snapshot.json"))
    args = parser.parse_args()
    output = {
        "schema_version": 1,
        "scope": "Offline audit of two saved JSON artifacts; no model calls, no imports from pgc, no source edits",
        "interpretation": [
            "Exact counts characterize saved records, not verified specialist model performance.",
            "Answerable subset excludes uncertain gold labels and is a different evaluation target.",
            "API errors count as failures for end-to-end exact accuracy but have no probabilistic score.",
            "No three-class Brier is fabricated: uncertainty probabilities are absent.",
            "Saved Brier is a top-prediction correctness score; it is not a proper multiclass Brier score.",
            "No execution provenance, hardware, measured wall-clock timing, or monetary cost can be reconstructed.",
        ],
        "datasets": {filename: audit_file(args.repo / filename, labels) for filename, labels in FILES},
    }
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.output.resolve()}")
    for filename, dataset in output["datasets"].items():
        print(f"{filename}: {dataset['example_count']} examples; sha256={dataset['sha256']}")
        for backend, summary in dataset["backends"].items():
            exact = summary["strict_exact_accuracy"]
            binary = summary["answerable_exact_accuracy"]
            errors = summary["provenance"]["error_rows"]
            print(f"  {backend}: exact={exact['numerator']}/{exact['denominator']}; answerable={binary['numerator']}/{binary['denominator']}; errors={errors}")


if __name__ == "__main__":
    main()
