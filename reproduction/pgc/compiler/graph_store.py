"""Small transactional graph store used for offline compiler experiments.

All mutation application and provenance construction happen on private copies.
A global version compare-and-swap publishes the verified snapshot under a lock.
Constraint specifications are data, never executable Python.
"""

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import RLock
from typing import Any, Dict, Optional
import math
import hashlib
import json
import uuid

from pgc.ir import (
    Constraint, ConstraintStatus, MutationOperation, MutationStatus,
    ProvenanceEntry, Transaction,
)


class GraphValidationError(ValueError):
    pass


class VersionConflict(GraphValidationError):
    pass


class IdempotencyConflict(GraphValidationError):
    pass


def _fingerprint(value):
    def normalize(item):
        if isinstance(item, Enum):
            return item.value
        if isinstance(item, datetime):
            return item.isoformat()
        if isinstance(item, dict):
            return {str(k): normalize(v) for k, v in item.items()}
        if isinstance(item, (list, tuple)):
            return [normalize(v) for v in item]
        return item
    return hashlib.sha256(json.dumps(normalize(value), sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def mutation_fingerprint(mutation):
    """Bind immutable action data; lifecycle timestamps/results are excluded."""
    fields = ("mutation_id", "operation", "target_entity", "target_entities", "new_properties", "new_type",
              "preconditions", "postconditions", "evidence_links", "decision_links", "candidate_link",
              "subject_id", "predicate", "object_id", "dependencies", "selected_outcome", "risk_class", "requires_review")
    data = asdict(mutation)
    return _fingerprint({key: data[key] for key in fields})


@dataclass
class GraphSnapshot:
    graph_id: str
    version: str = "v1"
    nodes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    edges: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # One entry per mutation preserves successive changes to the same object.
    provenance: Dict[str, ProvenanceEntry] = field(default_factory=dict)
    transactions: Dict[str, Transaction] = field(default_factory=dict)


_SHORTHANDS = {
    "all_nodes_typed": {"rule": "required_type"},
    "∀n ∈ nodes: n.type ≠ ∅": {"rule": "required_type"},
    "referential": {"rule": "referential"},
    "∀e ∈ edges: e.subject ∈ nodes ∧ e.object ∈ nodes": {"rule": "referential"},
    "no_self_loops": {"rule": "no_self_loops"},
    "∀e ∈ edges: e.subject ≠ e.object": {"rule": "no_self_loops"},
    "False": {"rule": "always_false"},
    "false": {"rule": "always_false"},
}


def evaluate_constraint(constraint: Constraint, snapshot: GraphSnapshot):
    """Return PASS/FAIL/UNKNOWN with a reason; unknown rules fail closed."""
    spec = constraint.formal_spec
    if isinstance(spec, str):
        spec = _SHORTHANDS.get(spec)
    if not isinstance(spec, dict):
        return ConstraintStatus.UNKNOWN, "Unsupported constraint specification"
    rule = spec.get("rule")
    try:
        if rule == "always_false":
            valid = False
        elif rule == "referential":
            valid = all(e["subject"] in snapshot.nodes and e["object"] in snapshot.nodes
                        for e in snapshot.edges.values())
        elif rule == "no_self_loops":
            valid = all(e["subject"] != e["object"] for e in snapshot.edges.values())
        elif rule == "required_type":
            required = spec.get("type")
            if required is not None and not isinstance(required, str):
                raise ValueError("type must be a string")
            valid = all(bool(n["types"]) and (required is None or required in n["types"])
                        for n in snapshot.nodes.values())
        elif rule == "unique_property":
            prop = spec["property"]
            values = [n["properties"][prop] for n in snapshot.nodes.values()
                      if prop in n["properties"]]
            valid = all(value != previous for index, value in enumerate(values)
                        for previous in values[:index])
        elif rule == "cardinality":
            predicate, maximum = spec["predicate"], spec["max"]
            direction = spec.get("direction", "out")
            if type(maximum) is not int or maximum < 0 or direction not in ("in", "out"):
                raise ValueError("invalid cardinality parameters")
            key = "subject" if direction == "out" else "object"
            counts = {}
            for edge in snapshot.edges.values():
                if edge["predicate"] == predicate:
                    counts[edge[key]] = counts.get(edge[key], 0) + 1
            valid = all(count <= maximum for count in counts.values())
        elif rule == "domain_range":
            predicate = spec["predicate"]
            domain, range_type = spec.get("domain"), spec.get("range")
            if domain is None and range_type is None:
                raise ValueError("domain or range must be provided")
            valid = all((domain is None or domain in snapshot.nodes[e["subject"]]["types"])
                        and (range_type is None or range_type in snapshot.nodes[e["object"]]["types"])
                        for e in snapshot.edges.values() if e["predicate"] == predicate)
        else:
            return ConstraintStatus.UNKNOWN, "Unsupported rule: " + str(rule)
        return (ConstraintStatus.PASS if valid else ConstraintStatus.FAIL,
                "Rule satisfied" if valid else "Rule violated: " + str(rule))
    except (KeyError, TypeError, ValueError) as error:
        return ConstraintStatus.UNKNOWN, "Malformed rule or graph: " + str(error)


class InMemoryGraphStore:
    def __init__(self, graph_id: str, *, nodes=None, edges=None):
        self._lock = RLock()
        self._snapshot = GraphSnapshot(graph_id)
        for entity_id, original in (nodes or {}).items():
            node = deepcopy(original)
            node.update(id=entity_id)
            node.setdefault("mention", entity_id)
            node.setdefault("types", [])
            node.setdefault("properties", {})
            self._snapshot.nodes[entity_id] = node
        self._snapshot.edges = deepcopy(edges or {})
        self._revision = 1
        self._retries = {}
        self._validate_structure(self._snapshot)

    def snapshot(self):
        with self._lock:
            return deepcopy(self._snapshot)

    def lookup_retry(self, key: Optional[str], fingerprint: str):
        if key is None:
            return None
        with self._lock:
            previous = self._retries.get(key)
            if previous is None:
                return None
            previous_fingerprint, transaction = previous
            if previous_fingerprint != fingerprint:
                raise IdempotencyConflict("Idempotency key reused with a different payload")
            return deepcopy(transaction)

    @staticmethod
    def _validate_structure(snapshot):
        if set(snapshot.nodes) & set(snapshot.edges):
            raise GraphValidationError("Node and edge identifiers must be distinct")
        for entity_id, node in snapshot.nodes.items():
            if not isinstance(entity_id, str) or not entity_id or node.get("id") != entity_id:
                raise GraphValidationError("Invalid node identifier")
            if not isinstance(node.get("types"), list) or not isinstance(node.get("properties"), dict):
                raise GraphValidationError("Invalid node payload")
            if any(not isinstance(t, str) or not t for t in node["types"]):
                raise GraphValidationError("Invalid node type")
        triples = set()
        for entity_id, edge in snapshot.edges.items():
            if edge.get("id") != entity_id or not edge.get("predicate"):
                raise GraphValidationError("Invalid edge payload")
            if edge.get("subject") not in snapshot.nodes or edge.get("object") not in snapshot.nodes:
                raise GraphValidationError("Edge endpoint does not exist")
            triple = (edge["subject"], edge["predicate"], edge["object"])
            if triple in triples:
                raise GraphValidationError("Duplicate edge triple")
            triples.add(triple)

    @staticmethod
    def _apply(snapshot, mutation):
        entity_id = mutation.target_entity
        if not entity_id or mutation.requires_review:
            raise GraphValidationError("Mutation has no target or requires review")
        exists = entity_id in snapshot.nodes or entity_id in snapshot.edges
        for condition in mutation.preconditions:
            if condition == "target_not_exists" and exists:
                raise GraphValidationError("Target already exists: " + entity_id)
            if condition == "target_exists" and not exists:
                raise GraphValidationError("Target does not exist: " + entity_id)
            if condition not in ("target_not_exists", "target_exists"):
                raise GraphValidationError("Unsupported precondition: " + str(condition))
        operation = mutation.operation
        if operation == MutationOperation.CREATE_NODE:
            if exists:
                raise GraphValidationError("Target already exists: " + entity_id)
            properties = deepcopy(mutation.new_properties)
            snapshot.nodes[entity_id] = {
                "id": entity_id, "mention": properties.pop("mention", entity_id),
                "types": [mutation.new_type] if mutation.new_type else [],
                "properties": properties,
            }
        elif operation == MutationOperation.CREATE_EDGE:
            if exists:
                raise GraphValidationError("Target already exists: " + entity_id)
            snapshot.edges[entity_id] = {
                "id": entity_id, "subject": mutation.subject_id,
                "predicate": mutation.predicate, "object": mutation.object_id,
                "properties": deepcopy(mutation.new_properties),
            }
        elif operation == MutationOperation.ADD_TYPE:
            if entity_id not in snapshot.nodes or not mutation.new_type:
                raise GraphValidationError("Type mutation requires existing node and type")
            if mutation.new_type not in snapshot.nodes[entity_id]["types"]:
                snapshot.nodes[entity_id]["types"].append(mutation.new_type)
        elif operation == MutationOperation.SET_PROPERTY:
            target = snapshot.nodes.get(entity_id, snapshot.edges.get(entity_id))
            if target is None or not mutation.new_properties:
                raise GraphValidationError("Property mutation requires target and values")
            target["properties"].update(deepcopy(mutation.new_properties))
        else:
            raise GraphValidationError("Unsupported mutation operation: " + str(operation))
        for condition in mutation.postconditions:
            if condition == "target_exists":
                if entity_id not in snapshot.nodes and entity_id not in snapshot.edges:
                    raise GraphValidationError("Postcondition target_exists failed")
            else:
                raise GraphValidationError("Unsupported postcondition: " + str(condition))

    def commit(self, mutations, *, expected_version, constraints, provenance,
               fingerprint, idempotency_key=None, committed_by="system",
               certificate=None, dry_run=False, failure_after=None):
        """Verify and publish all operations and provenance, or publish nothing.

        failure_after injects a failure after N applications on the private copy.
        It is an offline fault-injection hook, never a partial public commit.
        """
        with self._lock:
            if not dry_run:
                previous = self.lookup_retry(idempotency_key, fingerprint)
                if previous is not None:
                    return previous
            if self._snapshot.version != expected_version:
                raise VersionConflict("Expected " + str(expected_version) + "; current " + self._snapshot.version)
            shadow = deepcopy(self._snapshot)
            planned = deepcopy(list(mutations))
            entries = deepcopy(provenance)
            cert = deepcopy(certificate or {})
            certified_requests = {r["request_id"]: r for r in cert.get("requests", [])}
            certified_decisions = {d["decision_id"]: d for d in cert.get("decisions", [])}
            if (len(certified_requests) != len(cert.get("requests", []))
                    or len(certified_decisions) != len(cert.get("decisions", []))):
                raise GraphValidationError("Duplicate certified requests or decisions")
            original_candidates = cert.get("candidates", {})
            certified_nodes = {n["candidate_id"]: n for n in original_candidates.get("nodes", [])}
            certified_edges = {e["candidate_id"]: e for e in original_candidates.get("edges", [])}
            allowed_modes = set(cert.get("allowed_execution_modes", ["real"]))
            if not allowed_modes or not allowed_modes.issubset({"real", "mock", "unknown"}):
                raise GraphValidationError("Invalid execution-mode policy")
            identifiers = [m.mutation_id for m in planned]
            if len(set(identifiers)) != len(identifiers):
                raise GraphValidationError("Duplicate mutation IDs")
            if set(identifiers) & set(shadow.provenance):
                raise GraphValidationError("Mutation ID already committed")
            applied = set()
            for index, mutation in enumerate(planned, 1):
                if not set(mutation.dependencies).issubset(applied):
                    raise GraphValidationError("Missing or unordered mutation dependency")
                entry = entries.get(mutation.mutation_id)
                if (entry is None or entry.mutation_id != mutation.mutation_id
                        or entry.entity_id != mutation.target_entity
                        or entry.candidate_id != mutation.candidate_link
                        or set(d.decision_id for d in entry.decisions) != set(mutation.decision_links)):
                    raise GraphValidationError("Incomplete provenance certificate")
                if cert.get("mutation_sha256", {}).get(mutation.mutation_id) != mutation_fingerprint(mutation):
                    raise GraphValidationError("Mutation payload differs from certified plan")
                if any(not set(d.depends_on).issubset(mutation.decision_links) for d in entry.decisions):
                    raise GraphValidationError("Missing decision dependency")
                pending = {d.decision_id: set(d.depends_on) for d in entry.decisions}
                if len(pending) != len(entry.decisions) or len(set(mutation.decision_links)) != len(mutation.decision_links):
                    raise GraphValidationError("Duplicate decision IDs")
                resolved = set()
                while pending:
                    ready = {key for key, dependencies in pending.items() if dependencies <= resolved}
                    if not ready:
                        raise GraphValidationError("Cyclic decision dependencies")
                    resolved.update(ready)
                    pending = {key: value for key, value in pending.items() if key not in ready}
                if not entry.decisions or not entry.evidence:
                    raise GraphValidationError("Mutation requires decisions and evidence")
                source_hashes = cert.get("evidence_sha256", {})
                if ([asdict(e) for e in entry.evidence] != [asdict(e) for e in mutation.evidence_links]
                        or any(source_hashes.get(e.evidence_id) != _fingerprint(asdict(e)) for e in entry.evidence)):
                    raise GraphValidationError("Evidence does not match supplied source snapshot")
                for decision in entry.decisions:
                    distribution = decision.distribution
                    if (decision.state_hash != _fingerprint(decision.request)
                            or decision.request.get("request_id") != decision.decision_id
                            or certified_requests.get(decision.decision_id) != decision.request
                            or _fingerprint(certified_decisions.get(decision.decision_id)) != _fingerprint(asdict(decision))):
                        raise GraphValidationError("Decision does not match its original request")
                    if (not distribution or decision.selected_outcome not in distribution
                            or set(distribution) != set(decision.request.get("labels") or [])
                            or any(type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1
                                   for p in distribution.values())
                            or not math.isclose(sum(distribution.values()), 1, abs_tol=1e-6)
                            or distribution[decision.selected_outcome] != max(distribution.values())
                            or distribution[decision.selected_outcome] < cert.get("confidence_threshold", .85)):
                        raise GraphValidationError("Invalid or insufficient decision probability")
                    if not dry_run and decision.execution_mode not in allowed_modes:
                        raise GraphValidationError("Execution mode not permitted: " + decision.execution_mode)
                risk_budget = cert.get("dependency_risk_budget")
                if risk_budget is not None and sum(1 - d.distribution[d.selected_outcome] for d in entry.decisions) > risk_budget + 1e-12:
                    raise GraphValidationError("Estimated dependency risk exceeds policy budget")
                if mutation.operation == MutationOperation.CREATE_EDGE and not any(
                        d.candidate_id == mutation.candidate_link and d.request.get("task") == "relation_support"
                        and d.selected_outcome == "SUPPORTS" for d in entry.decisions):
                    raise GraphValidationError("Positive edge requires a supported relation decision")
                own_decisions = [d for d in entry.decisions if d.candidate_id == mutation.candidate_link]
                expected_state = "\n".join(e.location.content for e in entry.evidence)
                if not own_decisions or any(d.request.get("state") != expected_state for d in own_decisions):
                    raise GraphValidationError("Candidate decision is not grounded in its evidence")
                if mutation.operation == MutationOperation.CREATE_NODE and not any(
                        (d.request.get("task"), d.selected_outcome) in
                        (("node_existence", "create"), ("entity_resolution_choice", "new")) for d in own_decisions):
                    raise GraphValidationError("Node creation requires a positive entity decision")
                if mutation.operation == MutationOperation.CREATE_EDGE:
                    source = certified_edges.get(mutation.candidate_link)
                    if source is None or mutation.target_entity != source["candidate_id"]:
                        raise GraphValidationError("Edge does not match its source candidate")
                    claim = " ".join(source[key] for key in ("subject_mention", "predicate_mention", "object_mention"))
                    if not any(d.request.get("task") == "relation_support" and d.request.get("payload", {}).get("claim") == claim
                               for d in own_decisions):
                        raise GraphValidationError("Support decision refers to a different claim")
                    predicate_decisions = [d for d in own_decisions if d.request.get("task") == "relation_type"]
                    expected_predicate = predicate_decisions[0].selected_outcome if predicate_decisions else source["predicate_mention"]
                    if mutation.predicate != expected_predicate or (source.get("predicate_candidates") and not predicate_decisions):
                        raise GraphValidationError("Edge predicate differs from selected relation")

                    def resolved_node(candidate_id):
                        identity = [d for d in entry.decisions if d.candidate_id == candidate_id
                                    and d.request.get("task") in ("node_existence", "entity_resolution_choice")]
                        if len(identity) != 1:
                            return None
                        chosen = identity[0].selected_outcome
                        return candidate_id if chosen in ("create", "new") else chosen

                    for role, actual in (("subject", mutation.subject_id), ("object", mutation.object_id)):
                        explicit, mention = source.get(role + "_id"), source[role + "_mention"]
                        if explicit:
                            expected_endpoint = resolved_node(explicit) if explicit in certified_nodes else explicit
                        else:
                            matching = [key for key, node in certified_nodes.items() if node["mention"] == mention]
                            if len(matching) == 1:
                                expected_endpoint = resolved_node(matching[0])
                            elif matching:
                                expected_endpoint = None
                            elif mention in self._snapshot.nodes:
                                expected_endpoint = mention
                            else:
                                matches = [d.selected_outcome for d in own_decisions
                                           if d.request.get("task") == "entity_resolution_choice"
                                           and d.request.get("payload", {}).get("mention") == mention]
                                expected_endpoint = matches[0] if len(matches) == 1 else None
                        if actual != expected_endpoint or expected_endpoint is None:
                            raise GraphValidationError("Edge endpoint differs from resolved candidate")
                if mutation.new_type and not any(d.request.get("task") == "node_type"
                                                and d.selected_outcome == mutation.new_type for d in own_decisions):
                    raise GraphValidationError("Type does not match selected outcome")
                if mutation.operation in (MutationOperation.CREATE_NODE, MutationOperation.SET_PROPERTY):
                    for key, value in mutation.new_properties.items():
                        if key == "mention" and mutation.operation == MutationOperation.CREATE_NODE:
                            continue
                        if not any(d.request.get("task") == "property_value"
                                   and d.request.get("payload", {}).get("property") == key
                                   and d.selected_outcome == value for d in own_decisions):
                            raise GraphValidationError("Property does not match selected outcome")
                self._apply(shadow, mutation)
                applied.add(mutation.mutation_id)
                if failure_after is not None and index >= failure_after:
                    raise GraphValidationError("Injected failure during shadow application")
            self._validate_structure(shadow)
            rule_results = {}
            for constraint in constraints.values():
                status, reason = evaluate_constraint(constraint, shadow)
                constraint.status, constraint.evaluated, constraint.evidence = status, True, reason
                rule_results[constraint.constraint_id] = status.value
            failed = [key for key, status in rule_results.items() if status != "pass"]
            if failed:
                raise GraphValidationError("Constraints did not pass: " + ", ".join(failed))
            will_commit = bool(planned) and not dry_run
            next_version = "v" + str(self._revision + 1) if will_commit else shadow.version
            now = datetime.now(timezone.utc) if will_commit else None
            transaction_id = str(uuid.uuid4())
            cert.update(constraint_results=rule_results, verified_graph_version=expected_version)
            transaction = Transaction(
                transaction_id, shadow.graph_id, shadow.version, next_version,
                mutations=planned, committed_at=now,
                committed_by=committed_by if will_commit else "",
                read_set=set(self._snapshot.nodes) | set(self._snapshot.edges),
                affected_set={m.target_entity for m in planned},
                status="committed" if will_commit else ("dry_run" if dry_run else "no_op"),
                fingerprint=fingerprint, certificate=cert, errors=list(cert.get("decision_errors", [])),
            )
            for mutation in planned:
                mutation.constraint_results = {key: ConstraintStatus(value) for key, value in rule_results.items()}
                mutation.status = MutationStatus.COMMITTED if will_commit else MutationStatus.AUTO_COMMITTABLE
                mutation.committed_at = now
                mutation.committed_by = committed_by if will_commit else None
                mutation.graph_version_at_commit = next_version if will_commit else None
                entry = entries[mutation.mutation_id]
                entry.transaction_id = transaction_id if will_commit else None
                entry.graph_version = next_version
                entry.constraints_checked = deepcopy(list(constraints.values()))
                shadow.provenance[mutation.mutation_id] = entry
            if will_commit:
                shadow.version = next_version
                shadow.transactions[transaction_id] = deepcopy(transaction)
                self._snapshot = shadow
                self._revision += 1
            if not dry_run and idempotency_key is not None:
                self._retries[idempotency_key] = (fingerprint, deepcopy(transaction))
            return transaction
