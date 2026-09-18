"""Finalize an authorized additive main merge without changing CI permissions.

Only reporting integration is edited. Frozen benchmarks and other studies stay
unchanged. Workflow unions and the two-parent merge use the connected GitHub API.
"""
import subprocess
from .report import ROOT, HERE

PIN = '6530321dd0060c9c7f13bb69d6f1c88346a8e1e2'
NOTE = '''**Further concurrent integration.** Main subsequently advanced through PR #24 to `6530321dd0060c9c7f13bb69d6f1c88346a8e1e2`. Its [assumption-aware study](../assumption_aware/RESULTS.md) is also preserved unchanged. Its dependence-robust probability envelopes address unknown joint dependence rather than H1's supplied latent-source conditional model. Its connected-tree ancestor-message updates overlap H5's objective, but H5 uses a balanced segment tree on a fixed path, with a different update mechanism and counted work metric. These results are parallel extensions of the same pinned baseline, not independent replications, combined semantic observations, or claims of unique worldwide invention. Frozen frontier hypotheses, implementations, fixture seeds and numerical results are unchanged; only additive reporting and combined regression coverage expand.'''


def main():
    subprocess.run(['git','merge-base','--is-ancestor',PIN,'HEAD'],cwd=ROOT,check=True)
    path=HERE/'report.py'; text=path.read_text(encoding='utf-8')
    prior="    anchor=next((x for x in ('<!-- SOURCE_STRUCTURAL_RESEARCH_END -->','<!-- STRUCTURAL_RESEARCH_END -->',ANCHOR) if x in text),ANCHOR)"
    invalid="    anchors=re.findall(r'<!-- [A-Z_]+_RESEARCH_END -->',text)\n    anchor=anchors[-1] if anchors else ANCHOR"
    fixed="    anchor=next((x for x in ('<!-- ASSUMPTION_AWARE_RESEARCH_END -->','<!-- SOURCE_STRUCTURAL_RESEARCH_END -->','<!-- STRUCTURAL_RESEARCH_END -->',ANCHOR) if x in text),ANCHOR)"
    for old in (prior,invalid):
        if old in text:
            assert text.count(old)==1
            text=text.replace(old,fixed)
    assert fixed in text,'Unexpected paper anchor implementation'
    if NOTE not in text:
        anchor='## 2. H1: Source-conditioned evidence probability'
        assert text.count(anchor)==1
        text=text.replace(anchor,NOTE+'\n\n'+anchor,1)
    path.write_text(text,encoding='utf-8',newline='\n')
    path=HERE/'NOVELTY.md'; text=path.read_text(encoding='utf-8')
    if NOTE not in text:
        path.write_text(text+'\n## Further concurrent integration\n\n'+NOTE+'\n',encoding='utf-8',newline='\n')
    path=HERE/'IMPLEMENTATION.md'; text=path.read_text(encoding='utf-8')
    note='Further integration preserves PR #24 at `'+PIN+'`, including its requirements and all evidence. The full regression runner includes its tests. The reporting anchor follows the latest supported refinement study, before the historical follow-up boundary, so the complete paper retains all three concurrent studies. Latent-source versus dependence-envelope assumptions and path-segment-tree versus tree-message update mechanisms are explicitly distinguished. No benchmark endpoint or implementation is changed.'
    correction='Integration validation recorded 772 passing tests and one manuscript-regeneration failure in the first 773-test run. Choosing the last physical research marker incorrectly placed the new section after the historical follow-up, whose unchanged writer relocates itself immediately before the original-study boundary. The correction selects the latest refinement predecessor (assumption-aware, source-structural, structural, then reliability), preserving the historical follow-up position. The existing failing regression remains unchanged and must pass before publication. No research result or acceptance threshold changed.'
    for paragraph in (note,correction):
        if paragraph not in text:
            text+='\n'+paragraph+'\n'
    path.write_text(text,encoding='utf-8',newline='\n')
    for name in ('structural','source_structural','assumption_aware'):
        subprocess.run(['git','diff','--exit-code',PIN,'--','graph_synthesis/'+name],cwd=ROOT,check=True)
    print('Verified current main ancestry and three unchanged concurrent studies; frontier precedes the historical follow-up boundary')


if __name__=='__main__':main()
