import copy
import unittest
import numpy as np
from .study import (prepare, ARMS, probabilities, temperature, fit_calibration,
                    calibrated, evaluate_metrics, validate_questions, nll)

class TestStudy(unittest.TestCase):
    def test_all_archived_splits_and_panels(self):
        for task in ARMS:
            _,parts,panels=prepare(task)
            self.assertEqual(len(parts['train'])+len(parts['validation']),60)
            self.assertEqual(len(panels['evaluation']),339 if task=='relation_support' else 413)
    def test_temperature_preserves_argmax(self):
        p=np.random.default_rng(17).dirichlet([1,2,3],100)
        for t in [.05,.2,1,4,20]:
            q=temperature(p,t)
            np.testing.assert_allclose(q.sum(axis=1),1)
            np.testing.assert_array_equal(np.argmax(p,axis=1),np.argmax(q,axis=1))
    def test_bad_temperature_rejected(self):
        for t in [0,-1,float('nan'),float('inf')]:
            with self.assertRaises(ValueError):temperature([[.5,.5]],t)
    def test_calibration_never_uses_test_labels(self):
        p=np.array([[.99,.01],[.99,.01],[.01,.99],[.01,.99]])
        fit=fit_calibration(p,[0,1,0,1])
        self.assertGreater(fit['temperature'],1)
        self.assertLess(nll(calibrated(p,fit,'temperature'),[0,1,0,1]),nll(p,[0,1,0,1]))
    def test_all_calibration_distributions(self):
        rng=np.random.default_rng(4);p=rng.dirichlet([1,1,1],120);y=rng.integers(3,size=120)
        fit=fit_calibration(p,y)
        for method in ['raw','temperature','temperature_bias']:
            q=calibrated(p,fit,method)
            self.assertTrue(np.all(np.isfinite(q)));np.testing.assert_allclose(q.sum(axis=1),1)
    def test_question_schema_stable(self):
        original={'a':{'type':'choice','instructions':'judge','criteria':{'x':'x','y':'y'}}}
        bad=copy.deepcopy(original);bad['a']['criteria']['z']='z'
        with self.assertRaises(ValueError):validate_questions(bad,original)
        bad=copy.deepcopy(original);bad['a']['type']='noul'
        with self.assertRaises(ValueError):validate_questions(bad,original)
        self.assertEqual(validate_questions(original,original),original)
    def test_conditional_nouls(self):
        q={'a':{'type':'noul'},'b':{'type':'noul'}}
        p=probabilities({'a':{'noul':.8},'b':{'noul':.5}},'relation_support',q)
        np.testing.assert_allclose(p,[.8,.1,.1])
    def test_unknown_probability_rejected(self):
        with self.assertRaises(ValueError):probabilities({'a':{'type':'choice','probabilities':{'z':1}}},'entity_resolution',{'a':{}})
    def test_noul_out_of_range(self):
        with self.assertRaises(ValueError):probabilities({'a':{'type':'noul','noul':2}},'entity_resolution',{'a':{}})
    def test_metrics_and_wrong_merges(self):
        rows=[{'id':'a','gold_label':'same'},{'id':'b','gold_label':'different'}]
        result=evaluate_metrics(np.array([[.99,.01],[.8,.2]]),rows,'entity_resolution')
        self.assertEqual(result['accuracy'],.5);self.assertEqual(result['wrong_positive_edges'],1)
        self.assertEqual(result['correct_positive_edges'],1)

if __name__=='__main__':unittest.main()
