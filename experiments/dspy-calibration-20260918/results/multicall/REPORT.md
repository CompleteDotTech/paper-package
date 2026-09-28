# DSPy multi-call transfer and decision-frozen calibration

All eight shards completed: **486 examples** (150 calibration + 336 transfer), **5,832 HTTP attempts**, **15,521,786 reported input tokens**.

The original primary-verifier prompt and all five frozen DSPy accuracy-selected prompts were run through every original multi-call workflow. No prompt was selected using transfer-test outcomes. All requests and policy decisions were reconstructed from raw responses.

| Workflow | Baseline policy accuracy | DSPy policy accuracy mean ± SD | DSPy coverage | DSPy raw forecast NLL | Temperature NLL | Temperature + bias NLL |
|---|---:|---:|---:|---:|---:|---:|
| single | 0.8631 | 0.8685 ± 0.0044 | 1.0000 | 0.7456 | 0.5057 | 0.4778 |
| repeat_vote | 0.8690 | 0.8667 ± 0.0033 | 1.0000 | 0.6760 | 0.4868 | 0.4585 |
| blind_vote | 0.8661 | 0.8726 ± 0.0025 | 1.0000 | 0.6597 | 0.5127 | 0.4837 |
| targeted | 0.8631 | 0.8631 ± 0.0021 | 1.0000 | 0.9296 | 0.5489 | 0.4963 |
| structured | 0.8690 | 0.8685 ± 0.0013 | 1.0000 | 0.8347 | 0.5311 | 0.4856 |
| contrastive | 0.8690 | 0.8649 ± 0.0027 | 1.0000 | 0.7855 | 0.4928 | 0.4556 |
| selective | 0.8631 | 0.8631 ± 0.0021 | 1.0000 | 0.8341 | 0.5329 | 0.4982 |

## What calibration changes

These calibrations change only the normalized forecasts, not the original votes, abstentions, escalation threshold, or adjudication inputs. Policy accuracy is identical across calibration methods by construction. Forecast argmax accuracy is a different endpoint and is reported separately. For voting workflows the normalized forecast is the mean component distribution, not an independence product.

## Coverage and uncertainty

All seven workflow methods, six prompt variants, three calibration methods, and three transfer-panel views are retained in `all-results.json` and `all-results.csv`. `policy-results.json` counts abstentions as incorrect for unconditional accuracy and separately reports coverage, conditional accuracy, confusion matrices, and wrong/correct positive edges. `seed-summary.json` includes means, standard deviations, minima and maxima.

`paired-intervals.json` uses the same source-cluster resampling for baseline and all five search variants. Repeated uses of each example are not independent datasets. Intervals are exploratory and conditional on selected prompts/calibrators. `calibration-effects.json` isolates forecast-quality changes.

## Limits

Only the primary verifier prompt changes. Other reviewers, dimension checks, adjudication instructions, examples and workflow rules are fixed. This is not DSPy optimization of every multi-agent component. Controls are shared and verifier questions batched; isolated per-variant latency and production cost were not measured. This public, already evaluated corpus is not a new external holdout. The small local proposer and three-round searches limit conclusions about larger/longer optimization.

Calibration fits use only the separate 150-row calibration split. The full 336-row transfer panel and original development/test subpanels are never used for fitting. Existing frozen evidence remains unchanged.
