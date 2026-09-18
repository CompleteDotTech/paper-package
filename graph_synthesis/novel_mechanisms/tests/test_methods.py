"""Independent invariants, malicious-input controls and bounded failure paths."""
from copy import deepcopy
from fractions import Fraction
from itertools import combinations,product
import math
import random
import unittest
from unittest.mock import patch

import numpy as np
from graph_synthesis.novel_mechanisms import methods as m
from graph_synthesis.novel_mechanisms.run import repair_oracle,graph_oracle,assertion,integer_conflicts


def pred(label='SUPPORTS',p=None):
    p=p or {k:float(k==label) for k in m.LABELS}
    return {'status':'ok','label':label,'score':p[label],'probabilities':p}


def small_dev():
    return [{'id':str(i),'split':'development','gold':k,'prediction':pred(k)} for i,k in enumerate(m.LABELS)]


class ShiftTests(unittest.TestCase):
    def test_face_solver_matches_dense_grid_lower_bound(self):
        c=np.eye(3);observed=np.array([.8,.15,.05]);prior=np.full(3,1/3)
        q=np.array(m.simplex_fit(c,observed,prior))
        objective=lambda x:np.sum((c@x-observed)**2)+.01*np.sum((x-prior)**2)
        grid=min(objective(np.array([a/50,b/50,(50-a-b)/50])) for a in range(51) for b in range(51-a))
        self.assertLessEqual(objective(q),grid+1e-12)
        self.assertAlmostEqual(sum(q),1)

    def test_boundary_face(self):
        c=np.array([[.9,.7,.7],[.05,.2,.1],[.05,.1,.2]])
        q=m.simplex_fit(c,[1,0,0],[1/3]*3)
        self.assertAlmostEqual(q[0],1)

    def test_fit_rejects_test_gold(self):
        with self.assertRaises(ValueError):m.fit_shift(small_dev(),[{'id':'t','gold':'SUPPORTS','prediction':pred()}])

    def test_predict_rejects_test_gold(self):
        with self.assertRaises(ValueError):m.apply_shift([{'gold':'REFUTES'}],{})

    def test_wrong_split_rejected(self):
        dev=small_dev();dev[0]['split']='test'
        with self.assertRaises(ValueError):m.fit_shift(dev,[{'id':'t','prediction':pred()}])

    def test_all_failed_development_rejected(self):
        dev=small_dev()
        for r in dev:r['prediction']={'status':'error','label':'ERROR'}
        with self.assertRaises(ValueError):m.fit_shift(dev,[{'id':'t','prediction':pred()}])

    def test_empty_target_rejected(self):
        with self.assertRaises(ValueError):m.fit_shift(small_dev(),[])

    def test_failure_preserved(self):
        target=[{'id':'t','prediction':pred()},{'id':'bad','prediction':{'status':'error','label':'ERROR'}}]
        fit=m.fit_shift(small_dev(),target)
        self.assertEqual(m.apply_shift(target,fit)[1]['label'],'ERROR')

    def test_fit_and_apply_do_not_mutate(self):
        dev=small_dev();target=[{'id':'t','prediction':pred()}];snapshot=deepcopy((dev,target))
        fit=m.fit_shift(dev,target);m.apply_shift(target,fit)
        self.assertEqual((dev,target),snapshot)

    def test_unidentifiable_retains_exact_prediction(self):
        dev=small_dev()
        for r in dev:r['prediction']=pred()
        target=[{'id':'t','prediction':pred('REFUTES')}];fit=m.fit_shift(dev,target)
        self.assertEqual(fit['fallback'],'unchanged_unidentifiable')
        self.assertEqual(m.apply_shift(target,fit),[{'id':'t',**target[0]['prediction']}])

    def test_malformed_vectors(self):
        for p in ([math.nan,.5,.5],[1.1,0,-.1],[.1,.1,.1],[True,0,0]):
            with self.subTest(p=p),self.assertRaises(ValueError):m.vector(pred(p=dict(zip(m.LABELS,p))))

    def test_bad_priors_rejected(self):
        with self.assertRaises(ValueError):m.apply_shift([{'id':'t','prediction':pred()}],{'source_prior':[0,.5,.5],'target_prior':[1/3]*3})

    def test_invalid_simplex_inputs(self):
        for c in ([[1]],np.full((3,3),math.nan),np.ones((3,3))):
            with self.subTest(c=c),self.assertRaises(ValueError):m.simplex_fit(c,[1/3]*3,[1/3]*3)


