# Jev research paper package

This directory contains a manuscript draft and the evidence needed to develop, audit and reproduce a detailed empirical paper on improving Jev decisions. It is portable as one directory. The main finding is a narrow entity-matching improvement on a fixed evaluation split; relation verification did not show a resolved improvement. Publication readiness and empirical evidence are separate: see the submission checklist before claiming a general result.

## Start here

| Material | Location | Purpose |
|---|---|---|
| Manuscript draft | [manuscript/paper.md](manuscript/paper.md) | Full paper text with methods, positive and null results, discussion and limitations |
| Bibliography | [manuscript/references.bib](manuscript/references.bib) | Verified primary references for citation management |
| Methods supplement | [supplementary/METHODS_AND_REPRODUCIBILITY.md](supplementary/METHODS_AND_REPRODUCIBILITY.md) | Exact data preparation, prompts, metrics and statistical procedure |
| Claim-to-evidence map | [supplementary/CLAIM_EVIDENCE.md](supplementary/CLAIM_EVIDENCE.md) | Trace paper claims to saved evidence |
| Submission checklist | [supplementary/SUBMISSION_READINESS.md](supplementary/SUBMISSION_READINESS.md) | Remaining scientific, reporting and venue decisions |
| Source and data notes | [supplementary/REFERENCES_AND_DATA.md](supplementary/REFERENCES_AND_DATA.md) | Source verification, dataset attribution and rights |
| Tables | [tables/TABLES.md](tables/TABLES.md) | Generated tables with machine-readable companions |
| Figures | [figures/paired_effects.svg](figures/paired_effects.svg) | Vector figure; PNG also included |
| Frozen study | [reproduction/results/jev/run-20260918/](reproduction/results/jev/run-20260918/) | Prompts, selected examples, raw requests/responses, predictions, calibration and complete results |
| Protocol | [reproduction/results/jev/PROTOCOL.md](reproduction/results/jev/PROTOCOL.md) | Study commitments frozen before research calls |
| Reproduction guide | [REPRODUCE.md](REPRODUCE.md) | Integrity checking, exact offline replay and optional fresh calls |
| Original context | [background/README.md](background/README.md) | Original reports, theory work and historical drafts with status notes |
| Copy provenance | [PROVENANCE.json](PROVENANCE.json) | Source locations and byte hashes for collected evidence |
| Package inventory | [MANIFEST.json](MANIFEST.json) | SHA-256 and size for every package file |

## What the package establishes

The corrected baseline and selected formulation use the same requested Jev model version. On 413 held-out DBLP–ACM pairs, macro-F1 increased from 0.9605 to 0.9859 and false merges decreased from eight to two, with one additional missed match. The paired macro-F1 interval excludes zero on this split. On 339 SciFact examples, the relation macro-F1 interval includes zero. The intervention combines question formulation and demonstrations; its components have not been independently attributed on held-out data.

All 3,644 predictions can be reconstructed from saved responses. The package verifier copies its runtime to a temporary directory, disables networking, checks the independent artifact audit, replays every phase and compares the original calls, predictions, calibration and results byte for byte. Fresh service repeat panels are separate measurements and do not establish bitwise determinism.

The source code and experiment evidence are included. Public datasets and prepared dataset files are downloaded and regenerated with `python -B scripts/download_datasets.py`; they are excluded from Git. Virtual environments, model weights, API credentials and session logs are excluded. The Jev replay needs no model weights or credentials. Earlier specialist results are included for historical context, but their locally trained checkpoints are not included and exact specialist retraining is not part of the verified Jev replay.

## Scope and attribution

Standalone public datasets are fetched on demand. Saved experiment plans and API requests still contain the selected examples required to audit the reported results. `PROVENANCE.json` and the archived validation report describe the original assembly; `MANIFEST.json` describes the current repository files and `scripts/datasets.json` records the expected downloaded dataset bytes.

The original research material proposed a much broader graph compiler. This package's primary manuscript reports the actually executed Jev decision study; the broader system remains background. Old publication drafts are archived with their supersession notices and must not be used as current measured claims.

The directory does not grant a new license to the project's code or to third-party data. Dataset licensing, attribution and transformation notes are in the source supplement. Author order, affiliations, conflicts, funding, target venue and any public archival DOI remain author decisions. API charges are estimates from reported usage, not verified invoices.
