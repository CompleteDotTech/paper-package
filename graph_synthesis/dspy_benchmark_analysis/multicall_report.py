"""Audit live multi-call transfer and fit decision-frozen forecast calibrators."""
from __future__ import annotations
import argparse
import gzip
import json
from pathlib import Path
import statistics
import numpy as np
from graph_synthesis.dspy_benchmark.study import (MODEL,SEEDS,ROOT,EXTRA,prepare,read,sha,calibrated,fit_calibration,evaluate_metrics)
from graph_synthesis.dspy_jev_optimizer.core import digest,write_json
from graph_synthesis.dspy_multicall.run import SHARDS,load_configs,evaluate_row
from graph_synthesis.multicall import ARMS,LABELS
from .report import close,paired_interval,write_csv,clusters
METHODS=('raw','temperature','temperature_bias')


def policy_metrics(rows,workflow,variant):
    labels=list(LABELS);k=len(labels);confusion=np.zeros((k,k+1),dtype=int)
    accepted=correct=wrong_edges=correct_edges=0
    for row in rows:
        result=row['variants'][variant]['workflows'][workflow]
        gold=labels.index(row['gold_label']);chosen=result['label']
        pred=labels.index(chosen) if chosen in labels and result['status']=='ok' else k
        confusion[gold,pred]+=1;accepted+=int(pred<k);correct+=int(pred==gold)
        wrong_edges+=int(pred<k and labels[pred]!='NOT_ENOUGH_INFO' and pred!=gold)
        correct_edges+=int(pred<k and labels[pred]!='NOT_ENOUGH_INFO' and pred==gold)
    truth=confusion.sum(axis=1);forecast=confusion[:,:k].sum(axis=0);diag=np.diag(confusion[:,:k])
    f1=np.divide(2*diag,truth+forecast,out=np.zeros(k,dtype=float),where=truth+forecast>0)
    true_full=np.r_[truth,0];pred_full=confusion.sum(axis=0);n=len(rows)
    denominator=float(np.sqrt((n*n-np.sum(true_full**2))*(n*n-np.sum(pred_full**2))))
    mcc=(correct*n-float(true_full@pred_full))/denominator if denominator else 0.
    return {'n':n,'accuracy':correct/n,'macro_f1':float(f1.mean()),'mcc':mcc,
        'confusion_labels':labels+['ABSTAIN_OR_ERROR'],'coverage':accepted/n,
        'conditional_accuracy':correct/accepted if accepted else None,
        'abstentions_or_errors':n-accepted,'wrong_positive_edges':wrong_edges,
        'correct_positive_edges':correct_edges,'confusion_rows_gold_columns_pred_plus_abstention':confusion.tolist()}


def policy_paired_interval(rows,workflow):
    groups=clusters([{'groups':[row['group']]} for row in rows]);rng=np.random.default_rng(20260918)
    counts=rng.multinomial(len(groups),np.full(len(groups),1/len(groups)),size=2000)
    w=np.zeros((2000,len(rows)))
    for i,indices in enumerate(groups):w[:,indices]=counts[:,i,None]
    correct=np.asarray([[row['variants'][i]['workflows'][workflow]['label']==row['gold_label'] and row['variants'][i]['workflows'][workflow]['status']=='ok' for row in rows] for i in range(6)],dtype=float)
    delta=correct[1:].mean(axis=0)-correct[0];effects=w@delta/w.sum(axis=1)
    return {'mean_accuracy_delta':float(delta.mean()),'cluster_bootstrap_95_percentile':np.quantile(effects,[.025,.975]).tolist(),
            'n_examples':len(rows),'n_source_components':len(groups),'repetitions':2000,
            'interpretation':'Exploratory conditional-on-prompts paired interval; no multiplicity correction.'}


def load_shards(input_dir,capture):
    variants,freeze_hash=load_configs(capture);plan=read(ROOT/EXTRA);_,parts,_=prepare('relation_support')
    expected=[('calibration',r) for r in parts['calibration']]+[('additional_corpus',r) for r in plan['rows']]
    paths=sorted(p.parent for p in input_dir.rglob('execution.json') if (p.parent/'protocol.json').exists())
    seen=set();allrows=[];executions=[];seen_rows=set()
    for path in paths:
        protocol=read(path/'protocol.json');execution=read(path/'execution.json');shard=protocol['shard']
        if shard in seen or not 0<=shard<SHARDS:raise ValueError('Duplicate/unknown shard')
        seen.add(shard)
        if protocol['upstream_freeze_sha256']!=freeze_hash or protocol['model']!=MODEL:raise ValueError('Wrong frozen upstream')
        if protocol['original_plan_sha256']!=sha(ROOT/EXTRA) or protocol['original_multicall_source_sha256']!=sha(ROOT/'graph_synthesis/multicall.py'):
            raise ValueError('Original workflow or data changed')
        if execution['status']!='completed' or not execution['live']:raise ValueError('Incomplete live capture')
        for name,want in read(path/'artifact-manifest.json')['sha256'].items():
            if not (path/name).resolve().is_relative_to(path.resolve()) or sha(path/name)!=want:raise ValueError('Capture integrity failure')
        journal={};attempts=tokens=0
        with gzip.open(path/'calls.jsonl.gz','rt',encoding='utf-8') as handle:
            for line in handle:
                call=json.loads(line);attempts+=1
                if digest(call['payload'])!=call['request_sha256']:raise ValueError('Request hash mismatch')
                if call['payload']['model']!=MODEL:raise ValueError('Model drift')
                if call['response']:
                    if call['response']['model']!=MODEL:raise ValueError('Response drift')
                    tokens+=int(call['response'].get('usage',{}).get('input_tokens',0))
                if call['error'] is None:
                    if call['site'] in journal:raise ValueError('Duplicate successful logical call')
                    journal[call['site']]=call
        if attempts!=execution['http_attempts'] or tokens!=execution['reported_input_tokens']:raise ValueError('Usage mismatch')
        recorded={}
        with gzip.open(path/'predictions.jsonl.gz','rt',encoding='utf-8') as handle:
            for line in handle:
                row=json.loads(line);key=(row['phase'],row['id'])
                if key in recorded or key in seen_rows:raise ValueError('Duplicate row')
                recorded[key]=row;seen_rows.add(key)
        assigned=[(phase,row) for i,(phase,row) in enumerate(expected) if i%SHARDS==shard]
        if set(recorded)!={(phase,row['id']) for phase,row in assigned}:raise ValueError('Missing/additional shard rows')
        used=set()
        class Replay:
            def send(self,payload,site):
                if site not in journal:raise ValueError('Missing raw service call')
                call=journal[site]
                if digest(payload)!=call['request_sha256']:raise ValueError('Reconstructed request differs')
                if site in used:raise ValueError('Duplicate replay access')
                used.add(site);return call['response']
        for phase,row in assigned:
            actual=evaluate_row(row,plan,variants,Replay(),phase)
            close(actual,recorded[(phase,row['id'])],'multicall/'+str(shard)+'/'+row['id']);allrows.append(actual)
        if used!=set(journal):raise ValueError('Unaccounted successful observations')
        executions.append({'shard':shard,**execution,'capture_manifest_sha256':sha(path/'artifact-manifest.json')})
        print('Verified multi-call shard',shard,'rows',len(assigned),flush=True)
    if seen!=set(range(SHARDS)):raise ValueError('A full comparison requires all eight shards')
    index={(phase,r['id']):i for i,(phase,r) in enumerate(expected)}
    allrows.sort(key=lambda r:index[(r['phase'],r['id'])])
    return allrows,executions,freeze_hash


