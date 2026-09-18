# NLI research results

Unchanged pinned DeBERTa checkpoint; real CUDA inference. These are supplied-cited-abstract classification experiments, not retrieval or leaderboard scores.

| Arm | Accuracy | Macro F1 | Sum Brier | Log loss | Rationale sentence recall |
|---|---:|---:|---:|---:|---:|
| full | 0.4720 | 0.4166 | 0.9496 | 2.4649 | 0.9262 |
| full_calibrated | 0.4720 | 0.4166 | 0.6136 | 1.0201 | 0.9262 |
| selected | 0.4897 | 0.4420 | 0.9094 | 2.3790 | 0.9235 |
| selected_calibrated | 0.4897 | 0.4420 | 0.6043 | 1.0066 | 0.9235 |
| prefix80 | 0.4041 | 0.3199 | 1.1453 | 4.0595 | 0.0000 |
| wrong_hypothesis | 0.3805 | 0.2047 | 1.2072 | 3.9314 | 0.9290 |
| train_prior | 0.3835 | 0.1848 | 0.6469 | 1.0665 | N/A |

One duplicated source citation was removed: the final evaluation contains 339 unique claim-document pairs. Metrics and group intervals were recomputed offline from unchanged cached model outputs; training, calibration and retained input hashes were verified unchanged. The 340-row intermediate artifact is archived and is not the reported evaluation.

Temperatures were fitted only on the separate calibration split; the prior only on training labels. Selection uses training-IDF lexical overlap and no rationale annotations. Rationale recall is measured after the model's 512-token truncation.

| Paired comparison | Accuracy delta [95% group CI] | Brier delta [95% group CI] |
|---|---:|---:|
| full minus train_prior | +0.0885 [+0.0397, +0.1350] | +0.3027 [+0.1931, +0.4126] |
| full minus prefix80 | +0.0678 [+0.0147, +0.1223] | -0.1957 [-0.2850, -0.1023] |
| full minus wrong_hypothesis | +0.0914 [+0.0444, +0.1368] | -0.2576 [-0.3445, -0.1717] |
| selected minus full | +0.0177 [+0.0000, +0.0396] | -0.0402 [-0.0802, -0.0110] |
| full_calibrated minus full | +0.0000 [+0.0000, +0.0000] | -0.3360 [-0.4144, -0.2567] |
| selected_calibrated minus selected | +0.0000 [+0.0000, +0.0000] | -0.3051 [-0.3785, -0.2288] |

Higher accuracy and lower Brier are better. Intervals resample connected claim/document/duplicate-abstract groups. Intervals containing zero do not establish an improvement in that metric. Calibration is not expected to change argmax accuracy.

Full logits, errors/coverage, per-class confusion, reliability bins, calibration records, source hashes, pinned model/dependency versions, timing and legacy binary diagnostics are in [nli_results.json](nli_results.json).

Data: {"calibration": {"groups": 73, "labels": {"NOT_ENOUGH_INFO": 55, "REFUTES": 30, "SUPPORTS": 65}, "row_ids_sha256": "4341381c347f4429662518e35d429d6a0d1bcdbd20a882b480eae73b2aca4193", "rows": 150}, "evaluation": {"groups": 247, "labels": {"NOT_ENOUGH_INFO": 130, "REFUTES": 71, "SUPPORTS": 138}, "row_ids_sha256": "8b572ea59b9bc782238df3993f607173641f57324a9f1a6ea00d365a685fa392", "rows": 339}, "train": {"groups": 255, "labels": {"NOT_ENOUGH_INFO": 198, "REFUTES": 82, "SUPPORTS": 179}, "row_ids_sha256": "fd9c235ca5f2bcd4a41c28ebc3bab7cecdf92ca700c621c800df6bd61e1e59c7", "rows": 459}}

Limitations: Cited-abstract classification only; not document retrieval or an official SciFact leaderboard result. One unchanged public checkpoint and one fixed held-out split; no cross-domain guarantee. Rationale retention is complete-sentence recall after tokenization, not verified causal attribution. Legacy binary diagnostics are incompatible with the three-class task and excluded from primary comparisons. Group-bootstrap intervals condition on fixed model, training split and fitted temperatures; multiplicity is not corrected. Local inference uses measured device time; monetary compute cost was not estimated.
