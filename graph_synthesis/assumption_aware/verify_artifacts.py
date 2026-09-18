"""Check source/evidence/artifact binding and retention of first observed outcomes."""
import json
import math
from pathlib import Path
from .run import HERE, ROOT, sha


def verify():
    manifest=json.loads((HERE/'artifact-manifest.json').read_text(encoding='utf-8'))
    for path,want in manifest['sha256'].items():
        target=(ROOT/path).resolve()
        if not target.is_relative_to(HERE):raise ValueError('Manifest path escapes extension')
        if sha(target)!=want:raise ValueError('Artifact hash mismatch: '+path)
    r=json.loads((HERE/'results.json').read_text(encoding='utf-8'))
    for field in ('implementation_sha256','source_hashes'):
        for path,want in r[field].items():
            if sha(ROOT/path)!=want:raise ValueError('Research input/source mismatch: '+path)
    if r['protocol_sha256']!=sha(HERE/'PROTOCOL.md'):raise ValueError('Protocol changed')
    if r['fresh_service_calls']!=0:raise ValueError('Unexpected service calls')
    first=json.loads((HERE/'FIRST_OBSERVATION.json').read_text(encoding='utf-8'))
    if first['target_outcomes']!={f'H{i}':r[f'H{i}']['primary_target_met'] for i in range(1,6)}:
        raise ValueError('First target outcomes changed without an amendment')
    comparisons={'H1_primary_width_reduction':r['H1']['relative_width_reduction'],
                 'H3_exposure_before':r['H3']['baseline_primary']['weighted_exposure'],
                 'H3_exposure_after':r['H3']['proposed_primary']['weighted_exposure'],
                 'H4_balanced_dp_saving':r['H4']['balanced']['dp_saving'],
                 'H5_sparse_dependency_saving':r['H5']['local']['saving']}
    for key,value in comparisons.items():
        if not math.isclose(first[key],value,rel_tol=1e-10,abs_tol=1e-10):raise ValueError('First primary result changed: '+key)
    build=json.loads((ROOT/'manuscript/paper-current.build.json').read_text(encoding='utf-8'))
    for field,path in [('source_sha256','manuscript/paper-current.md'),('renderer_sha256','graph_synthesis/render_current_paper.py'),('pdf_sha256','manuscript/paper-current.pdf')]:
        if sha(ROOT/path)!=build[field]:raise ValueError('Complete paper hash mismatch: '+path)
    print('Verified extension artifacts, frozen protocol, first outcomes, captured inputs and complete paper')


if __name__=='__main__':verify()
