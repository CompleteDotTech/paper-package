"""Tests of protocol boundaries, numeric implementation, and real replay."""
from copy import deepcopy
from dataclasses import replace
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from graph_synthesis.core import digest
from graph_synthesis.edge_fusion import (ARMS, LABELS, Decision, Observation, budget_metrics,
    feature_vector, fit_model, fold_for, load_split, metrics, model_identity,
    model_probability, objective_gradient, predict, rank_edges, train_policy, valid)
from graph_synthesis.edge_experiment import (bootstrap_f1, bootstrap_precision,
    bootstrap_weights, compact_journal, compare_reference, graph_for)
from graph_synthesis.recorded import RecordedJev

ROOT = Path(__file__).resolve().parents[2]


def observation(id_="x", a=(.8, .1, .1), b=(.6, .2, .2), group="g"):
    return Observation(id_, group, (a, b), ("request-a", "request-b"), ("call-a", "call-b"), "jev-1.13.0")


def fixture(n=30):
    obs, gold = [], []
    for i in range(n):
        p = [.05]*3
        p[i % 3] = .9
        obs.append(observation(str(i), tuple(p), tuple(p), str(i)))
        gold.append(LABELS[i % 3])
    return obs, gold


class NumericTests(unittest.TestCase):
    def test_gradient_matches_finite_difference(self):
        rng = np.random.default_rng(2)
        x = np.column_stack((rng.normal(size=(8, 6)), np.ones(8)))
        y = np.arange(8) % 3
        w = rng.normal(size=(7, 3))*.1
        _, gradient = objective_gradient(x, y, w, .1)
        for i in range(7):
            for j in range(3):
                plus, minus = w.copy(), w.copy()
                plus[i, j] += 1e-6; minus[i, j] -= 1e-6
                numeric = (objective_gradient(x, y, plus, .1)[0]-objective_gradient(x, y, minus, .1)[0])/2e-6
                self.assertAlmostEqual(numeric, gradient[i, j], places=7)

    def test_fit_converges_and_probabilities_are_valid(self):
        obs, gold = fixture()
        model = fit_model(obs, gold, .1)
        self.assertTrue(model["converged"])
        self.assertLess(model["final_objective"], model["initial_objective"])
        for o, g in zip(obs, gold):
            p = model_probability(o, model)
            self.assertAlmostEqual(sum(p), 1, places=7)
            self.assertEqual(predict(o, "stacked", model).label, g)

    def test_features_handle_exact_zero_one_and_constant_scales(self):
        o = observation(a=(1., 0., 0.), b=(1., 0., 0.))
        self.assertTrue(np.isfinite(feature_vector(o)).all())
        model = fit_model([replace(o, id=str(i)) for i in range(9)], list(LABELS)*3, .1)
        self.assertEqual(model["scale"], [1.]*6)

    def test_training_validation(self):
        obs, gold = fixture()
        for penalty in (0, -1, float("nan")):
            with self.assertRaises(ValueError): fit_model(obs, gold, penalty)
        with self.assertRaises(ValueError): fit_model(obs, ["SUPPORTS"]*len(obs), .1)
        with self.assertRaises(ValueError): fit_model(obs, gold[:-1], .1)

    def test_invalid_features_rejected(self):
        for p in ((.2, .2, .2), (float("nan"), .5, .5), (True, 0., 0.), (.5, .5), (-.1, .5, .6)):
            with self.assertRaises(ValueError): feature_vector(observation(a=p))
        with self.assertRaises(ValueError): feature_vector(observation(a=None))


