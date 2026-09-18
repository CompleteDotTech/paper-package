from copy import deepcopy
from itertools import combinations, product
import json
import math
import unittest
from unittest.mock import patch

from graph_synthesis.source_structural.methods import (
    group_features, source_truth, fit_source, predict_source, review_options,
    knapsack, budgeted_greedy, frontier_probability, solve_conflicts,
    verify_certificate, LineageCache)
from graph_synthesis.source_structural.run import (HERE, sha, feature_only,
    evaluate_review, chain_fixture, chain_oracle, complete_fixture, grid_fixture,
    full_lineage, independent_set_oracle)


def row(key='a', group='g', label='SUPPORTS', score=.95, gold='SUPPORTS', split='development'):
    return {'id': key, 'group': group, 'split': split, 'gold': gold,
            'views': {'base1': {'label': label, 'score': score}}}


class SourceTests(unittest.TestCase):
    def test_feature_cells(self):
        self.assertEqual(group_features([row(), row('b', score=.5)]), {'g': (1, 1)})
        self.assertEqual(group_features([row()]), {'g': (0, 0)})

    def test_empty_accepted_group_excluded(self):
        self.assertEqual(group_features([row(label='NOT_ENOUGH_INFO')]), {})
        self.assertEqual(source_truth([row(label='NOT_ENOUGH_INFO')]), {})

    def test_any_error_event_not_edge_average(self):
        self.assertEqual(source_truth([row(), row('b', gold='REFUTES')]), {'g': 1})

    def test_missing_score_is_low(self):
        self.assertEqual(group_features([row(score=None)]), {'g': (0, 1)})

    def test_training_split_guard(self):
        with self.assertRaises(ValueError):
            fit_source([row(split='test')], 4)
        with self.assertRaises(ValueError):
            fit_source([], 4)

    def test_alpha_guard(self):
        for alpha in (0, 2, True, 4., 100):
            with self.subTest(alpha=alpha), self.assertRaises(ValueError):
                fit_source([row()], alpha)

    def test_group_shrinkage_formula(self):
        fit = fit_source([row(), row('b', 'g2', gold='REFUTES')], 4)
        self.assertEqual(fit['prior'], .5)
        self.assertEqual(predict_source(feature_only([row()]), fit)['g'], .5)

    def test_gold_forbidden_at_inference(self):
        with self.assertRaises(ValueError):
            predict_source([row()], fit_source([row()], 1))

    def test_unseen_feature_cell_uses_prior(self):
        fit = fit_source([row()], 4)
        self.assertEqual(predict_source(feature_only([row(score=.1)]), fit)['g'], fit['prior'])

    def test_inference_and_fit_do_not_mutate(self):
        rows = [row(), row('b', 'g2', gold='REFUTES')]
        before = deepcopy(rows)
        fit = fit_source(rows, 4)
        predict_source(feature_only(rows), fit)
        self.assertEqual(rows, before)


