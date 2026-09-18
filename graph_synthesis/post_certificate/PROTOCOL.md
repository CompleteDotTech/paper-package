# Frozen protocol: post-certificate graph-synthesis improvements

Baseline: `9d2e4a60a6c79e616ab1d352cd5da9fe414e6c98` (merged PR #20)
Protocol date: 2026-09-18
Status: frozen before implementation/execution
Fresh Jev service calls planned: 0
New scientific documents planned: 0
Seed: 20260923

## Scope and evidence boundary

The merged evidence separates semantic extraction quality from structural correctness. Repeated prompt/routing/calibration variants have not established a robust semantic advantage, while bounded exact graph algorithms, dependence-aware certificates, repair semantics and delta maintenance have repeatedly passed controlled tests. This protocol therefore tests five **structural / decision-theoretic extensions** suggested by those results rather than another prompt variant.

The five mechanisms below were not found as executed implementations in the baseline repository inventory. That is a repository-scope statement, not a worldwide novelty claim. Their ingredients have substantial prior art: treewidth/variable-elimination dynamic programming, incremental view maintenance and transactions, query resilience/deletion propagation, robust/minimax decision making under imprecise probabilities, and weighted constraint/hypergraph optimization.

No experiment changes candidate extraction, accepted Jev edges, production defaults, or the frozen original evidence. Controlled priorities, probabilities, costs and constraints are supplied inputs and must not be reinterpreted as calibrated factual truth.

## H1 - Induced-width exact conflict optimization

### Motivation
Prior studies established exact handling for bounded enumeration, forests, cutsets and bipartite conflict graphs. A remaining gap is connected non-bipartite cyclic structure that is still tractable because its induced width is small.

### Method
Implement max-sum variable elimination for maximum-weight compatible assertion selection over pairwise conflict factors. A deterministic min-fill elimination order is computed without using assertion weights. Execution is allowed only when:
- induced width <= 4;
- every factor scope is <= 5 variables;
- cumulative materialized factor states <= 250,000.

Otherwise the component is staged without a partial write. The returned assignment includes objective value, selected assertion IDs, elimination order, induced width and a direct feasibility check.

### Frozen test
- 160 seeded small connected graphs, 8-16 vertices, generated from bounded-width constructions with random non-negative integer weights.
- Independent exhaustive subset oracle for every small fixture.
- 8 connected large triangle-chain / partial-2-tree fixtures from 33 through 1,025 vertices, checked by an independently implemented chain dynamic program.
- 5 over-width clique controls (K6-K10) that must stage.
- 8 input-order permutations per first 64 small fixtures.

### Primary target
Zero objective, feasibility, witness or permutation failures; all 8 large tractable fixtures solved; all 5 over-width controls staged. On the 12-16 vertex small subset, counted max-sum table states must be at least 90% below the full 2^n assignment count in aggregate.

## H2 - Transactional batch delta maintenance

### Motivation
Merged studies validate local incremental maintenance and revision checks, but explicitly stop at sequential in-memory updates. Real graph changes often arrive as batches whose derived consequences must be all-or-nothing.

### Method
Implement an in-memory transactional dependency engine for Boolean primitives and derived facts over an acyclic dependency graph. A transaction:
1. validates expected revision and every primitive change;
2. computes the affected reverse-dependency closure;
3. evaluates the new values in topological order against a copy-on-write overlay;
4. commits the complete overlay only if every evaluation succeeds.

Injected evaluation failure, malformed update, or stale revision must leave both values and revision unchanged. This is atomic batch behavior only; no crash durability or concurrent database-isolation claim is made.

### Frozen test
- 128 seeded modular DAGs with 64 primitive nodes and 256 derived nodes.
- Five 1-4 primitive transactions per DAG (640 accepted local transactions total), each compared with independent full recomputation from the post-transaction primitive snapshot.
- 64 injected evaluation-failure controls, 64 stale-revision controls and 64 malformed-update controls.
- 16 connected-control DAGs in which one primitive intentionally reaches nearly every derived node.

### Primary target
Zero snapshot mismatches and zero partial-write/revision failures. Local transactions must perform at least 80% fewer derived-node evaluations than full recomputation in aggregate. The connected control must remain reported separately and must not be used to infer universal savings.

## H3 - Exact query-resilience certificates

### Motivation
The repository can classify query answers across repairs, but binary certainty does not quantify how much evidence must change before a currently true monotone query becomes false. A robustness margin can distinguish a query supported by many independent proof paths from one resting on a single fragile atom.

### Method
For a monotone DNF lineage with positive integer evidence-removal costs, compute the minimum-cost evidence set whose deletion hits every active proof clause. The implementation uses:
- incidence-component decomposition;
- forced singleton reductions;
- branch-and-bound with deterministic branching;
- a disjoint-clause lower bound;
- explicit deletion witness validation.

Connected components above 18 distinct evidence atoms stage rather than silently approximate.

### Frozen test
- 160 seeded small DNF fixtures with <=12 atoms and 2-10 proof clauses.
- Independent exhaustive deletion-subset oracle for every small fixture.
- 8 analytic large fixtures composed of hundreds to thousands of disconnected proof components, with closed-form expected resilience.
- 6 over-cap connected controls that must stage.
- Mutation checks that every returned deletion set actually falsifies the query and removing any positive-cost proper subset does not beat the reported optimum.

### Primary target
Zero optimum/witness/oracle failures; all 8 analytic large fixtures solved exactly; all 6 over-cap controls staged. The result is a resilience certificate relative to supplied lineage and costs, not factual truth.

## H4 - Interval-minimax query review

### Motivation
Prior query-directed review assumes point probabilities. Multiple merged studies show that point risk estimates and calibration can fail. Review selection should therefore be stress-tested against uncertainty in the supplied probabilities themselves.

### Method
Each primitive has an independent probability interval [lo, hi]. For a fixed review budget of two primitives, choose the review set that minimizes the **worst-case expected residual Bernoulli variance** of supplied monotone queries across all interval endpoint vectors. Perfect review reveals the selected primitive states. The production method evaluates query probability by memoized Shannon recursion; the independent oracle enumerates complete Boolean worlds directly.

A midpoint selector using the same expected-loss objective at interval midpoints is the comparator. This study does not remove the conditional-independence assumption; it tests robustness to marginal imprecision only.

### Frozen test
- 96 seeded six-atom interval fixtures with 1-3 monotone DNF queries.
- 32 engineered interval controls where midpoint ranking is intentionally fragile.
- Every candidate review pair checked by the independent world-enumeration oracle.
- Degenerate point-interval controls must reduce exactly to the point-probability solution.

### Primary target
Zero production/oracle objective discrepancies above 1e-10. The minimax selector's worst-case objective must never exceed the midpoint selector's worst-case objective, and must be strictly lower on at least 20% of the 128 non-degenerate fixtures.

## H5 - N-ary conflict constraints

### Motivation
Every merged graph-repair optimizer represents incompatibility as pairwise edges. Some consistency rules are genuinely n-ary (for example, “not all three assertions may coexist”) and a pairwise clique projection can remove compatible pairs unnecessarily.

### Method
Generalize max-sum elimination to forbidden hyperedge factors: a factor contributes negative infinity only when every member of the forbidden set is selected. Pairwise conflicts are size-2 hyperedges. The same deterministic induced-width and state caps as H1 apply, and returned selections are checked directly against every hyperedge.

### Frozen test
- 160 seeded small weighted hypergraphs with 8-14 vertices, size-2 and size-3 forbidden sets, compared with exhaustive subset optimization.
- 8 large three-consecutive-forbidden chain fixtures from 64 through 2,048 vertices. With unit weights, the known optimum is n - floor(n/3).
- Pairwise-clique projection of each size-3 hyperedge is retained as an explicit over-conservative baseline.
- 5 high-arity / over-width controls must stage.
- 8 permutations per first 64 small fixtures.

### Primary target
Zero objective/feasibility/oracle/permutation failures; all 8 large chain fixtures solved exactly; all 5 controls staged. On every large chain, the n-ary optimizer must retain at least as much supplied utility as pairwise projection and strictly more on all fixtures.

## Reporting and falsification rules

- A failed conjunction remains failed even if some endpoints improve.
- No five-result success percentage may be reported.
- Negative/null outcomes remain in results and figures.
- Work counters (factor states, node evaluations) are not wall-clock, API-latency or cloud-cost measurements.
- No controlled algorithm result may be described as independent Jev semantic accuracy.
- No external system superiority is claimed without a matched executed baseline.
- The current manuscript must preserve every prior study and append this section additively.

## Reproducibility target

The implementation will provide:
- `graph_synthesis/post_certificate/run.py`
- `graph_synthesis/post_certificate/methods.py`
- `graph_synthesis/post_certificate/tests/`
- `graph_synthesis/post_certificate/results.json`
- `graph_synthesis/post_certificate/summary.csv`
- `graph_synthesis/post_certificate/RESULTS.md`
- five deterministic SVG figures
- additive updates to `CURRENT_RESULTS.md` and `manuscript/paper-current.md`
- a read-only GitHub Actions workflow that replays all five experiments and tests.

Protocol thresholds, fixture counts, caps and seed must not be changed after benchmark execution except to correct an implementation bug; any such correction must be documented without changing the frozen success criteria.
