<div align="center">

# Jev research: evidence and reproduction

**Read the current record. Trace the claim. Replay the evidence.**

[Current manuscript](../manuscript/paper-current.md) · [Current results](../CURRENT_RESULTS.md) · [Reproduction guide](../CURRENT_REPRODUCTION.md) · [Original study](../manuscript/paper.md)

</div>

---

This repository preserves an original Jev decision study and subsequent fresh-call, saved-response, and controlled graph-synthesis studies. The [current manuscript](../manuscript/paper-current.md) maps the studies and their evidence types; [CURRENT_RESULTS.md](../CURRENT_RESULTS.md) links the executed reports and negative findings. Both remain author-review research drafts.

## Current findings and original context

A fresh full Jev repeat on the previously inspected data did **not** resolve the original entity macro-F1 improvement: its paired 95% interval was [-0.0086, +0.0425] and includes zero. Entity accuracy changed descriptively from 405/413 to 408/413. Relation accuracy changed from 286/339 to 290/339; its paired 95% macro-F1 interval was [-0.0175, +0.0428] and also includes zero. This repeat is not independent validation. See the [fresh-run report](../experiments/jev-rerun-20260918/RESULTS.md) and [current summary](../CURRENT_RESULTS.md).

The original fixed-split study found an entity-matching macro-F1 increase from 0.9605 to 0.9859 on 413 DBLP–ACM pairs. Its paired 95% interval was [+0.0010, +0.0540] and excluded zero. The selected formulation combined question wording, a typed decision contract, and demonstrations; the study did not isolate their individual effects. The original relation-verification comparison on 339 SciFact examples did not resolve an improvement.

A later [additional-call study](../experiments/jev-multicall-20260918/REPORT.md) used 3,024 fresh calls on SciFact training source groups unused within the earlier archived Jev runs. No tested added-call policy established a matched-volume edge advantage. Many subsequent graph studies reuse recorded responses or test supplied and simulated inputs. Their controlled target passes do not establish new semantic accuracy or safe unattended graph writes.

## Choose a reading path

| Goal | Start here |
| --- | --- |
| Understand the current research record | [Current manuscript and study map](../manuscript/paper-current.md), [PDF](../manuscript/paper-current.pdf), and [current results](../CURRENT_RESULTS.md) |
| Reproduce the current checkout | [Current reproduction guide](../CURRENT_REPRODUCTION.md) and [graph extension guide](../graph_synthesis/README.md) |
| Audit the original fixed-split study | [Original manuscript](../manuscript/paper.md), [claim-to-evidence map](../supplementary/CLAIM_EVIDENCE.md), [tables](../tables/TABLES.md), and [frozen run](../reproduction/results/jev/run-20260918/) |
| Inspect graph-synthesis methods and limits | [Graph research guide](../graph_synthesis/README.md) and [illustrated assessment](../graph_synthesis/paper.md) |
| Check data origins and rights | [Source and data notes](../supplementary/REFERENCES_AND_DATA.md) |

## Reproduce and cite responsibly

The [current reproduction guide](../CURRENT_REPRODUCTION.md) gives clean-checkout Windows and Unix commands for pinned dependencies, exact dataset hashes, offline replay, and original tests. The current verifier preserves the 161-file original archive. The archived [root README](../README.md) and [original reproduction notes](../REPRODUCE.md) describe that original closed package and remain byte-pinned evidence.

Research workflows run only when explicitly dispatched. The [local validation map](LOCAL_VALIDATION.md) lists the available checks and study commands.

Public datasets are acquired on demand and retain their separate notices. Original project code is offered under AGPL-3.0-only; [reuse boundaries](../RIGHTS.md) distinguish code from manuscripts, saved evidence, and third-party data. Use [CITATION.cff](../CITATION.cff) to cite this package and [source and data notes](../supplementary/REFERENCES_AND_DATA.md) to cite its inputs.
