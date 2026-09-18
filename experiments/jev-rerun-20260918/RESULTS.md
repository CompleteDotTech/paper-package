# Jev same-model research results

This compares Jev request formulations and probability post-processing using the same service. It does not establish a general benchmark win or compare newly trained models.

Arm selection uses development macro F1, then Brier, then arm name. Scalar temperatures use calibration labels only; held-out evaluation and fixtures are not used for fitting. Service errors count as operational failures. Probabilistic scores use valid responses; vendor-reported confidence is not ground truth.

## entity_resolution

Baseline: `baseline_noul`. Selected alternative: `fewshot_contract`.

| Development arm | Accuracy | Macro F1 | Brier | Probability N | Errors |
|---|---:|---:|---:|---:|---:|
| fewshot_contract | 1.0000 | 1.0000 | 0.0083 | 60 | 0 |
| identity_contract | 1.0000 | 1.0000 | 0.0187 | 60 | 0 |
| identity_noul | 1.0000 | 1.0000 | 0.0366 | 60 | 0 |
| baseline_noul | 0.9833 | 0.9819 | 0.0413 | 60 | 0 |

Selected alternative beats baseline on development macro F1: True.

| Split | Arm | Calibration | N | Errors | Accuracy | Macro F1 | Brier | Log loss | False merge |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| development | baseline_noul | raw | 60 | 0 | 0.9833 | 0.9819 | 0.0413 | 0.1168 | 0.0256 |
| development | baseline_noul | calibrated | 60 | 0 | 0.9833 | 0.9819 | 0.0160 | 0.0253 | 0.0256 |
| development | fewshot_contract | raw | 60 | 0 | 1.0000 | 1.0000 | 0.0083 | 0.0158 | 0.0000 |
| development | fewshot_contract | calibrated | 60 | 0 | 1.0000 | 1.0000 | 0.0067 | 0.0114 | 0.0000 |
| calibration | baseline_noul | raw | 390 | 0 | 0.9974 | 0.9947 | 0.0219 | 0.0834 | 0.0179 |
| calibration | baseline_noul | calibrated | 390 | 0 | 0.9974 | 0.9947 | 0.0057 | 0.0122 | 0.0179 |
| calibration | fewshot_contract | raw | 390 | 0 | 0.9974 | 0.9948 | 0.0090 | 0.0180 | 0.0000 |
| calibration | fewshot_contract | calibrated | 390 | 0 | 0.9974 | 0.9948 | 0.0080 | 0.0154 | 0.0000 |
| evaluation | baseline_noul | raw | 413 | 0 | 0.9806 | 0.9605 | 0.0407 | 0.1067 | 0.1270 |
| evaluation | baseline_noul | calibrated | 413 | 0 | 0.9806 | 0.9605 | 0.0313 | 0.0652 | 0.1270 |
| evaluation | fewshot_contract | raw | 413 | 0 | 0.9879 | 0.9764 | 0.0181 | 0.0333 | 0.0476 |
| evaluation | fewshot_contract | calibrated | 413 | 0 | 0.9879 | 0.9764 | 0.0157 | 0.0262 | 0.0476 |
| fixtures | baseline_noul | raw | 100 | 0 | 0.9545 | 0.8961 | 0.0707 | 0.1375 | 0.2500 |
| fixtures | baseline_noul | calibrated | 100 | 0 | 0.9545 | 0.8961 | 0.0804 | 0.1920 | 0.2500 |
| fixtures | fewshot_contract | raw | 100 | 0 | 0.9886 | 0.9767 | 0.0513 | 0.1369 | 0.0000 |
| fixtures | fewshot_contract | calibrated | 100 | 0 | 0.9886 | 0.9767 | 0.0394 | 0.1228 | 0.0000 |

Evaluation paired differences are selected minus baseline. Intervals condition on the fixed development choice and fitted temperatures; multiple comparisons are not corrected.

| Version | Metric | Difference | 95% interval | Paired Brier N |
|---|---|---:|---|---:|
| raw | accuracy | 0.0073 | [-0.0048, 0.0194] | 413 |
| raw | macro_f1 | 0.0160 | [-0.0086, 0.0425] | 413 |
| raw | brier_score | -0.0225 | [-0.0325, -0.0134] | 413 |
| raw | false_merge_rate | -0.0794 | [-0.1538, -0.0179] | 413 |
| calibrated | accuracy | 0.0073 | [-0.0048, 0.0194] | 413 |
| calibrated | macro_f1 | 0.0160 | [-0.0086, 0.0425] | 413 |
| calibrated | brier_score | -0.0156 | [-0.0328, -0.0010] | 413 |
| calibrated | false_merge_rate | -0.0794 | [-0.1538, -0.0179] | 413 |

Calibration fits:

- `baseline_noul`: T=0.2918, 390/390 calibration responses; calibration log loss 0.0834 to 0.0122.
- `fewshot_contract`: T=0.6459, 390/390 calibration responses; calibration log loss 0.0180 to 0.0154.

No resolved improvement in raw operational macro F1: the paired interval includes zero or evidence is unavailable.

## relation_support

Baseline: `baseline_choice`. Selected alternative: `fewshot_contract`.

| Development arm | Accuracy | Macro F1 | Brier | Probability N | Errors |
|---|---:|---:|---:|---:|---:|
| fewshot_contract | 0.8667 | 0.8657 | 0.2005 | 60 | 0 |
| conditional_nouls | 0.8667 | 0.8649 | 0.2216 | 60 | 0 |
| evidence_contract | 0.8500 | 0.8494 | 0.2342 | 60 | 0 |
| baseline_choice | 0.8000 | 0.8017 | 0.2768 | 60 | 0 |

Selected alternative beats baseline on development macro F1: True.

