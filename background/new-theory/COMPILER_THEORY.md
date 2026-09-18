# Compiler theories: from local judgments to defensible graph changes

These are proposed mechanisms and experiments, not measured improvements. The strongest opportunity is to evaluate graph compilation as a separate scientific object from classifier accuracy: identical model outputs can produce different graphs depending on dependency handling, constraints, and acceptance policy.

## What the current compiler establishes

The present implementation provides useful IR dataclasses and a staged orchestration sketch. It does not yet establish transactional graph integrity:

- [`_validate_constraints`](../typed-probabilistic-graph-compiler/pgc/compiler/orchestrator.py#L432) assigns every rule `PASS` without evaluating `formal_spec`.
- [`_create_mutations`](../typed-probabilistic-graph-compiler/pgc/compiler/orchestrator.py#L446) turns every recorded decision into `CREATE_NODE`, with no action payload or interpretation of its selected outcome.
- [`_materialize`](../typed-probabilistic-graph-compiler/pgc/compiler/orchestrator.py#L469) accepts confidence at least 0.85, without checking proposition polarity, constraint results, or dependencies. It records timestamps rather than applying operations to a graph store.
- Each `_decide_*` method invokes the backend, then [`_invoke_backend_batch`](../typed-probabilistic-graph-compiler/pgc/compiler/orchestrator.py#L505) invokes it again with empty state and omitted options. The ledger retains the first result if the second invocation has no error.
- [`compile`](../typed-probabilistic-graph-compiler/pgc/compiler/orchestrator.py#L121) constructs a transaction description without advancing the compiler's graph version. [`record_provenance`](../typed-probabilistic-graph-compiler/pgc/compiler/orchestrator.py#L538) is not called by compilation and omits required `ProvenanceEntry` constructor fields.

An [offline deterministic probe](probe_compiler_semantics.py) on 2026-09-17 supplied one edge with `P(false)=0.99`, confidence 0.99, and a constraint whose specification was `False`. It produced two backend calls, a passing constraint, and one `CREATE_NODE` in the dry-run transaction. The graph version remained `v1` and the provenance dictionary remained empty. The [saved snapshot](compiler_probe_snapshot.json) includes the source commit and file hashes. This demonstrates incorrect staging semantics, not a persistent graph mutation. No model service was contacted.

## 1. Compile selected meanings into typed actions

**Hypothesis C1:** Correct action semantics will remove predictable false automatic proposals independently of model improvement.

A high-confidence negative judgment is evidence to reject a positive edge. It is not permission to materialize that edge. For a binary relation, let `p=P(supported | evidence)` and consider three actions with losses:

```text
L(commit) = C_FP * (1 - p)
L(reject) = C_FN * p
L(review) = C_review + expected residual review loss
action = argmin L(action), subject to deterministic validity
```

Under a perfect reviewer assumption, review loss reduces to `C_review`; real experiments must measure reviewer error and delay. With only commit/reject, commit is preferred when `p > C_FP/(C_FP+C_FN)`. Thus the threshold should depend on the proposed operation's cost, not on `max(p,1-p)`. A false merge can damage many inherited relationships and warrant a different cost from a reversible property addition.

For `CHOICE`, preserve the selected option's meaning: existing entity ID means link or merge under explicit preconditions; `new` means create; `unknown` means defer. Relation support, relation type, and endpoint resolution jointly justify one edge operation. They should not create separate nodes. Attach candidate ID, decision IDs, selected outcomes, and evidence to each mutation using the existing [`MutationPlan` fields](../typed-probabilistic-graph-compiler/pgc/ir/__init__.py#L263).

**First experiment:** Freeze a table of decision distributions and compare existing staging against typed staging. Include high-confidence negatives, ambiguous choices, unsupported primitives, malformed distributions, missing endpoints, and backend errors. Measure action correctness and invalid proposal counts. This is a correctness check, not evidence that a model learned better semantics.

**Falsification:** Once obvious invalid proposals are removed, test graph precision/recall on held-out graphs. If typed staging gives no benefit at matched coverage, its benefit is implementation correctness and auditability rather than improved statistical inference. Perfectly typed actions can still be semantically false.

## 2. Resolve mutually dependent decisions jointly

**Hypothesis C2:** Structural inference improves graph accuracy when useful constraints connect noisy local judgments.

For binary candidate decisions `x_i`, start with a weighted objective:

```text
x* = argmax over x in F(G, schema)
     sum_i [x_i log(p_i) + (1-x_i) log(1-p_i)]
```

`F` is the set of assignments satisfying validated graph rules. Clip probabilities away from zero/one for finite numerical scores. This is MAP only under the stipulated factorized model and hard-rule assumptions; with correlated local predictions it is a useful surrogate objective, not a proven posterior.

For entity identity, enforce transitivity with `x_ab + x_bc - x_ac <= 1`, including permutations. Consider `p_ab=.90`, `p_bc=.90`, `p_ac=.01`: independent thresholding proposes an inconsistent triangle, while blindly merging connected components ignores the strong negative edge. Weighted correlation clustering instead searches for an equivalence relation consistent with as much evidence as possible. This is an established approach, including log-odds edge weights, in [Bansal, Blum, and Chawla's correlation clustering paper](https://www.cs.cmu.edu/~shuchi/papers/clusteringfull.pdf).

Other rules can express endpoint existence, relation domain/range, unique identifiers, or mutually exclusive values at a particular time. Separate genuinely invariant rules from heuristics: “one employer” is generally unsuitable as a timeless hard constraint. Start with exhaustive search on small connected components, then compare integer optimization and continuous relaxations. [Bach et al.'s PSL/HL-MRF formulation](https://jmlr.org/papers/v18/15-631.html) provides established machinery for weighted logical dependencies and scalable convex MAP inference; it does not establish that our proposed rules are correct.

**Experiment:** Construct and independently label graph components containing ambiguous identity triangles, shared identifiers, and temporal exceptions. Hold local scores fixed; compare independent decisions, union-find merging, reject-on-conflict validation, and constrained optimization. Report pairwise/entity clustering quality, graph fact precision/recall, semantic false merges, solver cost, and structural violations.

**Falsification:** Zero structural violations with worse semantic accuracy refutes the accuracy claim. Incorrect hard rules can force a consistent but false graph. Evaluate deliberately misspecified rules and report abstentions when no feasible assignment exists. Do not treat optimization objective improvements as ground-truth improvements.

## 3. Allocate risk across the complete dependency graph

**Hypothesis C3:** Decisions about shared endpoints should consume risk according to their downstream effects, reducing harmful automatic mutations at comparable useful coverage.

An edge may require four correct events: subject identity, object identity, predicate selection, and evidential support. The current [`Decision.depends_on`](../typed-probabilistic-graph-compiler/pgc/ir/__init__.py#L211) field supports dependency representation but is not populated by the orchestrator.

Let `A_i` mean prerequisite `i` is correct. Suppose `epsilon_i` is a valid bound on `P(not A_i | I)` for the **same conditioning information** `I`, and all prerequisites together suffice for mutation correctness. The union bound gives:

```text
P(any required prerequisite fails | I) <= sum_i epsilon_i
P(mutation correct | I) >= max(0, 1 - sum_i epsilon_i)
```

No independence assumption is required. With prerequisite correctness probabilities .88, .95, and .97, the guaranteed lower bound is .80. Multiplying them gives .81092 only with suitable conditional independence. Calling the product “conservative” is unjustified: two .90-correct events with disjoint failures have joint correctness .80, below the product .81.

For a proposed batch `B`, let `D(B)` contain each required decision once. Bounding `sum_{i in D(B)} epsilon_i <= alpha` bounds the probability of any prerequisite failure by `alpha`. Counting a shared endpoint once is appropriate for this event-probability budget; its failure can still corrupt many mutations. For additive damage, separately estimate `sum_m C_m * q_m`, where `q_m` bounds mutation error. Linearity of expectation does not require independent mutation errors.

The assumptions are substantial. Raw confidence, marginal calibration, or a reliability diagram does not supply a valid pointwise conditional bound. Missing dependencies invalidate the sufficiency assumption. Adaptive batch selection needs bounds valid under that selection process; a calibration guarantee on arbitrary individual examples does not automatically transfer to chosen graph components.

**Experiment:** Hold local marginal accuracies constant while varying shared endpoint frequency and correlated error generation. Compare single-confidence gating, independent probability products, and dependency budgets. Measure mutation error, probability of any batch error, damaged fact count, and coverage separately. First verify the bound with known synthetic probabilities; then test estimated bounds on held-out graph components.

**Falsification:** If useful coverage collapses with no meaningful reduction in weighted error, this conservative policy is impractical. A violation under truly valid inputs refutes the implementation; a violation using estimated confidence may instead expose failed calibration or omitted dependencies.

## 4. Make accepted mutations carry verifiable certificates

**Hypothesis C4:** A small deterministic verifier can preserve graph invariants across retries, evidence changes, and concurrent compilations without trusting the decision backend.

Each proposed transaction should carry a certificate containing the graph/schema version, evidence snapshots, original requests, responses, candidate/action mapping, dependency closure, rule results, and acceptance policy version. Store each backend response once against its original request; do not reconstruct an empty request and make a second judgment.

The verifier checks legal operation types, target references, prerequisites, and the resulting graph `G'`. For a minimal implementation, stage against an immutable snapshot, validate `G'`, then atomically replace graph state and version only if the original version still matches. A dry run returns a proposal and validation report without a committed transaction timestamp. Provenance must become visible atomically with graph changes.

**Conditional invariant:** If the initial graph satisfies the implemented invariants, the verifier correctly validates the entire affected closure, and atomic application uses the exact verified snapshot and payload, each successful commit preserves those invariants. This proves neither evidence truth nor schema adequacy; a perfectly valid graph can contain false facts.

**Experiment:** Use deterministic backends and an in-memory graph first. Inject stale versions, duplicate retries, missing endpoints, partial-apply failures, and changed evidence. Check unchanged state on rejection, single application on retry, provenance completeness, and actual invariant preservation. Then compare the same cached semantic decisions with and without verification at matched accepted recall.

**Falsification:** Any committed invalid graph, graph/provenance mismatch, or partial transaction refutes the implementation claim. Lower throughput is an explicit tradeoff to measure. If semantic false-mutation rates are unchanged, report integrity improvements separately from classification gains.

## Recommended order

Implement C1 and C4 as the minimum credible experimental compiler. Evaluate C2 on small labeled components where exact inference is possible. Add C3 only after a complete dependency representation and a defensible calibration protocol exist. Preserve original local outputs in every ablation so improvements can be attributed to compilation policy rather than changed model calls.
