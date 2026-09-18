# Research tables

Generated directly from saved artifacts by `scripts/generate_tables.py`; no model calls. Full precision and additional fields are in `tables.json`.

All intervals are selected minus baseline, paired percentile 95%, 2,000 draws, seed 20260917. They are exploratory and unadjusted for multiple comparisons. SciFact resamples 247 connected components; DBLP–ACM resamples 413 identity-disjoint pairs.

## Prepared data

ER training groups are row IDs; they are not independent identity units. Calibration and evaluation were additionally reduced to identity-disjoint pairs. Only six demonstrations and 60 arm-selection examples from each prepared training split were used by Jev.

| Task | Split | Rows | Stored groups | Class counts |
| --- | --- | --- | --- | --- |
| scifact | train | 459 | 255 | {"NOT_ENOUGH_INFO": 198, "REFUTES": 82, "SUPPORTS": 179} |
| scifact | calibration | 150 | 73 | {"SUPPORTS": 65, "NOT_ENOUGH_INFO": 55, "REFUTES": 30} |
| scifact | evaluation | 339 | 247 | {"NOT_ENOUGH_INFO": 130, "SUPPORTS": 138, "REFUTES": 71} |
| entity_resolution | train | 4592 | 4592 | {"different": 3283, "same": 1309} |
| entity_resolution | calibration | 390 | 390 | {"same": 334, "different": 56} |
| entity_resolution | evaluation | 413 | 413 | {"same": 350, "different": 63} |

## All development arms

Each arm has 60 eligible examples. Selection excludes baseline, ranks operational macro-F1, then Brier, then arm name. ER three-way perfect-F1 tie is resolved by Brier.

| Task | Arm | Selected | Accuracy | Macro-F1 | Brier | Errors | Probability n |
| --- | --- | --- | --- | --- | --- | --- | --- |
| relation_support | fewshot_contract | True | 0.900000 | 0.896326 | 0.197747 | 0 | 60 |
| relation_support | conditional_nouls | False | 0.850000 | 0.857647 | 0.224898 | 1 | 59 |
| relation_support | evidence_contract | False | 0.833333 | 0.841898 | 0.237892 | 1 | 59 |
| relation_support | baseline_choice | False | 0.783333 | 0.793190 | 0.283783 | 1 | 59 |
| entity_resolution | fewshot_contract | True | 1.000000 | 1.000000 | 0.009207 | 0 | 60 |
| entity_resolution | identity_contract | False | 1.000000 | 1.000000 | 0.019247 | 0 | 60 |
| entity_resolution | identity_noul | False | 1.000000 | 1.000000 | 0.032307 | 0 | 60 |
| entity_resolution | baseline_noul | False | 0.983333 | 0.981879 | 0.041057 | 0 | 60 |

## Held-out classification and probability scores

Operational classification retains service failures. Probability scores use valid responses only. Brier is the sum over every class (range 0–2), including both ER coordinates. Scalar calibration preserves predicted labels.

| Task | Arm | Version | Eligible n | Errors | Probability n | Accuracy | Macro-F1 | Brier | Log loss |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| relation_support | baseline_choice | raw | 339 | 1 | 338 | 0.852507 | 0.850824 | 0.233967 | 1.241526 |
| relation_support | baseline_choice | calibrated | 339 | 1 | 338 | 0.852507 | 0.850824 | 0.276930 | 0.563853 |
| relation_support | fewshot_contract | raw | 339 | 2 | 337 | 0.849558 | 0.852728 | 0.230552 | 1.240099 |
| relation_support | fewshot_contract | calibrated | 339 | 2 | 337 | 0.849558 | 0.852728 | 0.250530 | 0.625570 |
| entity_resolution | baseline_noul | raw | 413 | 0 | 413 | 0.980630 | 0.960452 | 0.040836 | 0.106685 |
| entity_resolution | baseline_noul | calibrated | 413 | 0 | 413 | 0.980630 | 0.960452 | 0.031248 | 0.065346 |
| entity_resolution | fewshot_contract | raw | 413 | 0 | 413 | 0.992736 | 0.985860 | 0.018384 | 0.033516 |
| entity_resolution | fewshot_contract | calibrated | 413 | 0 | 413 | 0.992736 | 0.985860 | 0.015583 | 0.026094 |

## Paired held-out effects

Brier effects use common-success pairs; classification effects retain all eligible rows, including errors. A negative Brier or false-merge-rate effect is an improvement. ER accuracy interval includes zero; ER macro-F1 interval excludes zero on this split. Relation macro-F1 is unresolved.

