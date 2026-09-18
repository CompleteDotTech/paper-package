"""Synthetic metadata tests; no scientific annotations or model calls."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from graph_synthesis.corpus.plan import (SPLITS, assign_split, build_plan, canonical,
                                         digest, strict_json, write_receipt)

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = ROOT / "graph_synthesis/corpus/protocol.example.json"


def fixtures():
    config = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    config.update(stages=[30, 60, 120], max_decisions=1000000,
                  usd_per_decision="0.001", fixed_overhead_usd="10.00",
                  max_estimated_usd="1000.00")
    rows = [{"paper_id": f"synthetic-paper-{i:04d}", "work_id": f"synthetic-work-{i:04d}",
             "split_group": f"synthetic-study-{i // 2:04d}",
             "domain": config["domains"][i % 3], "year": 2025,
             "source": "synthetic_fixture_not_a_publication", "license": "synthetic-test-only",
             "rights_reviewed": True, "full_text": True,
             "text_sha256": hashlib.sha256(f"synthetic text {i}".encode()).hexdigest(),
             "estimated_candidates": 5} for i in range(120)]
    return rows, config


class CorpusPlanningTests(unittest.TestCase):
    def setUp(self):
        self.rows, self.config = fixtures()

    def test_deterministic_under_reordering(self):
        self.assertEqual(build_plan(self.rows, self.config), build_plan(list(reversed(self.rows)), self.config))

    def test_nested_stages_and_additional_counts(self):
        previous = set()
        for stage in build_plan(self.rows, self.config)["stages"]:
            ids = {row["paper_id"] for row in stage["assignments"]}
            self.assertTrue(previous <= ids)
            self.assertEqual(stage["additional_papers"], len(ids - previous))
            previous = ids

    def test_entire_groups_selected_across_domains(self):
        plan = build_plan(self.rows, self.config)
        for stage in plan["stages"]:
            ids = {row["paper_id"] for row in stage["assignments"]}
            groups = {row["split_group"] for row in stage["assignments"]}
            self.assertEqual(ids, {row["paper_id"] for row in self.rows if row["split_group"] in groups})

    def test_group_has_one_split_across_all_stages(self):
        seen = {}
        for stage in build_plan(self.rows, self.config)["stages"]:
            for row in stage["assignments"]:
                self.assertEqual(seen.setdefault(row["split_group"], row["split"]), row["split"])

    def test_split_does_not_depend_on_corpus_order_or_size(self):
        for group in ("a", "b", "c"):
            self.assertIn(assign_split(group, self.config), SPLITS)
            changed = deepcopy(self.config)
            changed["stages"] = [1]
            self.assertEqual(assign_split(group, changed), assign_split(group, self.config))

    def test_seed_changes_assignment_or_sample(self):
        changed = deepcopy(self.config)
        changed["seed"] += 1
        self.assertNotEqual(build_plan(self.rows, self.config)["stages"], build_plan(self.rows, changed)["stages"])

    def test_shortage_is_not_silently_replaced_by_other_domains(self):
        subset = [row for row in self.rows if row["domain"] != self.config["domains"][0]]
        stage = build_plan(subset, self.config)["stages"][0]
        self.assertIn("insufficient_papers_in_stratum", stage["planning_blockers"])
        self.assertEqual(stage["stratum_shortfalls"][self.config["domains"][0]], 10)

    def test_cost_includes_arms_repeats_attempts_overhead(self):
        stage = build_plan(self.rows, self.config)["stages"][-1]
        self.assertEqual(stage["estimated_attempted_decisions"], 120 * 5 * 6 * 3 * 2)
        self.assertEqual(stage["estimated_usd"], "31.600")

    def test_unpriced_plan_blocked(self):
        for field in ("usd_per_decision", "fixed_overhead_usd"):
            with self.subTest(field=field):
                config = dict(self.config, **{field: None})
                stage = build_plan(self.rows, config)["stages"][0]
                self.assertIsNone(stage["estimated_usd"])
                self.assertIn("unpriced_decisions_or_overhead", stage["planning_blockers"])

    def test_caps_are_checked_after_group_expansion(self):
        config = dict(self.config, max_decisions=1, max_estimated_usd="0")
        stage = build_plan(self.rows, config)["stages"][0]
        self.assertIn("decision_cap_exceeded", stage["planning_blockers"])
        self.assertIn("estimated_cost_cap_exceeded", stage["planning_blockers"])

    def test_never_authorizes_execution_even_under_caps(self):
        plan = build_plan(self.rows, self.config)
        self.assertTrue(plan["stages"][-1]["within_planning_caps"])
        self.assertTrue(all(not s["execution_authorized"] for s in plan["stages"]))

    def test_empty_splits_blocked(self):
        for row in self.rows:
            row["split_group"] = "one-dependency-component"
        stage = build_plan(self.rows, self.config)["stages"][0]
        self.assertIn("empty_development_calibration_or_test_split", stage["planning_blockers"])

    def test_zero_candidate_plan_blocked(self):
        for row in self.rows:
            row["estimated_candidates"] = 0
        self.assertIn("no_estimated_candidates", build_plan(self.rows, self.config)["stages"][0]["planning_blockers"])

    def test_duplicate_identifiers_and_text_rejected(self):
        for field in ("paper_id", "work_id", "text_sha256"):
            with self.subTest(field=field):
                rows = deepcopy(self.rows)
                rows[1][field] = rows[0][field]
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    build_plan(rows, self.config)

    def test_labels_or_unknown_fields_rejected(self):
        self.rows[0]["gold_label"] = "supports"
        with self.assertRaisesRegex(ValueError, "no labels"):
            build_plan(self.rows, self.config)

    def test_missing_fields_rejected(self):
        del self.rows[0]["license"]
        with self.assertRaises(ValueError):
            build_plan(self.rows, self.config)

    def test_reviewed_rights_and_full_text_required(self):
        for field in ("rights_reviewed", "full_text"):
            for value in (False, "true", 1, None):
                with self.subTest(field=field, value=value):
                    rows = deepcopy(self.rows)
                    rows[0][field] = value
                    with self.assertRaises(ValueError):
                        build_plan(rows, self.config)

    def test_sha_format(self):
        for value in ("123", "G" * 64, "A" * 64, None):
            with self.subTest(value=value):
                rows = deepcopy(self.rows)
                rows[0]["text_sha256"] = value
                with self.assertRaises(ValueError):
                    build_plan(rows, self.config)

    def test_invalid_counts(self):
        for value in (-1, 1.5, True, "2"):
            with self.subTest(value=value):
                rows = deepcopy(self.rows)
                rows[0]["estimated_candidates"] = value
                with self.assertRaises(ValueError):
                    build_plan(rows, self.config)

    def test_year_and_domain_validation(self):
        for field, value in (("year", 2027), ("year", True), ("domain", "undeclared"), ("source", " ")):
            with self.subTest(field=field):
                rows = deepcopy(self.rows)
                rows[0][field] = value
                with self.assertRaises(ValueError):
                    build_plan(rows, self.config)

    def test_config_unknown_fields(self):
        self.config["model_secret"] = "not-a-secret"
        with self.assertRaises(ValueError):
            build_plan(self.rows, self.config)

    def test_config_stages_and_names(self):
        for field, value in (("stages", []), ("stages", [2, 1]), ("stages", [1, 1]),
                             ("stages", [True]), ("arms", ["a", "a"]), ("domains", []),
                             ("status", "preregistered"), ("schema_version", True)):
            with self.subTest(field=field, value=value):
                config = dict(self.config, **{field: value})
                with self.assertRaises(ValueError):
                    build_plan(self.rows, config)

    def test_split_percent_validation(self):
        for value in ({"test": 100}, dict.fromkeys(SPLITS, 20),
                      {"development": True, "calibration": 39, "test": 60}):
            with self.subTest(value=value):
                config = dict(self.config, split_percent=value)
                with self.assertRaises(ValueError):
                    build_plan(self.rows, config)

    def test_money_validation(self):
        for value in ("NaN", "Infinity", "-1", True, {}, "invalid"):
            with self.subTest(value=value):
                config = dict(self.config, usd_per_decision=value)
                with self.assertRaises(ValueError):
                    build_plan(self.rows, config)

    def test_empty_corpus_rejected(self):
        with self.assertRaises(ValueError):
            build_plan([], self.config)

    def test_receipt_hash(self):
        result = build_plan(self.rows, self.config)
        expected = result.pop("plan_sha256")
        self.assertEqual(expected, digest(result))

    def test_manifest_hash_tracks_metadata_changes(self):
        original = build_plan(self.rows, self.config)
        self.rows[0]["estimated_candidates"] += 1
        self.assertNotEqual(original["corpus_sha256"], build_plan(self.rows, self.config)["corpus_sha256"])

    def test_strict_json_rejects_duplicate_keys_and_nonfinite_numbers(self):
        for text in ('{"a": 1, "a": 2}', '{"a": NaN}', '{"a": Infinity}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                strict_json(text)

    def test_receipt_idempotent_and_non_overwriting(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "receipt.json"
            write_receipt(path, {"a": 1})
            write_receipt(path, {"a": 1})
            with self.assertRaisesRegex(ValueError, "overwrite"):
                write_receipt(path, {"a": 2})
            self.assertEqual(path.read_bytes(), canonical({"a": 1}) + b"\n")

    def test_network_disabled(self):
        with patch.object(socket, "socket", side_effect=AssertionError("network forbidden")):
            build_plan(self.rows, self.config)

    def test_cli_and_idempotent_replay(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            corpus = root / "corpus.jsonl"
            protocol = root / "protocol.json"
            output = root / "plan.json"
            corpus.write_text("\n".join(json.dumps(row) for row in self.rows), encoding="utf-8")
            protocol.write_text(json.dumps(self.config), encoding="utf-8")
            command = [sys.executable, "-B", "-m", "graph_synthesis.corpus.plan",
                       "--corpus", str(corpus), "--protocol", str(protocol), "--output", str(output)]
            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
            second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
            self.assertEqual(first.stdout, second.stdout)
            self.assertFalse(json.loads(first.stdout)["execution_authorized"])
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["eligible_unique_papers"], 120)

    def test_cli_rejects_invalid_input_without_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            corpus = root / "bad.jsonl"
            output = root / "plan.json"
            corpus.write_text('{"gold": true}\n', encoding="utf-8")
            run = subprocess.run([sys.executable, "-B", "-m", "graph_synthesis.corpus.plan",
                                  "--corpus", str(corpus), "--protocol", str(PROTOCOL),
                                  "--output", str(output)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
