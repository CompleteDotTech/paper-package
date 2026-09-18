"""Compile typed semantic judgments into verified in-memory transactions."""
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import math
from typing import Any, Dict, List, Optional
import uuid

from pgc.ir import (CandidateGraphIR, Decision, DecisionLedger, Evidence,
                    MutationOperation, MutationPlan, MutationStatus, ObjectKind,
                    PrimitiveType, ProvenanceEntry, Transaction)
from pgc.decision import DecisionRequest, DecisionResponse
from pgc.compiler.graph_store import (
    GraphValidationError, IdempotencyConflict, InMemoryGraphStore, VersionConflict, mutation_fingerprint)

RELATION_LABELS = ["SUPPORTS", "REFUTES", "NOT_ENOUGH_INFO"]


def _canonical(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _canonical(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    return value


def _digest(value):
    return hashlib.sha256(json.dumps(_canonical(value), sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


@dataclass
class CompilationContext:
    compilation_id: str
    graph_id: str
    graph_version: str
    timestamp: datetime
    evidence: List[Evidence] = field(default_factory=list)
    candidate_graph: Optional[CandidateGraphIR] = None
    decision_ledger: DecisionLedger = field(default_factory=lambda: DecisionLedger(str(uuid.uuid4()), "pending"))
    constraints: Dict[str, Any] = field(default_factory=dict)
    mutations: List[MutationPlan] = field(default_factory=list)
    mutations_committed: List[MutationPlan] = field(default_factory=list)
    mutations_escalated: List[MutationPlan] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    requests: List[DecisionRequest] = field(default_factory=list)
    rejected_candidates: Dict[str, str] = field(default_factory=dict)
    certificate: Dict[str, Any] = field(default_factory=dict)
    dry_run: bool = False


class GraphCompiler:
    def __init__(self, graph_id, decision_backend, *, store=None, confidence_threshold=.85,
                 dependency_risk_budget=None, allow_legacy_binary=False, allowed_execution_modes=None):
        if not 0 <= confidence_threshold <= 1:
            raise ValueError("confidence_threshold must be in [0, 1]")
        if dependency_risk_budget is not None and not 0 <= dependency_risk_budget <= 1:
            raise ValueError("dependency_risk_budget must be in [0, 1]")
        self.graph_id, self.backend = graph_id, decision_backend
        self.store = store or InMemoryGraphStore(graph_id)
        if self.store.snapshot().graph_id != graph_id:
            raise ValueError("Store belongs to a different graph")
        self.confidence_threshold = confidence_threshold
        self.dependency_risk_budget = dependency_risk_budget
        self.allow_legacy_binary = allow_legacy_binary
        self.allowed_execution_modes = frozenset({"real"} if allowed_execution_modes is None else allowed_execution_modes)
        if not self.allowed_execution_modes or not self.allowed_execution_modes.issubset({"real", "mock", "unknown"}):
            raise ValueError("allowed_execution_modes must select real, mock, or explicitly unknown")

    @property
    def graph_version(self):
        return self.store.snapshot().version

    @property
    def provenance_db(self):
        return self.store.snapshot().provenance

    def compile(self, evidence, candidate_graph, constraints, dry_run=False, *,
                expected_version=None, idempotency_key=None, failure_after=None):
        snapshot = self.store.snapshot()
        ctx = CompilationContext(str(uuid.uuid4()), self.graph_id, snapshot.version, datetime.now(timezone.utc))
        ctx.evidence, ctx.candidate_graph = deepcopy(evidence), deepcopy(candidate_graph)
        ctx.constraints = deepcopy(constraints.constraints)
        ctx.decision_ledger.graph_id = self.graph_id
        ctx.dry_run = dry_run
        expected = expected_version if expected_version is not None else candidate_graph.version
        try:
            candidate_payload = asdict(ctx.candidate_graph)
            candidate_payload.pop("timestamp", None)
            fingerprint = _digest({
                "evidence": [asdict(item) for item in ctx.evidence], "candidates": candidate_payload,
                "expected_version": expected,
                "schema_id": constraints.schema_id, "schema_version": constraints.schema_version,
                "constraints": {k: {"type": v.constraint_type, "spec": v.formal_spec} for k, v in ctx.constraints.items()},
                "backend": [self.backend.name(), self.backend.version()],
                "policy": [self.confidence_threshold, self.dependency_risk_budget, self.allow_legacy_binary,
                           sorted(self.allowed_execution_modes)]})
        except (ValueError, TypeError, OverflowError) as error:
            ctx.errors.append("Input cannot be fingerprinted: " + str(error))
            return Transaction(str(uuid.uuid4()), self.graph_id, snapshot.version, snapshot.version,
                               status="rejected", errors=list(ctx.errors), committed_by=""), ctx
        try:
            if not dry_run:
                previous = self.store.lookup_retry(idempotency_key, fingerprint)
                if previous is not None:
                    ctx.mutations = deepcopy(previous.mutations)
                    ctx.mutations_committed = deepcopy(previous.mutations) if previous.status == "committed" else []
                    ctx.certificate = deepcopy(previous.certificate)
                    return previous, ctx
            if candidate_graph.graph_id != self.graph_id:
                raise GraphValidationError("Candidate graph ID does not match compiler")
            if snapshot.version != expected:
                raise VersionConflict("Expected " + str(expected) + "; current " + snapshot.version)
            ids = [c.candidate_id for c in candidate_graph.nodes + candidate_graph.edges + candidate_graph.properties]
            if len(set(ids)) != len(ids):
                raise GraphValidationError("Duplicate candidate IDs")
            evidence_by_id = {}
            for item in ctx.evidence:
                if item.evidence_id in evidence_by_id:
                    raise GraphValidationError("Duplicate evidence ID: " + item.evidence_id)
                if (item.source_id != item.location.source_id or item.source_version != item.location.source_version
                        or not item.location.content or item.location.start_char < 0
                        or item.location.end_char < item.location.start_char):
                    raise GraphValidationError("Invalid evidence snapshot: " + item.evidence_id)
                evidence_by_id[item.evidence_id] = _digest(asdict(item))
            for candidate in ctx.candidate_graph.nodes + ctx.candidate_graph.edges + ctx.candidate_graph.properties:
                for item in candidate.evidence:
                    if evidence_by_id.get(item.evidence_id) != _digest(asdict(item)):
                        raise GraphValidationError("Candidate evidence missing or changed: " + item.evidence_id)
            bindings = self._invoke_once(ctx, self._requests(ctx, snapshot))
            self._plan(ctx, snapshot, bindings)
            accepted = [m for m in ctx.mutations if m.status == MutationStatus.AUTO_COMMITTABLE]
            if not accepted and ctx.errors:
                raise GraphValidationError("No valid mutations: " + "; ".join(ctx.errors))
            ctx.certificate = {
                "input_fingerprint": fingerprint, "schema_id": constraints.schema_id,
                "schema_version": constraints.schema_version, "policy_version": "typed-v1",
                "confidence_threshold": self.confidence_threshold,
                "dependency_risk_budget": self.dependency_risk_budget,
                "allowed_execution_modes": sorted(self.allowed_execution_modes),
                "risk_semantics": "sum of estimated prerequisite error; not a statistical guarantee",
                "decision_errors": list(ctx.errors),
                "candidates": _canonical(asdict(ctx.candidate_graph)),
                "mutation_sha256": {mutation.mutation_id: mutation_fingerprint(mutation) for mutation in accepted},
                "evidence_sha256": {ev.evidence_id: _digest(asdict(ev)) for ev in ctx.evidence},
                "requests": [_canonical(asdict(r)) for r in ctx.requests],
                "decisions": [_canonical(asdict(d)) for d in ctx.decision_ledger.decisions.values()]}
            transaction = self.store.commit(
                accepted, expected_version=expected, constraints=ctx.constraints,
                provenance=self._provenance(ctx, accepted), fingerprint=fingerprint,
                idempotency_key=idempotency_key, committed_by=self.backend.name(),
                certificate=ctx.certificate, dry_run=dry_run, failure_after=failure_after)
            ctx.certificate = deepcopy(transaction.certificate)
            if transaction.status == "committed":
                ctx.mutations_committed = deepcopy(transaction.mutations)
            return transaction, ctx
        except (GraphValidationError, ValueError, TypeError) as error:
            ctx.errors.append(str(error))
            for mutation in ctx.mutations:
                if mutation.status == MutationStatus.AUTO_COMMITTABLE:
                    mutation.status = MutationStatus.REVIEW_REQUIRED
                    mutation.requires_review = True
                    ctx.mutations_escalated.append(mutation)
            status = "conflict" if isinstance(error, (VersionConflict, IdempotencyConflict)) else "rejected"
            return Transaction(str(uuid.uuid4()), self.graph_id, snapshot.version, snapshot.version,
                               status=status, errors=list(ctx.errors), fingerprint=fingerprint,
                               committed_by="", certificate=deepcopy(ctx.certificate)), ctx

    def _requests(self, ctx, snapshot):
        specs = []
        node_mentions = {n.mention for n in ctx.candidate_graph.nodes}

        def add(candidate, role, question, options, task, payload):
            if not options or len(set(options)) != len(options):
                ctx.errors.append("Invalid options: " + candidate.candidate_id + ":" + role)
                return
            state = "\n".join(ev.location.content for ev in candidate.evidence)
            request = DecisionRequest(str(uuid.uuid4()), PrimitiveType.CHOICE, question, state,
                                      options=options, task=task, payload={**payload, "evidence": state}, labels=options)
            specs.append((candidate.candidate_id, role, request))
            ctx.requests.append(request)

        for node in ctx.candidate_graph.nodes:
            if node.kind != ObjectKind.NODE:
                ctx.errors.append("Unsupported node kind: " + str(node.kind))
                continue
            if node.candidate_entities:
                records = {eid: snapshot.nodes[eid] for eid, _ in node.candidate_entities if eid in snapshot.nodes}
                if len(records) != len(node.candidate_entities):
                    ctx.errors.append("Candidate entity records unavailable: " + node.candidate_id)
                else:
                    add(node, "identity", "Which entity does the mention identify?", list(records) + ["new", "defer"],
                        "entity_resolution_choice", {"mention": node.mention, "candidates": records})
            else:
                add(node, "identity", "Does the evidence justify creating this entity?", ["create", "reject", "unknown"],
                    "node_existence", {"mention": node.mention})
            if node.candidate_types:
                add(node, "type", "What is the type of " + node.mention + "?", [t for t, _ in node.candidate_types],
                    "node_type", {"mention": node.mention})
            for name, values in node.candidate_properties.items():
                add(node, "property:" + name, "What is the " + name + " of " + node.mention + "?",
                    [v for v, _ in values], "property_value", {"mention": node.mention, "property": name})
        for edge in ctx.candidate_graph.edges:
            if edge.kind != ObjectKind.EDGE:
                ctx.errors.append("Unsupported edge kind: " + str(edge.kind))
                continue
            claim = " ".join((edge.subject_mention, edge.predicate_mention, edge.object_mention))
            add(edge, "support", "Classify the evidence for this claim.", RELATION_LABELS, "relation_support", {"claim": claim})
            if edge.predicate_candidates:
                add(edge, "predicate", "Which relation is supported?", [p for p, _ in edge.predicate_candidates],
                    "relation_type", {"claim": claim})
            for role in ("subject", "object"):
                mention = getattr(edge, role + "_mention")
                if getattr(edge, role + "_id") or mention in node_mentions or mention in snapshot.nodes:
                    continue
                candidates = getattr(edge, role + "_candidates")
                if candidates:
                    records = {eid: snapshot.nodes[eid] for eid, _ in candidates if eid in snapshot.nodes}
                    if len(records) != len(candidates):
                        ctx.errors.append("Endpoint records unavailable: " + edge.candidate_id + ":" + role)
                    else:
                        add(edge, role, "Which entity does this endpoint identify?", list(records) + ["defer"],
                            "entity_resolution_choice", {"mention": mention, "candidates": records})
        for prop in ctx.candidate_graph.properties:
            add(prop, "property", "What is the " + prop.property_name + "?",
                [v for v, _ in prop.candidate_values] or [prop.proposed_value], "property_value",
                {"entity_id": prop.entity_id, "property": prop.property_name})
        return specs

    def _invoke_once(self, ctx, specs):
        if not specs:
            return {}
        try:
            responses = list(self.backend.batch_decide([deepcopy(spec[2]) for spec in specs]))
        except Exception as error:
            ctx.errors.append("Backend batch failed: " + str(error))
            return {}
        response_map, duplicates = {}, set()
        for response in responses:
            if not isinstance(response, DecisionResponse):
                ctx.errors.append("Backend returned an invalid response envelope")
                return {}
            if response.request_id in response_map:
                duplicates.add(response.request_id)
            response_map[response.request_id] = response
        if set(response_map) - {spec[2].request_id for spec in specs}:
            ctx.errors.append("Backend returned unknown request IDs")
            return {}
        bindings = {}
        for candidate_id, role, request in specs:
            response = response_map.get(request.request_id)
            if response is None or request.request_id in duplicates:
                ctx.errors.append("Missing or duplicate response: " + request.request_id)
                continue
            if response.error or response.execution_mode == "unavailable":
                ctx.errors.append("Decision unavailable: " + (response.error or request.request_id))
                continue
            distribution = dict(response.distribution)
            if request.task == "relation_support" and set(distribution) == {"true", "false"} and self.allow_legacy_binary:
                distribution = {"SUPPORTS": distribution["true"], "REFUTES": 0.0, "NOT_ENOUGH_INFO": distribution["false"]}
            if (set(distribution) != set(request.labels) or
                    any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in distribution.values()) or
                    not math.isclose(sum(distribution.values()), 1.0, abs_tol=1e-6)):
                ctx.errors.append("Invalid probability distribution: " + request.request_id)
                continue
            selected = max(request.labels, key=distribution.get)
            decision = Decision(request.request_id, request.primitive, request.question, self.backend.name(), self.backend.version(),
                                distribution, confidence=distribution[selected], raw_output=deepcopy(response.raw_output),
                                state_hash=_digest(asdict(request)), candidate_id=candidate_id, selected_outcome=selected,
                                request=_canonical(asdict(request)), execution_mode=response.execution_mode,
                                model_params={"response_metadata": deepcopy(response.metadata)})
            ctx.decision_ledger.record(decision)
            bindings[candidate_id, role] = decision
            if not ctx.dry_run and decision.execution_mode not in self.allowed_execution_modes:
                ctx.errors.append("Execution mode not permitted for commits: " + decision.execution_mode)
        return bindings

    def _plan(self, ctx, snapshot, bindings):
        node_bindings, mentions = {}, {}
        decisions = ctx.decision_ledger.decisions

        def selected(candidate, role):
            return bindings.get((candidate.candidate_id, role))

        def add(candidate, operation, target, linked, dependencies=None, **payload):
            unique = list(dict.fromkeys(d.decision_id for d in linked if d is not None))
            dependency_ids = list(dict.fromkeys(dependencies or []))
            acceptable = bool(unique) and bool(candidate.evidence)
            acceptable &= all(decisions[key].confidence >= self.confidence_threshold for key in unique)
            acceptable &= all(ctx.dry_run or decisions[key].execution_mode in self.allowed_execution_modes for key in unique)
            if self.dependency_risk_budget is not None:
                acceptable &= sum(1 - decisions[key].confidence for key in unique) <= self.dependency_risk_budget + 1e-12
            acceptable &= all(any(m.mutation_id == key and m.status == MutationStatus.AUTO_COMMITTABLE
                                  for m in ctx.mutations) for key in dependency_ids)
            mutation = MutationPlan(str(uuid.uuid4()), operation, target_entity=target,
                                    preconditions=["target_not_exists"] if operation in (MutationOperation.CREATE_NODE, MutationOperation.CREATE_EDGE) else ["target_exists"],
                                    postconditions=["target_exists"], evidence_links=deepcopy(candidate.evidence),
                                    decision_links=unique, candidate_link=candidate.candidate_id, dependencies=dependency_ids,
                                    status=MutationStatus.AUTO_COMMITTABLE if acceptable else MutationStatus.REVIEW_REQUIRED,
                                    requires_review=not acceptable, **payload)
            ctx.mutations.append(mutation)
            if not acceptable:
                ctx.mutations_escalated.append(mutation)
            return mutation

        for node in ctx.candidate_graph.nodes:
            identity = selected(node, "identity")
            if identity is None or identity.selected_outcome in ("reject", "unknown", "defer"):
                ctx.rejected_candidates[node.candidate_id] = identity.selected_outcome if identity else "unavailable"
                continue
            entity_id = node.candidate_id if identity.selected_outcome in ("new", "create") else identity.selected_outcome
            linked = [identity]
            node_type = selected(node, "type")
            if node.candidate_types and node_type is None:
                ctx.rejected_candidates[node.candidate_id] = "type unavailable"
                continue
            if node_type is not None:
                node_type.depends_on = [identity.decision_id]
                linked.append(node_type)
            properties, missing = {}, False
            for name in node.candidate_properties:
                chosen = selected(node, "property:" + name)
                if chosen is None:
                    missing = True
                    continue
                chosen.depends_on = [identity.decision_id]
                linked.append(chosen)
                properties[name] = chosen.selected_outcome
            if missing:
                ctx.rejected_candidates[node.candidate_id] = "property unavailable"
                continue
            prerequisites = []
            if identity.selected_outcome in ("new", "create"):
                mutation = add(node, MutationOperation.CREATE_NODE, entity_id, linked,
                               new_type=node_type.selected_outcome if node_type else None,
                               new_properties={"mention": node.mention, **properties}, selected_outcome=identity.selected_outcome)
                prerequisites.append(mutation.mutation_id)
            else:
                if node_type is not None:
                    prerequisites.append(add(node, MutationOperation.ADD_TYPE, entity_id, linked, new_type=node_type.selected_outcome).mutation_id)
                if properties:
                    prerequisites.append(add(node, MutationOperation.SET_PROPERTY, entity_id, linked, new_properties=properties).mutation_id)
            node_bindings[node.candidate_id] = (entity_id, linked, prerequisites)
            mentions.setdefault(node.mention, []).append(node.candidate_id)

        def endpoint(edge, role):
            explicit, mention = getattr(edge, role + "_id"), getattr(edge, role + "_mention")
            if explicit:
                return node_bindings.get(explicit) or ((explicit, [], []) if explicit in snapshot.nodes else None)
            candidate_ids = mentions.get(mention, [])
            if len(candidate_ids) == 1:
                return node_bindings[candidate_ids[0]]
            if len(candidate_ids) > 1:
                return None
            if mention in snapshot.nodes:
                return mention, [], []
            choice = selected(edge, role)
            if choice and choice.selected_outcome in snapshot.nodes:
                return choice.selected_outcome, [choice], []
            return None

        for edge in ctx.candidate_graph.edges:
            support = selected(edge, "support")
            if support is None or support.selected_outcome != "SUPPORTS":
                ctx.rejected_candidates[edge.candidate_id] = support.selected_outcome if support else "unavailable"
                continue
            subject, object_, predicate = endpoint(edge, "subject"), endpoint(edge, "object"), selected(edge, "predicate")
            if subject is None or object_ is None or (edge.predicate_candidates and predicate is None):
                ctx.rejected_candidates[edge.candidate_id] = "unresolved endpoint or predicate"
                ctx.errors.append("Unresolved edge dependency: " + edge.candidate_id)
                continue
            linked = subject[1] + object_[1] + [support] + ([predicate] if predicate else [])
            support.depends_on = list(dict.fromkeys(d.decision_id for d in subject[1] + object_[1]))
            if predicate:
                predicate.depends_on = list(support.depends_on)
            add(edge, MutationOperation.CREATE_EDGE, edge.candidate_id, linked, subject[2] + object_[2],
                subject_id=subject[0], object_id=object_[0], predicate=predicate.selected_outcome if predicate else edge.predicate_mention,
                selected_outcome="SUPPORTS")
        for prop in ctx.candidate_graph.properties:
            chosen = selected(prop, "property")
            if chosen is None:
                continue
            target = node_bindings.get(prop.entity_id) or ((prop.entity_id, [], []) if prop.entity_id in snapshot.nodes else None)
            if target is None:
                ctx.errors.append("Unresolved property target: " + prop.entity_id)
                continue
            chosen.depends_on = [d.decision_id for d in target[1]]
            add(prop, MutationOperation.SET_PROPERTY, target[0], target[1] + [chosen], target[2],
                new_properties={prop.property_name: chosen.selected_outcome})

    def _provenance(self, ctx, mutations):
        return {m.mutation_id: ProvenanceEntry(
            entity_id=m.target_entity, entity_kind=ObjectKind.EDGE if m.operation == MutationOperation.CREATE_EDGE else ObjectKind.NODE,
            evidence=deepcopy(m.evidence_links), candidate_id=m.candidate_link,
            decisions=[deepcopy(ctx.decision_ledger.decisions[key]) for key in m.decision_links],
            constraints_checked=deepcopy(list(ctx.constraints.values())), mutation_id=m.mutation_id,
            transaction_id=None, graph_version=ctx.graph_version, created_at=ctx.timestamp) for m in mutations}

    def record_provenance(self, entity_id, entity_kind, evidence, decisions, mutation):
        raise GraphValidationError("Provenance must be committed atomically with its mutation")
