# Source risk, review budgets and structural certificates for Jev graph synthesis

Timothy Wayne Gregg | AI-assisted author-review research extension | September 18, 2026

## Abstract

Five follow-up hypotheses test whether the limitations exposed by PR #17 can be reduced. Direct source-event shrinkage increases evaluation Brier from 0.128923 to 0.138249; the calibration target is not met. Setup-cost-aware review leaves 12.1875 expected contaminated groups versus 11.4375 for greedy review at the same hypothetical budget; its target is not met. Frontier lineage evaluation, certified bipartite conflict optimization and revision-checked source invalidation meet their controlled algorithmic targets. The cache reduces fact reevaluations by 98.83% on local updates, but by 0.00% when a shared source affects every fact. These are replay, simulation and algorithm results, not new Jev calls, human-review measurements or independent semantic validation.

## 1. Research questions and frozen evaluation

The [preceding reliability study](../reliability/RESULTS.md) found that a group-risk multiplier improved mean bias but worsened Brier, and that single-view review features could save acquisition tokens. Its structural experiments also exposed a 16-atom lineage boundary, a four-vertex conflict-cutset boundary, and update-locality limits. This extension changes the risk model, explicitly prices review setup, and broadens the tractable structural cases. It applies established shrinkage, dynamic programming, max-flow/min-cut and dependency indexing rather than claiming a new mathematical algorithm.

The [protocol](PROTOCOL.md) was committed before execution as `b92009c6c36d87d9f3cbf0c92c2dad9f9615d726`, against baseline `a62a3257645d8e35cd4e45be53bfa9511d27724b`. Previous evaluation outcomes informed the hypotheses: this is an exploratory, pre-execution commitment, not an independent preregistration. H1/H2 reuse 73 development candidates in 40 connected source groups and 263 evaluation candidates in 149 groups. The original claim/document/duplicate-abstract grouping is preserved. A source group is not necessarily one document. In H2, setup is therefore charged per connected group, not per physical document opened. These hypothetical units cannot establish actual reviewer costs.

Raw responses and input hashes are verified before reconstruction. Development and evaluation groups are disjoint; policy inference receives no evaluation gold. **Fresh service calls: 0.** Earlier public test-set inspection still prevents independent confirmation. No production graph policy is changed.

| Hypothesis | Frozen primary criterion | Outcome | Evidence class |
|---|---|---|---|
| H1: Direct source-event shrinkage | 10% lower Brier than both prior models; absolute bias <=0.03 | Not met | Archived prediction scoring |
| H2: Setup-cost-aware review | At least 0.5 fewer expected contaminated groups; <=0.1 extra correct removals; budget respected | Not met | Label-evaluated review simulation |
| H3: Frontier-bounded lineage | No finite-oracle or invariance errors; ten large analytic cases exact; one interval tightened | Met | Supplied independent-event model |
| H4: Certified bipartite conflict solving | No small-case regression; ten certified large optima; at least four utility gains | Met | Supplied conflict graphs and priorities |
| H5: Revision-checked evidence cache | No stale values or atomicity failures; at least 90% fewer local fact reevaluations | Met | Sequential in-memory mutations |

Passing three algorithmic targets does not amount to a three-out-of-five semantic success rate. The two unsuccessful predictive/review hypotheses and all assumption-breaking controls remain part of the results.

## 2. H1: Direct source-event shrinkage

The response variable is whether a connected group contains any incorrect base1-accepted SUPPORTS or REFUTES edge. Empty accepted groups are excluded. The proposed estimator uses two binary features: at least two accepted edges, and any accepted score below 0.90 (a missing score is treated conservatively as low). For cell c, the estimate is (errors_c + alpha * prior)/(n_c + alpha), with a Beta(1,1)-smoothed global group-error prior. Alpha is chosen from {1,4,16} by leave-one-development-group-out Brier; exact ties favor stronger shrinkage. This targets the group event directly instead of multiplying estimated edge-correctness probabilities.

