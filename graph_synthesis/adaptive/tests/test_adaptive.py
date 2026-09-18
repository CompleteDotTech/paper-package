"""Regression and falsification controls; no service or gold-label access by policies."""
import copy
import unittest
from unittest.mock import patch

from graph_synthesis.adaptive.methods import *
from graph_synthesis.adaptive.run import assertion, oracle_optimum, oracle_valid, review_outcome


def call(label='SUPPORTS', tokens=10, error=None):
    return {'error':error,'response':{'answers':{'decision':{'probabilities':{k:float(k==label) for k in LABELS}}}},
            'tokens_used':{'input':tokens}}


def panel():
    return {k:call() for k in (*VIEWS,'checks','adjudicate')}


class RoutingTests(unittest.TestCase):
    def test_agree_skips_rich(self):
        result=compact_route(panel())
        self.assertEqual(result['sites'],['contrastive','blind1'])
        self.assertEqual(result['input_tokens'],20)

    def test_disagree_charges_rich(self):
        p=panel();p['blind1']=call('REFUTES');p['base1']=call('NOT_ENOUGH_INFO')
        result=compact_route(p)
        self.assertEqual(result['label'],'NOT_ENOUGH_INFO')
        self.assertEqual(result['input_tokens'],30)

    def test_compact_error_escalates(self):
        p=panel();p['contrastive']=call(error='bad')
        self.assertEqual(compact_route(p)['label'],'SUPPORTS')

    def test_reviewer_error_escalates(self):
        p=panel();p['blind1']=call(error='bad')
        self.assertIn('base1',compact_route(p)['sites'])

    def test_fallback_failure_stays_error(self):
        p=panel();p['blind1']=call('REFUTES');p['base1']=call(error='bad')
        self.assertEqual(compact_route(p)['label'],'ERROR')

    def test_confidence_has_no_reviewer_cost(self):
        self.assertEqual(compact_route(panel(),disagreement=False)['sites'],['contrastive'])

    def test_confidence_threshold(self):
        p=panel();p['contrastive']['response']['answers']['decision']['probabilities']={LABELS[0]:.8,LABELS[1]:.1,LABELS[2]:.1}
        self.assertIn('base1',compact_route(p,disagreement=False)['sites'])

    def test_deduplicate_accounting(self):
        self.assertEqual(charged({},['base1','base1'],panel())['input_tokens'],10)

    def test_unknown_usage_rejected(self):
        p=panel();p['contrastive']['tokens_used']=None
        with self.assertRaises(ValueError):compact_route(p)

    def test_negative_usage_rejected(self):
        p=panel();p['contrastive']['tokens_used']['input']=-1
        with self.assertRaises(ValueError):compact_route(p)


class FailureIsolationTests(unittest.TestCase):
    def test_invalid_base_uses_standalone_compact(self):
        p=panel();p['base1']=call(error='bad');p['contrastive']=call('REFUTES')
        result=safe_targeted(p)
        self.assertEqual(result['label'],'REFUTES')
        self.assertEqual(result['sites'],['base1','contrastive'])

    def test_invalid_checks_cannot_authorize_adjudication(self):
        p=panel();p['checks']=call(error='bad');p['adjudicate']={'do_not_read':True}
        self.assertEqual(safe_targeted(p)['label'],'SUPPORTS')
        self.assertEqual(safe_targeted(p)['sites'],['base1','checks'])

    def test_invalid_adjudication_keeps_base(self):
        p=panel();p['adjudicate']=call(error='bad')
        self.assertEqual(safe_targeted(p)['label'],'SUPPORTS')
        self.assertEqual(safe_targeted(p)['input_tokens'],30)

    def test_valid_chain_keeps_adjudication(self):
        p=panel();p['adjudicate']=call('REFUTES')
        self.assertEqual(safe_targeted(p)['label'],'REFUTES')

    def test_two_failures_remain_failure(self):
        p=panel();p['base1']=call(error='bad');p['contrastive']=call(error='bad')
        self.assertEqual(safe_targeted(p)['label'],'ERROR')


class VotingTests(unittest.TestCase):
    def development(self):
        return [{'id':str(i),'group':str(i),'split':'development','gold':'REFUTES',
                 'views':{v:{'label':'SUPPORTS'} for v in VIEWS}} for i in range(3)]

    def test_identical_errors_collapse(self):
        self.assertEqual(len(fit_clusters(self.development(),split='development')['clusters']),1)

    def test_test_fit_rejected(self):
        with self.assertRaises(ValueError):fit_clusters(self.development(),split='test')

    def test_mixed_fit_rejected(self):
        rows=self.development();rows[0]['split']='test'
        with self.assertRaises(ValueError):fit_clusters(rows,split='development')

    def test_no_errors_not_independence(self):
        rows=self.development()
        for row in rows:row['gold']='SUPPORTS'
        self.assertEqual(len(fit_clusters(rows,split='development')['clusters']),7)

    def test_one_cluster_cannot_emit_positive(self):
        self.assertEqual(ensemble(panel(),[list(VIEWS)])['label'],'ABSTAIN')

    def test_negative_needs_no_corroboration(self):
        p={k:call('NOT_ENOUGH_INFO') for k in VIEWS}
        self.assertEqual(ensemble(p,[list(VIEWS)])['label'],'NOT_ENOUGH_INFO')

    def test_flat_majority(self):
        self.assertEqual(ensemble(panel(),[[v] for v in VIEWS])['label'],'SUPPORTS')

    def test_invalid_component_is_error(self):
        p=panel();p['base1']=call(error='bad')
        self.assertEqual(ensemble(p,[[v] for v in VIEWS])['label'],'ERROR')

    def test_valid_same_cluster_view_can_replace_failure(self):
        p=panel();p['base1']=call(error='bad')
        groups=[['base1','base2']]+[[v] for v in VIEWS if v not in ('base1','base2')]
        self.assertEqual(ensemble(p,groups)['label'],'SUPPORTS')

    def test_duplicate_view_cluster_rejected(self):
        with self.assertRaises(ValueError):ensemble(panel(),[list(VIEWS),['base1']])

    def test_all_views_charged(self):
        self.assertEqual(ensemble(panel(),[[v] for v in VIEWS])['input_tokens'],70)


