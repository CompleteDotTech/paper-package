"""Semantic contracts and failure accounting, with no model downloads or APIs."""

import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pgc.decision import DecisionBackend, DecisionRequest, DecisionResponse
from pgc.evaluation import (
    DiagnosticBackend, ER_LABELS, RELATION_LABELS, brier_score, evaluate_request, group_split,
    log_loss, save_benchmark_artifact, summarize_results, validate_distribution,
)
from pgc.experiments.benchmark_entity_resolution_100 import EntityResolutionBenchmark
from pgc.experiments.entity_resolution_100 import ERExample
from pgc.experiments.scifact_benchmark import SciFactBenchmark, SciFactExample
from pgc.ir import PrimitiveType


class StubBackend(DecisionBackend):
    def __init__(self, distribution=None, error=None, raises=False):
        self.distribution = distribution
        self.error = error
        self.raises = raises
        self.requests = []

    def name(self):
        return "test-backend"

    def version(self):
        return "test-revision"

    def decide(self, request):
        self.requests.append(request)
        if self.raises:
            raise RuntimeError("simulated outage")
        return DecisionResponse(
            request_id=request.request_id, distribution=self.distribution,
            confidence=0.99, error=self.error, execution_mode="mock",
            metadata={"test_fixture": True}, tokens_used={"input": 4, "output": 3},
            latency_ms=9999.0,
        )

    def batch_decide(self, requests):
        return [self.decide(request) for request in requests]


def er_result(gold="same", distribution=None, error=None, raises=False):
    backend = StubBackend(distribution, error, raises)
    request = DecisionRequest("request", PrimitiveType.NOUL, "Same?", "A\nB",
                              task="entity_resolution", labels=list(ER_LABELS))
    return evaluate_request("example", gold, backend, request, ER_LABELS,
                            excluded_gold_labels=("uncertain",))


class DistributionTests(unittest.TestCase):
    def test_multiclass_brier_uses_all_coordinates(self):
        distribution = {"SUPPORTS": 0.6, "REFUTES": 0.3, "NOT_ENOUGH_INFO": 0.1}
        self.assertAlmostEqual(brier_score(distribution, "SUPPORTS", RELATION_LABELS), 0.26)
        self.assertAlmostEqual(log_loss(distribution, "SUPPORTS", RELATION_LABELS), -math.log(0.6))
        self.assertAlmostEqual(brier_score({"same": 0.8, "different": 0.2}, "same", ER_LABELS), 0.08)

    def test_wrong_vocab_nonfinite_bounds_and_normalization_rejected(self):
        cases = [
            {}, {"true": 0.7, "false": 0.3}, {"same": 1.0},
            {"same": 0.7, "different": 0.7},
            {"same": float("nan"), "different": 0.0},
            {"same": float("inf"), "different": 0.0},
            {"same": -0.1, "different": 1.1},
            {"same": True, "different": 0.0},
            {"same": "0.8", "different": 0.2},
        ]
        for distribution in cases:
            with self.subTest(distribution=distribution), self.assertRaises(ValueError):
                validate_distribution(distribution, ER_LABELS)

    def test_zero_gold_probability_has_explicit_clipped_log_loss(self):
        row = er_result(distribution={"same": 0.0, "different": 1.0})
        summary = summarize_results([row], ER_LABELS)
        self.assertEqual(summary["n_log_loss_clipped"], 1)
        self.assertAlmostEqual(summary["log_loss"], -math.log(1e-15))
        self.assertEqual(summary["brier_score"], 2.0)


