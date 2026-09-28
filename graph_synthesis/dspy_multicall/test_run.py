"""Mock wiring tests, distinct from live benchmark evidence."""
import unittest
from graph_synthesis.dspy_benchmark.study import prepare, read, ROOT, EXTRA
from graph_synthesis.multicall import ARMS, LABELS
from .run import evaluate_row

class FakeLive:
    def __init__(self):self.calls=[]
    def send(self,payload,site):
        self.calls.append((payload,site));answers={}
        for key,q in payload['questions'].items():
            labels=list(q['criteria']);choice='SUPPORTS' if 'SUPPORTS' in labels else 'MATCH'
            probs={l: .9 if l==choice else .1/(len(labels)-1) for l in labels}
            answers[key]={'type':'choice','choice':choice,'probabilities':probs,'confidence':.7}
        return {'model':'jev-1.13.0','answers':answers}

class TestTransfer(unittest.TestCase):
    def test_all_workflows_preserve_labels_and_call_structure(self):
        original,_,_=prepare('relation_support');q=original['question_specs']['relation_support']['fewshot_contract']
        plan=read(ROOT/EXTRA);live=FakeLive();variants=[('baseline',0,q),('dspy',17,q)]
        result=evaluate_row(plan['rows'][0],plan,variants,live,'evaluation')
        self.assertEqual(len(live.calls),8)
        self.assertEqual(len(result['variants']),2)
        for v in result['variants']:
            self.assertEqual(set(v['workflows']),set(ARMS))
            for row in v['workflows'].values():
                self.assertEqual(row['label'],'SUPPORTS');self.assertAlmostEqual(sum(row['forecast']),1)
        for payload,site in live.calls:
            self.assertNotIn('gold_label',payload['state'])
        adjudications=[p for p,s in live.calls if '/adjudicate/' in s]
        for p in adjudications:self.assertIn('dimension_checks',p['state'])

if __name__=='__main__':unittest.main()
