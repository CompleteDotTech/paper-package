# Data-quality and optimizer diagnostics

These descriptive analyses use completed captures only. They do not change prompts, selected seeds, calibration fits or primary results.

| Task / formulation | Distinct final configurations | Accuracy seeds retaining baseline | Choice answers with mass defect | Largest mass defect |
|---|---:|---|---:|---:|
| entity_resolution / baseline_noul | 6 | [17, 43, 101] | 0 | 0 |
| entity_resolution / fewshot_contract | 3 | [17, 29, 43, 71, 101] | 0 | 0 |
| entity_resolution / identity_contract | 6 | [29] | 0 | 0 |
| entity_resolution / identity_noul | 8 | [] | 0 | 0 |
| relation_support / baseline_choice | 1 | [17, 29, 43, 71, 101] | 23 | 0.01 |
| relation_support / conditional_nouls | 1 | [17, 29, 43, 71, 101] | 0 | 0 |
| relation_support / evidence_contract | 1 | [17, 29, 43, 71, 101] | 20 | 0.01 |
| relation_support / fewshot_contract | 1 | [17, 29, 43, 71, 101] | 13 | 0.01 |

Identical question payloads can yield slightly different probabilities within the same request. `quality-diagnostics.json` quantifies those differences and any label disagreements. A difference between two unchanged prompts must not be attributed to successful prompt optimization.

The primary analysis uses the bounded normalization rule fixed in amendment v2. `strict-mass-subset-results.json` is a sensitivity analysis excluding a row for every variant when any variant returned a non-unit-sum Choice vector on that row. Calibrators are not refit. This common subset avoids comparing different subsets across methods, but remains a post-hoc selected data-quality subset.

Convergence figures contain only validation scores. Reliability figures pool descriptive predictions across five searches but do not treat those repeated predictions as independent new examples or display inferential confidence intervals.
