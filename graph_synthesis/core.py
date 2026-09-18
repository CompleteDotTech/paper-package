"""Small durable graph compiler, with explicit policy and reversible identity views.

This is a research store, not a scalable database or a semantic truth certificate.
Evidence alternatives are separate assertions; evidence/dependencies within one
assertion are conjunctive. Retraction deactivates assertions, never source records.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import sqlite3
from typing import Any, Iterable, Mapping


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def probability(value: Any) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("Expected a finite probability, not a boolean or missing value")
    return float(value)


def distribution(values: Mapping[str, float], labels: Iterable[str]) -> dict[str, float]:
    labels = tuple(labels)
    if not labels or len(set(labels)) != len(labels) or set(values) != set(labels):
        raise ValueError("Probability labels must match the task exactly")
    result = {key: probability(values[key]) for key in labels}
    if not math.isclose(sum(result.values()), 1.0, abs_tol=1e-6, rel_tol=0):
        raise ValueError("Distribution must sum to one; do not silently renormalize failures")
    return result


@dataclass(frozen=True)
class Relation:
    domain: str
    range: str
    symmetric: bool = False
    inverse_of: str | None = None
    incompatible: tuple[str, ...] = ()
    transitive: bool = False
    allow_self: bool = False


@dataclass(frozen=True)
class Policy:
    version: str
    thresholds: Mapping[str, float]
    contracts: Mapping[str, tuple[str, ...]]
    allowed_modes: tuple[str, ...] = ("recorded", "live")

    def __post_init__(self) -> None:
        if not self.version or not self.thresholds:
            raise ValueError("An explicit version and per-predicate thresholds are required")
        if set(self.contracts) != set(self.thresholds):
            raise ValueError("Every predicate needs an outcome contract and threshold")
        for predicate, value in self.thresholds.items():
            probability(value)
            labels = self.contracts[predicate]
            if len(labels) < 2 or len(set(labels)) != len(labels) or any(not isinstance(x, str) or not x for x in labels):
                raise ValueError("Contracts list the accepted label first, then alternative labels")
        if not self.allowed_modes or set(self.allowed_modes) - {"recorded", "live", "synthetic"}:
            raise ValueError("Execution modes must be explicit")


def evidence(source: str, version: str, text: str, *, origin: str | None = None,
             start: int = 0, end: int | None = None) -> dict[str, Any]:
    end = len(text) if end is None else end
    if not source or not version or not isinstance(text, str) or not text:
        raise ValueError("Source identity, version, and nonempty text are required")
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
        raise ValueError("Evidence offsets must identify a nonempty exact source span")
    item = {"source": source, "version": version, "origin": origin or source,
            "text": text, "start": start, "end": end, "span": text[start:end]}
    return {"id": digest(item), **item}


def candidate(fact_id: str, subject: str, predicate: str, object_: str,
              evidence_ids: Iterable[str], *, depends_on: Iterable[str] = (),
              qualifiers: Mapping[str, str] | None = None) -> dict[str, Any]:
    return {"id": fact_id, "subject": subject, "predicate": predicate, "object": object_,
            "evidence": sorted(set(evidence_ids)), "depends_on": sorted(set(depends_on)),
            "qualifiers": dict(qualifiers or {})}


def bind(item: Mapping[str, Any], probabilities: Mapping[str, float], selected: str,
         *, model: str, mode: str, request_hash: str, policy_version: str,
         labels: Iterable[str] | None = None) -> dict[str, Any]:
    """Bind a supplied decision to exact action bytes; this does not authenticate truth."""
    result = deepcopy(dict(item))
    values = distribution(probabilities, tuple(labels or probabilities))
    if selected not in values or values[selected] != max(values.values()):
        raise ValueError("Selected label must be a maximal-probability task label")
    result["decision"] = {"candidate_hash": digest(item), "distribution": values,
                          "selected": selected, "model": model, "mode": mode,
                          "request_hash": request_hash, "policy_version": policy_version}
    return result


def _schema(relations: Mapping[str, Relation | Mapping[str, Any]]) -> dict[str, Any]:
    if not relations:
        raise ValueError("Empty relation schema")
    schema = {key: asdict(value) if isinstance(value, Relation) else dict(value)
              for key, value in relations.items()}
    # Convert tuples to lists, matching the representation loaded from SQLite.
    schema = json.loads(canonical(schema))
    fields = set(asdict(Relation("a", "b")))
    for key, spec in schema.items():
        if not isinstance(key, str) or not key or set(spec) != fields:
            raise ValueError("Unknown or incomplete relation schema")
        if not all(isinstance(spec[x], str) and spec[x] for x in ("domain", "range")):
            raise ValueError("Domain and range must be named types")
        if any(type(spec[x]) is not bool for x in ("symmetric", "transitive", "allow_self")):
            raise ValueError("Relation flags must be boolean")
        inverse = spec["inverse_of"]
        if inverse is not None:
            if inverse not in schema or schema[inverse]["inverse_of"] is not None or spec["symmetric"]:
                raise ValueError("Inverse must reference a canonical, nonsymmetric relation")
            target = schema[inverse]
            if (spec["domain"], spec["range"]) != (target["range"], target["domain"]):
                raise ValueError("Inverse domain/range mismatch")
        if not isinstance(spec["incompatible"], list):
            raise ValueError("Incompatible predicates must be a list")
        if spec["symmetric"] and spec["domain"] != spec["range"]:
            raise ValueError("A symmetric predicate requires identical endpoint types")
        if any(other not in schema for other in spec["incompatible"]):
            raise ValueError("Unknown incompatible predicate")
    return schema


def normalize(item: Mapping[str, Any], schema: Mapping[str, Any]) -> tuple[str, str, str]:
    s, p, o = item["subject"], item["predicate"], item["object"]
    if p not in schema:
        raise ValueError("Unknown predicate: " + p)
    if schema[p]["inverse_of"]:
        s, p, o = o, schema[p]["inverse_of"], s
    if schema[p]["symmetric"] and s > o:
        s, o = o, s
    return s, p, o


def components(nodes: Iterable[str], pairs: Iterable[tuple[str, str]]) -> dict[str, str]:
    parent = {node: node for node in nodes}

    def root(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for left, right in pairs:
        if left not in parent or right not in parent:
            raise ValueError("Unknown identity endpoint")
        a, b = root(left), root(right)
        parent[max(a, b)] = min(a, b)
    return {node: root(node) for node in parent}


def _clusters(state: Mapping[str, Any]) -> dict[str, str]:
    active = [x for x in state["facts"].values() if x["active"]]
    pairs = [(x["subject"], x["object"]) for x in active if x["predicate"] == "same_as"]
    result = components(state["nodes"], pairs)
    for a, b in pairs:
        if state["nodes"][a] != state["nodes"][b]:
            raise ValueError("Identity cannot merge incompatible node types")
    for item in active:
        if item["predicate"] == "different_from" and result[item["subject"]] == result[item["object"]]:
            raise ValueError("Identity transitivity conflicts with a cannot-link")
    return result


def _validate(state: Mapping[str, Any]) -> None:
    active = {key: value for key, value in state["facts"].items() if value["active"]}
    for item in active.values():
        if not item["evidence"] or any(key not in state["evidence"] or key in state["withdrawn"]
                                      for key in item["evidence"]):
            raise ValueError("Missing or withdrawn evidence")
        if any(key not in active for key in item["depends_on"]):
            raise ValueError("Missing or inactive prerequisite")
    pending = {key: set(value["depends_on"]) for key, value in active.items()}
    done: set[str] = set()
    while pending:
        ready = {key for key, deps in pending.items() if deps <= done}
        if not ready:
            raise ValueError("Cyclic assertion dependency")
        done.update(ready)
        pending = {key: deps for key, deps in pending.items() if key not in ready}
    identities = _clusters(state)
    seen: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for item in active.values():
        s, p, o = normalize(item, state["schema"])
        spec = state["schema"][p]
        if s not in state["nodes"] or o not in state["nodes"]:
            raise ValueError("Missing relationship endpoint")
        for node, expected in ((s, spec["domain"]), (o, spec["range"])):
            if expected != "*" and state["nodes"][node] != expected:
                raise ValueError("Relationship domain/range violation")
        # Identity is a reversible view; original assertions are never rewired.
        if p not in {"same_as", "different_from"}:
            s, o = identities[s], identities[o]
            if spec["symmetric"] and s > o:
                s, o = o, s
        if s == o and not spec["allow_self"]:
            raise ValueError("Self relationship forbidden by schema")
        scope = canonical(item["qualifiers"])
        key = (s, o, scope)
        previous = seen[key]
        if any(other in spec["incompatible"] or p in state["schema"][other]["incompatible"]
               for other in previous):
            raise ValueError("Incompatible relationships within identical qualifiers")
        previous.add(p)


class GraphStore:
    """SQLite transaction + append-only audit history; callers own authorization.

    Each revision stores a complete JSON state. This intentionally trades scale
    for inspectability. sqlite3 BEGIN IMMEDIATE serializes concurrent writers.
    """
    def __init__(self, path: str, relations: Mapping[str, Relation], policy: Policy):
        self.policy = deepcopy(policy)
        self.db = sqlite3.connect(path, isolation_level=None, timeout=10)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS journal (version INTEGER PRIMARY KEY, key TEXT UNIQUE NOT NULL, fingerprint TEXT NOT NULL, event TEXT NOT NULL, previous TEXT NOT NULL, hash TEXT NOT NULL)")
        initial = {"version": 0, "schema": _schema(relations), "schema_version": "initial",
                   "nodes": {}, "evidence": {}, "withdrawn": [], "facts": {}}
        self.db.execute("INSERT OR IGNORE INTO state VALUES (1,?)", (canonical(initial),))
        if self.snapshot()["schema"] != initial["schema"]:
            self.db.close()
            raise ValueError("Reopen with the current schema; schema changes require migrate()")

    def close(self) -> None:
        self.db.close()

    def snapshot(self) -> dict[str, Any]:
        return json.loads(self.db.execute("SELECT body FROM state WHERE id=1").fetchone()[0])

    def _transaction(self, operation: Mapping[str, Any], expected_version: int, key: str,
                     *, fail_before_publish: bool = False) -> dict[str, Any]:
        if type(expected_version) is not int or expected_version < 0 or not isinstance(key, str) or not key:
            raise ValueError("Explicit nonnegative version and idempotency key required")
        payload = {"operation": operation, "expected_version": expected_version,
                   "policy": asdict(self.policy)}
        fingerprint = digest(payload)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            previous = self.db.execute("SELECT fingerprint,event FROM journal WHERE key=?", (key,)).fetchone()
            if previous:
                if previous[0] != fingerprint:
                    raise ValueError("Idempotency key reused for different input or policy")
                self.db.execute("ROLLBACK")
                return json.loads(previous[1])
            state = self.snapshot()
            if state["version"] != expected_version:
                raise ValueError("Stale graph version")
            before = digest(state)
            kind = operation["kind"]
            if kind == "commit":
                for node, type_ in operation["nodes"].items():
                    if not isinstance(node, str) or not node or not isinstance(type_, str) or not type_:
                        raise ValueError("Named node and type required")
                    if node in state["nodes"] and state["nodes"][node] != type_:
                        raise ValueError("Node type changes require explicit migration")
                    state["nodes"][node] = type_
                for item in operation["evidence"]:
                    value = dict(item)
                    id_ = value.pop("id")
                    if id_ != digest(value) or evidence(value["source"], value["version"], value["text"],
                            origin=value["origin"], start=value["start"], end=value["end"]) != item:
                        raise ValueError("Evidence snapshot or span was changed")
                    state["evidence"][id_] = item
                for original in operation["facts"]:
                    item = deepcopy(original)
                    decision = item.pop("decision")
                    if set(item) != {"id", "subject", "predicate", "object", "evidence", "depends_on", "qualifiers"}:
                        raise ValueError("Unknown assertion fields")
                    if any(not isinstance(item[x], str) or not item[x] for x in ("id", "subject", "predicate", "object")):
                        raise ValueError("Assertion identities and endpoints must be named")
                    if item["id"] in state["facts"]:
                        raise ValueError("Assertion identifiers are immutable, including retracted assertions")
                    if not isinstance(item["qualifiers"], dict) or any(not isinstance(k, str) or not isinstance(v, str)
                                                                     for k, v in item["qualifiers"].items()):
                        raise ValueError("Qualifiers must be explicit string pairs")
                    if decision["candidate_hash"] != digest(item):
                        raise ValueError("Decision is not bound to this exact assertion")
                    contract = self.policy.contracts.get(item["predicate"])
                    if contract is None:
                        raise ValueError("No decision contract for predicate")
                    values = distribution(decision["distribution"], contract)
                    selected = decision["selected"]
                    if selected != contract[0]:
                        raise ValueError("Decision polarity does not authorize this relation")
                    if selected not in values or values[selected] != max(values.values()):
                        raise ValueError("Decision label mismatch")
                    if not decision["model"] or not decision["request_hash"] or decision["mode"] not in self.policy.allowed_modes:
                        raise ValueError("Missing decision provenance or prohibited execution mode")
                    if decision["policy_version"] != self.policy.version:
                        raise ValueError("Stale decision policy")
                    threshold = self.policy.thresholds.get(item["predicate"])
                    if threshold is None or values[selected] < threshold:
                        raise ValueError("No acceptance policy or insufficient probability")
                    item.update(decision=decision, active=True, retracted_because=None)
                    state["facts"][item["id"]] = item
            elif kind == "retract":
                roots = set(operation["facts"])
                removed_evidence = set(operation["evidence"])
                if not roots <= state["facts"].keys() or not removed_evidence <= state["evidence"].keys():
                    raise ValueError("Cannot retract unknown facts or evidence")
                state["withdrawn"] = sorted(set(state["withdrawn"]) | removed_evidence)
                roots.update(key for key, value in state["facts"].items() if removed_evidence & set(value["evidence"]))
                while True:
                    expanded = roots | {key for key, value in state["facts"].items() if roots & set(value["depends_on"])}
                    if expanded == roots:
                        break
                    roots = expanded
                for id_ in roots:
                    state["facts"][id_].update(active=False, retracted_because=operation["reason"])
            elif kind == "migrate":
                state["schema"] = _schema(operation["schema"])
                state["schema_version"] = operation["schema_version"]
            else:
                raise ValueError("Unknown graph operation")
            _validate(state)
            state["version"] += 1
            event = {"version": state["version"], "before": before, "after": digest(state),
                     "operation": operation, "policy": asdict(self.policy)}
            previous_hash = self.db.execute("SELECT hash FROM journal ORDER BY version DESC LIMIT 1").fetchone()
            previous_hash = previous_hash[0] if previous_hash else "GENESIS"
            event_hash = digest({"previous": previous_hash, "event": event, "fingerprint": fingerprint})
            if fail_before_publish:
                raise RuntimeError("Injected failure before publication")
            self.db.execute("UPDATE state SET body=? WHERE id=1", (canonical(state),))
            self.db.execute("INSERT INTO journal VALUES (?,?,?,?,?,?)",
                            (state["version"], key, fingerprint, canonical(event), previous_hash, event_hash))
            self.db.execute("COMMIT")
            return json.loads(canonical(event))
        except BaseException:
            if self.db.in_transaction:
                self.db.execute("ROLLBACK")
            raise

    def commit(self, *, nodes: Mapping[str, str], sources: Iterable[Mapping[str, Any]],
               facts: Iterable[Mapping[str, Any]], expected_version: int, key: str,
               fail_before_publish: bool = False) -> dict[str, Any]:
        operation = {"kind": "commit", "nodes": dict(nodes), "evidence": list(sources), "facts": list(facts)}
        return self._transaction(operation, expected_version, key, fail_before_publish=fail_before_publish)

    def retract(self, *, fact_ids: Iterable[str] = (), evidence_ids: Iterable[str] = (),
                expected_version: int, key: str, reason: str) -> dict[str, Any]:
        if not reason:
            raise ValueError("An auditable retraction reason is required")
        return self._transaction({"kind": "retract", "facts": sorted(set(fact_ids)),
                                  "evidence": sorted(set(evidence_ids)), "reason": reason}, expected_version, key)

    def migrate(self, relations: Mapping[str, Relation], *, schema_version: str,
                reviewed_by: str, reason: str, expected_version: int, key: str) -> dict[str, Any]:
        if not reviewed_by or not reason or not schema_version:
            raise ValueError("Schema migration requires an explicit reviewer, reason, and version")
        return self._transaction({"kind": "migrate", "schema": _schema(relations), "schema_version": schema_version,
                                  "reviewed_by": reviewed_by, "reason": reason}, expected_version, key)

    def audit(self) -> dict[str, Any]:
        previous, last_after, count = "GENESIS", None, 0
        for version, fingerprint, body, previous_hash, event_hash in self.db.execute(
                "SELECT version,fingerprint,event,previous,hash FROM journal ORDER BY version"):
            event = json.loads(body)
            if version != count + 1 or event["version"] != version or previous_hash != previous:
                raise ValueError("Broken audit chain")
            if event_hash != digest({"previous": previous, "event": event, "fingerprint": fingerprint}):
                raise ValueError("Altered audit event")
            if last_after is not None and event["before"] != last_after:
                raise ValueError("Discontinuous graph history")
            previous, last_after, count = event_hash, event["after"], count + 1
        state = self.snapshot()
        if not count and any(state[x] for x in ("nodes", "evidence", "withdrawn", "facts")):
            raise ValueError("Nonempty state without a journal")
        if state["version"] != count or (count and digest(state) != last_after):
            raise ValueError("State differs from journal")
        return {"events": count, "head_hash": previous, "state_hash": digest(state)}

    def view(self) -> dict[str, Any]:
        state = self.snapshot()
        identities = _clusters(state)
        grouped: dict[tuple[str, str, str, str], list[str]] = defaultdict(list)
        for id_, item in state["facts"].items():
            if item["active"]:
                s, p, o = normalize(item, state["schema"])
                if p not in {"same_as", "different_from"}:
                    s, o = identities[s], identities[o]
                    if state["schema"][p]["symmetric"] and s > o:
                        s, o = o, s
                grouped[s, p, o, canonical(item["qualifiers"])].append(id_)
        return {"version": state["version"], "identities": identities,
                "edges": [{"subject": s, "predicate": p, "object": o,
                           "qualifiers": json.loads(q), "assertions": sorted(ids)}
                          for (s, p, o, q), ids in sorted(grouped.items())]}


def select_identity(scores: Mapping[str, float], *, threshold: float, margin: float,
                    new_entity_supported: bool = False) -> str:
    """Pairwise scores are not a mutually exclusive Choice distribution."""
    probability(threshold)
    probability(margin)
    if any(key in {"new", "defer"} or not key for key in scores):
        raise ValueError("Reserved or empty entity identifier")
    ordered = sorted(((probability(value), key) for key, value in scores.items()), reverse=True)
    if not ordered:
        return "new" if new_entity_supported else "defer"
    top, identity = ordered[0]
    second = ordered[1][0] if len(ordered) > 1 else 0.0
    if top >= threshold and (len(ordered) == 1 or (top > second and top - second >= margin)):
        return identity
    return "defer"  # Missing or low-score candidates do not establish a new identity.


def graph_metrics(nodes: Iterable[str], edges: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Typed edge counts and weak components; density is structural, not correctness."""
    nodes = set(nodes)
    edges = list(edges)
    pairs = {(x["subject"], x["object"]) for x in edges}
    roots = components(nodes, pairs)
    indegree, outdegree = Counter(o for _, o in pairs), Counter(s for s, _ in pairs)
    sizes = Counter(roots.values())
    pair_labels = defaultdict(set)
    for edge in edges:
        pair_labels[edge["subject"], edge["object"]].add(edge["predicate"])
    return {"nodes": len(nodes), "typed_edges": len(edges), "distinct_directed_pairs": len(pairs),
            "relation_counts": dict(sorted(Counter(x["predicate"] for x in edges).items())),
            "multi_label_directed_pairs": sum(len(v) > 1 for v in pair_labels.values()),
            "self_relationship_pairs": sum(s == o for s, o in pairs),
            "reciprocal_pair_sets": sum(s < o and (o, s) in pairs for s, o in pairs),
            "weak_component_size_histogram": dict(sorted(Counter(map(str, sizes.values())).items())),
            "weak_components": len(sizes), "largest_component": max(sizes.values(), default=0),
            "isolates": sum(indegree[n] + outdegree[n] == 0 for n in nodes),
            "max_in_degree": max(indegree.values(), default=0), "max_out_degree": max(outdegree.values(), default=0),
            "directed_pair_density": len({(s, o) for s, o in pairs if s != o}) / (len(nodes) * (len(nodes)-1)) if len(nodes) > 1 else 0.0}