class PolicyTests(unittest.TestCase):
    def test_immutable_baselines_and_mean(self):
        o = observation()
        a = predict(o, "baseline_choice")
        self.assertEqual(a.probabilities, o.probabilities[0])
        self.assertEqual(a.call_ids, ("call-a",))
        self.assertEqual(predict(o, "mean_pool").probabilities, (.7, .15000000000000002, .15000000000000002))

    def test_disagreement_is_abstention_not_nei(self):
        o = observation(b=(.1, .8, .1))
        d = predict(o, "agreement_gate")
        self.assertEqual(d.label, "ABSTAIN")
        self.assertIsNone(d.probabilities)
        m = metrics(["NOT_ENOUGH_INFO"], [d])
        self.assertEqual(m["accuracy"], 0)
        self.assertEqual(m["abstentions"], 1)

    def test_invalid_constituent_is_error_not_fallback(self):
        o = observation(a=None)
        model = fit_model(*fixture(), .1)
        for arm in ARMS[2:]:
            d = predict(o, arm, model)
            self.assertEqual(d.label, "ERROR")
            self.assertIsNone(d.probabilities)
            self.assertEqual(len(d.call_ids), 2)
        self.assertEqual(predict(o, "fewshot_contract").label, "SUPPORTS")

    def test_input_and_model_changes_rebind_provenance(self):
        o = observation()
        model = fit_model(*fixture(), .1)
        original = predict(o, "stacked", model).request_hash
        changed = replace(o, request_hashes=("new-evidence-request", "request-b"))
        self.assertNotEqual(original, predict(changed, "stacked", model).request_hash)
        model["weights"][0][0] += .1
        self.assertNotEqual(original, predict(o, "stacked", model).request_hash)

    def test_changed_constituent_response_changes_binding(self):
        o = observation()
        first = predict(o, "mean_pool")
        changed = replace(o, probabilities=((.7,.2,.1), o.probabilities[1]))
        self.assertNotEqual(first.request_hash, predict(changed, "mean_pool").request_hash)
        changed = replace(o, call_ids=("another-call", "call-b"))
        self.assertNotEqual(first.request_hash, predict(changed, "mean_pool").request_hash)

    def test_malformed_model_fails_closed(self):
        model = fit_model(*fixture(), .1)
        for field, value in (("scale", [0.]*6), ("weights", [[float("nan")]*3]*7), ("mean", [1.])):
            bad = deepcopy(model); bad[field] = value
            with self.assertRaises(ValueError): model_probability(observation(), bad)

    def test_ties_have_canonical_label_and_id_order(self):
        obs = [observation("b", (.5,.5,0), (.5,.5,0)), observation("a", (.5,.5,0), (.5,.5,0))]
        decisions = [predict(o, "mean_pool") for o in obs]
        self.assertEqual([d.label for d in decisions], ["SUPPORTS"]*2)
        self.assertEqual(rank_edges(obs, decisions), [1, 0])
        b = budget_metrics(["SUPPORTS"]*2, obs, decisions, 1)
        self.assertEqual(b["boundary_ties"], 2)

    def test_unknown_arm_and_missing_model_fail(self):
        with self.assertRaises(ValueError): predict(observation(), "nonexistent")
        with self.assertRaises(ValueError): predict(observation(), "stacked")

    def test_gold_and_groups_are_not_prediction_features(self):
        o = observation(); model = fit_model(*fixture(), .1)
        a = predict(o, "stacked", model)
        b = predict(replace(o, id="new-row", group="new-group"), "stacked", model)
        self.assertEqual(a, b)

    def test_selection_rejects_evaluation_and_duplicate_rows(self):
        obs, gold = fixture()
        with self.assertRaisesRegex(ValueError, "never evaluation"):
            train_policy(obs, gold, split="evaluation")
        with self.assertRaises(ValueError): train_policy(obs+obs[:1], gold+gold[:1], split="calibration")


