"""Offline regression tests. Scripted responses are not Jev performance evidence."""
from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
import unittest
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import patch

from graph_synthesis.dspy_jev_optimizer.core import (
    BudgetExhausted, Cache, Evaluator, Example, JevConfig, digest, disjoint,
    evaluate_frozen, feedback, fingerprints, frozen_run, load_data, metrics,
    optimize, parse_json, read_json, validate_answer, write_json,
)
from graph_synthesis.dspy_jev_optimizer.optimize import FixtureBackend, FixtureProposer, NoProposer
from graph_synthesis.dspy_jev_optimizer.providers import TypeSafeBackend

CONFIG = JevConfig.from_dict({"task": "Relation", "instructions": "fixture-baseline",
                             "criteria": {"supports": "Supported", "refutes": "Contradicted", "insufficient": "Unknown"}})


def rows(split):
    return [Example(f"{split}-{i}", {"split": split, "fixture_index": i}, label)
            for i, label in enumerate(CONFIG.criteria)]


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.run = self.root / "run"
        self.cache = Cache(self.root / "cache.sqlite3")
        self.backend = FixtureBackend()
        self.ev = Evaluator(self.backend, self.cache, self.run, 100)

    def tearDown(self):
        self.cache.close()
        self.tmp.cleanup()

    def search(self, **kwargs):
        return optimize(CONFIG, rows("train"), rows("val"), FixtureProposer(), self.ev, self.run, **kwargs)

    def test_optimizer_accepts_improvement_and_skips_duplicate(self):
        result = self.search(iterations=3)
        self.assertEqual(result["champion"]["instructions"], "fixture-perfect")
        self.assertEqual([r["status"] for r in read_json(self.run/"ledger.json")],
                         ["baseline", "accepted", "duplicate_candidate", "duplicate_candidate"])
        self.assertEqual(self.ev.calls, 12)
        self.assertGreater(self.ev.cache_hits, 0)

    def test_zero_iterations_still_saves_baseline_and_freeze(self):
        optimize(CONFIG, rows("train"), rows("val"), NoProposer(), self.ev, self.run, iterations=0)
        self.assertEqual(read_json(self.run/"optimized-config.json"), asdict(CONFIG))
        self.assertTrue((self.run/"freeze.json").is_file())
        self.assertEqual(self.ev.calls, 3)

    def test_failure_feedback_includes_training_state_not_validation(self):
        class Spy(FixtureProposer):
            observed = None
            def propose(inner, cfg, sample, iteration, history):
                inner.observed = sample
                return super().propose(cfg, sample, iteration, history)
        spy = Spy()
        optimize(CONFIG, rows("train"), rows("val"), spy, self.ev, self.run, iterations=1)
        self.assertTrue(all(x["state"]["split"] == "train" for x in spy.observed))
        self.assertIn("gold", spy.observed[0])

    def test_bounded_feedback_marks_truncation(self):
        data = [Example("x", "x"*7000, "supports")]
        pred = [{"id": "x", "gold": "supports", "choice": "supports", "probabilities": {"supports": .9}}]
        self.assertTrue(feedback(data, pred, 1)[0]["state_truncated"])

    def test_ties_keep_incumbent(self):
        class Tied(FixtureProposer):
            def propose(self, cfg, *args):
                return {**asdict(cfg), "instructions": "new-but-equivalent"}
        result = optimize(CONFIG, rows("train"), rows("val"), Tied(), self.ev, self.run, iterations=1)
        self.assertEqual(result["champion"], asdict(CONFIG))
        self.assertEqual(read_json(self.run/"ledger.json")[-1]["status"], "rejected")

    def test_invalid_candidate_is_recorded_without_evaluation(self):
        class Invalid(FixtureProposer):
            def propose(self, *args):
                return {**asdict(CONFIG), "criteria": {"new": "label", "other": "label"}}
        optimize(CONFIG, rows("train"), rows("val"), Invalid(), self.ev, self.run, iterations=1)
        self.assertEqual(self.ev.calls, 6)
        self.assertEqual(read_json(self.run/"ledger.json")[-1]["status"], "invalid_candidate")

    def test_proposer_failure_is_fatal_and_not_a_rejected_candidate(self):
        class Broken(FixtureProposer):
            def propose(self, *args):
                raise RuntimeError("secret provider payload")
        with self.assertRaises(RuntimeError):
            optimize(CONFIG, rows("train"), rows("val"), Broken(), self.ev, self.run, iterations=1)
        self.assertFalse((self.run/"freeze.json").exists())
        self.assertNotIn("secret", (self.run/"failure.json").read_text())

    def test_budget_stops_search_without_partial_candidate_promotion(self):
        self.ev.max_calls = 7
        result = self.search(iterations=3)
        self.assertEqual(result["stop_reason"], "jev_call_budget")
        self.assertEqual(result["champion"], asdict(CONFIG))
        self.assertEqual(self.ev.calls, 7)
        self.assertEqual(read_json(self.run/"ledger.json")[-1]["status"], "budget_exhausted")

    def test_insufficient_baseline_budget_fails_without_freeze(self):
        self.ev.max_calls = 1
        with self.assertRaises(BudgetExhausted):
            self.search(iterations=0)
        self.assertFalse((self.run/"freeze.json").exists())

    def test_patience_counts_non_improvements(self):
        result = self.search(iterations=10, patience=1)
        self.assertEqual(result["stop_reason"], "patience")
        self.assertEqual(len(read_json(self.run/"ledger.json")), 3)

    def test_existing_output_not_overwritten(self):
        self.run.mkdir()
        with self.assertRaises(FileExistsError):
            self.search()
        self.assertEqual(self.ev.calls, 0)

    def test_invalid_search_options_fail_before_calls(self):
        for kwargs in ({"iterations": -1}, {"failure_sample": 0}, {"patience": -1}, {"selection_metric": "test_accuracy"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.search(**kwargs)
        self.assertEqual(self.ev.calls, 0)

    def test_cache_is_persistent_and_model_namespaced(self):
        self.ev.evaluate(CONFIG, rows("train"), "train")
        second = Evaluator(self.backend, self.cache, self.root/"second", 100)
        second.evaluate(CONFIG, rows("train"), "train")
        self.assertEqual(second.calls, 0)
        self.assertEqual(second.cache_hits, 3)
        other = FixtureBackend()
        other.identity = {**other.identity, "sdk_version": "changed"}
        third = Evaluator(other, self.cache, self.root/"third", 100)
        third.evaluate(CONFIG, rows("train"), "train")
        self.assertEqual(third.calls, 3)

    def test_cache_detects_corruption(self):
        self.ev.evaluate(CONFIG, rows("train"), "train")
        self.cache.db.execute("UPDATE responses SET digest='corrupt'")
        self.cache.db.commit()
        with self.assertRaises(ValueError):
            self.ev.evaluate(CONFIG, rows("train"), "train")

    def test_model_drift_is_rejected_and_not_cached(self):
        class Drift(FixtureBackend):
            def predict(self, cfg, state):
                return {**super().predict(cfg, state), "model": "unexpected-model"}
        ev = Evaluator(Drift(), self.cache, self.run, 100)
        with self.assertRaises(ValueError):
            ev.evaluate(CONFIG, rows("train"), "train")
        self.assertEqual(self.cache.db.execute("SELECT COUNT(*) FROM responses").fetchone()[0], 0)

    def test_probabilities_fail_closed(self):
        for probs in ({"supports": .9}, {"supports": 1, "refutes": 1, "insufficient": 0},
                      {"supports": float("nan"), "refutes": 0, "insufficient": 0},
                      {"supports": True, "refutes": 0, "insufficient": 0},
                      {"supports": -.1, "refutes": 1, "insufficient": .1}):
            with self.subTest(probs=probs), self.assertRaises(ValueError):
                validate_answer({"choice": "supports", "probabilities": probs}, CONFIG.criteria)

    def test_unknown_choice_rejected(self):
        answer = self.backend.predict(CONFIG, rows("train")[0].state)
        answer["choice"] = "unknown"
        with self.assertRaises(ValueError):
            validate_answer(answer, CONFIG.criteria)

    def test_metrics_perfect_and_log_loss(self):
        preds = [{"gold": k, "choice": k, "probabilities": {j: float(j == k) for j in CONFIG.criteria}} for k in CONFIG.criteria]
        result = metrics(preds, CONFIG.criteria)
        for field in ("accuracy", "macro_f1", "mcc", "composite"):
            self.assertAlmostEqual(result[field], 1)
        for field in ("brier", "log_loss", "ece"):
            self.assertEqual(result[field], 0)

    def test_ece_uses_selected_probability_not_vendor_confidence(self):
        result = metrics([{"gold": "supports", "choice": "supports", "confidence": 0,
                           "probabilities": {"supports": .7, "refutes": .2, "insufficient": .1}}], CONFIG.criteria)
        self.assertAlmostEqual(result["ece"], .3)
        self.assertAlmostEqual(result["log_loss"], -math.log(.7))
        self.assertAlmostEqual(result["brier"], .14)

    def test_json_rejects_duplicate_keys_and_nonfinite(self):
        for raw in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'):
            with self.assertRaises(ValueError):
                parse_json(raw)

    def test_loader_rejects_missing_id_unknown_label_and_empty(self):
        path = self.root/"data.jsonl"
        for value in ('', '{"state":"a","label":"supports"}', '{"id":"a","state":"a","label":"bad"}'):
            path.write_text(value)
            with self.assertRaises(ValueError):
                load_data(path, CONFIG.criteria)

    def test_duplicate_id_or_state_rejected(self):
        for data in ([rows("t")[0], replace(rows("t")[1], id="t-0")],
                     [rows("t")[0], replace(rows("t")[1], state=rows("t")[0].state)]):
            with self.assertRaises(ValueError):
                fingerprints(data)

    def test_train_validation_leakage_prevents_all_calls(self):
        with self.assertRaises(ValueError):
            optimize(CONFIG, rows("train"), rows("train"), FixtureProposer(), self.ev, self.run)
        self.assertEqual(self.ev.calls, 0)

    def test_source_groups_cannot_overlap(self):
        a = [replace(r, group_id="paper-A") for r in rows("train")]
        b = [replace(r, group_id="paper-A") for r in rows("val")]
        with self.assertRaises(ValueError):
            disjoint(fingerprints(a), fingerprints(b))

    def test_partial_group_ids_rejected(self):
        data = rows("train")
        data[0] = replace(data[0], group_id="paper-A")
        with self.assertRaises(ValueError):
            fingerprints(data)

    def test_candidate_preserves_label_order(self):
        cfg = JevConfig.from_dict({**asdict(CONFIG), "criteria": dict(reversed(list(CONFIG.criteria.items())))}, CONFIG)
        self.assertEqual(list(cfg.criteria), list(CONFIG.criteria))

    def test_test_not_loaded_until_frozen_evaluation(self):
        with patch("graph_synthesis.dspy_jev_optimizer.core.load_data", side_effect=AssertionError("no test reads during search")):
            self.search(iterations=1)
        test_path = self.root/"test.jsonl"
        test_path.write_text("".join(json.dumps(asdict(r))+"\n" for r in rows("test")))
        ev = Evaluator(self.backend, self.cache, self.run/"final", 100)
        result = evaluate_frozen(self.run, test_path, ev)
        self.assertEqual(result["champion"]["accuracy"], 1)
        self.assertGreater(result["accuracy_delta"], 0)
        with self.assertRaises(FileExistsError):
            evaluate_frozen(self.run, test_path, ev)

    def test_hidden_test_leakage_blocked_before_service_call(self):
        self.search(iterations=0)
        path = self.root/"test.jsonl"
        path.write_text("".join(json.dumps(asdict(r))+"\n" for r in rows("val")))
        ev = Evaluator(self.backend, self.cache, self.run/"final", 100)
        with self.assertRaises(ValueError):
            evaluate_frozen(self.run, path, ev)
        self.assertEqual(ev.calls, 0)

    def test_freeze_tamper_detected(self):
        self.search(iterations=0)
        protocol = read_json(self.run/"protocol.json")
        protocol["iterations"] = 100
        write_json(self.run/"protocol.json", protocol)
        with self.assertRaises(ValueError):
            frozen_run(self.run)

    def test_version_alias_rejected_before_sdk_import(self):
        for name in ("jev-latest", "jev-preview", "", "other"):
            with self.assertRaises(ValueError):
                TypeSafeBackend(name)

    def test_cli_both_entrypoints_and_no_test_flag_for_search(self):
        script = Path(__file__).resolve().parents[1]/"optimize.py"
        process = subprocess.run([sys.executable, "-B", str(script), "--help"], capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        bad = subprocess.run([sys.executable, "-B", str(script), "optimize", "--test", "x"], capture_output=True)
        self.assertEqual(bad.returncode, 2)


if __name__ == "__main__":
    unittest.main()
