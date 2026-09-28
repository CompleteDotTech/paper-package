"""Fresh, repeated benchmark execution. Never treats a replay as live evidence."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from threading import Lock
import numpy as np
from graph_synthesis.dspy_jev_optimizer.core import (
    JevConfig, Evaluator, Cache, BudgetExhausted, digest, canonical, parse_json,
    validate_answer, metrics, optimize, write_json, read_json, frozen_run)
from graph_synthesis.dspy_jev_optimizer.providers import TypeSafeBackend, DSPyProposer
from .data import ROOT, SEEDS, OBJECTIVES, load_task, panels, state, inventory
from .calibration import fit, apply, evaluation

JEV_INPUT_USD_PER_MILLION = 0.042
DEEPSEEK_INPUT_USD_PER_MILLION = 0.30
DEEPSEEK_OUTPUT_USD_PER_MILLION = 1.20
PROPOSAL_RESERVE_USD = 0.07
PER_SEED_BUDGET_USD = 8.0  # Five manually dispatched seeds reserve at most $40 of the $50 cap.


class CostBudget:
    """Conservative per-seed guard; records provider-reported usage, never keys."""
    def __init__(self, limit=PER_SEED_BUDGET_USD):
        self.limit = limit
        self.lock = Lock()
        self.target_input_tokens = 0
        self.proposals = 0
        self.proposer_input_tokens = 0
        self.proposer_output_tokens = 0
        self.reserved_usd = 0.0

    def target(self, usage):
        tokens = usage.get('input_tokens') if isinstance(usage, dict) else None
        if type(tokens) is not int or tokens < 0:
            raise BudgetExhausted('Jev response lacks valid input-token usage')
        with self.lock:
            self.target_input_tokens += tokens
            self._check()

    def reserve_proposal(self, payload_bytes):
        if payload_bytes > 120_000:
            raise BudgetExhausted('Proposal input exceeds pre-priced bound')
        with self.lock:
            self.proposals += 1
            self.reserved_usd += PROPOSAL_RESERVE_USD
            self._check()

    def proposal_usage(self, usage):
        if not isinstance(usage, dict):
            return  # Conservative per-proposal reserve remains charged.
        input_tokens = usage.get('prompt_tokens', usage.get('input_tokens'))
        output_tokens = usage.get('completion_tokens', usage.get('output_tokens'))
        if type(input_tokens) is int and input_tokens >= 0:
            self.proposer_input_tokens += input_tokens
        if type(output_tokens) is int and output_tokens >= 0:
            self.proposer_output_tokens += output_tokens
        self._check()

    def _check(self):
        if self.estimated_usd() > self.limit:
            raise BudgetExhausted('Per-seed estimated spend limit reached')

    def estimated_usd(self):
        jev = self.target_input_tokens * JEV_INPUT_USD_PER_MILLION / 1_000_000
        observed_proposal = (self.proposer_input_tokens * DEEPSEEK_INPUT_USD_PER_MILLION
                             + self.proposer_output_tokens * DEEPSEEK_OUTPUT_USD_PER_MILLION) / 1_000_000
        return jev + max(self.reserved_usd, observed_proposal)

    def record(self):
        return {'limit_usd': self.limit, 'estimated_usd': self.estimated_usd(),
                'jev_input_tokens': self.target_input_tokens,
                'proposal_calls': self.proposals,
                'proposal_input_tokens_reported': self.proposer_input_tokens,
                'proposal_output_tokens_reported': self.proposer_output_tokens,
                'proposal_reserve_usd': self.reserved_usd,
                'pricing_basis': {'jev_input_per_million_usd': JEV_INPUT_USD_PER_MILLION,
                                  'deepseek_input_per_million_usd': DEEPSEEK_INPUT_USD_PER_MILLION,
                                  'deepseek_output_per_million_usd': DEEPSEEK_OUTPUT_USD_PER_MILLION},
                'note': 'Estimate from reported tokens and conservative proposal reserve, not an invoice.'}


class ParallelEvaluator(Evaluator):
    """Only the caller thread touches SQLite and audit files."""
    def __init__(self, *args, workers=4, budget=None, **kwargs):
        super().__init__(*args, **kwargs)
        if not 1 <= workers <= 8:
            raise ValueError('workers must be 1..8')
        self.workers = workers
        self.budget = budget

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
                    if self.budget is not None:
                        self.budget.target(response.get('usage'))
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
        super().__init__(model, retries=0)
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
    def __init__(self, model, output, seed, budget=None):
        base = os.environ.get('DSPY_PROPOSER_API_BASE', '').strip()
        if base:
            if model != 'openai/ollamacloud/deepseek-v4.1-flash' or base != 'https://train.home.complete.tech:20128/v1':
                raise ValueError('Unregistered proposal model or gateway endpoint')
            import dspy
            lm = dspy.LM(model, api_base=base, api_key=os.environ['OPENAI_API_KEY'],
                         temperature=1.0, max_tokens=16384, timeout=180, num_retries=0, cache=False)
            self.inner = DSPyProposer(model, lm=lm)
            self.inner.identity['max_tokens'] = 16384
        else:
            self.inner = DSPyProposer(model)
        self.output = output
        self.budget = budget
        self.identity = {**self.inner.identity,'repeat_seed':seed,
                         'seed_scope':'Python/NumPy and feedback order; remote sampling is not guaranteed deterministic'}

    def propose(self, config, feedback, iteration, history):
        if self.budget is not None:
            self.budget.reserve_proposal(len(canonical({'config':asdict(config),'feedback':feedback,
                                                         'history':history,'iteration':iteration}).encode('utf-8')))
        proposal = self.inner.propose(config,feedback,iteration,history)
        records = self.inner.lm.history
        last = records[-1] if records else {}
        if self.budget is not None:
            self.budget.proposal_usage(last.get('usage'))
        # LiteLLM usage may contain nested wrapper objects; record only scalar counts.
        usage = last.get('usage')
        usage_record = scalar_proposal_usage(usage)
        cost = last.get('cost')
        cost = float(cost) if type(cost) in (int, float) else None
        # Whitelist metadata; never serialize provider arguments or authentication headers.
        row = {'iteration':iteration,'input_config':asdict(config),'training_feedback':feedback,
               'candidate':proposal,'usage':usage_record, 'cost_usd':cost}
        self.output.parent.mkdir(parents=True,exist_ok=True)
        with self.output.open('a',encoding='utf-8') as f:
            f.write(canonical(row)+'\n')
        return proposal


def scalar_proposal_usage(usage):
    """Reduce LiteLLM's nested usage wrappers to auditable integer counts."""
    if not isinstance(usage, dict):
        return {}
    return {key: usage[key] for key in ('prompt_tokens','completion_tokens','total_tokens')
            if type(usage.get(key)) is int and usage[key] >= 0}


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


