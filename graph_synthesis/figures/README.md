# Graph-synthesis visual assessment

Generated from frozen observations and executed summaries by `python -B -m graph_synthesis.visualize`. No fresh inference or threshold selection. Read the [revised manuscript](../paper.md).

SVG is the committed, scalable source; optional PNG (240 dpi) and PDF exports use the same figure data. `data.json` contains complete chart inputs and source SHA-256 hashes; `edge_summary.csv` exposes the main denominators. Each figure has its own plot and can be read independently.

## 01 edge yield

![Figure 1: 01 edge yield](01_edge_yield.svg)

All 339 SciFact candidates remain in each bar. Correct and incorrect SUPPORTS/REFUTES edges are separated from no-edge outcomes. No edge includes NOT_ENOUGH_INFO, operational failure, and (for the agreement arm) abstention; it does not mean correct rejection. Source: fusion.arms.*.operational. Existing experiment, not fresh inference.

## 02 precision recall

![Figure 2: 02 precision recall](02_precision_recall.svg)

Typed-edge precision versus recall for the five frozen experimental arms. Recall uses all 209 gold SUPPORTS/REFUTES rows, not accepted predictions. Wrong polarity is both an incorrect edge and a missed gold edge. Axes run from 0 to 100%; the arrows only locate labels. No confidence region or superiority claim is implied.

## 03 identity risk coverage

![Figure 3: 03 identity risk coverage](03_identity_risk_coverage.svg)

Identity same-action risk (incorrect accepted same labels / accepted same labels) versus accepted candidates / all 413 candidates. Each point admits a complete equal-score tie block. The curve is descriptive evaluation-set evidence, not a calibrated policy; different_from constraints are outside this curve.

## 04 relation risk coverage

![Figure 4: 04 relation risk coverage](04_relation_risk_coverage.svg)

Pooled SUPPORTS/REFUTES wrong-edge risk versus accepted candidates / all 339 candidates. Whole score ties are admitted; no exact-K splitting or synthetic origin point is used. NEI and errors remain in the coverage denominator. Risk is not false-positive rate among negatives. No threshold is selected from this curve.

## 05 confusion baseline

![Figure 5: 05 confusion baseline](05_confusion_baseline.svg)

Generic Choice operational confusion on 339 SciFact candidates. Cells show counts and within-gold-row percentages. ERROR is a separate output column and remains in the denominator. All gold counts are printed; color intensity is normalized within each gold row.

## 06 confusion selected

![Figure 6: 06 confusion selected](06_confusion_selected.svg)

Selected formulation operational confusion, using exactly the baseline plot's gold order, columns and normalization. A predicted NEI is not the same as abstention or an operational error. In particular, true support can be omitted without becoming a wrong committed edge.

## 07 matched precision

![Figure 7: 07 matched precision](07_matched_precision.svg)

Selected-minus-baseline precision at equal accepted PRIMARY-action counts: 351 same-identity actions and 118 SUPPORTS actions. Points and intervals come from the existing 1,000-draw paired percentile bootstrap (seed 20260918). SciFact resamples components; identity resamples disjoint pair units. Both intervals include zero. This is not the pooled-edge fusion comparison.

## 08 component coverage

![Figure 8: 08 component coverage](08_component_coverage.svg)

SciFact nodes grouped by the size of their accepted-edge weak component. Each bar equals component size times component count. Both arms retain all 583 candidate nodes, including isolates (size 1); totals therefore have the same denominator. More connected nodes do not establish more correct facts.

## 09 identity reliability

![Figure 9: 09 identity reliability](09_identity_reliability.svg)

Classwise raw P(same) reliability on every valid identity response. Fixed ten equal-width bins, [lower, upper), with 1 included in the last bin; empty bins are omitted, not zero-filled. Marker area is proportional to bin count. The diagonal denotes equality of binned means, not certification of low graph risk.

## 10 support reliability

![Figure 10: 10 support reliability](10_support_reliability.svg)

Raw P(SUPPORTS) against gold support frequency on every valid SciFact response, including rows predicted as other labels. Same bins and marker sizing as the identity reliability plot. Failures are excluded ONLY from probability diagnostics, not operational metrics. Repeated components make this descriptive, not an independent-binomial confidence assessment.

## 11 refute reliability

![Figure 11: 11 refute reliability](11_refute_reliability.svg)

Raw P(REFUTES) classwise reliability with fixed bins and sample-size-proportional marker area. The plot describes source-to-claim classification, not factual probabilities of biomedical relations. It is not a new temperature-scaling experiment.

## 12 changed component

![Figure 12: 12 changed component](12_changed_component.svg)

An actual supplied-candidate SciFact component, selected deterministically by the largest number of changed predictions, then node count, then IDs, without gold-based selection. Nodes are original document/claim identifiers. Each arrow lists baseline / selected / gold. Dashed arrows mark changed predictions; a no-edge prediction does not delete its nodes. This deliberately selected disagreement example is not representative evidence of average quality.

## 13 source withdrawal

![Figure 13: 13 source withdrawal](13_source_withdrawal.svg)

Controlled withdrawal of the most incident source snapshot in each existing graph. Bars show active and deactivated assertions after withdrawal; their totals equal preserved historical assertions. Identity includes same_as AND different_from assertions. Reopen/audit checks are software outcomes, not independently observed scientific retractions.

## 14 fusion effects

![Figure 14: 14 fusion effects](14_fusion_effects.svg)

Existing component-paired macro-F1 differences relative to the selected formulation, with 2,000-draw 95% percentile intervals from the relationship experiment. Intervals are unadjusted, conditional on frozen selection, and include zero. No fresh model fit or experiment is performed by the figure generator.

## 15 recorded input cost

![Figure 15: 15 recorded input cost](15_recorded_input_cost.svg)

Historical evaluation input tokens needed by each formulation versus correctly retained SciFact edges. Two-formulation arms require both sets of requests. Counts exclude retrieval, extraction, storage, review, current prices and fresh measurements; they are not an end-to-end cost or latency benchmark. Three ensemble points share an input-token coordinate.
