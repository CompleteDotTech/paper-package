"""Regression tests intentionally include false premises and unsupported inputs."""
from __future__ import annotations
import copy
import json
import math
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from graph_synthesis.certificates import risk, lineage, graphs


def row(group='g', label='SUPPORTS', gold='SUPPORTS', split='development'):
    return {'group': group, 'split': split, 'gold': gold, 'views': {'base1': {'label': label}}}


class RiskTests(unittest.TestCase):
    def test_probability_boundaries(self):
        for rho in risk.RHO_GRID:
            self.assertEqual(risk.contamination(0, .3, rho), 0)
            self.assertEqual(risk.contamination(4, 0, rho), 0)
            self.assertEqual(risk.contamination(4, 1, rho), 1)

    def test_singletons_do_not_identify_dependence(self):
        for rho in risk.RHO_GRID:
            self.assertAlmostEqual(risk.contamination(1, .17, rho), .17, places=12)

    def test_positive_correlation_lowers_any_error_at_fixed_mean(self):
        for n in (2, 4, 10):
            values = [risk.contamination(n, .2, r) for r in risk.RHO_GRID]
            self.assertTrue(all(b <= a + 1e-12 for a, b in zip(values, values[1:])))

    def test_beta_binomial_mass_normalizes(self):
        for rho in risk.RHO_GRID:
            self.assertAlmostEqual(sum(math.exp(risk.log_mass(k, 7, .2, rho)) for k in range(8)), 1, places=12)

    def test_development_only_fit(self):
        with self.assertRaises(ValueError):
            risk.fit([row(split='test')])
        with self.assertRaises(ValueError):
            risk.fit([])

    def test_gold_not_read_for_forecast(self):
        class Blind(dict):
            def __getitem__(self, key):
                if key == 'gold':
                    raise AssertionError('Gold was read')
                return super().__getitem__(key)
        exposure = risk.counts([Blind(row()), Blind(row(label='ERROR'))])
        self.assertEqual(exposure, {'g': 1})
        self.assertEqual(set(risk.predict(exposure, {'mu': .2, 'rho': .1})), {'g'})

    def test_fit_order_invariance_and_no_mutation(self):
        data = [row('a'), row('a', gold='REFUTES'), row('b')]
        old = copy.deepcopy(data)
        self.assertEqual(risk.fit(data), risk.fit(list(reversed(data))))
        self.assertEqual(data, old)

    def test_invalid_parameters(self):
        for args in ((-1, .2, .1), (True, .2, .1), (2, float('nan'), .1), (2, .2, 1), (2, -1, 0)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                risk.contamination(*args)


class LineageTests(unittest.TestCase):
    def test_unknown_dependence_prevents_false_admission(self):
        result = lineage.bounds([['a'], ['b']], {'a': .8, 'b': .8})
        self.assertAlmostEqual(result['lower'], .8, places=8)
        self.assertAlmostEqual(result['upper'], 1, places=8)
        self.assertLess(result['lower'], .95)
        self.assertGreater(1 - .2**2, .95)

    def test_shared_source_constraint(self):
        result = lineage.bounds([['a'], ['b']], {'a': .8, 'b': .8}, [(['a', 'b'], .8)])
        self.assertAlmostEqual(result['lower'], .8, places=8)
        self.assertAlmostEqual(result['upper'], .8, places=8)

    def test_independent_pair_information_recovers_admission(self):
        result = lineage.bounds([['a'], ['b']], {'a': .8, 'b': .8}, [(['a', 'b'], .64)])
        self.assertGreaterEqual(result['lower'], .95)
        self.assertAlmostEqual(result['upper'], .96, places=8)

    def test_impossible_constraints_stage(self):
        result = lineage.bounds([['a']], {'a': .8}, [(['a'], .7)])
        self.assertFalse(result['certified'])
        self.assertEqual(result['status'], 'infeasible_constraints')
        self.assertEqual((result['lower'], result['upper']), (0, 1))

    def test_capacity_stages(self):
        result = lineage.bounds([['a0']], {f'a{i}': .5 for i in range(11)})
        self.assertFalse(result['certified'])
        self.assertEqual(result['status'], 'capacity_staged')

    def test_duplicate_and_order_invariance(self):
        proofs, p = [['a', 'b'], ['b', 'c']], {'a': .7, 'b': .8, 'c': .9}
        one = lineage.bounds(proofs, p)
        for copies in (1, 2, 5, 20):
            two = lineage.bounds(list(reversed(proofs)) * copies, p)
            self.assertEqual(one, two)

    def test_empty_formula_and_tautology(self):
        false = lineage.bounds([], {})
        true = lineage.bounds([[]], {})
        self.assertLess(false['upper'], 1e-8)
        self.assertGreater(true['lower'], 1 - 1e-8)

    def test_nonfinite_invalid_and_missing_atoms(self):
        for p in ({'a': float('nan')}, {'a': float('inf')}, {'a': -1}, {'a': True}):
            with self.assertRaises(ValueError):
                lineage.bounds([['a']], p)
        with self.assertRaises(ValueError):
            lineage.bounds([['missing']], {'a': .8})

    def test_solver_failure_never_admits(self):
        class Failed:
            success, status = False, 4
        with patch('graph_synthesis.certificates.lineage.linprog', return_value=Failed()):
            result = lineage.bounds([['a']], {'a': 1})
        self.assertFalse(result['certified'])
        self.assertEqual(result['lower'], 0)

    def test_dual_witness_bounds_primal(self):
        r = lineage.bounds([['a', 'b'], ['c']], {'a': .7, 'b': .8, 'c': .2})
        for side in ('min', 'max'):
            self.assertLessEqual(r[side]['dual_lower'], r[side]['signed_primal'] + 1e-10)
            self.assertLessEqual(r[side]['residual'], 1e-7)


class GraphTests(unittest.TestCase):
    def test_weighted_complete_bipartite(self):
        w = {**{f'l{i}': 3 for i in range(16)}, **{f'r{i}': 2 for i in range(16)}}
        e = [(f'l{i}', f'r{j}') for i in range(16) for j in range(16)]
        result = graphs.solve(w, e)
        self.assertEqual(result['utility'], 48)
        self.assertFalse(result['staged'])
        self.assertTrue(graphs.verify_flow(w, e, result['components'][0]))

    def test_tampered_flow_rejected(self):
        w, e = {'a': 3, 'b': 2}, [('a', 'b')]
        result = graphs.solve(w, e)['components'][0]
        bad = copy.deepcopy(result)
        bad['certificate']['arcs'][0][3] += 100
        self.assertFalse(graphs.verify_flow(w, e, bad))
        bad = copy.deepcopy(result)
        bad['utility'] += 1
        self.assertFalse(graphs.verify_flow(w, e, bad))

    def test_zero_priorities_and_isolated_nodes(self):
        r = graphs.solve({'a': 0, 'b': 0, 'c': 5}, [('a', 'b')])
        self.assertEqual(r['utility'], 5)
        self.assertIn('c', r['selected'])
        self.assertFalse(r['staged'])

    def test_empty_graph(self):
        self.assertEqual(graphs.solve({}, []), {'selected': [], 'staged': [], 'utility': 0, 'components': []})

    def test_odd_cycle_uses_existing_solver(self):
        w = {str(i): 1 for i in range(17)}
        e = [(str(i), str((i + 1) % 17)) for i in range(17)]
        r = graphs.solve(w, e)
        self.assertEqual(r['utility'], 8)
        self.assertNotEqual(r['components'][0]['method'], 'bipartite_flow')

    def test_dense_unsupported_is_staged(self):
        w = {str(i): 1 for i in range(17)}
        e = [(str(i), str(j)) for i in range(17) for j in range(i)]
        self.assertEqual(len(graphs.solve(w, e)['staged']), 17)

    def test_order_duplicates_and_input_immutability(self):
        w, e = {'a': 5, 'b': 4, 'c': 0}, [('a', 'b'), ('b', 'c')]
        old = copy.deepcopy((w, e))
        self.assertEqual(graphs.solve(w, e), graphs.solve(dict(reversed(list(w.items()))), list(reversed(e)) * 5))
        self.assertEqual((w, e), old)

    def test_invalid_graph_rejected(self):
        for w, e in (({'a': -1}, []), ({'a': 1}, [('a', 'a')]), ({'a': 1}, [('a', 'z')]), ({'a': True}, [])):
            with self.assertRaises(ValueError):
                graphs.solve(w, e)

    def test_false_priority_is_not_truth(self):
        r = graphs.solve({'false': 9, 'true': 8}, [('false', 'true')])
        self.assertEqual(r['selected'], ['false'])


class QueryTests(unittest.TestCase):
    def test_tie_is_ambiguous_with_witness(self):
        w, e = {'a': 1, 'b': 1}, [('a', 'b')]
        chosen = graphs.solve(w, e)['selected'][0]
        r = graphs.query(w, e, [chosen])
        self.assertEqual(r['classification'], 'ambiguous')
        self.assertNotIn(chosen, r['counterexample'])
        self.assertTrue(r['single_optimum_answer'])

    def test_unique_forced_assertion_is_certain(self):
        self.assertEqual(graphs.query({'a': 2, 'b': 1}, [('a', 'b')], ['a'])['classification'], 'certain')

    def test_conflicting_conjunction_is_impossible(self):
        self.assertEqual(graphs.query({'a': 1, 'b': 1}, [('a', 'b')], ['a', 'b'])['classification'], 'impossible')

    def test_tolerance_weakens_certainty(self):
        w, e = {'a': 20, 'b': 19}, [('a', 'b')]
        self.assertEqual(graphs.query(w, e, ['a'])['classification'], 'certain')
        self.assertEqual(graphs.query(w, e, ['a'], epsilon=1)['classification'], 'ambiguous')

    def test_empty_query_and_zero_weights(self):
        self.assertEqual(graphs.query({}, [], [])['classification'], 'certain')
        self.assertEqual(graphs.query({'a': 0}, [], ['a'])['classification'], 'ambiguous')

    def test_invalid_query_and_unsupported_graph(self):
        with self.assertRaises(ValueError):
            graphs.query({'a': 1}, [], ['missing'])
        with self.assertRaises(ValueError):
            graphs.query({'a': 1}, [], ['a'], epsilon=-1)
        w = {str(i): 1 for i in range(17)}
        e = [(str(i), str(j)) for i in range(17) for j in range(i)]
        self.assertEqual(graphs.query(w, e, ['0'])['classification'], 'unsupported')


class DeltaTests(unittest.TestCase):
    def setUp(self):
        self.w = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        self.e = [('a', 'b'), ('c', 'd')]
        self.engine = graphs.DeltaIndex(self.w, self.e)

    def assert_oracle(self):
        s = self.engine.snapshot()
        expected = graphs.solve(s['weights'], s['edges'])
        self.assertEqual(self.engine.summary(), {k: expected[k] for k in ('selected', 'staged', 'utility')})

    def test_weight_update_and_unaffected_reuse(self):
        before = self.engine._solutions[self.engine._which['c']]
        self.engine.update({'kind': 'weight', 'node': 'a', 'value': 10})
        self.assertIs(before, self.engine._solutions[self.engine._which['c']])
        self.assert_oracle()

    def test_bridge_merge_split_and_vertex_removal(self):
        for cmd in ({'kind': 'insert_edge', 'a': 'b', 'b': 'c'}, {'kind': 'delete_edge', 'a': 'b', 'b': 'c'},
                    {'kind': 'delete_vertex', 'node': 'b'}):
            self.engine.update(cmd)
            self.assert_oracle()

    def test_insert_delete_isolated_vertex(self):
        self.engine.update({'kind': 'insert_vertex', 'node': 'new', 'value': 7})
        self.assert_oracle()
        self.engine.update({'kind': 'delete_vertex', 'node': 'new'})
        self.assert_oracle()

    def test_invalid_commands_preserve_state(self):
        commands = [{'kind': 'weight', 'node': 'a', 'value': -1}, {'kind': 'delete_vertex', 'node': 'missing'},
                    {'kind': 'insert_edge', 'a': 'a', 'b': 'a'}, {'kind': 'insert_edge', 'a': 'a', 'b': 'b'},
                    {'kind': 'delete_edge', 'a': 'a', 'b': 'd'}, {'kind': 'insert_vertex', 'node': 'a', 'value': 3},
                    {'kind': 'weight', 'node': 'a', 'value': 3, 'gold': 'unused'}]
        before = self.engine.snapshot()
        work = self.engine.total_work
        for cmd in commands:
            with self.assertRaises(ValueError):
                self.engine.update(cmd)
            self.assertEqual(before, self.engine.snapshot())
            self.assertEqual(work, self.engine.total_work)

    def test_solver_failure_preserves_state(self):
        before = self.engine.snapshot()
        with patch('graph_synthesis.certificates.graphs.component', side_effect=RuntimeError('injected failure')):
            with self.assertRaises(RuntimeError):
                self.engine.update({'kind': 'weight', 'node': 'a', 'value': 10})
        self.assertEqual(before, self.engine.snapshot())

    def test_snapshot_is_not_mutable_internal_state(self):
        before = self.engine.snapshot()
        altered = self.engine.snapshot()
        altered['weights']['a'] = 999
        altered['edges'].clear()
        altered['selected'].clear()
        self.assertEqual(before, self.engine.snapshot())

    def test_delta_outputs_reconstruct_selection(self):
        selected = set(self.engine.summary()['selected'])
        delta = self.engine.update({'kind': 'weight', 'node': 'a', 'value': 10})
        selected.difference_update(delta['selected_removed'])
        selected.update(delta['selected_added'])
        self.assertEqual(selected, set(self.engine.summary()['selected']))

    def test_full_comparator_same_output_more_local_work(self):
        full = graphs.DeltaIndex(self.w, self.e, rescan_all=True)
        cmd = {'kind': 'weight', 'node': 'a', 'value': 10}
        self.engine.update(cmd)
        full.update(cmd)
        self.assertEqual(self.engine.snapshot(), full.snapshot())
        self.assertLess(sum(self.engine.last_work.values()), sum(full.last_work.values()))


class ArtifactTests(unittest.TestCase):
    def test_result_invariants_when_present(self):
        path = Path(__file__).resolve().parents[1] / 'results.json'
        if not path.exists():
            self.skipTest('Executed artifact is not yet present')
        r = json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(r['fresh_service_calls'], 0)
        self.assertEqual(r['protocol_commit'], 'bc70b76621daca198b3b97eb4f698b17d4c40a0b')
        self.assertFalse(set(r['H1']['fit']['fit_groups']) & set(r['H1']['test_exposures']))
        for h in ('H2', 'H3', 'H4', 'H5'):
            self.assertEqual(r[h]['failures'], 0)
        for fold in r['H1']['leave_group_out']:
            self.assertNotIn(fold['held_group'], fold['fit_groups'])

    def test_manuscript_insertion_is_idempotent(self):
        from graph_synthesis.certificates.report import insert, START, END, ANCHOR
        text = '# Existing\n' + ANCHOR + '\nTail\n'
        first = insert(text, 'New findings')
        self.assertEqual(first, insert(first, 'New findings'))
        self.assertEqual(first.count(START), 1)
        self.assertEqual(first.count(END), 1)
        self.assertIn('Tail', first)
        with self.assertRaises(ValueError):
            insert('No anchor', 'body')


if __name__ == '__main__':
    unittest.main()
