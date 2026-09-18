"""Metric, negative-control, and real frozen-observation regression tests."""
from copy import deepcopy
import json
import math
from pathlib import Path
import unittest

from graph_synthesis.core import digest
from graph_synthesis.falsification import (ACTIONS, candidate_loss, component_groups,
    component_quality, joint_errors, paired_component_bootstrap, prevalence_projection,
    quality, quantile, surviving_ids, validate_pair, zero_error_sample_size)
from graph_synthesis.recorded import RecordedJev, BASELINES
from graph_synthesis.study import read_scores
from graph_synthesis.stress_mechanisms import (copied_source_witness, descendants,
    identity_bridge, repair_episode, semantic_witnesses)

ROOT = Path(__file__).resolve().parents[2]


def row(id_, gold="SUPPORTS", label="SUPPORTS", *, document=None, claim=None):
    return {"id": id_, "gold": gold, "label": label, "score": 1.0,
            "row": {"document_id": document or "d"+id_, "claim_id": claim or "c"+id_,
                    "entity_1": "a"+id_, "entity_2": "b"+id_}}


class MetricTests(unittest.TestCase):
    def test_empty_precision_not_perfect(self):
        q = quality([], ACTIONS["relation_support"])
        self.assertIsNone(q["precision"])
        self.assertIsNone(q["recall"])

    def test_wrong_polarity_is_wrong_edge_and_missed_gold(self):
        q = quality([row("a", label="REFUTES")], ACTIONS["relation_support"])
        self.assertEqual((q["wrong"], q["recall"]), (1, 0))

    def test_error_is_not_neutral(self):
        q = quality([row("a", label="ERROR")], ACTIONS["relation_support"])
        self.assertEqual(q["operational_errors"], 1)
        self.assertEqual(q["recall"], 0)
        self.assertIsNone(q["precision"])

    def test_empty_graph_is_not_complete_synthesis(self):
        rows = [row("a", label="NOT_ENOUGH_INFO")]
        q = component_quality(rows, ACTIONS["relation_support"], {"a": "g"})
        self.assertEqual(q["complete_and_clean_components"], 0)
        self.assertEqual(q["empty_components"], 1)

    def test_no_positive_component_is_not_counted_complete(self):
        rows = [row("a", gold="NOT_ENOUGH_INFO", label="NOT_ENOUGH_INFO")]
        q = component_quality(rows, ACTIONS["relation_support"], {"a": "g"})
        self.assertEqual(q["gold_positive_components"], 0)
        self.assertIsNone(q["complete_and_clean_fraction"])

    def test_one_wrong_edge_contaminates_whole_component(self):
        rows = [row("a"), row("b", label="REFUTES")]
        q = component_quality(rows, ACTIONS["relation_support"], {"a": "g", "b": "g"})
        self.assertEqual((q["contaminated_components"], q["complete_and_clean_components"]), (1, 0))

    def test_complete_and_clean_requires_all_gold_edges(self):
        rows = [row("a"), row("b", label="NOT_ENOUGH_INFO")]
        q = component_quality(rows, ACTIONS["relation_support"], {"a": "g", "b": "g"})
        self.assertEqual(q["contaminated_components"], 0)
        self.assertEqual(q["complete_and_clean_components"], 0)

    def test_all_candidate_endpoints_group_even_failed_rows(self):
        rows = [row("a", document="shared"), row("b", document="shared", label="ERROR")]
        groups = component_groups(rows, "relation_support")
        self.assertEqual(groups["a"], groups["b"])

    def test_grouping_does_not_use_gold_or_scores(self):
        rows = [row("a"), row("b", document="da")]
        expected = component_groups(rows, "relation_support")
        for r in rows:
            r["gold"] = "REFUTES"
            r["label"] = "ERROR"
            r["score"] = 0
        self.assertEqual(component_groups(rows, "relation_support"), expected)

    def test_grouping_is_order_invariant(self):
        rows = [row("a"), row("b", document="da"), row("c")]
        self.assertEqual(component_groups(rows, "relation_support"), component_groups(rows[::-1], "relation_support"))

    def test_pair_validator_rejects_missing_ids(self):
        with self.assertRaises(ValueError):
            validate_pair([row("a")], [])

    def test_pair_validator_rejects_duplicate_ids(self):
        with self.assertRaises(ValueError):
            validate_pair([row("a"), row("a")], [row("a"), row("a")])

    def test_pair_validator_rejects_different_gold(self):
        with self.assertRaises(ValueError):
            validate_pair([row("a")], [row("a", gold="REFUTES")])

    def test_pair_validator_rejects_different_candidate(self):
        with self.assertRaises(ValueError):
            validate_pair([row("a")], [row("a", document="other")])

    def test_joint_errors_excludes_operations_from_semantic_denominator(self):
        a = [row("a", label="ERROR"), row("b", label="REFUTES")]
        b = [row("a"), row("b", label="REFUTES")]
        j = joint_errors(a, b)
        self.assertEqual((j["common_success"], j["both_wrong"], j["agree_wrong"]), (1, 1, 1))

    def test_joint_errors_zero_marginal_no_infinite_ratio(self):
        j = joint_errors([row("a")], [row("a")])
        self.assertIsNone(j["observed_to_independent_joint_ratio"])

    def test_joint_errors_pair_by_id_not_row_order(self):
        a = [row("a"), row("b", label="REFUTES")]
        self.assertEqual(joint_errors(a, a), joint_errors(a, a[::-1]))

    def test_identical_arms_have_zero_bootstrap_difference(self):
        rows = [row("a"), row("b", label="REFUTES")]
        result = paired_component_bootstrap(rows, rows[::-1], "relation_support", 20)
        for v in result["metrics"].values():
            self.assertEqual((v["lower"], v["upper"]), (0, 0))

    def test_undefined_precision_draws_are_reported(self):
        rows = [row("a", label="NOT_ENOUGH_INFO")]
        p = paired_component_bootstrap(rows, rows, "relation_support", 20)
        self.assertEqual(p["metrics"]["precision"]["valid_draws"], 0)
        self.assertIsNone(p["metrics"]["precision"]["lower"])

    def test_invalid_bootstrap_draws(self):
        with self.assertRaises(ValueError):
            paired_component_bootstrap([], [], "relation_support", 0)

    def test_quantile_linear_interpolation(self):
        self.assertEqual(quantile([0, 2], .25), .5)
        self.assertIsNone(quantile([], .5))
        with self.assertRaises(ValueError):
            quantile([1], 2)

    def test_source_loss_nested_and_shared(self):
        rows = [row(str(i)) for i in range(20)]
        for seed in range(10):
            previous = {r["id"] for r in rows}
            for loss in (0, .1, .25, .5, .75, 1):
                keep = surviving_ids(rows, "relation_support", loss, seed)
                self.assertLessEqual(keep, previous)
                self.assertEqual(keep, surviving_ids(rows[::-1], "relation_support", loss, seed))
                previous = keep

    def test_source_loss_removes_all_candidates_from_source(self):
        rows = [row("a", document="shared"), row("b", document="shared"), row("c")]
        keep = surviving_ids(rows, "relation_support", .5, 0)
        self.assertEqual("a" in keep, "b" in keep)

    def test_source_loss_ignores_labels(self):
        rows = [row(str(i)) for i in range(10)]
        expected = surviving_ids(rows, "relation_support", .5, 17)
        for r in rows:
            r["gold"] = "REFUTES"
            r["label"] = "ERROR"
        self.assertEqual(surviving_ids(rows, "relation_support", .5, 17), expected)

    def test_candidate_loss_keeps_original_denominator(self):
        rows = [row(str(i)) for i in range(4)]
        panels = candidate_loss({"a": rows, "b": rows[::-1]}, "relation_support", 2)
        fifty = next(p for p in panels if p["loss_fraction"] == .5)
        self.assertEqual(fifty["original_gold_positive"], 4)
        self.assertEqual(fifty["arm_recall"]["a"]["mean"], .5)
        self.assertEqual(fifty["arm_recall"]["a"], fifty["arm_recall"]["b"])

    def test_invalid_loss_is_rejected(self):
        with self.assertRaises(ValueError):
            surviving_ids([], "relation_support", 1.01, 0)

    def test_prevalence_formula_and_decreasing_base_rate(self):
        rows = [row("a"), row("b", gold="NOT_ENOUGH_INFO")]
        result = prevalence_projection(rows, "SUPPORTS")
        # TPR=FPR=1 implies precision equals prevalence.
        for p in result["projections"]:
            self.assertAlmostEqual(p["projected_precision"], p["prevalence"])

    def test_missing_class_gives_undefined_projection(self):
        result = prevalence_projection([row("a")], "SUPPORTS")
        self.assertTrue(all(p["projected_precision"] is None for p in result["projections"]))

    def test_zero_error_planning_is_minimal(self):
        self.assertEqual(zero_error_sample_size(.01), 299)
        self.assertEqual(zero_error_sample_size(.001), 2995)
        for target in (.01, .001):
            n = zero_error_sample_size(target)
            self.assertLessEqual(1 - .05 ** (1/n), target)
            self.assertGreater(1 - .05 ** (1/(n-1)), target)

    def test_planning_rejects_invalid_risk(self):
        for target in (0, 1, -1, float("nan")):
            with self.subTest(target=target), self.assertRaises(ValueError):
                zero_error_sample_size(target)


