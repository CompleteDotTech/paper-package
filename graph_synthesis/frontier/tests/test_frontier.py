"""Adversarial regression tests; target failures are valid research outcomes."""
import copy
import hashlib
import itertools
import json
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from graph_synthesis.frontier.methods import (
    PathOptimizer, bipartite_optimum, compile_lineage, optimal_review,
    packed_review, probability, ratio_review, review_gain, solve_frontier,
    source_mixture, verify_certificate,
)
from graph_synthesis.frontier.run import (
    HERE, make_review_candidates, independent_set_oracle, joint_oracle,
    linear_path_oracle, review_oracle,
)
from graph_synthesis.reliability.methods import fit_small


def row(i='a', group='g', risk=.5, cost=1, detect=.75, false_remove=.01):
    return dict(id=i, group=group, risk=risk, cost=cost, detect=detect, false_remove=false_remove)


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.sources = {'s': .8}
        self.atoms = {a: dict(source='s', p0=0., p1=1.) for a in 'ab'}

    def test_shared_or(self):
        self.assertAlmostEqual(source_mixture([['a'], ['b']], self.sources, self.atoms)['lower'], .8)

    def test_shared_and(self):
        self.assertAlmostEqual(source_mixture([['a', 'b']], self.sources, self.atoms)['lower'], .8)

    def test_independent_sources(self):
        atoms = copy.deepcopy(self.atoms); atoms['b']['source'] = 't'
        self.assertAlmostEqual(source_mixture([['a'], ['b']], {'s': .8, 't': .8}, atoms)['lower'], .96)

    def test_conditional_noise_oracle(self):
        atoms = {'a': dict(source='s', p0=.3, p1=.7), 'b': dict(source='s', p0=.2, p1=.9)}
        proofs = [['a', 'b']]
        self.assertAlmostEqual(source_mixture(proofs, self.sources, atoms)['lower'], joint_oracle(proofs, self.sources, atoms))

    def test_deterministic_sources(self):
        for p in (0., 1.):
            self.assertEqual(source_mixture([['a']], {'s': p}, self.atoms)['lower'], p)

    def test_duplicate_invariant(self):
        self.assertEqual(source_mixture([['a'], ['b']], self.sources, self.atoms),
                         source_mixture([['b'], ['a'], ['a']], self.sources, self.atoms))

    def test_empty_disjunction(self):
        self.assertEqual(source_mixture([], {}, {})['lower'], 0.)

    def test_empty_conjunction_rejected(self):
        with self.assertRaises(ValueError): source_mixture([[]], self.sources, self.atoms)

    def test_unknown_source(self):
        with self.assertRaises(ValueError): source_mixture([['a']], {}, self.atoms)

    def test_invalid_probabilities(self):
        for p in (-.1, 1.1, float('nan'), float('inf'), True, '0.5'):
            with self.subTest(p=p), self.assertRaises(ValueError): probability(p)

    def test_source_cap_stages(self):
        value = source_mixture([['a']], {str(i): .5 for i in range(9)}, {'a': dict(source='0', p0=0., p1=1.)})
        self.assertEqual((value['lower'], value['upper'], value['exact']), (0., 1., False))

    def test_atom_cap_stages(self):
        atoms = {str(i): dict(source='s', p0=0., p1=1.) for i in range(17)}
        self.assertFalse(source_mixture([['0']], self.sources, atoms)['exact'])

    def test_input_unchanged(self):
        before = copy.deepcopy((self.sources, self.atoms))
        source_mixture([['a']], self.sources, self.atoms)
        self.assertEqual(before, (self.sources, self.atoms))


