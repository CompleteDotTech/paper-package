import copy
import csv
import io
import json
import random
import unittest
from pathlib import Path
from unittest.mock import patch

from graph_synthesis.post_certificate import methods, report, run


class CorrectionTests(unittest.TestCase):
    def test_overwidth_scope_stages_before_any_table_allocation(self):
        with patch.object(methods, 'product', side_effect=AssertionError('table allocated')):
            result = methods.max_sum_elimination([1] * 30, [tuple(range(30))])
        self.assertEqual(result.status, 'staged')
        self.assertEqual(result.factor_states, 0)

    def test_input_allocation_budget_stages_before_any_table_allocation(self):
        with patch.object(methods, 'product', side_effect=AssertionError('table allocated')):
            result = methods.max_sum_elimination([1] * 6, [(0, 1, 2, 3, 4)], state_cap=20)
        self.assertEqual(result.status, 'staged')

    def test_long_graph_reports_actual_width(self):
        result = methods.max_sum_elimination([1] * 65, [(i, i + 2) for i in range(63)], width_cap=1)
        self.assertEqual(result.status, 'solved')
        self.assertEqual(result.induced_width, 1)
        self.assertEqual(result.objective, 33)

    def test_min_fill_matches_independent_full_rescoring(self):
        rng = random.Random(719)
        for _ in range(30):
            n = 9
            edges = [(i, j) for i in range(n) for j in range(i + 1, n) if rng.random() < .3]
            graph = {i: set() for i in range(n)}
            for a, b in edges:
                graph[a].add(b); graph[b].add(a)
            expected = []; width = 0
            while graph:
                scores = {}
                for v, neighbors in graph.items():
                    missing = sum(b not in graph[a] for a in neighbors for b in neighbors if a < b)
                    scores[v] = missing, len(neighbors), v
                v = min(scores, key=scores.get)
                neighbors = graph.pop(v)
                width = max(width, len(neighbors)); expected.append(v)
                for a in neighbors:
                    graph[a].discard(v); graph[a].update(neighbors - {a})
            actual = methods.min_fill_order(n, [methods.Factor(edge, {}) for edge in edges])
            self.assertEqual(actual, (expected, width))

    def test_independent_chain_recurrence_matches_weighted_exhaustive_oracle(self):
        weights = [3, 1, 4, 9, 2, 6, 5]
        edges = [(i, j) for i in range(len(weights)) for j in range(i + 1, min(i + 3, len(weights)))]
        expected, _ = methods.brute_force_optimum(weights, edges)
        self.assertEqual(run.triangle_chain_oracle(weights), expected)

    def test_dag_order_does_not_depend_on_node_identifiers(self):
        graph = methods.DependencyGraph(1, {1: ('and', (4,)), 4: ('and', (0,))})
        old = graph.full_recompute({0: False})
        values, revision, _ = graph.transact(old, 0, {0: True}, expected_revision=0)
        self.assertEqual(values, {0: True, 1: True, 4: True})
        self.assertEqual(revision, 1)
        self.assertEqual(old, {0: False, 1: False, 4: False})

    def test_invalid_dag_rejected(self):
        for definitions in ({1: ('and', (2,)), 2: ('and', (1,))}, {1: ('and', (5,))}):
            with self.subTest(definitions=definitions), self.assertRaises(ValueError):
                methods.DependencyGraph(1, definitions)

    def test_atomicity_benchmark_fails_if_expected_exceptions_are_suppressed(self):
        original = methods.DependencyGraph.transact
        def broken(graph, values, revision, changes, **kwargs):
            if (kwargs.get('fail_node') is not None or kwargs['expected_revision'] != revision
                    or any(k >= graph.primitive_count for k in changes)):
                return dict(values), revision, 0
            return original(graph, values, revision, changes, **kwargs)
        with patch.object(methods.DependencyGraph, 'transact', broken):
            result = run.h2(random.Random(run.SEED))
        self.assertFalse(result['primary_target_met'])
        self.assertEqual(result['failure_atomic_controls'], 0)
        self.assertEqual(result['stale_revision_controls'], 0)
        self.assertEqual(result['malformed_controls'], 0)

    def test_interior_counterexample_is_retained_as_negative_evidence(self):
        result = run.interval_interior_counterexample()
        self.assertFalse(result['continuous_interval_claim_supported'])
        self.assertAlmostEqual(result['endpoint_worst'], .09)
        self.assertAlmostEqual(result['interior_loss'], .25)
        self.assertAlmostEqual(result['alternative_continuous_worst'], .24)
        self.assertGreater(result['interior_loss'], result['alternative_continuous_worst'])

    def test_failed_targets_remain_failed_in_every_summary(self):
        result = json.loads(Path(run.OUT).read_text(encoding='utf-8'))
        result = copy.deepcopy(result)
        result['H4']['interior_counterexample'] = run.interval_interior_counterexample()
        for i in range(1, 6):
            result[f'H{i}']['primary_target_met'] = False
        generated = report.generated(result)
        rows = list(csv.DictReader(io.StringIO(generated['summary.csv'])))
        self.assertTrue(all(row['result'] == 'not met' and None not in row for row in rows))
        for name in ('RESULTS.md', 'PAPER_SECTION.md', 'CURRENT_SNIPPET.md'):
            for i in range(1, 6):
                self.assertIn(f'H{i}: not met', generated[name])
            self.assertNotIn('All five', generated[name])
        self.assertIn('endpoint', generated['figures/04_interval_review.svg'].lower())


if __name__ == '__main__':
    unittest.main()
