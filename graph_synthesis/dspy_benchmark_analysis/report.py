"""Verify and compare captured Jev observations; makes no network or model calls."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
from dataclasses import dataclass
import gzip
import json
from pathlib import Path
import statistics
import numpy as np
from graph_synthesis.dspy_benchmark.study import (
    ARMS, LABELS, MODEL, SEEDS, calibrated, evaluate_metrics, fit_calibration, prepare, read, sha)
from graph_synthesis.dspy_jev_optimizer.core import digest, write_json

METRICS = ('accuracy', 'macro_f1', 'mcc', 'brier', 'log_loss', 'ece', 'aurc',
           'correct_positive_edges', 'wrong_positive_edges')
METHODS = ('raw', 'temperature', 'temperature_bias')
BOOTSTRAPS = 2000


def close(a, b, context=''):
    if isinstance(a, dict):
        if set(a) != set(b): raise ValueError('Mismatched keys: '+context)
        for k in a: close(a[k], b[k], context+'/'+k)
    elif isinstance(a, list):
        if len(a) != len(b): raise ValueError('Mismatched length: '+context)
        for i,(x,y) in enumerate(zip(a,b)): close(x,y,context+'/'+str(i))
    elif isinstance(a, (float,int)) and not isinstance(a,bool):
        if not np.isclose(a,b,atol=2e-10,rtol=1e-9): raise ValueError('Mismatched value: '+context)
    elif a != b: raise ValueError('Mismatched value: '+context)


def clusters(rows):
    """Connected components of overlapping source/entity identities, not individual pairs."""
    parent=list(range(len(rows))); seen={}
    def root(i):
        while parent[i] != i:
            parent[i]=parent[parent[i]];i=parent[i]
        return i
    for i,row in enumerate(rows):
        for group in row['groups']:
            if group in seen: parent[root(i)]=root(seen[group])
            else:seen[group]=i
    components=defaultdict(list)
    for i in range(len(rows)):components[root(i)].append(i)
    return [np.asarray(v,dtype=int) for v in components.values()]


def weighted_scores(p,y,weights):
    p=np.asarray(p,dtype=float);pred=p.argmax(axis=1);n=weights.sum(axis=1)
    out={'accuracy':weights@(pred==y)/n,
         'log_loss':weights@(-np.log(np.clip(p[np.arange(len(y)),y],1e-15,1)))/n,
         'brier':weights@np.sum((p-np.eye(p.shape[1])[y])**2,axis=1)/n}
    confusion=np.asarray([weights@((y==g)&(pred==c)) for g in range(p.shape[1]) for c in range(p.shape[1])]).T.reshape(len(weights),p.shape[1],p.shape[1])
    truth=confusion.sum(axis=2);prediction=confusion.sum(axis=1)
    diag=np.diagonal(confusion,axis1=1,axis2=2)
    out['macro_f1']=np.divide(2*diag,truth+prediction,out=np.zeros_like(diag),where=truth+prediction>0).mean(axis=1)
    den=np.sqrt(np.maximum(0,(n*n-(truth*truth).sum(axis=1))*(n*n-(prediction*prediction).sum(axis=1))))
    out['mcc']=np.divide(diag.sum(axis=1)*n-(truth*prediction).sum(axis=1),den,out=np.zeros(len(n)),where=den>0)
    confidence=p.max(axis=1);bins=np.minimum(9,(confidence*10).astype(int));ece=np.zeros(len(n))
    for b in range(10):ece+=abs(weights@((bins==b)*(confidence-(pred==y))))/n
    out['ece']=ece
    return out


def paired_interval(base,candidates,rows,labels,seed=20260918):
    """The same sampled components are used for baseline and all five searches."""
    groups=clusters(rows);rng=np.random.default_rng(seed)
    weights=np.zeros((BOOTSTRAPS,len(rows)),dtype=float)
    counts=rng.multinomial(len(groups),np.full(len(groups),1/len(groups)),size=BOOTSTRAPS)
    for j,indices in enumerate(groups):weights[:,indices]=counts[:,j,None]
    y=np.asarray([labels.index(r['gold_label']) for r in rows]);baseline=weighted_scores(base,y,weights)
    cs=[weighted_scores(p,y,weights) for p in candidates];result={}
    ones=np.ones((1,len(rows)));bpoint=weighted_scores(base,y,ones);cpoints=[weighted_scores(p,y,ones) for p in candidates]
    for key in baseline:
        delta=np.mean([c[key] for c in cs],axis=0)-baseline[key]
        lo,hi=np.quantile(delta,[.025,.975])
        result[key]={'mean_paired_delta':float(np.mean([c[key][0] for c in cpoints])-bpoint[key][0]),
                     'cluster_bootstrap_95_percentile':[float(lo),float(hi)]}
    return {'n_examples':len(rows),'n_source_components':len(groups),'bootstrap_repetitions':BOOTSTRAPS,
            'interpretation':'Exploratory pointwise intervals conditional on frozen searches and fitted calibrators; no multiplicity correction or calibration-fit uncertainty.',
            'metrics':result}


@dataclass
class Capture:
    directory: Path
    task: str
    arm: str
    protocol: dict
    calibration: dict
    results: list
    panels: dict
    execution: dict
    calls: dict


def load_capture(directory):
    manifest=read(directory/'artifact-manifest.json')['sha256']
    for name,want in manifest.items():
        path=directory/name
        if not path.resolve().is_relative_to(directory.resolve()) or sha(path)!=want:
            raise ValueError('Capture hash mismatch: '+str(path))
    execution=read(directory/'execution.json')
    if execution.get('status')!='completed' or execution.get('live') is not True:
        raise ValueError('Capture is not a completed live run: '+str(directory))
    protocol=read(directory/'protocol.json');task,arm=protocol['task'],protocol['arm']
    if task not in ARMS or arm not in ARMS[task] or protocol['model']!=MODEL or protocol['seeds']!=SEEDS:
        raise ValueError('Unexpected protocol identity')
    from graph_synthesis.dspy_benchmark.study import ROOT, probabilities
    for name,want in protocol['data_hashes'].items():
        if sha(ROOT/name)!=want:raise ValueError('Dataset hash mismatch')
    plan,parts,expected_panels=prepare(task)
    for name,rows in parts.items():
        if protocol['split_ids'][name]!=[r['id'] for r in rows]:raise ValueError('Split changed')
    frozen=read(directory/'freeze.json')
    if digest(frozen['payload'])!=frozen['sha256'] or frozen['payload']['protocol_sha256']!=digest(protocol):
        raise ValueError('Freeze integrity failure')
    for search in frozen['payload']['searches']:
        if digest(read(directory/f"search-{search['seed']}.json"))!=search['ledger_sha256']:
            raise ValueError('Search ledger integrity failure')
    cal=read(directory/'calibration.json');results=read(directory/'results.json');panels={};keys=set()
    for panel,rows in expected_panels.items():
        saved=read(directory/(panel+'-predictions.json'))
        if [r['id'] for r in saved['rows']]!=[r['id'] for r in rows]:raise ValueError('Panel IDs changed')
        if [r['gold_label'] for r in saved['rows']]!=[r['gold_label'] for r in rows]:raise ValueError('Panel labels changed')
        p=np.asarray(saved['probabilities'])
        if p.shape != (11,len(rows),len(LABELS[task])):raise ValueError('Missing prediction grid')
        expected_variants=[{'selection':'baseline','seed':0}]+[{'selection':s,'seed':j} for j in SEEDS for s in ('accuracy','nll')]
        if saved['variants']!=expected_variants:raise ValueError('Variant order changed')
        panels[panel]=saved
        for i,variant in enumerate(saved['variants']):
            key=(variant['selection'],variant['seed'])
            for method in METHODS:
                matches=[r for r in results if r['panel']==panel and r['selection']==key[0] and r['seed']==key[1] and r['calibration']==method]
                if len(matches)!=1:raise ValueError('Duplicate or missing result')
                recomputed=evaluate_metrics(calibrated(p[i],cal['fits'][i],method),rows,task)
                close(recomputed,matches[0]['metrics'],f'{task}/{arm}/{panel}/{key}/{method}')
                keys.add((panel,*key,method))
    if len(keys)!=len(results):raise ValueError('Unaccounted results')
    calls={};n_calls=tokens=0;phase=Counter();latency=defaultdict(list)
    with gzip.open(directory/'calls.jsonl.gz','rt',encoding='utf-8') as handle:
        for line in handle:
            record=json.loads(line);n_calls+=1
            if record['request_sha256']!=digest(record['payload']):raise ValueError('Request hash differs')
            if record['payload']['model']!=MODEL:raise ValueError('Model drift')
            kind=record['site'].split('/')[0];phase[kind]+=1;latency[kind].append(record['latency_seconds'])
            if record['response']:
                if record['response']['model']!=MODEL:raise ValueError('Response model drift')
                tokens+=int(record['response'].get('usage',{}).get('input_tokens',0))
            if (record['site'].startswith('test/') or record['site'].startswith('calibration/')) and record['error'] is None:
                if record['site'] in calls:raise ValueError('Duplicate final inference')
                calls[record['site']]=record
    if n_calls!=execution['http_attempts'] or tokens!=execution['reported_input_tokens']:
        raise ValueError('Usage audit mismatch')
    configs=[protocol['baseline']]+[s[objective+'_questions'] for s in frozen['payload']['searches'] for objective in ('accuracy','nll')]
    order=list(plan['question_specs'][task][arm]);configs=[{k:cfg[k] for k in order} for cfg in configs]
    if cal['ids'] != [r['id'] for r in parts['calibration']]:raise ValueError('Calibration IDs changed')
    ycal=[LABELS[task].index(r['gold_label']) for r in parts['calibration']]
    if cal['gold'] != ycal:raise ValueError('Calibration labels changed')
    pc=np.asarray(cal['probabilities'])
    if pc.shape != (11,len(ycal),len(LABELS[task])):raise ValueError('Missing calibration grid')
    for j,row in enumerate(parts['calibration']):
        call=calls['calibration/'+row['id']]
        for i,cfg in enumerate(configs):
            actual=probabilities({k:call['response']['answers'][f'v{i}__{k}'] for k in cfg},task,cfg)
            close(actual,cal['probabilities'][i][j],f'calibration/raw/{i}/{j}')
    for i,probs in enumerate(pc):
        again=fit_calibration(probs,ycal)
        for method in METHODS:
            if not np.allclose(calibrated(probs,again,method),calibrated(probs,cal['fits'][i],method),atol=2e-5,rtol=2e-5):
                raise ValueError('Calibration refit differs from archived fit')
    for panel,saved in panels.items():
        for j,row in enumerate(saved['rows']):
            call=calls['test/'+panel+'/'+row['id']]
            for i,cfg in enumerate(configs):
                raw=probabilities({k:call['response']['answers'][f'v{i}__{k}'] for k in cfg},task,cfg)
                close(raw,saved['probabilities'][i][j],f'raw/{panel}/{i}/{j}')
    execution={**execution,'attempts_by_phase':dict(phase),
               'latency_seconds_by_phase':{k:{'median':float(np.median(v)),'p95':float(np.quantile(v,.95))} for k,v in latency.items()}}
    return Capture(directory,task,arm,protocol,cal,results,panels,execution,calls)


def write_csv(path,rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def summaries(results):
    buckets=defaultdict(list)
    for r in results:buckets[tuple(r[k] for k in ('task','arm','panel','selection','calibration'))].append(r)
    output=[]
    for key,rows in sorted(buckets.items()):
        n=1 if key[3]=='baseline' else 5
        if len(rows)!=n:raise ValueError('Incomplete seed group')
        entry=dict(zip(('task','arm','panel','selection','calibration'),key));entry['runs']=n
        entry['test_examples_per_run']=rows[0]['metrics']['n']
        for m in METRICS:
            v=[r['metrics'][m] for r in rows]
            entry[m]={'mean':statistics.mean(v),'std':statistics.stdev(v) if n>1 else 0.,'min':min(v),'max':max(v)}
        output.append(entry)
    return output


def graph_replay(capture):
    """Apply new captured probabilities to the existing graph compiler, without inference."""
    from graph_synthesis.recorded import ScoredDecision
    from graph_synthesis.study import make_graph
    _,parts,_=prepare(capture.task);rows=parts['evaluation'];saved=capture.panels['evaluation'];output=[]
    for i,v in enumerate(saved['variants']):
        for method in METHODS:
            p=calibrated(np.asarray(saved['probabilities'][i]),capture.calibration['fits'][i],method);values=[]
            for row,probs in zip(rows,p):
                label=LABELS[capture.task][int(np.argmax(probs))];raw=capture.calls['test/evaluation/'+row['id']]
                binding=digest({'raw_request_sha256':raw['request_sha256'],'variant':i,
                                'calibration_method':method,'fit':capture.calibration['fits'][i] if method!='raw' else None})
                decision=ScoredDecision(dict(zip(LABELS[capture.task],map(float,probs))),label,MODEL,'recorded',binding,row['id'])
                values.append({'id':row['id'],'group':row.get('group',row['id']),'gold':row['gold_label'],
                               'label':label,'score':float(max(probs)),'row':row,'decision':decision})
            for threshold in (0.,.9):
                result=make_graph(values,capture.task,threshold);result.pop('accepted_assertion_ids',None)
                output.append({'task':capture.task,'arm':capture.arm,**v,'calibration':method,**result})
    return output


def analyze(captures,out,graphs=False):
    out.mkdir(parents=True,exist_ok=False)
    results=[r for cap in captures for r in cap.results];summary=summaries(results)
    write_json(out/'all-results.json',results)
    flat=[{**{k:r[k] for k in ('task','arm','panel','selection','seed','calibration')},**{k:r['metrics'][k] for k in ('n',)+METRICS}} for r in results]
    write_csv(out/'all-results.csv',flat);write_json(out/'seed-summary.json',summary)
    write_json(out/'execution.json',[{'task':c.task,'arm':c.arm,**c.execution} for c in captures])
    intervals=[];changes=[];ledger_stats=[];calibration_effects=[]
    for cap in captures:
        for seed in SEEDS:
            ledger=read(cap.directory/f'search-{seed}.json')
            ledger_stats.append({'task':cap.task,'arm':cap.arm,'seed':seed,'statuses':dict(Counter(e['status'] for e in ledger)),
                                 'best_validation_accuracy':max(e['validation']['accuracy'] for e in ledger if e.get('validation'))})
        for panel,saved in cap.panels.items():
            rows=saved['rows'];p=np.asarray(saved['probabilities']);variants=saved['variants'];y=np.asarray([LABELS[cap.task].index(r['gold_label']) for r in rows])
            base={m:calibrated(p[0],cap.calibration['fits'][0],m) for m in METHODS}
            for select in ('accuracy','nll'):
                indices=[i for i,v in enumerate(variants) if v['selection']==select]
                for method in METHODS:
                    cs=[calibrated(p[i],cap.calibration['fits'][i],method) for i in indices]
                    intervals.append({'task':cap.task,'arm':cap.arm,'panel':panel,'selection':select,'calibration':method,
                                      **paired_interval(base[method],cs,rows,LABELS[cap.task])})
                    for i,c in zip(indices,cs):
                        bp=base[method].argmax(axis=1);cp=c.argmax(axis=1)
                        changes.append({'task':cap.task,'arm':cap.arm,'panel':panel,'selection':select,'seed':variants[i]['seed'],'calibration':method,
                            'baseline_wrong_candidate_right':int(np.sum((bp!=y)&(cp==y))),
                            'baseline_right_candidate_wrong':int(np.sum((bp==y)&(cp!=y))),
                            'both_wrong':int(np.sum((bp!=y)&(cp!=y))),
                            'changed_prediction_ids':[r['id'] for r,b,c_ in zip(rows,bp,cp) if b!=c_]})
            for i,v in enumerate(variants):
                raw=evaluate_metrics(p[i],rows,cap.task)
                for method in METHODS[1:]:
                    transformed=calibrated(p[i],cap.calibration['fits'][i],method);cal=evaluate_metrics(transformed,rows,cap.task)
                    changed=int(np.sum(p[i].argmax(axis=1)!=transformed.argmax(axis=1)))
                    if method=='temperature' and changed:raise ValueError('Scalar temperature changed argmax')
                    calibration_effects.append({'task':cap.task,'arm':cap.arm,'panel':panel,**v,'calibration':method,'changed_labels':changed,
                       **{m+'_delta':cal[m]-raw[m] for m in METRICS}})
    write_json(out/'paired-intervals.json',intervals);write_json(out/'prediction-changes.json',changes)
    write_json(out/'search-summary.json',ledger_stats);write_json(out/'calibration-effects.json',calibration_effects)
    if graphs:
        replay=[]
        for cap in captures:
            replay.extend(graph_replay(cap));print('Graph replay:',cap.task,cap.arm,flush=True)
        write_json(out/'graph-replay.json',replay)
    write_json(out/'input-manifest.json',{'captures':{c.task+'--'+c.arm:sha(c.directory/'artifact-manifest.json') for c in captures},
                'analysis_source_sha256':sha(__file__),'note':'Capture manifests bind raw observations; this report does not run a model.'})
    render(out,summary,captures,graphs)
    write_json(out/'artifact-manifest.json',{'sha256':{p.relative_to(out).as_posix():sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='artifact-manifest.json'}})


def render(out,summary,captures,graphs):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figure_dir=out/'figures';figure_dir.mkdir();table=[]
    for c in captures:
        key={'task':c.task,'arm':c.arm,'panel':'evaluation'}
        find=lambda s,m:next(r for r in summary if all(r[k]==v for k,v in key.items()) and r['selection']==s and r['calibration']==m)
        base=find('baseline','raw');dspy=find('accuracy','raw');temp=find('accuracy','temperature');bias=find('accuracy','temperature_bias')
        table.append(f"| {c.task} / {c.arm} | {base['accuracy']['mean']:.4f} | {dspy['accuracy']['mean']:.4f} ± {dspy['accuracy']['std']:.4f} | {dspy['log_loss']['mean']:.4f} | {temp['log_loss']['mean']:.4f} | {bias['log_loss']['mean']:.4f} |")
        relevant=[r for r in summary if r['task']==c.task and r['arm']==c.arm and r['panel']=='evaluation' and r['selection'] in ('baseline','accuracy')]
        for metric in ('accuracy','log_loss','brier','ece'):
            fig,ax=plt.subplots(figsize=(9,5))
            for selection,label in [('baseline','Jev baseline'),('accuracy','Jev + DSPy (five searches)')]:
                rows=[next(r for r in relevant if r['selection']==selection and r['calibration']==m) for m in METHODS]
                ax.errorbar(range(3),[r[metric]['mean'] for r in rows],yerr=[r[metric]['std'] for r in rows],marker='o',capsize=4,label=label)
            ax.set_xticks(range(3),['Raw','Temperature','Temperature + bias']);ax.set_ylabel(metric.replace('_',' ').title())
            ax.set_title(c.task.replace('_',' ').title()+' — '+c.arm);ax.legend();ax.grid(axis='y',alpha=.2);fig.tight_layout()
            stem=f'{c.task}--{c.arm}--{metric}';fig.savefig(figure_dir/(stem+'.png'),dpi=300);fig.savefig(figure_dir/(stem+'.svg'));plt.close(fig)
    attempts=sum(c.execution['http_attempts'] for c in captures);tokens=sum(c.execution['reported_input_tokens'] for c in captures)
    text=['# Repeated DSPy and calibration comparison','','## Execution scope','',
          f'Completed captures: **{len(captures)}/8 formulations**, {len(captures)*5} seed-labelled DSPy searches, {attempts:,} Jev HTTP attempts, {tokens:,} reported input tokens.',
          '','Every reported result was reconstructed from saved distributions, every final probability was checked against its raw Jev response, and calibration fits were independently reproduced. Five prompt-search seeds share the same test examples; they are not five independent datasets.',
          '','## Main held-out panels','',
          '| Task / original formulation | Baseline accuracy | DSPy accuracy mean ± SD | DSPy raw NLL | DSPy temperature NLL | DSPy temperature + bias NLL |',
          '|---|---:|---:|---:|---:|---:|',*table,'',
          'Scalar temperature is a probability-quality intervention and leaves argmax accuracy unchanged. Temperature plus bias may change labels. Neither calibration method is guaranteed to improve held-out results.',
          '', '## Evidence and interpretation','',
          '- `all-results.csv` and `all-results.json`: every seed, formulation, panel, selection rule and calibration method, including confusion matrices in JSON.',
          '- `seed-summary.json`: means, sample standard deviations, minima and maxima; no best-test-seed selection.',
          '- `paired-intervals.json`: paired source-component bootstrap for mean search performance versus its same-method baseline. Pointwise exploratory 95% intervals are conditional on the selected prompts and fitted calibrators.',
          '- `calibration-effects.json`: each raw-to-calibrated delta and count of changed labels.',
          '- `prediction-changes.json`: paired repaired errors and regressions; `search-summary.json`: malformed, duplicate, rejected and accepted proposals.',
          '- `execution.json`: actual calls, usage and latency by phase. Final variants were batched, so isolated per-variant latency/cost was not measured.',
          '- `graph-replay.json`: compiler/topology/lifecycle behavior using the new probabilities at fixed thresholds 0 and 0.9.' if graphs else '- Graph replay was not requested in this analysis invocation.',
          '', '## Limits','',
          'These are public, previously evaluated panels: retrospective exploratory evidence, not a new untouched external benchmark. The local Qwen2.5-1.5B proposer, 31-example training / 29-example validation panels and three-round budget limit conclusions about larger models or longer searches. The NLL-selected arm comes from the accuracy-guided candidate pool; it is not a separate NLL-directed search.',
          '', 'All original question types and demonstrations are preserved. Original deterministic graph suites are separate replay/regression checks, not independent live semantic benchmarks. The seven original multi-call workflows have a separately reported frozen-prompt transfer experiment; question-level evaluation alone must not be represented as that experiment. Specialist retraining and open-corpus retrieval remain outside this run.',
          '', 'Calibration fits use only the disjoint calibration split. Bootstrap intervals do not include refitting uncertainty, distribution shift, or multiple-testing correction. Confidence gains are not proof of better calibration; inspect Brier/NLL and calibration deltas together.',
          '', '## Sources','',
          '- TypeSafe API: https://docs.typesafe.ai/api',
          '- Guo et al. (2017), On Calibration of Modern Neural Networks: https://proceedings.mlr.press/v70/guo17a.html',
          '- Official proposal model: https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF','']
    (out/'REPORT.md').write_text('\n'.join(text),encoding='utf-8')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--graphs',action='store_true');p.add_argument('--allow-partial',action='store_true');args=p.parse_args()
    paths=sorted(path.parent for path in args.input.rglob('execution.json') if (path.parent/'protocol.json').exists())
    captures=[load_capture(path) for path in paths]
    ids={(c.task,c.arm) for c in captures};expected={(t,a) for t,arms in ARMS.items() for a in arms}
    if len(ids)!=len(captures) or (not args.allow_partial and ids!=expected) or not captures:raise ValueError('Missing/duplicate task/formulation captures')
    analyze(captures,args.output,args.graphs)

if __name__=='__main__':main()
