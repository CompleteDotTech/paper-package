# Current Jev research results — September 18, 2026

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
