"""Independent certificate-boundary regressions; no models, network, or GPU."""

from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import unittest

from pgc.compiler import GraphCompiler, InMemoryGraphStore
from pgc.compiler.graph_store import GraphValidationError, mutation_fingerprint
from pgc.decision import DecisionBackend, DecisionResponse
from pgc.ir import CandidateGraphIR, ConstraintSet, EdgeCandidate, Evidence, EvidenceSpan, ObjectKind


def canonical(value):
    return json.loads(json.dumps(value, default=lambda item: item.value if isinstance(item, Enum) else item.isoformat()))


def request_hash(request):
    return hashlib.sha256(json.dumps(request, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


class PositiveFixture(DecisionBackend):
    def __init__(self):
        self.calls = 0

    def name(self):
        return "independent-certificate-fixture"

    def version(self):
        return "1"

    def decide(self, request):
        self.calls += 1
        return DecisionResponse(request.request_id,
                                {label: .99 if label == "SUPPORTS" else .005 for label in request.labels},
                                execution_mode="mock")

    def batch_decide(self, requests):
        return [self.decide(request) for request in requests]


def inputs():
    text = "Ada mentors Lin."
    evidence = Evidence("source", "document", "document", "revision-1",
                        EvidenceSpan("document", "revision-1", 0, len(text), text),
                        "independent-fixture", "1", datetime(2026, 9, 17, tzinfo=timezone.utc))
    candidates = CandidateGraphIR("certificate-test", "v1", datetime(2026, 9, 17, tzinfo=timezone.utc))
    candidates.edges = [EdgeCandidate("edge", ObjectKind.EDGE, "Ada", "mentors", "Lin", [evidence],
                                      subject_id="left", object_id="right")]
    return [evidence], candidates, ConstraintSet("schema", "1")


def compiler_fixture():
    store = InMemoryGraphStore("certificate-test", nodes={
        "left": {"mention": "Ada", "types": ["Person"]},
        "right": {"mention": "Lin", "types": ["Person"]},
    })
    return GraphCompiler("certificate-test", PositiveFixture(), store=store, allowed_execution_modes={"mock"})


class IndependentCertificateTests(unittest.TestCase):
    def preview(self):
        compiler = compiler_fixture()
        transaction, context = compiler.compile(*inputs(), dry_run=True)
        self.assertEqual(transaction.status, "dry_run", context.errors)
        self.assertEqual(len(transaction.mutations), 1)
        return compiler, transaction, context

    def commit(self, compiler, transaction, context, mutations, provenance=None, certificate=None):
        return compiler.store.commit(
            mutations, expected_version="v1", constraints=context.constraints,
            provenance=provenance if provenance is not None else compiler._provenance(context, mutations),
            fingerprint=transaction.fingerprint,
            certificate=certificate if certificate is not None else context.certificate,
        )

    def test_changed_edge_action_cannot_use_original_certificate(self):
        for field, replacement in (("predicate", "opposes"), ("subject_id", "right"), ("object_id", "left")):
            with self.subTest(field=field):
                compiler, transaction, context = self.preview()
                before = compiler.store.snapshot()
                mutations = deepcopy(transaction.mutations)
                setattr(mutations[0], field, replacement)
                with self.assertRaisesRegex(GraphValidationError, "certified plan"):
                    self.commit(compiler, transaction, context, mutations)
                self.assertEqual(compiler.store.snapshot(), before)

    def test_rehashed_edge_still_must_match_original_predicate_and_endpoints(self):
        for field, replacement in (("predicate", "opposes"), ("subject_id", "right"), ("object_id", "left")):
            with self.subTest(field=field):
                compiler, transaction, context = self.preview()
                before = compiler.store.snapshot()
                mutations = deepcopy(transaction.mutations)
                setattr(mutations[0], field, replacement)
                certificate = deepcopy(context.certificate)
                certificate["mutation_sha256"][mutations[0].mutation_id] = mutation_fingerprint(mutations[0])
                with self.assertRaisesRegex(GraphValidationError, "Edge (predicate|endpoint) differs"):
                    self.commit(compiler, transaction, context, mutations, certificate=certificate)
                self.assertEqual(compiler.store.snapshot(), before)

    def test_changed_provenance_decision_cannot_diverge_from_certificate(self):
        compiler, transaction, context = self.preview()
        before = compiler.store.snapshot()
        mutations = deepcopy(transaction.mutations)
        provenance = compiler._provenance(context, mutations)
        decision = provenance[mutations[0].mutation_id].decisions[0]
        decision.distribution = {"SUPPORTS": 1.0}
        decision.confidence = 1.0
        with self.assertRaisesRegex(GraphValidationError, "original request"):
            self.commit(compiler, transaction, context, mutations, provenance=provenance)
        self.assertEqual(compiler.store.snapshot(), before)

    def test_certified_decision_must_still_include_every_requested_label(self):
        compiler, transaction, context = self.preview()
        mutations = deepcopy(transaction.mutations)
        provenance = compiler._provenance(context, mutations)
        decision = provenance[mutations[0].mutation_id].decisions[0]
        decision.distribution = {"SUPPORTS": 1.0}
        decision.confidence = 1.0
        certificate = deepcopy(context.certificate)
        certificate["decisions"] = [canonical(asdict(decision))]
        with self.assertRaisesRegex(GraphValidationError, "decision probability"):
            self.commit(compiler, transaction, context, mutations, provenance, certificate)
        self.assertEqual(compiler.store.snapshot().version, "v1")
        self.assertFalse(compiler.store.snapshot().provenance)

    def test_self_rehashed_request_cannot_replace_certified_request(self):
        compiler, transaction, context = self.preview()
        mutations = deepcopy(transaction.mutations)
        provenance = compiler._provenance(context, mutations)
        decision = provenance[mutations[0].mutation_id].decisions[0]
        decision.request["question"] = "A different semantic request"
        decision.state_hash = request_hash(decision.request)
        with self.assertRaisesRegex(GraphValidationError, "original request"):
            self.commit(compiler, transaction, context, mutations, provenance)
        self.assertEqual(compiler.store.snapshot().version, "v1")

    def test_successful_commit_persists_matching_request_decision_and_action(self):
        compiler, preview, context = self.preview()
        transaction = self.commit(compiler, preview, context, deepcopy(preview.mutations))
        self.assertEqual(transaction.status, "committed")
        snapshot = compiler.store.snapshot()
        self.assertEqual(snapshot.edges["edge"]["predicate"], "mentors")
        certified = {item["decision_id"]: item for item in transaction.certificate["decisions"]}
        requests = {item["request_id"]: item for item in transaction.certificate["requests"]}
        for mutation in transaction.mutations:
            self.assertEqual(transaction.certificate["mutation_sha256"][mutation.mutation_id], mutation_fingerprint(mutation))
            entry = snapshot.provenance[mutation.mutation_id]
            self.assertEqual(entry.transaction_id, transaction.transaction_id)
            self.assertEqual(entry.graph_version, snapshot.version)
            for decision in entry.decisions:
                self.assertEqual(canonical(asdict(decision)), certified[decision.decision_id])
                self.assertEqual(decision.request, requests[decision.decision_id])
                self.assertEqual(set(decision.distribution), set(decision.request["labels"]))

    def test_nonfinite_input_is_rejected_before_inference_without_side_effects(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                compiler = compiler_fixture()
                before = compiler.store.snapshot()
                arguments = inputs()
                arguments[0][0].metadata["invalid"] = value
                transaction, context = compiler.compile(*arguments)
                self.assertEqual(transaction.status, "rejected")
                self.assertIn("fingerprinted", transaction.errors[0])
                self.assertEqual(compiler.backend.calls, 0)
                self.assertEqual(compiler.store.snapshot(), before)

    def test_retry_with_changed_explicit_expected_version_conflicts(self):
        compiler = compiler_fixture()
        arguments = inputs()
        first, _ = compiler.compile(*arguments, idempotency_key="retry", expected_version="v1")
        self.assertEqual(first.status, "committed")
        before = compiler.store.snapshot()
        calls = compiler.backend.calls
        second, _ = compiler.compile(*arguments, idempotency_key="retry", expected_version="nonexistent-version")
        self.assertEqual(second.status, "conflict")
        self.assertNotEqual(second.transaction_id, first.transaction_id)
        self.assertEqual(compiler.backend.calls, calls)
        self.assertEqual(compiler.store.snapshot(), before)
        exact_retry, _ = compiler.compile(*arguments, idempotency_key="retry", expected_version="v1")
        self.assertEqual(exact_retry.transaction_id, first.transaction_id)
        self.assertEqual(compiler.backend.calls, calls)


if __name__ == "__main__":
    unittest.main()
