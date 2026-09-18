# Assumption-aware graph synthesis: five falsifiable follow-up experiments

Timothy Wayne Gregg | AI-assisted author-review research extension | September 18, 2026

## Abstract

The expanded Jev research distinguishes better typed decisions from stronger graph infrastructure. This follow-up tests five responses to unresolved limitations in PR #17: dependence-robust probability envelopes, answers invariant across optimal repairs, query-exposure-weighted review, connected-tree delta updates, and grounded cyclic provenance. Marginal-only probability envelopes reduce mean uncertainty width by 4.96%, missing the frozen 10% target. Query-weighted review also fails: at 20 idealized reviews, weighted residual contamination rises from 50 to 63, while contaminated source groups rise from 8 to 11. The three other controlled targets are met. Connected balanced-tree DP visits fall by 97.63%; agenda-indexed grounding reduces counted dependency inspections by 94.28%. These are bounded supplied-input engineering results, not new semantic accuracy, independent validation, external-system superiority, or production readiness. **Fresh Jev calls: 0.**

## 1. Motivation, scope and novelty boundary

The [preceding reliability study](../reliability/RESULTS.md) tightened lineage under assumed independence, but its deliberately false independence input still inflated 0.8 to 0.96. Its exact conflict optimizer could select a false high-priority assertion. Its component cache saved no solver work on the connected stress graph. Its single-view review economy did not establish effectiveness on an observed query workload. These limitations motivate changing the admissible assumptions and query semantics rather than simply asking the same model more times.

The [frozen protocol](PROTOCOL.md) was committed as `82ee57229570bb9f7299e0418a5f9b959c25d59f` against baseline `a62a3257645d8e35cd4e45be53bfa9511d27724b` before implementation and execution. Prior findings informed hypothesis choice. This is exploratory follow-up, not independent preregistration. H3 reuses 73 development cases in 40 groups and 263 evaluation cases in 149 groups; no new holdout is claimed. Raw-response reconstruction, unique identities, source-group separation and input hashes are checked before scoring. The policy receives no evaluation gold. Algorithm fixtures in H1/H2/H4/H5 are generated from the committed seeds, and all successful, unsuccessful and assumption-breaking cases remain in [results.json](results.json).

