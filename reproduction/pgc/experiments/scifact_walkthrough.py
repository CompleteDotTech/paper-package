"""Offline synthetic compiler walkthrough; historical module name retained.

This does not load SciFact, a neural model, or an external service. Predetermined
mock responses demonstrate validated graph state, provenance, and retry rules.
"""
from datetime import datetime
import json

from pgc.compiler import GraphCompiler, InMemoryGraphStore
from pgc.decision import DecisionBackend, DecisionResponse
from pgc.ir import (CandidateGraphIR, Constraint, ConstraintSet, EdgeCandidate,
                    Evidence, EvidenceSpan, ObjectKind)


class WalkthroughBackend(DecisionBackend):
    def __init__(self):
        self.calls = 0

    def name(self):
        return "synthetic-walkthrough"

    def version(self):
        return "1"

    def decide(self, request):
        self.calls += 1
        return DecisionResponse(request.request_id,
                                {"SUPPORTS": .99, "REFUTES": .005, "NOT_ENOUGH_INFO": .005},
                                confidence=.99, execution_mode="mock",
                                metadata={"source": "predetermined demonstration output"})

    def batch_decide(self, requests):
        return [self.decide(request) for request in requests]


def build_example_scifact_claim():
    """Return synthetic evidence, candidates, and constraints (legacy API name)."""
    text = "Synthetic fixture: Research group A collaborates with Research group B."
    evidence = Evidence("ev-demo", "synthetic-document", "document", "1",
                        EvidenceSpan("synthetic-document", "1", 0, len(text), text),
                        "fixture", "1", datetime(2026, 9, 17))
    candidate = EdgeCandidate("collaboration", ObjectKind.EDGE, "Research group A",
                              "collaborates_with", "Research group B", [evidence],
                              subject_id="group-a", object_id="group-b")
    graph = CandidateGraphIR("walkthrough", "v1", datetime(2026, 9, 17), edges=[candidate])
    constraints = ConstraintSet("organizations", "1", {
        "endpoints": Constraint("endpoints", "referential", "Endpoints exist", {"rule": "referential"}),
        "no_self_loops": Constraint("no_self_loops", "logical", "Distinct collaborators", {"rule": "no_self_loops"}),
        "domain_range": Constraint("domain_range", "type", "Organization collaboration",
                                   {"rule": "domain_range", "predicate": "collaborates_with",
                                    "domain": "Organization", "range": "Organization"}),
    })
    return [evidence], graph, constraints


def run_walkthrough():
    evidence, candidates, constraints = build_example_scifact_claim()
    store = InMemoryGraphStore("walkthrough", nodes={
        "group-a": {"mention": "Research group A", "types": ["Organization"]},
        "group-b": {"mention": "Research group B", "types": ["Organization"]},
    })
    backend = WalkthroughBackend()
    # Default commits require mode='real'. A dry run can inspect diagnostic data.
    default_compiler = GraphCompiler("walkthrough", backend, store=store)
    preview, _ = default_compiler.compile(evidence, candidates, constraints, dry_run=True)
    assert preview.status == "dry_run" and preview.committed_at is None
    assert not store.snapshot().edges and store.snapshot().version == "v1"
    blocked, _ = default_compiler.compile(evidence, candidates, constraints)
    assert blocked.status == "rejected" and not store.snapshot().edges

    # Explicitly allow the mock backend for this disposable in-memory example.
    compiler = GraphCompiler("walkthrough", backend, store=store, allowed_execution_modes={"mock"})
    transaction, context = compiler.compile(evidence, candidates, constraints, idempotency_key="demo")
    assert transaction.status == "committed", context.errors
    snapshot = store.snapshot()
    assert snapshot.version == "v2" and set(snapshot.edges) == {"collaboration"}
    assert len(snapshot.provenance) == 1 and transaction.transaction_id in snapshot.transactions

    calls_before_retry = backend.calls
    replay, _ = compiler.compile(evidence, candidates, constraints, idempotency_key="demo")
    assert replay.transaction_id == transaction.transaction_id and backend.calls == calls_before_retry
    stale, _ = compiler.compile(evidence, candidates, constraints, expected_version="v1")
    assert stale.status == "conflict" and store.snapshot() == snapshot
    print(json.dumps({
        "execution_mode": "mock", "data": "synthetic; not a SciFact benchmark",
        "dry_run_status": preview.status, "dry_run_committed_at": preview.committed_at,
        "default_mock_commit_status": blocked.status, "explicit_mock_commit_status": transaction.status,
        "graph_version": snapshot.version, "nodes": len(snapshot.nodes), "edges": len(snapshot.edges),
        "provenance_entries": len(snapshot.provenance), "retry_reused_transaction": True,
        "retry_additional_backend_calls": backend.calls - calls_before_retry,
        "stale_write_status": stale.status,
        "limitations": "In-memory state only; schema validation does not prove semantic truth",
    }, indent=2))
    return context, transaction


if __name__ == "__main__":
    run_walkthrough()
