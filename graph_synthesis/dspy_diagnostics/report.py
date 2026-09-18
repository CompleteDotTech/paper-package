"""Verify fresh repeatability/batching observations without inference."""
from __future__ import annotations
import argparse
from collections import defaultdict
import gzip
import json
from pathlib import Path
import statistics
import numpy as np
from graph_synthesis.dspy_benchmark import study
from graph_synthesis.dspy_benchmark_analysis.report import close,write_csv
from .run import load,bank_call


def audit(directory,primary):
    for name,want in study.read(directory/'artifact-manifest.json')['sha256'].items():
        if not (directory/name).resolve().is_relative_to(directory.resolve()) or study.sha(directory/name)!=want:raise ValueError('Capture hash mismatch')
    protocol=study.read(directory/'protocol.json');execution=study.read(directory/'execution.json');task=protocol['task']
    if protocol['model']!=study.MODEL or execution['status']!='completed' or not execution['live']:raise ValueError('Incomplete or wrong-model capture')
    plan,parts,_=study.prepare(task);original=plan['tasks'][task];lookup={r['id']:r for r in original['evaluation']+original['development']}
    if protocol['repeatability_ids']!=original['repeatability_ids'] or protocol['batching_ids']!=original['batching_ids']:raise ValueError('Panels changed')
    repeat=[lookup[i] for i in protocol['repeatability_ids']];batching=[lookup[i] for i in protocol['batching_ids']]
    configs={};fits={}
    for arm in study.ARMS[task]:
        found=[p.parent for p in primary.rglob('protocol.json') if study.read(p).get('task')==task and study.read(p).get('arm')==arm]
        if len(found)!=1:raise ValueError('Missing primary family')
        config,fit,freeze=load(found[0],task,arm)
        if freeze!=protocol['upstream_freeze_sha256'][arm] or study.sha(found[0]/'calibration.json')!=protocol['source_calibration_sha256'][arm]:raise ValueError('Upstream mismatch')
        close(config,protocol['configs'][arm],'config');configs[arm]=config;fits[arm]=fit
    journal={};attempts=tokens=0;phases=defaultdict(lambda:{'calls':0,'input_tokens':0,'latencies':[]})
    with gzip.open(directory/'calls.jsonl.gz','rt',encoding='utf-8') as handle:
        for line in handle:
            call=json.loads(line);attempts+=1
            if study.digest(call['payload'])!=call['request_sha256'] or call['payload']['model']!=study.MODEL:raise ValueError('Request mismatch')
            if call['response'] and call['response']['model']!=study.MODEL:raise ValueError('Model drift')
            usage=int((call.get('response') or {}).get('usage',{}).get('input_tokens',0));tokens+=usage
            phase=call['site'].rsplit('/',1)[0];phases[phase]['calls']+=1;phases[phase]['input_tokens']+=usage;phases[phase]['latencies'].append(call['latency_seconds'])
            if call['error'] is None:
                if call['site'] in journal:raise ValueError('Duplicate successful call')
                journal[call['site']]=call
    if attempts!=execution['http_attempts'] or tokens!=execution['reported_input_tokens'] or len(journal)!=640:raise ValueError('Execution count mismatch')
    used=set()
    class Replay:
        def send(self,payload,site):
            if site in used or site not in journal or study.digest(payload)!=journal[site]['request_sha256']:raise ValueError('Reconstructed request mismatch')
            used.add(site);return journal[site]['response']
    saved=study.read(directory/'predictions.json');k=len(study.LABELS[task]);demos=parts['demonstrations']
    arrays={kind:{a:np.asarray(p) for a,p in data.items()} for kind,data in saved.items()}
    ordinary=[(a,i,c) for a in configs if a!='fewshot_contract' for i,c in enumerate(configs[a])]
    fewshot=[('fewshot_contract',i,c) for i,c in enumerate(configs['fewshot_contract'])]
    for r in range(3):
        for name,bank in [('ordinary',ordinary),('fewshot',fewshot)]:
            for j,row in enumerate(repeat):
                for (a,i),p in bank_call(Replay(),task,row,bank,demos,f'repeat-{r}/{name}').items():close(p,arrays['repeatability'][a][r,i,j].tolist(),'repeat')
    for name,bank in [('ordinary',ordinary),('fewshot',fewshot)]:
        for j,row in enumerate(batching):
            for (a,i),p in bank_call(Replay(),task,row,bank,demos,'batch/'+name).items():close(p,arrays['batched'][a][i,j].tolist(),'batched')
    for a in configs:
        for i,c in enumerate(configs[a]):
            for j,row in enumerate(batching):
                p=bank_call(Replay(),task,row,[(a,i,c)],demos,f'isolated/{a}/{i}')[(a,i)]
                close(p,arrays['isolated'][a][i,j].tolist(),'isolated')
    if used!=set(journal):raise ValueError('Unaccounted successful response')
    results=study.read(directory/'repeat-metrics.json');expected=[];drift=[]
    for a in configs:
        if arrays['repeatability'][a].shape!=(3,6,20,k) or arrays['batched'][a].shape!=(6,20,k) or arrays['isolated'][a].shape!=(6,20,k):raise ValueError('Bad prediction shape')
        for i in range(6):
            selection='baseline' if i==0 else 'dspy';seed=0 if i==0 else study.SEEDS[i-1];fit_index=0 if i==0 else 2*i-1;p=arrays['repeatability'][a][:,i]
            drift.append({'task':task,'arm':a,'selection':selection,'seed':seed,
                'repeat_rows_with_label_disagreement':int(np.sum(np.any(p.argmax(axis=2)!=p[0].argmax(axis=1),axis=0))),
                'repeat_max_probability_spread':float(np.max(np.max(p,axis=0)-np.min(p,axis=0))),
                'batch_vs_isolated_label_disagreements':int(np.sum(arrays['batched'][a][i].argmax(axis=1)!=arrays['isolated'][a][i].argmax(axis=1))),
                'batch_vs_isolated_max_probability_difference':float(np.max(np.abs(arrays['batched'][a][i]-arrays['isolated'][a][i])))})
            for method in ('raw','temperature','temperature_bias'):
                for r in range(3):
                    value=study.calibrated(arrays['repeatability'][a][r,i],fits[a][fit_index],method)
                    expected.append({'task':task,'arm':a,'selection':selection,'seed':seed,'calibration':method,'repeat':r,'metrics':study.evaluate_metrics(value,repeat,task)})
    close(expected,results,'repeat metrics');close(drift,study.read(directory/'drift.json'),'drift')
    stats={key:{'calls':v['calls'],'input_tokens':v['input_tokens'],'mean_request_seconds':float(np.mean(v['latencies'])),
                'median_request_seconds':float(np.median(v['latencies'])),'p95_request_seconds':float(np.quantile(v['latencies'],.95))} for key,v in phases.items()}
    close(stats,study.read(directory/'performance.json'),'performance')
    packing=[]
    for name,armset in [('ordinary',[a for a in configs if a!='fewshot_contract']),('fewshot',['fewshot_contract'])]:
        batch=stats['batch/'+name];keys=[f'isolated/{a}/{i}' for a in armset for i in range(6)]
        separate_calls=sum(stats[x]['calls'] for x in keys);separate_tokens=sum(stats[x]['input_tokens'] for x in keys)
        packing.append({'task':task,'input_group':name,'unique_inputs':20,'configurations':len(armset)*6,
            'batch_http_attempts':batch['calls'],'isolated_http_attempts':separate_calls,
            'batch_input_tokens':batch['input_tokens'],'isolated_input_tokens':separate_tokens,
            'input_token_saving_fraction':1-batch['input_tokens']/separate_tokens,
            'mean_batch_request_seconds':batch['mean_request_seconds'],
            'mean_isolated_request_seconds':statistics.mean(stats[x]['mean_request_seconds'] for x in keys),
            'note':'Request latency covers different numbers of predictions. Timing order/server load were not randomized between batch and isolated modes.'})
    costs=[]
    for a in configs:
        base=stats[f'isolated/{a}/0'];others=[stats[f'isolated/{a}/{i}'] for i in range(1,6)]
        costs.append({'task':task,'arm':a,'unique_inputs':20,'baseline_input_tokens_per_prediction':base['input_tokens']/20,
            'dspy_mean_input_tokens_per_prediction':sum(r['input_tokens'] for r in others)/100,
            'baseline_mean_request_seconds':base['mean_request_seconds'],
            'dspy_mean_request_seconds':statistics.mean(r['mean_request_seconds'] for r in others),
            'note':'Separate one-configuration requests. Includes inference only, not prompt search or local proposer CPU time.'})
    return results,drift,packing,costs,{'task':task,**execution,'capture_manifest_sha256':study.sha(directory/'artifact-manifest.json')}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,required=True);parser.add_argument('--primary',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();paths=sorted(p.parent for p in args.input.rglob('execution.json') if (p.parent/'protocol.json').exists())
    if len(paths)!=2:raise ValueError('Require both task captures')
    results=[];drift=[];packing=[];costs=[];executions=[]
    for path in paths:
        r,d,p,c,e=audit(path,args.primary);results+=r;drift+=d;packing+=p;costs+=c;executions.append(e)
    if {e['task'] for e in executions}!=set(study.ARMS):raise ValueError('Missing task')
    summary=[]
    for task,arms in study.ARMS.items():
        for arm in arms:
            for method in ('raw','temperature','temperature_bias'):
                baseline=[r for r in results if r['task']==task and r['arm']==arm and r['selection']=='baseline' and r['calibration']==method]
                seeds=[[r for r in results if r['task']==task and r['arm']==arm and r['selection']=='dspy' and r['seed']==seed and r['calibration']==method] for seed in study.SEEDS]
                if len(baseline)!=3 or any(len(s)!=3 for s in seeds):raise ValueError('Missing repetitions')
                entry={'task':task,'arm':arm,'calibration':method,'unique_evaluation_examples':20,'search_seeds':5,'service_repetitions_per_seed':3}
                for metric in ('accuracy','macro_f1','mcc','brier','log_loss','ece'):
                    b=[r['metrics'][metric] for r in baseline];s=[[r['metrics'][metric] for r in records] for records in seeds]
                    means=[statistics.mean(v) for v in s]
                    entry[metric]={'baseline_mean':statistics.mean(b),'baseline_service_std':statistics.stdev(b),
                        'dspy_mean':statistics.mean(means),'between_search_std':statistics.stdev(means),
                        'mean_within_search_service_std':statistics.mean(statistics.stdev(v) for v in s)}
                summary.append(entry)
    args.output.mkdir(parents=True,exist_ok=False)
    for name,value in [('repeat-metrics',results),('drift',drift),('packing',packing),('isolated-costs',costs),('execution',executions),('replication-summary',summary)]:study.write_json(args.output/(name+'.json'),value)
    flat=[{**{k:r[k] for k in ('task','arm','selection','seed','calibration','repeat')},**{k:r['metrics'][k] for k in ('n','accuracy','macro_f1','mcc','brier','log_loss','ece')}} for r in results]
    write_csv(args.output/'repeat-metrics.csv',flat)
    text=['# Fresh repeatability, batching and isolated inference costs','',
        'The original 20-row repeatability panels were evaluated three times per frozen configuration. The original 20-row batching panels are development examples, used for packing/performance diagnostics, not new held-out accuracy claims. All eight formulations, baseline plus five frozen accuracy-selected DSPy prompts, are included.',
        '', 'Every recorded request and prediction was reconstructed from its raw response. The paired packing test retains the original grouping: all non-few-shot formulations share one state; few-shot input remains separate. Individual requests use exactly the same configurations and examples.',
        '', '| Task / formulation | Baseline repeat accuracy | DSPy repeat accuracy | Between-search SD | Mean within-search service SD |',
        '|---|---:|---:|---:|---:|']
    for r in summary:
        if r['calibration']=='raw':
            m=r['accuracy'];text.append(f"| {r['task']} / {r['arm']} | {m['baseline_mean']:.4f} | {m['dspy_mean']:.4f} | {m['between_search_std']:.4f} | {m['mean_within_search_service_std']:.4f} |")
    text+=['','## Probability calibration and service variation','',
        '`replication-summary.json` reports raw, temperature and temperature-plus-bias metrics. Calibrators are reused from the disjoint primary calibration split; no fits are made on these 20 examples. Means and standard deviations describe search and service repetition axes separately. Repeated observations are not new independent test examples.',
        '', '`drift.json` counts label disagreements across service repeats and between batched and isolated calls, plus maximum probability differences. Do not interpret a score difference for an unchanged prompt as proof of optimization.',
        '', '## Inference cost and packing','',
        '`packing.json` compares actual reported input tokens for the same examples and configurations batched versus separate. `isolated-costs.json` measures baseline and DSPy token usage and request latency without cross-configuration batching. These exclude optimizer overhead, local model CPU time, CI time and external invoice verification. Batch request latency covers many predictions, so it is not directly equivalent to isolated one-configuration latency.',
        '', 'The packing modes were executed in blocks, not randomized across server load; latency comparisons are descriptive. All raw calls, including retries, are retained. Input-token cost estimates use the documented Jev price and are not invoices.','']
    (args.output/'REPORT.md').write_text('\n'.join(text),encoding='utf-8')
    study.write_json(args.output/'artifact-manifest.json',{'sha256':{p.relative_to(args.output).as_posix():study.sha(p) for p in sorted(args.output.rglob('*')) if p.is_file() and p.name!='artifact-manifest.json'}})

if __name__=='__main__':main()
