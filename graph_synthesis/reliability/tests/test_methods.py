import copy
import json
from pathlib import Path
import unittest
from graph_synthesis.reliability.methods import (fit_small,assign_small,group_risks,canonical,
    exact_lineage,lineage_bounds,solve_graph,IncrementalSolver,graph_input,forest_optimum)
from graph_synthesis.reliability.run import (probability_oracle,independent_set_oracle,cycle_fixture,
    lineage_benchmark,graph_benchmark,incremental_benchmark,proper_scores)
from graph_synthesis.reliability.report import replace_after_anchor,START,END,ANCHOR


class RiskTests(unittest.TestCase):
    def row(self,label='SUPPORTS',gold='SUPPORTS',score=.9,split='development'):
        return {'id':'a','group':'g','split':split,'gold':gold,'views':{'base1':{'label':label,'score':score}}}
    def test_development_guard(self):
        with self.assertRaises(ValueError):fit_small([self.row(split='test')])
    def test_empty_fit(self):
        with self.assertRaises(ValueError):fit_small([])
    def test_gold_free_execution(self):
        row=self.row();fit=fit_small([row]);del row['gold'];del row['split']
        self.assertEqual(len(assign_small([row],fit)),1)
    def test_compact_view_not_required(self):
        self.assertTrue(assign_small([self.row()],fit_small([self.row()])))
    def test_nonpositive_omitted(self):
        row=self.row('ERROR','REFUTES',None)
        self.assertEqual(assign_small([row],fit_small([row])),[])
    def test_smoothed_risk_not_zero(self):
        row=self.row();self.assertGreater(assign_small([row],fit_small([row]))[0]['risk'],0)
    def test_group_probability(self):
        self.assertAlmostEqual(group_risks([{'group':'g','risk':.2},{'group':'g','risk':.5}])['g'],.6)
    def test_group_multiplier_identity(self):
        self.assertEqual(group_risks([{'group':'g','risk':.2}],1),group_risks([{'group':'g','risk':.2}]))
    def test_invalid_probability(self):
        for p in (-1,2,float('nan'),float('inf'),True):
            with self.subTest(p=p),self.assertRaises(ValueError):group_risks([{'group':'g','risk':p}])
    def test_invalid_multiplier(self):
        for k in (0,-1,float('nan')):
            with self.subTest(k=k),self.assertRaises(ValueError):group_risks([],k)
    def test_same_denominator_required(self):
        with self.assertRaises(ValueError):proper_scores({'a':.2},{'b':1})
    def test_brier_is_proper_loss(self):
        self.assertEqual(proper_scores({'a':0.,'b':1.},{'a':0,'b':1})['brier'],0.)


class LineageTests(unittest.TestCase):
    def test_empty_evidence_zero(self):self.assertEqual(exact_lineage([], {})['lower'],0)
    def test_empty_proof_rejected(self):
        with self.assertRaises(ValueError):exact_lineage([[]],{})
    def test_unknown_atom_rejected(self):
        with self.assertRaises(ValueError):exact_lineage([['x']],{})
    def test_invalid_primitive_probability(self):
        for p in (-.1,1.1,float('nan'),True):
            with self.subTest(p=p),self.assertRaises(ValueError):exact_lineage([['x']],{'x':p})
    def test_duplicate_invariance(self):
        a=exact_lineage([['x']],{'x':.8});self.assertEqual(a,exact_lineage([['x']]*20,{'x':.8}))
    def test_subsumption(self):self.assertEqual(canonical([['a'],['a','b']]),(('a',),))
    def test_shared_dependency(self):
        p={'a':.8,'b':.5,'c':.5};proofs=[['a','b'],['a','c']]
        self.assertAlmostEqual(exact_lineage(proofs,p)['lower'],.6)
        self.assertAlmostEqual(probability_oracle(proofs,p),.6)
    def test_state_cap_safe_fallback(self):
        x=exact_lineage([['a','b'],['a','c']],{'a':.8,'b':.5,'c':.5},state_cap=1)
        self.assertFalse(x['exact']);self.assertLessEqual(x['lower'],.6);self.assertGreaterEqual(x['upper'],.6)
    def test_atom_cap_safe_fallback(self):
        p={str(i):.5 for i in range(17)};x=exact_lineage([list(p)],p)
        self.assertFalse(x['exact']);self.assertEqual(x['components'][0]['reason'],'atom_cap')
    def test_probabilities_zero_one(self):
        self.assertEqual(exact_lineage([['a','b']],{'a':1.,'b':0.})['lower'],0)
    def test_bad_caps(self):
        with self.assertRaises(ValueError):exact_lineage([['a']],{'a':.5},atom_cap=17)
    def test_no_input_mutation(self):
        proofs=[['a','b'],['a']];before=copy.deepcopy(proofs);exact_lineage(proofs,{'a':.5,'b':.5});self.assertEqual(proofs,before)
    def test_frozen_random_oracles(self):self.assertTrue(lineage_benchmark()['primary_target_met'])


