# Post-certificate structural extensions for Jev graph synthesis

Timothy Wayne Gregg | AI-assisted author-review research extension | September 18, 2026; corrected September 28, 2026

## Abstract

Five precommitted controlled extensions were executed after the dependence-aware certificate study. Recorded frozen-target outcomes: **H1: met; H2: not met; H3: met; H4: met; H5: met.** These are separate algorithmic conjunctions, not a pooled success percentage. The experiments address induced-width repair, transactional delta maintenance, query resilience, finite endpoint-scenario review and n-ary conflict constraints. **H4 tests endpoint scenarios only; it does not establish minimax review over continuous probability intervals.** An interior counterexample below rejects that broader interpretation. No new semantic-accuracy observations, deployment guarantees or external-system superiority are established.

## 1. Frozen protocol and evidence boundary

The protocol was committed as `8187cc4e4b98e40f3146ce787b71f262b62b3abd` against baseline `9d2e4a60a6c79e616ab1d352cd5da9fe414e6c98` before implementation and execution. Its bytes, fixture definitions, caps, seed `20260923` and thresholds remain unchanged. **Fresh Jev calls: 0. New scientific documents: 0.** This is exploratory follow-up, not independent preregistration.

[The correction record](../graph_synthesis/post_certificate/CORRECTIONS.md) distinguishes repaired implementation/control defects from the preserved protocol. H4's frozen Method explicitly specifies interval endpoint vectors; its former broader interval-minimax description is withdrawn. The supplemental negative control is outside the frozen 128-fixture population. Treewidth-aware dynamic programming, incremental view maintenance, query resilience, finite-scenario minimax decisions and hypergraph optimization have prior art; these are repository experiments, not worldwide novelty claims.

| Hypothesis | Frozen target | Recorded outcome |
|---|---|---|
| H1: induced-width repair | zero oracle/permutation failures; solve 8 large chains; stage controls; >=90% fewer counted states | **met** |
| H2: transactional delta | zero snapshot/atomicity failures; >=80% fewer local evaluations | **not met** |
| H3: query resilience | zero oracle/witness failures; solve 8 analytic families; stage 6 controls | **met** |
| H4: endpoint-scenario review | zero endpoint-oracle discrepancies; never worse than midpoint on endpoint scenarios; strict gain on >=20% | **met**, endpoint scenarios only |
| H5: n-ary conflicts | zero oracle/permutation failures; solve 8 chains; strict gain vs pairwise projection; stage controls | **met** |

A failed conjunction remains not met regardless of individual favorable endpoints.

## 2. H1 - induced-width exact conflict optimization

The solver computes deterministic min-fill order from the actual graph, checking width and allocation limits before constructing exponential tables. The shortcut based on numeric identifier distance has been removed. Of 160 small fixtures, 160 match the exhaustive objective; recorded failures: **0**; permutation failures: **0**. Width distribution: {'1': 33, '2': 45, '3': 53, '4': 29}.

For the frozen 12-16 vertex subset, counted elimination evaluations are **14,660**, versus **1,986,560** full assignments: **99.26% reduction**. This original work counter is not total memory allocation or CPU time; a separate cumulative table-allocation guard enforces the frozen cap. Large triangle chains use an independent prefix dynamic-programming oracle. Per-fixture objectives, widths and staged controls remain in `results.json`.

![H1. Counted exact-DP work versus full enumeration.](../graph_synthesis/post_certificate/figures/01_induced_width.svg)

## 3. H2 - transactional batch delta maintenance

Transactions validate revisions and updates, evaluate an overlay in computed topological order, and return it only after successful evaluation. Unknown dependencies and cycles are rejected. Across **640** accepted transactions, independent full recomputation finds **0 snapshot mismatches**. A control passes only when the expected exception is raised and original values/revision remain unchanged: injected evaluation **63/64**, stale revision **64/64**, malformed update **64/64**. Returned revision mismatches: **0**. The frozen injected-failure conjunction is not met: one selected primitive has no affected derived node, so no failure was injected. That case remains in the denominator; the exact control record is retained in `results.json`.

Local evaluations: 16,205, versus 163,840 for full recomputation: **90.11% reduction**. Connected controls separately show **0.00% mean saving**. These are in-memory atomic batches, not crash durability or concurrent database isolation.

![H2. Local work and connected-control boundary.](../graph_synthesis/post_certificate/figures/02_transactional_delta.svg)

## 4. H3 - exact query-resilience certificates

For supplied monotone DNF lineage and removal costs, incidence decomposition and bounded branch-and-bound find a minimum-cost deletion set hitting each active proof clause. **160/160** small fixtures match the exhaustive oracle. Recorded oracle, witness or control failures: **0**. All 8 analytic-family results and 6 over-cap controls are retained. This is conditional structural resilience, not factual truth or calibrated review effort.

![H3. Recorded resilience cost in decomposable families.](../graph_synthesis/post_certificate/figures/03_resilience.svg)

## 5. H4 - endpoint-scenario query review

The selector minimizes worst-case expected residual Bernoulli variance **over the finite Cartesian product of interval endpoints**, with two reviews. Production uses Shannon recursion; the independent checker enumerates Boolean worlds over the same endpoint scenarios. Neither searches interval interiors.

Across 128 frozen fixtures, endpoint-oracle discrepancies: **0**; cases worse than midpoint on endpoint scenarios: **0**. Strict endpoint gains: **45/128 (35.16%)**, comprising 13 random and 32 engineered fixtures. Point-interval controls pass **16/16**.

**Continuous-interval claim: unsupported.** For singleton queries with intervals `0=[0.1,0.9]`, `1=[0.3,0.4]`, `2=[0.5,0.5]`, the supplemental control selects reviews [1, 2] and reports endpoint worst loss 0.09. The allowed interior witness `p0=0.5` yields **0.25**. Reviewing [0, 2] has analytic continuous worst loss **0.24**. The endpoint choice is therefore not continuous-interval minimax. This negative evidence is separate from the preserved endpoint target. Independent primitives are assumed; no dependence or semantic-calibration guarantee follows.

![H4. Endpoint-scenario outcomes only; continuous interval claim unsupported.](../graph_synthesis/post_certificate/figures/04_interval_review.svg)

## 6. H5 - n-ary conflict constraints

A forbidden hyperedge rejects only its all-selected assignment; pairwise conflict is the arity-two case. **160/160** small fixtures match exhaustive optimization; recorded failures: **0**; permutation failures: **0**. Eight chains compare against `n - floor(n/3)`, with objectives and staging controls retained. At the largest chain, retained n-ary utility is **1366**, versus **683** under deliberately over-conservative pairwise projection.

![H5. N-ary repair versus pairwise projection.](../graph_synthesis/post_certificate/figures/05_hypergraph.svg)

## 7. Interpretation

Every result is conditional on supplied graphs, lineage, costs, constraints or finite probability scenarios. Work counters do not measure wall-clock/API latency or cloud cost. The H4 interior counterexample rejects the broader interval-minimax interpretation. None establishes correct extracted entities, relations, qualifiers or probabilities. No production graph policy changes here.

## 8. Reproducibility

```bash
python -B -m unittest discover -s graph_synthesis/post_certificate/tests -v
python -B -m graph_synthesis.post_certificate.run --check
python -B -m graph_synthesis.post_certificate.report --check --update-paper
```

`results.json` retains outcomes and controls; `summary.csv` and five SVGs derive from those measurements. Manual validation also checks protocol ancestry/bytes, archive integrity, deterministic HTML and current-paper build hashes. The correction record documents implementation and interpretation changes; the frozen protocol is unchanged.
