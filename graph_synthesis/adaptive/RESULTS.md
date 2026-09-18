# Adaptive verification and joint conflict resolution for Jev graph synthesis

Timothy Wayne Gregg | AI-assisted author-review research extension | September 18, 2026

## Abstract

Following the multicall study, we execute five falsifiable improvements rather than assume that additional model calls improve graph quality. Compact disagreement routing saves 34.38% of recorded input tokens, preserves the single baseline's wrong-edge count, and recovers one additional correct edge, but misses its frozen 40% saving target. Dependency-safe fallback eliminates operational failures while admitting more incorrect relationships. Development-learned redundancy capping does not establish a matched-volume advantage. Group-aware review reduces source-group contamination under an explicitly simulated reviewer, and joint conflict optimization improves supplied priority utility in bounded controlled graphs. None of these results establishes independent semantic generalization, safe autonomous writes or superiority to KARMA.

## Research question and provenance

The protocol was committed in `8c404bc997dad7a2b01b453429f566e47dfd3b2f` before executing this extension, against baseline `a1555ade897a570be811039f4760ef17e55b793a`. Prior multicall test results were already inspected to formulate the hypotheses. This is an exploratory follow-on, not independent preregistration. H1-H3 replay authentic saved responses; H4 simulates review on observed source groups; H5 executes algorithms against an independent finite oracle. **Fresh service calls in this extension: 0.** The prior 3,024 calls are not counted as new inference.

The original split remains 73 development candidates in 40 source groups and 263 test candidates in 149 groups. H3 clusters and H4 risk estimates use development labels only. Every decision policy receives gold-free inputs. Hash checks, raw response reconstruction, group isolation and the original offline replay run before the new analysis. These published test items are not a new holdout.

