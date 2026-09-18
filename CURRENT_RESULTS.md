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

## Five follow-up improvements (PR #13)

[Executed results](graph_synthesis/followup/RESULTS.md), [frozen protocol](graph_synthesis/followup/PROTOCOL.md), [five figures](graph_synthesis/followup/figures/), and the updated full paper distinguish same-data response replay from controlled algorithm tests. No new service calls; negative results retained; no production-policy change.
