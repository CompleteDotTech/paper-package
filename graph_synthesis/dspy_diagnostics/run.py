"""Fresh repeatability and original cross-formulation batching layout, after freezing."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
import gzip
import json
from pathlib import Path
import random
import numpy as np
from graph_synthesis.dspy_benchmark import study
from graph_synthesis.dspy_benchmark_v2.adapter import probabilities,InvalidServiceResponse


def load(capture,task,arm):
    protocol=study.read(capture/'protocol.json');freeze=study.read(capture/'freeze.json')
    if protocol.get('revision')!=2 or (protocol['task'],protocol['arm'])!=(task,arm) or study.read(capture/'execution.json').get('status')!='completed':
        raise ValueError('Require the matching complete v2 capture')
    if study.digest(freeze['payload'])!=freeze['sha256'] or freeze['payload']['protocol_sha256']!=study.digest(protocol):raise ValueError('Freeze invalid')
    plan,parts,_=study.prepare(task);order=list(plan['question_specs'][task][arm])
    configs=[protocol['baseline']]
    for search in freeze['payload']['searches']:
        if study.digest(study.read(capture/f"search-{search['seed']}.json"))!=search['ledger_sha256']:raise ValueError('Search changed')
        configs.append(search['accuracy_questions'])
    if [s['seed'] for s in freeze['payload']['searches']]!=study.SEEDS:raise ValueError('Incomplete searches')
    configs=[{key:q[key] for key in order} for q in configs]
    return configs,study.read(capture/'calibration.json')['fits'],freeze['sha256']


def bank_call(live,task,row,bank,demos,phase):
    fewshot={arm=='fewshot_contract' for arm,_,_ in bank}
    if len(fewshot)!=1:raise ValueError('Do not mix incompatible input states')
    value=study.state(task,row)
    if True in fewshot:
        value={'labeled_examples':[{'input':study.state(task,d),'answer':d['gold_label']} for d in demos],'input':value}
    questions={f'{arm}__v{i}__{key}':q for arm,i,config in bank for key,q in config.items()}
    response=live.send({'model':study.MODEL,'state':value,'questions':questions},phase+'/'+row['id'])
    if set(response.get('answers',{}))!=set(questions):raise InvalidServiceResponse('Answer bank mismatch')
    return {(arm,i):probabilities({key:response['answers'][f'{arm}__v{i}__{key}'] for key in config},task,config) for arm,i,config in bank}


def run(task,input_dir,out):
    if out.exists():raise ValueError('Do not overwrite observations')
    plan,parts,_=study.prepare(task);original=plan['tasks'][task]
    lookup={r['id']:r for r in original['evaluation']+original['development']}
    repeat=[lookup[i] for i in original['repeatability_ids']];batching=[lookup[i] for i in original['batching_ids']]
    if len(repeat)!=20 or len(batching)!=20:raise ValueError('Unexpected original diagnostic panels')
    captures={};fits={};freezes={};configs={}
    for arm in study.ARMS[task]:
        candidates=[p.parent for p in input_dir.rglob('protocol.json') if study.read(p).get('task')==task and study.read(p).get('arm')==arm]
        if len(candidates)!=1:raise ValueError('Missing/duplicate primary capture')
        captures[arm]=candidates[0];configs[arm],fits[arm],freezes[arm]=load(candidates[0],task,arm)
    out.mkdir(parents=True)
    study.write_json(out/'protocol.json',{'experiment_type':'repeatability_and_batching','task':task,'model':study.MODEL,
        'source_sha256':study.sha(__file__),'seeds':study.SEEDS,'repetitions':3,'upstream_freeze_sha256':freezes,
        'repeatability_ids':original['repeatability_ids'],'batching_ids':original['batching_ids'],
        'repeatability_origin':'Original evaluation subset','batching_origin':'Original development subset, used only for packing/performance diagnostics',
        'source_calibration_sha256':{arm:study.sha(captures[arm]/'calibration.json') for arm in captures},
        'configs':configs,'expected_successful_calls':640})
    live=study.Live(out,max_calls=2000);demos=parts['demonstrations'];arms=list(configs)
    ordinary=[(arm,i,config) for arm in arms if arm!='fewshot_contract' for i,config in enumerate(configs[arm])]
    fewshot=[('fewshot_contract',i,config) for i,config in enumerate(configs['fewshot_contract'])]
    banks=[('ordinary',ordinary),('fewshot',fewshot)]
    k=len(study.LABELS[task]);repeated={arm:np.zeros((3,6,20,k)) for arm in arms}
    batched={arm:np.zeros((6,20,k)) for arm in arms};isolated={arm:np.zeros((6,20,k)) for arm in arms}
    for r in range(3):
        jobs=[(name,bank,j,row) for name,bank in banks for j,row in enumerate(repeat)]
        def one(item):
            name,bank,j,row=item
            return j,bank_call(live,task,row,bank,demos,f'repeat-{r}/{name}')
        with ThreadPoolExecutor(max_workers=2) as pool:
            for j,answers in pool.map(one,jobs):
                for (arm,i),p in answers.items():repeated[arm][r,i,j]=p
    jobs=[(name,bank,j,row) for name,bank in banks for j,row in enumerate(batching)]
    def batch_one(item):
        name,bank,j,row=item
        return j,bank_call(live,task,row,bank,demos,'batch/'+name)
    with ThreadPoolExecutor(max_workers=2) as pool:
        for j,answers in pool.map(batch_one,jobs):
            for (arm,i),p in answers.items():batched[arm][i,j]=p
    jobs=[(arm,i,config,j,row) for arm in arms for i,config in enumerate(configs[arm]) for j,row in enumerate(batching)]
    random.Random(20260918).shuffle(jobs)
    def separate_one(item):
        arm,i,config,j,row=item
        return arm,i,j,bank_call(live,task,row,[(arm,i,config)],demos,f'isolated/{arm}/{i}')[(arm,i)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for arm,i,j,p in pool.map(separate_one,jobs):isolated[arm][i,j]=p
    study.write_json(out/'predictions.json',{'repeatability':{a:p.tolist() for a,p in repeated.items()},
        'batched':{a:p.tolist() for a,p in batched.items()},'isolated':{a:p.tolist() for a,p in isolated.items()}})
    metrics=[];drift=[]
    for arm in arms:
        for i in range(6):
            selection='baseline' if i==0 else 'dspy';seed=0 if i==0 else study.SEEDS[i-1];fit_index=0 if i==0 else 2*i-1
            p=repeated[arm][:,i]
            drift.append({'task':task,'arm':arm,'selection':selection,'seed':seed,
                'repeat_rows_with_label_disagreement':int(np.sum(np.any(p.argmax(axis=2)!=p[0].argmax(axis=1),axis=0))),
                'repeat_max_probability_spread':float(np.max(np.max(p,axis=0)-np.min(p,axis=0))),
                'batch_vs_isolated_label_disagreements':int(np.sum(batched[arm][i].argmax(axis=1)!=isolated[arm][i].argmax(axis=1))),
                'batch_vs_isolated_max_probability_difference':float(np.max(np.abs(batched[arm][i]-isolated[arm][i])))})
            for method in ('raw','temperature','temperature_bias'):
                for r in range(3):
                    value=study.calibrated(repeated[arm][r,i],fits[arm][fit_index],method)
                    metrics.append({'task':task,'arm':arm,'selection':selection,'seed':seed,'calibration':method,'repeat':r,
                        'metrics':study.evaluate_metrics(value,repeat,task)})
    study.write_json(out/'repeat-metrics.json',metrics);study.write_json(out/'drift.json',drift)
    phases=defaultdict(lambda:{'calls':0,'input_tokens':0,'latencies':[]})
    with gzip.open(out/'calls.jsonl.gz','rt',encoding='utf-8') as f:
        for line in f:
            call=json.loads(line);phase=call['site'].rsplit('/',1)[0];entry=phases[phase]
            entry['calls']+=1;entry['input_tokens']+=int((call.get('response') or {}).get('usage',{}).get('input_tokens',0));entry['latencies'].append(call['latency_seconds'])
    stats={key:{'calls':v['calls'],'input_tokens':v['input_tokens'],'mean_request_seconds':float(np.mean(v['latencies'])),
                'median_request_seconds':float(np.median(v['latencies'])),'p95_request_seconds':float(np.quantile(v['latencies'],.95))} for key,v in phases.items()}
    study.write_json(out/'performance.json',stats)
    study.write_json(out/'execution.json',{'status':'completed','live':True,'task':task,'http_attempts':live.calls,
        'reported_input_tokens':live.tokens,'estimated_jev_usd':live.tokens*.042/1_000_000,'expected_successful_calls':640,
        'scope':'Three repeatability passes; all original non-few-shot formulations packed together; few-shot state isolated; matched individual calls.'})
    study.write_json(out/'artifact-manifest.json',{'sha256':{p.name:study.sha(p) for p in sorted(out.iterdir()) if p.is_file() and p.name!='artifact-manifest.json'}})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--task',choices=list(study.ARMS),required=True)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.task,a.input,a.output)

if __name__=='__main__':main()
