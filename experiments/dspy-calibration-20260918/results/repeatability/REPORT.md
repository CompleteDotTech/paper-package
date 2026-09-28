# Fresh repeatability, batching and isolated inference costs

The original 20-row repeatability panels were evaluated three times per frozen configuration. The original 20-row batching panels are development examples, used for packing/performance diagnostics, not new held-out accuracy claims. All eight formulations, baseline plus five frozen accuracy-selected DSPy prompts, are included.

Every recorded request and prediction was reconstructed from its raw response. The paired packing test retains the original grouping: all non-few-shot formulations share one state; few-shot input remains separate. Individual requests use exactly the same configurations and examples.

| Task / formulation | Baseline repeat accuracy | DSPy repeat accuracy | Between-search SD | Mean within-search service SD |
|---|---:|---:|---:|---:|
| relation_support / baseline_choice | 0.9500 | 0.9467 | 0.0075 | 0.0058 |
| relation_support / evidence_contract | 0.8833 | 0.8900 | 0.0091 | 0.0173 |
| relation_support / conditional_nouls | 0.8500 | 0.8500 | 0.0000 | 0.0000 |
| relation_support / fewshot_contract | 0.9000 | 0.9000 | 0.0000 | 0.0000 |
| entity_resolution / baseline_noul | 0.9833 | 0.9933 | 0.0091 | 0.0115 |
| entity_resolution / identity_contract | 0.9667 | 0.9900 | 0.0224 | 0.0000 |
| entity_resolution / identity_noul | 0.9500 | 0.9900 | 0.0224 | 0.0000 |
| entity_resolution / fewshot_contract | 1.0000 | 1.0000 | 0.0000 | 0.0000 |

## Probability calibration and service variation

`replication-summary.json` reports raw, temperature and temperature-plus-bias metrics. Calibrators are reused from the disjoint primary calibration split; no fits are made on these 20 examples. Means and standard deviations describe search and service repetition axes separately. Repeated observations are not new independent test examples.

`drift.json` counts label disagreements across service repeats and between batched and isolated calls, plus maximum probability differences. Do not interpret a score difference for an unchanged prompt as proof of optimization.

## Inference cost and packing

`packing.json` compares actual reported input tokens for the same examples and configurations batched versus separate. `isolated-costs.json` measures baseline and DSPy token usage and request latency without cross-configuration batching. These exclude optimizer overhead, local model CPU time, CI time and external invoice verification. Batch request latency covers many predictions, so it is not directly equivalent to isolated one-configuration latency.

The packing modes were executed in blocks, not randomized across server load; latency comparisons are descriptive. All raw calls, including retries, are retained. Input-token cost estimates use the documented Jev price and are not invoices.
