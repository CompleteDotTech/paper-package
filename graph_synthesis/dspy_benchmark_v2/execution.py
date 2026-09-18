"""Run amendment v2; original failed attempts are not pooled as successful seeds."""
from __future__ import annotations
import argparse
import gzip
from pathlib import Path
import numpy as np
from graph_synthesis.dspy_benchmark import study
from graph_synthesis.dspy_benchmark.execution import install_audit_boundary
from graph_synthesis.dspy_benchmark.audit import json_safe
from .adapter import probabilities,proposer,distribution


def install():
    install_audit_boundary()
    study.probabilities=probabilities


def run(task,arm,output):
    install()
    if arm not in study.ARMS[task]:raise ValueError('Unknown formulation')
    plan,parts,panels=study.prepare(task);baseline=plan['question_specs'][task][arm]
    output.mkdir(parents=True,exist_ok=False)
    def factory(seed):
        def trace(iteration,records):
            path=output/f'proposal-traces-{seed}.jsonl'
            with path.open('a',encoding='utf-8') as f:
                f.write(study.canonical(json_safe({'iteration':iteration,'questions':records}))+'\n')
        return proposer(seed,trace)
    study.proposer=factory
    protocol={'revision':2,'task':task,'arm':arm,'model':study.MODEL,'seeds':study.SEEDS,'rounds':study.ROUNDS,
        'source_sha256':study.sha(Path(study.__file__)),
        'amendment_sha256':study.sha(study.ROOT/'experiments/dspy-calibration-20260918/AMENDMENT_V2.md'),
        'adapter_sha256':study.sha(Path(__file__).with_name('adapter.py')),'runner_sha256':study.sha(Path(__file__)),
        'data_hashes':{p:study.sha(study.ROOT/p) for p in [study.ORIGINAL,study.EXTRA,study.CHALLENGE]},
        'split_ids':{s:[r['id'] for r in rows] for s,rows in parts.items()},
        'panels':{s:len(rows) for s,rows in panels.items()},'baseline':baseline,
        'proposer':'Qwen2.5-1.5B-Instruct-Q4_K_M / llama.cpp b10964 / DSPy 3.3.1 / flat fixed fields',
        'probability_interpretation':'Normalize only unit-sum tolerance 1e-6 or two-decimal vectors within K*0.005 rounding bound; retain/flag raw defects.',
        'causal_scope':'Exploratory published-data re-evaluation; no new unseen-data claim.'}
    study.write_json(output/'protocol.json',protocol)
    live=study.Live(output)
    searches=[study.search(task,arm,baseline,parts,live,output,seed) for seed in study.SEEDS]
    freeze={'protocol_sha256':study.digest(protocol),'searches':searches}
    study.write_json(output/'freeze.json',{'payload':freeze,'sha256':study.digest(freeze)})
    variants=[('baseline',0,baseline)]+[(objective,s['seed'],s[objective+'_questions']) for s in searches for objective in ['accuracy','nll']]
    configs=[v[2] for v in variants]
    cal=live.evaluate(task,arm,parts['calibration'],configs,parts['demonstrations'],'calibration')
    y=[study.LABELS[task].index(r['gold_label']) for r in parts['calibration']]
    fits=[study.fit_calibration(p,y) for p in cal]
    study.write_json(output/'calibration.json',{'ids':[r['id'] for r in parts['calibration']],'gold':y,'probabilities':cal.tolist(),'fits':fits})
    results=[]
    for panel,rows in panels.items():
        probs=live.evaluate(task,arm,rows,configs,parts['demonstrations'],'test/'+panel)
        study.write_json(output/(panel+'-predictions.json'),{'rows':[{'id':r['id'],'gold_label':r['gold_label'],'groups':sorted(study.units(task,r)),'family':r.get('family')} for r in rows],
            'variants':[{'selection':v[0],'seed':v[1]} for v in variants],'probabilities':probs.tolist()})
        for i,(selection,seed,cfg) in enumerate(variants):
            for method in ('raw','temperature','temperature_bias'):
                p=study.calibrated(probs[i],fits[i],method)
                results.append({'task':task,'arm':arm,'panel':panel,'selection':selection,'seed':seed,'calibration':method,
                    'metrics':study.evaluate_metrics(p,rows,task),'config_sha256':study.digest(cfg)})
        study.write_json(output/'results.json',results)
        print(study.canonical({'task':task,'arm':arm,'completed_panel':panel,'n':len(rows),'http_attempts':live.calls}),flush=True)
    defects=[];answers=0
    import json
    with gzip.open(output/'calls.jsonl.gz','rt',encoding='utf-8') as handle:
        for line in handle:
            call=json.loads(line)
            for key,answer in (call.get('response') or {}).get('answers',{}).items():
                if answer['type']!='choice':continue
                answers+=1;p=list(answer['probabilities'].values());distribution(p)
                if abs(sum(p)-1)>1e-6:defects.append({'site':call['site'],'question':key,'raw_mass':sum(p),'raw_probabilities':answer['probabilities']})
    study.write_json(output/'probability-quality.json',{'choice_answers':answers,'rounded_mass_defects':len(defects),'defects':defects,
        'note':'Mass normalization is an explicit input interpretation, not fitted statistical calibration or DSPy improvement.'})
    study.write_json(output/'execution.json',{'status':'completed','revision':2,'live':True,'http_attempts':live.calls,
        'reported_input_tokens':live.tokens,'estimated_jev_usd':live.tokens*.042/1_000_000,
        'price_basis':'Input $0.042/M; estimate, not invoice','dspy_searches':len(study.SEEDS),'proposals_planned':len(study.SEEDS)*study.ROUNDS})
    study.write_json(output/'artifact-manifest.json',{'sha256':{p.name:study.sha(p) for p in sorted(output.iterdir()) if p.is_file() and p.name!='artifact-manifest.json'}})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task',choices=list(study.ARMS),required=True);parser.add_argument('--arm',required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();run(args.task,args.arm,args.output)

if __name__=='__main__':main()
