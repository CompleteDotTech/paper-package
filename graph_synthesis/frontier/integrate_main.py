"""Finalize the inspected additive merge; never alter workflows or research tests."""
import subprocess
from .report import ROOT, HERE

PIN = '114450ef08736c21c97c8725de700d8d2c6ca94d'
NOTES = [
'''**Further concurrent integration.** Main subsequently advanced through PR #24 to `6530321dd0060c9c7f13bb69d6f1c88346a8e1e2`. Its [assumption-aware study](../assumption_aware/RESULTS.md) is also preserved unchanged. Its dependence-robust probability envelopes address unknown joint dependence rather than H1's supplied latent-source conditional model. Its connected-tree ancestor-message updates overlap H5's objective, but H5 uses a balanced segment tree on a fixed path, with a different update mechanism and counted work metric. These results are parallel extensions of the same pinned baseline, not independent replications, combined semantic observations, or claims of unique worldwide invention. Frozen frontier hypotheses, implementations, fixture seeds and numerical results are unchanged; only additive reporting and combined regression coverage expand.''',
'''**Final integration snapshot.** Main also received PR #21, the [uncertainty and grounding study](../uncertainty/RESULTS.md), at `114450ef08736c21c97c8725de700d8d2c6ca94d`. That study and all three earlier concurrent extensions are preserved unchanged. Its dependence-agnostic bounds and query-loss-directed review further overlap the broad research questions here, but use different supplied-information assumptions and controlled objectives. This frontier study does not claim to be the unique first repository implementation on the reconciled main branch; its dated novelty comparison remains the frozen PR #17 baseline. All frozen numerical outcomes remain unchanged and overlapping captured observations are not pooled.''']


def main():
    subprocess.run(['git','merge-base','--is-ancestor',PIN,'HEAD'],cwd=ROOT,check=True)
    path=HERE/'report.py'; text=path.read_text(encoding='utf-8')
    alternatives=[
        "    anchor=next((x for x in ('<!-- SOURCE_STRUCTURAL_RESEARCH_END -->','<!-- STRUCTURAL_RESEARCH_END -->',ANCHOR) if x in text),ANCHOR)",
        "    anchors=re.findall(r'<!-- [A-Z_]+_RESEARCH_END -->',text)\n    anchor=anchors[-1] if anchors else ANCHOR",
        "    anchor=next((x for x in ('<!-- ASSUMPTION_AWARE_RESEARCH_END -->','<!-- SOURCE_STRUCTURAL_RESEARCH_END -->','<!-- STRUCTURAL_RESEARCH_END -->',ANCHOR) if x in text),ANCHOR)"]
    fixed="    anchor=next((x for x in ('<!-- UNCERTAINTY_RESEARCH_END -->','<!-- ASSUMPTION_AWARE_RESEARCH_END -->','<!-- SOURCE_STRUCTURAL_RESEARCH_END -->','<!-- STRUCTURAL_RESEARCH_END -->',ANCHOR) if x in text),ANCHOR)"
    for old in alternatives:
        if old in text:
            assert text.count(old)==1
            text=text.replace(old,fixed)
    assert fixed in text,'Unexpected paper anchor implementation'
    for note in NOTES:
        if note not in text:
            anchor='## 2. H1: Source-conditioned evidence probability'
            assert text.count(anchor)==1
            text=text.replace(anchor,note+'\n\n'+anchor,1)
    path.write_text(text,encoding='utf-8',newline='\n')
    path=HERE/'NOVELTY.md'; text=path.read_text(encoding='utf-8')
    for note in NOTES:
        if note not in text:
            text+='\n'+note+'\n'
    path.write_text(text,encoding='utf-8',newline='\n')
    path=HERE/'IMPLEMENTATION.md'; text=path.read_text(encoding='utf-8')
    records=[
        'Final integration preserves PRs #18, #19, #24 and #21 at `'+PIN+'`, including their requirements and all evidence. The full regression runner includes all their tests. The reporting anchor follows the latest supported refinement study, before the historical follow-up boundary. The renderer from current main is preserved unchanged because its generic marker-removal helper already handles the frontier section. Frozen benchmark implementations, protocol, fixture seeds and target indicators remain unchanged.',
        'Integration validation recorded 772 passing tests and one manuscript-regeneration failure in the first 773-test run. Choosing the last physical research marker incorrectly placed the new section after the historical follow-up, whose unchanged writer relocates itself immediately before the original-study boundary. The correction selects the latest refinement predecessor, preserving the historical follow-up position. The existing failing regression remains unchanged and must pass before publication. No research result or acceptance threshold changed.']
    for paragraph in records:
        if paragraph not in text:
            text+='\n'+paragraph+'\n'
    path.write_text(text,encoding='utf-8',newline='\n')
    for name in ('structural','source_structural','assumption_aware','uncertainty'):
        subprocess.run(['git','diff','--exit-code',PIN,'--','graph_synthesis/'+name],cwd=ROOT,check=True)
    print('Verified inspected main ancestry and four unchanged concurrent studies; frontier precedes the historical follow-up boundary')


if __name__=='__main__':main()