These five combinations were not found as executed suites in the audited baseline implementation. They are **not claims that the underlying ideas have never been attempted anywhere**. Probability envelopes already use linear programming in probabilistic satisfiability ([Hansen and Perron](https://doi.org/10.1016/j.ijar.2007.03.001)); all-repair semantics are established ([Staworko et al.](https://arxiv.org/abs/0908.0464)); utility-oriented KG auditing has prior empirical work ([Marchesin et al.](https://doi.org/10.1609/hcomp.v12i1.31605)); tree dynamic programming is established ([Gupta et al.](https://arxiv.org/abs/2305.03693)); and recursive materialisation maintenance is established ([Hu et al.](https://doi.org/10.1609/aaai.v32i1.11554)). The [novelty audit](NOVELTY.md) states the narrower integration differences and search limitations. No external implementation is benchmarked here.

| ID | Proposed improvement | Frozen target | Evidence class |
|---|---|---|---|
| H1 | Dependence-robust lineage envelopes | not met | Controlled supplied-input algorithm |
| H2 | Ambiguity-preserving repair answers | met | Controlled supplied-input algorithm |
| H3 | Query-exposure-weighted review | not met | Captured decisions + synthetic exposure + simulated review |
| H4 | Connected-tree delta messages | met | Controlled supplied-input algorithm |
| H5 | Grounded cyclic provenance | met | Controlled supplied-input algorithm |

A target pass establishes only its stated conjunction on its stated population. The pass count is not a semantic success rate. Failed targets are not rescued by changing thresholds or promoting a favorable sensitivity panel.

## 2. H1: Dependence-robust lineage envelopes

**Theory.** Let each world assign truth values to primitive source events. A nonnegative world-mass vector must normalize to one and match supplied marginals; optional pairwise intersections add constraints. For a fact supported by a disjunction of conjunctive proofs, minimize and maximize the sum of masses in satisfying worlds. Every supplied-compatible joint distribution lies between these extrema. Unlike an independent-events point estimate, the feasible family permits perfect source dependence. Primitive probabilities and any intersections are supplied assumptions, not measured Jev truth probabilities.

The comparator canonicalizes duplicate and subsumed proofs, applies marginal Frechet conjunction bounds and then union bounds. The bounded LP uses at most eight atoms (256 worlds), capped iterations, primal feasibility checks, dual-inequality residual correction and outward numerical allowance. Endpoint witnesses are saved and independently checked against constraints. Above the atom cap it returns conservative marginal bounds and explicit non-optimized status. Infeasible constraints, failed solves or failed verification stage with [0,1]. Floating-point residual checks are **not formal exact-arithmetic certificates**. Broader probability-envelope optimization is not generally cheap; [Kaski et al.](https://arxiv.org/abs/2605.03556) discuss the hardness of optimal union intervals.

**Frozen test.** Seed 20260922 generates 128 arbitrary joint distributions over two to six atoms and one to eight proofs. The joint masses are generated separately from both bounding algorithms. Require zero truth-containment errors beyond 1e-7, zero false lower-bound admissions at 0.95, zero order/duplicate errors, and at least 10% lower mean width than the Frechet baseline. The pairwise-constrained panel is a sensitivity analysis, not the primary target.

| Envelope | Mean width | Role |
|---|---:|---|
| Canonical Frechet | 0.359405 | Primary comparator |
| Marginal-only LP | 0.341587 | Primary proposal |
| Pairwise-constrained LP | 0.088167 | Additional-information sensitivity |

Across 256 containment checks there are 0 failures, 0 false admissions and 0 saved-witness feasibility failures. There are 0 errors in 512 invariance checks. The primary width reduction is 4.96%, so the target is **not met** despite those correctness checks passing.

**Falsification controls.** Two names for one actual 0.8-probability source produce 0.96 under independent OR aggregation. The marginal envelope is [0.8,1] and does not admit at 0.95. Correct shared identity yields 0.8. Supplying mutually exclusive 0.5 events yields an OR probability approximately one; incoherent intersections stage rather than returning a confident value. Empty, tautological, zero/one and over-cap inputs are retained. Unknown dependence is representable, but false marginals or missing primitive events still defeat semantic validity.

![H1. Primary marginal envelopes and explicitly separate pairwise sensitivity.](figures/01_dependence_envelopes.png)

## 3. H2: Ambiguity-preserving answers over optimal repairs

**Theory.** A deterministic tie-break gives one repair, not a fact valid in every repair. Let V be maximum supplied priority. An assertion selected in one optimum is forced precisely when forbidding it lowers V. An OR query is entailed by every optimum precisely when forbidding every queried assertion lowers V. An AND query requires each member to be forced. This tests entailment relative to a supplied optimization model, not truth of the assertions. A false query result means 'not entailed by all optima', not 'false in all worlds'.

The method reuses PR #17's bounded optimizer as a value oracle, with at most 1,024 vertices across components and 1,024 oracle calls. Its existing component/cutset caps remain in force. Any unresolved relevant solve yields unknown or partial status, never an unsupported certificate. Zero priorities, empty queries, repeated edges and deterministic order are handled explicitly.

**Frozen test.** On 128 random graphs with four to ten vertices, seed 20260923, integer priorities zero through five and edge probability 0.3, an independent combinations enumerator retains every maximum-priority consistent subset. It checks optimum utility, forced assertions and OR/AND answers. Require no mismatches, full retention on unique optima, and on 32 equal-priority conflicting pairs require every pair disjunction but no individual assertion.

The test records 0 oracle disagreements and 0 order failures. All 66 unique-optimum cases retain their selected assertions. Across random fixtures, a single repair contains 444 assertions; 388 are forced, retaining 87.39%. This lower assertion coverage is an intentional refusal to invent certainty, not a recall improvement. The random fixtures require 1,084 solver calls in total. The target is **met**.

The 32-pair control has 2^32 optima. The method certifies all 32 disjunctions without enumerating those optima and certifies no individual member. The 17-clique control stages. A false assertion with priority nine against a true assertion with priority eight remains forced: repair invariance cannot repair a misleading priority function. No better Jev edge accuracy follows.

![H2. Assertions selected in one repair versus assertions invariant across all optima.](figures/02_repair_ambiguity.png)

## 4. H3: Query-exposure-weighted review

**Theory.** The preceding single-view risk estimator offers a cheap review signal, but review utility could depend on downstream exposure. The proposal multiplies each expected source-contamination reduction by a fixed exposure weight. The product-based contamination model and tie-by-ID rule otherwise match the PR #17 single-view group-aware comparator. This adds a workload model, not model calls or evidence.

Exposures are deliberately synthetic: one plus the SHA-256 integer of `query-exposure-v1:` concatenated with the source-group ID, modulo ten. They are fixed without evaluation gold. Uniform and reversed weights are sensitivity panels. They are not observed queries, independently sampled deployments or new datasets. All policies use the same development-only risk fit, accepted pool and 941,809 recorded input tokens. The primary reviewer perfectly removes a reviewed wrong edge and never removes a correct edge; detection rates 0.5, 0.75 and 1 are scenario analyses, not human observations.

**Frozen test.** At 20 edge reviews require at least 10% lower weighted residual contaminated-source exposure with no increase in unweighted contaminated groups. An exposure unit is one synthetic weight attached to a contaminated source group. Outcomes at four budgets are shown below; correct retained edges remain 132 at the primary budget for both methods.

| Review budget | Baseline exposure | Proposed exposure | Baseline contaminated groups | Proposed contaminated groups |
|---:|---:|---:|---:|---:|
| 10 | 73 | 73 | 12 | 12 |
| 20 | 50 | 63 | 8 | 11 |
| 30 | 24 | 54 | 4 | 10 |
| 40 | 24 | 37 | 4 | 8 |

At budget 20, the weighted outcome changes from 50 to 63, a relative reduction of -26.00%; the negative reduction means deterioration. Contaminated groups change from 8 to 11. The target is **not met**. Uniform exposure reproduces the baseline order: True. The hypothesis's apparent objective alignment is insufficient when estimated risks, group interactions and imposed exposure weights do not rank realized errors well.

The paired source-group bootstrap uses 4,000 draws with seed 20260924, fixed fit and review sets, and recomputed exposure denominators in each draw. Proposed-minus-baseline weighted contamination rate has a 95% interval [-2.0768, +4.9289] percentage points and a 99% interval [-3.1182, +6.3003] percentage points. These descriptive, non-simultaneous intervals omit fitting and workload uncertainty, and include zero. No statistically resolved harm or benefit on a new population is asserted. The frozen point-target failure remains a failure.

![H3. Weighted residual contaminated-source exposure under equal idealized review budgets.](figures/03_query_review.png)

## 5. H4: Delta messages inside a connected tree

**Theory.** Component-level caching discards all work when any weight changes inside a connected component. On a fixed rooted tree, an include value is its vertex priority plus children's exclude values; an exclude value sums the larger child value. Cache these aggregates. A changed weight can affect only its ancestor path. Propagate child-value deltas, stopping when a message is unchanged. Validation and initial rooting occur once; structural edits are explicitly unsupported and rejected without mutation.

**Frozen test.** The primary connected binary tree has 255 vertices and 256 seeded weight updates, seed 20260925. Cold-build work is included for both methods. Compare utility to independent full-tree DP after every update, and check a reconstructed selected set for consistency and summed utility. Additionally, 128 small random trees with eight updates each are checked against exhaustive subset enumeration. Require zero disagreements and at least 75% fewer DP vertex visits on the balanced workload.

| Topology | Full DP visits | Delta DP visits | DP reduction | Reconstruction visits per policy |
|---|---:|---:|---:|---:|
| Balanced, primary | 65,535 | 1,556 | 97.63% | 65,535 |
| Path, control | 65,535 | 17,474 | 73.34% | 65,535 |

There are 0 small-tree failures across 1,024 updates, and 0 failures on the two large workloads. The primary target is **met**. Invalid weight/structural updates preserve state; repeated identical weights visit zero DP nodes.

**Cost boundary.** Reconstruction traverses the whole tree on demand. The cold reference computes the optimum value; the accounting charges it the same full-tree reconstruction traversal measured for the delta implementation. Counting both DP visits and these eager reconstruction visits reduces the balanced improvement to 48.81% and the path improvement to 36.67%. These sums are transparent operation accounting, not uniform CPU-cost models or measured latency. Tall paths, changing topology and consumers demanding a complete repair after every update limit the gain. No corresponding reduction in service cost, database I/O or arbitrary-graph maintenance is established.

![H4. DP savings with the separately charged full-repair reconstruction work visible.](figures/04_connected_tree_work.png)

## 6. H5: Grounded cyclic provenance after retraction

**Theory.** Old derived facts must not become their own external justification. Start a positive Horn closure only from supplied external facts and empty-body axioms. Index each body occurrence by its prerequisite fact, initialize remaining-body counters, and activate a rule once all body members are grounded. Each newly grounded fact enters an agenda once. After a source change, recompute closure from current external facts, not from the previous derived closure.

This differs from the repository's earlier cascading prerequisite invalidation by preserving alternative positive supports while preventing unsupported cycles from surviving. It is nevertheless an implementation of established least-fixed-point grounding, not a new Datalog deletion algorithm. The strong comparator is a cold, repeated full-scan closure. A deliberately unsafe warm-start comparator is used only to expose circular self-support, not as the sole correctness or efficiency baseline. The prototype is in-memory, with caps of 4,096 facts, 8,192 distinct rules and 65,536 body occurrences.

**Frozen test.** Seed 20260926 generates 128 rule systems with four to twelve facts and eight source toggles each. Every closure is checked against independent cold scanning. The primary work test has 64 eight-rule chains in adversarial order and 128 source toggles, including cold setup. Require zero closure mismatches, no unsupported survivors in withdrawn-cycle controls, and at least 75% fewer dependency inspections.

| Workload | Full-scan inspections | Indexed inspections including index build | Reduction | Separate rule-counter initializations |
|---|---:|---:|---:|---:|
| Sparse chains, primary | 590,336 | 33,792 | 94.28% | 66,048 |
| Dense dependency control | 6,240 | 2,400 | 61.54% | 4,080 |

The random systems have 0 closure mismatches in 1,024 updates. The work panels also have 0 mismatches. Removing the only external seed clears a two-fact cycle; providing an independent alternate seed preserves its consequences. Pure unseeded cycles derive nothing. Empty-body axioms, self-loops and duplicate rules have explicit regression tests. Unknown external facts are rejected atomically. The target is **met**.

The indexed engine still initializes every rule counter after each update. It is a faster bounded cold recomputation under the stated work metric, **not** dependency-local incremental deletion, distributed transaction support or a measured DRed comparison. False external facts still ground false consequences. Correct grounding means derivable from supplied facts and rules, not verified real-world truth.

![H5. Dependency-inspection work; counter initialization remains a separately reported cost.](figures/05_grounded_provenance.png)

## 7. Research implications and limitations

The most defensible new knowledge is about failure boundaries. Marginal-only dependence reasoning can prevent unjustified point confidence, but did not deliver the frozen width improvement. Adding workload importance to a weakly calibrated review signal made the primary observed replay outcome worse. Neither failed proposal is promoted to a default policy. Repair-invariant answers distinguish ambiguity from arbitrary tie-breaking, but still inherit misleading priorities. Connected-tree messages remove avoidable recomputation for value-only consumers under fixed topology. Grounded positive closure makes cyclic support behavior explicit while preserving genuine alternatives.

The successful tests are controlled algorithmic checks, not scientific proof of correctness on every input. Bounded exhaustive/analytic oracles and malformed-input regression tests provide stronger evidence than agreement between two copies of the same algorithm. Supplied priorities, marginals, constraints, rule heads/bodies and external facts are not automatically discovered or verified. H3 adds synthetic exposure and idealized review to already inspected data. No new paper corpus, independently adjudicated semantic labels, live workload trace, measured reviewer outcome, external baseline implementation or prospective Jev latency panel was collected. No confidence interval from H3 should be assigned to H1/H2/H4/H5 operation counts.

An independent semantic experiment would need the entire policy frozen before a new source-disjoint corpus, verified provenance/qualifiers, actual query utility, calibrated primitive events, and matched evidence/resource budgets against systems such as KARMA. Those experiments remain unexecuted here. The present changes add research modules and evidence only; the default graph compiler and archived original study remain unchanged.

## 8. Reproducibility and evidence links

The [protocol](PROTOCOL.md), [methods](methods.py), [runner](run.py), [regression tests](tests/test_methods.py), [results](results.json), [summary table](summary.csv), [claim map](CLAIM_EVIDENCE.md), [bibliography](references.bib) and [artifact manifest](artifact-manifest.json) form the extension package. The original evidence verifier checks all 161 archived files. The generated complete manuscript retains every preceding study and its limitations.

```bash
python -m pip install -r graph_synthesis/assumption_aware/requirements.txt
python -B -m unittest discover -s graph_synthesis/assumption_aware/tests -v
python -B -m graph_synthesis.assumption_aware.run --check
python -B -m graph_synthesis.assumption_aware.report --figures --update-paper
python -B -m graph_synthesis.render_current_paper --output manuscript/paper-current.pdf
```

Running without `--check` intentionally regenerates results. Network connection methods are blocked during benchmark execution; saved API failures remain charged in source evidence. Fixtures, updates, endpoint witnesses, fits, exposure weights, selected review IDs, bootstrap intervals, resource boundaries and source hashes are retained. Result replay checks exact structure/counts and narrowly bounded floating-point differences; the PDF build manifest binds the mutable full-paper source, renderer and PDF. The extension manifest excludes its own hash and does not rewrite earlier study manifests.
