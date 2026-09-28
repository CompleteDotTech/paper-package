# Jev with and without DSPy: repeated searches and calibration

**Actual live Jev inference and actual DSPy-generated prompt proposals.** The named Jev credential stayed in GitHub Actions. The proposal model was a locally executed, checksum-verified Qwen2.5-1.5B-Instruct Q4_K_M through DSPy 3.3.1 and llama.cpp b10964.

## Coverage

Eight original formulations × five independent searches × three candidate rounds. All original source splits and demonstrations were retained; 31 TRAIN and 29 VALIDATION examples per task controlled search. Calibration used separate 150-row relation and 390-row entity panels. All five searches froze before calibration or test inference.

The primary capture includes the full 339-row relation and 413-row entity evaluations, 50 relation fixtures, all 100 entity fixtures, the 336-row relation transfer corpus and 48-row challenge. Binary fixture metrics use 88 eligible entity fixtures; 12 original uncertain fixtures are reported separately, without inventing binary labels.

All seven original multi-call workflows were rerun with baseline and all five frozen few-shot accuracy-selected prompts. Fresh service repeatability and original cross-formulation batching/isolated comparisons cover both tasks. The existing graph compiler was replayed 528 times on the new captured probabilities at fixed thresholds 0 and 0.9.

## Main held-out classification results

DSPy entries are mean ± sample standard deviation over **five searches**, not a cherry-picked seed. Percentage-point (pp) differences are absolute. The same test examples were reused across searches and are not counted as additional independent samples.

| Task / original formulation | Baseline accuracy | DSPy accuracy mean ± SD | Difference | Baseline macro-F1 | DSPy macro-F1 |
|---|---:|---:|---:|---:|---:|
| relation_support / baseline_choice | 84.37% | 84.37% ± 0.29 pp | +0.00 pp | 0.8423 | 0.8422 |
| relation_support / evidence_contract | 85.25% | 85.07% ± 0.16 pp | -0.18 pp | 0.8496 | 0.8494 |
| relation_support / conditional_nouls | 84.96% | 84.90% ± 0.25 pp | -0.06 pp | 0.8498 | 0.8494 |
| relation_support / fewshot_contract | 85.55% | 85.49% ± 0.13 pp | -0.06 pp | 0.8538 | 0.8523 |
| entity_resolution / baseline_noul | 98.06% | 98.11% ± 0.11 pp | +0.05 pp | 0.9605 | 0.9615 |
| entity_resolution / identity_contract | 98.31% | 98.60% ± 0.36 pp | +0.29 pp | 0.9674 | 0.9723 |
| entity_resolution / identity_noul | 97.82% | 98.60% ± 0.40 pp | +0.77 pp | 0.9581 | 0.9721 |
| entity_resolution / fewshot_contract | 98.79% | 98.84% ± 0.11 pp | +0.05 pp | 0.9761 | 0.9770 |

## Does calibration improve it?

The sequences below are **raw → temperature → temperature plus class bias**, for the accuracy-selected DSPy prompts. Lower NLL and Brier are better. Improvements in NLL may coexist with worse Brier, ECE or accuracy; no single calibration metric establishes universal improvement. Baseline calibration results and NLL-selected-pool ablations are retained in the complete reports, not omitted.

| Task / formulation | Mean NLL: raw → T → T+bias | Mean Brier: raw → T → T+bias | Accuracy after T+bias |
|---|---:|---:|---:|
| relation_support / baseline_choice | 1.2698 → 0.5506 → 0.5193 | 0.2329 → 0.2973 → 0.2860 | 81.12% |
| relation_support / evidence_contract | 1.3225 → 0.5944 → 0.5299 | 0.2363 → 0.2906 → 0.2775 | 78.29% |
| relation_support / conditional_nouls | 0.4809 → 0.4597 → 0.4308 | 0.2475 → 0.2343 → 0.2301 | 84.25% |
| relation_support / fewshot_contract | 1.1015 → 0.6211 → 0.5842 | 0.2341 → 0.2529 → 0.2518 | 84.48% |
| entity_resolution / baseline_noul | 0.1117 → 0.0794 → 0.0789 | 0.0431 → 0.0326 → 0.0324 | 98.11% |
| entity_resolution / identity_contract | 0.0589 → 0.0591 → 0.0566 | 0.0270 → 0.0235 → 0.0225 | 98.55% |
| entity_resolution / identity_noul | 0.1218 → 0.0556 → 0.0535 | 0.0496 → 0.0241 → 0.0229 | 98.69% |
| entity_resolution / fewshot_contract | 0.0434 → 0.0361 → 0.0367 | 0.0204 → 0.0198 → 0.0199 | 98.74% |

Across these eight formulation comparisons, temperature lowered mean DSPy NLL in 7/8, Brier in 5/8, and ECE in 5/8. Temperature plus bias lowered these metrics in 8/8, 5/8 and 5/8 respectively. These correlated comparisons are descriptive counts, not eight independent replications.

Scalar temperature is analytically rank preserving, but one near-tied saved probability row changes its floating-point argmax after transformation. This numerical sensitivity is documented in [numerical-ties.json](primary/numerical-ties.json), not credited as semantic improvement. Bias calibration can change labels and can harm accuracy. All calibrator fits use only the designated calibration split, with fixed bounds and regularization.

## Seven multi-call workflows

This is transfer of the five already-frozen primary-verifier prompts, not independent DSPy optimization of every reviewer or workflow component. Original reviewer/adjudicator prompts, policies, threshold, demonstrations and abstention rules stay fixed.

