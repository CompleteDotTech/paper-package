"""Random fixtures test statistics, not model accuracy."""
import unittest
import numpy as np
from graph_synthesis.dspy_benchmark.study import evaluate_metrics, LABELS
from .report import clusters, weighted_scores, paired_interval

class TestReport(unittest.TestCase):
    def test_overlapping_identity_units_share_component(self):
        result=clusters([{'groups':['a','b']},{'groups':['b','c']},{'groups':['d']},{'groups':['e','c']}])
        self.assertEqual([x.tolist() for x in result],[[0,1,3],[2]])
    def test_weighted_bootstrap_matches_direct_evaluation(self):
        rng=np.random.default_rng(17)
        for task,k in [('relation_support',3),('entity_resolution',2)]:
            for repeat in range(10):
                p=rng.dirichlet(np.ones(k),40);y=rng.integers(k,size=40)
                w=rng.multinomial(40,np.full(40,1/40),size=5).astype(float)
                calculated=weighted_scores(p,y,w)
                for j in range(5):
                    idx=np.repeat(np.arange(40),w[j].astype(int))
                    rows=[{'id':str(i),'gold_label':LABELS[task][y[i]]} for i in idx]
                    direct=evaluate_metrics(p[idx],rows,task)
                    for m in calculated:self.assertAlmostEqual(direct[m],calculated[m][j],places=12)
    def test_identical_predictions_have_zero_paired_effect(self):
        p=np.array([[.7,.3],[.2,.8],[.8,.2],[.4,.6]])
        rows=[{'id':str(i),'gold_label':['same','different'][i%2],'groups':[str(i)]} for i in range(4)]
        results=paired_interval(p,[p.copy() for _ in range(5)],rows,['same','different'])
        self.assertEqual(results['n_examples'],4)
        self.assertEqual(results['n_source_components'],4)
        for value in results['metrics'].values():
            self.assertAlmostEqual(value['mean_paired_delta'],0,places=12)
            np.testing.assert_allclose(value['cluster_bootstrap_95_percentile'],[0,0],atol=1e-12)

if __name__=='__main__':unittest.main()