| Task | Version | Metric | Difference | 95% interval | Common-success n |
| --- | --- | --- | --- | --- | --- |
| relation_support | raw | accuracy | -0.002950 | [-0.038017, 0.030960] | 336 |
| relation_support | raw | macro_f1 | 0.001904 | [-0.031390, 0.033734] | 336 |
| relation_support | raw | brier_score | -0.003358 | [-0.036781, 0.033750] | 336 |
| relation_support | calibrated | accuracy | -0.002950 | [-0.038017, 0.030960] | 336 |
| relation_support | calibrated | macro_f1 | 0.001904 | [-0.031390, 0.033734] | 336 |
| relation_support | calibrated | brier_score | -0.025005 | [-0.046170, -0.002326] | 336 |
| entity_resolution | raw | accuracy | 0.012107 | [0.000000, 0.024213] | 413 |
| entity_resolution | raw | macro_f1 | 0.025408 | [0.000960, 0.053964] | 413 |
| entity_resolution | raw | brier_score | -0.022453 | [-0.033325, -0.012205] | 413 |
| entity_resolution | raw | false_merge_rate | -0.095238 | [-0.173930, -0.030758] | 413 |
| entity_resolution | calibrated | accuracy | 0.012107 | [0.000000, 0.024213] | 413 |
| entity_resolution | calibrated | macro_f1 | 0.025408 | [0.000960, 0.053964] | 413 |
| entity_resolution | calibrated | brier_score | -0.015665 | [-0.033694, -0.000369] | 413 |
| entity_resolution | calibrated | false_merge_rate | -0.095238 | [-0.173930, -0.030758] | 413 |

## Calibration fits

Fits use calibration labels only. None reaches a boundary. Improvement in fitted calibration log loss is not independent test evidence.

| Task | Arm | Planned n | Fit n | T | Raw log loss | Fitted log loss | Boundary |
| --- | --- | --- | --- | --- | --- | --- | --- |
| relation_support | baseline_choice | 150 | 149 | 4.803020 | 0.794987 | 0.472579 | — |
| relation_support | fewshot_contract | 150 | 150 | 3.149975 | 0.612474 | 0.435796 | — |
| entity_resolution | baseline_noul | 390 | 390 | 0.299708 | 0.082399 | 0.011739 | — |
| entity_resolution | fewshot_contract | 390 | 390 | 0.623887 | 0.017512 | 0.014384 | — |

## Secondary fixtures

Fixtures have prior development use and unadjudicated labels. The 12 uncertain ER cases are retained but excluded from binary correctness and probability scores.

| Task | Arm | Total n | Eligible n | Excluded gold | Accuracy | Macro-F1 | False merges | Negative n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| relation_support | baseline_choice | 50 | 50 | 0 | 0.920000 | 0.921296 | — | — |
| relation_support | fewshot_contract | 50 | 50 | 0 | 0.900000 | 0.901479 | — | — |
| entity_resolution | baseline_noul | 100 | 88 | 12 | 0.954545 | 0.896104 | 3 | 12 |
| entity_resolution | fewshot_contract | 100 | 88 | 12 | 0.988636 | 0.976689 | 0 | 12 |

## Fresh repeated calls

Three fresh responses for each of 20 examples produce 60 pair comparisons per arm; those 60 comparisons are dependent. Round zero reuses the original evaluation call with identical payload. Immediate calls do not establish long-term determinism.

| Task | Arm | Examples | All-three labels equal | Valid pair comparisons | Exact vectors equal | Label agreement | Mean TV | Max TV |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| entity_resolution | baseline_noul | 20 | 20 | 60 | 32 | 1.000000 | 0.008333 | 0.050000 |
| entity_resolution | fewshot_contract | 20 | 20 | 60 | 51 | 1.000000 | 0.006000 | 0.090000 |
| relation_support | baseline_choice | 20 | 19 | 60 | 35 | 0.966667 | 0.011000 | 0.140000 |
| relation_support | fewshot_contract | 20 | 20 | 60 | 27 | 1.000000 | 0.020667 | 0.220000 |

## Development batching control

Exploratory batched versus separate calls on development examples. These controls do not select arms or establish accuracy on a new test set.

