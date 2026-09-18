# Reliability ranking, source diversity and bounded exact inference for Jev graph synthesis

Timothy Wayne Gregg | AI-assisted author-review research extension | September 18, 2026

## Abstract

Five refinements follow the latest risk-controlled experiments. Source-balanced reliability ranking reduces wrong accepted edges from 17 to 15 at an equal volume of 145 edges, but the 11.76% reduction misses the frozen 20% target. Source diversification covers more source groups but retains fewer correct edges and contaminates more groups. Dependence-robust review allocation meets its mathematical objective yet worsens the observed-label reviewer simulation at the primary budget. Bounded exact lineage inference recovers 16 controlled high-probability admissions lost by conservative bounds, without an oracle error. Feedback-cutset conditioning extends exact conflict optimization to the tested cyclic components of up to 256 assertions. These last two successes concern supplied probability and priority models, not improved scientific extraction or factual truth. No fresh Jev calls, independent semantic validation or production-policy change is claimed.

## 1. Research motivation and evidence boundary

The [preceding risk-control study](../risk_control/RESULTS.md) exposed a useful distinction: reliable execution, estimated risk, structural consistency and factual correctness are different properties. Its economical routing guard rejected every learned candidate, source-risk gating lost substantial correct-edge coverage, qualifier checks supplied no valid veto, and review risk estimates were optimistic. The controlled forest solver succeeded but staged large cyclic components. The [earlier follow-up](../followup/RESULTS.md) supplied conservative probability bounds for shared proof lineage. These findings motivate different acceptance rankings and exact downstream inference instead of another correlated vote.

The [protocol](PROTOCOL.md) was committed as `466c3dadffee223d67eb06e2ad1032155fc84430` before these new policies were executed, against baseline `338981392c77f4771cdbb58a9f8c90fd723da64a`. Earlier aggregate results and test cases had already been inspected. This is a frozen exploratory follow-up, not an independent preregistration. H1-H3 reuse authentic captured requests and responses: 73 development candidates in 40 source groups and 263 evaluation candidates in 149 groups. Fitting uses development labels only; selection interfaces receive no gold labels. Raw-response reconstruction, hashes and source-group separation pass before analysis.

**Fresh service calls: 0.** The historical 3,024 calls are not counted again. H1-H2 are counterfactual selection over the single-rich capture. H3 is an analytic simulation using assumed reviewer sensitivity and false-removal rates. H4-H5 compare controlled algorithms with independent finite or analytic oracles. No benchmark here evaluates candidate discovery, source extraction, a live human reviewer, an external system such as KARMA, or unattended database writes.

An accepted edge is a valid SUPPORTS or REFUTES prediction. It is correct only when its polarity equals the gold label. A wrong polarity is both a wrong accepted edge and a missed gold edge. NOT_ENOUGH_INFO and operational errors are not accepted edges. Source groups are dependence units derived from source identifiers, not measured graph-connected components. A represented group contains an accepted edge; a contaminated group contains at least one wrong accepted edge.

## 2. Frozen primary criteria

| Hypothesis | Required conjunction | Executed outcome |
|---|---|---|
| H1: Reliability ranking | At K=145: at least 20% fewer wrong edges, at least 95% natural correct-edge retention, no fewer source groups | Not met |
| H2: Source-diverse acceptance | At K=100: at least 10% more source groups, at least 98% correct-edge retention, no extra contaminated groups | Not met |
| H3: Dependence-robust review | At budget 20: strictly fewer expected contaminated observed groups, no fewer expected correct edges, no worse union-bound objective | Not met |
| H4: Exact shared lineage | All finite/analytic oracles and invariance checks pass; recover at least one valid 0.95 admission without false admissions | Met, controlled algorithms only |
| H5: Feedback-cutset conflicts | All finite/analytic oracles and order checks pass; no prior utility regression; all 16 large cycles exact and unstaged | Met, controlled algorithms only |

Each target is a conjunction, not an invitation to substitute a favorable secondary metric. Target indicators are engineering criteria, not statistical discoveries. The two evidence types must not be pooled into a semantic success percentage.

## 3. H1: Source-balanced empirical reliability ranking

The policy changes acceptance order rather than requesting another answer. Six bins combine predicted polarity with score intervals [0,0.90), [0.90,0.99) and [0.99,1]. Every development source group with positive predictions contributes total edge weight one. A Beta(1,1)-smoothed global correctness mean supplies four pseudo-observations per bin. Unseen bins use the global mean. Selection orders estimated bin reliability, raw score and finally ID. The unweighted-fit ablation uses the same bins and smoothing without source balancing. No evaluation outcome chooses a parameter.

