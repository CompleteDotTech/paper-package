"""Reconcile the explicitly inspected concurrent main snapshot on the research branch.

No checkout/reset of the full tree; only seven shared renderer/paper files are
resolved from main, then this extension is reinserted by its report generator.
Unknown conflicts abort. Frozen protocol, methods and benchmark endpoints stay.
"""
import subprocess
from pathlib import Path
from .report import ROOT, HERE

PIN = 'a21314d17c33c639b75522ecce120586ef8dab35'
SHARED = {'.github/workflows/jev-multicall.yml', 'graph_synthesis/render_current_paper.py',
          'CURRENT_RESULTS.md', 'manuscript/paper-current.md', 'manuscript/paper-current.html',
          'manuscript/paper-current.pdf', 'manuscript/paper-current.build.json'}
NOTE = '''**Concurrent integration disclosure.** While this frozen extension was executing, main advanced to `a21314d17c33c639b75522ecce120586ef8dab35` with the [structural refinement](../structural/RESULTS.md) and [source-structural](../source_structural/RESULTS.md) studies. Both are preserved unchanged. The source-structural study also implements certified bipartite optimization: H4 here is therefore a parallel implementation and additional frozen test suite, not a mechanism unique to the reconciled main branch. Its frontier-width lineage evaluator overlaps H3's goal but differs from the reusable decision-diagram state budget tested here. Source-setup review differs from H2's heterogeneous per-edge effort/noise model; source-revision invalidation differs from H5's connected-path summary maintenance. Repository-new claims are limited to the protocol's original pinned baseline, not the later integration snapshot. No thresholds, fixtures or numerical results were retuned after examining the concurrent studies. Reused semantic captures must not be pooled as independent observations.'''


def git(*args, check=True):
    return subprocess.run(['git', *args], cwd=ROOT, check=check, capture_output=True)


def main():
    if git('merge-base', '--is-ancestor', PIN, 'HEAD', check=False).returncode == 0:
        print('Pinned concurrent main snapshot already integrated; no mutation performed')
        return
    git('config', 'user.name', 'github-actions[bot]')
    git('config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
    outcome = git('merge', '--no-commit', '--no-ff', PIN, check=False)
    conflicts = set(git('diff', '--name-only', '--diff-filter=U').stdout.decode().splitlines())
    if conflicts-SHARED or (outcome.returncode and not conflicts):
        raise RuntimeError('Unexpected merge conflict or merge failure: '+repr(conflicts)+' '+outcome.stderr.decode())
    for name in sorted(SHARED):
        (ROOT/name).write_bytes(git('show', PIN+':'+name).stdout)
    path = ROOT/'.github/workflows/jev-multicall.yml'
    text = path.read_text(encoding='utf-8')
    anchor = '          python -B -m graph_synthesis.source_structural.report --update-paper\n'
    assert text.count(anchor) == 1
    text = text.replace(anchor, anchor+'          python -B -m graph_synthesis.frontier.report --update-paper\n')
    text = text.replace('graph_synthesis/structural graph_synthesis/source_structural\n',
                        'graph_synthesis/structural graph_synthesis/source_structural graph_synthesis/frontier\n')
    path.write_text(text, encoding='utf-8', newline='\n')
    path = ROOT/'graph_synthesis/render_current_paper.py'
    text = path.read_text(encoding='utf-8')
    assert text.count('|SOURCE_STRUCTURAL)') == 1
    path.write_text(text.replace('|SOURCE_STRUCTURAL)', '|SOURCE_STRUCTURAL|FRONTIER)'), encoding='utf-8', newline='\n')
    path = HERE/'report.py'
    text = path.read_text(encoding='utf-8')
    old = "    if text.count(ANCHOR)!=1:\n        raise ValueError('Exactly one preceding reliability-study anchor required')\n    return text.replace(ANCHOR,ANCHOR+'\\n\\n'+START+'\\n\\n'+body.strip()+'\\n\\n'+END,1)"
    new = "    anchor=next((x for x in ('<!-- SOURCE_STRUCTURAL_RESEARCH_END -->','<!-- STRUCTURAL_RESEARCH_END -->',ANCHOR) if x in text),ANCHOR)\n    if text.count(anchor)!=1:\n        raise ValueError('Exactly one preceding study anchor required')\n    return text.replace(anchor,anchor+'\\n\\n'+START+'\\n\\n'+body.strip()+'\\n\\n'+END,1)"
    assert text.count(old) == 1
    text = text.replace(old,new).replace('## 2. H1: Source-conditioned evidence probability', NOTE+'\n\n## 2. H1: Source-conditioned evidence probability',1)
    path.write_text(text,encoding='utf-8',newline='\n')
    path = HERE/'NOVELTY.md'
    path.write_text(path.read_text(encoding='utf-8')+'\n## Concurrent integration update\n\n'+NOTE+'\n',encoding='utf-8',newline='\n')
    path = HERE/'IMPLEMENTATION.md'
    path.write_text(path.read_text(encoding='utf-8')+'\nConcurrent main integration pinned `'+PIN+'`. Both intervening studies, their evidence and protocols are preserved. Shared manuscript and renderer conflicts are resolved additively; H4 overlap is explicitly disclosed in the novelty audit and paper. Benchmark code, frozen protocol, fixtures and target indicators remain unchanged. The expanded combined regression count is recorded by all-regressions.json after integration.\n',encoding='utf-8',newline='\n')
    git('add', *sorted(SHARED), 'graph_synthesis/frontier/report.py', 'graph_synthesis/frontier/NOVELTY.md', 'graph_synthesis/frontier/IMPLEMENTATION.md')
    remaining=git('diff','--name-only','--diff-filter=U').stdout.decode().strip()
    assert not remaining,remaining
    for directory in ('graph_synthesis/structural','graph_synthesis/source_structural'):
        assert not git('diff','--name-only',PIN,'--',directory).stdout.strip(),directory
    print('Reconciled pinned concurrent main; benchmark execution and PDF regeneration must finish before merge commit publication')


if __name__=='__main__':main()
