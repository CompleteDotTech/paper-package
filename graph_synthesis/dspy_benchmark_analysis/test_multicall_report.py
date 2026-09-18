import copy
import unittest
from graph_synthesis.multicall import ARMS
from .multicall_report import policy_metrics,policy_paired_interval

class PolicyTests(unittest.TestCase):
    def rows(self):
        rows=[]
        for i,(gold,pred,status) in enumerate([('SUPPORTS','SUPPORTS','ok'),('REFUTES','ABSTAIN','abstain'),('NOT_ENOUGH_INFO','SUPPORTS','ok')]):
            variant={'workflows':{arm:{'label':pred,'status':status} for arm in ARMS}}
            rows.append({'id':str(i),'group':str(i),'gold_label':gold,'variants':[copy.deepcopy(variant) for _ in range(6)]})
        return rows
    def test_abstentions_count_as_errors_unconditionally(self):
        result=policy_metrics(self.rows(),'repeat_vote',0)
        self.assertAlmostEqual(result['accuracy'],1/3)
        self.assertAlmostEqual(result['coverage'],2/3)
        self.assertAlmostEqual(result['conditional_accuracy'],.5)
        self.assertEqual(result['abstentions_or_errors'],1)
        self.assertEqual(result['wrong_positive_edges'],1)
        self.assertEqual(result['correct_positive_edges'],1)
    def test_identical_policy_replicates_do_not_inflate_sample(self):
        result=policy_paired_interval(self.rows(),'repeat_vote')
        self.assertEqual(result['n_examples'],3)
        self.assertEqual(result['mean_accuracy_delta'],0.)
        self.assertEqual(result['cluster_bootstrap_95_percentile'],[0.,0.])

if __name__=='__main__':unittest.main()
