# Controlled synthetic research results

These are reproducible mechanism experiments, not real-model or biomedical results.

Run: `python -m pgc.research.advanced_experiments`.

## E5: source dependence

| Policy | Brier (one coordinate) | Log loss | Accuracy |
|---|---:|---:|---:|
| naive | 0.2542 | 3.3067 | 0.723 |
| exact_dedup | 0.1823 | 0.7688 | 0.763 |
| grouped | 0.1485 | 0.4601 | 0.800 |
| wrong_all_sources_one_group | 0.1789 | 0.5437 | 0.763 |

Exact-copy invariance, independent corroboration, and contradiction sensitivity are recorded in JSON. Known source grouping is an assumption; incorrectly collapsing origins loses information.

## E7: exact small-component identity inference

| Condition | Policy | Pairwise F1 | False merge rate | Transitivity violations | Hard-rule violations |
|---|---|---:|---:|---:|---:|
| coherent_control | independent | 1.000 | 0.000 | 0.00 | 0.00 |
| coherent_control | union_find | 1.000 | 0.000 | 0.00 | 0.00 |
| coherent_control | reject_conflict | 1.000 | 0.000 | 0.00 | 0.00 |
| coherent_control | joint_exact | 1.000 | 0.000 | 0.00 | 0.00 |
| noisy_bridges | independent | 0.769 | 0.222 | 6.96 | 0.23 |
| noisy_bridges | union_find | 0.571 | 1.000 | 0.00 | 1.00 |
| noisy_bridges | reject_conflict | 0.710 | 0.029 | 0.00 | 0.00 |
| noisy_bridges | joint_exact | 0.913 | 0.021 | 0.00 | 0.00 |
| misspecified_hard_rule | independent | 1.000 | 0.000 | 0.00 | 1.00 |
| misspecified_hard_rule | union_find | 1.000 | 0.000 | 0.00 | 1.00 |
| misspecified_hard_rule | reject_conflict | 0.800 | 0.000 | 0.00 | 0.00 |
| misspecified_hard_rule | joint_exact | 0.800 | 0.000 | 0.00 | 0.00 |

All 15 pair scores are held fixed across policies. Wrong hard rules are deliberately included. Exact inference enumerates 203 partitions per six-entity component; this implementation is bounded to eight entities.

## E8: dependency risk at 50% episode coverage

| Coupling / sharing | Policy | Expected corruption given commit | Accepted mutations / episode |
|---|---|---:|---:|
| independent:shared_identity=False | single | 0.419 | 2.02 |
| independent:shared_identity=False | product | 0.379 | 2.02 |
| independent:shared_identity=False | union | 0.379 | 2.02 |
| independent:shared_identity=True | single | 0.230 | 1.98 |
| independent:shared_identity=True | product | 0.204 | 1.98 |
| independent:shared_identity=True | union | 0.204 | 1.98 |
| positive_shared_noise:shared_identity=False | single | 0.143 | 2.04 |
| positive_shared_noise:shared_identity=False | product | 0.127 | 2.04 |
| positive_shared_noise:shared_identity=False | union | 0.128 | 2.04 |
| positive_shared_noise:shared_identity=True | single | 0.107 | 1.99 |
| positive_shared_noise:shared_identity=True | product | 0.083 | 1.99 |
| positive_shared_noise:shared_identity=True | union | 0.084 | 1.99 |
| maximally_disjoint_failures:shared_identity=False | single | 0.523 | 1.94 |
| maximally_disjoint_failures:shared_identity=False | product | 0.443 | 1.94 |
| maximally_disjoint_failures:shared_identity=False | union | 0.443 | 1.94 |
| maximally_disjoint_failures:shared_identity=True | single | 0.262 | 1.94 |
| maximally_disjoint_failures:shared_identity=True | product | 0.219 | 1.94 |
| maximally_disjoint_failures:shared_identity=True | union | 0.219 | 1.94 |

Primary tables match both accepted episode and mutation counts by stratifying on transaction size. The JSON also gives 25%, 75%, and 100% coverage, episode-only matching, fixed risk thresholds, realized corruption, and damaged facts. Union bounds stay valid under the synthetic dependence structures but can reject almost everything at a strict threshold. Products underestimate disjoint failures. Neither uses estimated neural probabilities here.

## E8: routing at five queries per 20 decisions

| Condition | Policy | Weighted error / decision | Accuracy | Coverage |
|---|---|---:|---:|---:|
| heterogeneous_specialist | random | 7.007 | 0.757 | 1.0 |
| heterogeneous_specialist | confidence | 5.348 | 0.810 | 1.0 |
| heterogeneous_specialist | impact | 6.029 | 0.780 | 1.0 |
| heterogeneous_specialist | voi | 4.232 | 0.826 | 1.0 |
| uniform_specialist | random | 6.730 | 0.795 | 1.0 |
| uniform_specialist | confidence | 5.209 | 0.841 | 1.0 |
| uniform_specialist | impact | 3.626 | 0.817 | 1.0 |
| uniform_specialist | voi | 3.640 | 0.823 | 1.0 |
| distribution_shift | random | 7.639 | 0.760 | 1.0 |
| distribution_shift | confidence | 6.222 | 0.811 | 1.0 |
| distribution_shift | impact | 6.456 | 0.784 | 1.0 |
| distribution_shift | voi | 10.276 | 0.725 | 1.0 |

Runtime routing sees confidence, source kind, action impact, and query cost only. VOI uses disjoint development outcomes; its additional development-query cost is disclosed separately in JSON and is excluded from matched evaluation budgets. The distribution-shift arm deliberately reverses specialist competence, so a development-fitted router can be worse than a simple policy. Zero-query and all-query policies coincide across methods.

## Interpretation and uncertainty

The JSON includes paired episode-bootstrap mean differences and 95% percentile intervals for every declared primary comparison. These intervals are exploratory, unadjusted for multiple comparisons, and are not formal risk certificates. Read the full frontier before choosing a policy; this report does not select policies using evaluation outcomes.

Supported only in the stated controls: copies should not create new evidence; negative identity scores can prevent false merges; complete dependency accounting improves on a single-score gate; and routing can exploit development-observed heterogeneous query value. These mechanisms do not establish a real-data improvement. Null full-coverage results, wrong-rule damage, conservative risk coverage, and distribution-shift failures remain in the tables.
