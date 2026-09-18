"""Constructed limitation witnesses and repair-oracle tests, never Jev predictions."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import random
import tempfile

from .core import GraphStore, Policy, Relation, bind, candidate, digest, evidence

SCHEMA = {"supports": Relation("Document", "Claim", incompatible=("refutes",)),
          "refutes": Relation("Document", "Claim", incompatible=("supports",)),
          "same_as": Relation("Record", "Record", symmetric=True, transitive=True)}
CONTRACTS = {"supports": ("yes", "no"), "refutes": ("yes", "no"), "same_as": ("yes", "no")}
POLICY = Policy("synthetic-witness-v1", {p: 1.0 for p in SCHEMA}, CONTRACTS, ("synthetic",))


def make_fact(id_, subject, predicate, object_, sources, *, deps=(), qualifiers=None):
    item = candidate(id_, subject, predicate, object_, sources, depends_on=deps, qualifiers=qualifiers)
    return bind(item, {"yes": 1.0, "no": 0.0}, "yes", model="constructed-not-Jev",
                mode="synthetic", request_hash=digest(["constructed-witness", item]),
                policy_version=POLICY.version, labels=CONTRACTS[predicate])


def semantic_witnesses() -> dict:
    ev = evidence("document", "v1", "The claim is explicitly false. This is a synthetic source.")
    store = GraphStore(":memory:", SCHEMA, POLICY)
    try:
        f = make_fact("false", "d", "supports", "c", [ev["id"]])
        store.commit(nodes={"d": "Document", "c": "Claim"}, sources=[ev], facts=[f], expected_version=0, key="false")
        false_accepted = len(store.view()["edges"])
    finally:
        store.close()
    store = GraphStore(":memory:", SCHEMA, POLICY)
    try:
        facts = [make_fact("a", "d", "supports", "c", [ev["id"]],
                           qualifiers={"valid_from": "2020-01-01", "valid_to": "2025-01-01"}),
                 make_fact("b", "d", "refutes", "c", [ev["id"]],
                           qualifiers={"valid_from": "2024-01-01", "valid_to": "2026-01-01"})]
        store.commit(nodes={"d": "Document", "c": "Claim"}, sources=[ev], facts=facts, expected_version=0, key="overlap")
        temporal_accepted = len(store.view()["edges"])
    finally:
        store.close()
    store = GraphStore(":memory:", SCHEMA, POLICY)
    try:
        invalid = make_fact("bad-type", "d", "supports", "c", [ev["id"]])
        rejected = False
        try:
            store.commit(nodes={"d": "Claim", "c": "Document"}, sources=[ev], facts=[invalid], expected_version=0, key="type")
        except ValueError:
            rejected = store.snapshot()["version"] == 0
    finally:
        store.close()
    return {"valid_but_false_assertions_accepted": false_accepted,
            "overlapping_temporal_opposites_accepted": temporal_accepted,
            "schema_invalid_assertion_rejected_atomically": rejected,
            "status": "limitation_witnesses_not_semantic_model_results",
            "temporal_scope": "Exact qualifier equality is enforced; interval overlap is not interpreted."}


def copied_source_witness(copies: int = 10) -> dict:
    if type(copies) is not int or copies < 1:
        raise ValueError("Positive copy count required")
    sources = [evidence(f"copy-{i}", "v1", "Identical synthetic source text.", origin="one-origin") for i in range(copies)]
    facts = [make_fact(f"f{i}", "d", "supports", "c", [ev["id"]]) for i, ev in enumerate(sources)]
    store = GraphStore(":memory:", SCHEMA, POLICY)
    try:
        store.commit(nodes={"d": "Document", "c": "Claim"}, sources=sources, facts=facts, expected_version=0, key="copies")
        initial_edges = len(store.view()["edges"])
        store.retract(evidence_ids=[sources[0]["id"]], expected_version=1, key="one-copy", reason="withdraw one content record, not all origins")
        residual = sum(f["active"] for f in store.snapshot()["facts"].values())
        store.retract(evidence_ids=[e["id"] for e in sources], expected_version=2, key="all-copies", reason="explicit origin-wide policy supplies every evidence ID")
        return {"source_records": copies, "unique_origins": 1, "initial_derived_edges": initial_edges,
                "residual_assertions_after_one_copy_withdrawal": residual,
                "active_after_explicit_origin_wide_withdrawal": sum(f["active"] for f in store.snapshot()["facts"].values()),
                "status": "source_records_are_not_independent_corroborations"}
    finally:
        store.close()


def identity_bridge(size: int) -> dict:
    if type(size) is not int or size < 2:
        raise ValueError("Cluster size must be at least two")
    ev = evidence("synthetic-identities", "v1", "Two distinct real-world identities, each with multiple records.")
    clusters = [[f"{name}{i:04}" for i in range(size)] for name in ("a", "b")]
    nodes = {node: "Record" for cluster in clusters for node in cluster}
    facts = [make_fact(f"{c[0]}-{i}", c[i-1], "same_as", c[i], [ev["id"]])
             for c in clusters for i in range(1, size)]
    facts.append(make_fact("wrong-bridge", clusters[0][0], "same_as", clusters[1][0], [ev["id"]]))
    store = GraphStore(":memory:", SCHEMA, POLICY)
    try:
        store.commit(nodes=nodes, sources=[ev], facts=facts, expected_version=0, key="bridge")
        identities = store.view()["identities"]
        false_pairs = sum(identities[a] == identities[b] for a in clusters[0] for b in clusters[1])
        store.retract(fact_ids=["wrong-bridge"], expected_version=1, key="repair", reason="synthetic adjudication rejects the bridge")
        repaired = store.view()["identities"]
        return {"records_per_true_cluster": size, "injected_wrong_edges": 1,
                "false_cross_identity_pairs_before_repair": false_pairs,
                "false_cross_identity_pairs_after_repair": sum(repaired[a] == repaired[b] for a in clusters[0] for b in clusters[1]),
                "identity_components_after_repair": len(set(repaired.values()))}
    finally:
        store.close()


def descendants(dependencies: dict[str, set[str]], roots: set[str]) -> set[str]:
    """Independent adjacency/BFS oracle, not the runtime's fixed-point algorithm."""
    outgoing = {key: [] for key in dependencies}
    for child, parents in dependencies.items():
        for parent in parents:
            outgoing[parent].append(child)
    removed, queue = set(roots), list(roots)
    while queue:
        for child in outgoing[queue.pop()]:
            if child not in removed:
                removed.add(child)
                queue.append(child)
    return removed


