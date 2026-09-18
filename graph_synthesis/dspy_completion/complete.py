"""Reconstruct complete v2 observations; distinguish unknown-label diagnostic fixtures.

This module makes no network calls. A failed CI status does not become a successful
capture unless every frozen search, calibration row and evaluation response exists.
"""
from __future__ import annotations
import argparse
from collections import Counter
from copy import copy
import gzip
import json
from pathlib import Path
import shutil
import numpy as np
from graph_synthesis.dspy_benchmark import study
from graph_synthesis.dspy_benchmark_v2.adapter import probabilities,distribution
from graph_synthesis.dspy_benchmark_analysis import report

_original_metrics=study.evaluate_metrics


def eligible_metrics(p,rows,task):
    labels=study.LABELS[task];unknown=[r for r in rows if r['gold_label'] not in labels]
    if unknown and (task!='entity_resolution' or any(r['gold_label']!='uncertain' for r in unknown)):
        raise ValueError('Unknown label is not an original ambiguous entity fixture')
    indices=[i for i,r in enumerate(rows) if r['gold_label'] in labels]
    if not indices:raise ValueError('No semantically eligible classification rows')
    result=_original_metrics(np.asarray(p)[indices],[rows[i] for i in indices],task)
    if unknown:
        result['input_rows']=len(rows);result['ambiguous_fixture_rows']=len(unknown)
    return result


def install():
    study.probabilities=probabilities
    study.evaluate_metrics=eligible_metrics
    report.evaluate_metrics=eligible_metrics


def expected_payload(task,arm,row,configs,demos):
    state=study.state(task,row)
    if arm=='fewshot_contract':
        state={'labeled_examples':[{'input':study.state(task,d),'answer':d['gold_label']} for d in demos],'input':state}
    return {'model':study.MODEL,'state':state,
            'questions':{f'v{i}__{key}':q for i,config in enumerate(configs) for key,q in config.items()}}


