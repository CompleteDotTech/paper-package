"""Regression and adversarial controls for the distinct interval-regret experiment."""
from copy import deepcopy
import json
from pathlib import Path
import random
import unittest

from graph_synthesis.novel_mechanisms.regret import robust_select, endpoint_oracle, insert_section, reconcile, NOTICE
from graph_synthesis.novel_mechanisms.run import HERE, ROOT, sha


class RegretTests(unittest.TestCase):
    def test_fixed_uncertain_priority_control(self):
        got=robust_select({'a':9,'b':8},{'a':[0,10],'b':[8,8]},[('a','b')])
        self.assertEqual(got['selected'],['b']);self.assertEqual(got['regret'],2)
        self.assertEqual(got['nominal_utility'],8)
        self.assertEqual(got['witness'],{'a':10,'b':8})
        self.assertEqual(got['rival'],['a'])

    def test_endpoint_oracle_independence(self):
        rng=random.Random(32416190071)
        for _ in range(20):
            keys=list('abcde');nominal={k:rng.randint(1,9) for k in keys}
            intervals={k:[rng.randint(0,nominal[k]),rng.randint(nominal[k],nominal[k]+9)] for k in keys}
            edges=[(a,b) for i,a in enumerate(keys) for b in keys[i+1:] if rng.random()<.4]
            got=robust_select(nominal,intervals,edges);oracle,_=endpoint_oracle(nominal,intervals,edges)
            self.assertEqual({k:got[k] for k in oracle},oracle)

    def test_zero_width_is_nominal_optimum(self):
        got=robust_select({'a':9,'b':8},{'a':[9,9],'b':[8,8]},[('a','b')])
        self.assertEqual(got['selected'],['a']);self.assertEqual(got['regret'],0)

    def test_empty_graph(self):
        got=robust_select({}, {}, [])
        self.assertEqual(got['selected'],[]);self.assertEqual(got['regret'],0)
        self.assertEqual(got['witness'],{})

    def test_disconnected_graph(self):
        got=robust_select({'a':2,'b':3},{'a':[0,4],'b':[1,5]},[])
        self.assertEqual(got['selected'],['a','b']);self.assertEqual(got['regret'],0)

    def test_equal_priority_tie_is_lexical(self):
        got=robust_select({'a':2,'b':2},{'a':[1,3],'b':[1,3]},[('a','b')])
        self.assertEqual(got['selected'],['a'])

    def test_permutation_and_duplicate_edges(self):
        n={'a':9,'b':8};p={'a':[0,10],'b':[8,8]}
        self.assertEqual(robust_select(n,p,[('a','b')]),robust_select(dict(reversed(list(n.items()))),dict(reversed(list(p.items()))),[('b','a'),('a','b')]))

    def test_vertex_cap_stages_without_partial_optimum(self):
        n={str(i):1 for i in range(13)};p={k:[0,2] for k in n}
        got=robust_select(n,p,[])
        self.assertEqual(got['status'],'staged');self.assertIsNone(got['regret']);self.assertEqual(got['selected'],[])

    def test_pair_cap_stages(self):
        got=robust_select({'a':1},{'a':[0,2]},[],pair_cap=1)
        self.assertEqual(got['reason'],'pair_cap');self.assertIsNone(got['regret'])

    def test_invalid_bounds(self):
        for pair in ([True,2],[-1,2],[2,3],[0,0],[0,1.5],[0],None):
            with self.subTest(pair=pair),self.assertRaises(ValueError):robust_select({'a':1},{'a':pair},[])
        with self.assertRaises(ValueError):robust_select({'a':1},{},[])

    def test_unknown_and_self_edges_rejected(self):
        for edges in ([('a','a')],[('a','unknown')]):
            with self.assertRaises(ValueError):robust_select({'a':1},{'a':[0,2]},edges)

    def test_invalid_caps(self):
        for kwargs in ({'vertex_cap':True},{'vertex_cap':13},{'pair_cap':0},{'pair_cap':1000001}):
            with self.assertRaises(ValueError):robust_select({}, {}, [], **kwargs)

    def test_inputs_are_not_mutated(self):
        n={'a':1,'b':2};p={'a':[0,3],'b':[1,4]};e=[['a','b']];before=deepcopy((n,p,e))
        robust_select(n,p,e);self.assertEqual((n,p,e),before)

    def test_outside_interval_control_not_certified(self):
        got=robust_select({'a':9,'b':8},{'a':[0,10],'b':[8,8]},[('a','b')])
        actual={'a':10,'b':0};regret=max(actual.values())-sum(actual[k] for k in got['selected'])
        self.assertEqual(regret,10);self.assertGreater(regret,got['regret'])

    def test_additive_publication_is_idempotent(self):
        anchor='<!-- NOVEL_MECHANISMS_RESEARCH_END -->'
        source='older\n'+anchor+'\nconcurrent study\n'
        once=insert_section(source,'new evidence')
        self.assertEqual(once,insert_section(once,'new evidence'))
        self.assertTrue(once.endswith('concurrent study\n'))
        first=reconcile('# Five new mechanisms for evidence-preserving Jev graph synthesis\nbody',NOTICE)
        self.assertEqual(first,reconcile(first,NOTICE))

    def test_stored_artifacts(self):
        path=HERE/'regret-results.json'
        if not path.exists():self.skipTest('Execute the frozen regret experiment before stored-artifact auditing')
        result=json.loads(path.read_text(encoding='utf-8'))
        for name,expected in result['source_hashes'].items():self.assertEqual(sha(ROOT/name),expected)
        improved=0
        for row in result['fixtures']:
            got=row['proposed'];self.assertTrue(row['valid_witness'])
            self.assertEqual(got['regret'],row['oracle']['regret'])
            self.assertLessEqual(got['regret'],row['baseline']['regret'])
            improved+=got['regret']<row['baseline']['regret']
        self.assertEqual(improved,result['improved_cases']);self.assertEqual(result['fresh_service_calls'],0)
        self.assertEqual(result['primary_target_met'],not any(result[k] for k in ('oracle_failures','consistency_failures','witness_failures','regret_regressions')) and improved>=12.8)


if __name__=='__main__':unittest.main()
