"""Aggregate completed runs only; no inference and no selection on test scores."""
import argparse
import csv
import hashlib
import json
import statistics
from pathlib import Path
from collections import defaultdict
from .data import SEEDS
from graph_synthesis.dspy_jev_optimizer.core import read_json, write_json, digest


def validate_artifact(directory, seed, item):
    manifest_path = directory/'artifact-inventory.json'
    if not manifest_path.is_file():
        return 'missing artifact inventory'
    manifest = read_json(manifest_path)
    hashes = manifest.get('sha256') if isinstance(manifest, dict) else None
    if not isinstance(manifest, dict) or manifest.get('schema_version') != 1 or not isinstance(hashes, dict):
        return 'malformed artifact inventory'
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*')
              if p.is_file() and p != manifest_path}
    if actual != set(hashes):
        return 'artifact file set differs from inventory'
    for relative, expected in hashes.items():
        sha = hashlib.sha256()
        with (directory/relative).open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                sha.update(chunk)
        if sha.hexdigest() != expected:
            return 'artifact hash mismatch: '+relative
    for name in ('protocol.json','status.json','metrics.json','usage.json',
                 'relation_support/frozen-targets.json','relation_support/calibration-freeze.json',
                 'entity_resolution/frozen-targets.json','entity_resolution/calibration-freeze.json'):
        if name not in hashes:
            return 'required artifact missing: '+name
    protocol = read_json(directory/'protocol.json')
    if (protocol.get('seed') != seed or item.get('protocol_sha256') != digest(protocol)
            or bool(protocol.get('baseline_only')) != (item['status'] == 'completed_baseline_only')
            or (item['status'] == 'completed' and protocol.get('iterations', 0) < 1)):
        return 'protocol and completion status disagree'
    if protocol.get('proposer_model') == 'openai/ollamacloud/deepseek-v4.1-flash':
        if protocol.get('iterations') != 8 or 'cost-budget.json' not in hashes:
            return 'authorized live protocol or budget artifact missing'
        budget = read_json(directory/'cost-budget.json')
        if (budget.get('limit_usd') != 8.0 or budget.get('estimated_usd', 9.0) > 8.0
                or budget.get('proposal_calls') != 32):
            return 'authorized live budget or proposal count invalid'
    metrics = read_json(directory/'metrics.json')
    if not isinstance(metrics, list) or not metrics:
        return 'missing metric records'
    for task in ('relation_support','entity_resolution'):
        arms = set(read_json(directory/task/'frozen-targets.json')['targets'])
        observed = {row['arm'] for row in metrics if row['task'] == task and row['panel'] == 'test'}
        if not arms or not arms.issubset(observed):
            return 'missing test measurements for '+task
        if item['status'] == 'completed' and not any(a.startswith('dspy_') for a in arms):
            return 'full run has no DSPy arms'
    return None


def aggregate(rows):
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
    return summary


def write_summary_csv(path, summary):
    if not summary:
        path.unlink(missing_ok=True)
        return
    with path.open('w',newline='',encoding='utf-8') as f:
        writer = csv.DictWriter(f,fieldnames=list(summary[0]))
        writer.writeheader();writer.writerows(summary)


def summarize(root):
    rows, baseline_rows, status = [], [], []
    for seed in SEEDS:
        directory = root/('seed-'+str(seed))
        try:
            item = read_json(directory/'status.json') if (directory/'status.json').exists() else {'status':'not_run'}
            if not isinstance(item, dict) or 'status' not in item:
                raise ValueError('malformed status')
        except (OSError, ValueError, TypeError):
            item = {'status':'invalid_artifact','artifact_error':'unreadable status'}
        if item['status'] in ('completed','completed_baseline_only'):
            try:
                error = validate_artifact(directory,seed,item)
            except (OSError, ValueError, KeyError, TypeError):
                error = 'unreadable run artifact'
            if error:
                item = {'status':'invalid_artifact','reported_status':item['status'],
                        'artifact_error':error}
        status.append({'seed':seed,**item})
        if item['status'] == 'completed':
            rows.extend(read_json(directory/'metrics.json'))
        elif item['status'] == 'completed_baseline_only':
            baseline_rows.extend(read_json(directory/'metrics.json'))
    write_json(root/'run-status.json',status)
    baseline_summary = aggregate(baseline_rows)
    write_json(root/'baseline-only-summary.json',baseline_summary)
    write_summary_csv(root/'baseline-only-summary.csv',baseline_summary)
    summary = aggregate(rows)
    write_json(root/'summary.json',summary)
    write_summary_csv(root/'summary.csv',summary)
    complete = sum(s['status']=='completed' for s in status)
    baseline_complete = sum(s['status']=='completed_baseline_only' for s in status)
    lines = ['# Repeated DSPy / Jev benchmark comparison','',
             f'Completed full DSPy runs: **{complete}/{len(SEEDS)}**.',
             f'Full five-seed matrix: **{"complete" if complete == len(SEEDS) else "incomplete"}**.',
             f'Completed baseline-only runs: **{baseline_complete}/{len(SEEDS)}**.','',
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
    if not complete:
        lines += ['','**No completed live DSPy comparison is available.**']
    if baseline_summary:
        lines += ['', '## Baseline-only results (separate partial run)', '',
                  'These measurements contain no DSPy search and are excluded from the primary comparison.', '',
                  '| Task | Arm | Calibration | Runs | Accuracy | Macro-F1 | Brier | Log loss | ECE |',
                  '|---|---|---|---:|---:|---:|---:|---:|---:|']
        for r in baseline_summary:
            if r['panel']=='test' and r['calibration'].endswith('_1.0'):
                lines.append('| '+ ' | '.join([r['task'],r['arm'],r['calibration'],str(r['runs'])]+[
                    f"{r[k+'_mean']:.6f}" for k in ('accuracy','macro_f1','brier','log_loss','ece')])+' |')
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
