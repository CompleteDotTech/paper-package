"""Deterministic graph-state tests; no models, downloads, or network calls."""
from copy import deepcopy
from datetime import datetime
import unittest

from pgc.compiler import GraphCompiler, InMemoryGraphStore
from pgc.compiler.graph_store import GraphValidationError, evaluate_constraint
from pgc.decision import DecisionBackend, DecisionResponse
from pgc.ir import (
    CandidateGraphIR, Constraint, ConstraintSet, ConstraintStatus, EdgeCandidate,
    Evidence, EvidenceSpan, MutationOperation, MutationStatus, NodeCandidate,
    ObjectKind, PropertyCandidate,
)


class FixedBackend(DecisionBackend):
    def __init__(self, support="SUPPORTS", confidence=.99, overrides=None, hook=None):
        self.support, self.confidence = support, confidence
        self.overrides, self.hook = overrides or {}, hook
        self.calls, self.batches = [], 0

    def name(self):
        return "deterministic-fixture"

    def version(self):
        return "1"

    def decide(self, request):
        self.calls.append(deepcopy(request))
        outcome = self.overrides.get(request.task, self.support if request.task == "relation_support" else request.options[0])
        if outcome == "ERROR":
            return DecisionResponse(request.request_id, {}, error="unavailable fixture", execution_mode="unavailable")
        if outcome == "BINARY_FALSE":
            return DecisionResponse(request.request_id, {"true": .01, "false": .99}, confidence=.99, execution_mode="mock")
        confidence = self.confidence if len(request.options) > 1 else 1.0
        distribution = {label: confidence if label == outcome else (1-confidence)/(len(request.options)-1)
                        for label in request.options} if len(request.options) > 1 else {outcome: 1.0}
        return DecisionResponse(request.request_id, distribution, confidence=confidence, execution_mode="mock")

    def batch_decide(self, requests):
        self.batches += 1
        if self.hook:
            hook, self.hook = self.hook, None
            hook()
        return [self.decide(request) for request in requests]


def evidence():
    text = "Alice knows Bob. Alice and Bob are people."
    return Evidence("ev1", "document1", "document", "v1",
                    EvidenceSpan("document1", "v1", 0, len(text), text),
                    "fixture", "1", datetime(2026, 9, 17))


def proposal(*, version="v1", edge=True, nodes=True):
    ev = evidence()
    candidates = CandidateGraphIR("g", version, datetime(2026, 9, 17))
    if nodes:
        candidates.nodes = [NodeCandidate("a", ObjectKind.NODE, "Alice", [ev], candidate_types=[("Person", 1)]),
                            NodeCandidate("b", ObjectKind.NODE, "Bob", [ev], candidate_types=[("Person", 1)])]
    if edge:
        candidates.edges = [EdgeCandidate("ab", ObjectKind.EDGE, "Alice", "knows", "Bob", [ev],
                                         subject_id="a", object_id="b")]
    constraints = ConstraintSet("schema", "1", {
        "typed": Constraint("typed", "type", "Nodes have types", {"rule": "required_type"}),
        "refs": Constraint("refs", "referential", "Endpoints exist", {"rule": "referential"}),
        "loops": Constraint("loops", "logical", "No self loops", {"rule": "no_self_loops"}),
    })
    return [ev], candidates, constraints


def seeded_store():
    return InMemoryGraphStore("g", nodes={"a": {"mention": "Alice", "types": ["Person"]},
                                          "b": {"mention": "Bob", "types": ["Person"]}})


def make_compiler(*args, **kwargs):
    kwargs.setdefault("allowed_execution_modes", {"mock"})
    return GraphCompiler(*args, **kwargs)


