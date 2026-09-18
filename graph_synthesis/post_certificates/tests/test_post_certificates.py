"""Regression and adversarial tests for the post-certificate suite."""
from __future__ import annotations

import unittest

from graph_synthesis.post_certificates import methods
from graph_synthesis.certificates import graphs


class IntervalMarginalTests(unittest.TestCase):
    def test_point_singleton_is_exact_up_to_padding(self):
        result = methods.exact_point_bounds([["a"]], {"a": .8})
        self.assertTrue(result["certified"])
        self.assertLessEqual(result["lower"], .8)
        self.assertGreaterEqual(result["upper"], .8)
        self.assertLess(result["upper"] - result["lower"], 1e-5)
        self.assertIn("dual_lower", result["min"])
        self.assertIn("dual_lower", result["max"])
        self.assertLessEqual(result["min"]["dual_lower"], result["min"]["signed_primal"] + 1e-9)
        self.assertLessEqual(result["max"]["dual_lower"], result["max"]["signed_primal"] + 1e-9)

    def test_interval_singleton_tracks_uncertainty(self):
        result = methods.interval_lineage_bounds([["a"]], {"a": [.7, .9]})
        self.assertTrue(result["certified"])
        self.assertLessEqual(result["lower"], .700001)
        self.assertGreaterEqual(result["upper"], .899999)

    def test_bad_intervals_fail_closed(self):
        bad = (
            {"a": [.9, .8]},
            {"a": [-.1, .8]},
            {"a": [.1, 1.1]},
            {"a": [float("nan"), .8]},
        )
        for intervals in bad:
            with self.subTest(intervals=intervals):
                result = methods.interval_lineage_bounds([["a"]], intervals)
                self.assertFalse(result["certified"])
                self.assertEqual((result["lower"], result["upper"]), (0.0, 1.0))

    def test_unknown_atom_fails_closed(self):
        result = methods.interval_lineage_bounds([["b"]], {"a": [.1, .9]})
        self.assertFalse(result["certified"])


class NearBipartiteTests(unittest.TestCase):
    def test_triangle_solved_with_one_vertex_separator(self):
        weights = {"a": 4, "b": 3, "c": 2}
        edges = [("a", "b"), ("b", "c"), ("c", "a")]
        result = methods.near_bipartite_solve(weights, edges, ["a"])
        self.assertFalse(result["staged"])
        self.assertEqual(result["utility"], 4)
        self.assertEqual(result["selected"], ["a"])

    def test_bad_separator_stages(self):
        weights = {"a": 1, "b": 1, "c": 1}
        edges = [("a", "b"), ("b", "c"), ("c", "a")]
        result = methods.near_bipartite_solve(weights, edges, [])
        self.assertTrue(result["staged"])
        self.assertEqual(result["status"], "not_transversal")

    def test_over_cap_separator_stages(self):
        weights = {str(i): 1 for i in range(6)}
        result = methods.near_bipartite_solve(weights, [], list(weights)[:5])
        self.assertTrue(result["staged"])


class MarginIndexTests(unittest.TestCase):
    def test_matches_existing_singleton_query(self):
        weights = {"a": 2, "b": 2, "c": 1}
        edges = [("a", "b")]
        index = methods.build_margin_index(weights, edges)
        self.assertEqual(index["status"], "indexed")
        for vertex in weights:
            for epsilon in (0, 1, 2):
                with self.subTest(vertex=vertex, epsilon=epsilon):
                    expected = graphs.query(weights, edges, [vertex], epsilon=epsilon)
                    actual = methods.query_margin(index, vertex, epsilon)
                    self.assertEqual(actual["classification"], expected["classification"])

    def test_equal_pair_is_ambiguous(self):
        weights = {"a": 1, "b": 1}
        edges = [("a", "b")]
        index = methods.build_margin_index(weights, edges)
        self.assertEqual(methods.query_margin(index, "a", 0)["classification"], "ambiguous")

    def test_dominant_vertex_is_certain(self):
        weights = {"a": 2, "b": 1}
        edges = [("a", "b")]
        index = methods.build_margin_index(weights, edges)
        self.assertEqual(methods.query_margin(index, "a", 0)["classification"], "certain")
        self.assertEqual(methods.query_margin(index, "b", 0)["classification"], "impossible")


if __name__ == "__main__":
    unittest.main()