This exploits label-conditional reliability differences without assuming that raw confidence is calibrated. The fitted global mean is 0.90; bin estimates range from about 0.683 to 0.968. These small-sample estimates are ranking features, not deployment-certified probabilities. Calibration and decision ranking are distinct: a score transformation can alter acceptance order without improving all proper scoring rules. See [Guo et al., On Calibration of Modern Neural Networks](https://proceedings.mlr.press/v70/guo17a.html) for the general calibration distinction, not evidence validating this specific ranking.

| Accepted budget | Policy | Correct / wrong edges | Represented / contaminated groups |
|---:|---|---:|---:|
| 100 | raw | 92 / 8 | 69 / 6 |
| 100 | balanced | 89 / 11 | 74 / 11 |
| 100 | unweighted | 93 / 7 | 74 / 7 |
| 125 | raw | 114 / 11 | 83 / 9 |
| 125 | balanced | 111 / 14 | 84 / 12 |
| 125 | unweighted | 111 / 14 | 84 / 12 |
| 145 | raw | 128 / 17 | 95 / 15 |
| 145 | balanced | 130 / 15 | 95 / 13 |
| 145 | unweighted | 130 / 15 | 95 / 13 |

At the primary budget, the balanced and unweighted variants both retain 130 correct edges, versus 128 for confidence ranking. Balanced retention is 98.48% of the natural single-rich baseline's 132 correct edges. Represented groups remain 95. However, reducing 17 mistakes to 15 is only 11.76%, below 20%, so H1 fails. At K=100 the balanced fit is worse than both raw confidence and the unweighted ablation. Source balancing therefore cannot be credited with a general improvement.

The fixed-selection balanced-minus-raw precision difference at K=145 has descriptive 95% interval [+0.00, +3.48] percentage points and 99% interval [-0.09, +4.32] points. The former touches zero and the latter crosses it. These intervals do not establish a resolved independent accuracy effect. All variants require the same 263 captured single-rich calls and 941,809 recorded input tokens; this is not a token-saving method.

![H1. Wrong edges at equal accepted volume; the frozen 20% reduction remains unmet.](figures/01_reliability_ranking.png)

## 4. H2: Diminishing-return source diversification

The separate diversity policy repeatedly selects the positive prediction maximizing raw_score / (1 + already_selected_in_source), with raw-score and ID tie-breaking. It does not train on labels or change predictions. The premise is that spreading a limited acceptance budget across sources might improve useful coverage without sacrificing correctness.

| Accepted budget | Confidence: correct / wrong; groups / contaminated | Diverse: correct / wrong; groups / contaminated |
|---:|---:|---:|
| 100 | 92 / 8; 69 / 6 | 85 / 15; 98 / 15 |
| 125 | 114 / 11; 83 / 9 | 108 / 17; 98 / 15 |
| 145 | 128 / 17; 95 / 15 | 127 / 18; 98 / 15 |

At K=100, coverage rises from 69 to 98 represented groups (42.03%), but correct edges fall from 92 to 85. Retention is only 92.39%, below 98%. Contaminated groups increase from 6 to 15. H2 fails despite the favorable coverage count. At larger budgets the correctness penalty narrows, but no diagnostic budget replaces the primary test.

The mechanism is visible in the policy: a high-confidence second edge in one source can be displaced by a less reliable first edge in another. Coverage is a design preference, not a free accuracy gain. Source-group coverage is not graph-node recall, relationship diversity or recovered scientific knowledge. The ranking still consumes the same full single-rich acquisition budget.

![H2. Budget labels show the tradeoff between represented sources and correct edges.](figures/02_source_coverage.png)

## 5. H3: Review allocation robust to dependence, conditional on valid marginals

For residual edge-error marginals q_i, the probability of any error in a group lies between max(q_i) and min(1, sum(q_i)). The prior independent estimate 1 - product(1-q_i) lies between those bounds. A review multiplies its edge marginal by 1-s, where assumed sensitivity s=0.75. Group-budget dynamic programming minimizes the sum of the upper envelopes. For a fixed review count within a group, reviewing its highest-risk edges minimizes the residual sum; enumerating all group counts then yields the exact global allocation for this supplied objective. This establishes optimality of the modeled allocation, not correctness of the supplied risks.

The development-only risk features and acquisition charges are unchanged from the previous independent-risk optimizer. False removal of a correct reviewed edge is assumed to be 0.05 and measured in the outcome simulation, not included in the allocation objective. Exact subset enumeration on 64 eight-edge fixtures finds zero objective failures. Enumeration of 64 four-edge joint distributions, including dependent errors, finds zero containment failures. These checks validate arithmetic under supplied marginals. A miscalibration control supplies four marginals of 0.01 although the actual union event has probability one: the computed upper envelope 0.04 is then invalid for truth. Removing an independence assumption cannot repair inaccurate marginal estimates.

| Reviews | Independent allocation: expected contaminated / correct | Robust allocation: expected contaminated / correct | Fitted upper envelope (both) |
|---:|---:|---:|---:|
| 10 | 12.7500 / 131.70 | 12.7500 / 131.70 | 4.5364 |
| 20 | 10.6875 / 131.35 | 12.1875 / 131.25 | 4.0978 |
| 30 | 9.1875 / 130.95 | 10.6875 / 130.85 | 3.8786 |
| 40 | 9.1875 / 130.45 | 9.1875 / 130.45 | 3.6593 |

At the primary budget 20, the robust allocation leaves 12.1875 expected contaminated groups, versus 10.6875, and retains 131.25 rather than 131.35 expected correct edges. H3 fails. Both allocations tie the fitted upper-envelope objective, so a different optimum can still be worse under the observed-label simulation. The fitted upper envelope near 4.10 is far below either simulation outcome; it is not a calibrated empirical upper confidence bound.

Risk-feature acquisition requires 1,274,247 recorded input tokens before reviewer cost. The stored sensitivity analysis crosses s in {0.5,0.75,1} with false-removal rates {0,0.01,0.05}, keeping selected IDs fixed. These are expectations under assumed independent reviewer detections, not measured human trials or guarantees about correlated reviewer mistakes.

![H3. Observed-label reviewer simulations diverge despite equal modeled robust objectives.](figures/03_review_allocation.png)

## 6. H4: Bounded exact inference over shared proof lineage

A sufficient proof is a conjunction of explicitly supplied primitive Bernoulli events. The accepted assertion is the disjunction of its sufficient proofs. The previous component bounds deduplicate and account conservatively for shared atoms, but can be too loose for admission. The refinement canonicalizes proof clauses, absorbs supersets, and applies Shannon decomposition: P(F) = p_a P(F | a=true) + (1-p_a) P(F | a=false). The most frequent atom is conditioned first, with lexical tie-breaking; canonical residual formulas are memoized. Shared proofs are never treated as independent witnesses.

The exactness follows by the law of total probability and independence of the supplied primitive atoms, not independence of clauses. This is an application of established Boolean/probabilistic inference rather than a newly invented theorem. [Darwiche and Marquis, A Knowledge Compilation Map](https://arxiv.org/abs/1106.1819) situates representation/tractability tradeoffs; [Fink, Han and Olteanu, Aggregation in Probabilistic Databases via Knowledge Compilation](https://arxiv.org/abs/1201.6569) provides related probabilistic-database context. Neither reference validates Jev scores as source reliabilities.

All 128 seeded eight-atom fixtures match full possible-world enumeration within 1e-10. All 512 duplicate/order checks pass. Eight larger shared-hub fixtures also match the analytic probability 0.99 * (1 - 0.5^(n-1)). Their atoms are the independent hub and leaves; proofs share the hub. The old lower bound stays 0.495 while exact probabilities exceed the 0.95 admission threshold.

| Primitive atoms | Old lower bound | Exact / analytic probability | Memoized states |
|---:|---:|---:|---:|
| 8 | 0.495000 | 0.982265625 | 10 |
| 16 | 0.495000 | 0.989969788 | 18 |
| 32 | 0.495000 | 0.990000000 | 34 |
| 64 | 0.495000 | 0.990000000 | 66 |
| 96 | 0.495000 | 0.990000000 | 98 |
| 128 | 0.495000 | 0.990000000 | 130 |
| 192 | 0.495000 | 0.990000000 | 194 |
| 256 | 0.495000 | 0.990000000 | 258 |

Across the 128 finite fixtures and eight analytic fixtures, exact inference recovers 16 oracle-valid admissions that the old lower bound would withhold, with 0 false admissions. H4 meets its controlled target. The endpoint counts fixtures, not newly discovered scientific graph edges. Values rounded to 0.99 in the table retain normal floating-point limitations; no symbolic exact-arithmetic claim is made.

The implementation caps supplied atoms at 256, input proofs at 512 and memoized residual states at 4,096. On input/state exhaustion it returns the prior valid bounds with nonexact status and no point probability. The one-state control returns [0.25,0.50], containing the exact probability 0.375. This finite cap is a safety boundary, not a polynomial-time guarantee for arbitrary Boolean formulas. A corrupted-lineage control declares two aliases of the same 0.9 event independent and obtains 0.99 instead of 0.9. Incorrect primitive identity or uncalibrated reliability can therefore invalidate apparently precise answers. Raw Jev confidence is not promoted to primitive reliability.

![H4. Eight controlled shared-hub families resolve the old lower-bound abstention.](figures/04_exact_lineage.png)

## 7. H5: Feedback-cutset conditioning for cyclic conflicts

The prior solver handled forest components by exact dynamic programming, cyclic components of at most 16 vertices by enumeration, and staged larger cycles. The refinement finds a bounded feedback set by repeatedly removing a deterministic maximum-degree vertex from the current cycle-containing 2-core. If at most four removals leave a forest, every independent assignment of the cutset is enumerated. For each assignment, selected cutset vertices exclude their neighbors and the residual forest is solved exactly. Maximizing across these assignments is exact for the supplied weighted independent-set problem because every feasible solution has one enumerated cutset assignment.

Cutset discovery is a heuristic: failing its four-removal cap does not prove that the graph lacks a smaller feedback vertex set. Such failures retain the prior solver behavior, including exact small-component fallback and explicit staging. Components over 256 vertices remain staged. No asymptotic improvement is claimed for conflict construction, and the generic graph backend does not establish that these cyclic topologies arise in a particular scientific corpus.

All 128 seeded ten-vertex graphs agree with exhaustive subset enumeration, have consistent selected sets, and never regress below prior utility. All 256 input-order checks pass. Sixteen large uniform/weighted cycles agree with an independently implemented two-path recurrence; the prior solver stages every one of them.

| Cycle vertices | Uniform: new / oracle | Weighted: new / oracle | Prior utility (both) |
|---:|---:|---:|---:|
| 17 | 8 / 8 | 60 / 60 | 0 |
| 24 | 12 / 12 | 84 / 84 | 0 |
| 32 | 16 / 16 | 114 / 114 | 0 |
| 48 | 24 / 24 | 171 / 171 | 0 |
| 64 | 32 / 32 | 221 / 221 | 0 |
| 96 | 48 / 48 | 333 / 333 | 0 |
| 128 | 64 / 64 | 447 / 447 | 0 |
| 256 | 128 / 128 | 882 / 882 | 0 |

H5 meets its controlled target. The 17-clique cap control stages all 17 vertices, and the 257-cycle control stages all 257. A semantic control offers two conflicting assertions with priorities nine and eight and marks the higher-priority assertion false. The exact solver still chooses the false assertion. Optimal priority retention and consistency are not factual validation. This extension changes research-only solvers, not the default graph compiler.

![H5. Weighted cycle utility equals the independent oracle beyond the prior cyclic cap.](figures/05_cutset_capacity.png)

## 8. Uncertainty, limitations and next discriminating evidence

H1-H2 use 4,000 paired source-group bootstrap draws, seed 20260921. Fitted rankings and accepted IDs are fixed in each resample. Reported 95% and 99% percentile intervals are descriptive, not simultaneous; they omit fitting uncertainty and cannot undo prior test exposure. No result is an independent confirmatory p-value. Repeated model responses are not new independent labels, and source groups do not remove every possible dependency or public-corpus training overlap.

The strongest semantic lead is a small equal-volume ranking improvement, not a validated deployment policy. The strongest controlled improvements exploit structure already supplied to the algorithm. They require independently credible primitive reliabilities, correct provenance and well-specified conflict priorities. Larger candidate sets, diverse real graph topologies, externally adjudicated edge truth and fresh source-disjoint evaluations remain necessary before translating those gains into claims about Jev-assisted graph synthesis. A matched-evidence comparison with [KARMA](https://arxiv.org/abs/2502.06472) has not been run here.

A discriminating next semantic experiment should freeze the ranking before obtaining new independently adjudicated source groups, compare it with raw-confidence ranking at matched accepted volume and acquisition cost, and report source coverage alongside correct and wrong edges. A next systems experiment should preserve a real extracted provenance/conflict graph, blind its truth labels during policy selection, and measure cap/staging frequency and wall-clock cost. Those are future evidence requirements, not unexecuted results represented as complete.

## 9. Reproduction and claim audit

Run `python -B -m graph_synthesis.structural.run --check` to reconstruct inputs and reproduce all five outcomes without service access. Run `python -B -m unittest discover -s graph_synthesis/structural/tests -v` for implementation regressions. Run `python -B -m graph_synthesis.structural.report --figures --update-paper` to regenerate this report, five PNG/SVG figures and the additive current-paper section. The shared renderer then builds the full HTML/PDF, and its build record binds manuscript, renderer and PDF SHA-256 hashes.

`results.json` retains fitted parameters, selected IDs, all finite fixtures, oracle outputs, control failures, descriptive intervals and reviewer sensitivities. `summary.csv` records all equal-volume policy comparisons. `artifact-manifest.json` binds extension files without rewriting archived evidence. [CLAIM_EVIDENCE.md](CLAIM_EVIDENCE.md) maps each conclusion to its evidence and forbidden extrapolation. Environment files distinguish local execution from CI. The original 161-file study and earlier extension outputs remain intact. The full manuscript remains an author-review draft.
