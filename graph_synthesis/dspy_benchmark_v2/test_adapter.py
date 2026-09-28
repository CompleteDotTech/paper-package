import json
import unittest
import numpy as np
from .adapter import distribution,probabilities,InvalidServiceResponse,signature,FlatPredictor

class AdapterTests(unittest.TestCase):
    def test_observed_decimal_mass_defect(self):
        p=distribution([.93,.05,.01]);self.assertAlmostEqual(sum(p),1)
        np.testing.assert_allclose(p,[.93/.99,.05/.99,.01/.99])
    def test_larger_or_unexplained_defects_rejected(self):
        for p in [[.9,.05,.01],[.934,.05,.01],[0,0,0],[1.01,-.01],[float('nan'),1],[True,0]]:
            with self.assertRaises(InvalidServiceResponse):distribution(p)
    def test_normalization_preserves_argmax(self):
        for p in [[.34,.34,.33],[.01,.05,.93],[.8,.2]]:
            self.assertEqual(np.argmax(p),np.argmax(distribution(p)))
    def test_wrong_answer_type_is_service_failure(self):
        with self.assertRaises(InvalidServiceResponse):
            probabilities({'x':{'type':'choice'}},'entity_resolution',{'x':{'type':'noul'}})
    def test_conditional_order_and_invalid_noul(self):
        q={'support':{'type':'noul'},'conditional_refute':{'type':'noul'}}
        answers={'support':{'type':'noul','noul':.8},'conditional_refute':{'type':'noul','noul':.5}}
        np.testing.assert_allclose(probabilities(answers,'relation_support',q),[.8,.1,.1])
        answers['support']['noul']=-1
        with self.assertRaises(InvalidServiceResponse):probabilities(answers,'relation_support',q)
    def test_actual_dspy_fixed_fields_and_output_mapping(self):
        import dspy
        from dspy.utils.dummies import DummyLM
        question={'type':'choice','instructions':'Judge','criteria':{'SUPPORTS':'yes','REFUTES':'no','NOT_ENOUGH_INFO':'unknown'}}
        self.assertEqual(set(signature(question).output_fields),{'revised_question','criterion_0','criterion_1','criterion_2'})
        lm=DummyLM([{'revised_question':'Use the evidence.','criterion_0':'supports','criterion_1':'contradicts','criterion_2':'unresolved'}],adapter=dspy.JSONAdapter())
        with dspy.context(lm=lm,adapter=dspy.JSONAdapter()):
            p=FlatPredictor(lm)(task='relation_support',questions_json=json.dumps([question]),training_feedback_json='[]',iteration=1)
        self.assertEqual(p.improved_instructions,['Use the evidence.'])
        self.assertEqual(p.improved_criteria,[{'SUPPORTS':'supports','REFUTES':'contradicts','NOT_ENOUGH_INFO':'unresolved'}])
    def test_actual_dspy_two_atomic_nouls(self):
        import dspy
        from dspy.utils.dummies import DummyLM
        q=[{'type':'noul','instructions':'support?'},{'type':'noul','instructions':'refute if no support?'}]
        lm=DummyLM([{'revised_question':'Does evidence support?'},{'revised_question':'Otherwise, does evidence refute?'}],adapter=dspy.JSONAdapter())
        with dspy.context(lm=lm,adapter=dspy.JSONAdapter()):
            p=FlatPredictor(lm)(task='relation_support',questions_json=json.dumps(q),training_feedback_json='[]',iteration=1)
        self.assertEqual(len(p.improved_instructions),2);self.assertEqual(p.improved_criteria,[{},{}])

if __name__=='__main__':unittest.main()