class DiagramTests(unittest.TestCase):
    def test_analytical_formula(self):
        value = compile_lineage([['a', 'b'], ['b', 'c']]).evaluate(dict(a=.5, b=.5, c=.5))
        self.assertEqual(value['lower'], .375)
        self.assertTrue(value['exact'])

    def test_probability_endpoints(self):
        diagram = compile_lineage([['a', 'b'], ['b', 'c']])
        for bits in itertools.product((0, 1), repeat=3):
            p = dict(zip('abc', bits))
            self.assertEqual(diagram.evaluate(p)['lower'], bool(bits[1] and (bits[0] or bits[2])))

    def test_compile_reuse_is_immutable(self):
        diagram = compile_lineage([['a', 'b']]); before = repr(diagram)
        diagram.evaluate(dict(a=.2, b=.4)); diagram.evaluate(dict(a=.8, b=.9))
        self.assertEqual(repr(diagram), before)

    def test_duplicate_permutation(self):
        self.assertEqual(compile_lineage([['a', 'b'], ['a', 'c']]), compile_lineage([['c', 'a'], ['b', 'a']]*3))

    def test_subsumed_proofs(self):
        d = compile_lineage([['a'], ['a', 'b']])
        self.assertEqual(d.evaluate(dict(a=.7, b=.1))['lower'], .7)

    def test_empty_disjunction(self):
        self.assertEqual(compile_lineage([]).evaluate({})['lower'], 0.)

    def test_reject_empty_proof(self):
        with self.assertRaises(ValueError): compile_lineage([[]])

    def test_missing_probabilities(self):
        with self.assertRaises(ValueError): compile_lineage([['a']]).evaluate({})

    def test_extra_probabilities(self):
        with self.assertRaises(ValueError): compile_lineage([['a']]).evaluate(dict(a=.5, b=.5))

    def test_invalid_probabilities(self):
        for p in (True, float('nan'), -1., 2.):
            with self.subTest(p=p), self.assertRaises(ValueError): compile_lineage([['a']]).evaluate({'a': p})

    def test_bad_atom(self):
        for term in ([''], ['a', 1]):
            with self.subTest(term=term), self.assertRaises(ValueError): compile_lineage([term])

    def test_cap_bounds(self):
        v = compile_lineage([['a', 'b'], ['b', 'c']], state_cap=1).evaluate(dict(a=.5, b=.5, c=.5))
        self.assertFalse(v['exact']); self.assertLessEqual(v['lower'], .375); self.assertGreaterEqual(v['upper'], .375)

    def test_atom_cap(self):
        keys = [str(i) for i in range(513)]
        d = compile_lineage([keys]); v = d.evaluate({k: .5 for k in keys})
        self.assertEqual((v['lower'], v['upper'], v['reason']), (0., 1., 'input_cap'))

    def test_proof_cap(self):
        self.assertEqual(compile_lineage([['a']]*4097).reason, 'input_cap')

    def test_invalid_state_caps(self):
        for cap in (0, -1, 32769, True, 3.5):
            with self.subTest(cap=cap), self.assertRaises(ValueError): compile_lineage([['a']], state_cap=cap)

    def test_large_fan(self):
        keys = ['a'+str(i) for i in range(128)]
        d = compile_lineage([[keys[0], k] for k in keys[1:]])
        v = d.evaluate({k: .5 for k in keys})
        self.assertTrue(v['exact']); self.assertAlmostEqual(v['lower'], .5)


