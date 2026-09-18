import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from graph_synthesis.dspy_jev_optimizer.core import Example,JevConfig,Cache,BudgetExhausted,metrics,read_json
from graph_synthesis.dspy_benchmark.data import inventory,load_task,panels,SEEDS
from graph_synthesis.dspy_benchmark.calibration import fit,apply,evaluation,paired_interval
from graph_synthesis.dspy_benchmark.run import ParallelEvaluator,provider_model,execute
from graph_synthesis.dspy_benchmark.report import summarize

LABELS={'a':'first','b':'second'}
CFG=JevConfig('task','classify',LABELS)

def sample(n=20):
    return [{'id':str(i),'group_id':str(i//2),'gold':'a' if i%4 else 'b',
             'choice':'a','probabilities':{'a':.98,'b':.02}} for i in range(n)]

class FakeBackend:
    def __init__(self,seed=1,bad=False):
        self.identity={'model':'mock-test-only','seed':seed};self.count=0;self.bad=bad
    def predict(self,config,state):
        self.count+=1
        return {'model':'drift' if self.bad else self.identity['model'],'choice':'a',
                'probabilities':{'a':.8,'b':.2},'usage':{'input_tokens':10,'output_tokens':0}}

class Tests(unittest.TestCase):
    def test_inventory_all_registered_panels(self):
        v=inventory()
        self.assertEqual(v['relation_support']['splits']['test']['n'],339)
        self.assertEqual(v['entity_resolution']['splits']['test']['n'],413)
        self.assertEqual(v['relation_support']['panels']['semantic_challenge']['n'],48)
        self.assertEqual(v['relation_support']['panels']['multicall_test']['n'],263)
    def test_train_validation_calibration_are_distinct(self):
        for task in ('relation_support','entity_resolution'):
            _,s,_,_=load_task(task)
            self.assertEqual((len(s['train']),len(s['validation'])),(29,31))
            for a in s:
                for b in s:
                    if a!=b:self.assertFalse({r.id for r in s[a]} & {r.id for r in s[b]})
    def test_all_legacy_formulations_are_retained(self):
        self.assertEqual(len(load_task('relation_support')[2]),4)
        self.assertEqual(len(load_task('entity_resolution')[2]),4)
    def test_uncertain_fixtures_are_not_silently_removed(self):
        cfg,_,_,_=load_task('entity_resolution')
        rows=panels('entity_resolution')['fixtures']
        self.assertEqual(len(rows),100)
        self.assertEqual(sum(r.label not in cfg.criteria for r in rows),12)
    def test_inventory_deterministic(self):
        self.assertEqual(inventory(),inventory())
    def test_state_does_not_include_labels(self):
        for task in ('relation_support','entity_resolution'):
            for rows in load_task(task)[1].values():
                for r in rows:self.assertFalse({'gold_label','rationale_sentence_ids','label'} & set(r.state))
    def test_temperature_preserves_labels(self):
        rows=sample();model=fit(rows,LABELS)
        self.assertEqual([r['choice'] for r in apply(rows,model)],[r['choice'] for r in rows])
    def test_temperature_reduces_overconfident_calibration_loss(self):
        rows=sample();after=apply(rows,fit(rows,LABELS))
        self.assertLess(metrics(after,LABELS)['log_loss'],metrics(rows,LABELS)['log_loss'])
    def test_raw_is_unchanged(self):
        rows=sample();self.assertEqual(rows,apply(rows,fit(rows,LABELS,'raw')))
    def test_bias_temperature_is_normalized(self):
        for row in apply(sample(),fit(sample(),LABELS,'bias_temperature')):
            self.assertAlmostEqual(sum(row['probabilities'].values()),1)
    def test_fit_serializes(self):
        model=fit(sample(),LABELS)
        self.assertEqual(model,json.loads(json.dumps(model)))
    def test_invalid_calibration_distribution(self):
        rows=sample();rows[0]['probabilities']['a']=4
        with self.assertRaises(ValueError):fit(rows,LABELS)
    def test_empty_calibration_rejected(self):
        with self.assertRaises(ValueError):fit([],LABELS)
    def test_unscorable_excluded_from_denominator(self):
        rows=sample()+[{'id':'u','gold':'uncertain','choice':'a','probabilities':{'a':.5,'b':.5}}]
        r=evaluation(rows,LABELS)
        self.assertEqual((r['n'],r['unscorable_count']),(20,1))
    def test_risk_empty_acceptance_is_not_zero_error_claim(self):
        rows=sample();r=evaluation(rows,LABELS)
        self.assertIsNone(r['selective'][-1]['risk'])
    def test_identical_paired_interval_zero(self):
        r=paired_interval(sample(),sample(),LABELS,'brier',repeats=10)
        self.assertEqual((r['delta'],r['low'],r['high']),(0.,0.,0.))
    def test_unpaired_intervals_rejected(self):
        with self.assertRaises(ValueError):paired_interval(sample(),list(reversed(sample())),LABELS,'accuracy')
    def test_five_registered_seeds(self):
        self.assertEqual(len(SEEDS),5);self.assertEqual(len(set(SEEDS)),5)
    def test_cache_never_crosses_repeat_namespace(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);cache=Cache(p/'c.sqlite');r=[Example('one',{'x':1},'a')]
            a=FakeBackend(1);e=ParallelEvaluator(a,cache,p/'a',10)
            e.evaluate(CFG,r,'test');e.evaluate(CFG,r,'test');self.assertEqual(a.count,1)
            b=FakeBackend(2);ParallelEvaluator(b,cache,p/'b',10).evaluate(CFG,r,'test')
            self.assertEqual(b.count,1);cache.close()
    def test_budget_prevents_partial_evaluation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);c=Cache(p/'c');b=FakeBackend();e=ParallelEvaluator(b,c,p,1)
            with self.assertRaises(BudgetExhausted):e.evaluate(CFG,[Example('1',{'x':1},'a'),Example('2',{'x':2},'a')],'test')
            self.assertEqual(b.count,0);c.close()
    def test_model_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);c=Cache(p/'c');e=ParallelEvaluator(FakeBackend(bad=True),c,p,2)
            with self.assertRaises(RuntimeError):e.evaluate(CFG,[Example('1',{'x':1},'a')],'test')
            c.close()
    def test_missing_keys_block_before_model_calls(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{},clear=True):
            p=Path(d)/'run'
            with self.assertRaises(RuntimeError):execute(p,11)
            self.assertEqual(read_json(p/'status.json')['live_calls'],0)
    def test_missing_results_are_not_zero_accuracy(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(summarize(Path(d)),[])
            self.assertEqual(read_json(Path(d)/'run-status.json')[0]['status'],'not_run')
    def test_provider_is_explicit_not_magic_fallback(self):
        with patch.dict(os.environ,{},clear=True):self.assertIsNone(provider_model())
    def test_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileExistsError):execute(Path(d),11)

    def test_full_comparison_orchestration_with_test_doubles(self):
        events=[]
        class Backend:
            def __init__(self,*args,**kwargs): self.identity={'model':'jev-1.13.0','test_double':True}
            def close(self): pass
            def predict(self,config,state):
                events.append(state['phase'])
                return {'model':'jev-1.13.0','choice':'a','probabilities':{'a':.7,'b':.3},'usage':{'input_tokens':2,'output_tokens':0}}
        class Proposer:
            def __init__(self,*args,**kwargs): self.identity={'test_double':True}
            def propose(self,cfg,feedback,iteration,history):
                return {'task':cfg.task,'instructions':cfg.instructions+' revised','criteria':cfg.criteria}
        def rows(phase,n):
            return [Example(phase+str(i),{'phase':phase,'i':i},'a' if i%2 else 'b',phase+str(i)) for i in range(n)]
        splits={s:rows(s,6) for s in ('train','validation','calibration')}
        from graph_synthesis.dspy_benchmark import run
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{'TYPESAFE_API_KEY':'test-only','DSPY_PROPOSER_MODEL':'test-only'},clear=True), patch.object(run,'load_task',return_value=(CFG,splits,{'baseline_choice':{}},{'demonstrations':[]})), patch.object(run,'panels',return_value={'test':rows('test',6)}), patch.object(run,'TypeSafeBackend',Backend), patch.object(run,'LegacyBackend',Backend), patch.object(run,'LoggedProposer',Proposer):
            output=Path(d)/'seed-11'
            result=execute(output,11,iterations=1,workers=2)
            self.assertEqual(read_json(output/'status.json')['status'],'completed')
            self.assertEqual(len(result),2*3*7)
            self.assertEqual({r['arm'] for r in result},{'dspy_accuracy','dspy_composite','without_dspy_baseline_choice'})
            self.assertTrue((output/'relation_support'/'calibration-freeze.json').exists())
            self.assertGreater(events.index('test'),events.index('calibration'))

if __name__=='__main__':unittest.main()