| Split | Arm | Calibration | N | Errors | Accuracy | Macro F1 | Brier | Log loss | False merge |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| development | baseline_choice | raw | 60 | 0 | 0.8000 | 0.8017 | 0.2768 | 0.9852 | N/A |
| development | baseline_choice | calibrated | 60 | 0 | 0.8000 | 0.8017 | 0.2794 | 0.5143 | N/A |
| development | fewshot_contract | raw | 60 | 0 | 0.8667 | 0.8657 | 0.2005 | 0.8769 | N/A |
| development | fewshot_contract | calibrated | 60 | 0 | 0.8667 | 0.8657 | 0.2077 | 0.4784 | N/A |
| calibration | baseline_choice | raw | 150 | 0 | 0.8667 | 0.8564 | 0.2206 | 0.8169 | N/A |
| calibration | baseline_choice | calibrated | 150 | 0 | 0.8667 | 0.8564 | 0.2550 | 0.4933 | N/A |
| calibration | fewshot_contract | raw | 150 | 1 | 0.8333 | 0.8345 | 0.2344 | 0.6163 | N/A |
| calibration | fewshot_contract | calibrated | 150 | 1 | 0.8333 | 0.8345 | 0.2311 | 0.4255 | N/A |
| evaluation | baseline_choice | raw | 339 | 1 | 0.8437 | 0.8432 | 0.2342 | 1.2402 | N/A |
| evaluation | baseline_choice | calibrated | 339 | 1 | 0.8437 | 0.8432 | 0.2726 | 0.5700 | N/A |
| evaluation | fewshot_contract | raw | 339 | 2 | 0.8555 | 0.8566 | 0.2244 | 1.3207 | N/A |
| evaluation | fewshot_contract | calibrated | 339 | 2 | 0.8555 | 0.8566 | 0.2561 | 0.6323 | N/A |
| fixtures | baseline_choice | raw | 50 | 0 | 0.9400 | 0.9414 | 0.1295 | 0.2469 | N/A |
| fixtures | baseline_choice | calibrated | 50 | 0 | 0.9400 | 0.9414 | 0.1818 | 0.2877 | N/A |
| fixtures | fewshot_contract | raw | 50 | 0 | 0.9000 | 0.9015 | 0.1028 | 0.1626 | N/A |
| fixtures | fewshot_contract | calibrated | 50 | 0 | 0.9000 | 0.9015 | 0.1625 | 0.2766 | N/A |

Evaluation paired differences are selected minus baseline. Intervals condition on the fixed development choice and fitted temperatures; multiple comparisons are not corrected.

| Version | Metric | Difference | 95% interval | Paired Brier N |
|---|---|---:|---|---:|
| raw | accuracy | 0.0118 | [-0.0202, 0.0422] | 336 |
| raw | macro_f1 | 0.0134 | [-0.0175, 0.0428] | 336 |
| raw | brier_score | -0.0105 | [-0.0452, 0.0255] | 336 |
| calibrated | accuracy | 0.0118 | [-0.0202, 0.0422] | 336 |
| calibrated | macro_f1 | 0.0134 | [-0.0175, 0.0428] | 336 |
| calibrated | brier_score | -0.0164 | [-0.0374, 0.0061] | 336 |

Calibration fits:

- `baseline_choice`: T=4.5617, 150/150 calibration responses; calibration log loss 0.8169 to 0.4933.
- `fewshot_contract`: T=3.4437, 149/150 calibration responses; calibration log loss 0.6163 to 0.4255.

No resolved improvement in raw operational macro F1: the paired interval includes zero or evidence is unavailable.

## Fresh repeatability

- entity_resolution / `baseline_noul`: 20 examples, 60 valid fresh pairwise comparisons, agreement 1.0000, 0 argmax flips, maximum total variation 0.0600; 0 fresh comparisons contain errors. Provenance: {'fresh_recorded_calls': 60}.
- entity_resolution / `fewshot_contract`: 20 examples, 60 valid fresh pairwise comparisons, agreement 1.0000, 0 argmax flips, maximum total variation 0.0700; 0 fresh comparisons contain errors. Provenance: {'fresh_recorded_calls': 60}.
- relation_support / `baseline_choice`: 20 examples, 60 valid fresh pairwise comparisons, agreement 0.9667, 2 argmax flips, maximum total variation 0.0900; 0 fresh comparisons contain errors. Provenance: {'fresh_recorded_calls': 60}.
- relation_support / `fewshot_contract`: 20 examples, 58 valid fresh pairwise comparisons, agreement 0.9828, 1 argmax flips, maximum total variation 0.1400; 2 fresh comparisons contain errors. Provenance: {'fresh_recorded_calls': 60}.

Fresh calls are identified by distinct recorded call IDs. Exact repeated outputs alone do not prove either service determinism or caching; local cached replays are not fresh-repeat evidence.

## Usage and limitations

Recorded invocations: 3404; usage reported for 3404. Input tokens: 4792410; output tokens: 139558. Estimated USD for reported usage: 0.2013. Invoice verified: no.

Reported usage summed once per logical calls.jsonl entry; shared batches are never multiplied by prediction count. HTTP attempts/retries are counted separately; usage absent from retry responses is unknown. USD is a unit-price estimate, not a verified invoice. Missing usage is unknown; summed call latency is not parallel wall time.

Frozen-plan completeness: complete.

Full input predictions, requests and responses remain in `predictions.jsonl` and `calls.jsonl`; hashes and manifest are recorded in `results.json`. Fixture scores are diagnostic, not independent natural-data evidence. Bootstrap intervals reflect sampled evaluation groups, not model-selection uncertainty. Positive-temperature calibration preserves argmax and therefore cannot itself improve accuracy.

Batching comparisons are descriptive and available in `results.json`; they do not establish a general batching-invariance guarantee.
