"""Independent controls for risk bounds, gold isolation and optimization."""
import copy
from itertools import combinations
import math
import random
import unittest
from graph_synthesis.multicall import CHECKS
from graph_synthesis.adaptive.run import assertion, oracle_optimum, oracle_valid
from graph_synthesis.risk_control.methods import *


def call(label='SUPPORTS',score=.95,tokens=10,error=None):
    labels=('SUPPORTS','REFUTES','NOT_ENOUGH_INFO')
    p={x:score if x==label else (1-score)/2 for x in labels}
    return {'error':error,'tokens_used':{'input':tokens},'response':{'answers':{'decision':{'probabilities':p}}}}


def checks(dimension=None,p=.95,error=None):
    a={k:{'probabilities':{'MATCH':1.,'MISMATCH':0.,'UNRESOLVED':0.,'NOT_APPLICABLE':0.}} for k in CHECKS}
    if dimension:a[dimension]['probabilities'].update(MATCH=1-p,MISMATCH=p)
    return {'error':error,'tokens_used':{'input':20},'response':{'answers':a}}


class RoutingTests(unittest.TestCase):
    def panel(self):return {'base1':call('REFUTES',tokens=30),'contrastive':call(tokens=10)}
    def test_direct_cost(self):
        a=route(self.panel(),{'mode':'direct_rich'});self.assertEqual(a['input_tokens'],30);self.assertEqual(a['sites'],['base1'])
    def test_compact_cost(self):
        a=route(self.panel(),{'mode':'learned','actions':{'SUPPORTS:True':False}});self.assertEqual(a['label'],'SUPPORTS');self.assertEqual(a['input_tokens'],10)
    def test_escalation_cost(self):
        a=route(self.panel(),{'mode':'learned','actions':{}});self.assertEqual(a['label'],'REFUTES');self.assertEqual(a['input_tokens'],40)
    def test_invalid_always_escalates(self):
        p=self.panel();p['contrastive']['error']='invalid';self.assertEqual(route(p,{'mode':'learned','actions':{'ERROR:False':False}})['label'],'REFUTES')
    def test_unknown_usage(self):
        p=self.panel();p['base1']['tokens_used']=None
        with self.assertRaises(ValueError):route(p,{'mode':'direct_rich'})
    def test_nonmutation(self):
        p=self.panel();old=copy.deepcopy(p);route(p,{'mode':'learned','actions':{}});self.assertEqual(p,old)
    def test_no_gold_execution(self):
        class Guard(dict):
            def __getitem__(self,key):
                if key=='gold':raise AssertionError('gold accessed')
                return super().__getitem__(key)
        self.assertEqual(route(Guard(self.panel()),{'mode':'direct_rich'})['label'],'REFUTES')
    def test_fit_isolation(self):
        for rows,split in [([], 'development'),([{'split':'test'}],'development'),([{'split':'test'}],'test')]:
            with self.subTest(rows=rows,split=split),self.assertRaises(ValueError):fit_router(rows,{},split=split)
    def test_utility_polarity(self):
        self.assertEqual(edge_utility({'label':'REFUTES'},'SUPPORTS'),-5);self.assertEqual(edge_utility({'label':'NOT_ENOUGH_INFO'},'SUPPORTS'),0)