| Model | Brier | Log loss | Predicted risk | Observed risk | Bias |
|---|---:|---:|---:|---:|---:|
| Prior product | 0.128923 | 0.467074 | 8.04% | 15.31% | -7.26% |
| Prior scaled product | 0.134900 | 0.441344 | 13.64% | 15.31% | -1.67% |
| Direct source event | 0.138249 | 0.484622 | 8.49% | 15.31% | -6.81% |

There are 23 nonempty development groups and 98 nonempty evaluation groups. The chosen alpha is 4; the preceding development-selected multiplier is 2. Direct-minus-product Brier has descriptive 95% interval [-0.0140, +0.0363] and 99% interval [-0.0199, +0.0447]. Against the scaled product, the intervals are [-0.0326, +0.0432] and [-0.0429, +0.0574]. Neither a lower Brier nor the required bias is achieved: **not met**.

The small number of contaminated development groups makes cell estimation difficult. Directly predicting the desired event is a plausible modeling choice, but it is not a guarantee of better calibration. This experiment does not justify deploying the new estimator.

![H1. Source-event Brier on identical accepted evaluation groups; lower is better.](figures/01_source_risk.png)

## 3. H2: Review allocation with group setup costs

Both policies use the preceding single-view edge-risk fit. The comparator follows its group-aware greedy edge order and admits each edge only if the remaining budget covers the edge plus any newly required group setup. The proposed multiple-choice knapsack offers each group either no review or its top-k risk-ranked edges. It maximizes the increase in predicted group-clean probability under independent edge errors and independent reviewer detection. Gold labels enter only the subsequent outcome calculation. The optimizer is exact over these prefix options, not over every possible human review action.

The primary budget is 40 units: opening a connected group costs 2 and reviewing one edge costs 1. Detection is 0.75 and false removal of a correct reviewed edge is 0.01. These parameters are supplied assumptions, not observed reviewer behavior. Expected contamination counts a group if at least one incorrect accepted edge remains; a reviewer cannot add an omitted correct edge.

| Policy | Spent | Reviewed | Wrong reviewed | Expected contaminated groups | Expected correct removals |
|---|---:|---:|---:|---:|---:|
| Group-greedy | 40 | 14 | 6 | 11.4375 | 0.08 |
| Source-batched knapsack | 40 | 18 | 5 | 12.1875 | 0.13 |

The proposed policy reviews more edges but leaves 0.75 more expected contaminated groups, not at least 0.5 fewer. Its primary target is **not met**. The proposed-minus-greedy expected contamination-rate difference has descriptive 95% interval [+0.0000, +1.5101] pp and 99% interval [+0.0000, +2.0134] pp across all 149 evaluation groups.

There are 0 failures in 64 independently enumerated small knapsack tests and 0 budget violations in 108 fixed sensitivity scenarios. The full grid crosses budgets {20,40,80}, setup costs {0,1,2,5}, detection {0.5,0.75,1} and false removal {0,0.01,0.05}. A perfectly correlated within-group detection control gives 12.00 versus 11.25 expected contaminated groups at the primary setting. It also fails to reverse the unfavorable ordering.

Both policies use the same 941,809 recorded single-view input tokens, charged separately from hypothetical review units. Correct optimization of a misspecified risk objective need not improve label-evaluated outcomes. No human-time, dollar-cost, reviewer-quality or semantic noninferiority claim follows.

![H2. Simulated contamination at equal total budgets, with fixed setup and reviewer assumptions.](figures/02_review_budget.png)

## 4. H3: Frontier-bounded exact lineage

A fact is a disjunction of proof conjunctions over supplied independent Bernoulli primitives. After removing duplicate and subsumed proofs, the proposed iterative dynamic program processes sorted primitive IDs. It remembers only processed atoms used in unfinished proofs. Once a proof succeeds, its probability mass is absorbed into the success total, preventing double-counting of shared evidence. Constants, impossible primitives and certain primitives are explicit cases. This is a bounded-width inference strategy, not an assertion that document sources are independent.

The new path caps used atoms at 256, canonical proofs at 1,024, frontier width at 12 and state transitions at 65,536. Exceeding a cap delegates to the previous small-component exact/bounded routine. Partially evaluated mass is never reported as an exact answer. These caps bound the new frontier evaluation, not all validation, canonicalization or fallback work.