class CompilerTests(unittest.TestCase):
    def test_real_graph_edge_and_atomic_provenance(self):
        backend = FixedBackend()
        compiler = make_compiler("g", backend)
        tx, ctx = compiler.compile(*proposal())
        state = compiler.store.snapshot()
        self.assertEqual(tx.status, "committed", ctx.errors)
        self.assertEqual(state.version, "v2")
        self.assertEqual(set(state.nodes), {"a", "b"})
        self.assertEqual(state.edges["ab"]["subject"], "a")
        self.assertEqual(state.edges["ab"]["object"], "b")
        self.assertEqual(len(state.provenance), 3)
        self.assertEqual([m.operation for m in tx.mutations].count(MutationOperation.CREATE_EDGE), 1)
        for mutation in tx.mutations:
            entry = state.provenance[mutation.mutation_id]
            self.assertEqual(entry.transaction_id, tx.transaction_id)
            self.assertEqual(entry.candidate_id, mutation.candidate_link)
            self.assertEqual(entry.graph_version, "v2")
            self.assertTrue(entry.evidence)
            self.assertTrue(all(c.status == ConstraintStatus.PASS for c in entry.constraints_checked))
            self.assertEqual(mutation.status, MutationStatus.COMMITTED)
            self.assertIsNotNone(mutation.committed_at)
        self.assertEqual(backend.batches, 1)
        self.assertEqual(len(backend.calls), len(ctx.decision_ledger.decisions))
        self.assertTrue(all(r.state and r.options for r in backend.calls))
        self.assertEqual({d.execution_mode for d in ctx.decision_ledger.decisions.values()}, {"mock"})

    def test_high_confidence_refutation_and_neutral_never_create_edge(self):
        for label in ("REFUTES", "NOT_ENOUGH_INFO"):
            with self.subTest(label=label):
                compiler = make_compiler("g", FixedBackend(label), store=seeded_store())
                tx, ctx = compiler.compile(*proposal(nodes=False))
                self.assertEqual(tx.status, "no_op")
                self.assertEqual(ctx.rejected_candidates["ab"], label)
                self.assertEqual(compiler.store.snapshot().edges, {})
                self.assertEqual(compiler.graph_version, "v1")

    def test_binary_requires_explicit_legacy_conversion(self):
        backend = FixedBackend(overrides={"relation_support": "BINARY_FALSE"})
        compiler = make_compiler("g", backend, store=seeded_store())
        tx, ctx = compiler.compile(*proposal(nodes=False))
        self.assertEqual(tx.status, "rejected")
        self.assertTrue(any("Invalid probability" in e for e in ctx.errors))
        compiler = make_compiler("g", backend, store=seeded_store(), allow_legacy_binary=True)
        tx, ctx = compiler.compile(*proposal(nodes=False))
        self.assertEqual(tx.status, "no_op")
        self.assertEqual(ctx.rejected_candidates["ab"], "NOT_ENOUGH_INFO")
        self.assertFalse(compiler.store.snapshot().edges)

    def test_dry_run_is_honest_and_does_not_cache_retry(self):
        compiler = make_compiler("g", FixedBackend())
        before = compiler.store.snapshot()
        tx, ctx = compiler.compile(*proposal(), dry_run=True, idempotency_key="first")
        self.assertEqual(tx.status, "dry_run")
        self.assertIsNone(tx.committed_at)
        self.assertEqual(tx.graph_version_before, tx.graph_version_after)
        self.assertFalse(ctx.mutations_committed)
        self.assertTrue(all(m.committed_at is None for m in tx.mutations))
        self.assertEqual(compiler.store.snapshot(), before)
        committed, _ = compiler.compile(*proposal(), idempotency_key="first")
        self.assertEqual(committed.status, "committed")

    def test_failure_in_middle_rolls_back_graph_and_provenance(self):
        compiler = make_compiler("g", FixedBackend())
        before = compiler.store.snapshot()
        tx, ctx = compiler.compile(*proposal(), failure_after=1)
        self.assertEqual(tx.status, "rejected")
        self.assertIn("Injected failure", tx.errors[-1])
        self.assertEqual(compiler.store.snapshot(), before)
        self.assertFalse(ctx.mutations_committed)

    def test_unsupported_and_false_constraints_block_atomically(self):
        for formal_spec, status in (("False", ConstraintStatus.FAIL),
                                    ("__import__('os').system('echo unsafe')", ConstraintStatus.UNKNOWN)):
            with self.subTest(formal_spec=formal_spec):
                inputs = proposal()
                inputs[2].constraints["bad"] = Constraint("bad", "logical", "Cannot pass", formal_spec)
                compiler = make_compiler("g", FixedBackend())
                tx, ctx = compiler.compile(*inputs)
                self.assertEqual(tx.status, "rejected")
                self.assertEqual(ctx.constraints["bad"].status, status)
                self.assertFalse(compiler.store.snapshot().nodes)
                self.assertFalse(compiler.provenance_db)

    def test_missing_endpoint_cannot_materialize(self):
        compiler = make_compiler("g", FixedBackend())
        tx, ctx = compiler.compile(*proposal(nodes=False))
        self.assertEqual(tx.status, "rejected")
        self.assertIn("unresolved endpoint", ctx.rejected_candidates["ab"])
        self.assertFalse(compiler.store.snapshot().edges)

    def test_low_confidence_dependency_blocks_edge(self):
        compiler = make_compiler("g", FixedBackend(confidence=.8))
        tx, ctx = compiler.compile(*proposal())
        self.assertEqual(tx.status, "no_op")
        self.assertEqual(len(ctx.mutations_escalated), 3)
        self.assertFalse(compiler.store.snapshot().nodes)

    def test_dependency_risk_budget_counts_unique_events(self):
        compiler = make_compiler("g", FixedBackend(), dependency_risk_budget=.02)
        tx, ctx = compiler.compile(*proposal())
        self.assertEqual(tx.status, "committed")
        self.assertEqual(len(compiler.store.snapshot().nodes), 2)
        self.assertFalse(compiler.store.snapshot().edges)
        self.assertEqual(len(ctx.mutations_escalated), 1)

    def test_idempotent_retry_has_no_new_calls_or_version_change(self):
        backend = FixedBackend()
        compiler = make_compiler("g", backend)
        tx, _ = compiler.compile(*proposal(), idempotency_key="retry")
        calls = len(backend.calls)
        second, _ = compiler.compile(*proposal(), idempotency_key="retry")
        self.assertEqual(second.transaction_id, tx.transaction_id)
        self.assertEqual(len(backend.calls), calls)
        self.assertEqual(compiler.graph_version, "v2")
        altered = proposal()
        altered[1].edges[0].predicate_mention = "dislikes"
        conflict, _ = compiler.compile(*altered, idempotency_key="retry")
        self.assertEqual(conflict.status, "conflict")
        self.assertEqual(compiler.store.snapshot().edges["ab"]["predicate"], "knows")

    def test_stale_version_before_inference(self):
        backend = FixedBackend()
        compiler = make_compiler("g", backend)
        tx, _ = compiler.compile(*proposal(), expected_version="v0")
        self.assertEqual(tx.status, "conflict")
        self.assertFalse(backend.calls)

    def test_concurrent_writer_invalidates_verified_snapshot(self):
        store = InMemoryGraphStore("g")
        other = make_compiler("g", FixedBackend(), store=store)
        backend = FixedBackend(hook=lambda: other.compile(*proposal(edge=False)))
        compiler = make_compiler("g", backend, store=store)
        tx, _ = compiler.compile(*proposal())
        self.assertEqual(tx.status, "conflict")
        state = store.snapshot()
        self.assertEqual(state.version, "v2")
        self.assertEqual(len(state.nodes), 2)
        self.assertFalse(state.edges)
        self.assertEqual(len(state.provenance), 2)

    def test_returned_snapshots_and_transactions_cannot_mutate_store(self):
        compiler = make_compiler("g", FixedBackend())
        tx, _ = compiler.compile(*proposal())
        snapshot = compiler.store.snapshot()
        snapshot.nodes.clear()
        tx.mutations.clear()
        self.assertEqual(len(compiler.store.snapshot().nodes), 2)
        self.assertEqual(len(compiler.store.snapshot().provenance), 3)

    def test_property_candidates_use_set_property(self):
        inputs = proposal(nodes=False, edge=False)
        inputs[1].properties = [PropertyCandidate("prop", "a", "role", "researcher", inputs[0])]
        compiler = make_compiler("g", FixedBackend(), store=seeded_store())
        tx, _ = compiler.compile(*inputs)
        self.assertEqual(tx.status, "committed")
        self.assertEqual(tx.mutations[0].operation, MutationOperation.SET_PROPERTY)
        self.assertEqual(compiler.store.snapshot().nodes["a"]["properties"]["role"], "researcher")

    def test_existing_entity_choices_receive_records(self):
        inputs = proposal(nodes=False, edge=False)
        inputs[1].nodes = [NodeCandidate("alias", ObjectKind.NODE, "A. Scientist", inputs[0],
                                       candidate_entities=[("a", 1)], candidate_types=[("Researcher", 1)])]
        backend = FixedBackend()
        compiler = make_compiler("g", backend, store=seeded_store())
        tx, _ = compiler.compile(*inputs)
        self.assertEqual(tx.status, "committed")
        self.assertEqual(backend.calls[0].payload["candidates"]["a"]["mention"], "Alice")
        self.assertIn("Researcher", compiler.store.snapshot().nodes["a"]["types"])
        self.assertNotIn("alias", compiler.store.snapshot().nodes)

    def test_malformed_response_and_unavailable_are_honest(self):
        compiler = make_compiler("g", FixedBackend(overrides={"relation_support": "ERROR"}), store=seeded_store())
        tx, ctx = compiler.compile(*proposal(nodes=False))
        self.assertEqual(tx.status, "rejected")
        self.assertFalse(ctx.decision_ledger.decisions)
        self.assertFalse(compiler.provenance_db)

    def test_direct_store_rejects_invalid_mutation_and_missing_certificate(self):
        compiler = make_compiler("g", FixedBackend())
        tx, ctx = compiler.compile(*proposal(), dry_run=True)
        invalid = deepcopy(tx.mutations)
        invalid[0].operation = MutationOperation.MERGE_NODES
        with self.assertRaisesRegex(GraphValidationError, "Mutation payload differs"):
            compiler.store.commit(invalid, expected_version="v1", constraints=ctx.constraints,
                                  provenance=compiler._provenance(ctx, invalid), fingerprint="bad", certificate=ctx.certificate)
        with self.assertRaisesRegex(GraphValidationError, "Incomplete provenance"):
            compiler.store.commit(tx.mutations, expected_version="v1", constraints={}, provenance={}, fingerprint="bad")
        self.assertFalse(compiler.store.snapshot().nodes)

    def test_supported_constraint_rules(self):
        compiler = make_compiler("g", FixedBackend())
        compiler.compile(*proposal())
        snapshot = compiler.store.snapshot()
        for spec, expected in (({"rule": "domain_range", "predicate": "knows", "domain": "Person"}, ConstraintStatus.PASS),
                               ({"rule": "cardinality", "predicate": "knows", "max": 0}, ConstraintStatus.FAIL),
                               ({"rule": "cardinality", "predicate": "knows", "max": -1}, ConstraintStatus.UNKNOWN),
                               ({"rule": "unique_property", "property": "identifier"}, ConstraintStatus.PASS)):
            rule = Constraint("test", "logical", "Fixture rule", spec)
            self.assertEqual(evaluate_constraint(rule, snapshot)[0], expected)

    def test_diagnostic_modes_require_explicit_commit_permission(self):
        for mode in ("mock", "unknown"):
            class DiagnosticBackend(FixedBackend):
                def decide(self, request):
                    response = super().decide(request)
                    response.execution_mode = mode
                    return response
            with self.subTest(mode=mode):
                compiler = GraphCompiler("g", DiagnosticBackend())
                tx, ctx = compiler.compile(*proposal())
                self.assertEqual(tx.status, "rejected")
                self.assertFalse(compiler.store.snapshot().nodes)
                self.assertIn("Execution mode not permitted", tx.errors[-1])
                preview, _ = compiler.compile(*proposal(), dry_run=True)
                self.assertEqual(preview.status, "dry_run")
                self.assertIsNone(preview.committed_at)

    def test_unregistered_or_changed_candidate_evidence_rejected_before_inference(self):
        for remove, alter in ((True, False), (False, True)):
            inputs = proposal()
            if remove:
                inputs[0].clear()
            if alter:
                inputs[1].edges[0].evidence = deepcopy(inputs[1].edges[0].evidence)
                inputs[1].edges[0].evidence[0].location.content = "Changed content"
            backend = FixedBackend()
            compiler = make_compiler("g", backend)
            tx, _ = compiler.compile(*inputs)
            self.assertEqual(tx.status, "rejected")
            self.assertIn("Candidate evidence missing or changed", tx.errors[-1])
            self.assertFalse(backend.calls)
            self.assertFalse(compiler.store.snapshot().nodes)

    def test_invalid_probability_vectors_cannot_mutate_graph(self):
        for distribution in ({"SUPPORTS": float("nan"), "REFUTES": 0, "NOT_ENOUGH_INFO": 0},
                             {"SUPPORTS": .99, "REFUTES": .99, "NOT_ENOUGH_INFO": 0},
                             {"SUPPORTS": 1.1, "REFUTES": -.1, "NOT_ENOUGH_INFO": 0},
                             {"unrecognized_label": 1.0}):
            class InvalidBackend(FixedBackend):
                def decide(self, request):
                    return DecisionResponse(request.request_id, distribution, execution_mode="mock")
            compiler = make_compiler("g", InvalidBackend(), store=seeded_store())
            tx, _ = compiler.compile(*proposal(nodes=False))
            self.assertEqual(tx.status, "rejected")
            self.assertFalse(compiler.store.snapshot().edges)

    def test_backend_cannot_rewrite_preserved_request(self):
        class MutatingBackend(FixedBackend):
            def decide(self, request):
                response = super().decide(request)
                request.state = "overwritten evidence"
                request.payload["claim"] = "overwritten claim"
                return response
        compiler = make_compiler("g", MutatingBackend(), store=seeded_store())
        tx, ctx = compiler.compile(*proposal(nodes=False))
        self.assertEqual(tx.status, "committed")
        self.assertEqual(ctx.requests[0].state, evidence().location.content)
        self.assertEqual(tx.certificate["requests"][0]["payload"]["claim"], "Alice knows Bob")

    def test_malformed_response_payload_is_rejected_without_application(self):
        class MissingDistribution(FixedBackend):
            def decide(self, request):
                return DecisionResponse(request.request_id, None, execution_mode="mock")
        compiler = make_compiler("g", MissingDistribution(), store=seeded_store())
        before = compiler.store.snapshot()
        tx, _ = compiler.compile(*proposal(nodes=False))
        self.assertEqual(tx.status, "rejected")
        self.assertEqual(compiler.store.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
