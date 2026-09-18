"""Fresh, repeated benchmark execution. Never treats a replay as live evidence."""
from __future__ import annotations
import argparse
import gzip
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
import numpy as np
from graph_synthesis.dspy_jev_optimizer.core import (
    JevConfig, Evaluator, Cache, BudgetExhausted, digest, canonical, parse_json,
    validate_answer, metrics, optimize, write_json, read_json, frozen_run)
from graph_synthesis.dspy_jev_optimizer.providers import TypeSafeBackend, DSPyProposer
from .data import ROOT, SEEDS, OBJECTIVES, load_task, panels, state, inventory
from .calibration import fit, apply, evaluation


class ParallelEvaluator(Evaluator):
    """Only the caller thread touches SQLite and audit files."""
    def __init__(self, *args, workers=4, **kwargs):
        super().__init__(*args, **kwargs)
        if not 1 <= workers <= 8:
            raise ValueError('workers must be 1..8')
        self.workers = workers

    def evaluate(self, config, rows, phase):
        keys = [digest({'schema':1, 'backend':self.backend.identity,
                        'config':config.fingerprint(), 'state':r.state}) for r in rows]
        responses, missing = {}, {}
        for key, row in zip(keys, rows):
            cached = self.cache.get(key)
            if cached is None:
                missing.setdefault(key, row)
            else:
                responses[key] = cached
        if len(missing) > self.max_calls-self.calls:
            raise BudgetExhausted('Insufficient budget for a complete evaluation')
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            jobs = []
            for key, row in missing.items():
                self.calls += 1
                self.event({'event':'request', 'key':key, 'phase':phase, 'state':row.state,
                            'question':config.question(), 'backend':self.backend.identity})
                jobs.append((key, pool.submit(self.backend.predict, config, parse_json(canonical(row.state)))))
            errors = []
            for key, job in jobs:
                try:
                    response = job.result()
                    validate_answer(response,config.criteria)
                    if response.get('model') != self.backend.identity['model']:
                        raise ValueError('Pinned model drift')
                    for token in self.usage:
                        count = response.get('usage',{}).get(token,0)
                        if type(count) is not int or count < 0:
                            raise ValueError('Invalid usage')
                        self.usage[token] += count
                    self.cache.put(key,response)
                    responses[key] = response
                    self.event({'event':'response','key':key,'phase':phase,'response':response})
                except Exception as exc:
                    errors.append(type(exc).__name__)
                    self.event({'event':'request_failed','key':key,'phase':phase,'error_type':type(exc).__name__})
        if errors:
            raise RuntimeError('Inference failures: '+','.join(sorted(set(errors))))
        predictions = []
        for key,row in zip(keys,rows):
            response = responses[key]
            validate_answer(response,config.criteria)
            if response.get('model') != self.backend.identity['model']:
                raise ValueError('Cached model drift')
            if key not in missing:
                self.cache_hits += 1
                self.event({'event':'cache_hit','key':key,'phase':phase,'response':response})
            predictions.append({'id':row.id, 'group_id':row.group_id or row.id, 'gold':row.label,
                                'choice':response['choice'],'probabilities':response['probabilities'],
                                'request_sha256':key})
        scorable = [r for r in predictions if r['gold'] in config.criteria]
        return metrics(scorable,config.criteria) if scorable else {}, predictions