Independent assignment enumeration finds 0 errors beyond 1e-12 on 192 random fixtures with 2-10 atoms. There are 0 failures in 768 order/duplicate checks and 0 false lower-bound admissions at threshold 0.95. All 10 large path/cycle cases match an independent no-adjacent-success recurrence; 10 tighten the previous interval. The primary controlled target is **met**.

| Lineage | Atoms | Prior interval | Exact probability | Frontier width | Transitions |
|---|---:|---|---:|---:|---:|
| path | 17 | [0.0100, 0.1600] | 0.137675 | 1 | 66 |
| path | 32 | [0.0100, 0.3100] | 0.248938 | 1 | 126 |
| path | 64 | [0.0100, 0.6300] | 0.440647 | 1 | 254 |
| path | 128 | [0.0100, 1.0000] | 0.689753 | 1 | 510 |
| path | 256 | [0.0100, 1.0000] | 0.904556 | 1 | 1022 |
| cycle | 17 | [0.0100, 0.1700] | 0.144922 | 2 | 124 |
| cycle | 32 | [0.0100, 0.3200] | 0.255250 | 2 | 244 |
| cycle | 64 | [0.0100, 0.6400] | 0.445348 | 2 | 500 |
| cycle | 128 | [0.0100, 1.0000] | 0.692361 | 2 | 1012 |
| cycle | 256 | [0.0100, 1.0000] | 0.905358 | 2 | 2036 |

Each large fixture uses primitive probability 0.1 and adjacent-pair proofs. Dense 17-atom lineage triggers the width fallback; a 257-atom input and a deliberately tiny state budget exercise other guards. The shared-source control still yields 0.96 instead of the actual 0.8 when one source is incorrectly encoded as two independent primitives. Better exact inference cannot repair false provenance, and the supplied probabilities are not calibrated Jev truth probabilities.

![H3. Prior conservative intervals and exact frontier probabilities on large connected lineages.](figures/03_frontier_lineage.png)

## 5. H4: Certified bipartite conflict optimization

The input is an explicit undirected conflict graph with nonnegative integer priorities. On a bipartite component, maximum-weight independent set is reduced to minimum-weight vertex cover and solved by an integer max-flow/min-cut routine. The result includes a feasible flow and a vertex cover of equal weight. A separate verifier checks endpoints, capacities, conservation, cover feasibility, selection consistency and objective equality. This certificate proves the supplied combinatorial objective, not the truth of selected assertions.

Components remain capped at 256 vertices. Nonbipartite components delegate to the preceding cycle-cutset policy. A 2,000,000 residual-edge-inspection budget bounds the new flow solver; exhaustion delegates rather than certifying an unfinished answer. No external graph-system benchmark or extracted real-world conflict graph is substituted for these controlled cases.

There are 0 finite-oracle/consistency/regression failures among 192 random small graphs and 0 failures in 768 input-order checks. All 10 large cases attain independently known optima with valid certificates; 10 improve supplied utility over the prior staging policy. The primary controlled target is **met**.

| Conflict family | Vertices | Prior utility | Certified utility | Analytic optimum |
|---|---:|---:|---:|---:|
| grid | 25 | 0 | 13 | 13 |
| grid | 36 | 0 | 18 | 18 |
| grid | 64 | 0 | 32 | 32 |
| grid | 144 | 0 | 72 | 72 |
| grid | 256 | 0 | 128 | 128 |
| complete_bipartite | 18 | 0 | 45 | 45 |
| complete_bipartite | 32 | 0 | 80 | 80 |
| complete_bipartite | 64 | 0 | 160 | 160 |
| complete_bipartite | 128 | 0 | 320 | 320 |
| complete_bipartite | 256 | 0 | 640 | 640 |

Square grids use unit priorities and have optimum ceil(vertices/2). Complete balanced bipartite fixtures use priority 5 on one side and 3 on the other, with optimum five times the side size. These are specifically tractable families that exceeded the preceding four-cutset allowance, not representative samples of arbitrary graph-synthesis conflicts. Dense nonbipartite 17-clique staging, zero priorities, invalid inputs, work-budget exhaustion and damaged flow certificates are retained as controls. A false assertion of priority 9 still defeats a conflicting true assertion of priority 8; structural optimality is not factual accuracy.

