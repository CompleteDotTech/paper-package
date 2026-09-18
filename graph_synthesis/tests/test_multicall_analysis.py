import unittest
import numpy as np
from graph_synthesis.analyze_multicall import vector, scores, group_vectors


def row(i,gold,label,group='a'):
    return {'id':str(i),'group':group,'gold':gold,'arms':{'single':{
        'label':label,'sites':['base1'],'input_tokens':10,'unknown_usage_calls':0}}}


class EdgeAccountingTests(unittest.TestCase):
    def test_wrong_polarity_is_false_edge_and_missed_gold(self):
        data=[row(1,'SUPPORTS','REFUTES'),row(2,'REFUTES','REFUTES'),row(3,'NOT_ENOUGH_INFO','ABSTAIN')]
        s=scores(sum((vector(r,'single') for r in data),np.zeros(23)))
        self.assertEqual((s['accepted'],s['correct_edges'],s['wrong_edges'],s['gold_edges']),(2,1,1,2))
        self.assertEqual(s['recall'],.5)
        self.assertEqual(s['accuracy'],1/3)
        self.assertEqual(s['abstentions'],1)

    def test_empty_acceptance_has_undefined_precision(self):
        s=scores(vector(row(1,'SUPPORTS','ERROR'),'single'))
        self.assertIsNone(s['precision'])
        self.assertEqual(s['recall'],0)
        self.assertEqual(s['errors'],1)

    def test_matched_selection_preserves_denominators(self):
        data=[row(1,'SUPPORTS','SUPPORTS'),row(2,'SUPPORTS','SUPPORTS')]
        s=scores(sum((vector(r,'single',{'1'}) for r in data),np.zeros(23)))
        self.assertEqual(s['accepted'],1)
        self.assertEqual(s['gold_edges'],2)
        self.assertEqual(s['recall'],.5)

    def test_components_keep_dependent_rows_together(self):
        data=[row(1,'SUPPORTS','SUPPORTS','a'),row(2,'SUPPORTS','REFUTES','a'),row(3,'REFUTES','REFUTES','b')]
        grouped=group_vectors(data,'single',['a','b'])
        self.assertEqual(grouped[:,0].tolist(),[2,1])
        self.assertEqual(scores(grouped[0]*2)['wrong_edges'],2)