class ReviewTests(unittest.TestCase):
    def test_group_marginal_differs_from_individual(self):
        rows=[{'id':'a','group':'X','risk':.6},{'id':'b','group':'X','risk':.6},{'id':'c','group':'Y','risk':.4}]
        self.assertEqual(review_order(rows,group_aware=False)[0],'a')
        self.assertEqual(review_order(rows,group_aware=True)[0],'c')

    def test_stable_ties(self):
        rows=[{'id':'b','group':'Y','risk':.2},{'id':'a','group':'X','risk':.2}]
        self.assertEqual(review_order(rows,group_aware=True),['a','b'])

    def test_invalid_risk_rejected(self):
        with self.assertRaises(ValueError):review_order([{'id':'a','group':'X','risk':float('nan')}],group_aware=True)

    def test_duplicates_rejected(self):
        with self.assertRaises(ValueError):review_order([{'id':'a','risk':.2}]*2,group_aware=False)

    def test_test_risk_fit_rejected(self):
        with self.assertRaises(ValueError):fit_risk([{'split':'test'}],split='development')

    def test_empty_risk_fit_rejected(self):
        with self.assertRaises(ValueError):fit_risk([],split='development')

    def test_review_expected_contamination(self):
        data=[{'id':str(i),'group':'g','gold':'REFUTES','views':{'base1':{'label':'SUPPORTS'}}} for i in range(2)]
        result=review_outcome(data,{'0','1'},.5,0.)
        self.assertEqual(result['expected_contaminated_groups'],.75)
        self.assertEqual(result['expected_wrong_edges'],1.)

    def test_unreviewed_wrong_contaminates(self):
        data=[{'id':'a','group':'g','gold':'REFUTES','views':{'base1':{'label':'SUPPORTS'}}}]
        self.assertEqual(review_outcome(data,set())['expected_contaminated_groups'],1)

    def test_false_removal_cost(self):
        data=[{'id':'a','group':'g','gold':'SUPPORTS','views':{'base1':{'label':'SUPPORTS'}}}]
        self.assertEqual(review_outcome(data,{'a'},1.,.05)['expected_correct_edges'],.95)


class JointTests(unittest.TestCase):
    def example(self):
        return [assertion('wide',0,2,'B',5),assertion('early',0,1,'A',3),assertion('late',1,2,'A',3)]

    def test_joint_beats_greedy(self):
        rows=self.example()
        self.assertEqual(optimize_batch(rows)['utility'],6)
        self.assertEqual(greedy_batch(rows,priority=True)['utility'],5)

    def test_matches_independent_oracle(self):
        self.assertEqual(optimize_batch(self.example())['utility'],oracle_optimum(self.example()))

    def test_oracle_detects_collision(self):
        self.assertFalse(oracle_valid(self.example()))

    def test_permutation_invariance(self):
        self.assertEqual(optimize_batch(self.example()),optimize_batch(list(reversed(self.example()))))

    def test_half_open_endpoints(self):
        rows=[assertion('a',0,1,'A',1),assertion('b',1,2,'B',1)]
        self.assertEqual(optimize_batch(rows)['utility'],2)

    def test_scope_separates_components(self):
        rows=[assertion('a',0,2,'A',1),assertion('b',0,2,'B',1,scope='B')]
        self.assertEqual(optimize_batch(rows)['utility'],2)

    def test_opposite_polarities_conflict(self):
        rows=[assertion('a',0,2,'A',1),assertion('b',0,2,'A',2,polarity=-1)]
        self.assertEqual(optimize_batch(rows)['selected'],['b'])

    def test_unknown_staged(self):
        rows=self.example();rows[0]['scope']=None
        self.assertEqual(optimize_batch(rows)['staged'],['wide'])

    def test_nonfinite_weight_staged(self):
        rows=self.example();rows[0]['weight']=float('inf')
        self.assertEqual(optimize_batch(rows)['staged'],['wide'])

    def test_negative_weight_staged(self):
        rows=self.example();rows[0]['weight']=-1
        self.assertEqual(optimize_batch(rows)['staged'],['wide'])

    def test_oversized_component_staged(self):
        rows=[assertion(str(i),0,2,str(i),1) for i in range(17)]
        self.assertEqual(len(optimize_batch(rows)['staged']),17)
        self.assertEqual(optimize_batch(rows)['selected'],[])

    def test_component_not_batch_limit(self):
        rows=[assertion(str(i),0,2,str(i),1,scope=str(i)) for i in range(17)]
        self.assertEqual(len(optimize_batch(rows)['selected']),17)

    def test_invalid_limit_rejected(self):
        with self.assertRaises(ValueError):optimize_batch(self.example(),limit=17)

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):optimize_batch(self.example()*2)

    def test_empty_batch(self):
        self.assertEqual(optimize_batch([])['selected'],[])

    def test_weights_not_truth(self):
        rows=[assertion('false',0,2,'B',9),assertion('true',0,2,'A',8)]
        self.assertEqual(optimize_batch(rows)['selected'],['false'])

    def test_stable_zero_weight_ties(self):
        self.assertEqual(optimize_batch([assertion('a',0,2,'A',0)])['selected'],[])


if __name__=='__main__':unittest.main()
