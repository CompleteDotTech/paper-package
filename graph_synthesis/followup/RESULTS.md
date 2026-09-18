# Five follow-up improvements: executed research

This study builds on the ten-theory suite and the September 18 service rerun. **No fresh Jev requests were made in this follow-up.** H1-H3 replay captured observations; H4-H5 execute controlled algorithms against finite oracles. These are different evidence types, not five independent tests of improved model accuracy.

Baseline `1e03d0e7dfbf0b0deb1e39ecf133e66e05be141b`; protocol committed as `49975b97464ce4ee8e5c67250d6690aaebeaea73` before suite execution. Prior results were already known, so this is exploratory, not independent preregistration. Policies were not retuned after viewing the following outcomes.

## Summary of fixed operational targets

| Hypothesis | Evidence | Primary target met? |
|---|---|---|
| H1: Guarded probability calibration | Captured Jev replay | False |
| H2: Edge-aware economical routing | Captured-token routing counterfactual | True |
| H3: Cross-run stability gate | Paired captured observations | False |
| H4: Scope and interval conflicts | Finite controlled oracle | True |
| H5: Duplicate/shared-lineage bounds | Finite independent-event oracle | True |

A target pass is a point-estimate engineering result, not a statistically established general improvement. Do not pool the indicators into a success rate.

## H1: Guarded probability calibration

Tables label the original capture old and the September 18 rerun new; base denotes the baseline formulation.

The fresh rerun showed that optimizing log loss could worsen Brier score. The proposed change fits a temperature on half of the original calibration components, then chooses a raw/temperature mixture on the other half with a no-worse-Brier constraint. Both components of this mixture preserve label order. No rerun labels enter the fit.

For the primary relation few-shot arm, selected temperature is 8 and mixture weight is 0; fit/guard valid observations are 62/88.

| Task / arm | Run | Raw log loss | Temp log loss | Guard log loss | Raw Brier | Temp Brier | Guard Brier |
|---|---|---:|---:|---:|---:|---:|---:|
| Relation / base | old | 1.2415 | 0.5385 | 0.4535 | 0.2340 | 0.3048 | 0.2282 |
| Relation / base | new | 1.2402 | 0.5396 | 0.4546 | 0.2342 | 0.3036 | 0.2280 |
| Relation / few-shot | old | 1.2401 | 0.5435 | 1.2401 | 0.2306 | 0.3127 | 0.2306 |
| Relation / few-shot | new | 1.3207 | 0.5542 | 1.3207 | 0.2244 | 0.3151 | 0.2244 |
| Entity / base | old | 0.1067 | 0.0744 | 0.0744 | 0.0408 | 0.0317 | 0.0317 |
| Entity / base | new | 0.1067 | 0.0730 | 0.0730 | 0.0407 | 0.0317 | 0.0317 |
| Entity / few-shot | old | 0.0335 | 0.0269 | 0.0268 | 0.0184 | 0.0149 | 0.0150 |
| Entity / few-shot | new | 0.0333 | 0.0275 | 0.0270 | 0.0181 | 0.0154 | 0.0152 |

Primary target met: **False**. Rerun valid probability N=337; failures=2; label changes=0. Guard-minus-raw descriptive paired 95% component intervals: log loss [0.0, 0.0]; Brier [0.0, 0.0].

The no-harm constraint holds on the guard partition only. It is not an out-of-sample guarantee, and preserving labels means this intervention cannot improve classification accuracy. Temperature-only here is fitted on the same half-calibration data as the guarded method, not the larger full-calibration fit reported in the previous paper.

![Probability trade-off](figures/01_calibration.svg)

## H2: Edge-aware economical routing

The earlier macro-F1/cost cascade could save tokens while admitting more wrong relationships. This follow-up explicitly constrains correct edges, wrong edges and precision during calibration-only selection. Positive and negative baseline labels have separate escalation thresholds; failed baseline calls escalate. Always-few-shot is an explicit fallback that avoids unnecessary baseline cost.

