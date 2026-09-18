# Offline compiler quickstart

Run these commands from the repository root. The compiler, walkthrough, and deterministic tests use Python's standard library; no model downloads or credentials are required.

```console
python -B -m pgc.experiments.scifact_walkthrough
python -B -m unittest discover -s tests -p test_compiler.py -v
python -B -m pgc.experiments.run_compiler_research
```

The historically named `scifact_walkthrough` now uses explicitly synthetic research groups and predetermined mock responses. It is not a SciFact benchmark or a measurement of model quality. It demonstrates an unchanged graph after a dry run, rejection of mock commits under the default policy, an explicitly permitted mock commit, replay without a second application, and rejection of a stale graph version.

The controlled research runner writes `results/research/compiler_results.json` and `results/research/COMPILER_RESULTS.md`. It compares typed actions and a deliberately flawed confidence-only positive-edge policy using identical frozen predictions, then checks graph/provenance snapshots under injected failures. Results are synthetic mechanism controls.

An optional real-adapter integration smoke is available when the research virtual environment, pinned NLI checkpoint, and CUDA are installed:

```console
.venv\Scripts\python.exe -B -m pgc.experiments.run_real_compiler_smoke
```

It runs only two manually constructed support/refutation pairs through the real specialist and default compiler policy, then saves exact probabilities and graph outcomes to `results/research/real_compiler_smoke.json`. This smoke is CUDA-only and does not fall back to CPU. It requires PyTorch/Transformers and may fetch the pinned public checkpoint if absent. It is an integration check, not held-out performance evidence.

## Compile an evidence-backed edge

```python
from pgc.compiler import GraphCompiler, InMemoryGraphStore
from pgc.experiments.scifact_walkthrough import (
    WalkthroughBackend, build_example_scifact_claim,
)

evidence, candidates, constraints = build_example_scifact_claim()
store = InMemoryGraphStore("walkthrough", nodes={
    "group-a": {"mention": "Research group A", "types": ["Organization"]},
    "group-b": {"mention": "Research group B", "types": ["Organization"]},
})
compiler = GraphCompiler(
    "walkthrough", WalkthroughBackend(), store=store,
    allowed_execution_modes={"mock"},  # Explicit permission for this offline fixture.
)
preview, context = compiler.compile(evidence, candidates, constraints, dry_run=True)
assert preview.status == "dry_run" and preview.committed_at is None
assert store.snapshot().version == "v1" and not store.snapshot().edges

transaction, context = compiler.compile(
    evidence, candidates, constraints, expected_version="v1", idempotency_key="example-1",
)
assert transaction.status == "committed", context.errors
assert store.snapshot().version == "v2"
assert store.snapshot().edges["collaboration"]["subject"] == "group-a"
assert len(store.snapshot().provenance) == 1
```

By default, actual commits require decisions marked `execution_mode="real"`. Mock and legacy unknown outputs need an explicit `allowed_execution_modes` override. An unavailable response cannot become a semantic decision. A mode flag records adapter provenance; it does not independently authenticate an external service.

Candidate evidence IDs, source versions, and snapshots must match the supplied evidence collection. New node IDs use their candidate IDs. An entity-resolution choice needs actual existing entity records from the store, not bare retrieval IDs. Bind previously resolved edges using `EdgeCandidate.subject_id` and `object_id`, or let the compiler resolve candidate mentions. Missing endpoints or required decisions cannot create edges.

The built-in NLI specialist directly handles the compiler's `relation_support` requests when endpoints and predicates are already resolved. The ER specialist currently handles pairwise `entity_resolution` with `same`/`different`; it does not implement the compiler's `entity_resolution_choice` over entity IDs plus `new`/`defer`. A backend that supports those choice tasks is required for automatic candidate resolution. Node existence, type, property, and predicate-choice requests likewise require a compatible backend; unsupported requests are reported as errors, rather than silently converted to unrelated classifier scores.

Relation decisions retain `SUPPORTS`, `REFUTES`, and `NOT_ENOUGH_INFO`. High-confidence refutations do not create positive edges. Binary support responses require explicit `allow_legacy_binary=True`; the false branch becomes not-supported/unknown, never an inferred refutation. This compatibility conversion cannot recover the original distinction between refutation and missing evidence.

## Validation and transactions

Supported operations are `CREATE_NODE`, `CREATE_EDGE`, `ADD_TYPE`, and `SET_PROPERTY`. Other operations reject until their semantics are implemented. Entity choices can link a mention to an existing record; the compiler does not merge two existing graph nodes.

Constraints use declarative dictionaries, for example:

```python
{"rule": "referential"}
{"rule": "required_type"}  # Every node has at least one type.
{"rule": "no_self_loops"}
{"rule": "unique_property", "property": "identifier"}
{"rule": "cardinality", "predicate": "manages", "max": 1, "direction": "out"}
{"rule": "domain_range", "predicate": "collaborates_with",
 "domain": "Organization", "range": "Organization"}
```

Unsupported or malformed specifications become `UNKNOWN` and block the batch. Specifications are never evaluated as Python code. Selected operations apply to a private snapshot, and the full resulting graph is validated before graph state, transaction certificate, and provenance are published together. A version conflict or an apply failure publishes nothing. `failure_after=1` injects a failure after the first private application for deterministic tests.

`Transaction.status` distinguishes `committed`, `dry_run`, `no_op`, `rejected`, and `conflict`. Only actual commits receive commit timestamps and advance the graph version. Check `context.errors`, `context.rejected_candidates`, and `context.mutations_escalated` as well: a transaction can commit independent valid candidates while other candidates require review.

Reuse an idempotency key for the same inputs to retrieve the original transaction without repeating inference. Reusing the key with changed input evidence, candidates, schema, backend version, or policy rejects. The in-memory retry ledger is lost when the store process ends.

The expected graph version is part of retry intent: changing it while reusing a key conflicts. Certificates bind original candidate/request/decision snapshots and mutation payloads, and the verifier also checks semantic action consistency. These are integrity checks within a trusted process. Caller-produced hashes are not signatures or authenticated proofs of an external source.

An optional `dependency_risk_budget` gates a mutation using the sum of distinct prerequisite error estimates. This is an estimated-risk policy, not a statistical guarantee from raw model confidence. All accepted mutations retain original requests, selected outcomes, evidence, constraints, backend modes, and dependency links in their provenance. Provenance entries are keyed by mutation ID so later updates do not overwrite earlier lineage.

The store is intended for controlled experiments. It does not provide durable storage, distributed transactions, existing-node merges, general logical inference, or proof that an evidence-supported statement is true.
