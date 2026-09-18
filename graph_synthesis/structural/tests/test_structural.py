"""Regression tests separate implementation correctness from hypothesis success."""
import copy
import json
import math
from pathlib import Path
import unittest
from graph_synthesis.structural.methods import (
    fit_rank, select_rank, contamination_bounds, robust_review, canonical,
    lineage_probability, feedback_cutset, cutset_independent_set)
from graph_synthesis.structural.run import cycle, cycle_oracle


class RankingTests(unittest.TestCase):
    def setUp(self):
        self.rows = [dict(id='a', group='A', label='SUPPORTS', score=.99, gold='SUPPORTS', split='development'),
                     dict(id='b', group='A', label='SUPPORTS', score=.95, gold='REFUTES', split='development'),
                     dict(id='c', group='B', label='REFUTES', score=.8, gold='REFUTES', split='development')]
        self.features = [{k: r[k] for k in ('id', 'group', 'label', 'score')} for r in self.rows]

    def test_fit_requires_development(self):
        for rows in ([], [{**self.rows[0], 'split': 'test'}], self.rows + [{**self.rows[0], 'split': 'test'}]):
            with self.assertRaises(ValueError): fit_rank(rows)

    def test_group_total_weight(self):
        fit = fit_rank(self.rows)
        self.assertEqual(sum(x['total_weight'] for x in fit['bins'].values()), 2)
        self.assertAlmostEqual(fit['global_mean'], 2.5/4)
        self.assertEqual(sum(x['total_weight'] for x in fit_rank(self.rows, balanced=False)['bins'].values()), 3)

    def test_fit_all_nonpositive(self):
        fit = fit_rank([{**self.rows[0], 'label': 'NOT_ENOUGH_INFO'}])
        self.assertEqual(fit['global_mean'], .5)
        self.assertEqual(fit['bins'], {})

    def test_no_gold_needed(self):
        self.assertEqual(select_rank(self.features, 2), ['a', 'b'])
        self.assertEqual(len(select_rank(self.features, 2, fit_rank(self.rows))), 2)

    def test_diversity_and_limits(self):
        self.assertEqual(select_rank(self.features, 2, diverse=True), ['a', 'c'])
        self.assertEqual(select_rank(self.features, 0), [])
        self.assertEqual(select_rank(self.features, 99), ['a', 'b', 'c'])

    def test_invalid_budget_and_duplicates(self):
        for k in (-1, True, 1.5):
            with self.assertRaises(ValueError): select_rank(self.features, k)
        with self.assertRaises(ValueError): select_rank(self.features*2, 2)
        with self.assertRaises(ValueError): select_rank(self.features, 2, fit_rank(self.rows), diverse=True)

    def test_bad_scores(self):
        for score in (None, -1, 1.1, float('nan'), float('inf')):
            with self.assertRaises(ValueError): select_rank([{**self.features[0], 'score': score}], 1)

    def test_nonpositive_exclusion(self):
        other = [dict(id='error', group='C', label='OPERATIONAL_ERROR', score=None)]
        self.assertEqual(select_rank(self.features+other, 99), ['a', 'b', 'c'])

    def test_unseen_bin_fallback(self):
        fit = fit_rank([self.rows[0]])
        self.assertEqual(select_rank([self.features[2]], 1, fit), ['c'])

    def test_permutation_and_immutability(self):
        saved = copy.deepcopy(self.rows)
        for diversity in (False, True):
            self.assertEqual(select_rank(self.features, 2, diverse=diversity), select_rank(self.features[::-1], 2, diverse=diversity))
        fit_rank(self.rows)
        self.assertEqual(saved, self.rows)


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.rows = [dict(id='a', group='A', risk=.9), dict(id='b', group='A', risk=.9), dict(id='c', group='B', risk=.2)]

    def test_bounds(self):
        b = contamination_bounds(self.rows, set())
        self.assertAlmostEqual(b['lower'], 1.1)
        self.assertAlmostEqual(b['independent'], 1.19)
        self.assertAlmostEqual(b['upper'], 1.2)

    def test_complementarity(self):
        self.assertEqual(robust_review(self.rows, 2), ['a', 'b'])
        self.assertAlmostEqual(contamination_bounds(self.rows, {'a', 'b'})['upper'], .65)

    def test_bound_order(self):
        for selected in (set(), {'a'}, {'a', 'b'}, {'a', 'b', 'c'}):
            b = contamination_bounds(self.rows, selected)
            self.assertLessEqual(b['lower'], b['independent']+1e-12)
            self.assertLessEqual(b['independent'], b['upper']+1e-12)

    def test_empty_and_full(self):
        self.assertEqual(robust_review([], 10), [])
        self.assertEqual(robust_review(self.rows, 0), [])
        self.assertEqual(robust_review(self.rows, 99), ['a', 'b', 'c'])
        self.assertEqual(contamination_bounds(self.rows, {'a','b','c'}, 1)['upper'], 0)

    def test_validation(self):
        for risk in (-.1, 1.1, float('nan')):
            with self.assertRaises(ValueError): robust_review([{**self.rows[0], 'risk': risk}], 1)
        for budget in (-1, True, 1.5):
            with self.assertRaises(ValueError): robust_review(self.rows, budget)
        with self.assertRaises(ValueError): robust_review(self.rows*2, 1)
        with self.assertRaises(ValueError): robust_review(self.rows, 1, 1.1)

    def test_order_immutability(self):
        before = copy.deepcopy(self.rows)
        self.assertEqual(robust_review(self.rows, 2), robust_review(self.rows[::-1], 2))
        self.assertEqual(self.rows, before)


