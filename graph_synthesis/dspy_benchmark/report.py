"""Aggregate completed runs only; no inference and no selection on test scores."""
import argparse
import csv
import gzip
import hashlib
import json
import math
import statistics
from pathlib import Path
from collections import defaultdict
from .data import SEEDS, inventory
from graph_synthesis.dspy_jev_optimizer.core import read_json, write_json, digest

EXPECTED_ARMS = {
    'relation_support': {'dspy_accuracy','dspy_composite','without_dspy_baseline_choice',
                         'without_dspy_conditional_nouls','without_dspy_evidence_contract',
                         'without_dspy_fewshot_contract'},
    'entity_resolution': {'dspy_accuracy','dspy_composite','without_dspy_baseline_noul',
                          'without_dspy_fewshot_contract','without_dspy_identity_contract',
                          'without_dspy_identity_noul'},
}
EXPECTED_PANELS = {
    'relation_support': {'test','fixtures','semantic_challenge','multicall_development','multicall_test'},
    'entity_resolution': {'test','fixtures'},
}
CALIBRATIONS = {'raw_1.0'} | {method+'_'+fraction for method in
    ('temperature','bias_temperature') for fraction in ('0.25','0.5','1.0')}


def audit_live_receipts(directory, budget, status, registered):
    """Recompute usage and retry counts from the hashed raw event journals."""
    requests = tokens = invalid_retries = timeout_retries = timeouts = 0
    for task in EXPECTED_ARMS:
        for stage in [f'search-{objective}' for objective in ('accuracy','composite')] + list(EXPECTED_ARMS[task]):
            with (directory/task/stage/'calls.jsonl').open(encoding='utf-8') as stream:
                for line in stream:
                    event = json.loads(line)
                    kind = event.get('event')
                    if kind == 'request': requests += 1
                    elif kind in ('response','invalid_answer'):
                        value = event['response']['usage']['input_tokens']
                        if type(value) is not int or value < 0:
                            return 'raw Jev usage is invalid'
                        tokens += value
                    elif kind == 'retry_request': invalid_retries += 1
                    elif kind == 'retry_timeout_request': timeout_retries += 1
                    elif kind == 'jev_timeout': timeouts += 1
        for arm in EXPECTED_ARMS[task]:
            for panel in EXPECTED_PANELS[task]:
                with gzip.open(directory/task/arm/(panel+'-predictions.json.gz'),'rt',encoding='utf-8') as stream:
                    predictions = json.load(stream)
                if not isinstance(predictions,list) or len(predictions) != registered[task]['panels'][panel]['n']:
                    return 'prediction count differs from registered panel'
    proposal_tokens_in = proposal_tokens_out = parse_failures = 0
    for task in EXPECTED_ARMS:
        for objective in ('accuracy','composite'):
            with (directory/task/f'proposals-{objective}.jsonl').open(encoding='utf-8') as stream:
                for line in stream:
                    usage = json.loads(line).get('usage',{})
                    proposal_tokens_in += usage.get('prompt_tokens',0)
                    proposal_tokens_out += usage.get('completion_tokens',0)
        path=directory/task/'proposal-parse-failures.jsonl'
        if path.exists():
            parse_failures += len(path.read_text(encoding='utf-8').splitlines())
    if (requests < 1 or requests != status.get('live_logical_calls') or tokens != budget.get('jev_input_tokens')
            or invalid_retries != budget.get('invalid_answer_retries')
            or timeout_retries != budget.get('jev_timeout_retries')
            or timeouts != budget.get('jev_timeout_failures')
            or timeouts != budget.get('jev_unknown_usage_calls')
            or parse_failures != budget.get('proposal_parse_retries')
            or proposal_tokens_in != budget.get('proposal_input_tokens_reported')
            or proposal_tokens_out != budget.get('proposal_output_tokens_reported')):
        return 'budget receipt disagrees with raw traces'
    proposal_reserve = (32+parse_failures)*.07
    estimated = (tokens*.042/1_000_000 + timeouts*.05
                 + max(proposal_reserve,(proposal_tokens_in*.30+proposal_tokens_out*1.20)/1_000_000))
    if (not math.isclose(budget.get('proposal_reserve_usd',-1),proposal_reserve,abs_tol=1e-9)
            or not math.isclose(budget.get('estimated_usd',-1),estimated,abs_tol=1e-8)):
        return 'budget arithmetic disagrees with raw traces'
    return None


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
    if item['status'] == 'completed':
        if (protocol.get('model') != 'jev-1.13.0'
                or protocol.get('proposer_model') != 'openai/ollamacloud/deepseek-v4.1-flash'
                or protocol.get('iterations') != 8 or 'cost-budget.json' not in hashes):
            return 'authorized live protocol or budget artifact missing'
        budget = read_json(directory/'cost-budget.json')
        if (budget.get('limit_usd') != 8.0 or budget.get('estimated_usd', 9.0) > 8.0
                or budget.get('proposal_calls') != 32 or budget.get('jev_inflight_calls') != 0
                or not 0 <= budget.get('invalid_answer_retries', 21) <= 20
                or not 0 <= budget.get('proposal_parse_retries', 21) <= 20
                or not 0 <= budget.get('jev_timeout_retries', 21) <= 20
                or budget.get('proposal_attempts') != 32+budget.get('proposal_parse_retries',0)):
            return 'authorized live budget or proposal count invalid'
        if (protocol.get('inventory') != inventory()
                or not isinstance(protocol.get('source_sha256'),dict)
                or not {'graph_synthesis/dspy_benchmark/run.py',
                        'graph_synthesis/dspy_benchmark/data.py',
                        'graph_synthesis/dspy_benchmark/report.py',
                        'graph_synthesis/dspy_jev_optimizer/core.py',
                        'graph_synthesis/dspy_jev_optimizer/providers.py',
                        'graph_synthesis/dspy_benchmark/requirements.txt'} <= set(protocol['source_sha256'])
                or not {'typesafe-sdk','dspy','litellm','numpy','scipy'} <=
                       set(protocol.get('dependency_versions',{}))):
            return 'registered data or execution provenance missing'
    metrics = read_json(directory/'metrics.json')
    if not isinstance(metrics, list) or not metrics:
        return 'missing metric records'
    if item['status'] == 'completed':
        expected = {(task,arm,panel,calibration)
                    for task in EXPECTED_ARMS for arm in EXPECTED_ARMS[task]
                    for panel in EXPECTED_PANELS[task] for calibration in CALIBRATIONS}
        observed = [(row.get('task'),row.get('arm'),row.get('panel'),row.get('calibration'))
                    for row in metrics]
        if len(observed) != 294 or len(set(observed)) != 294 or set(observed) != expected:
            return 'incomplete or duplicate registered metric matrix'
        registered = protocol['inventory']
        for row in metrics:
            panel = registered[row['task']]['panels'][row['panel']]
            if (row.get('n') != panel['scorable']
                    or row.get('unscorable_count') != panel['n']-panel['scorable']):
                return 'metric denominator differs from registered panel'
        required_traces = set()
        for task in EXPECTED_ARMS:
            for objective in ('accuracy','composite'):
                required_traces.update({f'{task}/proposals-{objective}.jsonl',
                                        f'{task}/search-{objective}/calls.jsonl',
                                        f'{task}/search-{objective}/ledger.json',
                                        f'{task}/search-{objective}/freeze.json'})
            for arm in EXPECTED_ARMS[task]:
                prefix=f'{task}/{arm}/'
                required_traces.update({prefix+'calls.jsonl',prefix+'calibration.json',
                                        prefix+'calibration-predictions.json.gz'})
                required_traces.update(prefix+panel+'-predictions.json.gz'
                                       for panel in EXPECTED_PANELS[task])
        if not required_traces <= set(hashes):
            return 'required raw trace or prediction missing'
        for task in EXPECTED_ARMS:
            for objective in ('accuracy','composite'):
                path=directory/task/f'proposals-{objective}.jsonl'
                proposals=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
                if len(proposals) != 8 or [row.get('iteration') for row in proposals] != list(range(1,9)):
                    return 'proposal trace differs from eight accepted iterations'
        error = audit_live_receipts(directory,budget,item,registered)
        if error:
            return error
    for task in ('relation_support','entity_resolution'):
        arms = set(read_json(directory/task/'frozen-targets.json')['targets'])
        if item['status'] == 'completed' and arms != EXPECTED_ARMS[task]:
            return 'frozen arm roster differs from registered comparison'
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
    full_protocols = []
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
            full_protocols.append(digest({key:value for key,value in
                                          read_json(directory/'protocol.json').items() if key != 'seed'}))
        elif item['status'] == 'completed_baseline_only':
            baseline_rows.extend(read_json(directory/'metrics.json'))
    if len(set(full_protocols)) > 1:
        rows = []
        status = [{'seed':s['seed'],'status':'invalid_artifact',
                   'reported_status':'completed','artifact_error':'mixed protocol cohort'}
                  if s['status']=='completed' else s for s in status]
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
