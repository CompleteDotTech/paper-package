"""Newly correct edges must not replace lost baseline edges in retention."""
import unittest
from unittest.mock import patch
from graph_synthesis.novel_mechanisms.run import shift_benchmark


class RetentionTests(unittest.TestCase):
    def test_added_correct_edges_do_not_mask_lost_correct_edges(self):
        rows=[]
        for name in 'abcd':
            label='SUPPORTS' if name in 'ab' else 'NOT_ENOUGH_INFO'
            rows.append({'id':name,'group':name,'gold':'SUPPORTS',
                'views':{'base1':{'label':label,'score':.9,'status':'ok'}},
                'arms':{'single':{'input_tokens':1}}})
        changed=[{'id':name,'label':'REFUTES' if name=='b' else 'SUPPORTS',
                  'score':.9,'status':'ok'} for name in 'abcd']
        with patch('graph_synthesis.novel_mechanisms.run.fit_shift',return_value={'valid_target':4}), \
             patch('graph_synthesis.novel_mechanisms.run.apply_shift',return_value=changed), \
             patch('graph_synthesis.novel_mechanisms.run.bootstrap',return_value={}):
            got=shift_benchmark([],rows)
        self.assertEqual(got['natural']['baseline']['correct'],2)
        self.assertEqual(got['natural']['proposed']['correct'],3)
        self.assertEqual(got['retained_baseline_correct_ids'],['a'])
        self.assertEqual(got['lost_baseline_correct_ids'],['b'])
        self.assertEqual(got['correct_retention'],.5)
        self.assertFalse(got['primary_target_met'])


if __name__=='__main__':unittest.main()
