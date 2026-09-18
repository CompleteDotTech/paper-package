import unittest
from copy import deepcopy
from graph_synthesis.multicall import decisions, payloads, SITES, CONTRASTS


def call(label="SUPPORTS", score=.96):
    values = {k:(score if k==label else (1-score)/2) for k in ("SUPPORTS","REFUTES","NOT_ENOUGH_INFO")}
    return {"error":None,"response":{"answers":{"decision":{"probabilities":values}}},"tokens_used":{"input":10}}


class MulticallTests(unittest.TestCase):
    def test_three_way_disagreement_abstains(self):
        calls={s:call() for s in SITES}
        calls['base2']=call('REFUTES'); calls['base3']=call('NOT_ENOUGH_INFO')
        self.assertEqual(decisions(calls)['repeat_vote']['label'],'ABSTAIN')

    def test_failed_repeat_does_not_disappear(self):
        calls={s:call() for s in SITES}
        calls['base2']={"error":"invalid","tokens_used":None}
        self.assertEqual(decisions(calls)['repeat_vote']['status'],'error')
        self.assertEqual(decisions(calls)['single']['status'],'ok')
        self.assertEqual(decisions(calls)['repeat_vote']['unknown_usage_calls'],1)

    def test_targeted_requires_valid_checks(self):
        calls={s:call() for s in SITES}; calls['checks']['error']='bad distribution'
        self.assertEqual(decisions(calls)['targeted']['status'],'error')

    def test_selective_threshold_and_required_cost(self):
        calls={s:call() for s in SITES}
        self.assertEqual(decisions(calls)['selective']['sites'],['base1'])
        calls['base1']=call(score=.89); calls['adjudicate']=call('REFUTES')
        self.assertEqual(decisions(calls)['selective']['label'],'REFUTES')
        self.assertEqual(decisions(calls)['selective']['input_tokens'],30)

    def test_majority_is_not_probability_product(self):
        calls={s:call() for s in SITES}
        calls['base3']=call('REFUTES')
        result=decisions(calls)['repeat_vote']
        self.assertEqual(result['label'],'SUPPORTS')
        self.assertAlmostEqual(result['score'],(.96+.96+.02)/3)

    def test_gold_rationale_and_other_answers_absent_from_blind_requests(self):
        row={'claim':'X','evidence':['One.','Two.'],'gold_label':'SUPPORTS','rationale_sentence_ids':[1]}
        plan={'demonstrations':[],'contrasts':CONTRASTS}
        original=payloads(row,plan)
        changed=deepcopy(row); changed['gold_label']='REFUTES'; changed['rationale_sentence_ids']=[0]
        self.assertEqual(original,payloads(changed,plan))
        self.assertEqual(original['base1'],original['base2'])
        self.assertEqual(original['base2'],original['base3'])
        for key in ('blind1','blind2'):
            self.assertEqual(set(original[key]['state']),{'claim','evidence'})
        indexed=original['structured']['state']['input']['evidence']
        self.assertEqual([s['text'] for s in indexed],row['evidence'])