def proposer_credential(model):
    """Resolve only the proposal providers explicitly exposed by the workflow."""
    for prefix, key in (('openrouter/', 'OPENROUTER_API_KEY'),
                        ('anthropic/', 'ANTHROPIC_API_KEY'),
                        ('openai/', 'OPENAI_API_KEY')):
        if model.startswith(prefix):
            return key
    return None


def save_predictions(path, rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(gzip.compress(canonical(rows).encode(),mtime=0))


def write_artifact_inventory(output: Path):
    files = {}
    for path in sorted(output.rglob('*')):
        if path.is_file() and path.name != 'artifact-inventory.json':
            digest_file = hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest_file.update(chunk)
            files[path.relative_to(output).as_posix()] = digest_file.hexdigest()
    write_json(output/'artifact-inventory.json', {'schema_version':1,'sha256':files})


def execute(output: Path, seed: int, *, iterations=8, baseline_only=False, model='jev-1.13.0', workers=4):
    if seed not in SEEDS or not 0 <= iterations <= 12 or (iterations == 0 and not baseline_only):
        raise ValueError('Unregistered seed or iteration budget')
    if output.exists():
        raise FileExistsError('Use a new run directory; do not overwrite an experiment')
    proposer_model = provider_model() if not baseline_only else None
    if baseline_only:
        iterations = 0
    proposer_key = proposer_credential(proposer_model) if proposer_model else None
    target_ready = bool(os.environ.get('TYPESAFE_API_KEY', '').strip())
    proposal_ready = baseline_only or bool(proposer_key and os.environ.get(proposer_key, '').strip())
    output.mkdir(parents=True)
    if not target_ready or not proposal_ready:
        write_json(output/'status.json', {'status':'blocked_missing_credentials',
            'typesafe_key_present':target_ready,
            'proposer_model_configured':bool(proposer_model),
            'proposer_credential_present':bool(proposer_key and os.environ.get(proposer_key, '').strip()),
            'live_calls':0})
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
    budget = CostBudget()
    all_metrics,usage = [],[]
    try:
        for task in ('relation_support','entity_resolution'):
            cfg,splits,specs,source = load_task(task)
            train = list(splits['train'])
            random.Random(seed).shuffle(train)
            task_dir = output/task
            task_dir.mkdir()
            cache = Cache(task_dir/'calls.sqlite3')
            backend = TypeSafeBackend(model,retries=0)
            backend.identity['repeat_seed'] = seed
            targets = []
            try:
                # Freeze every search before this task's calibration or test inference.
                if not baseline_only:
                    for objective in OBJECTIVES:
                        search = task_dir/('search-'+objective)
                        ev = ParallelEvaluator(backend,cache,search,2000,workers=workers,budget=budget)
                        proposer = LoggedProposer(proposer_model, task_dir/('proposals-'+objective+'.jsonl'),seed,budget=budget)
                        freeze = optimize(cfg,train,splits['validation'],proposer,ev,search,
                                          iterations=iterations,selection_metric=objective,failure_sample=12,patience=0)
                        if freeze['stop_reason'] != 'iteration_budget':
                            raise BudgetExhausted('Search ended before the frozen iteration budget')
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
                    ev = ParallelEvaluator(target_backend,cache,target_dir,12000,workers=workers,budget=budget)
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
            write_json(output/'cost-budget.json',budget.record())
        if not baseline_only and budget.proposals != iterations * len(OBJECTIVES) * 2:
            raise RuntimeError('Completed comparison lacks frozen proposal count')
        write_json(output/'status.json',{'status':'completed_baseline_only' if baseline_only else 'completed',
            'live_logical_calls':sum(r['logical_calls'] for r in usage), 'protocol_sha256':digest(protocol),
            'estimated_cost_usd':budget.estimated_usd()})
        write_artifact_inventory(output)
        return all_metrics
    except Exception as exc:
        write_json(output/'usage.json',usage)
        write_json(output/'cost-budget.json',budget.record())
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
