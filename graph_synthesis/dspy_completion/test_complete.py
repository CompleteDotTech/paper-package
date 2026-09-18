import unittest
import numpy as np
from .complete import eligible_metrics,expected_payload,analysis_view
from graph_synthesis.dspy_benchmark import study

class CompletionTests(unittest.TestCase):
    def test_uncertain_is_not_invented_binary_ground_truth(self):
        rows=[{'id':'a','gold_label':'same'},{'id':'b','gold_label':'different'},{'id':'c','gold_label':'uncertain'}]
        result=eligible_metrics(np.array([[.8,.2],[.1,.9],[.99,.01]]),rows,'entity_resolution')
        self.assertEqual(result['n'],2);self.assertEqual(result['input_rows'],3)
        self.assertEqual(result['ambiguous_fixture_rows'],1);self.assertEqual(result['accuracy'],1.)
    def test_other_unknown_labels_are_not_silently_dropped(self):
        with self.assertRaises(ValueError):eligible_metrics([[.8,.2]],[{'id':'a','gold_label':'mistyped'}],'entity_resolution')
        with self.assertRaises(ValueError):eligible_metrics([[.8,.1,.1]],[{'id':'a','gold_label':'uncertain'}],'relation_support')
    def test_original_fixture_populations(self):
        _,_,panels=study.prepare('entity_resolution');rows=panels['fixtures']
        self.assertEqual(len(rows),100)
        self.assertEqual(sum(r['gold_label']=='uncertain' for r in rows),12)
        result=eligible_metrics(np.tile([.8,.2],(100,1)),rows,'entity_resolution')
        self.assertEqual(result['n'],88);self.assertEqual(result['input_rows'],100)
    def test_fewshot_payload_keeps_fixed_examples_and_no_target_label(self):
        plan,parts,_=study.prepare('relation_support')
        q=plan['question_specs']['relation_support']['fewshot_contract']
        p=expected_payload('relation_support','fewshot_contract',parts['train'][0],[q]*11,parts['demonstrations'])
        self.assertEqual(len(p['state']['labeled_examples']),6)
        self.assertNotIn('gold_label',p['state']['input'])
        self.assertEqual(len(p['questions']),11)

if __name__=='__main__':unittest.main()