class LegacyBackend(TypeSafeBackend):
    """Preserve native Choice/Noul formulations, not a rewritten surrogate."""
    def __init__(self, model, task, arm, spec, demos, seed):
        super().__init__(model, retries=2)
        self.task, self.arm, self.spec, self.demos = task,arm,spec,demos
        self.identity.update(legacy_arm=arm, spec_sha256=digest(spec), repeat_seed=seed,
                             demonstration_sha256=digest(demos) if arm=='fewshot_contract' else None)

    def predict(self, config, input_state):
        from typesafe_sdk import Choice, Noul
        questions = {k: (Choice(instructions=v['instructions'],criteria=v['criteria'])
                         if v['type']=='choice' else Noul(instructions=v['instructions'])) for k,v in self.spec.items()}
        current = input_state
        if self.arm == 'fewshot_contract':
            current = {'labeled_examples':self.demos, 'input':current}
        start = time.perf_counter()
        raw = self.client.system_one(model=self.identity['model'],state=current,questions=questions).model_dump(mode='json')
        a = raw['answers']
        if self.arm == 'conditional_nouls':
            p = float(a[self.arm+'__support']['noul'])
            r = float(a[self.arm+'__refute_given_not_support']['noul'])
            probs = {'SUPPORTS':p,'REFUTES':(1-p)*r,'NOT_ENOUGH_INFO':(1-p)*(1-r)}
        elif self.arm in ('baseline_noul','identity_noul'):
            p = float(a[self.arm+'__decision']['noul'])
            probs = {'same':p,'different':1-p}
        else:
            probs = a[self.arm+'__decision']['probabilities']
        # Match the original research decoder's argmax probability decision.
        choice = max(config.criteria, key=lambda k:probs[k])
        return {'choice':choice,'probabilities':probs,'model':raw['model'], 'usage':raw.get('usage',{}),
                'latency_seconds':time.perf_counter()-start,'raw_response':raw,
                'request':{'model':self.identity['model'],'state':current,'questions':self.spec}}


class LoggedProposer:
    def __init__(self, model, output, seed):
        self.inner = DSPyProposer(model)
        self.output = output
        self.identity = {**self.inner.identity,'repeat_seed':seed,
                         'seed_scope':'Python/NumPy and feedback order; remote sampling is not guaranteed deterministic'}

    def propose(self, config, feedback, iteration, history):
        proposal = self.inner.propose(config,feedback,iteration,history)
        records = self.inner.lm.history
        last = records[-1] if records else {}
        # Whitelist metadata; never serialize provider arguments or authentication headers.
        row = {'iteration':iteration,'input_config':asdict(config),'training_feedback':feedback,
               'candidate':proposal,'usage':last.get('usage'), 'cost_usd':last.get('cost')}
        self.output.parent.mkdir(parents=True,exist_ok=True)
        with self.output.open('a',encoding='utf-8') as f:
            f.write(canonical(row)+'\n')
        return proposal


def provider_model():
    configured = os.environ.get('DSPY_PROPOSER_MODEL','').strip()
    if configured:
        return configured
    for key,model in [('OPENROUTER_API_KEY','openrouter/anthropic/claude-sonnet-4.5'),
                      ('ANTHROPIC_API_KEY','anthropic/claude-sonnet-4-5-20250929'),
                      ('OPENAI_API_KEY','openai/gpt-4.1')]:
        if os.environ.get(key,'').strip():
            return model
    return None


