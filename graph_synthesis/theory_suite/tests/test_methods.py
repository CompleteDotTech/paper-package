from copy import deepcopy
from itertools import combinations, product
from pathlib import Path
import random
import socket
import tempfile
import unittest
from unittest.mock import patch

from graph_synthesis.core import GraphStore, Relation, evidence
from graph_synthesis.theory_suite import analyses, controlled, methods, run


def row(id_="x", score=.9, label="yes", gold="yes", group="g", tokens=10, error=False):
    return {"id": id_, "score": score, "label": label, "gold": gold, "group": group,
            "input_tokens": tokens, "error": error, "endpoints": (id_ + ":a", id_ + ":b"),
            "probabilities": {"yes": score if label == "yes" else 1-score,
                              "no": score if label == "no" else 1-score}}


class MethodTests(unittest.TestCase):
    def test_macro_f1_known_confusion(self):
        self.assertAlmostEqual(methods.macro_f1(["yes", "no", "yes"], ["yes", "yes", "no"], ["yes", "no"]), .25)

    def test_macro_f1_invalid_alignment(self):
        for gold, pred in (([], []), (["yes"], [])):
            with self.assertRaises(ValueError):
                methods.macro_f1(gold, pred, ["yes", "no"])

    def test_group_conformal_uses_maximum_and_finite_rank(self):
        rows = [row("a", .99, group="one"), row("b", .4, group="one"), row("c", .8, group="two")]
        fit = methods.conformal_fit(rows, ["yes", "no"], split="calibration", alpha=.5)
        self.assertEqual(fit["groups"], 2)
        self.assertAlmostEqual(fit["quantile"], .6)

    def test_conformal_empty_or_tiny_calibration_universal(self):
        for rows in ([], [row()]):
            fit = methods.conformal_fit(rows, ["yes", "no"], split="calibration")
            self.assertTrue(fit["universal"])
            self.assertEqual(methods.prediction_set({}, ["yes", "no"], fit), ("yes", "no"))

    def test_conformal_refuses_evaluation_fit(self):
        with self.assertRaises(ValueError):
            methods.conformal_fit([row()], ["yes", "no"], split="evaluation")

    def test_prediction_set_ties_errors_and_empty(self):
        fit = {"universal": False, "quantile": .5}
        self.assertEqual(methods.prediction_set({"yes": .5, "no": .5}, ["yes", "no"], fit), ("yes", "no"))
        self.assertEqual(methods.prediction_set({}, ["yes", "no"], fit, error=True), ("yes", "no"))
        self.assertEqual(methods.prediction_set({"yes": .5, "no": .5}, ["yes", "no"], {**fit, "quantile": .1}), ())

    def test_invalid_probability_rejected(self):
        for value in (float("nan"), float("inf"), -.1, 1.1, True):
            with self.assertRaises(ValueError):
                methods.projected_precision(value, .1, .01)
            with self.assertRaises(ValueError):
                methods.admit_budget([row(score=value)])

    def test_rare_prior_precision_known(self):
        self.assertAlmostEqual(methods.projected_precision(.9, .1, .01), .009 / .108)
        self.assertIsNone(methods.projected_precision(0, 0, .1))

    def test_budget_is_component_local_and_permutation_stable(self):
        rows = [row("a", .97), row("b", .97), row("c", .96, group="other")]
        expected = {"a", "c"}
        self.assertEqual(methods.admit_budget(rows), expected)
        self.assertEqual(methods.admit_budget(list(reversed(rows))), expected)

    def test_budget_duplicate_id_rejected(self):
        with self.assertRaises(ValueError):
            methods.admit_budget([row(), row()])

    def test_budget_does_not_treat_probability_one_as_certification(self):
        wrong = row(score=1, gold="no")
        self.assertEqual(methods.admit_budget(analyses.features([wrong]), 0), {"x"})
        self.assertNotEqual(wrong["label"], wrong["gold"])

    def test_source_component_purge_transitive_and_label_free(self):
        cal = [row("c1"), row("c2"), row("c3")]
        ev = [row("e1")]
        cal[0]["endpoints"], cal[1]["endpoints"] = ("a", "b"), ("b", "c")
        ev[0]["endpoints"] = ("c", "d")
        retained, audit = analyses.purge_groups(cal, ev)
        self.assertEqual([r["id"] for r in retained], ["c3"])
        self.assertEqual(audit["calibration_purged_rows"], 2)
        self.assertEqual(audit["overlap_after_purge"], 0)

    def test_features_exclude_gold_and_unknown_annotations(self):
        a = row()
        a["hidden_truth"] = "do not pass"
        output = analyses.features([a])[0]
        self.assertNotIn("gold", output)
        self.assertNotIn("hidden_truth", output)
        b = {**a, "gold": "no"}
        self.assertEqual(analyses.features([a]), analyses.features([b]))

    def test_review_gold_independence(self):
        rows = [row("a", .9), row("b", .7), row("c", .5)]
        original = methods.review_selection(analyses.features(rows), 1, topology=True)
        for r in rows:
            r["gold"] = "no"
        self.assertEqual(original, methods.review_selection(analyses.features(rows), 1, topology=True))

    def test_topological_review_uses_neighborhood_not_gold(self):
        rows = [row("a", .9), row("b", .86), row("c", .99), row("d", .99)]
        rows[0]["endpoints"] = ("hub", "x")
        rows[2]["endpoints"] = ("hub", "z")
        rows[3]["endpoints"] = ("hub", "w")
        self.assertEqual(methods.review_selection(analyses.features(rows), 1, topology=False), {"b"})
        self.assertEqual(methods.review_selection(analyses.features(rows), 1, topology=True), {"a"})

    def test_review_invalid_budget_and_duplicate(self):
        for budget in (-1, 2, True):
            with self.assertRaises(ValueError):
                methods.review_selection([row()], budget, topology=True)
        with self.assertRaises(ValueError):
            methods.review_selection([row(), row()], 1, topology=True)

    def test_cascade_cost_includes_initial_call_and_error_fallback(self):
        base = [row(error=True, tokens=10), row("y", score=.99, tokens=10)]
        few = [row(tokens=100), row("y", tokens=100)]
        pred, tokens, calls = methods.cascade_predict(analyses.features(base), analyses.features(few), 0)
        self.assertEqual((tokens, calls), (120, 1))
        self.assertEqual(pred, ["yes", "yes"])

    def test_cascade_calibration_only(self):
        with self.assertRaises(ValueError):
            methods.fit_cascade([row()], [row()], ["yes"], ["yes", "no"], split="evaluation")

    def test_cascade_alignment_and_missing_tokens(self):
        with self.assertRaises(ValueError):
            methods.cascade_predict([row()], [row("other")], .9)
        with self.assertRaises(ValueError):
            methods.cascade_predict([row(tokens=-1)], [row()], .9)

    def test_cascade_fit_uses_cheapest_eligible_not_evaluation(self):
        base = [row(), row("b", label="no", gold="no")]
        few = [{**r, "input_tokens": 100} for r in base]
        fit = methods.fit_cascade(analyses.features(base), analyses.features(few), ["yes", "no"], ["yes", "no"], split="calibration")
        self.assertEqual(fit["threshold"], 0)
        self.assertEqual(methods.cascade_predict(analyses.features(base), analyses.features(few), fit["threshold"])[1], 20)

    def test_bell_partition_count_and_size_guard(self):
        self.assertEqual([len(methods.partitions(i)) for i in (1, 2, 3, 6)], [1, 2, 5, 203])
        for n in (0, 8, True):
            with self.assertRaises(ValueError):
                methods.partitions(n)

    def test_exact_decoder_known_triangle(self):
        probs = {(0, 1): .99, (1, 2): .99, (0, 2): .001}
        answer = methods.joint_decode(3, probs)
        self.assertNotEqual(answer[0], answer[2])

    def test_exact_objective_not_worse_than_greedy(self):
        rng = random.Random(71)
        pairs = list(combinations(range(4), 2))
        for _ in range(25):
            probs = {pair: rng.random() for pair in pairs}
            a = methods.joint_decode(4, probs)
            b = methods.joint_decode(4, probs, greedy_order=pairs)
            self.assertGreaterEqual(methods.partition_objective(a, probs) + 1e-10, methods.partition_objective(b, probs))

    def test_exact_decoder_permutation_equivariance_without_ties(self):
        probs = {(0, 1): .999, (0, 2): .001, (1, 2): .002}
        p = (2, 0, 1)
        permuted = {(i, j): probs[tuple(sorted((p[i], p[j])))] for i, j in combinations(range(3), 2)}
        a, b = methods.joint_decode(3, probs), methods.joint_decode(3, permuted)
        for i, j in combinations(range(3), 2):
            self.assertEqual(a[p[i]] == a[p[j]], b[i] == b[j])

    def test_decoder_incomplete_pairs_and_bad_order(self):
        with self.assertRaises(ValueError):
            methods.joint_decode(3, {(0, 1): .9})
        with self.assertRaises(ValueError):
            methods.joint_decode(2, {(0, 1): .9}, greedy_order=[])

    def test_semantic_cache_key_versions_and_absence(self):
        args = {"state": {"x": 1}, "question": "q", "model": "m", "schema": "s", "policy": "p", "dependencies": {"absent_query": 0}}
        initial = methods.semantic_key(**args)
        for field in ("question", "model", "schema", "policy"):
            self.assertNotEqual(initial, methods.semantic_key(**{**args, field: "changed"}))
        self.assertNotEqual(initial, methods.semantic_key(**{**args, "dependencies": {"absent_query": 1}}))
        self.assertEqual(initial, methods.semantic_key(**deepcopy(args)))

    def test_semantic_cache_rejects_missing_versions_and_bad_generation(self):
        args = {"state": {}, "question": "q", "model": "m", "schema": "s", "policy": "p", "dependencies": {"x": 0}}
        for change in ({"model": ""}, {"dependencies": {"x": True}}, {"dependencies": {"x": -1}}):
            with self.assertRaises(ValueError):
                methods.semantic_key(**{**args, **change})

    def test_lineage_all_withdrawal_subsets(self):
        result = controlled.t09()
        self.assertEqual(len(result["cases"]), 16)
        self.assertTrue(result["target_met"])
        self.assertEqual(result["strategies"]["flattened_AND"]["false_removals"], 4)
        self.assertEqual(result["strategies"]["flattened_OR"]["false_retention"], 10)

    def test_schema_preview_detects_symmetry_and_inverse_drift(self):
        result = controlled.t10()
        self.assertEqual(result["query_changing_migrations"], 4)
        self.assertEqual(result["type_valid_migrations"], 8)
        self.assertTrue(result["target_met"])

    def test_schema_preview_invalid_migration_leaves_original(self):
        schema = {"p": Relation("Node", "Node")}
        policy = controlled.synthetic_policy(schema)
        store = GraphStore(":memory:", schema, policy)
        self.addCleanup(store.close)
        ev = evidence("s", "v1", "Controlled evidence")
        store.commit(nodes={"a": "Node", "b": "Node"}, sources=[ev],
                     facts=[controlled.fixture_fact("f", "p", [ev], policy)], expected_version=0, key="start")
        before = store.snapshot()
        result = methods.migration_preview(store, {"p": Relation("Other", "Node")}, [("a", "p", "b")])
        self.assertFalse(result["accepted"])
        self.assertFalse(result["type_valid"])
        self.assertEqual(before, store.snapshot())

    def test_offline_socket_guard(self):
        with self.assertRaisesRegex(RuntimeError, "offline"):
            run._no_network()

    def test_run_restores_socket_after_input_failure(self):
        original = socket.socket
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                run.run(Path(directory))
        self.assertIs(socket.socket, original)


class ArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backend, cls.data, cls.audit = analyses.load(run.ROOT)

    def test_original_recorded_inputs_and_no_post_purge_overlap(self):
        self.assertEqual(self.backend.plan["model"], "jev-1.13.0")
        for a in self.audit.values():
            self.assertEqual(a["overlap_after_purge"], 0)
        self.assertEqual(sum(a["evaluation_rows"] for a in self.audit.values()), 752)

    def test_cost_calls_are_unique_within_each_comparison(self):
        for arms in self.data.values():
            calls = [r["call_id"] for splits in arms.values() for rows in splits.values() for r in rows]
            self.assertEqual(len(calls), len(set(calls)))

    def test_eval_gold_changes_do_not_change_calibration_choices(self):
        task = "entity_resolution"
        changed = deepcopy(self.data[task])
        before = analyses.t06(task, changed)["fit"]
        for splits in changed.values():
            for r in splits["evaluation"]:
                r["gold"] = "different" if r["gold"] == "same" else "same"
        self.assertEqual(before, analyses.t06(task, changed)["fit"])

    def test_conformal_target_does_not_imply_nominal_coverage(self):
        result = analyses.t01("entity_resolution", self.data["entity_resolution"])
        self.assertTrue(result["target_met"])
        self.assertLess(result["row_label_coverage"], .9)

    def test_error_rate_budget_counterexample_is_retained(self):
        result = analyses.t04("relation_support", self.data["relation_support"])
        self.assertFalse(result["target_met"])
        self.assertGreater(result["wrong_edges_at_probability_one"], 0)


if __name__ == "__main__":
    unittest.main()
