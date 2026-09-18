"""Behavioral controls for the bounded E5/E7/E8 mechanisms."""

import json
import math
import unittest
from dataclasses import replace
from itertools import permutations

from pgc.research.advanced_experiments import (
    _dependency_episodes, _risk_selection, paired_bootstrap, routing_experiment,
)
from pgc.research.policies import (
    DevelopmentOutcome, EvidenceScore, QueryContext, ValueOfInformationRouter,
    aggregate_evidence, dependency_risk, exact_identity_clustering,
    greedy_identity_clustering, identity_pairs, pairwise_metrics, select_queries,
)


class EvidenceDependenceTests(unittest.TestCase):
    def setUp(self):
        self.support = EvidenceScore("s1", "g1", "study one supports", 2)

    def test_exact_copies_do_not_increase_confidence_even_if_relabelled(self):
        baseline = aggregate_evidence([self.support])["probability"]
        for count in (2, 5, 10):
            self.assertEqual(aggregate_evidence([self.support] * count)["probability"], baseline)
        relabelled = replace(self.support, source_id="mirror", group_id="mirror-group")
        self.assertEqual(aggregate_evidence([self.support, relabelled])["probability"], baseline)
        self.assertGreater(aggregate_evidence([self.support] * 5, mode="naive")["probability"], baseline)

    def test_independent_evidence_has_directional_effect(self):
        baseline = aggregate_evidence([self.support])["probability"]
        corroboration = EvidenceScore("s2", "g2", "separate replication", 2)
        contradiction = EvidenceScore("s3", "g3", "separate contradiction", -3)
        self.assertGreater(aggregate_evidence([self.support, corroboration])["probability"], baseline)
        self.assertLess(aggregate_evidence([self.support, contradiction])["probability"], 0.5)

    def test_origin_group_and_duplicate_detection_are_order_invariant(self):
        derivative = EvidenceScore("s2", "g1", "same underlying experiment", 2)
        mirror = replace(self.support, source_id="s3", group_id="g2")
        contrary = EvidenceScore("s4", "g2", "contrary finding in derivative", -1)
        values = [aggregate_evidence(items) for items in permutations([self.support, derivative, mirror, contrary])]
        self.assertTrue(all(value == values[0] for value in values))
        self.assertEqual(values[0]["source_groups"], 1)
        self.assertEqual(values[0]["unique_items"], 3)
        self.assertEqual(values[0]["log_odds"], 1)

    def test_conflicting_copy_scores_and_nonfinite_evidence_are_rejected(self):
        with self.assertRaises(ValueError):
            aggregate_evidence([self.support, replace(self.support, log_likelihood_ratio=-2)])
        with self.assertRaises(ValueError):
            aggregate_evidence([replace(self.support, log_likelihood_ratio=float("nan"))])


class IdentityClusteringTests(unittest.TestCase):
    def setUp(self):
        self.nodes = ("a", "b", "c")
        self.scores = {("a", "b"): 0.9, ("b", "c"): 0.9, ("a", "c"): 0.01}

    def test_joint_retains_strong_negative_edge_ignored_by_union_find(self):
        union = identity_pairs(greedy_identity_clustering(self.nodes, self.scores))
        joint = exact_identity_clustering(self.nodes, self.scores)
        selected = identity_pairs(joint["partition"])
        self.assertIn(("a", "c"), union)
        self.assertNotIn(("a", "c"), selected)
        self.assertEqual(len(selected), 1)
        self.assertEqual(joint["partitions_searched"], 5)
        independent = {pair for pair, score in self.scores.items() if score >= 0.5}
        self.assertEqual(pairwise_metrics(self.nodes, independent, selected)["transitivity_violations"], 1)
        self.assertEqual(pairwise_metrics(self.nodes, selected, selected)["transitivity_violations"], 0)

    def test_transitive_positive_rules_can_be_infeasible(self):
        result = exact_identity_clustering(self.nodes, self.scores,
                    must_link=(("a", "b"), ("b", "c")), cannot_link=(("a", "c"),))
        self.assertFalse(result["feasible"])
        self.assertIsNone(result["partition"])
        self.assertIsNone(result["objective"])
        json.dumps(result, allow_nan=False)

    def test_hard_rules_override_scores_but_can_reduce_semantic_f1(self):
        scores = {pair: 0.99 for pair in self.scores}
        truth = set(scores)
        result = exact_identity_clustering(self.nodes, scores, cannot_link=(("a", "b"),))
        selected = identity_pairs(result["partition"])
        metrics = pairwise_metrics(self.nodes, selected, truth, (("a", "b"),))
        self.assertEqual(metrics["hard_constraint_violations"], 0)
        self.assertLess(metrics["pairwise_f1"], 1)

    def test_complete_score_table_and_bounded_solver_are_required(self):
        with self.assertRaises(ValueError):
            exact_identity_clustering(self.nodes, {("a", "b"): 0.9})
        with self.assertRaises(ValueError):
            exact_identity_clustering(tuple("abcdefghi"), {})
        with self.assertRaises(ValueError):
            exact_identity_clustering(self.nodes, {**self.scores, ("b", "a"): 0.9})


