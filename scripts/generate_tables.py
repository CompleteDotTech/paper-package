"""Create compact paper tables from saved artifacts, without inference or network.

Run from anywhere. Defaults point inside the portable paper package. Inputs are
never modified; table JSON retains full precision while Markdown rounds values.
"""
import argparse
import hashlib
import json
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def select(mapping, keys):
    return {key: mapping.get(key) for key in keys}


def generate(run_dir, data_manifest, output):
    result = load(run_dir / "results.json")
    data = load(data_manifest)
    tables = {
        "provenance": {
            "results_sha256": hashlib.sha256((run_dir / "results.json").read_bytes()).hexdigest(),
            "data_manifest_sha256": hashlib.sha256(data_manifest.read_bytes()).hexdigest(),
            "model": result["manifest"]["model"],
            "seed": result["manifest"]["seed"],
            "rounding": "JSON retains source precision; Markdown displays six decimal places.",
            "comparison": "selected minus baseline; unadjusted paired 95% percentile bootstrap intervals, conditional on fixed selection",
        },
        "splits": [], "development": [], "evaluation": [], "paired_effects": [],
        "calibration": [], "confusion": [], "fixtures": [], "repeatability": [],
        "batching": [], "usage": result["usage"],
    }
    for task, manifest in data.items():
        for split, summary in manifest["split_summary"].items():
            tables["splits"].append({"task": task, "split": split, **summary})
    metric_keys = ("n_examples", "n_semantic_examples", "n_excluded_gold", "n_errors",
                   "probability_score_denominator", "accuracy", "macro_f1", "balanced_accuracy",
                   "brier_score", "log_loss", "ece_10_bins", "false_merge_count",
                   "false_merge_denominator", "false_merge_rate")
    for task, values in result["tasks"].items():
        for row in values["selection"]["ranking"]:
            tables["development"].append({"task": task, **row, "selected": row["arm"] == values["selection"]["selected"]})
        for split in ("evaluation", "fixtures"):
            for arm, versions in values["scores"][split].items():
                for version, metrics in versions.items():
                    tables[split].append({"task": task, "arm": arm, "version": version,
                                          **select(metrics, metric_keys)})
                for gold, predictions in versions["raw"]["confusion"].items():
                    for prediction, count in predictions.items():
                        tables["confusion"].append({"task": task, "split": split, "arm": arm,
                                                    "gold": gold, "prediction": prediction, "count": count})
        for arm, fit in values["calibration"].items():
            tables["calibration"].append({"task": task, "arm": arm,
                **select(fit, ("n_calibration_rows", "n_fit_rows", "n_excluded_rows", "fit_class_counts",
                               "missing_fit_classes", "n_clipped_probability_coordinates", "temperature",
                               "calibration_log_loss_before", "calibration_log_loss_after", "boundary_fit"))})
        for version, comparison in values["evaluation_comparisons"].items():
            for metric, effect in comparison["metrics"].items():
                tables["paired_effects"].append({"task": task, "version": version, "metric": metric,
                    "n_pairs": comparison["n_pairs"], "n_groups": comparison["n_groups"],
                    "n_brier_pairs": comparison["n_brier_pairs"], **effect})
    for row in result["repeatability"]:
        tables["repeatability"].append({key: value for key, value in row.items() if key != "examples"})
    for row in result["batching"]:
        tables["batching"].append({key: value for key, value in row.items() if key != "pairs"})
    output.mkdir(parents=True, exist_ok=True)
    (output / "tables.json").write_text(json.dumps(tables, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")

    def fmt(value):
        if value is None:
            return "—"
        if isinstance(value, float):
            return f"{value:.6f}"
        if isinstance(value, list) and all(isinstance(item, (int, float)) for item in value):
            return "[" + ", ".join(fmt(item) for item in value) + "]"
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value).replace("|", "\\|")

    lines = ["# Research tables", "", "Generated directly from saved artifacts by `scripts/generate_tables.py`; no model calls. Full precision and additional fields are in `tables.json`.", "",
             "All intervals are selected minus baseline, paired percentile 95%, 2,000 draws, seed 20260917. They are exploratory and unadjusted for multiple comparisons. SciFact resamples 247 connected components; DBLP–ACM resamples 413 identity-disjoint pairs.", ""]

    def table(title, rows, columns, note=""):
        lines.extend([f"## {title}", ""])
        if note:
            lines.extend([note, ""])
        lines.extend(["| " + " | ".join(label for _, label in columns) + " |",
                      "| " + " | ".join("---" for _ in columns) + " |"])
        lines.extend("| " + " | ".join(fmt(row.get(key)) for key, _ in columns) + " |" for row in rows)
        lines.append("")

    table("Prepared data", tables["splits"], [("task", "Task"), ("split", "Split"), ("rows", "Rows"), ("groups", "Stored groups"), ("labels", "Class counts")],
          "ER training groups are row IDs; they are not independent identity units. Calibration and evaluation were additionally reduced to identity-disjoint pairs. Only six demonstrations and 60 arm-selection examples from each prepared training split were used by Jev.")
    table("All development arms", tables["development"], [("task", "Task"), ("arm", "Arm"), ("selected", "Selected"), ("accuracy", "Accuracy"), ("macro_f1", "Macro-F1"), ("brier_score", "Brier"), ("n_errors", "Errors"), ("probability_score_denominator", "Probability n")],
          "Each arm has 60 eligible examples. Selection excludes baseline, ranks operational macro-F1, then Brier, then arm name. ER three-way perfect-F1 tie is resolved by Brier.")
    table("Held-out classification and probability scores", tables["evaluation"], [("task", "Task"), ("arm", "Arm"), ("version", "Version"), ("n_semantic_examples", "Eligible n"), ("n_errors", "Errors"), ("probability_score_denominator", "Probability n"), ("accuracy", "Accuracy"), ("macro_f1", "Macro-F1"), ("brier_score", "Brier"), ("log_loss", "Log loss")],
          "Operational classification retains service failures. Probability scores use valid responses only. Brier is the sum over every class (range 0–2), including both ER coordinates. Scalar calibration preserves predicted labels.")
    table("Paired held-out effects", tables["paired_effects"], [("task", "Task"), ("version", "Version"), ("metric", "Metric"), ("difference", "Difference"), ("ci95", "95% interval"), ("n_brier_pairs", "Common-success n")],
          "Brier effects use common-success pairs; classification effects retain all eligible rows, including errors. A negative Brier or false-merge-rate effect is an improvement. ER accuracy interval includes zero; ER macro-F1 interval excludes zero on this split. Relation macro-F1 is unresolved.")
    table("Calibration fits", tables["calibration"], [("task", "Task"), ("arm", "Arm"), ("n_calibration_rows", "Planned n"), ("n_fit_rows", "Fit n"), ("temperature", "T"), ("calibration_log_loss_before", "Raw log loss"), ("calibration_log_loss_after", "Fitted log loss"), ("boundary_fit", "Boundary")],
          "Fits use calibration labels only. None reaches a boundary. Improvement in fitted calibration log loss is not independent test evidence.")
    table("Secondary fixtures", [x for x in tables["fixtures"] if x["version"] == "raw"], [("task", "Task"), ("arm", "Arm"), ("n_examples", "Total n"), ("n_semantic_examples", "Eligible n"), ("n_excluded_gold", "Excluded gold"), ("accuracy", "Accuracy"), ("macro_f1", "Macro-F1"), ("false_merge_count", "False merges"), ("false_merge_denominator", "Negative n")],
          "Fixtures have prior development use and unadjudicated labels. The 12 uncertain ER cases are retained but excluded from binary correctness and probability scores.")
    table("Fresh repeated calls", tables["repeatability"], [("task", "Task"), ("arm", "Arm"), ("n_examples", "Examples"), ("n_examples_with_all_three_fresh_labels_identical", "All-three labels equal"), ("n_valid_fresh_comparisons", "Valid pair comparisons"), ("exact_distribution_matches", "Exact vectors equal"), ("classification_agreement", "Label agreement"), ("mean_total_variation", "Mean TV"), ("max_total_variation", "Max TV")],
          "Three fresh responses for each of 20 examples produce 60 pair comparisons per arm; those 60 comparisons are dependent. Round zero reuses the original evaluation call with identical payload. Immediate calls do not establish long-term determinism.")
    table("Development batching control", tables["batching"], [("task", "Task"), ("arm", "Arm"), ("n_pairs", "Pairs"), ("n_errors", "Errors"), ("classification_agreement", "Label agreement"), ("exact_distribution_matches", "Exact vectors equal"), ("max_total_variation", "Max TV")],
          "Exploratory batched versus separate calls on development examples. These controls do not select arms or establish accuracy on a new test set.")
    usage_rows = [{"measure": key, "value": value} for key, value in tables["usage"].items() if not isinstance(value, dict)]
    table("Usage and timing", usage_rows, [("measure", "Measure"), ("value", "Value")],
          "Usage includes the toy preflight and failed requests. Total call latency sums overlapping requests and is not elapsed wall time. Cost is an estimate using the frozen price snapshot, not a provider invoice or complete-pipeline cost.")
    table("Raw confusion counts", tables["confusion"], [("task", "Task"), ("split", "Split"), ("arm", "Arm"), ("gold", "Gold"), ("prediction", "Prediction"), ("count", "Count")])
    (output / "TABLES.md").write_text("\n".join(lines), encoding="utf-8")
    return tables


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=PACKAGE / "reproduction/results/jev/run-20260918")
    parser.add_argument("--data-manifest", type=Path, default=PACKAGE / "reproduction/results/research/data_manifest.json")
    parser.add_argument("--output", type=Path, default=PACKAGE / "tables")
    args = parser.parse_args()
    tables = generate(args.run_dir, args.data_manifest, args.output)
    print(json.dumps({"status": "generated", "tables": len(tables) - 1, "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
