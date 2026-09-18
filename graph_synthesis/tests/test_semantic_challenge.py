"""No provider is called: all prediction fixtures are explicitly synthetic."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from graph_synthesis.core import digest
from graph_synthesis.semantic_challenge import (LABELS, evaluate, load_cases,
                                               public_inputs, request_payload)


def prediction(case, status="ok"):
    p = {"id": case["id"], "input_hash": digest(request_payload(case)), "status": status,
         "model": "synthetic-test-only", "request_hash": "a" * 64, "response_hash": "b" * 64}
    if status == "ok":
        p.update(label=case["gold"], probabilities={k: float(k == case["gold"]) for k in LABELS})
    if status == "error":
        p["error"] = "synthetic timeout"
    return p


class ChallengeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_cases()

    def test_48_distinct_cases_12_families(self):
        self.assertEqual(len(self.cases), 48)
        self.assertEqual(len({c["family"] for c in self.cases}), 12)
        self.assertEqual(len({digest(c["state"]) for c in self.cases}), 48)

    def test_gold_free_exports(self):
        for p in public_inputs(self.cases):
            self.assertEqual(set(p), {"id", "input_hash", "state", "labels", "question"})
            self.assertEqual(set(p["state"]), {"claim", "evidence"})
            self.assertNotIn("gold", p)
            self.assertNotIn("rationale", p)
            self.assertNotIn("family", p)

    def test_export_is_detached_from_labels(self):
        cases = deepcopy(self.cases)
        before = public_inputs(cases)
        for c in cases:
            c["gold"] = "REFUTES"
            c["rationale"] = "different"
        self.assertEqual(before, public_inputs(cases))

    def test_export_does_not_alias_state(self):
        cases = deepcopy(self.cases)
        public_inputs(cases)[0]["state"]["claim"] = "changed"
        self.assertEqual(cases, self.cases)

    def test_input_hash_includes_instruction_and_allowed_labels(self):
        p = public_inputs(self.cases)[0]
        raw = {k: p[k] for k in ("state", "question", "labels")}
        self.assertEqual(p["input_hash"], digest(raw))
        raw["question"] += " changed"
        self.assertNotEqual(p["input_hash"], digest(raw))

    def test_empty_journal_counts_missing_not_perfect(self):
        r = evaluate(self.cases, [])
        self.assertEqual(r["overall"]["statuses"], {"MISSING": 48})
        self.assertEqual(r["overall"]["accuracy_all_cases"], 0)
        self.assertIsNone(r["overall"]["edge_precision"])
        self.assertFalse(r["fresh_execution_verified"])

    def test_oracle_fixture_is_only_evaluator_positive_control(self):
        r = evaluate(self.cases, [prediction(c) for c in self.cases])
        self.assertEqual(r["overall"]["correct"], 48)
        self.assertEqual(r["paired_cases_all_correct"], 24)
        self.assertFalse(r["fresh_execution_verified"])
        self.assertEqual(r["model"], "synthetic-test-only")

    def test_errors_and_abstentions_distinct(self):
        r = evaluate(self.cases, [prediction(self.cases[0], "error"), prediction(self.cases[1], "abstain")])
        self.assertEqual(r["overall"]["statuses"], {"ABSTAIN": 1, "ERROR": 1, "MISSING": 46})

    def test_partial_journal_denominator_not_shrunk(self):
        r = evaluate(self.cases, [prediction(self.cases[0])])
        self.assertEqual(r["overall"]["accuracy_all_cases"], 1/48)

    def test_duplicate_predictions_rejected(self):
        p = prediction(self.cases[0])
        with self.assertRaises(ValueError):
            evaluate(self.cases, [p, p])

    def test_unknown_predictions_rejected(self):
        p = prediction(self.cases[0]); p["id"] = "unknown"
        with self.assertRaises(ValueError):
            evaluate(self.cases, [p])

    def test_changed_input_cannot_reuse_predictions(self):
        cases = deepcopy(self.cases)
        p = prediction(cases[0]); cases[0]["state"]["evidence"].append("new information")
        with self.assertRaises(ValueError):
            evaluate(cases, [p])

    def test_nonfinite_distribution_rejected(self):
        p = prediction(self.cases[0]); p["probabilities"]["SUPPORTS"] = float("nan")
        with self.assertRaises(ValueError):
            evaluate(self.cases, [p])

    def test_unrecognized_probability_label_rejected(self):
        p = prediction(self.cases[0]); p["probabilities"]["other"] = 0
        with self.assertRaises(ValueError):
            evaluate(self.cases, [p])

    def test_nonmaximal_label_rejected(self):
        p = prediction(self.cases[0]); p["label"] = "REFUTES"
        with self.assertRaises(ValueError):
            evaluate(self.cases, [p])

    def test_error_cannot_invent_probabilities(self):
        p = prediction(self.cases[0]); p["status"] = "error"
        with self.assertRaises(ValueError):
            evaluate(self.cases, [p])

    def test_empty_provenance_rejected(self):
        p = prediction(self.cases[0]); p["request_hash"] = ""
        with self.assertRaises(ValueError):
            evaluate(self.cases, [p])

    def test_nonhash_provenance_rejected(self):
        p = prediction(self.cases[0]); p["response_hash"] = "not-a-hash"
        with self.assertRaises(ValueError):
            evaluate(self.cases, [p])

    def test_mixed_model_arms_rejected(self):
        a, b = prediction(self.cases[0]), prediction(self.cases[1])
        b["model"] = "another-arm"
        with self.assertRaises(ValueError):
            evaluate(self.cases, [a, b])

    def test_journal_hash_is_row_order_independent(self):
        predictions = [prediction(c) for c in self.cases[:4]]
        self.assertEqual(evaluate(self.cases, predictions)["prediction_hash"],
                         evaluate(self.cases, predictions[::-1])["prediction_hash"])

    def test_challenge_duplicate_ids_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "cases.json"
            path.write_text(json.dumps([self.cases[0], self.cases[0]]))
            with self.assertRaises(ValueError):
                load_cases(path)

    def test_challenge_state_cannot_contain_gold(self):
        cases = deepcopy(self.cases)
        cases[0]["state"]["gold"] = cases[0]["gold"]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "cases.json"
            path.write_text(json.dumps(cases))
            with self.assertRaises(ValueError):
                load_cases(path)


if __name__ == "__main__":
    unittest.main()
