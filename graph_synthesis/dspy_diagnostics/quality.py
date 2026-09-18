"""Post-capture diagnostics; never used for prompt or calibrator selection."""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import gzip
import json
from pathlib import Path
import numpy as np
from graph_synthesis.dspy_benchmark import study
from graph_synthesis.dspy_benchmark_v2.adapter import distribution


def diagnose(directory):
    protocol=study.read(directory/'protocol.json');task=protocol['task'];arm=protocol['arm']
    execution=study.read(directory/'execution.json')
    if execution.get('status')!='completed' or execution.get('live') is not True:raise ValueError('Capture did not complete live')
    for name,want in study.read(directory/'artifact-manifest.json')['sha256'].items():
        if not (directory/name).resolve().is_relative_to(directory.resolve()) or study.sha(directory/name)!=want:raise ValueError('Capture integrity mismatch')
    frozen=study.read(directory/'freeze.json')
    if study.digest(frozen['payload'])!=frozen['sha256'] or frozen['payload']['protocol_sha256']!=study.digest(protocol):raise ValueError('Freeze mismatch')
    if protocol.get('revision')!=2:raise ValueError('Only amendment-v2 captures are comparable here')
    freeze=frozen['payload']
    variants=[('baseline',0,protocol['baseline'])]+[(select,r['seed'],r[select+'_questions']) for r in freeze['searches'] for select in ('accuracy','nll')]
    configs=[study.digest(v[2]) for v in variants]
    grouped=defaultdict(list)
    for i,key in enumerate(configs):grouped[key].append(i)
    groups=[v for v in grouped.values() if len(v)>1]
    flags=defaultdict(set);quality=Counter();mass_errors=[]
    with gzip.open(directory/'calls.jsonl.gz','rt',encoding='utf-8') as handle:
        for line in handle:
            call=json.loads(line)
            for key,answer in (call.get('response') or {}).get('answers',{}).items():
                if answer.get('type')!='choice':continue
                p=answer['probabilities'];distribution(list(p.values()));quality['choice_answers']+=1
                mass=float(sum(p.values()))
                if abs(mass-1)>1e-6:
                    quality['mass_defects']+=1;quality['mass_defects_'+call['site'].split('/')[0]]+=1
                    mass_errors.append(abs(mass-1));flags[call['site']].add(key)
    duplicate_diagnostics=[];sensitivity=[];fits=study.read(directory/'calibration.json')['fits']
    for panel in protocol['panels']:
        saved=study.read(directory/(panel+'-predictions.json'));p=np.asarray(saved['probabilities']);rows=saved['rows']
        for indices in groups:
            spread=np.max(p[indices],axis=0)-np.min(p[indices],axis=0)
            predictions=np.argmax(p[indices],axis=2)
            duplicate_diagnostics.append({'panel':panel,'identical_config_sha256':configs[indices[0]],
                'variant_indices':indices,'variant_roles':[{'selection':variants[i][0],'seed':variants[i][1]} for i in indices],
                'rows':len(rows),'rows_with_any_probability_difference':int(np.sum(np.any(spread>1e-12,axis=1))),
                'rows_with_label_disagreement':int(np.sum(np.any(predictions!=predictions[0],axis=0))),
                'max_probability_spread':float(np.max(spread)),
                'note':'Descriptive same-request, identical-prompt nuisance diagnostic; not additional independent test cases.'})
        keep=[i for i,row in enumerate(rows) if not flags['test/'+panel+'/'+row['id']]]
        if not keep:continue
        strict_rows=[rows[i] for i in keep]
        for i,(selection,seed,_) in enumerate(variants):
            for method in ('raw','temperature','temperature_bias'):
                pp=study.calibrated(p[i],fits[i],method)[keep]
                sensitivity.append({'task':task,'arm':arm,'panel':panel,'selection':selection,'seed':seed,'calibration':method,
                    'common_subset_rows':len(keep),'excluded_mass_defect_rows':len(rows)-len(keep),
                    'metrics':study.evaluate_metrics(pp,strict_rows,task),
                    'note':'Post-hoc data-quality sensitivity on the same rows for all variants; fitted calibrators unchanged. Not the primary estimand.'})
    return {'task':task,'arm':arm,'distinct_final_configurations':len(grouped),
        'accuracy_seeds_with_unchanged_baseline':[v[1] for i,v in enumerate(variants) if v[0]=='accuracy' and configs[i]==configs[0]],
        'nll_seeds_with_unchanged_baseline':[v[1] for i,v in enumerate(variants) if v[0]=='nll' and configs[i]==configs[0]],
        'mass_quality':dict(quality),'max_mass_defect':max(mass_errors,default=0.),
        'duplicate_prompt_diagnostics':duplicate_diagnostics},sensitivity


