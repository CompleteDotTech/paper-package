# Jev same-model research results

This compares Jev request formulations and probability post-processing using the same service. It does not establish a general benchmark win or compare newly trained models.

Arm selection uses development macro F1, then Brier, then arm name. Scalar temperatures use calibration labels only; held-out evaluation and fixtures are not used for fitting. Service errors count as operational failures. Probabilistic scores use valid responses; vendor-reported confidence is not ground truth.

## relation_support

Baseline: `baseline_choice`. Selected alternative: `fewshot_contract`.

| Development arm | Accuracy | Macro F1 | Brier | Probability N | Errors |
|---|---:|---:|---:|---:|---:|
| fewshot_contract | 0.9000 | 0.8963 | 0.1977 | 60 | 0 |
| conditional_nouls | 0.8500 | 0.8576 | 0.2249 | 59 | 1 |
| evidence_contract | 0.8333 | 0.8419 | 0.2379 | 59 | 1 |
| baseline_choice | 0.7833 | 0.7932 | 0.2838 | 59 | 1 |

Selected alternative beats baseline on development macro F1: True.

| Split | Arm | Calibration | N | Errors | Accuracy | Macro F1 | Brier | Log loss | False merge |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| development | baseline_choice | raw | 60 | 1 | 0.7833 | 0.7932 | 0.2838 | 1.0192 | N/A |
| development | baseline_choice | calibrated | 60 | 1 | 0.7833 | 0.7932 | 0.2835 | 0.5135 | N/A |
| development | fewshot_contract | raw | 60 | 0 | 0.9000 | 0.8963 | 0.1977 | 0.8808 | N/A |
| development | fewshot_contract | calibrated | 60 | 0 | 0.9000 | 0.8963 | 0.2049 | 0.4936 | N/A |
| calibration | baseline_choice | raw | 150 | 1 | 0.8667 | 0.8580 | 0.2086 | 0.7950 | N/A |
| calibration | baseline_choice | calibrated | 150 | 1 | 0.8667 | 0.8580 | 0.2475 | 0.4726 | N/A |
| calibration | fewshot_contract | raw | 150 | 0 | 0.8400 | 0.8357 | 0.2360 | 0.6125 | N/A |
| calibration | fewshot_contract | calibrated | 150 | 0 | 0.8400 | 0.8357 | 0.2317 | 0.4358 | N/A |
| evaluation | baseline_choice | raw | 339 | 1 | 0.8525 | 0.8508 | 0.2340 | 1.2415 | N/A |
| evaluation | baseline_choice | calibrated | 339 | 1 | 0.8525 | 0.8508 | 0.2769 | 0.5639 | N/A |
| evaluation | fewshot_contract | raw | 339 | 2 | 0.8496 | 0.8527 | 0.2306 | 1.2401 | N/A |
| evaluation | fewshot_contract | calibrated | 339 | 2 | 0.8496 | 0.8527 | 0.2505 | 0.6256 | N/A |
| fixtures | baseline_choice | raw | 50 | 0 | 0.9200 | 0.9213 | 0.1325 | 0.2483 | N/A |
| fixtures | baseline_choice | calibrated | 50 | 0 | 0.9200 | 0.9213 | 0.1750 | 0.2714 | N/A |
| fixtures | fewshot_contract | raw | 50 | 0 | 0.9000 | 0.9015 | 0.1043 | 0.1676 | N/A |
| fixtures | fewshot_contract | calibrated | 50 | 0 | 0.9000 | 0.9015 | 0.1537 | 0.2647 | N/A |

Evaluation paired differences are selected minus baseline. Intervals condition on the fixed development choice and fitted temperatures; multiple comparisons are not corrected.

| Version | Metric | Difference | 95% interval | Paired Brier N |
|---|---|---:|---|---:|
| raw | accuracy | -0.0029 | [-0.0380, 0.0310] | 336 |
| raw | macro_f1 | 0.0019 | [-0.0314, 0.0337] | 336 |
| raw | brier_score | -0.0034 | [-0.0368, 0.0337] | 336 |
| calibrated | accuracy | -0.0029 | [-0.0380, 0.0310] | 336 |
| calibrated | macro_f1 | 0.0019 | [-0.0314, 0.0337] | 336 |
| calibrated | brier_score | -0.0250 | [-0.0462, -0.0023] | 336 |

Calibration fits:

- `baseline_choice`: T=4.8030, 149/150 calibration responses; calibration log loss 0.7950 to 0.4726.
- `fewshot_contract`: T=3.1500, 150/150 calibration responses; calibration log loss 0.6125 to 0.4358.

No resolved improvement in raw operational macro F1: the paired interval includes zero or evidence is unavailable.

## entity_resolution

Baseline: `baseline_noul`. Selected alternative: `fewshot_contract`.

| Development arm | Accuracy | Macro F1 | Brier | Probability N | Errors |
|---|---:|---:|---:|---:|---:|
| fewshot_contract | 1.0000 | 1.0000 | 0.0092 | 60 | 0 |
| identity_contract | 1.0000 | 1.0000 | 0.0192 | 60 | 0 |
| identity_noul | 1.0000 | 1.0000 | 0.0323 | 60 | 0 |
| baseline_noul | 0.9833 | 0.9819 | 0.0411 | 60 | 0 |

Selected alternative beats baseline on development macro F1: True.

| Split | Arm | Calibration | N | Errors | Accuracy | Macro F1 | Brier | Log loss | False merge |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| development | baseline_noul | raw | 60 | 0 | 0.9833 | 0.9819 | 0.0411 | 0.1163 | 0.0256 |
| development | baseline_noul | calibrated | 60 | 0 | 0.9833 | 0.9819 | 0.0161 | 0.0259 | 0.0256 |
| development | fewshot_contract | raw | 60 | 0 | 1.0000 | 1.0000 | 0.0092 | 0.0165 | 0.0000 |
| development | fewshot_contract | calibrated | 60 | 0 | 1.0000 | 1.0000 | 0.0084 | 0.0128 | 0.0000 |
| calibration | baseline_noul | raw | 390 | 0 | 0.9974 | 0.9947 | 0.0211 | 0.0824 | 0.0179 |
| calibration | baseline_noul | calibrated | 390 | 0 | 0.9974 | 0.9947 | 0.0053 | 0.0117 | 0.0179 |
| calibration | fewshot_contract | raw | 390 | 0 | 0.9949 | 0.9897 | 0.0089 | 0.0175 | 0.0000 |
| calibration | fewshot_contract | calibrated | 390 | 0 | 0.9949 | 0.9897 | 0.0082 | 0.0144 | 0.0000 |
| evaluation | baseline_noul | raw | 413 | 0 | 0.9806 | 0.9605 | 0.0408 | 0.1067 | 0.1270 |
| evaluation | baseline_noul | calibrated | 413 | 0 | 0.9806 | 0.9605 | 0.0312 | 0.0653 | 0.1270 |
| evaluation | fewshot_contract | raw | 413 | 0 | 0.9927 | 0.9859 | 0.0184 | 0.0335 | 0.0317 |
| evaluation | fewshot_contract | calibrated | 413 | 0 | 0.9927 | 0.9859 | 0.0156 | 0.0261 | 0.0317 |
| fixtures | baseline_noul | raw | 100 | 0 | 0.9545 | 0.8961 | 0.0718 | 0.1383 | 0.2500 |
| fixtures | baseline_noul | calibrated | 100 | 0 | 0.9545 | 0.8961 | 0.0826 | 0.1934 | 0.2500 |
| fixtures | fewshot_contract | raw | 100 | 0 | 0.9886 | 0.9767 | 0.0475 | 0.1233 | 0.0000 |
| fixtures | fewshot_contract | calibrated | 100 | 0 | 0.9886 | 0.9767 | 0.0353 | 0.1059 | 0.0000 |

Evaluation paired differences are selected minus baseline. Intervals condition on the fixed development choice and fitted temperatures; multiple comparisons are not corrected.

| Version | Metric | Difference | 95% interval | Paired Brier N |
|---|---|---:|---|---:|
| raw | accuracy | 0.0121 | [0.0000, 0.0242] | 413 |
| raw | macro_f1 | 0.0254 | [0.0010, 0.0540] | 413 |
| raw | brier_score | -0.0225 | [-0.0333, -0.0122] | 413 |
| raw | false_merge_rate | -0.0952 | [-0.1739, -0.0308] | 413 |
| calibrated | accuracy | 0.0121 | [0.0000, 0.0242] | 413 |
| calibrated | macro_f1 | 0.0254 | [0.0010, 0.0540] | 413 |
| calibrated | brier_score | -0.0157 | [-0.0337, -0.0004] | 413 |
| calibrated | false_merge_rate | -0.0952 | [-0.1739, -0.0308] | 413 |

Calibration fits:

- `baseline_noul`: T=0.2997, 390/390 calibration responses; calibration log loss 0.0824 to 0.0117.
- `fewshot_contract`: T=0.6239, 390/390 calibration responses; calibration log loss 0.0175 to 0.0144.

The raw selected alternative improves macro F1 with a paired 95% interval above zero on this evaluation split.

## Fresh repeatability

- entity_resolution / `baseline_noul`: 20 examples, 60 valid fresh pairwise comparisons, agreement 1.0000, 0 argmax flips, maximum total variation 0.0500; 0 fresh comparisons contain errors. Provenance: {'fresh_recorded_calls': 60}.
- entity_resolution / `fewshot_contract`: 20 examples, 60 valid fresh pairwise comparisons, agreement 1.0000, 0 argmax flips, maximum total variation 0.0900; 0 fresh comparisons contain errors. Provenance: {'fresh_recorded_calls': 60}.
- relation_support / `baseline_choice`: 20 examples, 60 valid fresh pairwise comparisons, agreement 0.9667, 2 argmax flips, maximum total variation 0.1400; 0 fresh comparisons contain errors. Provenance: {'fresh_recorded_calls': 60}.
- relation_support / `fewshot_contract`: 20 examples, 60 valid fresh pairwise comparisons, agreement 1.0000, 0 argmax flips, maximum total variation 0.2200; 0 fresh comparisons contain errors. Provenance: {'fresh_recorded_calls': 60}.

Fresh calls are identified by distinct recorded call IDs. Exact repeated outputs alone do not prove either service determinism or caching; local cached replays are not fresh-repeat evidence.

## Usage and limitations

Recorded invocations: 3405; usage reported for 3405. Input tokens: 4792778; output tokens: 139613. Estimated USD for reported usage: 0.2013. Invoice verified: no.

Reported usage summed once per logical calls.jsonl entry; shared batches are never multiplied by prediction count. HTTP attempts/retries are counted separately; usage absent from retry responses is unknown. USD is a unit-price estimate, not a verified invoice. Missing usage is unknown; summed call latency is not parallel wall time.

Frozen-plan completeness: complete.

Full input predictions, requests and responses remain in `predictions.jsonl` and `calls.jsonl`; hashes and manifest are recorded in `results.json`. Fixture scores are diagnostic, not independent natural-data evidence. Bootstrap intervals reflect sampled evaluation groups, not model-selection uncertainty. Positive-temperature calibration preserves argmax and therefore cannot itself improve accuracy.

Batching comparisons are descriptive and available in `results.json`; they do not establish a general batching-invariance guarantee.