def complete(source,out):
    install()
    if out.exists():raise ValueError('Never overwrite original or completed evidence')
    protocol=study.read(source/'protocol.json');task,arm=protocol['task'],protocol['arm']
    if protocol.get('revision')!=2 or protocol['seeds']!=study.SEEDS or protocol['model']!=study.MODEL:raise ValueError('Wrong experiment')
    plan,parts,panels=study.prepare(task)
    for name,want in protocol['data_hashes'].items():
        if study.sha(study.ROOT/name)!=want:raise ValueError('Data hash changed')
    for name,rows in parts.items():
        if protocol['split_ids'][name]!=[r['id'] for r in rows]:raise ValueError('Split changed')
    freeze=study.read(source/'freeze.json')
    if study.digest(freeze['payload'])!=freeze['sha256'] or freeze['payload']['protocol_sha256']!=study.digest(protocol):raise ValueError('Frozen selection invalid')
    searches=freeze['payload']['searches']
    if [s['seed'] for s in searches]!=study.SEEDS:raise ValueError('Missing frozen searches')
    for search in searches:
        ledger=study.read(source/f"search-{search['seed']}.json")
        if len(ledger)!=4 or study.digest(ledger)!=search['ledger_sha256']:raise ValueError('Missing or changed search ledger')
    variants=[('baseline',0,protocol['baseline'])]+[(selection,s['seed'],s[selection+'_questions']) for s in searches for selection in ('accuracy','nll')]
    order=list(plan['question_specs'][task][arm]);configs=[{key:q[key] for key in order} for _,_,q in variants]
    journal={};attempts=tokens=0;defects=[];choice_answers=0
    with gzip.open(source/'calls.jsonl.gz','rt',encoding='utf-8') as handle:
        for line in handle:
            call=json.loads(line);attempts+=1
            if call['request_sha256']!=study.digest(call['payload']) or call['payload']['model']!=study.MODEL:raise ValueError('Invalid request identity')
            response=call.get('response')
            if response:
                if response['model']!=study.MODEL:raise ValueError('Response model drift')
                tokens+=int(response.get('usage',{}).get('input_tokens',0))
                for key,answer in response['answers'].items():
                    if answer['type']=='choice':
                        choice_answers+=1;p=list(answer['probabilities'].values());distribution(p)
                        if abs(sum(p)-1)>1e-6:defects.append({'site':call['site'],'question':key,'raw_mass':sum(p),'raw_probabilities':answer['probabilities']})
            if (call['site'].startswith('calibration/') or call['site'].startswith('test/')) and call['error'] is None:
                if call['site'] in journal:raise ValueError('Duplicate final response')
                journal[call['site']]=call
    used=set()
    def reconstruct(rows,phase):
        output=[]
        for row in rows:
            site=phase+'/'+row['id']
            if site not in journal:raise ValueError('Missing live observation: '+site)
            call=journal[site];payload=expected_payload(task,arm,row,configs,parts['demonstrations'])
            if study.digest(payload)!=call['request_sha256']:raise ValueError('Reconstructed request changed')
            if set(call['response']['answers'])!=set(payload['questions']):raise ValueError('Incomplete answer bank')
            used.add(site)
            output.append([probabilities({key:call['response']['answers'][f'v{i}__{key}'] for key in q},task,q) for i,q in enumerate(configs)])
        return np.asarray(output).transpose(1,0,2)
    cal=study.read(source/'calibration.json');pc=reconstruct(parts['calibration'],'calibration')
    report.close(pc.tolist(),cal['probabilities'],'calibration probabilities')
    y=[study.LABELS[task].index(r['gold_label']) for r in parts['calibration']]
    if cal['gold']!=y or cal['ids']!=[r['id'] for r in parts['calibration']]:raise ValueError('Calibration identity changed')
    for i,p in enumerate(pc):
        fitted=study.fit_calibration(p,y)
        for method in ('raw','temperature','temperature_bias'):
            if not np.allclose(study.calibrated(p,fitted,method),study.calibrated(p,cal['fits'][i],method),atol=2e-5,rtol=2e-5):raise ValueError('Calibrator cannot be reproduced')
    predictions={};results=[];ambiguity=[]
    for panel,rows in panels.items():
        p=reconstruct(rows,'test/'+panel)
        saved={'rows':[{'id':r['id'],'gold_label':r['gold_label'],'groups':sorted(study.units(task,r)),'family':r.get('family')} for r in rows],
               'variants':[{'selection':s,'seed':seed} for s,seed,_ in variants],'probabilities':p.tolist()}
        original=source/(panel+'-predictions.json')
        if original.exists():report.close(saved,study.read(original),'saved panel')
        predictions[panel]=saved
        unknown=[i for i,r in enumerate(rows) if r['gold_label'] not in study.LABELS[task]]
        for i,(selection,seed,cfg) in enumerate(variants):
            for method in ('raw','temperature','temperature_bias'):
                transformed=study.calibrated(p[i],cal['fits'][i],method)
                results.append({'task':task,'arm':arm,'panel':panel,'selection':selection,'seed':seed,'calibration':method,
                    'metrics':eligible_metrics(transformed,rows,task),'config_sha256':study.digest(cfg)})
                if unknown:
                    values=transformed[unknown];confidence=values.max(axis=1)
                    ambiguity.append({'task':task,'arm':arm,'panel':panel,'selection':selection,'seed':seed,'calibration':method,
                        'n_ambiguous':len(unknown),'ids':[rows[j]['id'] for j in unknown],
                        'mean_max_probability':float(confidence.mean()),'max_probability':float(confidence.max()),
                        'fraction_confidence_at_least_0_9':float(np.mean(confidence>=.9)),
                        'mean_entropy_nats':float(np.mean(-np.sum(values*np.log(np.clip(values,1e-15,1)),axis=1))),
                        'note':'Gold uncertain is outside the binary schema. No binary accuracy, NLL or Brier score is defined for these rows.'})
    if used!=set(journal):raise ValueError('Unexpected unaccounted final responses')
    shutil.copytree(source,out)
    if (out/'results.json').exists():shutil.copyfile(out/'results.json',out/'original-results-before-completion.json')
    for panel,value in predictions.items():study.write_json(out/(panel+'-predictions.json'),value)
    study.write_json(out/'results.json',results);study.write_json(out/'ambiguity-results.json',ambiguity)
    study.write_json(out/'probability-quality.json',{'choice_answers':choice_answers,'rounded_mass_defects':len(defects),'defects':defects,
        'note':'Bounded input normalization fixed before this capture, distinct from fitted calibration.'})
    study.write_json(out/'completion.json',{'source_files_sha256':{p.name:study.sha(p) for p in sorted(source.iterdir()) if p.is_file()},
        'source_workflow_run':35342763186,'completion_source_sha256':study.sha(__file__),'new_inference_calls':0,
        'verified_final_response_count':len(used),'fixture_rule':'Binary classification metrics exclude original uncertain labels; all 100 fixture observations retained, 12 ambiguity rows reported separately.'})
    study.write_json(out/'execution.json',{'status':'completed','revision':2,'live':True,'http_attempts':attempts,'reported_input_tokens':tokens,
        'estimated_jev_usd':tokens*.042/1_000_000,'price_basis':'$0.042/M input; estimate, not invoice',
        'dspy_searches':5,'proposals_planned':15,'completion':'All required actual v2 responses verified; reporting completed offline with zero extra inference.'})
    study.write_json(out/'artifact-manifest.json',{'sha256':{p.name:study.sha(p) for p in sorted(out.iterdir()) if p.is_file() and p.name!='artifact-manifest.json'}})
    return out


def analysis_view(capture):
    """The raw audit sees every fixture; classification statistics use eligible rows only."""
    view=copy(capture);view.panels=dict(capture.panels)
    if capture.task=='entity_resolution':
        saved=dict(view.panels['fixtures']);indices=[i for i,r in enumerate(saved['rows']) if r['gold_label'] in study.LABELS[capture.task]]
        if len(indices)!=88:raise ValueError('Unexpected eligible entity fixture count')
        saved['rows']=[saved['rows'][i] for i in indices]
        saved['probabilities']=np.asarray(saved['probabilities'])[:,indices].tolist();view.panels['fixtures']=saved
    return view


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();complete(a.input,a.output)

if __name__=='__main__':main()
