"""Aggregate completed runs only; no inference and no selection on test scores."""
import argparse
import csv
import json
import statistics
from pathlib import Path
from collections import defaultdict
from .data import SEEDS
from graph_synthesis.dspy_jev_optimizer.core import read_json, write_json


def summarize(root):
    rows, status = [], []
    for seed in SEEDS:
        directory = root/('seed-'+str(seed))
        item = read_json(directory/'status.json') if (directory/'status.json').exists() else {'status':'not_run'}
        status.append({'seed':seed,**item})
        if item['status'] in ('completed','completed_baseline_only'):
            rows.extend(read_json(directory/'metrics.json'))
    write_json(root/'run-status.json',status)
    groups = defaultdict(list)
    for row in rows:
        groups[(row['task'],row['panel'],row['arm'],row['calibration'])].append(row)
    summary = []
    for key,values in sorted(groups.items()):
        record = dict(zip(('task','panel','arm','calibration'),key))
        record['runs'] = len(values)
        record['n_per_run'] = values[0]['n']
        for metric in ('accuracy','macro_f1','mcc','brier','log_loss','ece'):
            numbers = [r[metric] for r in values]
            record[metric+'_mean'] = statistics.mean(numbers)
            record[metric+'_sd'] = statistics.stdev(numbers) if len(numbers)>1 else None
        summary.append(record)
    write_json(root/'summary.json',summary)
    if summary:
        with (root/'summary.csv').open('w',newline='',encoding='utf-8') as f:
            writer = csv.DictWriter(f,fieldnames=list(summary[0]));writer.writeheader();writer.writerows(summary)
    complete = sum(s['status']=='completed' for s in status)
    lines = ['# Repeated DSPy / Jev benchmark comparison','',
             f'Completed full DSPy runs: **{complete}/{len(SEEDS)}**.','',
             'Previously published observations are not relabeled as fresh runs. '
             'A missing or failed run is not an accuracy score. Five evaluations on the same test set '
             'are repeated model/search runs, not five independent datasets.','',
             '| Seed | Status |','|---|---|']
    lines += [f"| {s['seed']} | {s['status']} |" for s in status]
    lines += ['', '## Primary test results', '',
              '| Task | Arm | Calibration | Runs | Accuracy | Macro-F1 | Brier | Log loss | ECE |',
              '|---|---|---|---:|---:|---:|---:|---:|---:|']
    for r in summary:
        if r['panel']=='test' and r['calibration'].endswith('_1.0'):
            lines.append('| '+ ' | '.join([r['task'],r['arm'],r['calibration'],str(r['runs'])]+[
                f"{r[k+'_mean']:.6f}" for k in ('accuracy','macro_f1','brier','log_loss','ece')])+' |')
    if not summary:
        lines += ['','**No completed live comparison is available.**']
    lines += ['','## Interpretation boundaries','',
        'Accuracy/composite search and post-hoc calibration are separate interventions. '
        'Temperature scaling leaves predicted labels unchanged; bias/temperature may change labels. '
        'Calibration uses only the original calibration split. Published synthetic fixtures and '
        'the semantic challenge are exploratory transfer panels, not new independent gold labels. '
        'Twelve uncertain entity fixtures have no label in the binary schema and are excluded from '
        'accuracy denominators, but their predictions remain in the raw records.','',
        'The implementation is the repository\'s custom DSPy proposal loop, not GEPA or MIPROv2. '
        'No test-score winner is selected across seeds. Broad superiority or a global accuracy optimum '
        'cannot be inferred from this finite search.']
    (root/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True)
    summarize(p.parse_args().directory)