class LineageTests(unittest.TestCase):
    def test_absorption(self):
        self.assertEqual(canonical([['a','b'],['a'],['a']]), (('a',),))
        self.assertAlmostEqual(lineage_probability([['a','b'],['a']], {'a':.3,'b':.4})['probability'], .3)

    def test_shared_atom(self):
        r = lineage_probability([['a','b'],['b','c']], {'a':.5,'b':.5,'c':.5})
        self.assertEqual(r['status'], 'exact')
        self.assertAlmostEqual(r['probability'], .375)

    def test_deterministic_primitives(self):
        self.assertEqual(lineage_probability([['a']], {'a':0})['probability'], 0)
        self.assertEqual(lineage_probability([['a']], {'a':1})['probability'], 1)
        self.assertEqual(lineage_probability([], {})['probability'], 0)

    def test_state_limit_sound(self):
        r = lineage_probability([['a','b'],['b','c']], {'a':.5,'b':.5,'c':.5}, max_states=1)
        self.assertEqual(r['status'], 'state_limit')
        self.assertIsNone(r['probability'])
        self.assertLessEqual(r['lower'], .375)
        self.assertGreaterEqual(r['upper'], .375)
        self.assertEqual(r['states'], 1)

    def test_input_caps(self):
        probabilities = {str(i): .5 for i in range(257)}
        self.assertEqual(lineage_probability([['0']], probabilities)['status'], 'input_limit')
        self.assertEqual(lineage_probability([['a']]*513, {'a':.5})['status'], 'input_limit')

    def test_validation(self):
        for proofs, ps in ([[]], {'a':.5}), ([['b']], {'a':.5}), ([['a']], {'a':-1}), ([['a']], {'a':float('nan')}):
            with self.assertRaises(ValueError): lineage_probability(proofs, ps)
        for limit in (0, True, 4097):
            with self.assertRaises(ValueError): lineage_probability([['a']], {'a':.5}, max_states=limit)

    def test_duplicates_and_immutability(self):
        proofs, ps = [['a','b'], ['b','c']], {'a':.3,'b':.4,'c':.5}
        before = copy.deepcopy((proofs, ps))
        r = lineage_probability(proofs, ps)
        self.assertEqual(r['probability'], lineage_probability(proofs[::-1]*20, ps)['probability'])
        self.assertEqual((proofs, ps), before)

    def test_false_independence_control(self):
        r = lineage_probability([['a'], ['alias_a']], {'a':.9,'alias_a':.9})
        self.assertAlmostEqual(r['probability'], .99)
        self.assertGreater(r['probability'], .9)  # true aliases violate the supplied independent-atom assumption


class ConflictTests(unittest.TestCase):
    def test_empty_and_forest(self):
        self.assertEqual(cutset_independent_set({}, {})['utility'], 0)
        graph = {'a':{'b'}, 'b':{'a','c'}, 'c':{'b'}}
        self.assertEqual(feedback_cutset(graph), [])
        self.assertEqual(cutset_independent_set(graph, {'a':2,'b':3,'c':2})['selected'], ['a','c'])

    def test_large_cycle(self):
        for n in (17, 32, 256):
            for weighted in (False, True):
                graph, weights = cycle(n, weighted)
                r = cutset_independent_set(graph, weights)
                self.assertEqual(r['utility'], cycle_oracle(weights))
                self.assertEqual(r['staged'], [])
                self.assertEqual(len(r['routes'][0]['cutset']), 1)

    def test_caps(self):
        graph, weights = cycle(257)
        self.assertEqual(len(cutset_independent_set(graph, weights)['staged']), 257)
        graph = {str(i): {str(j) for j in range(17) if i!=j} for i in range(17)}
        self.assertIsNone(feedback_cutset(graph))
        self.assertEqual(len(cutset_independent_set(graph, {v:1 for v in graph})['staged']), 17)

    def test_small_clique_fallback(self):
        graph = {str(i): {str(j) for j in range(8) if i!=j} for i in range(8)}
        r = cutset_independent_set(graph, {v:1 for v in graph})
        self.assertEqual(r['utility'], 1)
        self.assertEqual(r['staged'], [])

    def test_validation(self):
        for graph, weights in [({'a':{'a'}}, {'a':1}), ({'a':{'b'},'b':set()}, {'a':1,'b':2}), ({'a':set()}, {'a':-1})]:
            with self.assertRaises(ValueError): cutset_independent_set(graph, weights)

    def test_order_and_no_mutation(self):
        graph, weights = cycle(17, True)
        before = copy.deepcopy((graph, weights))
        result = cutset_independent_set(graph, weights)
        self.assertEqual(result, cutset_independent_set(dict(reversed(list(graph.items()))), weights))
        self.assertEqual((graph, weights), before)

    def test_semantics_not_utility(self):
        r = cutset_independent_set({'false':{'true'}, 'true':{'false'}}, {'false':9, 'true':8})
        self.assertEqual(r['selected'], ['false'])


class EvidenceTests(unittest.TestCase):
    def test_frozen_outcomes_and_oracles(self):
        path = Path(__file__).resolve().parents[1]/'results.json'
        r = json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual([r[f'H{i}']['primary_target_met'] for i in range(1,6)], [False,False,False,True,True])
        self.assertEqual(r['fresh_service_calls'], 0)
        self.assertEqual(r['test'], {'n':263,'groups':149})
        self.assertEqual(r['H3']['oracle_failures']+r['H3']['bound_failures']+r['H4']['oracle_failures']+r['H5']['oracle_failures'], 0)
        self.assertGreater(r['H4']['corrupt_lineage_control']['reported']['probability'], r['H4']['corrupt_lineage_control']['true_probability'])

if __name__ == '__main__':
    unittest.main()
