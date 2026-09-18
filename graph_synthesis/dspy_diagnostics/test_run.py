import unittest
from graph_synthesis.dspy_benchmark import study
from .run import bank_call

class FakeLive:
    def __init__(self):self.payloads=[]
    def send(self,payload,site):
        self.payloads.append(payload);answers={}
        for key,q in payload['questions'].items():
            if q['type']=='noul':answers[key]={'type':'noul','noul':.8}
            else:
                labels=list(q['criteria']);answers[key]={'type':'choice','choice':labels[0],'probabilities':{l:1/len(labels) for l in labels}}
        return {'model':study.MODEL,'answers':answers}

class DiagnosticsTests(unittest.TestCase):
    def test_original_batch_panels_are_development(self):
        for task in study.ARMS:
            plan,parts,_=study.prepare(task);data=plan['tasks'][task]
            self.assertTrue(set(data['batching_ids'])<={r['id'] for r in data['development']})
            self.assertTrue(set(data['repeatability_ids'])<={r['id'] for r in data['evaluation']})
    def test_cross_formulation_bank_retains_every_typed_question(self):
        plan,parts,_=study.prepare('relation_support');specs=plan['question_specs']['relation_support']
        bank=[(arm,i,specs[arm]) for arm in study.ARMS['relation_support'] if arm!='fewshot_contract' for i in range(6)]
        live=FakeLive();row=parts['train'][0]
        results=bank_call(live,'relation_support',row,bank,parts['demonstrations'],'test-only')
        self.assertEqual(len(results),18);self.assertEqual(len(live.payloads[0]['questions']),24)
        self.assertNotIn('gold_label',live.payloads[0]['state'])
        for p in results.values():self.assertAlmostEqual(sum(p),1)
    def test_fewshot_state_cannot_be_mixed_with_plain_state(self):
        plan,parts,_=study.prepare('relation_support');spec=plan['question_specs']['relation_support']
        with self.assertRaises(ValueError):
            bank_call(FakeLive(),'relation_support',parts['train'][0],
                [('baseline_choice',0,spec['baseline_choice']),('fewshot_contract',0,spec['fewshot_contract'])],parts['demonstrations'],'test-only')

if __name__=='__main__':unittest.main()
