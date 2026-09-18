"""Independent-oracle regression tests; benchmark targets may legitimately fail."""
import copy
from itertools import combinations, product
import math
import unittest
from unittest.mock import patch
from graph_synthesis.assumption_aware.methods import (
    DeltaTree, GroundedRules, exposure_order, frechet, invariant_repairs, lineage_envelope)
from graph_synthesis.assumption_aware.run import repair_oracle, scan_closure, full_tree


class ProbabilityTests(unittest.TestCase):
    def test_two_event_analytic_bounds(self):
        for a,b in product((0., .2, .5, .8, 1.), repeat=2):
            for proofs,lo,hi in [([['a'],['b']],max(a,b),min(1,a+b)),
                                 ([['a','b']],max(0,a+b-1),min(a,b))]:
                with self.subTest(a=a,b=b,proofs=proofs):
                    result=lineage_envelope(proofs,{'a':a,'b':b})
                    self.assertTrue(result['optimized'])
                    self.assertAlmostEqual(result['lower'],lo,places=6)
                    self.assertAlmostEqual(result['upper'],hi,places=6)
    def test_known_intersection(self):
        r=lineage_envelope([['a'],['b']],{'a':.6,'b':.5},[('a','b',.2)])
        self.assertAlmostEqual(r['lower'],.9,places=6)
        self.assertAlmostEqual(r['upper'],.9,places=6)
    def test_false_independence_not_admitted(self):
        r=lineage_envelope([['a'],['b']],{'a':.8,'b':.8})
        self.assertLess(r['lower'],.95)
        self.assertLessEqual(r['lower'],.8+1e-7)
        self.assertGreaterEqual(r['upper'],.8)
    def test_duplicate_subsumed_invariance(self):
        a=lineage_envelope([['a'],['a','b']],{'a':.4,'b':.9})
        b=lineage_envelope([['b','a'],['a'],['a']],{'b':.9,'a':.4})
        self.assertEqual(a,b)
    def test_inconsistent_constraints_stage(self):
        r=lineage_envelope([['a']],{'a':.8,'b':.8},[('a','b',.1)])
        self.assertFalse(r['optimized']); self.assertEqual((r['lower'],r['upper']),(0.,1.))
    def test_empty_and_tautology(self):
        self.assertEqual(lineage_envelope([], {})['upper'],0.)
        self.assertEqual(lineage_envelope([[]], {})['lower'],1.)
    def test_atom_cap_explicit(self):
        r=lineage_envelope([['a0']],{f'a{i}':.7 for i in range(9)})
        self.assertEqual(r['status'],'atom_cap'); self.assertFalse(r['optimized'])
    def test_invalid_marginals(self):
        for p in (-.1,1.1,float('nan'),float('inf'),True,'0.5'):
            with self.subTest(p=p), self.assertRaises(ValueError):
                lineage_envelope([['a']],{'a':p})
    def test_invalid_proof_pair_and_caps(self):
        for args,kwargs in [(([['x']],{'a':.5}),{}),
                            (([['a']],{'a':.5},[('a','a',.5)]),{}),
                            (([['a']],{'a':.5,'b':.5},[('a','b',.2),('b','a',.3)]),{}),
                            (([['a']],{'a':.5}),{'atom_cap':9}),
                            (([['a']],{'a':.5}),{'maxiter':0})]:
            with self.subTest(args=args,kwargs=kwargs), self.assertRaises(ValueError):
                lineage_envelope(*args,**kwargs)
    def test_solver_failure_never_admits(self):
        class Failure: success=False
        with patch('scipy.optimize.linprog',return_value=Failure()):
            r=lineage_envelope([['a']],{'a':.99})
        self.assertFalse(r['optimized']);self.assertEqual(r['lower'],0.)