| Task | Arm | Pairs | Errors | Label agreement | Exact vectors equal | Max TV |
| --- | --- | --- | --- | --- | --- | --- |
| entity_resolution | baseline_noul | 20 | 0 | 1.000000 | 11 | 0.020000 |
| entity_resolution | identity_contract | 20 | 0 | 1.000000 | 16 | 0.060000 |
| entity_resolution | identity_noul | 20 | 0 | 1.000000 | 11 | 0.040000 |
| relation_support | baseline_choice | 20 | 0 | 1.000000 | 14 | 0.030000 |
| relation_support | conditional_nouls | 20 | 0 | 1.000000 | 7 | 0.025800 |
| relation_support | evidence_contract | 20 | 0 | 1.000000 | 15 | 0.070000 |

## Usage and timing

Usage includes the toy preflight and failed requests. Total call latency sums overlapping requests and is not elapsed wall time. Cost is an estimate using the frozen price snapshot, not a provider invoice or complete-pipeline cost.

| Measure | Value |
| --- | --- |
| n_calls | 3405 |
| n_http_attempts | 3405 |
| n_retries | 0 |
| unknown_usage_attempts | 0 |
| budget_input_token_charge | 4792778 |
| n_questions_in_recorded_payloads | 3726 |
| n_calls_with_usage | 3405 |
| n_calls_missing_usage | 0 |
| reported_input_tokens | 4792778 |
| reported_output_tokens | 139613 |
| reported_total_tokens | 4932391 |
| n_failed_calls | 5 |
| sum_call_latency_ms | 1454044.099100 |
| mean_call_latency_ms | 427.032041 |
| latency_denominator | 3405 |
| recorded_stage_wall_seconds | 378.474118 |
| estimated_usd_for_reported_usage | 0.201297 |
| estimate_complete | True |
| invoice_verified | False |
| note | Reported usage summed once per logical calls.jsonl entry; shared batches are never multiplied by prediction count. HTTP attempts/retries are counted separately; usage absent from retry responses is unknown. USD is a unit-price estimate, not a verified invoice. Missing usage is unknown; summed call latency is not parallel wall time. |

## Raw confusion counts