def charts(directory,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    protocol=study.read(directory/'protocol.json');task=protocol['task'];arm=protocol['arm']
    figure_dir=out/'figures';figure_dir.mkdir(parents=True,exist_ok=True)
    fig,ax=plt.subplots(figsize=(9,5))
    for seed in study.SEEDS:
        ledger=study.read(directory/f'search-{seed}.json');score=ledger[0]['validation']['accuracy'];values=[score]
        for entry in ledger[1:]:
            if entry['status']=='accepted':score=entry['validation']['accuracy']
            values.append(score)
        ax.plot(range(len(values)),values,marker='o',label=f'Seed {seed}')
    ax.set_xlabel('Candidate round');ax.set_ylabel('Best validation accuracy');ax.set_xticks(range(study.ROUNDS+1))
    ax.set_title(f'{task} / {arm} — validation only');ax.legend();ax.grid(axis='y',alpha=.2);fig.tight_layout()
    stem=f'{task}--{arm}--convergence';fig.savefig(figure_dir/(stem+'.png'),dpi=300);fig.savefig(figure_dir/(stem+'.svg'));plt.close(fig)
    saved=study.read(directory/'evaluation-predictions.json');fits=study.read(directory/'calibration.json')['fits']
    p=np.asarray(saved['probabilities']);y=np.asarray([study.LABELS[task].index(r['gold_label']) for r in saved['rows']])
    indices=[i for i,v in enumerate(saved['variants']) if v['selection']=='accuracy']
    fig,ax=plt.subplots(figsize=(8,6));ax.plot([0,1],[0,1],linestyle='--',label='Perfect calibration reference')
    for selection,method,label in [('baseline','raw','Baseline raw'),('baseline','temperature','Baseline temperature'),('accuracy','raw','DSPy raw (five searches)'),('accuracy','temperature','DSPy temperature (five searches)')]:
        chosen=[0] if selection=='baseline' else indices
        conf=[];correct=[]
        for i in chosen:
            pred=study.calibrated(p[i],fits[i],method)
            conf.extend(np.max(pred,axis=1));correct.extend(pred.argmax(axis=1)==y)
        conf=np.asarray(conf);correct=np.asarray(correct);bins=np.minimum(9,(conf*10).astype(int));x=[];v=[]
        for j in range(10):
            mask=bins==j
            if mask.any():x.append(float(conf[mask].mean()));v.append(float(correct[mask].mean()))
        ax.plot(x,v,marker='o',label=label)
    ax.set_xlabel('Mean predicted confidence');ax.set_ylabel('Observed accuracy');ax.set_xlim(0,1);ax.set_ylim(0,1)
    ax.set_title(f'{task} / {arm}\nDescriptive reliability; repeated searches are not new examples')
    ax.legend(fontsize=8);fig.tight_layout();stem=f'{task}--{arm}--reliability'
    fig.savefig(figure_dir/(stem+'.png'),dpi=300);fig.savefig(figure_dir/(stem+'.svg'));plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);results=[];sensitivity=[]
    paths=sorted(p.parent for p in a.input.rglob('execution.json') if (p.parent/'protocol.json').exists())
    if len(paths)!=8:raise ValueError('Expected all eight formulations')
    identities=set()
    for directory in paths:
        item,extra=diagnose(directory);results.append(item);sensitivity.extend(extra);charts(directory,a.output)
        identities.add((item['task'],item['arm']))
    if identities!={(t,arm) for t,arms in study.ARMS.items() for arm in arms}:raise ValueError('Duplicate/missing formulation')
    study.write_json(a.output/'quality-diagnostics.json',results);study.write_json(a.output/'strict-mass-subset-results.json',sensitivity)
    text=['# Data-quality and optimizer diagnostics','',
        'These descriptive analyses use completed captures only. They do not change prompts, selected seeds, calibration fits or primary results.',
        '', '| Task / formulation | Distinct final configurations | Accuracy seeds retaining baseline | Choice answers with mass defect | Largest mass defect |',
        '|---|---:|---|---:|---:|']
    for r in results:
        text.append(f"| {r['task']} / {r['arm']} | {r['distinct_final_configurations']} | {r['accuracy_seeds_with_unchanged_baseline']} | {r['mass_quality'].get('mass_defects',0)} | {r['max_mass_defect']:.4g} |")
    text+=['','Identical question payloads can yield slightly different probabilities within the same request. `quality-diagnostics.json` quantifies those differences and any label disagreements. A difference between two unchanged prompts must not be attributed to successful prompt optimization.',
           '', 'The primary analysis uses the bounded normalization rule fixed in amendment v2. `strict-mass-subset-results.json` is a sensitivity analysis excluding a row for every variant when any variant returned a non-unit-sum Choice vector on that row. Calibrators are not refit. This common subset avoids comparing different subsets across methods, but remains a post-hoc selected data-quality subset.',
           '', 'Convergence figures contain only validation scores. Reliability figures pool descriptive predictions across five searches but do not treat those repeated predictions as independent new examples or display inferential confidence intervals.','']
    (a.output/'REPORT.md').write_text('\n'.join(text),encoding='utf-8')
    study.write_json(a.output/'artifact-manifest.json',{'sha256':{p.relative_to(a.output).as_posix():study.sha(p) for p in sorted(a.output.rglob('*')) if p.is_file() and p.name!='artifact-manifest.json'}})

if __name__=='__main__':main()