def report(input_dir,capture,out):
    allrows,executions,freeze_hash=load_shards(input_dir,capture)
    calibration=[r for r in allrows if r['phase']=='calibration'];test=[r for r in allrows if r['phase']=='additional_corpus']
    if len(calibration)!=150 or len(test)!=336:raise ValueError('Unexpected panel sizes')
    fits={};result=[];policy=[];intervals=[];effects=[]
    for workflow in ARMS:
        c=np.asarray([[r['variants'][i]['workflows'][workflow]['forecast'] for r in calibration] for i in range(6)])
        y=[list(LABELS).index(r['gold_label']) for r in calibration];fits[workflow]=[fit_calibration(p,y) for p in c]
        panels={'full_transfer':test,'original_development':[r for r in test if r['original_split']=='development'],
                'original_test':[r for r in test if r['original_split']=='test']}
        for panel,rows in panels.items():
            if not rows:raise ValueError('Missing panel')
            base_rows=[{'id':r['id'],'gold_label':r['gold_label'],'groups':[r['group']]} for r in rows]
            ps=np.asarray([[r['variants'][i]['workflows'][workflow]['forecast'] for r in rows] for i in range(6)])
            for i in range(6):
                selection='baseline' if i==0 else 'dspy';seed=0 if i==0 else SEEDS[i-1]
                fixed=policy_metrics(rows,workflow,i);policy.append({'workflow':workflow,'panel':panel,'selection':selection,'seed':seed,**fixed})
                before=evaluate_metrics(ps[i],base_rows,'relation_support')
                for method in METHODS:
                    p=calibrated(ps[i],fits[workflow][i],method);m=evaluate_metrics(p,base_rows,'relation_support')
                    result.append({'workflow':workflow,'panel':panel,'selection':selection,'seed':seed,'calibration':method,
                        'policy_accuracy':fixed['accuracy'],'policy_coverage':fixed['coverage'],'forecast_metrics':m})
                    if method!='raw':effects.append({'workflow':workflow,'panel':panel,'selection':selection,'seed':seed,'calibration':method,
                        'policy_accuracy_delta':0.0,'forecast_accuracy_delta':m['accuracy']-before['accuracy'],
                        **{key+'_delta':m[key]-before[key] for key in ('brier','log_loss','ece')}})
            interval={'workflow':workflow,'panel':panel,'policy':policy_paired_interval(rows,workflow),'forecast':{}}
            for method in METHODS:
                p=[calibrated(ps[i],fits[workflow][i],method) for i in range(6)]
                interval['forecast'][method]=paired_interval(p[0],p[1:],base_rows,list(LABELS))
            intervals.append(interval)
    out.mkdir(parents=True,exist_ok=False)
    write_json(out/'all-results.json',result);write_json(out/'policy-results.json',policy)
    write_json(out/'calibration-fits.json',{'upstream_freeze_sha256':freeze_hash,'n_calibration':150,'fits':fits})
    write_json(out/'calibration-effects.json',effects);write_json(out/'paired-intervals.json',intervals);write_json(out/'execution.json',executions)
    flat=[{**{k:v for k,v in r.items() if k!='forecast_metrics'},**{'forecast_'+k:r['forecast_metrics'][k] for k in ('n','accuracy','macro_f1','mcc','brier','log_loss','ece','aurc')}} for r in result]
    write_csv(out/'all-results.csv',flat)
    write_json(out/'input-manifest.json',{'upstream_capture_manifest_sha256':sha(capture/'artifact-manifest.json'),
             'analysis_source_sha256':sha(__file__),'note':'Every workflow result and request was reconstructed from captured live responses.'})
    summaries=[]
    for workflow in ARMS:
        for panel in ('full_transfer','original_development','original_test'):
            for selection in ('baseline','dspy'):
                for method in METHODS:
                    selected=[r for r in flat if r['workflow']==workflow and r['panel']==panel and r['selection']==selection and r['calibration']==method]
                    if len(selected)!=(1 if selection=='baseline' else 5):raise ValueError('Missing seeds')
                    entry={'workflow':workflow,'panel':panel,'selection':selection,'calibration':method,'runs':len(selected)}
                    for key in ['policy_accuracy','policy_coverage']+['forecast_'+k for k in ('accuracy','macro_f1','mcc','brier','log_loss','ece','aurc')]:
                        values=[r[key] for r in selected];entry[key]={'mean':statistics.mean(values),'std':statistics.stdev(values) if len(values)>1 else 0.,'min':min(values),'max':max(values)}
                    summaries.append(entry)
    write_json(out/'seed-summary.json',summaries);render(out,summaries,executions)
    write_json(out/'artifact-manifest.json',{'sha256':{p.relative_to(out).as_posix():sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='artifact-manifest.json'}})