class DependenceTests(unittest.TestCase):
    def test_correlated_or_not_independent(self):
        got=m.dependence_bounds([['a'],['b']],{'a':.8,'b':.8})
        self.assertEqual((got['lower_rational'],got['upper_rational']),('4/5','1'))
        self.assertFalse(got['admit_095'])

    def test_exact_dual_verified_independently(self):
        got=m.dependence_bounds([['a','b'],['c']],dict(a=.7,b=.8,c=.2))
        atoms=got['atoms'];p={'a':Fraction(7,10),'b':Fraction(4,5),'c':Fraction(1,5)}
        for certificate in got['certificates']:
            y=list(map(Fraction,certificate['dual']));sign=certificate['sign']
            for bits in product((0,1),repeat=len(atoms)):
                active={a for a,b in zip(atoms,bits) if b}
                truth=int({'a','b'}<=active or 'c' in active)
                self.assertLessEqual(y[0]+sum(v*b for v,b in zip(y[1:],bits)),sign*truth)
            self.assertEqual(y[0]+sum(v*p[a] for v,a in zip(y[1:],atoms)),Fraction(certificate['value']))

    def test_threshold_uses_exact_fraction(self):
        yes=m.dependence_bounds([['a']],{'a':Fraction(19,20)})
        no=m.dependence_bounds([['a']],{'a':Fraction(19,20)-Fraction(1,10**18)})
        self.assertTrue(yes['admit_095']);self.assertFalse(no['admit_095'])

    def test_duplicate_subsumption_invariance(self):
        self.assertEqual(m.dependence_bounds([['a'],['a','b']],dict(a=.8,b=.2)),m.dependence_bounds([['a']]*3,dict(b=.2,a=.8)))

    def test_empty_family_is_false(self):
        r=m.dependence_bounds([],{'a':.7});self.assertEqual(r['upper'],0);self.assertEqual(r['route'],'empty')

    def test_over_cap_fallback_is_bounded(self):
        r=m.dependence_bounds([[str(i)] for i in range(9)],{str(i):.8 for i in range(9)})
        self.assertEqual(r['route'],'frechet_fallback');self.assertEqual(r['lower'],.8)

    def test_solver_failure_does_not_publish_partial_result(self):
        def fail(*a,**kw):raise RuntimeError('Injected unavailable solver')
        r=m.dependence_bounds([['a'],['b']],dict(a=.8,b=.8),solver=fail)
        self.assertEqual(r['route'],'frechet_solver_fallback');self.assertEqual(r['certificates'],[])

    def test_bad_dual_cannot_issue_bad_certificate(self):
        class Answer:
            success=True
            class eqlin:marginals=[10.,10.,10.]
        r=m.dependence_bounds([['a'],['b']],dict(a=.8,b=.8),solver=lambda *a,**kw:Answer())
        self.assertLessEqual(r['lower'],.8);self.assertFalse(r['admit_095'])

    def test_invalid_probabilities(self):
        for value in (True,math.inf,math.nan,-.1,1.1,'0.5'):
            with self.subTest(value=value),self.assertRaises(ValueError):m.dependence_bounds([['a']],{'a':value})

    def test_invalid_proofs(self):
        for proofs in ([[]],[['unknown']],['a']):
            with self.subTest(proofs=proofs),self.assertRaises(ValueError):m.dependence_bounds(proofs,{'a':.8})

    def test_bounds_validation(self):
        for cap in (True,-1,9):
            with self.assertRaises(ValueError):m.dependence_bounds([['a']],{'a':.8},atom_cap=cap)

    def test_input_nonmutation(self):
        proofs=[['a','b'],['a']];p=dict(a=.8,b=.4);before=deepcopy((proofs,p))
        m.dependence_bounds(proofs,p);self.assertEqual((proofs,p),before)