class ReviewTests(unittest.TestCase):
    def test_setup_charged_once_per_source(self):
        risks = [{'id': 'a', 'group': 'g', 'risk': .3}, {'id': 'b', 'group': 'g', 'risk': .4}]
        options = review_options(risks, 2, .75)['g']
        self.assertEqual([o['cost'] for o in options], [0, 3, 4])
        self.assertEqual(options[1]['ids'], ['b'])
        self.assertAlmostEqual(options[1]['benefit'], .21)

    def test_knapsack_beats_first_choice(self):
        options = {'g': [{'cost': 0, 'benefit': 0., 'ids': []}, {'cost': 3, 'benefit': .4, 'ids': ['a']}],
                   'h': [{'cost': 0, 'benefit': 0., 'ids': []}, {'cost': 2, 'benefit': .3, 'ids': ['b']}, {'cost': 3, 'benefit': .6, 'ids': ['b', 'c']}]}
        self.assertEqual(knapsack(options, 3)['selected'], ['b', 'c'])

    def test_empty_budget(self):
        self.assertEqual(knapsack({}, 0), {'selected': [], 'spent': 0, 'predicted_benefit': 0.})

    def test_no_affordable_review(self):
        risks = [{'id': 'a', 'group': 'g', 'risk': 1.}]
        self.assertEqual(knapsack(review_options(risks, 2, .75), 2)['selected'], [])
        self.assertEqual(budgeted_greedy(risks, 2, 2)['selected'], [])

    def test_tie_prefers_lower_cost(self):
        opts = {'g': [{'cost': 0, 'benefit': 0., 'ids': []}, {'cost': 2, 'benefit': .5, 'ids': ['a']}, {'cost': 1, 'benefit': .5, 'ids': ['b']}]}
        self.assertEqual(knapsack(opts, 2)['selected'], ['b'])

    def test_order_invariance(self):
        rows = [{'id': str(i), 'group': str(i//2), 'risk': .1*i} for i in range(6)]
        self.assertEqual(knapsack(review_options(rows, 2, .75), 8), knapsack(review_options(list(reversed(rows)), 2, .75), 8))
        self.assertEqual(budgeted_greedy(rows, 8, 2), budgeted_greedy(list(reversed(rows)), 8, 2))

    def test_zero_and_one_risks(self):
        rows = [{'id': 'a', 'group': 'g', 'risk': 0.}, {'id': 'b', 'group': 'g', 'risk': 1.}]
        result = knapsack(review_options(rows, 0, 1.), 2)
        self.assertEqual(result['selected'], ['b'])
        self.assertEqual(result['predicted_benefit'], 1.)

    def test_invalid_risks(self):
        for p in (-.1, 1.1, float('nan'), float('inf'), True):
            with self.subTest(p=p), self.assertRaises(ValueError):
                review_options([{'id': 'a', 'group': 'g', 'risk': p}], 2, .75)

    def test_duplicate_candidate_rejected(self):
        candidate = {'id': 'a', 'group': 'g', 'risk': .5}
        with self.assertRaises(ValueError):
            review_options([candidate, candidate], 2, .75)

    def test_cost_contracts(self):
        for cost in (-1, True, 2.5):
            with self.subTest(cost=cost), self.assertRaises(ValueError):
                review_options([], cost, .75)
            with self.subTest(budget=cost), self.assertRaises(ValueError):
                knapsack({}, cost)

    def test_knapsack_no_empty_option_rejected(self):
        with self.assertRaises(ValueError):
            knapsack({'g': [{'cost': 2, 'benefit': .1, 'ids': ['a']}]}, 3)

    def test_correlated_review_control(self):
        rows = [row('a', gold='REFUTES'), row('b', gold='REFUTES')]
        independent = evaluate_review(rows, ['a', 'b'], .75, .01)
        correlated = evaluate_review(rows, ['a', 'b'], .75, .01, True)
        self.assertAlmostEqual(independent['expected_contaminated_groups'], 1-.75**2)
        self.assertAlmostEqual(correlated['expected_contaminated_groups'], .25)

    def test_unreviewed_wrong_edge_cannot_disappear(self):
        rows = [row('a', gold='REFUTES'), row('b', gold='REFUTES')]
        self.assertEqual(evaluate_review(rows, ['a'], 1., 0.)['expected_contaminated_groups'], 1.)

    def test_false_removal_and_no_gold_mutation(self):
        rows = [row()]
        before = deepcopy(rows)
        self.assertAlmostEqual(evaluate_review(rows, ['a'], .75, .01)['expected_correct_retained'], .99)
        self.assertEqual(rows, before)


class FrontierTests(unittest.TestCase):
    def test_constant_false(self):
        self.assertEqual(frontier_probability([], {})['lower'], 0.)

    def test_constant_true(self):
        self.assertEqual(frontier_probability([[]], {})['lower'], 1.)

    def test_boundary_probabilities(self):
        for p in (0., 1.):
            self.assertEqual(frontier_probability([['a']], {'a': p})['lower'], p)

    def test_shared_atom_probability(self):
        r = frontier_probability([['a', 'b'], ['b', 'c']], {'a': .6, 'b': .7, 'c': .8})
        self.assertAlmostEqual(r['lower'], .7*(.6+.8-.6*.8))

    def test_duplicate_and_subsumption(self):
        r = frontier_probability([['a'], ['a'], ['a', 'b']], {'a': .8, 'b': .5})
        self.assertAlmostEqual(r['lower'], .8)

    def test_unknown_primitives(self):
        with self.assertRaises(ValueError):
            frontier_probability([['missing']], {'a': .5})

    def test_invalid_probability(self):
        for value in (float('nan'), float('inf'), -1., 2., True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                frontier_probability([['a']], {'a': value})

    def test_string_is_not_proof(self):
        with self.assertRaises(ValueError):
            frontier_probability(['a'], {'a': .5})

    def test_large_path_and_cycle(self):
        for cycle in (False, True):
            proofs, ps = chain_fixture(256, cycle)
            result = frontier_probability(proofs, ps)
            self.assertTrue(result['exact'])
            self.assertAlmostEqual(result['lower'], chain_oracle(256, cycle=cycle), places=12)

    def test_frontier_cap_delegates(self):
        proofs, ps = chain_fixture(8)
        result = frontier_probability(proofs, ps, width_cap=0)
        self.assertEqual(result['method'], 'previous_fallback')
        self.assertEqual(result['reason'], 'width_cap')
        self.assertAlmostEqual(result['lower'], chain_oracle(8), places=12)

    def test_state_cap_never_certifies_partial_probability(self):
        proofs, ps = chain_fixture(8)
        result = frontier_probability(proofs, ps, state_cap=1)
        self.assertEqual(result['reason'], 'state_cap')
        self.assertAlmostEqual(result['lower'], chain_oracle(8), places=12)

    def test_large_dense_safe_interval(self):
        ps = {f'a{i:03d}': .1 for i in range(17)}
        result = frontier_probability(list(combinations(ps, 2)), ps)
        oracle = 1-.9**17-17*.1*.9**16
        self.assertFalse(result['exact'])
        self.assertLessEqual(result['lower'], oracle)
        self.assertGreaterEqual(result['upper'], oracle)

    def test_input_atom_cap(self):
        proofs, ps = chain_fixture(257)
        self.assertEqual(frontier_probability(proofs, ps)['reason'], 'input_cap')

    def test_unsafe_caps_rejected(self):
        for kwargs in ({'width_cap': 13}, {'width_cap': True}, {'state_cap': 0}, {'state_cap': 65537}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                frontier_probability([], {}, **kwargs)

    def test_false_independence_not_repaired(self):
        shared = frontier_probability([['a'], ['a']], {'a': .8})['lower']
        split = frontier_probability([['a'], ['b']], {'a': .8, 'b': .8})['lower']
        self.assertAlmostEqual(shared, .8)
        self.assertAlmostEqual(split, .96)


class FlowTests(unittest.TestCase):
    def check(self, weights, edges):
        result = solve_conflicts(weights, edges)
        self.assertEqual(result['utility'], independent_set_oracle(weights, edges))
        for part in result['components']:
            if part['method'] == 'bipartite_flow':
                keys = set(part['certificate']['nodes'])
                self.assertTrue(verify_certificate({k: weights[k] for k in keys}, [(a, b) for a, b in edges if a in keys and b in keys], part))
        return result

    def test_empty_graph(self):
        self.assertEqual(solve_conflicts({}, [])['utility'], 0)

    def test_one_conflict(self):
        self.assertEqual(self.check({'a': 9, 'b': 8}, [('a', 'b')])['selected'], ['a'])

    def test_zero_priorities(self):
        self.check({'a': 0, 'b': 0, 'c': 0}, [('a', 'b')])

    def test_all_four_vertex_graphs(self):
        keys = ['a', 'b', 'c', 'd']
        pairs = list(combinations(keys, 2))
        for mask in range(1 << len(pairs)):
            self.check(dict(zip(keys, [0, 2, 3, 5])), [p for i, p in enumerate(pairs) if mask & (1 << i)])

    def test_large_grid_certificate(self):
        w, edges, oracle = grid_fixture(16)
        result = solve_conflicts(w, edges)
        self.assertEqual(result['utility'], oracle)
        self.assertTrue(verify_certificate(w, edges, result['components'][0]))

    def test_large_dense_bipartite_certificate(self):
        w, edges, oracle = complete_fixture(128)
        result = solve_conflicts(w, edges)
        self.assertEqual(result['utility'], oracle)
        self.assertTrue(verify_certificate(w, edges, result['components'][0]))

    def test_nonbipartite_delegation(self):
        result = self.check({'a': 1, 'b': 2, 'c': 3}, [('a', 'b'), ('b', 'c'), ('c', 'a')])
        self.assertNotEqual(result['components'][0]['method'], 'bipartite_flow')

    def test_dense_nonbipartite_stages(self):
        keys = [f'v{i}' for i in range(17)]
        result = solve_conflicts({k: 1 for k in keys}, list(combinations(keys, 2)))
        self.assertEqual(len(result['staged']), 17)

    def test_component_size_cap(self):
        keys = [f'v{i:03d}' for i in range(257)]
        result = solve_conflicts({k: 1 for k in keys}, list(zip(keys, keys[1:])))
        self.assertEqual(len(result['staged']), 257)

    def test_work_cap_delegates(self):
        w, edges, _ = complete_fixture(9)
        result = solve_conflicts(w, edges, inspection_cap=1)
        self.assertEqual(result['components'][0]['fallback_reason'], 'flow_work_cap')
        self.assertTrue(result['staged'])

    def test_false_priority_can_win(self):
        result = solve_conflicts({'false': 9, 'true': 8}, [('false', 'true')])
        self.assertEqual(result['selected'], ['false'])

    def test_invalid_graph_inputs(self):
        for w, e in [({'a': -1}, []), ({'a': True}, []), ({'a': .5}, []), ({'a': 1}, [('a', 'a')]), ({'a': 1}, [('a', 'b')]), ({'a': 1}, [('a',)])]:
            with self.subTest(w=w, e=e), self.assertRaises(ValueError):
                solve_conflicts(w, e)

    def test_invalid_work_cap(self):
        for cap in (0, True, 2000001):
            with self.assertRaises(ValueError):
                solve_conflicts({}, [], inspection_cap=cap)

    def test_damaged_flow_and_cover_rejected(self):
        w, edges, _ = complete_fixture(2)
        good = solve_conflicts(w, edges)['components'][0]
        for kind in ('value', 'capacity', 'conservation', 'cover', 'selected', 'color', 'nodes', 'duplicate_flow'):
            bad = deepcopy(good)
            if kind == 'value': bad['certificate']['flow_value'] += 1
            elif kind == 'capacity': bad['certificate']['flow'][0][2] = 9999
            elif kind == 'conservation': bad['certificate']['flow'].pop()
            elif kind == 'cover': bad['certificate']['cover'] = []
            elif kind == 'selected': bad['selected'] = list(w)
            elif kind == 'color': bad['certificate']['left'] = list(w)
            elif kind == 'nodes': bad['certificate']['nodes'] = []
            else: bad['certificate']['flow'].append(bad['certificate']['flow'][0])
            with self.subTest(kind=kind):
                self.assertFalse(verify_certificate(w, edges, bad))

    def test_arbitrary_vertex_names_do_not_collide_with_flow_sentinels(self):
        self.check({'source': 2, 'sink': 3, '0': 1}, [('source', 'sink')])


class CacheTests(unittest.TestCase):
    def make(self):
        return LineageCache({'f': [['a']], 'g': [['b']]}, {'a': .9, 'b': .8})

    def test_constructor_does_not_alias_inputs(self):
        facts, ps = {'f': [['a']]}, {'a': .9}
        cache = LineageCache(facts, ps)
        facts['f'].clear(); ps['a'] = 0
        self.assertEqual(cache.snapshot()['values']['f']['lower'], .9)

    def test_snapshot_does_not_alias_state(self):
        cache = self.make()
        snap = cache.snapshot(); snap['values']['f']['lower'] = 0
        self.assertEqual(cache.snapshot()['values']['f']['lower'], .9)

    def test_local_retraction_recalculates_only_affected_fact(self):
        cache = self.make(); initial = cache.evaluations
        cache.update_probabilities({'a': 0.}, cache.revision)
        self.assertEqual(cache.evaluations-initial, 1)
        self.assertEqual(cache.snapshot()['values']['f']['lower'], 0.)
        self.assertEqual(cache.snapshot()['values']['g']['lower'], .8)

    def test_shared_retraction_recalculates_both(self):
        cache = LineageCache({'f': [['a']], 'g': [['a', 'b']]}, {'a': .9, 'b': .8})
        initial = cache.evaluations
        cache.update_probabilities({'a': 0.}, cache.revision)
        self.assertEqual(cache.evaluations-initial, 2)

    def test_proof_change_updates_both_sides_of_index(self):
        cache = self.make()
        cache.set_fact('f', [['b']], cache.revision)
        self.assertNotIn('a', cache.snapshot()['index'])
        self.assertEqual(cache.snapshot()['index']['b'], ['f', 'g'])
        initial = cache.evaluations
        cache.update_probabilities({'a': .1}, cache.revision)
        self.assertEqual(initial, cache.evaluations)
        cache.update_probabilities({'b': 0.}, cache.revision)
        self.assertEqual(cache.snapshot()['values']['f']['lower'], 0.)

    def test_remove_and_reinsert_fact(self):
        cache = self.make()
        cache.remove_fact('f', cache.revision)
        self.assertNotIn('a', cache.snapshot()['index'])
        cache.set_fact('f', [['a', 'b']], cache.revision)
        self.assertAlmostEqual(cache.snapshot()['values']['f']['lower'], .72)

    def test_no_op_has_no_evaluation_but_advances_revision(self):
        cache = self.make(); before = cache.evaluations
        cache.update_probabilities({'a': .9}, 0)
        self.assertEqual(cache.evaluations, before)
        self.assertEqual(cache.revision, 1)

    def test_stale_revision_is_atomic(self):
        cache = self.make(); before = cache.snapshot()
        with self.assertRaises(ValueError): cache.update_probabilities({'a': 0.}, -1)
        self.assertEqual(cache.snapshot(), before)

    def test_unknown_source_and_invalid_probabilities_are_atomic(self):
        cache = self.make(); before = cache.snapshot()
        for changes in ({'x': .5}, {'a': float('nan')}, {'a': 1.1}, {'a': True}, {'a': .5, 'b': -1.}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                cache.update_probabilities(changes, 0)
            self.assertEqual(cache.snapshot(), before)

    def test_proof_validation_is_atomic(self):
        cache = self.make(); before = cache.snapshot()
        with self.assertRaises(ValueError): cache.set_fact('f', [['x']], 0)
        self.assertEqual(cache.snapshot(), before)

    def test_unknown_delete_is_atomic(self):
        cache = self.make(); before = cache.snapshot()
        with self.assertRaises(ValueError): cache.remove_fact('x', 0)
        self.assertEqual(cache.snapshot(), before)

    def test_calculation_failure_after_first_result_rolls_back(self):
        cache = self.make()
        before = (cache.snapshot(), cache.evaluations, cache.index_touches)
        original, count = cache._evaluate, 0
        def failure(terms, probabilities):
            nonlocal count
            count += 1
            if count == 2: raise RuntimeError('injected')
            return original(terms, probabilities)
        with patch.object(cache, '_evaluate', side_effect=failure), self.assertRaises(RuntimeError):
            cache.update_probabilities({'a': 0., 'b': 0.}, 0)
        self.assertEqual((cache.snapshot(), cache.evaluations, cache.index_touches), before)

    def test_fact_calculation_failure_rolls_back(self):
        cache = self.make(); before = (cache.snapshot(), cache.evaluations, cache.index_touches)
        with patch.object(cache, '_evaluate', side_effect=RuntimeError('injected')), self.assertRaises(RuntimeError):
            cache.set_fact('f', [['b']], 0)
        self.assertEqual((cache.snapshot(), cache.evaluations, cache.index_touches), before)

    def test_constants_have_no_dependencies(self):
        cache = LineageCache({'true': [[]], 'false': []}, {'a': .5})
        before = cache.evaluations
        cache.update_probabilities({'a': .1}, 0)
        self.assertEqual(before, cache.evaluations)
        self.assertEqual(cache.snapshot()['values']['true']['lower'], 1.)
        self.assertEqual(cache.snapshot()['values']['false']['lower'], 0.)

    def test_subsumed_proof_does_not_leave_spurious_dependency(self):
        cache = LineageCache({'f': [['a'], ['a', 'b']]}, {'a': .8, 'b': .5})
        self.assertEqual(cache.snapshot()['index'], {'a': ['f']})


class ExecutedContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = json.loads((HERE/'results.json').read_text(encoding='utf-8'))

    def test_frozen_source_protocol_and_no_calls(self):
        self.assertEqual(self.r['fresh_service_calls'], 0)
        self.assertEqual(self.r['protocol_sha256'], sha(HERE/'PROTOCOL.md'))
        self.assertEqual(self.r['development']['n'], 73)
        self.assertEqual(self.r['test']['n'], 263)

    def test_all_source_folds_exclude_held_group(self):
        self.assertTrue(all(f['group'] not in f['fit_groups'] for f in self.r['H1']['folds']))
        self.assertEqual({x['alpha'] for x in self.r['H1']['grid']}, {1, 4, 16})

    def test_h1_verdict_is_frozen_conjunction_not_a_positive_default(self):
        scores = self.r['H1']['scores']; new = scores['direct_source']
        expected = new['brier'] <= .9*min(scores[x]['brier'] for x in ('raw_product', 'scaled_product')) and abs(new['bias']) <= .03
        self.assertEqual(self.r['H1']['primary_target_met'], expected)

    def test_review_oracle_and_budget_checks(self):
        self.assertEqual(self.r['H2']['oracle_failures'], 0)
        self.assertEqual(self.r['H2']['budget_failures'], 0)
        self.assertEqual(len(self.r['H2']['scenarios']), 108)
        self.assertEqual(len(self.r['H2']['oracle_fixtures']), 64)

    def test_all_lineage_controls_and_oracles(self):
        h = self.r['H3']
        self.assertEqual(h['random_cases'], 192)
        self.assertEqual(h['oracle_failures']+h['invariance_failures']+h['large_failures']+h['false_admissions'], 0)
        self.assertEqual(len(h['large']), 10)

    def test_all_graph_controls_and_oracles(self):
        h = self.r['H4']
        self.assertEqual(h['random_cases'], 192)
        self.assertEqual(h['oracle_failures']+h['invariance_failures']+h['large_failures'], 0)
        self.assertTrue(h['damaged_certificate_rejected'])
        self.assertEqual(len(h['large']), 10)

    def test_cache_mutations_and_atomicity(self):
        h = self.r['H5']
        self.assertEqual(h['mutation_cases'], 640)
        self.assertEqual(h['mismatches']+h['atomic_failures'], 0)
        self.assertEqual(h['global_source_control']['saving'], 0.)
        self.assertEqual(h['local_workload']['full_evaluations'], 128*257)


if __name__ == '__main__':
    unittest.main()
