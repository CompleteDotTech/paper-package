"""Independent metric and provenance controls; never call Jev or load models."""

import json
import hashlib
import math
from pathlib import Path
import tempfile
import unittest

from pgc.experiments.analyze_jev_research import (
    analyze, fit_temperature, paired_bootstrap, repeatability_report, select_arms,
    summarize_records, summarize_usage, temperature_scale,
)


def record(identity, gold="same", p=.8, *, arm="baseline_noul", split="evaluation",
           task="entity_resolution", group=None, error=None, repeat=0, call_ids=None):
    distribution = {"same": p, "different": 1 - p} if task == "entity_resolution" else {
        "SUPPORTS": p, "REFUTES": 1 - p, "NOT_ENOUGH_INFO": 0.0}
    return {"task": task, "split": split, "arm": arm, "id": identity,
            "gold_label": gold, "group": group or identity, "distribution": distribution,
            "error": error, "execution_mode": "real", "repeat": repeat,
            "call_ids": call_ids or [identity + ":" + str(repeat)]}


class JevAnalysisTests(unittest.TestCase):
    def test_literal_metrics_keep_failures_and_exclude_uncertain_gold(self):
        rows = [record("a"), record("b", "different"), record("c", "different", error="timeout"),
                record("d", "uncertain")]
        score = summarize_records(rows)
        self.assertEqual(score["n_examples"], 4)
        self.assertEqual(score["n_semantic_examples"], 3)
        self.assertEqual(score["confusion"]["different"]["ERROR"], 1)
        self.assertAlmostEqual(score["accuracy"], 1 / 3)
        self.assertAlmostEqual(score["macro_f1"], 1 / 3)
        self.assertAlmostEqual(score["conditional_accuracy"], .5)
        self.assertAlmostEqual(score["brier_score"], .68)
        self.assertAlmostEqual(score["log_loss"], (-math.log(.8) - math.log(.2)) / 2)
        self.assertEqual(score["probability_score_denominator"], 2)
        self.assertEqual(score["false_merge_rate"], .5)
        malformed = record("broken")
        malformed["distribution"] = {"same": 1.1, "different": -.1}
        score = summarize_records([malformed])
        self.assertEqual(score["accuracy"], 0)
        self.assertIsNone(score["brier_score"])
        self.assertEqual(score["n_validation_errors"], 1)

    def test_selection_ignores_heldout_and_chooses_alternative_even_if_worse(self):
        rows = [record("a", p=.9, split="development"),
                record("a", p=.4, split="development", arm="z_alternative"),
                record("a", p=.4, split="development", arm="a_alternative"),
                record("a", p=.99, arm="z_alternative")]
        choice = select_arms(rows)["entity_resolution"]
        self.assertEqual(choice["selected"], "a_alternative")
        self.assertEqual(choice["ranking"][0]["arm"], "baseline_noul")
        with self.assertRaisesRegex(ValueError, "identical"):
            select_arms(rows + [record("extra", arm="a_alternative", split="development")])

    def test_temperature_known_optimum_and_split_gate(self):
        # Four identical forecasts, three positives: optimal calibrated p=.75.
        # logit(.9) / T = logit(.75), so T = log(9) / log(3) = 2.
        rows = [record(str(i), "same" if i < 3 else "different", p=.9, split="calibration") for i in range(4)]
        fit = fit_temperature(rows)
        self.assertAlmostEqual(fit["temperature"], 2.0, places=5)
        scaled = temperature_scale(rows[0]["distribution"], fit["temperature"])
        self.assertAlmostEqual(scaled["same"], .75, places=6)
        self.assertLess(fit["calibration_log_loss_after"], fit["calibration_log_loss_before"])
        self.assertEqual(max(scaled, key=scaled.get), "same")
        with self.assertRaisesRegex(ValueError, "calibration rows only"):
            fit_temperature([record("evaluation")])
        failed = fit_temperature([record("bad", split="calibration", error="timeout")])
        self.assertIsNone(failed["temperature"])
        self.assertEqual(failed["n_excluded_rows"], 1)

    def test_group_bootstrap_preserves_components_and_common_valid_denominator(self):
        # One component contains two jointly improved rows: every resample must
        # preserve both rows. The failed baseline row still counts in accuracy.
        baseline = [record("a", "SUPPORTS", .1, task="relation_support", group="component"),
                    record("b", "SUPPORTS", .1, task="relation_support", group="component", error="timeout")]
        candidate = [{**r, "arm": "candidate", "distribution": {"SUPPORTS": .9, "REFUTES": .1, "NOT_ENOUGH_INFO": 0}, "error": None} for r in baseline]
        compared = paired_bootstrap(baseline, candidate, "relation_support", resamples=100)
        self.assertEqual(compared["n_groups"], 1)
        self.assertEqual(compared["n_brier_pairs"], 1)
        self.assertEqual(compared["metrics"]["accuracy"]["ci95"], [1, 1])
        self.assertAlmostEqual(compared["metrics"]["brier_score"]["difference"], -1.6)
        self.assertAlmostEqual(compared["metrics"]["macro_f1"]["difference"], 1 / 3)
        with self.assertRaisesRegex(ValueError, "identical IDs"):
            paired_bootstrap(baseline, candidate[:1], "relation_support")

    def test_fresh_repeats_are_not_inferred_from_identical_outputs_and_usage_is_per_call(self):
        rows = [record("a", call_ids=["batch0"]),
                record("a", split="repeatability", repeat=1, call_ids=["batch1"]),
                record("a", split="repeatability", repeat=2, call_ids=["batch1"])]
        calls = [{"call_id": identity, "request_sha256": "identical-complete-payload", "execution_mode": "real", "tokens_used": {"input": 100, "output": 20}, "error": None} for identity in ("batch0", "batch1")]
        report = repeatability_report(rows, calls)[0]
        self.assertEqual(report["n_fresh_comparisons"], 2)
        self.assertEqual(report["exact_distribution_matches"], 2)
        self.assertEqual(report["provenance_counts"]["cached_or_reused_calls"], 1)
        self.assertEqual(report["max_total_variation"], 0)
        usage = summarize_usage(calls, {"unit_prices_usd_per_million_tokens": {"input": 2, "output": 4}})
        self.assertEqual(usage["reported_total_tokens"], 240)
        self.assertAlmostEqual(usage["estimated_usd_for_reported_usage"], .00056)
        self.assertFalse(usage["invoice_verified"])
        with self.assertRaisesRegex(ValueError, "Duplicate call IDs"):
            summarize_usage(calls + [calls[0]], {})

    def test_offline_artifact_reports_null_evidence_and_preserves_input_bytes(self):
        rows = [record("dev", split="development"), record("dev", split="development", arm="candidate"),
                record("test"), record("test", arm="candidate", error="timeout")]
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "manifest.json").write_text(json.dumps({"selection": {"entity_resolution": {"baseline": "baseline_noul", "selected": "candidate"}}}), encoding="utf-8")
            path = directory / "predictions.jsonl"
            path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
            (directory / "calls.jsonl").write_text("", encoding="utf-8")
            original = path.read_bytes()
            result = analyze(directory)
            self.assertEqual(path.read_bytes(), original)
            self.assertIsNone(result["tasks"]["entity_resolution"]["evaluation_comparisons"]["calibrated"])
            self.assertEqual(result["tasks"]["entity_resolution"]["scores"]["evaluation"]["candidate"]["raw"]["n_errors"], 1)
            self.assertIsNone(result["usage"]["estimated_usd_for_reported_usage"])
            self.assertTrue((directory / "RESULTS.md").exists())
            self.assertEqual(json.loads((directory / "results.json").read_text())["n_prediction_records"], 4)
            plan = {"tasks": {"entity_resolution": {"development": [rows[0]], "calibration": [],
                    "evaluation": [rows[2], record("missing")], "fixtures": [], "repeatability_ids": [], "batching_ids": []}},
                    "question_specs": {"entity_resolution": {"baseline_noul": {}, "candidate": {}}}}
            plan_path = directory / "plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            manifest = {"plan_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(), "stages": [{"stage": "evaluation"}]}
            (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing 1 predictions"):
                analyze(directory)


if __name__ == "__main__":
    unittest.main()