class GraphTests(unittest.TestCase):
    def test_empty_graph(self):self.assertEqual(solve_graph({},[])['utility'],0)
    def test_negative_weight(self):
        with self.assertRaises(ValueError):solve_graph({'a':-1},[])
    def test_boolean_weight(self):
        with self.assertRaises(ValueError):solve_graph({'a':True},[])
    def test_unknown_endpoint(self):
        with self.assertRaises(ValueError):solve_graph({'a':1},[('a','b')])
    def test_self_conflict(self):
        with self.assertRaises(ValueError):solve_graph({'a':1},[('a','a')])
    def test_invalid_vertex_id(self):
        with self.assertRaises(ValueError):solve_graph({'':1},[])
    def test_forest_rejects_cycle(self):
        w={'a':1,'b':1,'c':1};adj=graph_input(w,[('a','b'),('b','c'),('a','c')])
        with self.assertRaises(ValueError):forest_optimum(w,adj,w)
    def test_odd_cycle_extension(self):
        w,e,o=cycle_fixture(17);self.assertEqual(solve_graph(w,e)['utility'],o);self.assertEqual(len(solve_graph(w,e,max_cut=0)['staged']),17)
    def test_wheel_extension(self):
        w,e,o=cycle_fixture(256,True);self.assertEqual(solve_graph(w,e)['utility'],o)
    def test_over_limit(self):
        w={str(i):1 for i in range(257)};e=[(str(i),str(i+1)) for i in range(256)]
        self.assertEqual(len(solve_graph(w,e)['staged']),257)
    def test_zero_priority(self):self.assertEqual(solve_graph({'a':0},[])['utility'],0)
    def test_false_priority_control(self):self.assertEqual(solve_graph({'false':9,'true':8},[('false','true')])['selected'],['false'])
    def test_frozen_graph_oracles(self):self.assertTrue(graph_benchmark()['primary_target_met'])
    def test_oracle_agreement(self):
        w={'a':5,'b':3,'c':3};e=[('a','b'),('a','c')]
        self.assertEqual(solve_graph(w,e)['utility'],independent_set_oracle(w,e))


class IncrementalTests(unittest.TestCase):
    def test_unchanged_snapshot_reuses_all(self):
        x=IncrementalSolver({'a':1},[]);x.update({'a':1},[]);self.assertEqual(x.solver_vertices,0)
    def test_weight_change_invalidates(self):
        x=IncrementalSolver({'a':1,'b':1},[]);x.update({'a':2,'b':1},[]);self.assertEqual(x.solver_vertices,1)
    def test_merge_and_split(self):
        w={'a':1,'b':1};x=IncrementalSolver(w,[])
        self.assertEqual(x.update(w,[('a','b')])['utility'],1)
        self.assertEqual(x.update(w,[])['utility'],2)
    def test_delete_last_vertex(self):
        x=IncrementalSolver({'a':1},[]);self.assertEqual(x.update({},[])['selected'],[])
    def test_failed_update_is_atomic(self):
        x=IncrementalSolver({'a':1},[])
        with self.assertRaises(ValueError):x.update({'a':-1},[])
        self.assertEqual(x.update({'a':1},[])['utility'],1);self.assertEqual(x.solver_vertices,0)
    def test_input_snapshot_copied(self):
        w={'a':1};x=IncrementalSolver(w,[]);w['a']=2;self.assertEqual(x.weights['a'],1)
    def test_output_cannot_mutate_cache(self):
        x=IncrementalSolver({'a':1},[]);r=x.update({'a':1},[]);r['selected'].clear()
        self.assertEqual(x.update({'a':1},[])['selected'],['a'])
    def test_frozen_mutation_oracles(self):self.assertTrue(incremental_benchmark()['primary_target_met'])


class ReportTests(unittest.TestCase):
    def test_insert_idempotent(self):
        base='before\n'+ANCHOR+'\n\nafter\n';first=replace_after_anchor(base,'body')
        self.assertEqual(first,replace_after_anchor(first,'body'))
    def test_preserves_prior_sections(self):
        x=replace_after_anchor('prior\n'+ANCHOR+'\n\noriginal','new')
        self.assertTrue(x.startswith('prior\n'));self.assertTrue(x.endswith('original'))
    def test_requires_one_anchor(self):
        with self.assertRaises(ValueError):replace_after_anchor('missing','body')
    def test_replaces_instead_of_duplicates(self):
        x=replace_after_anchor(replace_after_anchor(ANCHOR,'old'),'new')
        self.assertEqual(x.count(START),1);self.assertNotIn('old',x)


if __name__=='__main__':unittest.main()
