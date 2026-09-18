"""Regression, property, provenance and anti-leakage tests for five hypotheses."""
import copy
import json
import os
import subprocess
import sys
import math
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from graph_synthesis.followup import methods as m
from graph_synthesis.followup.run import load_data, h2, h3, h4, h5, SEED


def row(i=0,p=.8,gold='same',group=None):
    return {'id':str(i),'probabilities':{'same':p,'different':1-p},
            'label':'same' if p>=.5 else 'different','score':max(p,1-p),
            'error':False,'input_tokens':10,'gold':gold,'group':group or str(i)}


def assertion(**kw):
    return {**dict(subject='s',predicate='p',object='o',scope='adult',polarity=1,start=0,end=3),**kw}


class CalibrationTests(unittest.TestCase):
    def test_identity_exact(self):
        self.assertEqual(m.transform({'a':0.,'b':1.},1),{'a':0.,'b':1.})
    def test_zero_weight_exact(self):
        self.assertEqual(m.transform({'a':0.,'b':1.},8,0),{'a':0.,'b':1.})
    def test_normalizes(self):
        self.assertAlmostEqual(sum(m.transform({'a':.2,'b':.3,'c':.5},4,.5).values()),1)
    def test_argmax_preserved_grid(self):
        for t in m.TEMPERATURES:
            for w in m.SHRINKAGES:
                q=m.transform({'a':.1,'b':.2,'c':.7},t,w)
                self.assertEqual(max(q,key=q.get),'c')
    def test_zero_probability_finite(self):
        self.assertTrue(math.isfinite(m.loss({'a':0.,'b':1.},'a')[0]))
    def test_bad_temperature(self):
        for t in (0,-1,math.nan,math.inf):
            with self.subTest(t=t), self.assertRaises(ValueError):m.transform({'a':1.},t)
    def test_bad_probability(self):
        for p in (-.1,1.1,math.nan,math.inf,True):
            with self.subTest(p=p), self.assertRaises(ValueError):m.validate_probability(p)
    def test_bad_distribution(self):
        with self.assertRaises(ValueError):m.transform({'a':.2,'b':.2})
    def test_bad_weight(self):
        with self.assertRaises(ValueError):m.transform({'a':1.},1,2)
    def test_split_enforced(self):
        with self.assertRaises(ValueError):m.fit_guard([row()],split='evaluation')
    def test_empty_fit_rejected(self):
        with self.assertRaises(ValueError):m.fit_guard([],split='calibration')
    def test_component_split_disjoint(self):
        rows=[row(i,group=str(i//2)) for i in range(40)]
        fit=m.fit_guard(rows,split='calibration')
        self.assertFalse(set(fit['fit_groups'])&set(fit['guard_groups']))
    def test_group_guard_no_harm(self):
        rows=[row(i,p=.95 if i%2 else .6,gold='different' if i%7==0 else 'same') for i in range(80)]
        fit=m.fit_guard(rows,split='calibration')
        baseline=next(r for r in fit['guard_grid'] if r['weight']==0)
        chosen=next(r for r in fit['guard_grid'] if r['weight']==fit['weight'])
        self.assertLessEqual(chosen['brier'],baseline['brier']+1e-12)
    def test_fit_input_unchanged(self):
        rows=[row(i) for i in range(30)];before=copy.deepcopy(rows)
        m.fit_guard(rows,split='calibration');self.assertEqual(rows,before)
    def test_all_errors_identity(self):
        r=row();r['error']=True
        self.assertEqual(m.fit_guard([r],split='calibration')['status'],'identity_fallback')
    def test_invalid_loss_denominator(self):
        r=row();r['error']=True
        self.assertEqual(m.losses([r])['n'],0)
        self.assertIsNone(m.losses([r])['brier'])


class RoutingTests(unittest.TestCase):
    def test_features_strip_gold(self):
        self.assertNotIn('gold',m.features([row()])[0])
    def test_input_gold_not_needed(self):
        self.assertEqual(m.route(m.features([row()]),m.features([row()]),0,0)[0],['same'])
    def test_positive_escalation_cost(self):
        a,b=row(),row();b['input_tokens']=50
        pred,cost,n=m.route(m.features([a]),m.features([b]),.95,0)
        self.assertEqual((pred,cost,n),(['same'],60,1))
    def test_negative_threshold_separate(self):
        a,b=row(p=.1),row()
        self.assertEqual(m.route(m.features([a]),m.features([b]),.95,0)[0],['different'])
    def test_error_always_escalates(self):
        a,b=row(),row();a.update(error=True,label='ERROR',score=1)
        self.assertEqual(m.route(m.features([a]),m.features([b]),0,0)[2],1)
    def test_direct_avoids_baseline_cost(self):
        self.assertEqual(m.route(m.features([row()]),m.features([row()]),0,0,direct=True)[1],10)
    def test_missing_tokens_fails(self):
        a=row();a['input_tokens']=None
        with self.assertRaises(ValueError):m.route([a],[row()],0,0)
    def test_alignment_fails(self):
        with self.assertRaises(ValueError):m.route([row(0)],[row(1)],0,0)
    def test_no_precision_for_no_edges(self):
        self.assertIsNone(m.edges(['same'],['STAGE'])['precision'])
    def test_errors_retained(self):
        self.assertEqual(m.edges(['same'],['ERROR'])['operational_errors'],1)
    def test_fit_rejects_test_split(self):
        with self.assertRaises(ValueError):m.fit_edge_route([row()],[row()],split='evaluation')
    def test_fit_has_safe_direct_fallback(self):
        rows=[row(i) for i in range(20)]
        fit=m.fit_edge_route(rows,rows,split='calibration')
        self.assertTrue(any(r['direct'] and r['eligible'] for r in fit['grid']))
    def test_stability_is_not_truth(self):
        a=row(gold='different')
        self.assertEqual(m.stable_ids(m.features([a]),m.features([a])),{'0'})
    def test_disagreement_staged(self):
        self.assertFalse(m.stable_ids(m.features([row()]),m.features([row(p=.1)])))
    def test_stable_error_staged(self):
        a=row();a.update(error=True,label='ERROR')
        self.assertFalse(m.stable_ids(m.features([a]),m.features([a])))
    def test_stability_alignment(self):
        with self.assertRaises(ValueError):m.stable_ids([row(0)],[row(1)])


class IntervalTests(unittest.TestCase):
    def test_overlapping_opposition(self):
        self.assertEqual(m.conflict(assertion(),assertion(start=1,end=4,polarity=-1)),'conflict')
    def test_endpoint_touch_clear(self):
        self.assertEqual(m.conflict(assertion(),assertion(start=3,end=6,polarity=-1)),'clear')
    def test_disjoint_scopes(self):
        self.assertEqual(m.conflict(assertion(),assertion(scope='child',polarity=-1)),'clear')
    def test_unknown_scope_staged(self):
        self.assertEqual(m.conflict(assertion(scope=None),assertion()),'unknown')
    def test_unbounded_overlap(self):
        self.assertEqual(m.conflict(assertion(start=None,end=None),assertion(polarity=-1)),'conflict')
    def test_invalid_interval_staged(self):
        self.assertEqual(m.conflict(assertion(start=5,end=2),assertion()),'unknown')
    def test_functional_collision(self):
        self.assertEqual(m.conflict(assertion(),assertion(object='x'),frozenset({'p'})),'conflict')
    def test_nonfunctional_different_objects(self):
        self.assertEqual(m.conflict(assertion(),assertion(object='x')),'clear')
    def test_same_assertion_no_conflict(self):
        self.assertEqual(m.conflict(assertion(),assertion()),'clear')
    def test_missing_endpoint_unknown(self):
        a=assertion();del a['start']
        self.assertEqual(m.conflict(a,assertion()),'unknown')
    def test_qualifiers_not_mutated(self):
        a,b=assertion(),assertion(polarity=-1);before=copy.deepcopy((a,b))
        m.conflict(a,b);self.assertEqual((a,b),before)
    def test_finite_oracle(self):
        r=h4();self.assertEqual(r['supported_cases'],5408)
        self.assertTrue(r['primary_target_met']);self.assertGreater(r['strategies']['exact_qualifier']['missed_conflicts'],0)


class LineageTests(unittest.TestCase):
    def test_single_proof_exact(self):
        r=m.proof_bounds([['a']],{'a':.4});self.assertAlmostEqual(r['lower'],.4);self.assertEqual(r['lower'],r['upper'])
    def test_disjoint_proofs_exact(self):
        r=m.proof_bounds([['a'],['b']],{'a':.8,'b':.5});self.assertAlmostEqual(r['lower'],.9);self.assertEqual(r['lower'],r['upper'])
    def test_shared_proofs_bounds(self):
        proofs=[['a','b'],['a','c']];p=dict(a=.8,b=.5,c=.2)
        exact=m.exact_probability(proofs,p);bounds=m.proof_bounds(proofs,p)
        self.assertLessEqual(bounds['lower'],exact);self.assertGreaterEqual(bounds['upper'],exact)
    def test_duplicate_invariance(self):
        proofs=[['a','b'],['a','c']];p=dict(a=.8,b=.5,c=.2)
        self.assertEqual(m.proof_bounds(proofs,p),m.proof_bounds(proofs*20,p))
    def test_duplicate_atom_idempotence(self):
        self.assertEqual(m.proof_bounds([['a','a']],{'a':.7}),m.proof_bounds([['a']],{'a':.7}))
    def test_permutation_invariance(self):
        p=dict(a=.5,b=.6,c=.7)
        self.assertEqual(m.proof_bounds([['a','b'],['c']],p),m.proof_bounds([['c'],['b','a']],p))
    def test_empty_proofs_zero(self):
        self.assertEqual(m.proof_bounds([],{'a':.5})['upper'],0)
    def test_empty_clause_rejected(self):
        with self.assertRaises(ValueError):m.proof_bounds([[]],{'a':.5})
    def test_unknown_atom_rejected(self):
        with self.assertRaises(ValueError):m.proof_bounds([['b']],{'a':.5})
    def test_exact_oracle_bounded(self):
        with self.assertRaises(ValueError):m.exact_probability([],dict.fromkeys(map(str,range(13)),.5))
    def test_probability_boundaries(self):
        self.assertEqual(m.exact_probability([['a']],{'a':0}),0)
        self.assertEqual(m.exact_probability([['a']],{'a':1}),1)
    def test_corrupted_lineage_counterexample(self):
        self.assertGreater(m.proof_bounds([['a'],['b']],{'a':.8,'b':.8})['lower'],.8)
    def test_benchmark_including_control(self):
        r=h5();self.assertTrue(r['primary_target_met']);self.assertTrue(r['negative_control']['false_admission'])
    def test_fingerprint_independent_of_hash_seed(self):
        code='from graph_synthesis.followup.run import h5; print(h5()["case_sha256"])'
        outputs=[subprocess.check_output([sys.executable,'-B','-c',code],env={**os.environ,'PYTHONHASHSEED':str(seed)}) for seed in (1,2)]
        self.assertEqual(outputs[0],outputs[1])
    def test_random_finite_oracles(self):
        rng=random.Random(SEED)
        for _ in range(100):
            p={a:rng.random() for a in 'abcd'}
            proofs=[rng.sample(list(p),rng.randint(1,4)) for _ in range(5)]
            exact=m.exact_probability(proofs,p);r=m.proof_bounds(proofs,p)
            self.assertLessEqual(r['lower'],exact+1e-12);self.assertGreaterEqual(r['upper'],exact-1e-12)


class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data,cls.audit=load_data()
    def test_source_purge_no_overlap(self):
        for audit in self.audit.values():self.assertEqual(audit['overlap_after_purge'],0)
    def test_primary_candidate_counts(self):
        self.assertEqual(len(self.data['rerun']['relation_support']['fewshot_contract']['evaluation']),339)
        self.assertEqual(len(self.data['rerun']['entity_resolution']['fewshot_contract']['evaluation']),413)
    def test_model_failures_retained(self):
        rows=self.data['rerun']['relation_support']['fewshot_contract']['evaluation']
        self.assertEqual(sum(r['error'] for r in rows),2)
    def test_h3_recall_full_gold_denominator(self):
        r=h3(self.data)['tasks']['relation_support']['fewshot_contract']
        for k in ('rerun_all','stable','confidence_matched'):self.assertEqual(r[k]['gold_positive'],209)
    def test_evaluation_gold_does_not_change_fits(self):
        changed=copy.deepcopy(self.data)
        for run in changed.values():
            for task in run.values():
                for arm in task.values():
                    for r in arm['evaluation']:r['gold']='same' if 'same' in r['probabilities'] else 'SUPPORTS'
        for task in self.data['original']:
            base='baseline_choice' if task=='relation_support' else 'baseline_noul'
            for d in (self.data,changed):
                self.assertEqual(m.fit_edge_route(d['original'][task][base]['calibration'],d['original'][task]['fewshot_contract']['calibration'],split='calibration')['policy'],
                                 m.fit_edge_route(self.data['original'][task][base]['calibration'],self.data['original'][task]['fewshot_contract']['calibration'],split='calibration')['policy'])
    def test_no_network_on_data_loading(self):
        with patch('socket.socket',side_effect=AssertionError('network forbidden')):
            data,_=load_data()
        self.assertEqual(len(data),2)


class PresentationTests(unittest.TestCase):
    def test_interval_labels_survive_json_key_sort(self):
        from graph_synthesis.followup.report import interval_series
        data=json.loads(json.dumps({'H4':{'strategies':{
            'exact_qualifier':{'missed_conflicts':1108,'false_conflicts':0},
            'qualifier_blind':{'missed_conflicts':0,'false_conflicts':1544},
            'interval_scope':{'missed_conflicts':0,'false_conflicts':0}}}},sort_keys=True))
        rows=interval_series(data)
        self.assertEqual([label for label,_ in rows],['Exact qualifiers','Ignore qualifiers','Interval + scope'])
        self.assertEqual([m['false_conflicts'] for _,m in rows],[0,1544,0])
        self.assertEqual([m['missed_conflicts'] for _,m in rows],[1108,0,0])


if __name__=='__main__':unittest.main()