Primary selected policy: `{"direct": false, "negative_threshold": 0, "positive_threshold": 0.95}`.
Earlier macro-F1 rule, refitted on the same original calibration: threshold 0.

| Task | Run | Policy | Correct edges | Wrong edges | Precision | Input tokens | Macro-F1 |
|---|---|---|---:|---:|---:|---:|---:|
| Relation | old | baseline | 187 | 37 | 83.48% | 258,495 | 0.8508 |
| Relation | old | fewshot | 172 | 20 | 89.58% | 1,213,458 | 0.8527 |
| Relation | old | macro cascade | 187 | 37 | 83.48% | 262,102 | 0.8524 |
| Relation | old | edge cascade | 175 | 21 | 89.29% | 449,791 | 0.8581 |
| Relation | new | baseline | 185 | 38 | 82.96% | 258,495 | 0.8432 |
| Relation | new | fewshot | 173 | 19 | 90.10% | 1,213,458 | 0.8566 |
| Relation | new | macro cascade | 185 | 38 | 82.96% | 262,342 | 0.8448 |
| Relation | new | edge cascade | 173 | 19 | 90.10% | 442,640 | 0.8566 |
| Entity | old | baseline | 350 | 8 | 97.77% | 174,370 | 0.9605 |
| Entity | old | fewshot | 349 | 2 | 99.43% | 627,844 | 0.9859 |
| Entity | old | macro cascade | 350 | 8 | 97.77% | 174,370 | 0.9605 |
| Entity | old | edge cascade | 349 | 2 | 99.43% | 237,835 | 0.9859 |
| Entity | new | baseline | 350 | 8 | 97.77% | 174,370 | 0.9605 |
| Entity | new | fewshot | 348 | 3 | 99.15% | 627,844 | 0.9764 |
| Entity | new | macro cascade | 350 | 8 | 97.77% | 174,370 | 0.9605 |
| Entity | new | edge cascade | 348 | 3 | 99.15% | 242,280 | 0.9764 |

Primary target met: **True**. Input-token saving 63.52%; correct-edge retention 100.00%. The joint target requires at least 20% saving, 98% retention, and no extra wrong edges versus all-few-shot.

The edge-aware and all-few-shot rerun policies differ on 2 labels. These are recorded input-token counterfactuals, not measured new API latency or billing. Baseline requests are charged even when a fallback is needed. Calibration feasibility does not guarantee evaluation safety. A macro-F1-only success is not substituted for the stated graph target.

Descriptive paired 95% rate-difference intervals versus all-few-shot: correct edges [-0.008645533141, 0.008928571429]; wrong edges [0.0, 0.0]. This is not an equivalence test.

![Routing edge outcomes](figures/02_routing.svg)

## H3: Cross-run stability gate

The intervention accepts only positive labels that agree across exact-input original/rerun observations. Compare it with rerun confidence ranking and a uniform-random subset at exactly the same accepted volume. Stability is not independent corroboration; the two calls share model identity and evidence.

| Task / arm | Rerun correct / wrong | Stable correct / wrong | Matched confidence wrong | Random expected wrong | Retention |
|---|---:|---:|---:|---:|---:|
| Relation / base | 185 / 38 | 185 / 37 | 37 | 37.830 | 100.00% |
| Relation / few-shot | 173 / 19 | 170 / 18 | 17 | 18.604 | 98.27% |
| Entity / base | 350 / 8 | 350 / 7 | 7 | 7.978 | 100.00% |
| Entity / few-shot | 348 / 3 | 348 / 2 | 2 | 2.991 | 100.00% |

Primary target met: **False**. The primary arm has 335 common-valid pairs, 45 double errors and 45 agreements on a wrong label; 5 stable wrong positive edges have rerun score exactly one.
Two-run input cost is 2,426,916 versus 1,213,458 for the rerun alone.

Uniform-subset counts are exact expectations, not new random experiments or a significance test. Small volume reductions are not evidence of superiority when matched-volume confidence does better. A same-data repeat does not double the number of independent documents.