class AccountingTests(unittest.TestCase):
    def test_uncertain_gold_never_gets_automatic_credit(self):
        uncertain = er_result("uncertain", {"same": 0.8, "different": 0.2})
        uncertain_error = er_result("uncertain", {}, "offline")
        for row in (uncertain, uncertain_error):
            self.assertFalse(row.correct)
            self.assertFalse(row.semantic_eligible)
            self.assertIsNone(row.brier_score())
        summary = summarize_results([uncertain, uncertain_error], ER_LABELS)
        self.assertEqual(summary["n_excluded_gold"], 2)
        self.assertEqual(summary["n_semantic_examples"], 0)
        self.assertEqual(summary["service_success_rate"], 0.5)
        self.assertIsNone(summary["accuracy"])
        self.assertIsNone(summary["brier_score"])

    def test_operational_and_conditional_denominators_are_distinct(self):
        correct = er_result("same", {"same": 0.8, "different": 0.2})
        incorrect = er_result("different", {"same": 0.8, "different": 0.2})
        failed = er_result("different", {}, "offline")
        excluded = er_result("uncertain", {"same": 0.8, "different": 0.2})
        summary = summarize_results([correct, incorrect, failed, excluded], ER_LABELS)
        self.assertAlmostEqual(summary["operational_accuracy"], 1 / 3)
        self.assertEqual(summary["conditional_accuracy"], 0.5)
        self.assertAlmostEqual(summary["semantic_coverage"], 2 / 3)
        self.assertEqual(summary["service_success_rate"], 0.75)
        self.assertEqual(summary["probability_score_denominator"], 2)
        self.assertAlmostEqual(summary["brier_score"], 0.68)
        self.assertEqual(summary["balanced_accuracy"], 0.5)
        self.assertAlmostEqual(summary["macro_f1"], 1 / 3)
        self.assertEqual(summary["confusion"]["different"]["ERROR"], 1)
        self.assertEqual(summary["total_tokens"], 28)
        self.assertEqual(summary["token_usage_denominator"], 4)

    def test_invalid_backend_output_is_failure_not_crash(self):
        for distribution in ({}, None, {"true": 0.8, "false": 0.2}, {"same": float("nan"), "different": 0.0}):
            with self.subTest(distribution=distribution):
                row = er_result(distribution=distribution)
                self.assertFalse(row.service_success)
                self.assertEqual(row.predicted_label, "ERROR")
                self.assertIsNotNone(row.validation_error)
                self.assertIsNone(row.brier_score())
                json.dumps(row.to_dict(), allow_nan=False)

    def test_error_and_exception_evidence_is_retained(self):
        error = er_result(distribution={}, error="API unavailable")
        self.assertEqual(error.raw_error, "API unavailable")
        self.assertEqual(error.execution_mode, "mock")
        self.assertEqual(error.backend_version, "test-revision")
        self.assertTrue(error.metadata["test_fixture"])
        raised = er_result(raises=True)
        self.assertIn("simulated outage", raised.raw_error)
        self.assertEqual(raised.execution_mode, "unavailable")
        self.assertIsNotNone(raised.wall_latency_ms)
        self.assertIsNone(summarize_results([raised], ER_LABELS)["total_tokens"])

    def test_confidence_and_latency_do_not_trust_backend_claims(self):
        row = er_result(distribution={"same": 0.8, "different": 0.2})
        self.assertEqual(row.reported_confidence, 0.99)
        self.assertEqual(row.confidence, 0.8)
        self.assertEqual(row.latency_ms, 9999.0)
        summary = summarize_results([row], ER_LABELS)
        self.assertEqual(summary["mean_latency_ms"], row.wall_latency_ms)
        self.assertEqual(summary["execution_modes"], {"mock": 1})