class RepairTests(unittest.TestCase):
    def test_all_graphs_three_vertices_all_binary_weights(self):
        nodes=['a','b','c'];possible=list(combinations(nodes,2))
        queries=[('OR',['a','b']),('AND',['a','b']),('OR',[]),('AND',[])]
        for mask in range(8):
            edges=[e for i,e in enumerate(possible) if mask&(1<<i)]
            for ws in product((0,1),repeat=3):
                w=dict(zip(nodes,ws));r=invariant_repairs(w,edges,queries);o=repair_oracle(w,edges,queries)
                with self.subTest(mask=mask,weights=ws):
                    self.assertEqual(r['status'],'complete')
                    for field in ('utility','forced','queries'):self.assertEqual(r[field],o[field])
    def test_equal_pair_disjunction_not_member(self):
        r=invariant_repairs({'a':1,'b':1},[('a','b')],[('OR',['a','b']),('AND',['a','b'])])
        self.assertEqual(r['forced'],[]);self.assertEqual(r['queries'],[True,False])
    def test_unique_optimum(self):
        r=invariant_repairs({'a':2,'b':1},[('a','b')])
        self.assertEqual(r['forced'],['a']);self.assertEqual(r['forced'],r['selected'])
    def test_false_priority_remains_false(self):
        r=invariant_repairs({'false':9,'true':8},[('false','true')])
        self.assertEqual(r['forced'],['false'])
    def test_dense_unsupported_is_unknown(self):
        w={str(i):1 for i in range(17)}
        r=invariant_repairs(w,list(combinations(w,2)),[('OR',list(w))])
        self.assertEqual(r['status'],'unknown');self.assertEqual(r['queries'],[None])
    def test_call_cap_partial_not_false_certainty(self):
        r=invariant_repairs({'a':2,'b':1},[('a','b')],[('AND',['a']),('OR',['a'])],call_cap=1)
        self.assertEqual(r['status'],'partial');self.assertEqual(r['forced'],[])
        self.assertEqual(r['queries'],[None,None]);self.assertEqual(r['oracle_calls'],1)
    def test_vertex_cap(self):
        self.assertEqual(invariant_repairs({'a':1,'b':1},[],vertex_cap=1)['status'],'unknown')
    def test_empty_graph(self):
        r=invariant_repairs({},[],[('AND',[]),('OR',[])])
        self.assertEqual(r['queries'],[True,False])
    def test_query_validation(self):
        for query in [('X',['a']),('OR',['x'])]:
            with self.assertRaises(ValueError):invariant_repairs({'a':1},[],[query])
    def test_input_order_and_duplicate_edges(self):
        self.assertEqual(invariant_repairs({'a':1,'b':1},[('a','b')]),
                         invariant_repairs({'b':1,'a':1},[('b','a'),('a','b')]))


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.rows=[{'id':'a','group':'g','risk':.3},{'id':'b','group':'g','risk':.4},
                   {'id':'c','group':'h','risk':.2}]
    def test_uniform_matches_existing_strong_baseline(self):
        from graph_synthesis.adaptive.methods import review_order
        self.assertEqual(exposure_order(self.rows,{'g':1,'h':1}),review_order(self.rows,group_aware=True))
    def test_weights_can_change_priority(self):
        self.assertEqual(exposure_order(self.rows,{'g':1,'h':10})[0],'c')
    def test_no_gold_access_and_no_mutation(self):
        original=copy.deepcopy(self.rows)
        exposure_order(self.rows,{'g':1,'h':10})
        self.assertEqual(self.rows,original)
        self.assertTrue(all('gold' not in row for row in self.rows))
    def test_id_tie_deterministic(self):
        rows=[{'id':k,'group':k,'risk':.5} for k in ['b','a']]
        self.assertEqual(exposure_order(rows,{'a':1,'b':1}),['a','b'])
    def test_invalid_risk_exposure_and_duplicate(self):
        with self.assertRaises(ValueError):exposure_order(self.rows+self.rows,{'g':1,'h':1})
        for bad in (0,-1,float('nan'),float('inf'),True):
            with self.subTest(bad=bad),self.assertRaises(ValueError):exposure_order(self.rows,{'g':bad,'h':1})
        with self.assertRaises(ValueError):exposure_order([{'id':'a','group':'g','risk':2}],{'g':1})
        with self.assertRaises(ValueError):exposure_order(self.rows,{'g':1})
    def test_empty_review_pool(self):self.assertEqual(exposure_order([],{}),[])