![Matched stability errors](figures/03_stability.svg)

## H4: Scope- and interval-aware conflicts

Exact qualifier equality can miss contradictory assertions valid over overlapping time ranges. The opt-in guard checks half-open integer interval intersection, compatible known scope, polarity, and explicitly declared functional predicates. Unsupported/missing qualifiers return unknown and must be staged rather than silently accepted. It does not select which contradictory assertion is true.

Executed 5,408 exhaustive supported pairs, including 1,160 oracle conflicts.
| Guard | Missed conflicts | False conflict flags |
|---|---:|---:|
| exact_qualifier | 1108 | 0 |
| qualifier_blind | 0 | 1544 |
| interval_scope | 0 | 0 |

Unknown/malformed cases staged: 5/5. Primary target met: **True**.

The independent oracle enumerates integer instants. This exhausts the declared finite fixture space, not arbitrary interval semantics or extracted real-world qualifiers. No production GraphStore policy is changed, and correct qualifier extraction remains untested.

![Interval conflict validation](figures/04_intervals.svg)

## H5: Duplicate/shared-lineage probability bounds

Alternative proofs cannot be treated as independent when they share sources. This intervention deduplicates identical atom sets, connects overlapping proofs, bounds each component using maximum and summed proof probabilities, and combines disjoint components only under the supplied independent-atom model. An independent finite-state enumeration supplies exact probabilities.

Executed 1,536 configurations from 384 parameter/proof settings with 1, 2, 5 and 20 copies. These copies are interventions, not independent samples.

| Aggregator | False admissions at 0.95 | Correct high-probability admissions |
|---|---:|---:|
| naive_or | 628 | 364 |
| dedup_or | 44 | 364 |
| lineage_lower | 0 | 336 |

Bound violations: 0; duplication-invariance failures: 0. Mean interval width 0.1014, maximum 0.6000. Exact high-probability configurations: 364. Primary target met: **True**.

The conservative lower-bound gate loses 28 correct high-probability admissions compared with naive aggregation; lower false confidence comes with a retention cost.

**Negative control:** falsely declaring two aliases for one source independent produces lower bound 0.96 for actual probability 0.80, and incorrectly passes the 0.95 gate. Thus lineage discovery and provenance integrity are necessary, not optional implementation details.

These probabilities concern synthetic sufficient-proof validity events, not actual scientific truth. **Raw Jev confidence is not a certified primitive-event probability.** The control shows what the algorithm can guarantee under supplied assumptions and exactly how those assumptions can fail.

![Duplication and confidence inflation](figures/05_lineage.svg)

## Source separation, uncertainty and limitations

Both original/rerun empirical evaluations contain 339 relation candidates and 413 entity pairs; they are repeated observations of the same items. Original calibration component counts and purge audit are in results.json. Group construction uses claim/document or record IDs, not gold identity groups. Exact response reconstruction and pinned SHA-256 checks run before every analysis.

H1 and H2 intervals use 1,000 paired connected-component bootstrap draws with seed 20260918. They are descriptive 95% intervals, unadjusted for multiple comparisons. No p-value, confirmatory claim, external-model win, candidate-generation recall improvement or deployed graph-risk guarantee is inferred. Invalid responses remain operational errors, with explicit valid-only probability denominators. The source-disjoint independent corpus and matched KARMA comparison remain unexecuted.

## Reproduction and implementation status

```bash
python -B -m unittest discover -s graph_synthesis/followup/tests -v
python -B -m graph_synthesis.followup.run --check
python -B -m graph_synthesis.followup.report --figures --update-paper
python -B -m graph_synthesis.render_current_paper --output manuscript/paper-current.pdf
```

All numerical findings are generated from results.json. Existing frozen evidence and the default compiler remain unchanged. The methods are opt-in research implementations, not validated production replacements. All conclusions remain an AI-assisted author-review draft. See [PROTOCOL.md](PROTOCOL.md) for the frozen criteria and [CLAIM_EVIDENCE.md](CLAIM_EVIDENCE.md) for evidence boundaries.
