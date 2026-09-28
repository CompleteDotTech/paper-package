"""Exploratory recalibration of SAVED responses; never presented as a live DSPy run."""
import argparse
import hashlib
from pathlib import Path
from .data import ROOT, load_task
from .calibration import fit, apply, evaluation
from graph_synthesis.dspy_jev_optimizer.core import parse_json, write_json

SOURCE = 'experiments/jev-rerun-20260918/predictions.jsonl'

def execute(output):
    output.mkdir(parents=True,exist_ok=False)
    source=ROOT/SOURCE
    rows=[parse_json(line) for line in source.read_text(encoding='utf-8').splitlines() if line]
    result=[]
    exclusions=[]
    for task in ('relation_support','entity_resolution'):
        cfg,splits,_,_=load_task(task)
        groups={r.id:r.group_id for name in ('calibration','test') for r in splits[name]}
        arms=sorted({r['arm'] for r in rows if r['task']==task and r['split']=='calibration'})
        for arm in arms:
            def get(split):
                selected=[r for r in rows if r['task']==task and r['arm']==arm and r['split']==split and r['repeat']==0]
                bad=[r for r in selected if r.get('error')]
                exclusions.extend({'task':task,'arm':arm,'split':split,'id':r['id'],'error':r['error']} for r in bad)
                selected=[r for r in selected if not r.get('error')]
                return [{'id':r['id'],'group_id':groups[r['id']],'gold':r['gold_label'],
                         'choice':max(cfg.criteria,key=lambda k:r['distribution'][k]),'probabilities':r['distribution']} for r in selected]
            calibration,test=get('calibration'),get('evaluation')
            if not calibration or not test:
                raise ValueError('No valid archived responses')
            for method in ('raw','temperature','bias_temperature'):
                fitted=fit(calibration,list(cfg.criteria),method)
                write_json(output/(task+'-'+arm+'-'+method+'-fit.json'),fitted)
                result.append({'task':task,'arm':arm,'calibration':method,'temperature':fitted['temperature'],'planned_test_n':len(splits['test']),'response_coverage':len(test)/len(splits['test']),
                               **evaluation(apply(test,fitted),cfg.criteria)})
    report={'evidence':'exploratory_saved_response_reanalysis','fresh_model_calls':0,'dspy_runs':0,
            'source':SOURCE,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'method':'Fit only archived calibration labels; score historically examined archived evaluation labels. No method selected on test scores.',
            'excluded_invalid_responses':exclusions,'results':result}
    write_json(output/'results.json',report)
    text=['# Archived-output calibration check','',
          '**Zero fresh model calls. Zero DSPy runs. This is not the requested live comparison.** Invalid archived responses are excluded from probability metrics and listed in results.json; accuracy is conditional on a valid response, not end-to-end accuracy.','',
          'Calibrators were refit using only the archived calibration split. All three fixed methods are shown; none was selected using test performance. The archived evaluation split was historically examined, so these are exploratory results.', '',
          '| Task | Historical arm | Calibration | n | Accuracy | Macro-F1 | Brier | Log loss | ECE |',
          '|---|---|---|---:|---:|---:|---:|---:|---:|']
    for r in result:
        text.append('| '+' | '.join([r['task'],r['arm'],r['calibration'],str(r['n'])]+[f"{r[m]:.6f}" for m in ('accuracy','macro_f1','brier','log_loss','ece')])+' |')
    text.extend(['','Temperature scaling preserves decisions; its accuracy differences must be zero. Bias/temperature can change decisions. A probability-quality improvement is not necessarily an accuracy improvement.','',f"Source SHA-256: `{report['source_sha256']}`",''])
    (output/'RESULTS.md').write_text('\n'.join(text),encoding='utf-8')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    execute(parser.parse_args().output)
