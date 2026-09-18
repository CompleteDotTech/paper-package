# Five post-certificate improvements for Jev graph synthesis

Timothy Wayne Gregg | AI-assisted author-review research extension | September 18, 2026

## Abstract

The dependence-aware certificate study left an asymmetric frontier: its source-random-effects forecast improved Brier by only 6.39% and missed its frozen target, while its dependence bounds, flow certificates, repair-invariant queries and local delta maintenance passed controlled tests. This pre-execution-frozen follow-up tests five responses to those remaining boundaries. The outcomes are: H1 **not met**, H2 **met**, H3 **met**, H4 **met**, and H5 **met**. No fresh Jev calls are made. H1 reuses previously inspected saved responses; H2–H5 are controlled algorithmic experiments. These results are not new semantic-accuracy evidence and are not a comparison against KARMA or another external graph system.

## 1. Frozen methodology and novelty boundary

The protocol was committed as `f923e8d41ca5953d9793fadcc3730cfe9fc70b3a` against merged baseline `9d2e4a60a6c79e616ab1d352cd5da9fe414e6c98` before implementation or execution. It fixes generators, thresholds, comparators and seed 20260923. Existing package studies already contain relation-level stacking, fixed pairwise-dependence sensitivity analyses, bipartite flow, repair ambiguity and exact-marginal credal bounds. The five experiments here test different package-level integrations: source-group forecast stacking, active dependence-constraint acquisition, verified small-separator conditioning beyond bipartite graphs, reusable singleton repair margins and interval-valued marginal premises. This is a repository-scoped experiment distinction, not a worldwide novelty claim.

**Fresh Jev service calls: 0.** No production graph policy is changed. The controlled structural fixtures do not establish real-world source truth, reviewer behavior, calibrated Jev probabilities or end-to-end database latency. A pass means only that the frozen target for the stated evidence population was met.

| Hypothesis | Frozen primary requirement | Result | Evidence class |
|---|---|---|---|
| H1: exposure-stratified source-risk stacking | Beat random-effects Brier by >=3%, do not regress feature-risk Brier, |bias| <=0.03 | Not met | Previously inspected saved-response source forecasts |
| H2: active dependence constraints | Zero containment/widening failures; mean width <=75% marginal-only and <=90% lexicographic same-budget | Met | Supplied finite joint distributions |
| H3: near-bipartite separator solver | Exact small oracles; solve all 512/1024/2048 residual cases; safe controls | Met | Supplied weighted conflict graphs |
| H4: repair-margin query index | Zero query/witness mismatches and >=70% fewer frozen-count optimization invocations | Met | Repeated controlled singleton queries |
| H5: interval marginals | Zero containment failures; prevent 20/20 designed false admissions; fail closed on malformed inputs | Met | Supplied joint distributions and uncertainty intervals |

## 2. H1 — Exposure-stratified source-risk stacking

The certificate result suggested that within-source dependence contains information but did not outperform the richer feature-risk forecast. H1 therefore combines the two forecasts without using evaluation labels for fitting. Leave-one-source-group-out development predictions select convex weights separately for singleton and multi-edge exposure strata when each stratum has at least eight folds; otherwise the global development weight is used.

Development selected feature weights: global **1.0**, singleton **1.0**, multi-edge **1.0**. Development fold counts are 23 total, 14 singleton and 9 multi-edge. Evaluation scoring uses the identical 98 nonempty source groups as the comparators (60 singleton, 38 multi-edge).

| Forecast | Brier | Clipped log loss | Bias |
|---|---:|---:|---:|
| Existing feature-risk | 0.128923 | 0.467074 | -0.072629 |
| Certificate random effects | 0.131444 | 0.435042 | -0.012382 |
| Exposure-stratified stack | 0.128923 | 0.467074 | -0.072629 |

The stacked-minus-feature paired Brier mean is +0.000000, with descriptive 95% interval [+0.000000, +0.000000]. The stacked-minus-random-effects mean is -0.002522, with 95% interval [-0.028381, +0.021169]. The frozen conjunction is **not met**. These intervals condition on the selected development weights and reuse already inspected evaluation data; they are not independent validation.

![H1. Forecast Brier on the identical nonempty source-group denominator.](figures/01_stacked_risk.png)

## 3. H2 — Greedy acquisition of dependence constraints

Marginal-only dependence bounds are safe but can be wide. H2 treats exact pairwise intersections from each fixture's supplied joint distribution as controlled observations and asks which three would most narrow the conclusion interval. At each step the policy evaluates every not-yet-observed pair and selects the one giving the smallest certified width; the comparator spends the same budget on the first three lexicographic pairs.

Across 128 fixtures, mean width is **0.326563** from marginals alone, **0.176527** after the lexicographic budget and **0.096687** after the greedy budget. Truth-containment failures: **0**. Chosen-step widening failures: **0**. The frozen target is **met**.

