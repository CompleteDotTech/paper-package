# Repeated DSPy / Jev benchmark comparison

Completed full DSPy runs: **5/5**.
Full five-seed matrix: **complete**.
Completed baseline-only runs: **0/5**.

Previously published observations are not relabeled as fresh runs. A missing or failed run is not an accuracy score. Five evaluations on the same test set are repeated model/search runs, not five independent datasets.

| Seed | Status |
|---|---|
| 11 | completed |
| 23 | completed |
| 37 | completed |
| 53 | completed |
| 71 | completed |

## Primary test results

| Task | Arm | Calibration | Runs | Accuracy | Macro-F1 | Brier | Log loss | ECE |
|---|---|---|---:|---:|---:|---:|---:|---:|
| entity_resolution | dspy_accuracy | bias_temperature_1.0 | 5 | 0.985956 | 0.972232 | 0.021646 | 0.046210 | 0.006989 |
| entity_resolution | dspy_accuracy | raw_1.0 | 5 | 0.981598 | 0.964970 | 0.040846 | 0.082011 | 0.039869 |
| entity_resolution | dspy_accuracy | temperature_1.0 | 5 | 0.981598 | 0.964970 | 0.029518 | 0.062119 | 0.010250 |
| entity_resolution | dspy_composite | bias_temperature_1.0 | 5 | 0.989346 | 0.979117 | 0.017133 | 0.047025 | 0.007779 |
| entity_resolution | dspy_composite | raw_1.0 | 5 | 0.984988 | 0.971377 | 0.024946 | 0.061222 | 0.016910 |
| entity_resolution | dspy_composite | temperature_1.0 | 5 | 0.984988 | 0.971377 | 0.022313 | 0.056833 | 0.008117 |
| entity_resolution | without_dspy_baseline_noul | bias_temperature_1.0 | 5 | 0.981598 | 0.962526 | 0.032950 | 0.079694 | 0.015480 |
| entity_resolution | without_dspy_baseline_noul | raw_1.0 | 5 | 0.981114 | 0.961489 | 0.044195 | 0.113420 | 0.066015 |
| entity_resolution | without_dspy_baseline_noul | temperature_1.0 | 5 | 0.981114 | 0.961489 | 0.033801 | 0.081432 | 0.015789 |
| entity_resolution | without_dspy_fewshot_contract | bias_temperature_1.0 | 5 | 0.984988 | 0.969823 | 0.021609 | 0.035667 | 0.004959 |
| entity_resolution | without_dspy_fewshot_contract | raw_1.0 | 5 | 0.987409 | 0.975174 | 0.022391 | 0.039061 | 0.013123 |
| entity_resolution | without_dspy_fewshot_contract | temperature_1.0 | 5 | 0.987409 | 0.975174 | 0.020515 | 0.033787 | 0.008739 |
| entity_resolution | without_dspy_identity_contract | bias_temperature_1.0 | 5 | 0.983051 | 0.966566 | 0.024365 | 0.052203 | 0.006707 |
| entity_resolution | without_dspy_identity_contract | raw_1.0 | 5 | 0.979177 | 0.960298 | 0.047015 | 0.093531 | 0.043201 |
| entity_resolution | without_dspy_identity_contract | temperature_1.0 | 5 | 0.979177 | 0.960298 | 0.035757 | 0.074609 | 0.013207 |
| entity_resolution | without_dspy_identity_noul | bias_temperature_1.0 | 5 | 0.986925 | 0.974065 | 0.023417 | 0.050154 | 0.007578 |
| entity_resolution | without_dspy_identity_noul | raw_1.0 | 5 | 0.978208 | 0.958129 | 0.072489 | 0.150548 | 0.097918 |
| entity_resolution | without_dspy_identity_noul | temperature_1.0 | 5 | 0.978208 | 0.958129 | 0.035836 | 0.069835 | 0.011082 |
| relation_support | dspy_accuracy | bias_temperature_1.0 | 5 | 0.835398 | 0.829677 | 0.241380 | 0.599111 | 0.048490 |
| relation_support | dspy_accuracy | raw_1.0 | 5 | 0.846018 | 0.843832 | 0.253073 | 1.334751 | 0.080112 |
| relation_support | dspy_accuracy | temperature_1.0 | 5 | 0.846018 | 0.843832 | 0.273941 | 0.674977 | 0.100808 |
| relation_support | dspy_composite | bias_temperature_1.0 | 5 | 0.792330 | 0.787779 | 0.273857 | 0.501347 | 0.064047 |
| relation_support | dspy_composite | raw_1.0 | 5 | 0.857817 | 0.855482 | 0.242223 | 1.136000 | 0.079009 |
| relation_support | dspy_composite | temperature_1.0 | 5 | 0.857817 | 0.855482 | 0.301102 | 0.556353 | 0.163939 |
| relation_support | without_dspy_baseline_choice | bias_temperature_1.0 | 5 | 0.823009 | 0.807119 | 0.272380 | 0.527350 | 0.097390 |
| relation_support | without_dspy_baseline_choice | raw_1.0 | 5 | 0.849558 | 0.846900 | 0.233667 | 1.255837 | 0.076012 |
| relation_support | without_dspy_baseline_choice | temperature_1.0 | 5 | 0.849558 | 0.846900 | 0.285982 | 0.561722 | 0.138228 |
| relation_support | without_dspy_conditional_nouls | bias_temperature_1.0 | 5 | 0.845428 | 0.843321 | 0.231156 | 0.431300 | 0.029499 |
| relation_support | without_dspy_conditional_nouls | raw_1.0 | 5 | 0.848968 | 0.849085 | 0.247912 | 0.481139 | 0.083581 |
| relation_support | without_dspy_conditional_nouls | temperature_1.0 | 5 | 0.848968 | 0.849085 | 0.235049 | 0.460040 | 0.032593 |
| relation_support | without_dspy_evidence_contract | bias_temperature_1.0 | 5 | 0.844248 | 0.836798 | 0.245300 | 0.606601 | 0.059550 |
| relation_support | without_dspy_evidence_contract | raw_1.0 | 5 | 0.856637 | 0.855368 | 0.237755 | 1.254670 | 0.077752 |
| relation_support | without_dspy_evidence_contract | temperature_1.0 | 5 | 0.856637 | 0.855368 | 0.253737 | 0.665151 | 0.101752 |
| relation_support | without_dspy_fewshot_contract | bias_temperature_1.0 | 5 | 0.778761 | 0.774245 | 0.278962 | 0.575976 | 0.091095 |
| relation_support | without_dspy_fewshot_contract | raw_1.0 | 5 | 0.860177 | 0.858405 | 0.225932 | 1.282738 | 0.070324 |
| relation_support | without_dspy_fewshot_contract | temperature_1.0 | 5 | 0.860177 | 0.858405 | 0.259853 | 0.624301 | 0.132639 |

## Interpretation boundaries

Accuracy/composite search and post-hoc calibration are separate interventions. Temperature scaling leaves predicted labels unchanged; bias/temperature may change labels. Calibration uses only the original calibration split. Published synthetic fixtures and the semantic challenge are exploratory transfer panels, not new independent gold labels. Twelve uncertain entity fixtures have no label in the binary schema and are excluded from accuracy denominators, but their predictions remain in the raw records.

The implementation is the repository's custom DSPy proposal loop, not GEPA or MIPROv2. No test-score winner is selected across seeds. Broad superiority or a global accuracy optimum cannot be inferred from this finite search.
