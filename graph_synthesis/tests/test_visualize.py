"""Independent accounting/selection controls for the visual reanalysis."""
from copy import deepcopy
import json
from pathlib import Path
import socket
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from graph_synthesis.visualize import (ARMS, CAPTIONS, FUSION, GRAPH, ROOT, build_data,
    check_outputs, component_example, effect_vs_selected, load_gzip, reliability, risk_curve)


def row(id_, label, gold, score=.9, probability=None, error=None):
    return {"id": id_, "label": label, "gold": gold, "score": score,
            "decision": SimpleNamespace(error=error, probabilities={"same": score if probability is None else probability})}


class VisualMathTests(unittest.TestCase):
    def test_ties_are_never_split(self):
        rows = [row("a", "same", "same", 1), row("b", "same", "different", 1), row("c", "same", "same", .8)]
        curve = risk_curve(rows, {"same"})
        self.assertEqual([x["accepted"] for x in curve], [2, 3])
        self.assertEqual(curve[0]["risk"], .5)

    def test_coverage_retains_errors_and_no_edge(self):
        rows = [row("a", "SUPPORTS", "SUPPORTS"), row("b", "ERROR", "SUPPORTS"), row("c", "NOT_ENOUGH_INFO", "NOT_ENOUGH_INFO")]
        self.assertEqual(risk_curve(rows, {"SUPPORTS"})[0]["coverage"], 1/3)

    def test_empty_curve_does_not_claim_zero_risk(self):
        self.assertEqual(risk_curve([], {"same"}), [])
        self.assertEqual(risk_curve([row("a", "different", "different")], {"same"}), [])

    def test_polarity_error_is_wrong_edge(self):
        curve = risk_curve([row("a", "REFUTES", "SUPPORTS")], {"SUPPORTS", "REFUTES"})
        self.assertEqual(curve[0]["incorrect"], 1)

    def test_invalid_score_rejected(self):
        for value in (float("nan"), float("inf"), -.1, 1.1):
            with self.assertRaises(ValueError):
                risk_curve([row("a", "same", "same", value)], {"same"})

    def test_ranking_does_not_use_gold(self):
        a = [row("a", "same", "same", .9), row("b", "same", "different", .8)]
        b = deepcopy(a)
        for r in b: r["gold"] = "different"
        self.assertEqual([(r["threshold"], r["accepted"]) for r in risk_curve(a, {"same"})],
                         [(r["threshold"], r["accepted"]) for r in risk_curve(b, {"same"})])

    def test_reliability_includes_other_predictions(self):
        bins = reliability([row("a", "different", "same", probability=.2)], "same")
        self.assertEqual(bins[2]["observed_fraction"], 1)

    def test_probability_endpoints_and_boundaries(self):
        bins = reliability([row("a", "same", "same", probability=0), row("b", "same", "same", probability=.1), row("c", "same", "same", probability=1)], "same")
        self.assertEqual([bins[i]["n"] for i in (0, 1, 9)], [1, 1, 1])
        self.assertIsNone(bins[2]["observed_fraction"])

    def test_reliability_excludes_failed_response_only(self):
        bins = reliability([row("a", "ERROR", "same", error="failure"), row("b", "same", "same")], "same")
        self.assertEqual(sum(b["n"] for b in bins), 1)

    def test_invalid_reliability_probability(self):
        with self.assertRaises(ValueError):
            reliability([row("a", "same", "same", probability=float("nan"))], "same")

    def test_reversed_contrast_changes_interval_sign(self):
        saved = {"agreement_gate__vs__fewshot_contract": {"macro_f1_delta": .02, "macro_f1_bootstrap": {"interval": [-.01, .04], "draws": 2000}}}
        e = effect_vs_selected(saved, "agreement_gate")
        self.assertEqual(e["delta"], -.02); self.assertEqual(e["interval"], [-.04, .01])

    def test_component_selection_does_not_use_gold(self):
        left = [dict(row("a", "SUPPORTS", "SUPPORTS"), row={"document_id": "1", "claim_id": "1"}),
                dict(row("b", "SUPPORTS", "SUPPORTS"), row={"document_id": "2", "claim_id": "2"})]
        right = deepcopy(left); right[1]["label"] = "NOT_ENOUGH_INFO"
        first = component_example(left, right)
        for r in left: r["gold"] = "REFUTES"
        second = component_example(left, right)
        self.assertEqual(first["nodes"], second["nodes"])
        self.assertEqual(first["changed_decisions"], second["changed_decisions"])


class FrozenFigureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.object(socket, "create_connection", side_effect=AssertionError("network forbidden")):
            cls.data = build_data(ROOT)

    def test_no_new_inference(self):
        self.assertEqual(self.data["fresh_model_calls"], 0)

    def test_all_candidate_denominators_preserved(self):
        for arm in ARMS:
            op = self.data["fusion"]["arms"][arm]["operational"]
            self.assertEqual(op["n"], 339)
            self.assertEqual(op["edges"]["accepted"], op["edges"]["correct"] + op["edges"]["incorrect"])
            self.assertAlmostEqual(op["edges"]["recall"], op["edges"]["correct"] / 209)

    def test_topology_preserves_every_candidate_node(self):
        for task in self.data["tasks"].values():
            for arm in task["arms"].values():
                m = arm["graph"]["metrics"]
                self.assertEqual(sum(int(size)*n for size,n in m["weak_component_size_histogram"].items()), m["nodes"])

    def test_confusion_retains_every_row(self):
        for task in self.data["tasks"].values():
            for arm in task["arms"].values():
                self.assertEqual(sum(arm["confusion"].values()), arm["n"])

    def test_probability_denominator_matches_valid_rows(self):
        for task in self.data["tasks"].values():
            for arm in task["arms"].values():
                for bins in arm["reliability"].values():
                    self.assertEqual(sum(b["n"] for b in bins), arm["n"]-arm["errors"])

    def test_highest_score_is_not_assumed_perfect(self):
        curve = self.data["tasks"]["relation_support"]["arms"]["fewshot_contract"]["risk_curve"]
        self.assertEqual((curve[0]["threshold"], curve[0]["accepted"], curve[0]["incorrect"]), (1.0, 73, 5))

    def test_chart_inventory_and_data_are_current(self):
        report = check_outputs(ROOT, ROOT / "graph_synthesis/figures")
        self.assertEqual(report["figures_verified"], len(CAPTIONS))

    def test_every_svg_is_parseable_without_scripts(self):
        for name in CAPTIONS:
            root = ET.parse(ROOT / f"graph_synthesis/figures/{name}.svg").getroot()
            self.assertTrue(root.tag.endswith("svg"))
            self.assertFalse(any(node.tag.endswith("script") for node in root.iter()))

    def test_changed_summary_counts_fail_closed(self):
        graph, fusion = load_gzip(ROOT/GRAPH), load_gzip(ROOT/FUSION)
        fusion["arms"]["baseline_choice"]["operational"]["edges"]["correct"] += 1
        with patch("graph_synthesis.visualize.load_gzip", side_effect=[graph, fusion]):
            with self.assertRaises(ValueError): build_data(ROOT)

    def test_paper_includes_each_reviewed_figure_once(self):
        import re
        text = (ROOT / "graph_synthesis/paper.md").read_text(encoding="utf-8")
        images = re.findall(r'!\[[^\]]*\]\(figures/([^)]+)\)', text)
        self.assertEqual(len(images), len(CAPTIONS))
        self.assertEqual(set(images), {n + ".svg" for n in CAPTIONS})

    def test_lifecycle_retains_history(self):
        for task in self.data["tasks"].values():
            for arm in task["arms"].values():
                x = arm["graph"]["lifecycle"]
                self.assertEqual(x["original_assertions_preserved"], x["active_after_withdrawal"] + x["actual_retractions"])


if __name__ == "__main__":
    unittest.main()
