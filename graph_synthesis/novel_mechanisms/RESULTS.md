# Five new mechanisms for evidence-preserving Jev graph synthesis

Timothy Wayne Gregg | AI-assisted author-review research extension | September 18, 2026

## Abstract

Five mechanisms not previously tested in this repository are evaluated under a protocol committed before execution. Unlabeled label-shift correction ties the single-view baseline at 150 emitted edges: both produce 18 errors, missing the frozen 20% reduction target. Dependence-robust lineage bounds prevent a false independence-based admission in a correlated-source control, at the cost of wider uncertainty intervals. Protected-fact repair improves on greedy intervention in 13/82 feasible seeded fixtures. Bipartite min-cut optimization certifies the supplied-priority optimum in five dense components that the earlier cutset solver stages. Indexed conflict construction reduces semantic pair checks from 2,096,128 to 3,712 on 2,048 sparse assertions, with identical edges. These are exploratory saved-response and controlled algorithm results, not new Jev semantic observations or evidence of superiority to KARMA.

## 1. Motivation, novelty scope and protocol

The [latest reliability extension](../reliability/RESULTS.md) exposed failed source-risk calibration, a false primitive-independence assumption, bounded cyclic-graph solving and global preprocessing excluded from solver-only incremental savings. The [frozen protocol](PROTOCOL.md) maps each new mechanism to the closest earlier experiment. Novelty means untried in the audited repository snapshot, not invented here or never attempted worldwide. Label-shift adaptation, probability bounds, hitting-set search, flow/cover duality and interval sweeps are established ideas; the contribution is this testable integration and its limitations.

The protocol commit is `b2a5ccbda2f511cf76aad4e3348a7a67fb1aabad`; the baseline is `a62a3257645d8e35cd4e45be53bfa9511d27724b`. H1 reuses 73 development cases in 40 source groups and 263 evaluation cases in 149 groups. These previously inspected evaluation data are not a fresh holdout. Authentic raw responses are reconstructed and hashes, IDs and source-group separation checked before scoring. **Fresh service calls: 0.** H2-H5 use supplied controlled inputs, not model-produced facts. No production graph policy or default compiler changes; the original evidence archive remains unchanged.

| Hypothesis | Frozen primary requirement | Outcome | Evidence |
|---|---|---|---|
| H1: Unlabeled label-shift correction | Retain >=98% of naturally correct edges and reduce matched-volume errors >=20% | Not met | Previously captured Jev responses |
| H2: Dependence-robust lineage certificates | No false certified admission or excluded truth; analytic agreement; prevent one independence error | Met | Supplied marginal and joint probabilities |
| H3: Protected-fact minimal repair | Oracle agreement, no greedy cost regression, improve >=5% of feasible cases | Met | Supplied proofs, protections and costs |
| H4: Bipartite conflict optimization | Oracle agreement, no previous-policy regression, solve every large bipartite fixture | Met | Supplied conflict graphs and priorities |
| H5: Indexed interval conflict construction | Exact edge/staging parity and >=95% fewer sparse pair checks | Met | Supplied typed interval assertions |

A target pass is a conjunction of engineering requirements, not a significance test. Do not pool the five outcomes into a semantic success percentage.

## 2. H1: Unlabeled label-shift correction

