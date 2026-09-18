# Current Jev research results — September 18, 2026

<!-- ADAPTIVE_RESEARCH_START -->

## Five adaptive improvements after multicall verification

[Executed report](graph_synthesis/adaptive/RESULTS.md), [frozen protocol](graph_synthesis/adaptive/PROTOCOL.md), [five figures](graph_synthesis/adaptive/figures/) and [full updated paper](manuscript/paper-current.pdf). No fresh Jev calls. Compact disagreement routing saves 34.38% of recorded tokens but misses its frozen 40% target; invalid-check fallback removes operational failures but increases wrong edges; redundancy-capped voting fails its matched-volume target. Group-aware review meets its ideal-review target, and joint conflict optimization meets its finite-oracle target. Those controlled results are not independent semantic-accuracy evidence. No production policy changes.

<!-- ADAPTIVE_RESEARCH_END -->

<!-- RISK_CONTROL_RESEARCH_START -->

## Five risk-controlled improvements after PR #15

[Executed report](graph_synthesis/risk_control/RESULTS.md), [frozen protocol](graph_synthesis/risk_control/PROTOCOL.md), [five figures](graph_synthesis/risk_control/figures/) and [updated full paper](manuscript/paper-current.pdf). No new Jev calls. Learned routing falls back to single-rich; group-risk gating loses too much correct-edge coverage; direct qualifier vetoes yield no valid semantic filtering; optimal review ties observed outcomes. The forest-aware solver meets its controlled target on components up to 256 assertions. Negative results, explicit risk assumptions and the false-priority semantic control are retained. No production-policy changes.

<!-- RISK_CONTROL_RESEARCH_END -->

<!-- RELIABILITY_RESEARCH_START -->

## Five reliability and structural improvements after PR #16

[Executed report](graph_synthesis/reliability/RESULTS.md), [frozen protocol](graph_synthesis/reliability/PROTOCOL.md), [five figures](graph_synthesis/reliability/figures/) and [complete updated paper](manuscript/paper-current.pdf). H1 did not meet its frozen target; H2 met its frozen target; H3 met its frozen target; H4 met its frozen target; H5 met its frozen target. H1 scores captured predictions; H2 simulates review; H3-H5 test controlled algorithms. No fresh Jev calls, independent semantic-accuracy claim or production-policy change. Negative results and assumption-breaking controls are retained.

<!-- RELIABILITY_RESEARCH_END -->

<!-- SOURCE_STRUCTURAL_RESEARCH_START -->

## Five source-aware and structural improvements after PR #17

[Executed report](graph_synthesis/source_structural/RESULTS.md), [frozen protocol](graph_synthesis/source_structural/PROTOCOL.md), [five figures](graph_synthesis/source_structural/figures/) and [complete updated paper](manuscript/paper-current.pdf). H1 did not meet its frozen target; H2 did not meet its frozen target; H3 met its frozen target; H4 met its frozen target; H5 met its frozen target. Direct group-risk modeling and setup-cost-aware review fail their targets. Frontier lineage, certified bipartite optimization and revision-checked evidence invalidation meet controlled algorithmic targets. No fresh Jev calls, independent semantic validation, real reviewer cost measurements or production-policy changes. Negative results, correlated-detection and global-source controls are retained.

<!-- SOURCE_STRUCTURAL_RESEARCH_END -->

Read the [updated full paper](manuscript/paper-current.md), [PDF](manuscript/paper-current.pdf), or [HTML](manuscript/paper-current.html).

The fresh full Jev run does **not** reproduce the original interval-based entity improvement: its selected-minus-baseline macro-F1 interval includes zero. Entity accuracy still rises descriptively from 405/413 to 408/413; relation accuracy rises from 286/339 to 290/339, also without a resolved macro-F1 effect. This repeats previously inspected data; it is not independent validation.

- [Fresh run, raw evidence and figures](experiments/jev-rerun-20260918/)
- [Current paper update](experiments/jev-rerun-20260918/PAPER_UPDATE.md)
- [Full analysis](experiments/jev-rerun-20260918/RESULTS.md)
- [Independent artifact audit](experiments/jev-rerun-20260918/verification.json)
- [Byte-identical offline replay](experiments/jev-rerun-20260918/replay-verification.json)
- [48-case live challenge](experiments/jev-rerun-20260918/challenge/evaluation.json): 46/48 against provisional synthetic labels.
- [PR #10 falsification findings](experiments/falsification/PAPER_ADDENDUM.md): reproduced, with no changes to original observations.

The archived root README and original manuscript are retained as part of the immutable 161-file original study. Their earlier conclusions must be read together with this update. All materials here remain an author-review draft.

## Additional calls and information tests

[Full report](experiments/jev-multicall-20260918/REPORT.md), [seven figures](experiments/jev-multicall-20260918/figures/), [protocol](experiments/jev-multicall-20260918/PROTOCOL.md), and [raw evidence](experiments/jev-multicall-20260918/).

3,024 fresh Jev calls compare seven policies on previously unused SciFact source groups (73 development cases; 263 test cases). At 145 accepted test edges, single and repeated voting each make 17 mistakes; blind voting 18, targeted checks 19, indexed evidence 19, contrastive examples 17, and selective routing 20. No added-call method establishes a matched-volume advantage. Shorter contrastive examples use 64.70% fewer test input tokens, but this is an efficiency lead, not proven equivalent accuracy. All failures and unfavorable results are retained. The current full manuscript and PDF now lead with this study and preserve the preceding studies.

## Five follow-up improvements (PR #13)

[Executed results](graph_synthesis/followup/RESULTS.md), [frozen protocol](graph_synthesis/followup/PROTOCOL.md), [five figures](graph_synthesis/followup/figures/), and the updated full paper distinguish same-data response replay from controlled algorithm tests. No new service calls; negative results retained; no production-policy change.