class RepairTests(unittest.TestCase):
    def test_greedy_trap(self):
        t=[['a','b'],['a','c'],['b','d'],['c','e']];c=dict(a=2,b=2,c=2,d=3,e=3)
        self.assertEqual(m.minimal_repair(t,[],c)['cost'],4)
        self.assertEqual(m.greedy_repair(t,[],c)['cost'],6)

    def test_protected_alternative_survives(self):
        r=m.minimal_repair([['a','b']],[[['a'],['b']]],dict(a=1,b=2))
        self.assertEqual(r['removed'],['a'])

    def test_infeasible_preservation(self):
        self.assertEqual(m.minimal_repair([['a']],[[['a']]],{'a':1})['status'],'infeasible')

    def test_empty_target(self):
        self.assertEqual(m.minimal_repair([],[],{})['cost'],0)

    def test_empty_protected_fact(self):
        self.assertEqual(m.minimal_repair([], [[]], {'a':1})['status'],'infeasible')

    def test_state_exhaustion_stages(self):
        r=m.minimal_repair([['a','b']],[],dict(a=1,b=2),state_cap=1)
        self.assertEqual(r['status'],'staged');self.assertIsNone(r['cost']);self.assertEqual(r['removed'],[])

    def test_atom_cap(self):
        c={str(i):1 for i in range(17)}
        self.assertEqual(m.minimal_repair([['0']],[],c)['status'],'staged')

    def test_bad_costs(self):
        for c in (0,-1,True,1.5):
            with self.assertRaises(ValueError):m.minimal_repair([['a']],[],{'a':c})

    def test_permutation_ties(self):
        a=m.minimal_repair([['a','b']],[],dict(a=1,b=1))
        self.assertEqual(a,m.minimal_repair([['b','a']]*4,[],dict(b=1,a=1)))
        self.assertEqual(a['removed'],['a'])

    def test_random_exact_oracle(self):
        rng=random.Random(271828)
        for _ in range(40):
            keys=list('abcdef');c={k:rng.randrange(1,8) for k in keys}
            t=[rng.sample(keys,2) for _ in range(6)];p=[[rng.sample(keys,2),rng.sample(keys,2)]]
            actual=m.minimal_repair(t,p,c);expected=repair_oracle(t,p,c)
            self.assertEqual({k:actual[k] for k in expected},expected)

    def test_input_nonmutation(self):
        t=[['a','b']];p=[[['a'],['b']]];c=dict(a=1,b=2);before=deepcopy((t,p,c))
        m.minimal_repair(t,p,c);self.assertEqual((t,p,c),before)