| Task | Split | Arm | Gold | Prediction | Count |
| --- | --- | --- | --- | --- | --- |
| relation_support | evaluation | baseline_choice | SUPPORTS | SUPPORTS | 122 |
| relation_support | evaluation | baseline_choice | SUPPORTS | REFUTES | 6 |
| relation_support | evaluation | baseline_choice | SUPPORTS | NOT_ENOUGH_INFO | 10 |
| relation_support | evaluation | baseline_choice | SUPPORTS | ERROR | 0 |
| relation_support | evaluation | baseline_choice | REFUTES | SUPPORTS | 4 |
| relation_support | evaluation | baseline_choice | REFUTES | REFUTES | 65 |
| relation_support | evaluation | baseline_choice | REFUTES | NOT_ENOUGH_INFO | 2 |
| relation_support | evaluation | baseline_choice | REFUTES | ERROR | 0 |
| relation_support | evaluation | baseline_choice | NOT_ENOUGH_INFO | SUPPORTS | 14 |
| relation_support | evaluation | baseline_choice | NOT_ENOUGH_INFO | REFUTES | 13 |
| relation_support | evaluation | baseline_choice | NOT_ENOUGH_INFO | NOT_ENOUGH_INFO | 102 |
| relation_support | evaluation | baseline_choice | NOT_ENOUGH_INFO | ERROR | 1 |
| relation_support | evaluation | fewshot_contract | SUPPORTS | SUPPORTS | 110 |
| relation_support | evaluation | fewshot_contract | SUPPORTS | REFUTES | 5 |
| relation_support | evaluation | fewshot_contract | SUPPORTS | NOT_ENOUGH_INFO | 22 |
| relation_support | evaluation | fewshot_contract | SUPPORTS | ERROR | 1 |
| relation_support | evaluation | fewshot_contract | REFUTES | SUPPORTS | 2 |
| relation_support | evaluation | fewshot_contract | REFUTES | REFUTES | 62 |
| relation_support | evaluation | fewshot_contract | REFUTES | NOT_ENOUGH_INFO | 7 |
| relation_support | evaluation | fewshot_contract | REFUTES | ERROR | 0 |
| relation_support | evaluation | fewshot_contract | NOT_ENOUGH_INFO | SUPPORTS | 6 |
| relation_support | evaluation | fewshot_contract | NOT_ENOUGH_INFO | REFUTES | 7 |
| relation_support | evaluation | fewshot_contract | NOT_ENOUGH_INFO | NOT_ENOUGH_INFO | 116 |
| relation_support | evaluation | fewshot_contract | NOT_ENOUGH_INFO | ERROR | 1 |
| relation_support | fixtures | baseline_choice | SUPPORTS | SUPPORTS | 15 |
| relation_support | fixtures | baseline_choice | SUPPORTS | REFUTES | 0 |
| relation_support | fixtures | baseline_choice | SUPPORTS | NOT_ENOUGH_INFO | 0 |
| relation_support | fixtures | baseline_choice | SUPPORTS | ERROR | 0 |
| relation_support | fixtures | baseline_choice | REFUTES | SUPPORTS | 0 |
| relation_support | fixtures | baseline_choice | REFUTES | REFUTES | 15 |
| relation_support | fixtures | baseline_choice | REFUTES | NOT_ENOUGH_INFO | 0 |
| relation_support | fixtures | baseline_choice | REFUTES | ERROR | 0 |
| relation_support | fixtures | baseline_choice | NOT_ENOUGH_INFO | SUPPORTS | 2 |
| relation_support | fixtures | baseline_choice | NOT_ENOUGH_INFO | REFUTES | 2 |
| relation_support | fixtures | baseline_choice | NOT_ENOUGH_INFO | NOT_ENOUGH_INFO | 16 |
| relation_support | fixtures | baseline_choice | NOT_ENOUGH_INFO | ERROR | 0 |
| relation_support | fixtures | fewshot_contract | SUPPORTS | SUPPORTS | 12 |
| relation_support | fixtures | fewshot_contract | SUPPORTS | REFUTES | 0 |
| relation_support | fixtures | fewshot_contract | SUPPORTS | NOT_ENOUGH_INFO | 3 |
| relation_support | fixtures | fewshot_contract | SUPPORTS | ERROR | 0 |
| relation_support | fixtures | fewshot_contract | REFUTES | SUPPORTS | 0 |
| relation_support | fixtures | fewshot_contract | REFUTES | REFUTES | 15 |
| relation_support | fixtures | fewshot_contract | REFUTES | NOT_ENOUGH_INFO | 0 |
| relation_support | fixtures | fewshot_contract | REFUTES | ERROR | 0 |
| relation_support | fixtures | fewshot_contract | NOT_ENOUGH_INFO | SUPPORTS | 0 |
| relation_support | fixtures | fewshot_contract | NOT_ENOUGH_INFO | REFUTES | 2 |
| relation_support | fixtures | fewshot_contract | NOT_ENOUGH_INFO | NOT_ENOUGH_INFO | 18 |
| relation_support | fixtures | fewshot_contract | NOT_ENOUGH_INFO | ERROR | 0 |
| entity_resolution | evaluation | baseline_noul | same | same | 350 |
| entity_resolution | evaluation | baseline_noul | same | different | 0 |
| entity_resolution | evaluation | baseline_noul | same | ERROR | 0 |
| entity_resolution | evaluation | baseline_noul | different | same | 8 |
| entity_resolution | evaluation | baseline_noul | different | different | 55 |
| entity_resolution | evaluation | baseline_noul | different | ERROR | 0 |
| entity_resolution | evaluation | fewshot_contract | same | same | 349 |
| entity_resolution | evaluation | fewshot_contract | same | different | 1 |
| entity_resolution | evaluation | fewshot_contract | same | ERROR | 0 |
| entity_resolution | evaluation | fewshot_contract | different | same | 2 |
| entity_resolution | evaluation | fewshot_contract | different | different | 61 |
| entity_resolution | evaluation | fewshot_contract | different | ERROR | 0 |
| entity_resolution | fixtures | baseline_noul | same | same | 75 |
| entity_resolution | fixtures | baseline_noul | same | different | 1 |
| entity_resolution | fixtures | baseline_noul | same | ERROR | 0 |
| entity_resolution | fixtures | baseline_noul | different | same | 3 |
| entity_resolution | fixtures | baseline_noul | different | different | 9 |
| entity_resolution | fixtures | baseline_noul | different | ERROR | 0 |
| entity_resolution | fixtures | fewshot_contract | same | same | 75 |
| entity_resolution | fixtures | fewshot_contract | same | different | 1 |
| entity_resolution | fixtures | fewshot_contract | same | ERROR | 0 |
| entity_resolution | fixtures | fewshot_contract | different | same | 0 |
| entity_resolution | fixtures | fewshot_contract | different | different | 12 |
| entity_resolution | fixtures | fewshot_contract | different | ERROR | 0 |