class TreeTests(unittest.TestCase):
    def test_small_path_all_weights_and_updates(self):
        edges=[('a','b'),('b','c'),('c','d')]
        for ws in product((0,1,2),repeat=4):
            w=dict(zip('abcd',ws));engine=DeltaTree(w,edges)
            for key in 'abcd':
                w[key]=(w[key]+1)%3;engine.update(key,w[key]);o=repair_oracle(w,edges)
                with self.subTest(weights=ws,key=key):
                    self.assertEqual(engine.utility,o['utility'])
                    chosen=set(engine.selected())
                    self.assertFalse(any(a in chosen and b in chosen for a,b in edges))
                    self.assertEqual(sum(w[k] for k in chosen),o['utility'])
    def test_single_vertex(self):
        t=DeltaTree({'a':0},[]);self.assertEqual(t.selected(),[])
        self.assertEqual(t.update('a',3),3);self.assertEqual(t.selected(),['a'])
    def test_same_value_no_visits(self):
        t=DeltaTree({'a':1},[]);t.update('a',1);self.assertEqual(t.visits,0)
    def test_bad_updates_atomic(self):
        t=DeltaTree({'a':1,'b':2},[('a','b')]);before=copy.deepcopy(t.__dict__)
        for key,value in [('x',1),('a',-1),('a',True),('a',1.2)]:
            with self.assertRaises(ValueError):t.update(key,value)
            self.assertEqual(t.__dict__,before)
        with self.assertRaises(ValueError):t.change_structure([('a','c')])
        self.assertEqual(t.__dict__,before)
    def test_malformed_graphs(self):
        for weights,edges in [({},[]),({'a':1,'b':1},[]),
             ({'a':1,'b':1,'c':1},[('a','b'),('b','c'),('c','a')]),
             ({'a':1},[('a','a')]),({'a':-1},[])]:
            with self.subTest(weights=weights,edges=edges),self.assertRaises(ValueError):DeltaTree(weights,edges)
    def test_reconstruction_charged(self):
        t=DeltaTree({'a':1,'b':2,'c':3},[('a','b'),('a','c')])
        t.selected();self.assertEqual(t.reconstruction_visits,3)
    def test_copies_input_weights(self):
        w={'a':1};t=DeltaTree(w,[]);w['a']=9;self.assertEqual(t.utility,1)


class GroundingTests(unittest.TestCase):
    def test_pure_cycle_never_self_grounds(self):
        t=GroundedRules(['a','b'],[('a',['b']),('b',['a'])]);self.assertEqual(t.update([])['closure'],[])
    def test_withdrawing_only_seed_clears_cycle(self):
        t=GroundedRules(['a','b'],[('a',['b']),('b',['a'])]);t.update(['a'])
        r=t.update([]);self.assertEqual(r['closure'],[]);self.assertEqual(r['removed'],['a','b'])
    def test_alternate_grounding_survives(self):
        t=GroundedRules(['a','b','c'],[('a',['b']),('b',['a']),('a',['c'])])
        self.assertEqual(t.update(['c'])['closure'],['a','b','c'])
    def test_empty_body_axiom(self):
        t=GroundedRules(['a','b'],[('a',[]),('b',['a'])]);self.assertEqual(t.update([])['closure'],['a','b'])
    def test_duplicate_body_and_rules(self):
        t=GroundedRules(['a','b'],[('b',['a','a']),('b',['a'])])
        self.assertEqual(len(t.rules),1);self.assertEqual(t.update(['a'])['closure'],['a','b'])
    def test_self_loop_needs_external(self):
        t=GroundedRules(['a'],[('a',['a'])]);self.assertEqual(t.update([])['closure'],[])
        self.assertEqual(t.update(['a'])['closure'],['a']);self.assertEqual(t.update([])['closure'],[])
    def test_all_external_subsets_against_cold_scan(self):
        facts=list('abcd');rules=[('b',['a']),('c',['b']),('b',['c']),('d',['a','c'])]
        t=GroundedRules(facts,rules)
        for mask in range(16):
            external=[a for i,a in enumerate(facts) if mask&(1<<i)]
            self.assertEqual(t.update(external)['closure'],scan_closure(external,rules)['closure'])
    def test_bad_update_atomic(self):
        t=GroundedRules(['a','b'],[('b',['a'])]);t.update(['a']);before=copy.deepcopy(t.__dict__)
        for external in (['x'],'a'):
            with self.assertRaises(ValueError):t.update(external)
            self.assertEqual(t.__dict__,before)
    def test_bad_rules(self):
        for facts,rules in [('a',[]),(['a'],[('b',['a'])]),(['a'],[('a',['b'])]),(['a'],[('a','a')])]:
            with self.assertRaises(ValueError):GroundedRules(facts,rules)
    def test_wrong_external_can_ground_wrong_conclusion(self):
        t=GroundedRules(['false_source','false_fact'],[('false_fact',['false_source'])])
        self.assertIn('false_fact',t.update(['false_source'])['closure'])
    def test_initialization_cost_explicit(self):
        t=GroundedRules(['a','b','c'],[('b',['a']),('c',['a','b'])])
        self.assertEqual(t.index_inspections,3);self.assertEqual(t.update([])['counter_initializations'],2)


if __name__=='__main__':unittest.main()
