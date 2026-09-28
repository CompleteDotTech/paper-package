# Five dependence-aware graph certificate experiments

Baseline: `a62a3257645d8e35cd4e45be53bfa9511d27724b` (merged PR #17). This protocol is committed before implementing or executing this suite. Earlier public outcomes motivated its hypotheses; this is exploratory follow-up, not independent preregistration. Never retune the endpoints below after observing outcomes. No new Jev service calls, production policy changes, or edits to archived study evidence.

## Scope and novelty boundary

These five combinations were not found in the current repository's experiment inventory after inspection of the relationship, falsification, theory-suite, multicall, followup, adaptive, risk-control and reliability protocols and implementations. This is a repository-scoped claim, not proof that nobody has attempted them worldwide. Beta-binomial random effects, probability-bound linear programs, bipartite min-cut, consistent answers across repairs and incremental view maintenance have established predecessors. We test their specific integration and limitations for this Jev graph pipeline. Algorithmic correctness is not semantic accuracy.

## H1: Source-random-effects contamination forecasting

Motivation: the latest out-of-group multiplier reduced mean bias but worsened source-contamination Brier. Hypothesis: explicitly modeling within-source error dependence improves contamination forecasting without changing any accepted edge.

Reuse authenticated multicall base1 outputs: 73 development candidates in 40 source groups and 263 evaluation candidates in 149 disjoint groups. These evaluation data were already inspected in prior work. A group contributes only if base1 accepted at least one SUPPORTS/REFUTES edge. Record its accepted count n and wrong-edge count k. Fit pooled marginal error mu=(sum(k)+0.5)/(sum(n)+1) on development only. Select intraclass correlation rho from {0,0.01,0.05,0.1,0.2,0.4,0.6,0.8} by maximum development beta-binomial log likelihood; tie toward smaller rho. For rho>0, alpha=mu*(1/rho-1), beta=(1-mu)*(1/rho-1); predict contamination 1-B(alpha,beta+n)/B(alpha,beta). At rho=0 use 1-(1-mu)^n. Retain all likelihoods and leave-one-source-out development sensitivity fits. Execution receives group sizes, not evaluation gold.

Compare with the identical-marginal independent model, the prior feature-based independent model, and PR #17's development-selected multiplier model. Primary conjunction: >=10% lower Brier than the identical-marginal independent comparator, absolute mean bias <=0.03, and Brier no worse than the prior feature-based baseline. A rho=0 selection is a legitimate null result. Report sample-size denominators, proper scores, descriptive paired 95%/99% group bootstrap intervals (4000 draws, seed 20260922), and singleton-group/independence limitations. No deployed risk certificate or new semantic improvement is inferred.

## H2: Lineage admission without an independence assumption

Motivation: exact Shannon expansion was exact only for supplied independent primitives and falsely inflated a duplicated 0.8 source to 0.96 under corrupted independence. Hypothesis: a bounded extremal-probability program prevents independence-induced false admission while using explicit dependence information when available.

Represent a monotone DNF lineage over <=10 Boolean atoms by <=1024 possible worlds. Constrain world masses to be nonnegative, sum to one, and match supplied marginal probabilities and optional conjunction probabilities. Minimize/maximize the lineage indicator with SciPy HiGHS. Store solver residual diagnostics and dual objective bounds; outward-pad bounds by 1e-9. Infeasible, failed, over-cap or nonfinite inputs never yield an admission certificate. Threshold: lower bound >=0.95. Values are supplied fixture probabilities, never raw Jev truth probabilities.

Primary: zero containment failures on 128 seeded arbitrary joint distributions with 2-6 atoms, exact two-event Frechet bounds within 1e-8 on a fixed marginal grid, invariance under reordered/duplicated proofs, and prevention of all independence-induced false admissions in 20 perfectly correlated two-source controls. Explicit pair constraints must tighten or preserve interval width. Report withheld high-probability admissions, infeasible constraints, over-cap staging and a misspecified-marginal negative control. Finite-world and numerical limits are explicit; no unconditional truth guarantee.

## H3: Proof-carrying bipartite conflict optimization

Motivation: the four-vertex cutset cap stages dense conflict components even when they are bipartite. Hypothesis: a bipartite min-cut route solves such components exactly and provides an independently checkable flow/cover certificate.

Use unique nonempty string IDs, nonnegative integer priorities and explicit undirected edges. For each bipartite component <=2048 vertices and <=50000 edges, reduce minimum weighted vertex cover to integer max-flow; return its complementary independent set. Use deterministic sorted traversal, original priorities (no hidden tie perturbation), and certificates verifying capacity, flow conservation, cut capacity, cover feasibility and utility. Non-bipartite components retain the actual PR #17 solver and its original caps; over-cap components stage. Empty and zero-priority inputs remain valid.

Primary: zero utility/consistency/certificate failures on 128 seeded <=10-vertex bipartite fixtures versus independent subset enumeration; no utility regression on supported small general graphs; exact unstaged analytic results on balanced complete bipartite components of sizes 32,64,128,256 and on even cycles of sizes 512,1024,2048. Retain duplicate/order tests, odd-cycle and dense-clique controls, cap controls, and the false-high-priority semantic counterexample. Report graph capacity, not model accuracy.

## H4: Repair-invariant query certificates

Motivation: one deterministic optimum hides alternative equally good graphs; structural optimality cannot justify treating its arbitrary tie choices as certain. Hypothesis: constrained include/exclude re-optimization correctly distinguishes certain, ambiguous, and impossible conjunctive vertex-membership queries across all admissible repairs.

For a graph optimum U, admissible repairs are independent sets of utility >=U-epsilon; evaluate epsilon=0 and floor(0.05*U). For a conjunction of up to eight required vertices, solve the forced-in problem to establish possibility and each forced-out problem to establish certainty. Return an explicit counterexample repair for ambiguity; propagate staged/unsupported optimization rather than making a certainty claim. All priorities remain supplied inputs.

Primary: zero classification or witness errors on 128 seeded <=10-vertex general graphs checked by independent enumeration of all admissible independent sets; zero false certainty; correct retention of every oracle-certain answer; and prevention of a single-optimum false-certainty claim on a two-way tie control. Increasing epsilon must not create new certain answers. Include conflicting conjunctions, empty queries, zero priorities, unsupported graphs and a high-priority-false control. Certainty is conditional on the repair/priority model, not factual truth.

## H5: Delta-indexed updates without global snapshot rescans

Motivation: PR #17 saved solver-vertex work but still validated and discovered every component globally. Hypothesis: a validated graph invariant plus an explicit mutation API permits affected-component-only validation, discovery and solving with identical graph results.

Build an immutable-to-callers adjacency/priority store and node-to-component index. Support weight change, vertex insert/delete and edge insert/delete. Validate every mutation before state changes; construct and solve replacement affected-component states before publishing them. Bridge insertion invalidates both endpoint components; bridge deletion/vertex removal discovers splits only inside the affected old component. Unaffected component solutions are reused; updates return deltas and aggregate utility, not a forced whole-graph materialization. Provide an explicit full snapshot audit outside the update API.

Compare against full input validation/component discovery/recomputation with the same H3 solver, and record the distinction from PR #17. Primary: zero selected/staged/utility mismatches across 640 seeded updates including merges/splits and vertex deletion; zero state change on invalid mutations; >=75% reduction in explicitly counted graph-element visits (validation/discovery/solver-input, including cold build) on 512 components of eight vertices and 128 local updates. Record connected-graph stress where savings can vanish. Record nonbinding repeated local wall-clock measurements separately from deterministic results, with environment and timing boundary; do not infer database I/O, durable transactions, asymptotic guarantees or service latency. Oracle snapshot auditing is excluded from update timing for both policies and disclosed.

## Evidence, implementation and reporting

Seed 20260922. Preserve all fixed inputs and their SHA-256 hashes. Decision functions may not read evaluation gold. Reconstruct saved decisions from raw calls and verify source split before H1. Independent finite/analytic oracles must not call the proposed solver for their truth values. Freeze negative results alongside positive ones. Add regression/adversarial tests, raw per-case results, input/implementation/protocol hashes, one figure per hypothesis in SVG and PNG, a generated report, complete additive manuscript/PDF update and exact replay checks. Timing artifacts are nondeterministic and separate. Keep all prior studies and conclusions intact; no synthetic cases counted as Jev observations. Merge through a PR only after verification, figure/PDF review and required checks.

## Primary foundations and novelty search

- SciPy 1.17.0 beta-binomial definition: https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.stats.betabinom.html
- HiGHS linear programs and dual marginals: https://docs.scipy.org/doc/scipy-1.17.0/reference/optimize.linprog-highs.html
- Kaski, Mannila and Mohapatra, Optimal Union Probability Interval Is NP-Hard (2026): https://arxiv.org/abs/2605.03556
- Faour and Kuhn, Distributed CONGEST Approximation of Weighted Vertex Covers and Matchings (2021): https://arxiv.org/abs/2111.10577
- Pardal et al., Computational Complexity of Preferred Subset Repairs on Data-Graphs (2024): https://arxiv.org/abs/2402.09265
- Staworko and Chomicki, Consistent Query Answers in the Presence of Universal Constraints (2008): https://arxiv.org/abs/0809.1551
- Macedo et al., A Feature-based Classification of Model Repair Approaches (2015): https://arxiv.org/html/1504.03947v1
- TypeSafe typed-decision boundary: https://docs.typesafe.ai/introduction

These references establish antecedents and constraints; they do not validate this implementation or show worldwide novelty. Independent source-disjoint Jev accuracy evaluation and matched KARMA comparisons remain outside this replay/algorithm suite.