class ReviewTests(unittest.TestCase):
    def test_zero_budget(self): self.assertEqual(optimal_review([row()], 0)['selected'], [])
    def test_empty(self): self.assertEqual(optimal_review([], 40)['selected'], [])
    def test_harmful_review_is_skipped(self):
        self.assertEqual(optimal_review([row(risk=.01, false_remove=.5)], 40)['selected'], [])

    def test_cap_staging(self):
        v = optimal_review([row(str(i)) for i in range(13)], 40)
        self.assertEqual(v['staged_groups'], ['g']); self.assertEqual(v['selected'], [])

    def test_strict_feature_schema(self):
        for key in ('gold', 'label', 'compact', 'outcome'):
            with self.subTest(key=key), self.assertRaises(ValueError): optimal_review([{**row(), key: 'leak'}], 10)

    def test_bad_cost(self):
        for cost in (0, 9, True, 1.5):
            with self.subTest(cost=cost), self.assertRaises(ValueError): optimal_review([row(cost=cost)], 40)

    def test_bad_budget(self):
        for budget in (-1, 161, True, 40.1):
            with self.subTest(budget=budget), self.assertRaises(ValueError): optimal_review([row()], budget)

    def test_duplicate_ids(self):
        with self.assertRaises(ValueError): optimal_review([row(), row()], 40)

    def test_input_purity(self):
        rows = [row('a'), row('b', 'other')]; before = copy.deepcopy(rows)
        optimal_review(rows, 2); ratio_review(rows, 2); packed_review(rows, 2, ['b', 'a'])
        self.assertEqual(rows, before)

    def test_permutation(self):
        rows = [row(str(i), str(i//2), risk=.2+.1*i, cost=i+1) for i in range(6)]
        self.assertEqual(optimal_review(rows, 12), optimal_review(list(reversed(rows)), 12))

    def test_global_finite_oracle(self):
        rng = random.Random(918)
        for _ in range(32):
            rows = [row(str(i), str(i%3), risk=rng.random(), cost=rng.randrange(1,5), detect=rng.random()) for i in range(7)]
            got = optimal_review(rows, 9)
            self.assertAlmostEqual(got['modeled_gain'], review_oracle(rows, 9), places=10)
            self.assertLessEqual(got['cost'], 9)

    def test_packed_order_validation(self):
        for order in ([], ['a', 'a'], ['missing']):
            with self.subTest(order=order), self.assertRaises(ValueError): packed_review([row()], 10, order)

    def test_selected_features_ignore_test_gold(self):
        test = [{'id': 'x', 'group': 'g', 'gold': 'SUPPORTS', 'views': {'base1': {'label': 'SUPPORTS', 'score': .8}, 'compact': {'label': 'REFUTES'}}, 'arms': {'single': {'input_tokens': 2048}}}]
        fit = {'prior': .2, 'bins': {}}
        a = make_review_candidates(test, fit, .75, .01)
        test[0]['gold'] = 'REFUTES'; test[0]['views']['compact'] = {'label': 'SUPPORTS'}
        self.assertEqual(a, make_review_candidates(test, fit, .75, .01))
        self.assertEqual(a[0]['cost'], 3)

    def test_development_fit_rejects_test(self):
        with self.assertRaises(ValueError): fit_small([dict(split='test')])


class ConflictTests(unittest.TestCase):
    def setUp(self):
        self.w = dict(a=3, b=2, c=4); self.e = [('a', 'b'), ('b', 'c')]
        self.answer = bipartite_optimum(self.w, self.e)

    def test_optimum(self):
        self.assertEqual(self.answer['utility'], 7)
        trap = bipartite_optimum(dict(a=3, b=5, c=3), self.e)
        self.assertEqual(trap['utility'], 6)  # Priority-greedy would select the weight-5 center.
        self.assertTrue(verify_certificate(dict(a=3, b=5, c=3), self.e, trap))
    def test_certificate(self): self.assertTrue(verify_certificate(self.w, self.e, self.answer))
    def test_duplicate_edges(self): self.assertEqual(bipartite_optimum(self.w, self.e*3), self.answer)
    def test_order_invariance(self): self.assertEqual(bipartite_optimum(dict(reversed(list(self.w.items()))), list(reversed(self.e))), self.answer)
    def test_empty_graph(self): self.assertEqual(solve_frontier({}, [])['utility'], 0)
    def test_zero_weights(self): self.assertTrue(verify_certificate(dict(a=0,b=0), [('a','b')], bipartite_optimum(dict(a=0,b=0), [('a','b')])))

    def test_tampered_certificates(self):
        changes = [lambda x: x['certificate'].__setitem__('flow_value', 999),
                   lambda x: x['certificate']['arcs'][0].__setitem__('flow', -1),
                   lambda x: x['certificate']['arcs'][0].__setitem__('capacity', 999),
                   lambda x: x['certificate'].__setitem__('reachable', []),
                   lambda x: x.__setitem__('selected', ['a','b','c']),
                   lambda x: x.__setitem__('utility', 999)]
        for fn in changes:
            x = copy.deepcopy(self.answer); fn(x)
            self.assertFalse(verify_certificate(self.w, self.e, x))

    def test_odd_cycle_fallback(self):
        w = dict(a=1,b=2,c=3); e = [('a','b'),('b','c'),('a','c')]
        self.assertEqual(solve_frontier(w,e)['utility'], 3)
        with self.assertRaises(ValueError): bipartite_optimum(w,e)

    def test_dense_odd_clique_staged(self):
        w = {str(i):1 for i in range(17)}
        result = solve_frontier(w, list(itertools.combinations(w,2)))
        self.assertEqual(len(result['staged']), 17)

    def test_unknown_endpoint(self):
        with self.assertRaises(ValueError): bipartite_optimum(self.w, [('a','missing')])

    def test_invalid_weight(self):
        for weight in (-1, True, 1.2):
            with self.subTest(weight=weight), self.assertRaises(ValueError): bipartite_optimum(dict(a=weight), [])

    def test_self_conflict(self):
        with self.assertRaises(ValueError): bipartite_optimum(dict(a=1), [('a','a')])

    def test_semantically_false_priority(self):
        result = solve_frontier({'false':9,'true':8}, [('false','true')])
        self.assertEqual(result['selected'], ['false'])

    def test_finite_oracle_exhaustive_topologies(self):
        w = dict(a=2,b=1,c=3,d=4); possible = [('a','c'),('a','d'),('b','c'),('b','d')]
        for mask in range(16):
            edges = [e for i,e in enumerate(possible) if mask & (1<<i)]
            result = bipartite_optimum(w, edges)
            self.assertEqual(result['utility'], independent_set_oracle(w,edges))
            self.assertTrue(verify_certificate(w,edges,result))


class PathTests(unittest.TestCase):
    def test_single_vertex(self):
        e = PathOptimizer({'a':3}, []); self.assertEqual(e.utility,3); self.assertEqual(e.selected(),['a'])
        self.assertEqual(e.update('a',7),7); self.assertEqual(e.transitions,0)

    def test_all_binary_small_weights(self):
        keys = list('abcde'); edges = list(zip(keys,keys[1:]))
        for weights in itertools.product((0,1,3),repeat=5):
            w = dict(zip(keys,weights)); e = PathOptimizer(w,edges); selected=e.selected()
            self.assertEqual(e.utility, independent_set_oracle(w,edges))
            self.assertEqual(sum(w[k] for k in selected),e.utility)
            self.assertFalse(any(a in selected and b in selected for a,b in edges))

    def test_random_updates(self):
        rng=random.Random(8); keys=[str(i) for i in range(13)]; w={k:1 for k in keys}; edges=list(zip(keys,keys[1:]))
        e=PathOptimizer(w,edges)
        for _ in range(100):
            key=rng.choice(keys); w[key]=rng.randrange(20); e.update(key,w[key]); selected=e.selected()
            self.assertEqual(e.utility,linear_path_oracle(w,keys))
            self.assertEqual(sum(w[k] for k in selected),e.utility)
            self.assertFalse(any(a in selected and b in selected for a,b in edges))

    def test_atomic_invalid_updates(self):
        e=PathOptimizer(dict(a=1,b=2), [('a','b')]); before=copy.deepcopy(e.__dict__)
        for key,weight in [('missing',1),('a',-1),('a',True),('a',1.5)]:
            with self.assertRaises(ValueError): e.update(key,weight)
            self.assertEqual(e.__dict__,before)

    def test_same_value_no_work(self):
        e=PathOptimizer(dict(a=1,b=2), [('a','b')]); work=e.transitions
        e.update('a',1); self.assertEqual(e.transitions,work); self.assertEqual(e.last_transitions,0)

    def test_zero_weights(self): self.assertEqual(PathOptimizer(dict(a=0,b=0), [('a','b')]).utility,0)
    def test_empty_rejected(self):
        with self.assertRaises(ValueError): PathOptimizer({},[])
    def test_disconnected_rejected(self):
        with self.assertRaises(ValueError): PathOptimizer(dict(a=1,b=2),[])
    def test_cycle_rejected(self):
        with self.assertRaises(ValueError): PathOptimizer(dict(a=1,b=2,c=3),[('a','b'),('b','c'),('c','a')])
    def test_star_rejected(self):
        with self.assertRaises(ValueError): PathOptimizer(dict(a=1,b=2,c=3,d=4),[('a','b'),('a','c'),('a','d')])
    def test_topology_rebuild(self):
        self.assertEqual(PathOptimizer(dict(a=3,b=2,c=4), [('a','b'),('b','c')]).utility,7)
        self.assertEqual(PathOptimizer(dict(a=3,b=2,c=4), [('a','c'),('a','b')]).utility,6)
    def test_witness_work_is_reported(self):
        e=PathOptimizer({str(i):1 for i in range(16)},[(str(i),str(i+1)) for i in range(15)])
        e.selected(); self.assertEqual(e.witness_visits,31)
        e.update('7',2); self.assertEqual(e.last_transitions,32)


class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.results=json.loads((HERE/'results.json').read_text(encoding='utf-8'))
    def test_frozen_protocol(self):
        self.assertEqual(hashlib.sha256((HERE/'PROTOCOL.md').read_bytes()).hexdigest(),'7a9a060f65ba35032b0df2186c1725da7c1c5ac96ddee807ca9e1587e6c0c725')
    def test_no_service_calls(self): self.assertEqual(self.results['fresh_service_calls'],0)
    def test_real_input_shape(self): self.assertEqual(self.results['evaluation'],dict(n=263,groups=149))
    def test_negative_primary_is_retained(self): self.assertFalse(self.results['H2']['primary_target_met'])
    def test_counted_controlled_oracles(self):
        self.assertEqual(len(self.results['H1']['fixtures']),96)
        self.assertEqual(len(self.results['H3']['fixtures']),128)
        self.assertEqual(len(self.results['H4']['small']),192)
        self.assertEqual(len(self.results['H5']['small']),64)
    def test_all_declared_hashes(self):
        root=HERE.parents[1]
        for collection in ('source_hashes','code_hashes'):
            for path,want in self.results[collection].items():
                self.assertEqual(hashlib.sha256((root/path).read_bytes()).hexdigest(),want,path)


if __name__ == '__main__': unittest.main()