class FlowTests(unittest.TestCase):
    def test_weighted_dense_bipartite(self):
        w={**{f'l{i}':2 for i in range(8)},**{f'r{i}':3 for i in range(9)}}
        e=[(a,b) for a in w if a[0]=='l' for b in w if b[0]=='r']
        r=m.bipartite_solve(w,e);self.assertEqual(r['utility'],27);self.assertFalse(r['staged'])

    def test_flow_feasibility_certificate(self):
        w=dict(a=3,b=2,c=4,d=3);e=[('a','c'),('a','d'),('b','c')]
        c=m.bipartite_solve(w,e)['components'][0];balance=Counter()
        index={k:i+2 for i,k in enumerate(c['vertex_order'])};original_edges={frozenset(x) for x in e}
        for u,v,value,capacity in c['flow_edges']:
            self.assertGreater(value,0);self.assertLessEqual(value,capacity)
            if u==0:self.assertEqual(capacity,w[c['vertex_order'][v-2]])
            elif v==1:self.assertEqual(capacity,w[c['vertex_order'][u-2]])
            else:
                self.assertIn(frozenset([c['vertex_order'][u-2],c['vertex_order'][v-2]]),original_edges)
                self.assertEqual(capacity,sum(w.values())+1)
            balance[u]-=value;balance[v]+=value
        self.assertEqual(balance[0],-c['flow']);self.assertEqual(balance[1],c['flow'])
        self.assertTrue(all(balance[v]==0 for v in index.values()))
        self.assertTrue(all(a in c['cover'] or b in c['cover'] for a,b in e))
        self.assertEqual(sum(w[k] for k in c['cover']),c['flow'])

    def test_odd_cycle_fallback(self):
        r=m.bipartite_solve(dict(a=1,b=1,c=1),[('a','b'),('b','c'),('a','c')])
        self.assertEqual(r['utility'],1);self.assertNotEqual(r['components'][0]['method'],'bipartite_flow')

    def test_nonbipartite_staging(self):
        w={str(i):1 for i in range(17)}
        self.assertEqual(len(m.bipartite_solve(w,list(combinations(w,2)))['staged']),17)

    def test_large_component_cap(self):
        w={str(i):1 for i in range(257)};e=[('0',str(i)) for i in range(1,257)]
        self.assertEqual(len(m.bipartite_solve(w,e)['staged']),257)

    def test_zero_weights_and_isolated_vertices(self):
        r=m.bipartite_solve(dict(a=0,b=0,c=4),[('a','b')]);self.assertEqual(r['utility'],4)
        self.assertFalse('a' in r['selected'] and 'b' in r['selected'])

    def test_random_subset_oracle(self):
        rng=random.Random(314159)
        for _ in range(40):
            w={str(i):rng.randrange(0,8) for i in range(8)};e=[(str(a),str(b)) for a in range(4) for b in range(4,8) if rng.random()<.7]
            self.assertEqual(m.bipartite_solve(w,e)['utility'],graph_oracle(w,e))

    def test_input_validation(self):
        for w,e in [({'a':True},[]),({'a':-1},[]),({'a':1},[('a','a')]),({'a':1},[('a','b')])]:
            with self.assertRaises(ValueError):m.bipartite_solve(w,e)

    def test_permutation_and_nonmutation(self):
        w=dict(a=2,b=3,c=2);e=[('a','b'),('b','c')];before=deepcopy((w,e));a=m.bipartite_solve(w,e)
        self.assertEqual(a,m.bipartite_solve(dict(reversed(list(w.items()))),list(reversed(e))*2))
        self.assertEqual((w,e),before)


class IndexTests(unittest.TestCase):
    def test_half_open_contact(self):
        rows=[assertion('a',object='x',start=0,end=1),assertion('b',object='y',start=1,end=2)]
        self.assertEqual(m.indexed_conflicts(rows)['edges'],[])

    def test_unbounded_intervals(self):
        rows=[assertion('a',object='x',start=None,end=None),assertion('b',object='y',start=1,end=2)]
        self.assertEqual(m.indexed_conflicts(rows)['edges'],[['a','b']])

    def test_unknown_stage(self):
        r=m.indexed_conflicts([assertion('a',scope=None),assertion('b',start=2,end=1)])
        self.assertEqual(r['staged'],['a','b'])

    def test_scopes_are_not_universal(self):
        self.assertFalse(m.indexed_conflicts([assertion('a',scope='x'),assertion('b',scope='y',object='q')])['edges'])

    def test_same_object_opposite_polarity(self):
        self.assertEqual(m.indexed_conflicts([assertion('a'),assertion('b',polarity=-1)])['edges'],[['a','b']])

    def test_nonfunctional_different_objects(self):
        self.assertFalse(m.indexed_conflicts([assertion('a',predicate='p'),assertion('b',predicate='p',object='q')])['edges'])

    def test_duplicate_facts_are_not_conflicts(self):
        self.assertFalse(m.indexed_conflicts([assertion('a'),assertion('b')])['edges'])

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):m.indexed_conflicts([assertion('a'),assertion('a')])

    def test_empty_inputs(self):
        self.assertEqual(m.indexed_conflicts([]),m.pairwise_conflicts([]))

    def test_nonmutation(self):
        rows=[assertion('a'),assertion('b',object='q')];before=deepcopy(rows)
        m.indexed_conflicts(rows);self.assertEqual(rows,before)

    def test_exhaustive_small_bounded_intervals(self):
        for start,end in combinations(range(5),2):
            for start2,end2 in combinations(range(5),2):
                rows=[assertion('a',start=start,end=end),assertion('b',object='q',start=start2,end=end2)]
                self.assertEqual(m.indexed_conflicts(rows)['edges'],integer_conflicts(rows))


# Imported here deliberately: certificate conservation uses a separate counter.
from collections import Counter
if __name__=='__main__':unittest.main()
