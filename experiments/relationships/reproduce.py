"""Reproduce the relationship experiment and verify committed reference evidence."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True,
                        help='New output directory outside the repository')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    if output == root or root in output.parents:
        parser.error('Output must be outside the repository to preserve evidence')
    if output.exists() and any(output.iterdir()):
        parser.error('Output must be new or empty; refusing to overwrite a run')
    reference = Path(__file__).resolve().parent / 'reference'
    expected = json.loads((reference / 'REFERENCE.json').read_text(encoding='utf-8'))
    compressed = (reference / 'results.json.gz').read_bytes()
    if hashlib.sha256(compressed).hexdigest() != expected['results_gzip_sha256']:
        raise ValueError('Committed results reference integrity failure')
    subprocess.run([sys.executable, '-B', '-m', 'graph_synthesis.edge_experiment',
                    '--repository', str(root), '--output', str(output)], cwd=root, check=True)
    sys.path.insert(0, str(root))
    from graph_synthesis.edge_experiment import compare_reference
    from graph_synthesis.edge_fusion import model_identity
    actual_results = json.loads((output / 'results.json').read_text(encoding='utf-8'))
    compare_reference(actual_results, json.loads(gzip.decompress(compressed)))
    selection = json.loads((output / 'selection.json').read_text(encoding='utf-8'))
    model_reference = json.loads((reference / 'model.json').read_text(encoding='utf-8'))
    compare_reference(selection['model'], model_reference['model'])
    summaries = [{k: v for k, v in candidate.items() if k != 'oof'}
                 for candidate in selection['candidates']]
    compare_reference(summaries, model_reference['candidate_summary'])
    if model_identity(selection['model']) != expected['fitted_model_hash']:
        raise ValueError('Fitted transformation changed')
    if selection['selected_regularization'] != expected['selected_regularization']:
        raise ValueError('Calibration selection changed')
    journal = gzip.decompress((output / 'decisions.csv.gz').read_bytes())
    if hashlib.sha256(journal).hexdigest() != expected['decision_journal_decompressed_sha256']:
        raise ValueError('Per-example decision journal changed')
    report = {'passed': True, 'fitted_model_hash': selection['model_hash'],
              'decision_journal_sha256': hashlib.sha256(journal).hexdigest(),
              'result_comparison': 'exact structure/counts/labels/hashes; floats atol=rtol=1e-8',
              'full_journals': ['selection.json', 'expanded-decisions.jsonl', 'decisions.csv.gz'],
              'fresh_http_calls': actual_results['fresh_http_calls']}
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('Reference verification passed; exact fitted-transform and per-example decision hashes.')


if __name__ == '__main__':
    main()