class RiskTests(unittest.TestCase):
    def test_analytic_zero_events(self):self.assertAlmostEqual(binomial_upper(0,40,.01),1-.01**(1/40),places=14)
    def test_no_evidence_and_all_wrong(self):
        self.assertEqual(binomial_upper(0,0,.01),1);self.assertEqual(binomial_upper(40,40,.01),1)
    def test_monotonicity_and_multiplicity(self):
        x=[binomial_upper(k,40,.01) for k in range(41)];self.assertEqual(x,sorted(x));self.assertGreater(binomial_upper(2,40,.01),binomial_upper(2,40,.05))
    def test_exact_tail(self):
        p=binomial_upper(3,40,.01);self.assertAlmostEqual(sum(math.comb(40,i)*p**i*(1-p)**(40-i) for i in range(4)),.01,places=12)
    def test_invalid_counts(self):
        for args in ((-1,5,.05),(6,5,.05),(1.0,5,.05),(1,5,0),(1,5,1)):
            with self.subTest(args=args),self.assertRaises(ValueError):binomial_upper(*args)
    def test_explicit_no_certificate(self):self.assertEqual(threshold_gate({'label':'SUPPORTS'},None)['reason'],'no_nontrivial_certificate')
    def test_gate_boundaries(self):
        for label,score in [('SUPPORTS',.9),('NOT_ENOUGH_INFO',.1),('ERROR',None)]:
            a={'label':label,'score':score};self.assertEqual(threshold_gate(a,.9),a)
        self.assertEqual(threshold_gate({'label':'SUPPORTS','score':.8},.9)['label'],'ABSTAIN')
    def test_gate_fit_isolation(self):
        with self.assertRaises(ValueError):fit_gate([{'split':'test'}],split='development')
    def rows(self,groups=True,gold='SUPPORTS'):
        return [{'id':str(i),'group':str(i) if groups else 'g','split':'development','gold':gold,'arms':{'safe_targeted':{'label':'SUPPORTS','score':1}}} for i in range(40)]
    def test_groups_not_rows(self):
        fit=fit_gate(self.rows(False),split='development');self.assertFalse(fit['nontrivial']);self.assertEqual(fit['candidates'][0]['groups'],1)
    def test_all_wrong_never_certifies(self):self.assertFalse(fit_gate(self.rows(gold='REFUTES'),split='development')['nontrivial'])
    def test_zero_wrong_can_qualify(self):self.assertTrue(fit_gate(self.rows(),split='development')['nontrivial'])


class VetoTests(unittest.TestCase):
    def test_support_veto(self):
        a=qualifier_veto({'base1':call(),'checks':checks('population')});self.assertEqual(a['label'],'ABSTAIN');self.assertEqual(a['dimensions'],['population'])
    def test_non_support_no_checks(self):
        for label in ('REFUTES','NOT_ENOUGH_INFO'):
            a=qualifier_veto({'base1':call(label)});self.assertEqual(a['label'],label);self.assertEqual(a['sites'],['base1'])
    def test_invalid_stays_error(self):self.assertEqual(qualifier_veto({'base1':call(),'checks':checks(error='invalid')})['label'],'ERROR')
    def test_no_adjudicator(self):self.assertEqual(qualifier_veto({'base1':call(),'checks':checks()})['sites'],['base1','checks'])
    def test_threshold_inclusive(self):
        for p,want in ((.89,'SUPPORTS'),(.90,'ABSTAIN'),(1.,'ABSTAIN')):
            self.assertEqual(qualifier_veto({'base1':call(),'checks':checks('time',p)})['label'],want)
    def test_ablation(self):self.assertEqual(qualifier_veto({'base1':call(),'checks':checks('time')},veto=False)['label'],'SUPPORTS')
    def test_malformed_not_normalized(self):
        p={'base1':call(),'checks':checks()};p['checks']['response']['answers']['time']['probabilities']['MATCH']=2
        with self.assertRaises(ValueError):qualifier_veto(p)
    def test_missing_dimension(self):
        p={'base1':call(),'checks':checks()};del p['checks']['response']['answers']['time']
        with self.assertRaises(ValueError):qualifier_veto(p)
    def test_nonmutation(self):
        p={'base1':call(),'checks':checks('time')};old=copy.deepcopy(p);qualifier_veto(p);self.assertEqual(old,p)


