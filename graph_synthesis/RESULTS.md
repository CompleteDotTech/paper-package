# Executed graph study results

Post-hoc frozen-inference replay. No fresh model calls. Full JSON: `results/graph-study.json.gz`.

## Actual graph contents

| Task | Arm | Nodes | Accepted assertions | Correct labels | Incorrect labels | Isolates | Weak components |
|---|---|---:|---:|---:|---:|---:|---:|
| entity_resolution | baseline_noul | 826 | 413 | 405 | 8 | 0 | 413 |
| entity_resolution | fewshot_contract | 826 | 413 | 410 | 3 | 0 | 413 |
| relation_support | baseline_choice | 583 | 224 | 187 | 37 | 180 | 362 |
| relation_support | fewshot_contract | 583 | 192 | 172 | 20 | 241 | 394 |

Correctness is measured against original supplied-pair labels, not independently adjudicated world truth. Entity graphs include both same and different assertions; claims with insufficient evidence are not asserted.

## Equal accepted primary-action counts

| Task | Count per arm | Baseline correct / incorrect | Selected correct / incorrect | Precision difference 95% bootstrap interval |
|---|---:|---|---|---|
| entity_resolution | 351 | 347 / 4 | 349 / 2 | [0.000000, 0.014646] |
| relation_support | 118 | 109 / 9 | 110 / 8 | [-0.027081, 0.048247] |

Both intervals include zero. The selected sets are score-ranked without gold; these are post-hoc conditional, unadjusted intervals, not a new confirmatory benchmark.

## Acceptance policy

No arm obtains a qualified 1% false-positive operating threshold. The identity calibration has too few negative units for the fixed-grid requirement. SciFact calibration repeats components and is explicitly not qualified by independent-binomial row bounds.

## Lifecycle

Each of the four graph stores passed source-withdrawal and durable-reopen checks. The relation graphs removed five incident assertions each; the identity graphs removed one each. All original assertions remain in history. Multi-step cascades are separately covered by 30 synthetic dependency-DAG controls, not claimed as naturally observed retractions.
