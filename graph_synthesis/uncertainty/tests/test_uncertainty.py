"""Contracts, independent oracles, falsifying assumptions and additive reporting."""
from copy import deepcopy
from fractions import Fraction
from itertools import combinations
import math
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from graph_synthesis.uncertainty.methods import (
    credal_bounds, dnf, frechet_bounds, grounded, independent_probability,
    probabilities, query_loss, retraction_plan, review_plan, skeptical_repair,
    support_prune,
)
from graph_synthesis.uncertainty.run import (
    direct_brier, finite_model_oracle, independent_sets_oracle,
    rational_lineage_oracle, retraction_oracle,
)


class LineageTests(unittest.TestCase):
    def test_invalid_probabilities(self):
        for value in (-1, 1.1, math.nan, math.inf, True, '0.5'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                probabilities({'a': value})
        with self.assertRaises(ValueError):
            probabilities({})

    def test_invalid_proofs(self):
        for proof in ([[]], [['unknown']], ['a']):
            with self.subTest(proof=proof), self.assertRaises(ValueError):
                credal_bounds(proof, {'a': .5})

    def test_canonicalization(self):
        self.assertEqual(dnf([['b', 'a'], ['a'], ['a']], ['a', 'b']), (('a',),))
        self.assertEqual(credal_bounds([], {'a': .2})['upper'], 0)

    def test_correlated_control(self):
        proofs = [['a'], ['b']]; p = {'a': .8, 'b': .8}
        self.assertAlmostEqual(independent_probability(proofs, p), .96)
        result = credal_bounds(proofs, p)
        self.assertLess(result['lower'], .95)
        self.assertAlmostEqual(result['lower'], .8, places=7)
        self.assertGreaterEqual(result['upper'], .8)

    def test_rational_extrema(self):
        for proof in ([['a', 'b']], [['a'], ['b']], [['a', 'b'], ['b', 'c']]):
            p = {'a': Fraction(7, 10), 'b': Fraction(4, 10), 'c': Fraction(9, 10)}
            lo, hi = rational_lineage_oracle(proof, p)
            result = credal_bounds(proof, {a: float(x) for a, x in p.items()})
            self.assertAlmostEqual(result['raw_lower'], lo)
            self.assertAlmostEqual(result['raw_upper'], hi)

    def test_solver_status_fallback(self):
        with patch('scipy.optimize.linprog', return_value=SimpleNamespace(success=False)):
            result = credal_bounds([['a'], ['b']], {'a': .8, 'b': .8})
        self.assertEqual(result['reason'], 'solver-status')
        self.assertEqual(result['mode'], 'analytic-dependence-free')

    def test_solver_exception_fallback(self):
        with patch('scipy.optimize.linprog', side_effect=RuntimeError('controlled failure')):
            result = credal_bounds([['a', 'b']], {'a': .8, 'b': .8})
        self.assertEqual(result['reason'], 'solver-exception')
        self.assertAlmostEqual(result['lower'], .6)

    def test_cap_and_unused_atoms(self):
        p = {f'a{i}': .8 for i in range(9)}
        result = credal_bounds([[a] for a in p], p)
        self.assertEqual(result['reason'], 'atom-cap')
        self.assertEqual(credal_bounds([['a0']], p)['mode'], 'numerical-LP')

    def test_wrong_marginal_is_not_corrected(self):
        self.assertGreater(credal_bounds([['a']], {'a': .99})['lower'], .5)


class RepairTests(unittest.TestCase):
    def test_tie_and_isolated_backbone(self):
        result = skeptical_repair({'a': 5, 'b': 5, 'c': 2}, [('a', 'b')])
        self.assertEqual(result['necessary'], ['c'])
        self.assertEqual(result['possible'], ['a', 'b', 'c'])
        self.assertEqual(result['witnesses']['a']['include'], ['a', 'c'])
        self.assertEqual(result['witnesses']['a']['exclude'], ['b', 'c'])

    def test_all_small_unweighted_graphs(self):
        nodes = ['a', 'b', 'c', 'd']; edges = list(combinations(nodes, 2))
        for mask in range(1 << len(edges)):
            chosen = [edge for i, edge in enumerate(edges) if mask & (1 << i)]
            weights = {a: 1 for a in nodes}; best, optima = independent_sets_oracle(weights, chosen)
            result = skeptical_repair(weights, chosen)
            self.assertEqual(result['utility'], best)
            self.assertEqual(result['necessary'], sorted(set.intersection(*optima)))
            self.assertEqual(result['possible'], sorted(set.union(*optima)))

    def test_zero_priority_is_optional(self):
        result = skeptical_repair({'a': 0}, [])
        self.assertEqual(result['necessary'], [])
        self.assertEqual(result['possible'], ['a'])
        self.assertEqual(result['selected'], [])

    def test_invalid_graph(self):
        for weights, edges in (({'a': -1}, []), ({'a': True}, []), ({'a': 1}, [('a', 'a')]),
                               ({'a': 1}, [('a', 'b')]), ({'a': 1}, ['a'])):
            with self.subTest(weights=weights, edges=edges), self.assertRaises(ValueError):
                skeptical_repair(weights, edges)

    def test_large_component_is_explicitly_partial(self):
        weights = {f'a{i}': 1 for i in range(17)}; weights['isolated'] = 2
        edges = [(f'a{i}', f'a{(i+1)%17}') for i in range(17)]
        result = skeptical_repair(weights, edges)
        self.assertIsNone(result['utility'])
        self.assertEqual(len(result['staged']), 17)
        self.assertEqual(result['necessary'], ['isolated'])

    def test_unique_false_priority_control(self):
        result = skeptical_repair({'false': 9, 'true': 8}, [('false', 'true')])
        self.assertEqual(result['necessary'], ['false'])


class ReviewTests(unittest.TestCase):
    def test_direct_brier_and_monotonicity(self):
        p = {'a': .4, 'b': .7, 'c': .9}; queries = [[['a', 'b'], ['c']], [['b']]]
        losses = []
        for k in range(4):
            result = review_plan(queries, p, k)
            losses.append(result['loss'])
            self.assertAlmostEqual(result['loss'], direct_brier(queries, p, result['reviewed']))
        self.assertTrue(all(a+1e-12 >= b for a, b in zip(losses, losses[1:])))
        self.assertAlmostEqual(losses[-1], 0)

    def test_irrelevant_high_risk_atom(self):
        result = review_plan([[['important']]], {'important': .5, 'irrelevant': .01}, 1)
        self.assertEqual(result['reviewed'], ['important'])
        self.assertAlmostEqual(result['loss'], 0)

    def test_degenerate_probabilities(self):
        self.assertAlmostEqual(query_loss([[['a']], [['b']]], {'a': 0., 'b': 1.}, []), 0)

    def test_invalid_budgets(self):
        for budget in (-1, 2, True, .5):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                review_plan([[['a']]], {'a': .5}, budget)
        with self.assertRaises(ValueError):
            query_loss([[['a']]], {'a': .5}, ['unknown'])

    def test_misspecification_counterexample(self):
        q = [[['a']], [['a']], [['b']]]; p = {'a': .9, 'b': .05}; actual = {'a': .9, 'b': .5}
        proposed = review_plan(q, p, 1)['reviewed']
        self.assertGreater(direct_brier(q, p, proposed, actual), direct_brier(q, p, ['b'], actual))


class RetractionTests(unittest.TestCase):
    def setUp(self):
        self.facts = {'target': [['a', 'b'], ['a', 'c']], 'protected': [['b']], 'other': [['c']]}
        self.costs = {'a': 2, 'b': 1, 'c': 1}

    def test_exact_plan_and_no_mutation(self):
        before = deepcopy((self.facts, self.costs))
        result = retraction_plan(self.facts, 'target', ['protected'], self.costs)
        self.assertEqual(result['removed'], ['a'])
        self.assertEqual(result['collateral'], 0)
        self.assertEqual((self.facts, self.costs), before)
        oracle = retraction_oracle(self.facts, 'target', ['protected'], self.costs)
        self.assertEqual(result['removed'], oracle[1])

    def test_impossible_protection(self):
        result = retraction_plan({'t': [['a']], 'p': [['a']]}, 't', ['p'], {'a': 1})
        self.assertEqual(result['status'], 'infeasible')
        self.assertIsNone(result['removed'])

    def test_cap(self):
        costs = {f'a{i}': 1 for i in range(15)}
        result = retraction_plan({'t': [['a0']]}, 't', [], costs)
        self.assertEqual(result['status'], 'staged-cap')

    def test_invalid_retraction_inputs(self):
        for costs in ({'a': 0}, {'a': -1}, {'a': True}):
            with self.subTest(costs=costs), self.assertRaises(ValueError):
                retraction_plan({'t': [['a']]}, 't', [], costs)
        with self.assertRaises(ValueError):
            retraction_plan({'t': []}, 't', [], {'a': 1})
        with self.assertRaises(ValueError):
            retraction_plan({'t': [['a']]}, 'missing', [], {'a': 1})

    def test_missing_proof_control(self):
        plan = retraction_plan({'t': [['a']]}, 't', [], {'a': 1, 'b': 1})
        self.assertEqual(plan['removed'], ['a'])
        self.assertNotIn('b', plan['removed'])  # Undisclosed proof b survives.


class GroundingTests(unittest.TestCase):
    def test_withdrawn_cycle_and_backup(self):
        rules = [('a', ['seed']), ('b', ['a']), ('a', ['b'])]
        old = grounded(['seed'], rules)['active']
        self.assertEqual(grounded([], rules)['active'], [])
        self.assertEqual(support_prune(old, [], rules), ['a', 'b'])
        self.assertEqual(grounded(['backup'], rules+[('a', ['backup'])])['active'], ['a', 'b', 'backup'])

    def test_conjunctive_body_needs_all_atoms(self):
        rules = [('head', ['a', 'b'])]
        self.assertEqual(grounded(['a'], rules)['active'], ['a'])
        self.assertEqual(grounded(['a', 'b'], rules)['active'], ['a', 'b', 'head'])

    def test_finite_model_oracle(self):
        atoms = ['a', 'b', 'c']; rules = [('b', ['a']), ('c', ['b']), ('a', ['c'])]
        for bases in ([], ['a'], ['b'], ['a', 'c']):
            self.assertEqual(grounded(bases, rules)['active'], finite_model_oracle(bases, rules))

    def test_no_unseeded_self_support(self):
        self.assertEqual(grounded([], [('a', ['a'])])['active'], [])

    def test_invalid_ground_rules(self):
        for rules in ([('a', [])], [('a', 'b')], [('', ['a'])], [('a', [None])]):
            with self.subTest(rules=rules), self.assertRaises(ValueError):
                grounded([], rules)

    def test_rule_duplicate_order_and_work_bound(self):
        rules = [('b', ['a']), ('c', ['b', 'a']), ('a', ['c'])]
        result = grounded(['a'], rules)
        self.assertEqual(result, grounded(['a', 'a'], list(reversed(rules))*5))
        self.assertLessEqual(result['body_visits'], result['body_incidences'])

    def test_false_base_semantic_control(self):
        self.assertEqual(grounded(['false_base'], [('unsupported_in_reality', ['false_base'])])['active'],
                         ['false_base', 'unsupported_in_reality'])


class ReportTests(unittest.TestCase):
    def test_additive_update_is_idempotent(self):
        from graph_synthesis.uncertainty.report import replace_after_anchor, ANCHOR, START, END
        original = 'prior study content\n'+ANCHOR+'\n\nfollowing study content\n'
        updated = replace_after_anchor(original, 'new study content')
        self.assertEqual(updated, replace_after_anchor(updated, 'new study content'))
        self.assertTrue(updated.startswith('prior study content\n'+ANCHOR))
        self.assertTrue(updated.endswith('following study content\n'))
        self.assertEqual(updated.count(START), 1)
        self.assertEqual(updated.count(END), 1)

    def test_missing_or_malformed_anchor_is_rejected(self):
        from graph_synthesis.uncertainty.report import replace_after_anchor, ANCHOR, START
        for text in ('no anchor', ANCHOR+ANCHOR, ANCHOR+START):
            with self.subTest(text=text), self.assertRaises(ValueError):
                replace_after_anchor(text, 'content')


if __name__ == '__main__':
    unittest.main()