class ReviewTests(unittest.TestCase):
    def rows(self):return [{'id':'a','group':'A','risk':.9},{'id':'b','group':'A','risk':.9},{'id':'c','group':'B','risk':.2}]
    def test_complementarity(self):
        r=self.rows();a=optimal_review(r,2);b=greedy_review(r,2);self.assertEqual(a,['a','b']);self.assertLess(model_contamination(r,set(a)),model_contamination(r,set(b)))
    def test_budget_boundaries(self):
        self.assertEqual(optimal_review(self.rows(),0),[]);self.assertEqual(optimal_review(self.rows(),9),['a','b','c']);self.assertEqual(optimal_review([],9),[])
    def test_invalid_inputs(self):
        for rows,budget in [(self.rows(),-1),(self.rows()*2,1),([{'id':'a','group':'a','risk':float('nan')}],1)]:
            with self.subTest(rows=rows,budget=budget),self.assertRaises(ValueError):optimal_review(rows,budget)
    def test_permutation(self):self.assertEqual(optimal_review(self.rows(),2),optimal_review(self.rows()[::-1],2))
    def test_nonmutation(self):
        r=self.rows();old=copy.deepcopy(r);optimal_review(r,2);self.assertEqual(old,r)
    def test_risk_boundaries(self):self.assertEqual(optimal_review([{'id':'a','group':'A','risk':1.},{'id':'b','group':'A','risk':0.}],1),['a'])
    def test_independent_subset_oracle(self):
        rng=random.Random(4)
        for _ in range(20):
            rows=[{'id':str(i),'group':str(rng.randrange(3)),'risk':rng.random()} for i in range(7)]
            def truth(keys):
                return sum(1-math.prod(1-r['risk']*(.25 if r['id'] in keys else 1) for r in rows if r['group']==g) for g in {r['group'] for r in rows})
            optimum=min(truth(set(keys)) for keys in combinations([r['id'] for r in rows],3))
            self.assertAlmostEqual(truth(set(optimal_review(rows,3))),optimum)


class ForestTests(unittest.TestCase):
    def test_empty_single(self):
        self.assertEqual(forest_batch([])['utility'],0);self.assertEqual(forest_batch([assertion('a',0,1,'A',4)])['selected'],['a'])
    def test_unsupported_staged(self):
        for kwargs in ({'scope':None},{'weight':4.},{'weight':-1}):
            row={**assertion('a',0,1,'A',4),**kwargs};self.assertEqual(forest_batch([row])['staged'],['a'])
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):forest_batch([assertion('a',0,1,'A',1)]*2)
    def test_small_cycle_exact(self):
        a={str(i):{str(j) for j in range(3) if j!=i} for i in range(3)};r=independent_set(a,{str(i):i+1 for i in range(3)})
        self.assertEqual(r['utility'],3);self.assertEqual(r['routes'][0]['algorithm'],'enumeration')
    def test_large_cycle_staged(self):
        a={str(i):{str((i-1)%17),str((i+1)%17)} for i in range(17)};self.assertEqual(len(independent_set(a,{str(i):1 for i in range(17)})['staged']),17)
    def test_invalid_graph(self):
        for a,w in [({'a':{'b'},'b':set()},{'a':1,'b':1}),({'a':{'a'}},{'a':1})]:
            with self.assertRaises(ValueError):independent_set(a,w)
    def test_large_star_and_cap(self):
        from graph_synthesis.risk_control.run import large_fixture
        a=forest_batch(large_fixture('star',256));b=forest_batch(large_fixture('star',257))
        self.assertEqual(a['utility'],255);self.assertEqual(a['staged'],[]);self.assertEqual(b['selected'],[]);self.assertEqual(len(b['staged']),257)
    def test_order_and_nonmutation(self):
        rows=[assertion('a',0,2,'A',2),assertion('b',0,1,'B',1),assertion('c',1,2,'B',2)];old=copy.deepcopy(rows)
        self.assertEqual(forest_batch(rows),forest_batch(rows[::-1]));self.assertEqual(rows,old)
    def test_false_priority_control(self):self.assertEqual(forest_batch([assertion('false',0,1,'A',9),assertion('true',0,1,'B',8)])['selected'],['false'])
    def test_small_independent_oracle(self):
        rng=random.Random(4)
        for _ in range(20):
            rows=[assertion(str(i),0,rng.randrange(1,5),str(rng.randrange(3)),rng.randrange(1,9)) for i in range(7)]
            r=forest_batch(rows);self.assertEqual(r['utility'],oracle_optimum(rows));self.assertTrue(oracle_valid([a for a in rows if a['id'] in r['selected']]))
    def test_zero_weight_tie(self):
        rows=[assertion('a',0,2,'A',0),assertion('b',0,2,'B',0)];self.assertEqual(forest_batch(rows),forest_batch(rows[::-1]));self.assertEqual(forest_batch(rows)['utility'],0)


if __name__=='__main__':unittest.main()
