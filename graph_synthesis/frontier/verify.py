"""Verify extension hashes, protocol, prior evidence, and complete-paper binding."""
import hashlib
import json
from pathlib import Path
from .report import HERE, ROOT, START, END


def main():
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    manifest=json.loads((HERE/'artifact-manifest.json').read_text(encoding='utf-8'))
    for path,want in manifest['sha256'].items():
        assert sha(ROOT/path)==want,path
    results=json.loads((HERE/'results.json').read_text(encoding='utf-8'))
    assert sha(HERE/'PROTOCOL.md')=='7a9a060f65ba35032b0df2186c1725da7c1c5ac96ddee807ca9e1587e6c0c725'
    for family in ('source_hashes','code_hashes'):
        for path,want in results[family].items():assert sha(ROOT/path)==want,path
    assert results['fresh_service_calls']==0
    assert results['input_audit']['group_disjoint'] and results['input_audit']['raw_response_validation']
    build=json.loads((ROOT/'manuscript/paper-current.build.json').read_text(encoding='utf-8'))
    assert sha(ROOT/'manuscript/paper-current.md')==build['source_sha256']
    assert sha(ROOT/'graph_synthesis/render_current_paper.py')==build['renderer_sha256']
    assert sha(ROOT/'manuscript/paper-current.pdf')==build['pdf_sha256']
    for path in ('CURRENT_RESULTS.md','manuscript/paper-current.md'):
        text=(ROOT/path).read_text(encoding='utf-8')
        assert text.count(START)==text.count(END)==1,path
    assert START not in (ROOT/'manuscript/paper-current.html').read_text(encoding='utf-8')
    print(json.dumps({'status':'passed','extension_hashed_files':len(manifest['sha256']),'fresh_service_calls':0,'paper_binding':'verified'}))


if __name__=='__main__':main()