![H4. Certified optimization reaches analytic objectives where the previous bounded policy staged.](figures/04_bipartite_certificate.png)

## 6. H5: Revision-checked evidence invalidation

The prototype indexes each primitive to the facts whose canonical proofs depend on it. Probability changes reevaluate only those facts; proof replacement, insertion and deletion maintain the reverse index. Revocation is an explicit probability-zero update. Optimistic revision checks, input validation and all potentially failing evaluations run before state mutation. Stale revisions, invalid changes and injected evaluation failures are rejected without changing the prior snapshot. This is sequential in-memory behavior, not concurrent database isolation, crash recovery or durability.

Across 640 seeded source/proof/fact mutations, explicit retraction and restoration controls, and both work-count workloads, there are 0 cache/full-recomputation mismatches. All 7 atomic rejection controls pass. The primary controlled target is **met**.

| Workload | Facts | Updates | Full evaluations | Incremental evaluations | Reduction | Index touches |
|---|---:|---:|---:|---:|---:|---:|
| Local source updates | 128 | 256 | 32,896 | 384 | 98.83% | 896 |
| Global shared source | 128 | 16 | 2,176 | 2,176 | 0.00% | 2,448 |

Both counts include the cold build. Each local fact has two proofs over three private primitives; the global control makes every fact depend on one shared source. Dependency-index touches count index construction/maintenance separately. These metrics omit general interpreter, allocation, validation and snapshot-comparison work; no matching percentage reduction in total CPU time, database I/O or service latency is claimed. A fact reevaluation can itself have variable lineage complexity.

![H5. Fact reevaluation work falls for local evidence updates, not global dependencies.](figures/05_source_cache.png)

## 7. Interpretation and limits

H1/H2 use 4,000 paired source-group bootstrap draws, seed 20260922, with fixed fitted models, chosen hyperparameters and review selections. The 95% and 99% percentile intervals are descriptive, non-simultaneous and omit fitting uncertainty. H1 uses the 98 identical nonempty accepted evaluation groups; H2 uses all 149 groups. Earlier reuse of these evaluation labels means the intervals are not prospective validation of hypotheses selected from previous results.

The central finding is a separation: broader exact structural inference and safe local invalidation are achievable under supplied assumptions, while better source-risk estimates and useful cost-aware review are not established by these data. The structural methods remain opt-in research infrastructure. They do not remedy missing candidate edges, wrong relation qualifiers, correlated Jev errors, false provenance or untrustworthy priorities. A future semantic study should freeze policy before seeing an independently adjudicated, source-disjoint corpus, use matched information/resource budgets, and measure actual reviewer behavior and end-to-end latency. No advantage over KARMA or another external system is established here.

## 8. Reproduction and attribution

```bash
python -B -m graph_synthesis.source_structural.run
python -B -m unittest discover -s graph_synthesis/source_structural/tests -v
python -B -m graph_synthesis.source_structural.run --check
python -B -m graph_synthesis.source_structural.report --figures --update-paper
python -B -m graph_synthesis.render_current_paper --output manuscript/paper-current.pdf
```

The [machine-readable results](results.json) contain folds, fitted cell counts, individual group probabilities, review selections, all sensitivity settings, finite/analytic oracles, flow certificates, mutation traces and source hashes. The [summary table](summary.csv), five SVG/PNG figure pairs and this report are generated from those results. The extension manifest binds code, evidence, figures and captured validation logs; the current paper has a separate build manifest. The original frozen study and all previous executed sections are preserved.

Primary-source context: [TypeSafe documentation](https://docs.typesafe.ai/introduction) describes typed decisions and probability outputs; [Amarilli et al., Connecting Knowledge Compilation Classes and Width Parameters](https://arxiv.org/abs/1811.02944) provides bounded-width knowledge-compilation context; the [NetworkX minimum-cut documentation](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.flow.minimum_cut.html) states the max-flow/min-cut relation. These sources motivate established techniques, not the numerical results reported here. Our finite and analytic checks are included in the repository; no claim of mathematical novelty is made.