We fit a three-class hard-prediction confusion matrix on development labels, with one pseudo-count per predicted class in each true-class column. Source priors receive one pseudo-count per class. Target priors q minimize ||Cq-m|| squared + 0.01 ||q-p_source|| squared on the simplex; m uses only valid unlabeled target predictions. Enumerating all nonempty simplex faces avoids a local-search stopping criterion. Valid base1 probabilities are multiplied by q/p_source and normalized. Operational failures remain failures. Rank deficiency returns the unchanged predictor. This regularized BBSE-inspired method is not an exact reproduction of [Lipton, Wang and Smola (2018)](https://proceedings.mlr.press/v80/lipton18a.html), nor a guarantee of calibrated posteriors.

| Policy and volume | Emitted | Correct | Wrong | Precision | Recall over all 153 gold-positive candidates |
|---|---:|---:|---:|---:|---:|
| Single view, natural | 150 | 132 | 18 | 88.00% | 86.27% |
| Corrected, natural | 155 | 135 | 20 | 87.10% | 88.24% |
| Single view, matched | 150 | 132 | 18 | 88.00% | 86.27% |
| Corrected, matched | 150 | 132 | 18 | 88.00% | 86.27% |

Natural volume adds three correct edges and two wrong edges. At matched k=150, the primary error-reduction target is **not met**. Both policies retain one operational failure in the full 263-candidate denominator. The same 941,809 recorded input tokens are charged to each policy, including failed requests. No extra inference calls or invented monetary savings are claimed.

| Class | Development prior (smoothed) | Estimated target prior | Observed valid-target prior (evaluation only) |
|---|---:|---:|---:|
| SUPPORTS | 0.3553 | 0.4693 | 0.4275 |
| REFUTES | 0.1447 | 0.1186 | 0.1565 |
| NOT_ENOUGH_INFO | 0.5000 | 0.4121 | 0.4160 |

There are 262 valid target outputs. Target gold labels never enter fitting or reweighting; the observed prior is a diagnostic only. With fixed fit and selected ID sets, the paired source-group bootstrap gives corrected-minus-baseline precision intervals of [-1.765, +1.714] pp (95%) and [-2.361, +2.286] pp (99%). Wrong edges per candidate have intervals [-1.158, +1.141] pp and [-1.544, +1.527] pp. These descriptive, non-simultaneous intervals use 4,000 draws, seed 20260922; they omit fitting uncertainty and do not repair evaluation-set reuse.

The known-confusion control has prior L1 error 0.014667; changing the target conditional confusion increases it to 1.190667. Marginal adaptation is therefore not a remedy for arbitrary conditional shift or semantic errors.

![H1. Wrong emitted edges at natural and matched volume; lower is better.](figures/01_label_shift.png)

## 3. H2: Dependence-robust lineage certificates

A fact is a disjunction of conjunctive proofs. Instead of multiplying primitive marginals, enumerate Boolean worlds for at most eight atoms and constrain their nonnegative joint masses to match the supplied marginals and sum to one. Two linear programs minimize and maximize the fact indicator. We use [SciPy linear programming](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html), but do not trust a numerical success flag as a safety certificate: dual coefficients are converted to rational numbers, each inequality is checked over every world, and the constant is shifted outward if needed. Rational lower-bound comparison, not rounded display values, governs the 0.95 admission gate. Caps and solver failures return explicit conservative Frechet/union bounds. Certified bounds need not be numerically sharp on every input.

Across 128 seeded arbitrary joint-distribution fixtures, 0 certified intervals exclude supplied truth and 0 false lower-bound admissions occur. The 72 two-atom analytical AND/OR cases have 0 endpoint failures at tolerance 1e-8, with 0 duplicate/order failures. The controlled target is **met**. Mean interval width is 0.318428; this additional uncertainty is the price of removing independence, not a defect to hide.

| Correlated-source control | Probability or interval | Admitted at 0.95? |
|---|---:|---|
| Independence-assuming evaluator | 0.96 | Yes, incorrectly |
| Dependence-robust certificate | [0.80, 1.00] | No |
| Actual supplied joint truth | 0.80 | Below threshold |

The control contains two distinct primitive events that are perfectly correlated, each with marginal 0.8. The robust bound prevents the old false admission, but cannot certify an edge whose real dependence is unknown. Conversely, supplying a false marginal of 0.99 for an event whose actual probability is 0.8 still causes an incorrect admission. Certificates are conditional on correct marginals and proof semantics. Jev scores are not established truth marginals; TypeSafe probability outputs do not by themselves establish this assumption ([documentation](https://docs.typesafe.ai/introduction)).

![H2. Removing primitive independence prevents an unsupported admission, but widens the interval.](figures/02_dependence_bounds.png)

## 4. H3: Protected-fact minimal source repair

Instead of propagating a predetermined source withdrawal, the algorithm chooses a minimum-cost set intersecting every target proof while preserving at least one intact proof of each designated protected fact. It branches on an unhit target proof, prunes destroyed protections and dominated costs, and breaks ties by the sorted withdrawal tuple. A 16-atom and 65,536-state cap prevents an unfinished search from masquerading as an optimum: exhaustion stages the request. No sources are actually deleted.

An independent exhaustive subset oracle evaluates 128 seeded eight-atom fixtures. There are 82 feasible cases and 46 infeasible cases; feasibility, protection and optimum checks have 0 mismatches. Compared with cost-normalized greedy coverage that respects the same protections, 13/82 feasible cases (15.85%) have strictly lower cost or recover from a greedy dead end, exceeding the frozen 5% target. There are 0 cost regressions where greedy completes. The controlled target is **met**.

The fixed greedy trap withdraws a,b,c at cost 6, whereas the exact solution withdraws b,c at cost 4. A protected fact identical to the target makes repair infeasible; the algorithm refuses to silently sacrifice the protection. Costs are supplied positive integer units, not dollars or observed reviewer effort. Protected facts are designated by the fixture, not independently proven true.

![H3. Exact repair improves a subset of feasible cases; infeasible cases remain explicit.](figures/03_minimal_repair.png)

## 5. H4: Bipartite min-cut conflict optimization

For each bipartite component up to 256 vertices, a source/sink network computes minimum-weight vertex cover; its complement is a maximum-weight conflict-free assertion set. Cross-edge capacities exceed total priority. Integer max flow, cut capacity, cover membership and positive edge flows form a checkable objective certificate. Nonbipartite graphs retain the actual previous cutset/enumeration/staging implementation. This exploits a different tractable graph family rather than increasing an exponential search cap.

Across 128 small weighted bipartite fixtures and 32 general-graph controls, plus five analytical large cases, there are 0 oracle failures and 0 utility regressions against the previous solver. Duplicate/direction/order checks have 0 failures. The controlled target is **met**.

| Complete bipartite graph | Vertices | Prior cutset utility | Priority-greedy utility | Flow utility | Analytic optimum |
|---|---:|---:|---:|---:|---:|
| K(8,9) | 17 | 0 | 27 | 27 | 27 |
| K(16,16) | 32 | 0 | 48 | 48 | 48 |
| K(32,32) | 64 | 0 | 96 | 96 | 96 |
| K(64,64) | 128 | 0 | 192 | 192 | 192 |
| K(128,128) | 256 | 0 | 384 | 384 | 384 |

Left priorities are 2 and right priorities 3. Priority greedy also reaches the optimum on these large fixtures: the result is expanded certified coverage relative to the previous bounded solver, not superiority over every heuristic. A dense 17-clique still stages. A conflicting false assertion with priority 9 defeats a true assertion with priority 8: structural consistency and optimal supplied utility do not establish factual truth.

![H4. Dense bipartite components are solved beyond the prior cutset staging boundary.](figures/04_bipartite_capacity.png)

## 6. H5: Indexed interval conflict construction

Assertions are validated, partitioned by subject/predicate/scope, sorted by start time and swept with an expiry heap. Half-open intervals expire when end <= next start; None endpoints remain unbounded. Only simultaneously active assertions within a partition need semantic collision tests. Unsupported qualifiers stage, and duplicate or missing IDs are rejected. The baseline calls the existing pairwise conflict predicate on all supported pairs, including its per-pair validation. The indexed route validates once and hoists those repeated checks; both differences can affect runtime.

The 128 random cases include bounded/unbounded intervals, scope separation, opposing polarity, functional collisions and malformed qualifiers. There are 0 edge/staging mismatches, 0 failures against independent finite-instant truth, and 0 order failures. The controlled target is **met**.

| Workload | Rows | Pairwise checks | Indexed checks | Identical conflict edges | Pair-check reduction |
|---|---:|---:|---:|---:|---:|
| Sparse | 256 | 32,640 | 464 | 240 | 98.5784% |
| Sparse | 512 | 130,816 | 928 | 480 | 99.2906% |
| Sparse | 1024 | 523,776 | 1,856 | 960 | 99.6457% |
| Sparse | 2048 | 2,096,128 | 3,712 | 1,920 | 99.8229% |
| Dense control | 256 | 32,640 | 32,640 | 32,640 | 0.0000% |

Validation still visits every assertion; partitioning and sorting remain necessary, with O(n log n) comparison sorting overall. Active-pair work remains quadratic for mutually overlapping same-key assertions, and explicit output itself can be quadratic. The measured pair-check reduction is not an inferred end-to-end speedup.

### Separately measured construction runtime

Five alternating-order elapsed-time repeats per method were run on `Linux-6.17.0-1022-azure-x86_64-with-glibc2.39`, Python 3.12.14, NumPy 2.5.3, SciPy 1.18.0. Medians below include validation, grouping/sorting, collision tests and edge-list construction; input generation and I/O are excluded. These host-specific measurements are stored separately from deterministic result replay.

| Workload | Pairwise median (s) | Indexed median (s) |
|---|---:|---:|
| sparse_2048 | 4.696146 | 0.008272 |
| dense_256 | 0.112617 | 0.032635 |

Dense-case timing differences include hoisted validation and reduced Python overhead, not fewer pairs or subquadratic behavior. These are not service latency, database I/O or universally transferable speedup estimates.

![H5. Sparse construction avoids irrelevant pairs; the dense control does not.](figures/05_indexed_conflicts.png)

## 7. Interpretation and remaining falsification

The semantic adaptation target failed despite a plausible development-to-target prior shift. Therefore, this evidence does not justify changing the default Jev decision rule. In contrast, the controlled tests identify distinct opt-in engineering paths: represent dependence uncertainty rather than manufacture confidence; optimize a proposed repair while honoring explicit protections; recognize bipartite conflict structure before falling back to bounded generic solving; and index conflict construction rather than report solver-only savings.

The structural passes remain conditional. Incorrect marginals, incomplete proofs, mistaken protections, false priorities and erroneous scope/interval qualifiers can invalidate semantic conclusions even when every algorithm is correct. Results do not measure candidate generation, novel entity discovery, independent source truth, actual reviewer behavior, production database concurrency, or comparative end-to-end graph quality. A policy frozen before a new source-disjoint independently adjudicated corpus, with matched evidence and resource budgets against an external system such as KARMA, remains unexecuted by this extension.

## 8. Reproducibility and evidence preservation

```bash
python -m pip install -r graph_synthesis/novel_mechanisms/requirements.txt
python -B -m graph_synthesis.novel_mechanisms.run --timings
python -B -m unittest discover -s graph_synthesis/novel_mechanisms/tests -v
python -B -m graph_synthesis.novel_mechanisms.run --check
python -B -m graph_synthesis.novel_mechanisms.report --figures --update-paper
python -B -m graph_synthesis.render_current_paper --output manuscript/paper-current.pdf
```

The results preserve per-candidate predictions and selections, fitted priors, arbitrary joint tables, rational dual certificates, proof/repair fixtures, solver certificates, interval assertions, finite oracles and SHA-256 inputs. Replay disables network connections and uses the existing disclosed narrow numeric comparison tolerance; exact rational certificate strings are retained. Timings are not replay-equality claims. Five SVG/PNG pairs and summary.csv are generated from recorded results. The extension manifest binds its files; the shared manuscript uses its own build manifest. Current-paper insertion is additive and idempotent, retaining all earlier studies and limitations.
