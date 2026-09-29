# Five-seed live DSPy / Jev comparison

The registered seeds **11, 23, 37, 53, and 71** completed on source commit
[`306a02b`](https://github.com/CompleteDotTech/paper-package/commit/306a02be417e8ed863968ab8fac79c47c82fa555).
Every seed has 32 accepted proposals, 294 metric rows, and the same protocol,
data inventory, source hashes, and dependency versions. The aggregate verifier
accepted all five; every row of [`summary.csv`](summary.csv) has `runs=5`.
The [generated report](RESULTS.md) and [machine-readable summary](summary.json)
cover all registered arms, panels, and calibrations. The
[per-seed metrics](per-seed-metrics.json) preserve all 1,470 metric rows.

## Raw test interpretation

Mean raw test accuracy across the five runs was **0.8578** for relation-support
DSPy composite search and **0.9850** for entity-resolution DSPy composite
search. The registered no-DSPy baseline arms scored **0.8496** and **0.9811**;
the registered no-DSPy few-shot arms scored **0.8602** and **0.9874**. The full
table includes all four no-DSPy formulations per task and all calibration
settings. These observations do not establish a uniform DSPy advantage.

The five seeds repeat model calls and search on the **same fixed test sets**
(339 relation-support and 413 entity-resolution examples). They are not five
independent datasets. Search objectives, post-hoc calibration, and control
formulations are separate interventions. Temperature-only calibration preserves
labels; bias/temperature calibration may change them. In particular,
relation-support DSPy composite mean accuracy fell from **0.8578** raw to
**0.7923** under full-data bias/temperature calibration. This is a descriptive
finding, not a selected winning configuration. Synthetic fixtures and the
semantic challenge are exploratory transfer panels.

## Run and cost receipts

| Seed | Workflow | Guarded estimate | Artifact ZIP SHA-256 |
| ---: | --- | ---: | --- |
| 11 | [36494885890](https://github.com/CompleteDotTech/paper-package/actions/runs/36494885890) | $2.825902 | `52acd8dc622b42fc6f5f26bda8348eb8214d780548c9c39047b1f361810e9463` |
| 23 | [36498000250](https://github.com/CompleteDotTech/paper-package/actions/runs/36498000250) | $2.962973 | `cfd2f51e7f8de1ccc914c9c473cd7489008476335d0367c5b02f869136e6b93c` |
| 37 | [36500595454](https://github.com/CompleteDotTech/paper-package/actions/runs/36500595454) | $3.256784 | `b58f9f210c1822156751f7f4556de4cef52b7452ee65187525a8a8544cbc26a5` |
| 53 | [36503796739](https://github.com/CompleteDotTech/paper-package/actions/runs/36503796739) | $2.966748 | `530c1dd42530827f2b2cb72b0904e8407b49b881e278e0fcd86367dab29358f2` |
| 71 | [36506697817](https://github.com/CompleteDotTech/paper-package/actions/runs/36506697817) | $2.853800 | `5222e055c05595d7fe4965d4b59f526f25fb03eafdc7be370c24961936d08fec` |

The cohort's guarded estimate is **$14.866207**. Including earlier failed,
canceled, and standalone attempts, the guarded estimate is **$24.110630**
against the authorized **$50 total cap**. These are computed from reported
tokens plus conservative reserves for proposal calls and unknown Jev usage;
they are **not provider invoices**. The [receipt file](RUN_RECEIPTS.json)
records exact values, retries, usage, run IDs, protocol hashes, and artifact
inventories. [Earlier attempts](../LIVE_RUN_PLAN.md) remain excluded from this
cohort and retain their original failure history.

## Raw evidence and reuse

The five cohort raw request/response and proposal-trace ZIPs, plus ten excluded
earlier-attempt ZIPs, are attached to the
[evidence release](https://github.com/CompleteDotTech/paper-package/releases/tag/dspy-jev-five-seed-20260928).
Each release asset is the verified GitHub Actions artifact ZIP named in the
[cohort receipts](RUN_RECEIPTS.json) or [prior-attempt receipts](PRIOR_ATTEMPTS.json).
The cohort ZIPs include per-seed requests, responses, predictions,
proposal journals, usage, budget, status, and hashed artifact inventories.
They also include the resolved dependency record. Earlier ZIPs preserve partial
traces and the original errors; they are excluded from aggregate scores.
GitHub Actions copies have
a 14-day retention period; the release assets are the durable copies.

The [rights and attribution notice](PUBLICATION_NOTICE.md) applies to the raw
traces. The repository's AGPL code license does not relicense embedded
third-party research text or data. A credential-pattern scan of **1,058 entries
across all 15 ZIPs**, including decompressed prediction files, found no matches
for Bearer tokens or the named API-key patterns; this is a bounded scan, not a
general guarantee about arbitrary secrets.

## Rebuild and verification

Download the five ZIP assets, verify their SHA-256 values against
[`RUN_RECEIPTS.json`](RUN_RECEIPTS.json), and extract each artifact's `seed-N`
directory under one parent directory. With the dependencies pinned in the raw
environment records and the source commit above, run:

```bash
python -m graph_synthesis.dspy_benchmark.report --directory /path/to/five-seed-parent
```

The report rejects missing or mixed protocols, malformed matrices, inventory
hash mismatches, and cost receipts that disagree with the raw journals. It
produces `run-status.json`, `summary.json`, `summary.csv`, and `RESULTS.md`.
The original 161-file research inventory remains unchanged.