class MetricTests(unittest.TestCase):
    def test_denominators_wrong_polarity_and_errors(self):
        def d(label): return Decision(label, (.5,.3,.2) if label in LABELS else None, "h", ())
        m = metrics(["SUPPORTS", "REFUTES", "NOT_ENOUGH_INFO", "SUPPORTS"],
                    [d("SUPPORTS"), d("SUPPORTS"), d("REFUTES"), d("ERROR")])
        self.assertEqual(m["edges"]["accepted"], 3)
        self.assertEqual(m["edges"]["correct"], 1)
        self.assertEqual(m["edges"]["recall"], 1/3)
        self.assertEqual(m["edges"]["coverage"], 3/4)
        self.assertEqual(m["macro_f1"], 1/6)

    def test_zero_edges_and_empty_classes(self):
        d = Decision("NOT_ENOUGH_INFO", (0.,0.,1.), "h", ())
        m = metrics(["NOT_ENOUGH_INFO"], [d])
        self.assertEqual(m["macro_f1"], 1/3)
        self.assertIsNone(m["edges"]["precision"])
        self.assertIsNone(m["edges"]["recall"])
        with self.assertRaises(ValueError): budget_metrics(["NOT_ENOUGH_INFO"], [observation()], [d], 1)

    def test_component_bootstrap_pairs_and_undefined_precision(self):
        obs, gold = fixture(9)
        obs = [replace(o, group=str(i//3)) for i, o in enumerate(obs)]
        decisions = [predict(o, "mean_pool") for o in obs]
        groups, weights = bootstrap_weights(obs)
        self.assertEqual(len(groups), 3)
        self.assertTrue((weights.sum(axis=1) == 3).all())
        f1 = bootstrap_f1(gold, obs, decisions, groups, weights)
        self.assertTrue(np.allclose(f1, 1))
        p, counts = bootstrap_precision(gold, obs, decisions, [], groups, weights)
        self.assertTrue(np.isnan(p).all())
        self.assertTrue((counts == 0).all())

    def test_reference_comparison_does_not_hide_count_or_label_changes(self):
        compare_reference({"p": .12345678}, {"p": .123456780000001})
        for a, b in (({"n": 10}, {"n": 11}), (["SUPPORTS"], ["REFUTES"]), ({"p": 1}, {"p": 1.})):
            with self.assertRaises(AssertionError): compare_reference(a, b)


class ReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backend = RecordedJev(ROOT)
        cls.calibration, cls.cg = load_split(cls.backend, "calibration")
        cls.obs, cls.gold = load_split(cls.backend, "evaluation")
        cls.fitted = train_policy(cls.calibration, cls.cg, split="calibration")

    def test_actual_populations_and_disjointness(self):
        self.assertEqual((len(self.calibration), len(self.obs)), (150, 339))
        self.assertEqual(sum(valid(o) for o in self.calibration), 149)
        self.assertEqual(sum(valid(o) for o in self.obs), 336)
        self.assertFalse({o.group for o in self.calibration} & {o.group for o in self.obs})
        self.assertFalse(set(self.fitted["model"]["training_ids"]) & {o.id for o in self.obs})

    def test_grouped_selection_uses_only_calibration(self):
        for group, fold in self.fitted["folds"].items():
            self.assertEqual(fold, fold_for(group))
        self.assertEqual(self.fitted["source_split"], "calibration")
        self.assertEqual(len(self.fitted["candidates"]), 4)
        for c in self.fitted["candidates"]:
            self.assertEqual(len(c["oof"]), 150)
            self.assertEqual(c["errors"], 1)
            self.assertEqual(sum(f["test_n"] for f in c["folds"]), 150)

    def test_fold_preprocessing_excludes_held_groups(self):
        import graph_synthesis.edge_fusion as module
        original = module.fit_model
        seen = []
        def spy(obs, gold, penalty):
            seen.append({o.group for o in obs})
            return original(obs, gold, penalty)
        with patch.object(module, "fit_model", side_effect=spy):
            train_policy(self.calibration, self.cg, split="calibration")
        self.assertEqual(len(seen), 21)
        for i, groups in enumerate(seen[:-1]):
            self.assertTrue(all(fold_for(g) != i % 5 for g in groups))

    def test_original_point_metrics_reproduced(self):
        a = metrics(self.gold, [predict(o, ARMS[0]) for o in self.obs])
        b = metrics(self.gold, [predict(o, ARMS[1]) for o in self.obs])
        self.assertEqual((a["edges"]["correct"], a["edges"]["incorrect"]), (187, 37))
        self.assertEqual((b["edges"]["correct"], b["edges"]["incorrect"]), (172, 20))

    def test_graph_and_audit_independent_of_evaluation_gold(self):
        obs = self.obs[:20]; gold = self.gold[:20]
        decisions = [predict(o, "stacked", self.fitted["model"]) for o in obs]
        first = graph_for(self.backend, obs, gold, decisions)
        second = graph_for(self.backend, obs, ["NOT_ENOUGH_INFO"]*len(obs), decisions)
        self.assertEqual(first["audit"], second["audit"])
        self.assertEqual(first["metrics"], second["metrics"])
        self.assertTrue(first["lifecycle"]["durable_reopen_equal"])

    def test_journal_determinism_and_true_call_binding(self):
        outputs = {a: [predict(o, a, self.fitted["model"]) for o in self.obs[:5]] for a in ARMS}
        first = compact_journal(self.obs[:5], self.gold[:5], outputs, self.fitted["model_hash"])
        second = compact_journal(self.obs[:5], self.gold[:5], outputs, self.fitted["model_hash"])
        self.assertEqual(first, second)
        self.assertIn(self.fitted["model_hash"], gzip.decompress(first).decode())
        for d in outputs["stacked"]:
            self.assertTrue(all(c in self.backend.calls for c in d.call_ids))
            self.assertNotIn(d.request_hash, self.backend.calls)


if __name__ == "__main__":
    unittest.main()