class DependencyRiskTests(unittest.TestCase):
    def test_disjoint_failures_refute_the_product_as_a_bound(self):
        correctness = {"subject": 0.9, "support": 0.9}
        true_disjoint_failure_risk = 0.2
        self.assertAlmostEqual(dependency_risk(correctness, correctness, "union"), true_disjoint_failure_risk)
        self.assertLess(dependency_risk(correctness, correctness, "product"), true_disjoint_failure_risk)
        self.assertLess(dependency_risk(correctness, correctness, "single", primary="support"), true_disjoint_failure_risk)

    def test_shared_dependencies_are_counted_once_and_missing_ones_fail(self):
        correctness = {"shared": 0.95, "a": 0.98, "b": 0.97}
        self.assertAlmostEqual(dependency_risk(correctness, ["shared", "a", "shared", "b"]), 0.1)
        with self.assertRaises(ValueError):
            dependency_risk(correctness, ["unknown"])
        with self.assertRaises(ValueError):
            dependency_risk({"x": math.inf}, ["x"])

    def test_bound_holds_for_all_controlled_couplings(self):
        for coupling in ("independent", "positive_shared_noise", "maximally_disjoint_failures"):
            for sharing in (False, True):
                episodes = _dependency_episodes(17, 100, coupling, sharing)
                self.assertTrue(all(item["true_risk"] <= item["estimates"]["union"] + 1e-12 for item in episodes))
                if coupling == "maximally_disjoint_failures":
                    self.assertTrue(all(item["true_risk"] > item["estimates"]["product"] for item in episodes))

    def test_risk_comparisons_match_accepted_episodes_and_mutations(self):
        episodes = _dependency_episodes(19, 101, "independent", False)
        for coverage in (0.25, 0.5, 0.75, 1.0):
            selections = [_risk_selection(episodes, policy, coverage) for policy in ("single", "product", "union")]
            self.assertTrue(all(len(selection) == int(101 * coverage) for selection in selections))
            mutation_counts = [sum(episodes[i]["mutation_count"] for i in selection) for selection in selections]
            self.assertEqual(len(set(mutation_counts)), 1)


class RoutingTests(unittest.TestCase):
    def test_router_learns_query_value_on_development_only(self):
        useful = QueryContext(0.7, "useful", 10)
        harmful = QueryContext(0.7, "harmful", 10)
        development = ([DevelopmentOutcome(useful, False, True)] * 30 +
                       [DevelopmentOutcome(harmful, True, False)] * 30)
        router = ValueOfInformationRouter().fit(development)
        self.assertEqual(select_queries([harmful, useful], 1, "voi", router=router), {1})
        self.assertLess(router.score(harmful), 0)
        self.assertGreater(router.score(useful), 0)
        self.assertNotIn("baseline_correct", useful.__dataclass_fields__)
        self.assertNotIn("queried_correct", useful.__dataclass_fields__)

    def test_query_budget_is_exact_even_for_negative_value(self):
        context = QueryContext(0.95, "bad", 1)
        router = ValueOfInformationRouter().fit([DevelopmentOutcome(context, True, False)])
        for policy in ("random", "confidence", "impact", "voi"):
            self.assertEqual(len(select_queries([context] * 10, 3, policy, seed=4, router=router)), 3)
        with self.assertRaises(ValueError):
            select_queries([context, replace(context, query_cost=2)], 1, "random")

    def test_zero_and_all_queries_have_identical_outcomes_across_policies(self):
        result = routing_experiment(13, 20, 100)
        for condition in result["conditions"].values():
            self.assertNotEqual(condition["development"]["seed"], condition["evaluation"]["seed"])
            self.assertNotEqual(condition["development"]["episode_ids_sha256"],
                                condition["evaluation"]["episode_ids_sha256"])
            for budget in ("0", "20"):
                tables = list(condition["budgets"][budget]["table"].values())
                self.assertTrue(all(table == tables[0] for table in tables))

    def test_paired_bootstrap_uses_episode_differences(self):
        result = paired_bootstrap([2, 5, 9], [1, 4, 8], seed=1, resamples=100)
        self.assertEqual(result["mean_difference"], 1)
        self.assertEqual(result["ci95"], [1, 1])
        self.assertEqual(result["independent_episode_count"], 3)


if __name__ == "__main__":
    unittest.main()