def repair_episode(seed: int, size: int = 80) -> dict:
    if type(size) is not int or size < 2:
        raise ValueError("At least two assertions required")
    rng = random.Random(seed)
    ids = [f"f{i:04}" for i in range(size)]
    deps = {key: set(rng.sample(ids[:i], min(i, rng.randrange(4)))) for i, key in enumerate(ids)}
    sources = [evidence(key, "v1", "Synthetic evidence for " + key) for key in ids]
    facts = [make_fact(key, "d", "supports", "c" + key, [ev["id"]], deps=deps[key]) for key, ev in zip(ids, sources)]
    roots = set(rng.sample(ids, max(1, size // 10)))
    expected = descendants(deps, roots)
    rng.shuffle(facts)
    nodes = {"d": "Document", **{"c" + key: "Claim" for key in ids}}
    with tempfile.TemporaryDirectory() as directory:
        path = str(Path(directory) / "stress.sqlite")
        store = GraphStore(path, SCHEMA, POLICY)
        try:
            operation = dict(nodes=nodes, sources=sources, facts=facts, expected_version=0, key="load")
            before = store.snapshot()
            try:
                store.commit(**operation, fail_before_publish=True)
            except RuntimeError:
                pass
            else:
                raise AssertionError("Fault injection did not fire")
            assert store.snapshot() == before
            event = store.commit(**operation)
            assert store.commit(**operation) == event
            store.retract(fact_ids=sorted(roots), expected_version=1, key="withdraw", reason="seeded dependency fault")
            state = store.snapshot()
            actual = {key for key, f in state["facts"].items() if not f["active"]}
            assert actual == expected, (seed, actual, expected)
            assert len(state["facts"]) == size
            store.audit()
        finally:
            store.close()
        store = GraphStore(path, SCHEMA, POLICY)
        try:
            assert store.snapshot() == state
            store.audit()
        finally:
            store.close()
    return {"seed": seed, "assertions": size, "withdrawn_roots": len(roots),
            "oracle_retractions": len(expected), "actual_retractions": len(actual),
            "atomic_fault_rollback": True, "retry_idempotent": True, "durable_reopen": True}


def run_mechanisms() -> dict:
    episodes = [repair_episode(seed) for seed in range(20)]
    return {"classification": "constructed_synthetic_mechanisms_not_Jev_calls",
            "semantics": semantic_witnesses(), "copied_sources": copied_source_witness(),
            "identity_bridges": [identity_bridge(n) for n in (2, 10, 100)],
            "repair": {"episodes": len(episodes), "total_assertions": sum(x["assertions"] for x in episodes),
                       "total_retractions": sum(x["actual_retractions"] for x in episodes),
                       "all_oracles_matched": True, "episode_digest": digest(episodes)}}