The motivating evidence is the [multicall report](../../experiments/jev-multicall-20260918/REPORT.md) and [previous follow-up](../followup/RESULTS.md). The [frozen protocol](PROTOCOL.md) specifies all five conjunctions below. Typed output validity, semantic correctness and graph-level consistency remain separate properties. See the [TypeSafe documentation](https://docs.typesafe.ai/introduction) and [KARMA paper](https://arxiv.org/abs/2502.06472) for the respective bounded-decision and broader enrichment contexts; neither is a newly executed external baseline.

## Frozen operational targets

| Hypothesis | Target | Outcome and evidence boundary |
|---|---|---|
| H1: Compact disagreement routing | 40% token saving; 98% correct-edge retention; no extra wrong edges | Not met; Saved-response counterfactual |
| H2: Dependency-safe fallback | 75% fewer operational failures; 98% retention; no extra wrong edges | Not met; Saved-response counterfactual |
| H3: Redundancy-capped voting | 20% fewer matched-volume errors than flat voting; 95% retention | Not met; Development-fit response replay |
| H4: Group-aware review | Fewer contaminated groups than individual-risk review at budget 20; no lower retention | Met; Simulated ideal reviewer only |
| H5: Joint conflict optimization | Zero oracle errors; never below greedy utility; strict gain on at least 10% of random fixtures | Met; Finite controlled graph oracle only |

A target pass is a point-estimate engineering result, not a statistically established general improvement. Do not pool these different evidence types into a success rate.

## H1: Compact disagreement-triggered escalation

The compact contrastive prompt and the short evidence-only blind1 reviewer are evaluated first. Agreement keeps the compact answer; disagreement or invalid output invokes the rich base1 answer. The two views still share Jev and source evidence. The ablation replaces disagreement with the fixed 0.90 compact-confidence threshold. Every required preliminary, fallback and failed call is charged.

| Policy | Correct / wrong edges | Precision | Recall | Required calls | Input tokens |
|---|---:|---:|---:|---:|---:|
| Single rich prompt | 132 / 18 | 88.00% | 86.27% | 263 | 941,809 |
| Compact prompt | 129 / 17 | 88.36% | 84.31% | 263 | 332,438 |
| Compact confidence route | 132 / 18 | 88.00% | 86.27% | 340 | 608,117 |
| Compact disagreement route | 133 / 18 | 88.08% | 86.93% | 544 | 617,985 |

Disagreement routing retains 100.76% of baseline correct edges and saves 34.38% of tokens. Its quality point targets are met but the 40% cost target is not. It also requires more physical calls than the single baseline, so token savings cannot be presented as measured latency savings. The confidence ablation is slightly cheaper; disagreement gains one correct edge in this capture, not an established general advantage.

![H1: recorded tokens versus recovered correct edges](figures/01_routing.png)

## H2: Dependency-safe fallback for invalid typed checks

An invalid base1 call falls back to the independent standalone compact request. With a valid base1 answer, invalid check vectors preserve base1 and do not authorize adjudication. Valid prerequisites permit adjudication; an invalid adjudicator falls back to base1. “Standalone” means not conditioned on the invalid checks, not statistically independent. The policy neither normalizes invalid vectors nor invents unobserved responses.

| Policy | Correct / wrong edges | Operational errors | Input tokens |
|---|---:|---:|---:|
| Single rich prompt | 132 / 18 | 1 | 941,809 |
| Original targeted | 126 / 19 | 21 | 1,709,341 |
| Dependency-safe fallback | 137 / 21 | 0 | 1,680,906 |

Operational failures fall from 21 to 0. However, the recovered coverage raises incorrect edges to 21 versus 18 for the single baseline. The frozen safety conjunction is therefore not met. A valid typed answer is not necessarily a correct graph edge; failure recovery must be evaluated alongside semantic harm.

![H2: recovery and semantic error accounting](figures/02_fallback.png)

## H3: Redundancy-capped voting

Development error overlap clusters the seven views, using a fixed 0.80 same-wrong-label intersection/union threshold. Each cluster casts at most one vote. Positive acceptance requires a strict majority and at least two supporting clusters. At least one valid view is required in every cluster; otherwise the policy remains an operational error. These are empirical error-redundancy clusters, not independent sources or calibrated evidence units.

Learned clusters: `base1, base2, base3, structured`; `blind1`; `blind2`; `contrastive`.

At the natural operating point, capped voting yields 131 correct edges, 18 wrong edges, 7 abstentions and 2 errors. At a fixed 148 accepted edges:

| Policy | Correct / wrong | Precision | Input tokens for all candidate decisions |
|---|---:|---:|---:|
| Single rich prompt | 131 / 17 | 88.51% | 941,809 |
| Flat seven-view vote | 129 / 19 | 87.16% | 4,577,294 |
| Redundancy-capped vote | 130 / 18 | 87.84% | 4,577,294 |

The capped-versus-flat matched precision difference has a descriptive 95% interval of [-0.12, +2.10] pp and 99% interval of [-0.25, +2.84] pp. Both include zero. The 20% error-reduction target is not met; the single baseline also has fewer matched-volume mistakes. All seven calls are charged. Error diversity alone is insufficient evidence of useful or economical corroboration.

![H3: equal-volume incorrect edges](figures/03_corroboration.png)

## H4: Group-aware review allocation

Development-only shrinkage estimates edge error risk from label, the 0.90 score indicator, and disagreement with the compact view. Individual review sorts by that risk. Group-aware review greedily maximizes the estimated reduction in source-group contamination: an edge risk times the product of the remaining edges' estimated correctness. This independence-shaped product is only a ranking heuristic; it is not a risk certificate under correlated errors. Selection sees no test labels.

The primary simulated reviewer removes wrong accepted edges, retains correct accepted edges and adds no missing edge. A source group is contaminated when any remaining accepted edge has the wrong label. These groups are source-dependence units, not measured database topology.

| Review budget | Individual: wrong edges / contaminated groups | Group-aware: wrong edges / contaminated groups | Correct edges retained (both) |
|---|---:|---:|---:|
| 10 | 14 / 12 | 14 / 12 | 132 |
| 20 | 13 / 11 | 11 / 9 | 132 |
| 30 | 11 / 9 | 9 / 7 | 132 |
| 40 | 9 / 7 | 9 / 7 | 132 |

At budget 20, the ideal-review point target is met. The advantage is budget-dependent: the policies tie at budgets 10 and 40. Human-review accuracy and cost were not measured. Both rankings use the same observed features; obtaining those features entails single-plus-compact decisions for every candidate, not free additional evidence.

The recorded feature-acquisition total is 1,274,247 input tokens, before any actual review cost. Under a 5% false-removal rate, the following analytic sensitivity analysis applies at budget 20:

| Wrong-edge detection sensitivity | Individual: expected contaminated groups / correct edges | Group-aware: expected contaminated groups / correct edges |
|---|---:|---:|
| 50% | 13.25 / 131.25 | 12.25 / 131.35 |
| 75% | 12.19 / 131.25 | 10.69 / 131.35 |
| 100% | 11.00 / 131.25 | 9.00 / 131.35 |

These expectations assume independent reviewer detection across reviewed wrong edges and the specified false-removal rate; they are not additional observed trials. Full sensitivity combinations and selected IDs are in results.json.

![H4: contaminated source groups at fixed review budgets](figures/04_review.png)

## H5: Joint optimization of conflict components

The previous interval/scope guard detects incompatible assertions but does not choose a consistent batch. The new opt-in optimizer builds a conflict graph, separates connected components, and enumerates all subsets within components of at most 16 assertions. It chooses the maximum supplied priority sum among compatible assertions, with deterministic ID tie-breaking. Unsupported assertions and larger components are staged. This exponential method is deliberately bounded, not a database-scale algorithm.

On 128 seeded eight-assertion fixtures, it matches an independent integer-time active-fact oracle with 0 oracle/consistency failures. There are 0 failures across 1,024 input-order checks. Joint utility strictly exceeds priority-first greedy on 33/128 fixtures (25.78%); it is never lower.

| Method | Aggregate supplied priority utility |
|---|---:|
| Input-order greedy | 3,106 |
| Priority-first greedy | 3,530 |
| Joint bounded optimizer | 3,656 |

An explicit counterexample gives greedy utility 5 versus joint utility 6: one wide interval can block two compatible narrower assertions with greater combined priority. The 17-assertion over-limit control stages all 17 and writes none.

**Falsifying semantic control:** two conflicting assertions have supplied weights 9 and 8, but the higher-weight assertion is labeled false by the controlled truth assignment. The optimizer selects the false assertion. Constraint consistency and maximum supplied utility therefore do not establish semantic truth. Priorities are not Jev-calibrated truth probabilities, and mis-specified priorities can favor the wrong graph.

![H5: bounded joint versus greedy utility](figures/05_joint.png)

## Uncertainty, failure criteria and interpretation

H1-H3 use 4,000 paired source-group bootstrap draws with seed 20260919. Policies, development fits and matched-volume ID sets remain fixed during resampling. The 95% and wider 99% percentile intervals are descriptive and exploratory; they are not simultaneous confidence intervals for all endpoints, do not include fitting uncertainty, and do not erase previous test exposure. Different accepted-set denominators can vary during a group bootstrap. Operational errors and abstentions remain in the full classification denominator, and wrong polarity is both an incorrect accepted edge and a missed gold edge.

| Prespecified comparison | 95% interval | 99% interval |
|---|---:|---:|
| H1: recall difference vs single | [+0.00, +2.16] pp | [+0.00, +2.90] pp |
| H2: wrong-edge rate difference vs single | [-0.39, +2.87] pp | [-0.86, +3.44] pp |
| H3: matched precision difference vs flat vote | [-0.12, +2.10] pp | [-0.25, +2.84] pp |

The evidence favors treating token efficiency, operational resilience, semantic accuracy and graph maintenance as separate optimization goals. Compact routing remains an efficiency candidate; fallback needs explicit error-risk constraints; repeated or correlated votes are not independent corroboration. Group-level review and bounded joint optimization warrant broader tests, but their controlled gains must not be promoted to independent Jev-accuracy claims. No default policy is changed.

## Reproducibility and next falsification gates

```bash
python -B -m unittest discover -s graph_synthesis/adaptive/tests -v
python -B -m graph_synthesis.adaptive.run --check
python -B -m graph_synthesis.adaptive.report --figures --update-paper
python -B -m graph_synthesis.render_current_paper --output manuscript/paper-current.pdf
```

results.json contains all five outcomes, source hashes, group intervals, clusters, review selections, sensitivity settings and controlled graph fixtures. predictions.json preserves every new policy outcome and required-call attribution for all development and test cases. summary.csv and five SVG/PNG figures are generated from those records. The artifact manifest binds source, outputs and validation logs. Original evidence and the archived original manuscript remain unchanged.

Independent source-disjoint semantic validation, prospective routed-service latency, real reviewer studies, correct qualifier/lineage extraction and matched-resource external baselines remain unexecuted. Candidate generation and open-ended relation discovery are outside this extension. The next decisive experiment should freeze a policy on these development results and test it on previously unseen source groups or a new corpus, without selecting the policy after seeing that evaluation.
