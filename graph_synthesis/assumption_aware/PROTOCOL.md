# Assumption-aware graph synthesis: frozen follow-up protocol

Date: September 18, 2026. Baseline: `a62a3257645d8e35cd4e45be53bfa9511d27724b` (merged PR #17).

## Status and scope

This protocol is committed before implementation and execution of this extension. Published prior outcomes informed the hypotheses. This is exploratory follow-up, NOT independent preregistration or an uninspected holdout. Failures remain failures; thresholds, seeds and primary populations below must not be changed after execution. Bug corrections require an explicit amendment that preserves previous outcomes and explains the defect.

Five combinations are proposed as new experiments for this repository, subject to a source inventory audit. No assertion that the underlying algorithms have never been attempted worldwide is justified. Prior work already covers probabilistic entailment, consistent query answering, incremental dynamic programming and recursive materialisation. The contribution sought is an evidence-preserving integration and falsification study in the Jev graph-synthesis package.

No default compiler policy changes, no modification of the archived original 161-file study, and no fabricated Jev calls. The planned suite uses offline saved-response analysis (H3) and controlled algorithmic fixtures (H1/H2/H4/H5). Fresh Jev calls: zero. No superiority to KARMA or autonomous-production readiness will be inferred. Author-review manuscript status is retained.

## Motivation from PR #17

H1 in PR #17 worsened group Brier despite improving mean bias; H3 evaluated exact lineage under supplied independence and retained a false-independence counterexample; H4 optimized supplied priorities even when a false assertion had higher priority; H5 saved solver work on disconnected graphs but saved none on its connected stress case. H2 used idealized review and did not measure real query workloads or reviewers. These limitations motivate the following distinct interventions.

## H1 — Dependence-robust lineage envelopes

Hypothesis: an explicit feasible-joint-distribution envelope prevents unsupported admissions caused by independence assumptions and is tighter than recursively applied marginal Frechet bounds.

Method: represent each truth assignment to at most eight primitive source events by a nonnegative mass. Require masses to sum to one and match supplied primitive marginals (and, in a separate sensitivity panel, supplied pairwise intersections). Minimise and maximise the probability of the DNF proof event using bounded linear programming. Validate primal/dual residuals, widen reported bounds by numerical tolerance, and stage on infeasibility, failed verification or resource limits. Above the atom cap, return conservative Frechet bounds and an explicit non-exact status. Do not treat estimated Jev probabilities as verified source marginals.

Primary population: 128 seeded fixtures, 2–6 atoms, arbitrary joint masses generated independently of the algorithms, and 1–8 proofs of 1–3 atoms. Seed 20260922. Test both marginal-only and additional pairwise constraints. Compare with a canonicalised Frechet proof/union envelope; separately report the prior independent-event point estimate.

Frozen target: zero truth-containment failures beyond 1e-7, zero false lower-bound admissions at 0.95, zero duplicate/order invariance failures beyond 1e-7, and at least 10% mean interval-width reduction relative to the Frechet envelope. Report target failure even if the other requirements hold. Controls: shared 0.8 source renamed as two 0.8 primitives (independence would give 0.96); mutually exclusive events; inconsistent pairwise constraints; zero/one marginals; empty and tautological proof sets; nine-atom cap. Finite truth containment is not a universal proof; analytic two-event Frechet cases and independent feasible-world checks supplement it.

## H2 — Ambiguity-preserving optimal-repair answers

Hypothesis: answering only assertions/queries invariant over all optimal repairs avoids arbitrary tie-break conclusions while retaining justified disjunctive answers.

Method: use the existing bounded conflict optimizer as a value oracle. Obtain one optimal repair. For each selected assertion, forbid it and re-solve: it is forced only if optimum utility strictly decreases. For an OR query, forbid every queried assertion; a strict decrease certifies the disjunction without asserting any particular member. An AND query requires every member to be forced. If any relevant solve stages or fails, return unknown, not a certificate. Work is bounded by explicit vertex and oracle-call caps. Optimality refers only to supplied nonnegative integer priorities and conflicts.

Primary population: 128 random 4–10 vertex conflict graphs, weights 0–5, edge probability 0.3, seed 20260923. Independently enumerate every consistent subset, all utility maxima, forced assertions and OR/AND answers. Test duplicate edges, input order and zero weights. Include 32 equal-priority conflicting pairs, unique-optimum cases, 17-clique staging and a high-priority false assertion.

Frozen target: zero false or missing forced assertions/OR/AND answers on supported finite cases; 100% selected-assertion retention on unique-optimum cases; certify each pair disjunction but no individual member on the equal-pair control. Explicitly report coverage relative to one arbitrary repair, solver-call overhead and staged cases. Semantic truth is NOT certified: a uniquely preferred false assertion remains a negative control.

## H3 — Query-exposure-weighted review

Hypothesis: allocating the same 20 idealized edge reviews by downstream query exposure reduces weighted residual contaminated-source exposure by at least 10% without increasing the number of contaminated source groups.

Inputs: the existing multicall study's 73 development and 263 evaluation candidates. Fit the existing single-view risk estimator on development only. Policy execution receives IDs, source groups, base1 labels/scores and a predeclared synthetic exposure weight, never evaluation gold. Queries are NOT extracted or observed real workloads: group exposure is `1 + (integer(SHA256('query-exposure-v1:' + group)) mod 10)`. The primary workload uses these weights; sensitivity uses uniform weights and reversed weights (11 minus the primary weight). Do not relabel these scenarios as independent datasets.

Comparator: PR #17's single-view, group-aware greedy review allocation. Proposed policy multiplies each group's expected contamination-reduction gain by its exposure weight; retain the comparator's deterministic tie rule. All other features, accepted candidate pool and costs are identical. Gold enters only outcome scoring. Primary reviewer removes every wrong reviewed edge and preserves every correct edge. Report 10/20/30/40 review budgets, correct retained edges, weighted residual exposure and unweighted contaminated groups. The primary target is the conjunction above at budget 20 under the primary workload. Report 4,000 paired source-group bootstrap draws (seed 20260924), descriptive 95% and 99% intervals with fixed fitted policy and review sets. These omit fitting and workload uncertainty and are not confirmatory significance tests. Reviewer detection sensitivity 0.5/0.75/1.0 is descriptive, not observed human evidence.

## H4 — Connected-tree delta dynamic programming

Hypothesis: updating cached include/exclude messages only along the ancestor path can preserve the exact maximum-weight independent-set value while reducing counted DP updates by at least 75% on a connected balanced tree, closing PR #17's connected-component caching limitation.

Method: validate and root a supplied fixed tree once, cache child aggregates and include/exclude messages, and accept validated nonnegative integer single-vertex weight updates. Propagate message deltas to the root, stopping when unchanged. Structural edits are explicitly unsupported and must be rejected without mutation. Return exact utility and reconstruct a selected set on demand; charge reconstruction separately rather than hiding its linear work.

Primary workload: one connected 255-vertex binary tree, weights drawn from 1–9, and 256 seeded weight updates (seed 20260925). Include cold-build work for both policies. Compare with full-tree DP after every update; check selected-set feasibility and utility. Independently enumerate 128 small random trees of 2–10 vertices with 8 updates each. Record every update and deterministic operation counts. Frozen target: zero value/feasibility mismatches and at least 75% fewer DP vertex-message updates on the primary workload. Controls: 255-vertex path, repeated same-value updates, root/leaf updates, invalid weights, cycles, disconnected inputs and structural-change rejection. Report ancestor visits, message changes and selection-reconstruction work separately. No identical percentage speedup in wall-clock latency, I/O or arbitrary dynamic graphs is claimed.

## H5 — Grounded cyclic provenance and retraction

Hypothesis: least-fixed-point, agenda-indexed rule materialisation prevents unsupported circular facts after source retraction and reduces rule-body membership work relative to repeated global scans.

Method: facts start only from the currently supplied external fact set and explicit empty-body axioms. Index positive Horn rule bodies by fact. Fire a rule only once all body facts have become grounded; duplicates cannot add support. Recompute grounded closure after retraction rather than trusting cyclic reference counts. This is a bounded in-memory positive-rule prototype, not distributed DRed or durable transactions. Retain a deliberately unsafe warm-start closure comparator to demonstrate circular self-support, not as a claim about a competent Datalog baseline. The strong correctness comparator is independent cold full-scan least-fixed-point evaluation.

Primary population: 128 seeded random rule systems, 4–12 facts, up to 20 rules with 1–3 body facts, 8 source-removal/addition operations each; seed 20260926. Primary work population: 64 independently grounded eight-rule chains presented in adversarial order, 128 single-source toggles. Include cold-build work. Frozen target: zero closure mismatches versus cold full-scan evaluation, no ungrounded survivors in source-removed cycle controls, and at least 75% fewer counted body-fact membership inspections on the fixed sparse workload. Controls include pure cycles with no seed, a cycle with one external seed before/after withdrawal, independent alternate grounding, empty-body axioms, duplicate rules, self-loops and a completely connected dependency stress case. Invalid inputs must not mutate state. Wrong external facts can still ground wrong conclusions: retain this semantic control. Report closures, additions/removals, rule activations and operation counts; no semantic truth or distributed-maintenance guarantee follows.

## Evidence, validation and reporting

Record algorithm source hashes, frozen protocol hash and commit, baseline commit, seeds, all fixtures, all outcomes, resource caps, assumptions and failure controls. Preserve both positive and negative results. Five primary hypotheses have different evidence classes; do not pool pass counts into an accuracy estimate. Deterministic results replay must pass. Regression tests must exercise malformed inputs and independent oracles, not just saved numbers. Regenerate five vector/PNG figure pairs, a machine-readable summary, an evidence-linked manuscript section, the complete current manuscript/HTML/PDF, and an extension artifact manifest. Verify archived evidence unchanged and all applicable CI before merging the PR. Do not bypass protection or conceal failed checks.

## Prior-art anchors and novelty boundary

- Hansen and Perron, *Merging the local and global approaches to probabilistic satisfiability*, International Journal of Approximate Reasoning 47(2), 2008, DOI 10.1016/j.ijar.2007.03.001; author archive https://www.gerad.ca/fr/papers/G-2004-48 . Linear-program probability envelopes are established.
- Kaski, Mannila and Mohapatra, *Optimal Union Probability Interval Is NP-Hard*, 2026, https://arxiv.org/abs/2605.03556 . Bounded probability-envelope computation does not imply general tractability.
- Staworko, Chomicki and Marcinkowski, *Prioritized Repairing and Consistent Query Answering in Relational Databases*, https://arxiv.org/abs/0908.0464 . All-repair semantics are established.
- Pardal et al., *Computational Complexity of Preferred Subset Repairs on Data-Graphs*, 2024, https://arxiv.org/abs/2402.09265 . Weighted graph repair has substantial prior work.
- *Maintenance of datalog materialisations revisited*, Oxford author archive https://ora.ox.ac.uk/objects/uuid%3A5b988e72-5128-4c40-b9a2-81d6597dc748 . Recursive maintenance and counting limitations are established.

Literature verification continues before the report is finalized; it cannot establish a universal absence of prior attempts. Any overlaps found will be documented rather than renamed as world-first results.