This is an oracle value-of-information experiment: it assumes the selected pairwise intersections can be supplied exactly. It does not show that those quantities are observable cheaply, that Jev scores are source reliabilities, or that a production estimator would preserve the same benefit.

![H2. Mean certified width before and after equal three-constraint budgets.](figures/02_constraint_acquisition.png)

## 4. H3 — Separator-conditioned near-bipartite exact optimization

The prior flow certificate handles bipartite components but stages sufficiently large non-bipartite ones. H3 accepts a supplied separator of at most four vertices, verifies that deleting it leaves a bipartite graph, enumerates every independent separator choice and solves each residual branch with the existing certified bipartite solver. An invalid separator is not trusted; it stages.

The 128 small exhaustive fixtures have **0** oracle failures and **0** order/duplicate-invariance failures. Large residual-cycle results are 512→258/258, 1024→514/514, 2048→1026/1026, written as residual vertices → obtained/analytic utility. The current generic solver stages respectively **513, 1025, 2049** vertices on those fixtures. Malformed and non-transversal controls stage safely: **True**. The frozen target is **met**.

The supplied priorities and conflict edges remain premises. Exact maximum supplied-priority utility does not establish that a selected assertion is factually true.

![H3. Separator-conditioned utility versus the analytic optimum.](figures/03_near_bipartite.png)

## 5. H4 — Reusable repair-margin singleton query index

The certificate query implementation recomputes a base optimum plus forced-in/forced-out alternatives for repeated questions. H4 precomputes each vertex's inclusion and exclusion margin once, then classifies any singleton query at any tested tolerance by comparing those margins with the tolerance threshold.

Across **2653** repeated singleton queries, classification mismatches are **0** and witness failures are **0**. Under the frozen top-level solve-count accounting, repeated queries require **7,959** invocations versus **1,814** for index construction, a **77.21%** reduction. A control using the existing query's realized early-exit count gives a still-separated descriptive reduction of **74.41%**. The frozen target is **met**.

This index is deliberately limited to singleton queries and in-memory top-level optimization calls. It is not a measured SQL/database speedup or a semantic guarantee.

![H4. Frozen-accounting optimization calls for repeated queries versus one reusable index.](figures/04_query_index.png)

## 6. H5 — Interval-marginal dependence certificates

Previous dependence-safe methods remain conditional on exact atom marginals. H5 instead supplies each atom with a lower and upper probability and optimizes over all Boolean-world distributions whose marginals lie inside those intervals. Exact point marginals are a special case. Invalid, infeasible or over-cap inputs return a non-certifying [0,1] stage.

Across 128 arbitrary-joint fixtures, truth-containment failures are **0**. Mean point-bound width is **0.361057** and mean interval-marginal width is **0.467497**, exposing the cost of premise uncertainty rather than hiding it. On 20 deliberately biased singleton point estimates, the interval policy prevents **20/20** designed false admissions. Malformed inputs returning a certifying interval: **0**. The frozen target is **met**.

The interval itself is still a supplied assumption. If the real marginal falls outside it, the certificate can again be wrong. This test converts one known premise-error mode into explicit uncertainty; it does not validate how such intervals should be estimated from real sources.

![H5. False admissions on designed marginal-misspecification controls.](figures/05_interval_marginals.png)

## 7. Interpretation and falsification boundary

The five experiments are intentionally heterogeneous. H1 asks whether two already observed forecast signals combine on reused response data. H2 asks whether a constrained information budget can reduce dependence uncertainty on finite controlled worlds. H3 and H4 test exact structural reuse. H5 asks whether uncertainty in the probability premises can be represented rather than ignored. Their pass/fail outcomes must not be pooled into a semantic success percentage.

The strongest remaining scientific boundary is unchanged: freeze a policy before observing a new source-disjoint, independently adjudicated corpus and compare full graph quality, downstream queries, provenance errors, reviewer mistakes, resource budgets and staging against appropriate external baselines. None of the controlled algorithmic passes can substitute for that prospective semantic evaluation.

## 8. Reproduction

```bash
python -m pip install -r graph_synthesis/post_certificates/requirements.txt
python -B -m graph_synthesis.post_certificates.run
python -B -m unittest discover -s graph_synthesis/post_certificates/tests -v
python -B -m graph_synthesis.post_certificates.run --check
python -B -m graph_synthesis.post_certificates.report --figures --update-paper
python -B -m graph_synthesis.render_current_paper --output manuscript/paper-current.pdf
```

The machine-readable results retain the controlled fixtures, selected pair constraints, optimization witnesses, development-only weights, uncertainty intervals and falsifying controls. The five PNG/SVG pairs and summary table are generated from those recorded results. Earlier study artifacts are not rewritten.