| Workflow | Baseline policy accuracy | DSPy policy accuracy mean ± SD | DSPy coverage | Forecast NLL: raw → T → T+bias |
|---|---:|---:|---:|---:|
| single | 86.31% | 86.85% ± 0.44 pp | 100.00% | 0.7456 → 0.5057 → 0.4778 |
| repeat_vote | 86.90% | 86.67% ± 0.33 pp | 100.00% | 0.6760 → 0.4868 → 0.4585 |
| blind_vote | 86.61% | 87.26% ± 0.25 pp | 100.00% | 0.6597 → 0.5127 → 0.4837 |
| targeted | 86.31% | 86.31% ± 0.21 pp | 100.00% | 0.9296 → 0.5489 → 0.4963 |
| structured | 86.90% | 86.85% ± 0.13 pp | 100.00% | 0.8347 → 0.5311 → 0.4856 |
| contrastive | 86.90% | 86.49% ± 0.27 pp | 100.00% | 0.7855 → 0.4928 → 0.4556 |
| selective | 86.31% | 86.31% ± 0.21 pp | 100.00% | 0.8341 → 0.5329 → 0.4982 |

These post-hoc workflow calibrations change **forecasts only**. They do not alter votes, abstentions, escalation, adjudication input or policy-label accuracy. Vote-mixture forecast argmax is a distinct metric. Unconditional policy accuracy counts abstentions as errors; coverage and conditional accuracy are reported separately.

## Repeatability, packing and measurement quality

[Repeatability report](repeatability/REPORT.md) separates between-search dispersion from within-search service dispersion using three fresh passes on each original 20-row evaluation repeatability panel. Matched batching versus isolated requests use the original 20-row development batching panel solely for packing/cost diagnostics, not a new holdout accuracy claim.

[Data-quality report](quality/REPORT.md) lists unchanged selected prompts, differences between identical prompts in the same request, and returned probability-mass defects. A difference for an unchanged prompt is not evidence of successful prompt optimization. A fixed, bounded rounding interpretation proportionally normalizes only eligible near-unit-mass vectors; raw values and all flags are retained. This input normalization is distinct from learned statistical calibration.

## Actual execution and cost accounting

| Stage | HTTP attempts | Reported input tokens | Estimated Jev cost |
|---|---:|---:|---:|
| primary | 12,829 | 24,465,570 | $1.0276 |
| transfer | 5,832 | 15,521,786 | $0.6519 |
| diagnostics | 1,280 | 2,115,466 | $0.0888 |
| prior_pilots | 7,901 | 14,338,030 | $0.6022 |

Estimates use $0.042 per million reported Jev input tokens, not an invoice. Missing usage on failed calls, local proposal CPU work, GitHub Actions runtime and other infrastructure costs are not included. Prior pilots are reported separately and are not pooled as successful v2 searches. Reporting completion reused existing raw calls and made zero new inference calls.

## Complete results and reproduction

[Primary report](primary/REPORT.md) · [Every primary metric row, CSV](primary/all-results.csv) · [Primary JSON with confusion matrices](primary/all-results.json) · [Paired source-cluster intervals](primary/paired-intervals.json) · [Graph compiler outcomes](primary/graph-replay.json) · [Multi-call report](multicall/REPORT.md) · [Every workflow forecast row, CSV](multicall/all-results.csv) · [Workflow policy results](multicall/policy-results.json) · [Repeatability CSV](repeatability/repeat-metrics.csv).

The package contains raw compressed call journals, all proposal traces, rejected and duplicate candidates, frozen configurations, fitted calibrators, per-seed comparisons, prediction changes, calibration deltas, source/environment fingerprints, failed pilots and original workflow statuses. Manifests bind all published artifacts. The original frozen 161-file research inventory and original optimizer manifest are unchanged.

## Interpretation limits

These public, previously evaluated datasets provide **retrospective exploratory evidence**, not a new untouched external benchmark. The local 1.5B proposal model, three-round budget and small validation panel limit conclusions about stronger models or longer searches. The NLL-selected arm is selected from the same accuracy-guided candidate pool, not a separate NLL-directed optimizer. No GEPA/MIPROv2 invocation or weight training is claimed.

Paired bootstrap intervals resample connected source/entity components and preserve baseline/candidate pairing. They are pointwise exploratory intervals conditional on frozen prompts and fitted calibrators; they do not incorporate calibration-fit uncertainty or multiple-testing correction. Shared reviewer controls and batched final predictions are not independent service replicates. Timing phases are not randomized across server load.

The 17 legacy graph research workflows were rerun as regression/replay checks. They are not 17 new independently DSPy-trained semantic systems. Archived specialist-model retraining, open-corpus retrieval evaluation and exhaustive search of every possible prompt are outside this comparison.

## Source and execution provenance

- Primary live capture: https://github.com/CompleteDotTech/paper-package/actions/runs/35342763186
- Completion, transfer and repeatability captures: https://github.com/CompleteDotTech/paper-package/actions/runs/35345560822. Its original analysis job failed on a numerical near-tie and its downstream audit did not run.
- Offline independent audit source commit: `24b2060279f7d137fd78e345de96cca5ef158770`. [Offline audit status](offline-audit-status.json) and [original artifact receipts](source-artifact-receipts.json) preserve that failure history and the zero-new-inference correction.
- TypeSafe API and model documentation: https://docs.typesafe.ai/api ; https://docs.typesafe.ai/models
- Calibration reference: Guo et al. (2017), https://proceedings.mlr.press/v70/guo17a.html
- Official proposal model: https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF
