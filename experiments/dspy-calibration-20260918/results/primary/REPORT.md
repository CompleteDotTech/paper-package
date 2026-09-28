# Repeated DSPy and calibration comparison

## Execution scope

Completed captures: **8/8 formulations**, 40 seed-labelled DSPy searches, 12,829 Jev HTTP attempts, 24,465,570 reported input tokens.

Every reported result was reconstructed from saved distributions, every final probability was checked against its raw Jev response, and calibration fits were independently reproduced. Five prompt-search seeds share the same test examples; they are not five independent datasets.

## Main held-out panels

| Task / original formulation | Baseline accuracy | DSPy accuracy mean ± SD | DSPy raw NLL | DSPy temperature NLL | DSPy temperature + bias NLL |
|---|---:|---:|---:|---:|---:|
| entity_resolution / baseline_noul | 0.9806 | 0.9811 ± 0.0011 | 0.1117 | 0.0794 | 0.0789 |
| entity_resolution / fewshot_contract | 0.9879 | 0.9884 ± 0.0011 | 0.0434 | 0.0361 | 0.0367 |
| entity_resolution / identity_contract | 0.9831 | 0.9860 ± 0.0036 | 0.0589 | 0.0591 | 0.0566 |
| entity_resolution / identity_noul | 0.9782 | 0.9860 ± 0.0040 | 0.1218 | 0.0556 | 0.0535 |
| relation_support / baseline_choice | 0.8437 | 0.8437 ± 0.0029 | 1.2698 | 0.5506 | 0.5193 |
| relation_support / conditional_nouls | 0.8496 | 0.8490 ± 0.0025 | 0.4809 | 0.4597 | 0.4308 |
| relation_support / evidence_contract | 0.8525 | 0.8507 ± 0.0016 | 1.3225 | 0.5944 | 0.5299 |
| relation_support / fewshot_contract | 0.8555 | 0.8549 ± 0.0013 | 1.1015 | 0.6211 | 0.5842 |

Scalar temperature is analytically rank preserving; one recorded near-tie may change its floating-point argmax after transformation. See numerical-ties.json. Temperature plus bias may change labels. Neither calibration method is guaranteed to improve held-out results.

## Evidence and interpretation

- `all-results.csv` and `all-results.json`: every seed, formulation, panel, selection rule and calibration method, including confusion matrices in JSON.
- `seed-summary.json`: means, sample standard deviations, minima and maxima; no best-test-seed selection.
- `paired-intervals.json`: paired source-component bootstrap for mean search performance versus its same-method baseline. Pointwise exploratory 95% intervals are conditional on the selected prompts and fitted calibrators.
- `calibration-effects.json`: each raw-to-calibrated delta and count of changed labels.
- `prediction-changes.json`: paired repaired errors and regressions; `search-summary.json`: malformed, duplicate, rejected and accepted proposals.
- `execution.json`: actual calls, usage and latency by phase. Final variants were batched, so isolated per-variant latency/cost was not measured.
- `graph-replay.json`: compiler/topology/lifecycle behavior using the new probabilities at fixed thresholds 0 and 0.9.

## Limits

These are public, previously evaluated panels: retrospective exploratory evidence, not a new untouched external benchmark. The local Qwen2.5-1.5B proposer, 31-example training / 29-example validation panels and three-round budget limit conclusions about larger models or longer searches. The NLL-selected arm comes from the accuracy-guided candidate pool; it is not a separate NLL-directed search.

All original question types and demonstrations are preserved. Original deterministic graph suites are separate replay/regression checks, not independent live semantic benchmarks. The seven original multi-call workflows have a separately reported frozen-prompt transfer experiment; question-level evaluation alone must not be represented as that experiment. Specialist retraining and open-corpus retrieval remain outside this run.

Calibration fits use only the disjoint calibration split. Bootstrap intervals do not include refitting uncertainty, distribution shift, or multiple-testing correction. Confidence gains are not proof of better calibration; inspect Brier/NLL and calibration deltas together.

## Sources

- TypeSafe API: https://docs.typesafe.ai/api
- Guo et al. (2017), On Calibration of Modern Neural Networks: https://proceedings.mlr.press/v70/guo17a.html
- Official proposal model: https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF
