# Archived-output calibration check

**Zero fresh model calls. Zero DSPy runs. This is not the requested live comparison.** Invalid archived responses are excluded from probability metrics and listed in summary.json; accuracy is conditional on a valid response, not end-to-end accuracy.

Calibrators were refit using only the archived calibration split. All three fixed methods are shown; none was selected using test performance. The archived evaluation split was historically examined, so these are exploratory results.

| Task | Historical arm | Calibration | n | Accuracy | Macro-F1 | Brier | Log loss | ECE |
|---|---|---|---:|---:|---:|---:|---:|---:|
| relation_support | baseline_choice | raw | 338 | 0.846154 | 0.844335 | 0.234192 | 1.240206 | 0.074408 |
| relation_support | baseline_choice | temperature | 338 | 0.846154 | 0.844335 | 0.272597 | 0.569980 | 0.120948 |
| relation_support | baseline_choice | bias_temperature | 338 | 0.828402 | 0.817346 | 0.261256 | 0.532340 | 0.096751 |
| relation_support | fewshot_contract | raw | 337 | 0.860534 | 0.859685 | 0.224429 | 1.320742 | 0.068843 |
| relation_support | fewshot_contract | temperature | 337 | 0.860534 | 0.859685 | 0.256077 | 0.632292 | 0.131532 |
| relation_support | fewshot_contract | bias_temperature | 337 | 0.759644 | 0.756568 | 0.282491 | 0.574257 | 0.107833 |
| entity_resolution | baseline_noul | raw | 413 | 0.980630 | 0.960452 | 0.040651 | 0.106744 | 0.064504 |
| entity_resolution | baseline_noul | temperature | 413 | 0.980630 | 0.960452 | 0.031287 | 0.065248 | 0.013925 |
| entity_resolution | baseline_noul | bias_temperature | 413 | 0.983051 | 0.965638 | 0.028751 | 0.059969 | 0.013186 |
| entity_resolution | fewshot_contract | raw | 413 | 0.987893 | 0.976434 | 0.018150 | 0.033291 | 0.015036 |
| entity_resolution | fewshot_contract | temperature | 413 | 0.987893 | 0.976434 | 0.015705 | 0.026191 | 0.009182 |
| entity_resolution | fewshot_contract | bias_temperature | 413 | 0.987893 | 0.975793 | 0.017257 | 0.028161 | 0.003360 |

Temperature scaling preserves decisions; its accuracy differences must be zero. Bias/temperature can change decisions. A probability-quality improvement is not necessarily an accuracy improvement.

Source SHA-256: `9fc0f0a345f6fbbd311759a5143c1d1be62313b72e26acd54e3ae289e040d76f`