class RequestTests(unittest.TestCase):
    def test_relation_preserves_complete_claim_evidence_and_three_way_labels(self):
        passage = "Evidence beyond the former cutoff: " + "x" * 300 + " decisive contradiction."
        example = SciFactExample("claim-1", "The actual claim.", [passage], "REFUTES")
        backend = StubBackend({"SUPPORTS": 0.1, "REFUTES": 0.8, "NOT_ENOUGH_INFO": 0.1})
        report = SciFactBenchmark([example]).run([backend])
        request = backend.requests[0]
        self.assertEqual(request.task, "relation_support")
        self.assertEqual(request.question, example.claim_text)
        self.assertEqual(request.payload["evidence"], [passage])
        self.assertEqual(json.loads(request.state), request.payload)
        self.assertEqual(tuple(request.labels), RELATION_LABELS)
        self.assertEqual(request.primitive, PrimitiveType.CHOICE)
        self.assertTrue(report.results[0].correct)

    def test_er_retains_context_and_canonical_task(self):
        example = ERExample("pair-1", "A. Smith", "Alice Smith", "same", context="Same paper and affiliation.")
        backend = StubBackend({"same": 0.8, "different": 0.2})
        EntityResolutionBenchmark([example]).run([backend])
        request = backend.requests[0]
        self.assertEqual(request.payload["context"], example.context)
        self.assertEqual(request.payload["mention_1"], example.mention_1)
        self.assertEqual(request.task, "entity_resolution")
        self.assertEqual(tuple(request.labels), ER_LABELS)

    def test_dry_run_never_invokes_backend_and_marks_mock(self):
        example = SciFactExample("claim-1", "Claim", ["Evidence"], "NOT_ENOUGH_INFO")
        backend = StubBackend(raises=True)
        report = SciFactBenchmark([example]).run([backend], dry_run=True)
        self.assertEqual(backend.requests, [])
        self.assertEqual(report.results[0].execution_mode, "mock")
        self.assertTrue(report.results[0].metadata["dry_run"])


class ReproducibilityTests(unittest.TestCase):
    def test_diagnostic_baseline_is_seeded_canonical_and_explicitly_mock(self):
        request = DecisionRequest("request", PrimitiveType.CHOICE, "Claim", "Evidence",
                                  labels=list(RELATION_LABELS), task="relation_support")
        left = DiagnosticBackend(seed=71)
        right = DiagnosticBackend(seed=71)
        for _ in range(3):
            a, b = left.decide(request), right.decide(request)
            self.assertEqual(a.distribution, b.distribution)
            self.assertEqual(a.execution_mode, "mock")
            validate_distribution(a.distribution, RELATION_LABELS)

    def test_wrapper_dry_run_writes_new_artifact_without_model_initialization(self):
        from pgc.experiments.benchmark_relation_support_50 import run_relation_support_benchmark
        example = SciFactExample("claim-1", "Claim", ["Evidence"], "NOT_ENOUGH_INFO")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dry-run.json"
            report, summaries = run_relation_support_benchmark(
                examples=[example], dry_run=True, output_path=path)
            self.assertTrue(path.exists())
            self.assertEqual(len(report.results), 2)
            self.assertTrue(all(row.execution_mode == "mock" for row in report.results))
            self.assertTrue(all(row.metadata["dry_run"] for row in report.results))
            self.assertEqual({summary["n_service_success"] for summary in summaries.values()}, {1})

    def test_group_split_is_reproducible_and_has_no_group_overlap(self):
        groups = ["a", "b", "a", "c", "d", "b", "e"]
        fit, calibration = group_split(groups, seed=13, calibration_fraction=0.4)
        self.assertEqual((fit, calibration), group_split(groups, seed=13, calibration_fraction=0.4))
        self.assertEqual(set(fit) | set(calibration), set(range(len(groups))))
        self.assertFalse({groups[i] for i in fit} & {groups[i] for i in calibration})
        with self.assertRaises(ValueError):
            group_split(["a", "a"])

    def test_artifact_contains_provenance_and_never_overwrites(self):
        row = er_result(distribution={"same": 0.8, "different": 0.2})
        examples = [ERExample("pair-1", "A", "B", "same")]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact.json"
            with patch("pgc.evaluation.subprocess.run", side_effect=OSError("git unavailable")):
                save_benchmark_artifact("test", examples, [row], {"test-backend": summarize_results([row])},
                                        output_path=path, seed=42, manifest={"split": "heldout"})
                saved = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(saved["seed"], 42)
                self.assertEqual(len(saved["manifest"]["dataset_sha256"]), 64)
                self.assertEqual(saved["manifest"]["supplied"]["split"], "heldout")
                self.assertEqual(saved["raw_results"][0]["execution_mode"], "mock")
                self.assertIn("request_data", saved["raw_results"][0])
                original = path.read_bytes()
                with self.assertRaises(FileExistsError):
                    save_benchmark_artifact("test", examples, [row], {}, output_path=path)
                self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
