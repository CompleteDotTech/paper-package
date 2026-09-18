"""Protect additive manuscript composition and full-denominator metrics."""
import unittest
import json
from graph_synthesis.adaptive.report import START, END, replace_section
from graph_synthesis.adaptive.run import summary, select, review_outcome


class ReportingTests(unittest.TestCase):
    def test_additive_update_keeps_history(self):
        section=START+'\nnew\n'+END
        self.assertTrue(replace_section('historical results',section).endswith('historical results'))

    def test_update_is_idempotent(self):
        section=START+'\nnew\n'+END
        once=replace_section('historical results',section)
        self.assertEqual(replace_section(once,section),once)

    def test_replacing_preserves_both_sides(self):
        text='before\n'+START+'\nold\n'+END+'\nafter'
        result=replace_section(text,START+'\nnew\n'+END)
        self.assertIn('before\nafter',result)
        self.assertNotIn('\nold\n',result)

    def test_missing_end_fails(self):
        with self.assertRaises(ValueError):replace_section(START+'\ntext','replacement')

    def test_missing_start_fails(self):
        with self.assertRaises(ValueError):replace_section('text\n'+END,'replacement')


class MetricBoundaryTests(unittest.TestCase):
    def rows(self):
        pairs=[('SUPPORTS','SUPPORTS'),('SUPPORTS','REFUTES'),
               ('SUPPORTS','NOT_ENOUGH_INFO'),('ERROR','SUPPORTS'),
               ('ABSTAIN','REFUTES'),('NOT_ENOUGH_INFO','NOT_ENOUGH_INFO')]
        result=[]
        for i,(label,gold) in enumerate(pairs):
            answer={'label':label,'status':'error' if label=='ERROR' else 'abstain' if label=='ABSTAIN' else 'ok',
                    'score':.9 if label not in ('ERROR','ABSTAIN') else None,'input_tokens':10,
                    'sites':['base1'],'unknown_usage_calls':0}
            result.append({'id':str(i),'group':str(i),'gold':gold,'arms':{'single':answer},'views':{'base1':answer}})
        return result

    def test_operational_failures_remain_denominator(self):
        value=summary(self.rows(),'single')
        self.assertEqual(value['n'],6)
        self.assertEqual(value['errors'],1)
        self.assertEqual(value['abstentions'],1)
        self.assertEqual(value['input_tokens'],60)

    def test_metric_types_match_saved_json(self):
        from graph_synthesis.verify import compare_json
        value=summary(self.rows(),'single')
        self.assertEqual(compare_json(json.loads(json.dumps(value)),value),[])

    def test_wrong_polarity_is_wrong_accepted_edge(self):
        value=summary(self.rows(),'single')
        self.assertEqual(value['accepted'],3)
        self.assertEqual(value['correct_edges'],1)
        self.assertEqual(value['wrong_edges'],2)
        self.assertAlmostEqual(value['recall'],1/4)

    def test_matched_selection_uses_id_tie_break(self):
        self.assertEqual(select(list(reversed(self.rows())),'single',2),{'0','1'})

    def test_ideal_review_does_not_add_missing_edges(self):
        value=review_outcome(self.rows(),{'0','1','2'})
        self.assertEqual(value['expected_wrong_edges'],0)
        self.assertEqual(value['expected_correct_edges'],1)


if __name__=='__main__':unittest.main()
