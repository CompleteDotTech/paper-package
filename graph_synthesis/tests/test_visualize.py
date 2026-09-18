"""Conservation, lineage, boundary, and frozen-observation figure tests."""
from copy import deepcopy
import gzip
import json
import math
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from graph_synthesis.visualize import (INPUTS, FIGURES, collect, dispositions,
    encoded, load_reference, reliability, write_tables)

ROOT = Path(__file__).resolve().parents[2]


class FigureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.object(socket.socket, "connect", side_effect=AssertionError("Figures must be offline")):
            cls.data = collect(ROOT)
        cls.fusion = load_reference(ROOT, list(INPUTS)[1])

    def test_all_rows_partition_once(self):
        for row in self.data["arms"]:
            keys = ("correct_edge", "unsupported_edge", "wrong_polarity", "no_information", "abstain", "error")
            self.assertEqual(sum(row[x] for x in keys), 339)
            self.assertEqual(row["correct_edge"] + row["unsupported_edge"] + row["wrong_polarity"], row["accepted"])

    def test_distinct_operational_failure_and_abstention(self):
        row = next(x for x in self.data["arms"] if x["arm"] == "agreement_gate")
        self.assertEqual((row["abstain"], row["error"], row["no_information"]), (33, 3, 113))

    def test_wrong_polarity_and_unsupported_are_separate(self):
        self.assertEqual([(x["unsupported_edge"], x["wrong_polarity"]) for x in self.data["arms"]],
                         [(27, 10), (13, 7), (19, 8), (13, 6), (21, 14)])

    def test_partition_rejects_inconsistent_count(self):
        op = deepcopy(self.fusion["arms"]["baseline_choice"]["operational"])
        op["confusion"]["SUPPORTS"]["SUPPORTS"] += 1
        with self.assertRaises(ValueError):
            dispositions(op)

    def test_reference_tampering_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            relative = next(iter(INPUTS))
            (root / relative).parent.mkdir(parents=True)
            (root / relative).write_bytes(gzip.compress(b'{}', mtime=0))
            with self.assertRaises(ValueError):
                load_reference(root, relative)

    def test_reliability_includes_one_and_omits_empty_bins(self):
        rows = [{"label": "SUPPORTS", "gold": "SUPPORTS", "score": 1.0},
                {"label": "REFUTES", "gold": "SUPPORTS", "score": .95},
                {"label": "ERROR", "gold": "SUPPORTS", "score": 0.0},
                {"label": "NOT_ENOUGH_INFO", "gold": "SUPPORTS", "score": 1.0}]
        result = reliability(rows)
        self.assertEqual(len(result), 1)
        self.assertEqual((result[0]["bin"], result[0]["n"], result[0]["accuracy"]), (9, 2, .5))
        self.assertAlmostEqual(result[0]["mean_confidence"], .975)

    def test_reliability_invalid_scores_rejected(self):
        for value in (-.1, 1.1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                reliability([{"label": "SUPPORTS", "gold": "SUPPORTS", "score": value}])

    def test_reliability_counts_match_archived_edges(self):
        self.assertEqual([sum(b["n"] for b in a["bins"]) for a in self.data["reliability"]], [224, 192])
        self.assertEqual([sum(b["correct"] for b in a["bins"]) for a in self.data["reliability"]], [187, 172])

    def test_matched_null_findings_not_rewritten(self):
        gate = next(x for x in self.data["matched"] if x["name"] == "Agreement gate - Few-shot contract")
        self.assertEqual((gate["k"], gate["left_correct"], gate["right_correct"], gate["delta"]), (190, 171, 171, 0))
        for row in self.data["matched"]:
            self.assertLessEqual(row["interval"][0], 0)
            self.assertGreaterEqual(row["interval"][1], 0)

    def test_topology_retains_isolates_and_schema_denominator(self):
        generic, selected = self.data["topology"][:2]
        self.assertEqual((generic["nodes"], generic["isolates"], selected["isolates"]), (583, 180, 241))
        self.assertEqual(generic["schema_eligible_pairs"], 283*300)
        self.assertAlmostEqual(generic["schema_pair_density"], 224/(283*300))

    def test_withdrawal_is_conservative(self):
        for row in self.data["withdrawals"]:
            self.assertEqual(row["active_after"] + row["retracted"], row["initial"])
            self.assertEqual(row["initial"], row["history_preserved"])
            self.assertTrue(row["reopen_equal"])

    def test_fusion_usage_is_not_free_inference(self):
        for row in self.data["arms"][2:]:
            self.assertEqual((row["recorded_calls"], row["recorded_input_tokens"]), (678, 1471953))
            self.assertAlmostEqual(row["input_tokens_per_correct_edge"], 1471953/row["correct"])

    def test_neighborhood_is_real_and_candidate_selected(self):
        hood = self.data["neighborhood"]
        self.assertEqual(hood["claim_id"], "133")
        self.assertEqual(len(hood["candidates"]), 5)
        self.assertEqual(sum(x["generic"] == "SUPPORTS" for x in hood["candidates"]), 1)
        self.assertEqual(len({x["document_id"] for x in hood["candidates"]}), 5)

    def test_canonical_tables_and_committed_data(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            write_tables(self.data, output)
            self.assertEqual((output / 'data.json').read_bytes(), encoded(self.data))
            for path in output.iterdir():
                self.assertEqual(path.read_bytes(), (ROOT / 'graph_synthesis/figures' / path.name).read_bytes())

    def test_svg_files_are_static_valid_and_accessible_text(self):
        for name in FIGURES:
            raw = (ROOT / 'graph_synthesis/figures' / (name + '.svg')).read_text(encoding='utf-8')
            tree = ET.fromstring(raw)
            self.assertTrue(tree.tag.endswith('svg'))
            self.assertIn('<text', raw)
            self.assertNotIn('<script', raw.lower())
            self.assertNotIn('<foreignObject', raw)


if __name__ == '__main__':
    unittest.main()