class MechanismTests(unittest.TestCase):
    def test_schema_correct_does_not_mean_truth(self):
        self.assertEqual(semantic_witnesses()["valid_but_false_assertions_accepted"], 1)

    def test_overlapping_temporal_scope_is_known_limitation(self):
        self.assertEqual(semantic_witnesses()["overlapping_temporal_opposites_accepted"], 2)

    def test_declared_type_violation_fails_atomically(self):
        self.assertTrue(semantic_witnesses()["schema_invalid_assertion_rejected_atomically"])

    def test_origin_copy_is_not_new_corroboration(self):
        w = copied_source_witness(10)
        self.assertEqual((w["source_records"], w["unique_origins"], w["initial_derived_edges"]), (10, 1, 1))

    def test_withdrawing_one_copy_is_not_origin_wide(self):
        w = copied_source_witness(10)
        self.assertEqual(w["residual_assertions_after_one_copy_withdrawal"], 9)
        self.assertEqual(w["active_after_explicit_origin_wide_withdrawal"], 0)

    def test_identity_bridge_amplification_and_repair(self):
        for n in (2, 10, 100):
            with self.subTest(size=n):
                w = identity_bridge(n)
                self.assertEqual(w["false_cross_identity_pairs_before_repair"], n*n)
                self.assertEqual(w["false_cross_identity_pairs_after_repair"], 0)
                self.assertEqual(w["identity_components_after_repair"], 2)

    def test_independent_retraction_oracle(self):
        self.assertEqual(descendants({"a": set(), "b": {"a"}, "c": {"b"}, "d": set()}, {"a"}), {"a", "b", "c"})

    def test_twenty_seeded_dag_lifecycle_episodes(self):
        for seed in range(20):
            with self.subTest(seed=seed):
                e = repair_episode(seed)
                self.assertEqual(e["oracle_retractions"], e["actual_retractions"])
                self.assertTrue(e["atomic_fault_rollback"] and e["retry_idempotent"] and e["durable_reopen"])

    def test_invalid_mechanism_sizes(self):
        for fn, size in ((copied_source_witness, 0), (identity_bridge, 1)):
            with self.assertRaises(ValueError):
                fn(size)


class FrozenDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        backend = RecordedJev(ROOT)
        cls.rows = {arm: read_scores(backend, "relation_support", name, "evaluation")
                    for arm, name in (("generic", BASELINES["relation_support"]), ("fewshot", "fewshot_contract"))}

    def test_real_relation_quality_conservation(self):
        for arm, expected in (("generic", (224, 187, 37)), ("fewshot", (192, 172, 20))):
            q = quality(self.rows[arm], ACTIONS["relation_support"])
            self.assertEqual((q["accepted"], q["correct"], q["wrong"]), expected)
            self.assertEqual(q["gold_positive"], 209)

    def test_real_complete_neighborhood_tradeoff(self):
        groups = component_groups(self.rows["generic"], "relation_support")
        self.assertEqual(len(set(groups.values())), 247)
        for arm, complete in (("generic", 140), ("fewshot", 126)):
            c = component_quality(self.rows[arm], ACTIONS["relation_support"], groups)
            self.assertEqual(c["gold_positive_components"], 164)
            self.assertEqual(c["complete_and_clean_components"], complete)

    def test_real_errors_are_shared_not_independent_votes(self):
        j = joint_errors(self.rows["generic"], self.rows["fewshot"])
        self.assertEqual((j["both_wrong"], j["agree_wrong"], j["common_success"]), (34, 31, 336))

    def test_reference_fresh_call_count_zero(self):
        path = ROOT / "experiments/falsification/results.json"
        r = json.loads(path.read_text())
        self.assertEqual(r["fresh_model_calls"], 0)
        self.assertEqual(r["classification"], "post_hoc_frozen_inference_diagnostics")


if __name__ == "__main__":
    unittest.main()