def save_predictions(path, rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(gzip.compress(canonical(rows).encode(),mtime=0))


def execute(output: Path, seed: int, *, iterations=8, baseline_only=False, model='jev-1.13.0', workers=4):
    if seed not in SEEDS or not 0 <= iterations <= 12:
        raise ValueError('Unregistered seed or iteration budget')
    if output.exists():
        raise FileExistsError('Use a new run directory; do not overwrite an experiment')
    proposer_model = provider_model()
    output.mkdir(parents=True)
    if not os.environ.get('TYPESAFE_API_KEY') or (not proposer_model and not baseline_only):
        write_json(output/'status.json', {'status':'blocked_missing_credentials',
            'typesafe_key_present':bool(os.environ.get('TYPESAFE_API_KEY')),
            'proposer_model_configured':bool(proposer_model),'live_calls':0})
        raise RuntimeError('Live benchmark requires TypeSafe and a generative proposal provider')
    random.seed(seed)
    np.random.seed(seed)
    protocol = {'seed':seed,'iterations':iterations,'objectives':OBJECTIVES,'model':model,
                'proposer_model':proposer_model,'baseline_only':baseline_only, 'workers':workers,
                'inventory':inventory(),'source_sha256':{
                    p.name:__import__('hashlib').sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')},
                'execution':'live_provider_calls',
                'note':'Historically examined public test sets; held out only from the current optimization.'}
    write_json(output/'protocol.json',protocol)
    all_metrics,usage = [],[]
    try:
        for task in ('relation_support','entity_resolution'):
            cfg,splits,specs,source = load_task(task)
            train = list(splits['train'])
            random.Random(seed).shuffle(train)
            task_dir = output/task
            task_dir.mkdir()
            cache = Cache(task_dir/'calls.sqlite3')
            backend = TypeSafeBackend(model,retries=2)
            backend.identity['repeat_seed'] = seed
            targets = []
            try:
                # Freeze every search before this task's calibration or test inference.
                if not baseline_only:
                    for objective in OBJECTIVES:
                        search = task_dir/('search-'+objective)
                        ev = ParallelEvaluator(backend,cache,search,2000,workers=workers)
                        proposer = LoggedProposer(proposer_model, task_dir/('proposals-'+objective+'.jsonl'),seed)
                        freeze = optimize(cfg,train,splits['validation'],proposer,ev,search,
                                          iterations=iterations,selection_metric=objective,failure_sample=12,patience=0)
                        frozen_run(search)
                        targets.append(('dspy_'+objective,JevConfig.from_dict(freeze['champion']),backend))
                        usage.append({'task':task,'stage':'search_'+objective,**ev.summary()})
                demos = [{'input':state(task,r),'answer':r['gold_label']} for r in source['demonstrations']]
                controls = []
                for arm,spec in specs.items():
                    control = LegacyBackend(model,task,arm,spec,demos,seed)
                    controls.append(control)
                    targets.append(('without_dspy_'+arm,cfg,control))
                write_json(task_dir/'frozen-targets.json', {'targets':{name:asdict(c) for name,c,_ in targets},
                                                         'protocol_sha256':digest(protocol)})
                frozen_calibration = []
                # All calibration parameters are persisted before ANY test prediction in this task.
                for name,config,target_backend in targets:
                    target_dir = task_dir/name
                    ev = ParallelEvaluator(target_backend,cache,target_dir,12000,workers=workers)
                    _,cal = ev.evaluate(config,splits['calibration'],'calibration')
                    fits = {}
                    for fraction in (.25,.5,1.):
                        ranked = sorted(cal,key=lambda r:digest(['calibration-prefix-v1',seed,r['group_id']]))
                        groups = list(dict.fromkeys(r['group_id'] for r in ranked))
                        selected = set(groups[:max(1,int(len(groups)*fraction))])
                        subset = [r for r in ranked if r['group_id'] in selected]
                        for method in ('raw','temperature','bias_temperature'):
                            if method=='raw' and fraction!=1.:
                                continue
                            fits[method+'_'+str(fraction)] = fit(subset,list(config.criteria),method)
                    write_json(target_dir/'calibration.json',fits)
                    save_predictions(target_dir/'calibration-predictions.json.gz',cal)
                    frozen_calibration.append((name,config,ev,fits))
                write_json(task_dir/'calibration-freeze.json',{
                    name:digest(fits) for name,_,_,fits in frozen_calibration})
                for name,config,ev,fits in frozen_calibration:
                    for panel,rows in panels(task).items():
                        _,predictions = ev.evaluate(config,rows,panel)
                        save_predictions(task_dir/name/(panel+'-predictions.json.gz'),predictions)
                        for fit_name,fitted in fits.items():
                            transformed = apply(predictions,fitted)
                            all_metrics.append({'seed':seed,'task':task,'arm':name,'panel':panel,
                                'calibration':fit_name,'n_calibration':fitted['n_calibration'],
                                **evaluation(transformed,config.criteria)})
                        write_json(output/'metrics.json',all_metrics)
                    usage.append({'task':task,'stage':name,**ev.summary()})
                    print(json.dumps({'seed':seed,'task':task,'arm':name,'status':'evaluated'}),flush=True)
                for control in controls:
                    control.close()
            finally:
                backend.close()
                cache.close()
            write_json(output/'usage.json',usage)
        write_json(output/'status.json',{'status':'completed_baseline_only' if baseline_only else 'completed',
            'live_logical_calls':sum(r['logical_calls'] for r in usage), 'protocol_sha256':digest(protocol)})
        return all_metrics
    except Exception as exc:
        write_json(output/'usage.json',usage)
        write_json(output/'status.json',{'status':'failed','error_type':type(exc).__name__,
                                       'note':'Partial observations are not complete benchmark results.'})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seed',type=int,choices=SEEDS,required=True)
    parser.add_argument('--iterations',type=int,default=8)
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--baseline-only',action='store_true')
    args = parser.parse_args()
    execute(args.output,args.seed,iterations=args.iterations,workers=args.workers,baseline_only=args.baseline_only)

if __name__=='__main__':
    main()