def render(out,summary,executions):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figures=out/'figures';figures.mkdir();table=[]
    def get(workflow,selection,method):return next(r for r in summary if r['workflow']==workflow and r['panel']=='full_transfer' and r['selection']==selection and r['calibration']==method)
    for workflow in ARMS:
        baseline=get(workflow,'baseline','raw');raw=get(workflow,'dspy','raw');temp=get(workflow,'dspy','temperature');bias=get(workflow,'dspy','temperature_bias')
        table.append(f"| {workflow} | {baseline['policy_accuracy']['mean']:.4f} | {raw['policy_accuracy']['mean']:.4f} ± {raw['policy_accuracy']['std']:.4f} | {raw['policy_coverage']['mean']:.4f} | {raw['forecast_log_loss']['mean']:.4f} | {temp['forecast_log_loss']['mean']:.4f} | {bias['forecast_log_loss']['mean']:.4f} |")
    for metric in ('policy_accuracy','forecast_log_loss','forecast_brier','forecast_ece'):
        fig,ax=plt.subplots(figsize=(12,6));x=np.arange(len(ARMS))
        for selection,method,label in [('baseline','raw','Baseline'),('dspy','raw','DSPy'),('dspy','temperature','DSPy + temperature'),('dspy','temperature_bias','DSPy + temperature/bias')]:
            rows=[get(w,selection,method) for w in ARMS]
            ax.errorbar(x,[r[metric]['mean'] for r in rows],yerr=[r[metric]['std'] for r in rows],marker='o',capsize=3,label=label)
        ax.set_xticks(x,ARMS,rotation=20);ax.set_ylabel(metric.replace('_',' ').title());ax.set_title('Frozen-prompt transfer through seven multi-call workflows')
        ax.legend();ax.grid(axis='y',alpha=.2);fig.tight_layout();fig.savefig(figures/(metric+'.png'),dpi=300);fig.savefig(figures/(metric+'.svg'));plt.close(fig)
    calls=sum(e['http_attempts'] for e in executions);tokens=sum(e['reported_input_tokens'] for e in executions)
    text=['# DSPy multi-call transfer and decision-frozen calibration','',
        f'All eight shards completed: **486 examples** (150 calibration + 336 transfer), **{calls:,} HTTP attempts**, **{tokens:,} reported input tokens**.',
        '', 'The original primary-verifier prompt and all five frozen DSPy accuracy-selected prompts were run through every original multi-call workflow. No prompt was selected using transfer-test outcomes. All requests and policy decisions were reconstructed from raw responses.',
        '', '| Workflow | Baseline policy accuracy | DSPy policy accuracy mean ± SD | DSPy coverage | DSPy raw forecast NLL | Temperature NLL | Temperature + bias NLL |',
        '|---|---:|---:|---:|---:|---:|---:|',*table,'',
        '## What calibration changes','',
        'These calibrations change only the normalized forecasts, not the original votes, abstentions, escalation threshold, or adjudication inputs. Policy accuracy is identical across calibration methods by construction. Forecast argmax accuracy is a different endpoint and is reported separately. For voting workflows the normalized forecast is the mean component distribution, not an independence product.',
        '', '## Coverage and uncertainty','',
        'All seven workflow methods, six prompt variants, three calibration methods, and three transfer-panel views are retained in `all-results.json` and `all-results.csv`. `policy-results.json` counts abstentions as incorrect for unconditional accuracy and separately reports coverage, conditional accuracy, confusion matrices, and wrong/correct positive edges. `seed-summary.json` includes means, standard deviations, minima and maxima.',
        '', '`paired-intervals.json` uses the same source-cluster resampling for baseline and all five search variants. Repeated uses of each example are not independent datasets. Intervals are exploratory and conditional on selected prompts/calibrators. `calibration-effects.json` isolates forecast-quality changes.',
        '', '## Limits','',
        'Only the primary verifier prompt changes. Other reviewers, dimension checks, adjudication instructions, examples and workflow rules are fixed. This is not DSPy optimization of every multi-agent component. Controls are shared and verifier questions batched; isolated per-variant latency and production cost were not measured. This public, already evaluated corpus is not a new external holdout. The small local proposer and three-round searches limit conclusions about larger/longer optimization.',
        '', 'Calibration fits use only the separate 150-row calibration split. The full 336-row transfer panel and original development/test subpanels are never used for fitting. Existing frozen evidence remains unchanged.','']
    (out/'REPORT.md').write_text('\n'.join(text),encoding='utf-8')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--capture',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();report(a.input,a.capture,a.output)

if __name__=='__main__':main()
