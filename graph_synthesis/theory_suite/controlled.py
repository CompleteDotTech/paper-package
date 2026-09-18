"""T07--T10: explicitly simulated scores and controlled GraphStore invariants."""
from __future__ import annotations
from itertools import combinations, product
import random

from graph_synthesis.core import GraphStore, Policy, Relation, bind, candidate, digest, evidence
from graph_synthesis.recorded import BASELINES
from .analyses import FEW, SEED
from .methods import joint_decode, migration_preview, partition_objective, semantic_key


def t07(data: dict) -> dict:
    pairs = list(combinations(range(6), 2))
    output = {}
    patterns = ((0, 0, 1, 1, 2, 2), (0, 0, 0, 1, 1, 2), (0, 0, 0, 0, 1, 2), (0, 0, 0, 0, 0, 0))
    for arm in (BASELINES["entity_resolution"], FEW):
        rows = data["entity_resolution"][arm]["calibration"]
        pools = {label: [r["probabilities"]["same"] for r in rows if r["gold"] == label and not r["error"]]
                 for label in ("same", "different")}
        if not all(pools.values()):
            output[arm] = {"status": "missing_conditional_pool", "target_met": False}
            continue
        rng = random.Random(SEED)
        counts = {"exact": {"false_merges": 0, "missed_matches": 0}, "greedy": {"false_merges": 0, "missed_matches": 0}}
        improvements, order_changes, rows_out = 0, 0, []
        for world in range(256):
            truth = list(patterns[world % len(patterns)])
            rng.shuffle(truth)
            probs = {pair: rng.choice(pools["same" if truth[pair[0]] == truth[pair[1]] else "different"])
                     for pair in pairs}
            exact = joint_decode(6, probs)
            greedy = joint_decode(6, probs, greedy_order=pairs)
            gain = partition_objective(exact, probs) - partition_objective(greedy, probs)
            if gain < -1e-9:
                raise AssertionError("Exact decoder lost to a feasible partition")
            improvements += gain > 1e-9
            order = pairs[:]
            rng.shuffle(order)
            order_changes += joint_decode(6, probs, greedy_order=order) != greedy
            result = {"world": world, "objective_gain": round(gain, 8)}
            for name, partition in (("exact", exact), ("greedy", greedy)):
                fm = sum(partition[i] == partition[j] and truth[i] != truth[j] for i, j in pairs)
                mm = sum(partition[i] != partition[j] and truth[i] == truth[j] for i, j in pairs)
                counts[name]["false_merges"] += fm
                counts[name]["missed_matches"] += mm
                result[name] = {"false_merges": fm, "missed_matches": mm}
            rows_out.append(result)
        a, b = counts["exact"], counts["greedy"]
        output[arm] = {"worlds": 256, "nodes_per_world": 6, "pairs_per_world": 15,
                       "calibration_pool_sizes": {k: len(v) for k, v in pools.items()}, **counts,
                       "strict_objective_improvement_worlds": improvements, "greedy_order_sensitive_worlds": order_changes,
                       "world_result_digest": digest(rows_out),
                       "target_met": a["false_merges"] < b["false_merges"] and a["missed_matches"] <= b["missed_matches"]}
    return {"evidence_kind": "conditional_score_resampling_simulation", "arms": output,
            "assumptions": "Synthetic six-node truths; independent conditional pair-score draws from purged calibration. Not Jev predictions on synthetic texts or a scalable solver."}


def t08() -> dict:
    rng = random.Random(SEED)
    decisions = [{"id": i, "sources": sorted(rng.sample(range(1000), 3)), "bucket": i % 25} for i in range(500)]
    sources, buckets = [0] * 1000, [0] * 25
    versions = {"model": "m0", "schema": "s0", "policy": "p0"}
    names = ("input_only", "missing_absent_query_generation", "global_generation", "complete_dependencies")
    caches = {name: {} for name in names}
    counts = {name: {"hits": 0, "stale_hits": 0, "recomputations": 0} for name in names}
    trace = []
    for epoch in range(101):
        if epoch:
            if epoch in (25, 50, 75):
                key = {25: "model", 50: "schema", 75: "policy"}[epoch]
                versions[key] += ":changed"
                event = "global_" + key
            elif epoch % 4 == 0:
                bucket = rng.randrange(25)
                buckets[bucket] += 1
                event = "new_fact_in_previously_queried_bucket"
            else:
                source = rng.randrange(1000)
                sources[source] += 1
                event = "source_revision"
        else:
            event = "initial"
        trace.append(event)
        for decision in decisions:
            deps = {"source:" + str(i): sources[i] for i in decision["sources"]}
            complete = {**deps, "query_bucket:" + str(decision["bucket"]): buckets[decision["bucket"]]}
            common = {"state": {"candidate": decision["id"]}, "question": "fixed-choice-question", **versions}
            oracle = semantic_key(**common, dependencies=complete)
            keys = {"input_only": digest(common["state"]),
                    "missing_absent_query_generation": semantic_key(**common, dependencies=deps),
                    "global_generation": digest({"candidate": decision["id"], "epoch": epoch}),
                    "complete_dependencies": oracle}
            for name, key in keys.items():
                if key in caches[name]:
                    counts[name]["hits"] += 1
                    counts[name]["stale_hits"] += caches[name][key] != oracle
                else:
                    counts[name]["recomputations"] += 1
                    caches[name][key] = oracle
    target = counts["complete_dependencies"]["stale_hits"] == 0 and counts["complete_dependencies"]["hits"] > counts["global_generation"]["hits"]
    return {"evidence_kind": "context_digest_cache_simulation", "decisions": 500, "epochs_including_initial": 101,
            "requests": 50500, "strategies": counts, "event_counts": {k: trace.count(k) for k in sorted(set(trace))},
            "target_met": target, "limitation": "Complete fingerprint equals the specified oracle by construction. Correct dependency discovery and actual Jev output reuse remain untested."}


def fixture_fact(id_, predicate, sources, policy, *, deps=(), subject="a", object_="b"):
    item = candidate(id_, subject, predicate, object_, [ev["id"] for ev in sources], depends_on=deps)
    return bind(item, {"yes": 1.0, "no": 0.0}, "yes", model="controlled-fixture-not-Jev", mode="synthetic",
                request_hash=digest({"fixture": id_}), policy_version=policy.version)


def synthetic_policy(relations):
    return Policy("theory-fixture-v1", {p: 0 for p in relations}, {p: ("yes", "no") for p in relations}, ("synthetic",))


def t09() -> dict:
    relations = {p: Relation("Node", "Node") for p in ("P", "Q")}
    policy = synthetic_policy(relations)
    sources = [evidence("source:" + str(i), "v1", "Controlled source " + str(i)) for i in range(4)]
    totals = {name: {"false_removals": 0, "false_retention": 0} for name in ("alternative_proofs", "flattened_AND", "flattened_OR")}
    cases = []
    for mask in range(16):
        alive = [not bool(mask & (1 << i)) for i in range(4)]
        expected = ((alive[0] and alive[1]) or alive[2]) and alive[3]
        store = GraphStore(":memory:", relations, policy)
        try:
            facts = [fixture_fact("pa", "P", sources[:2], policy), fixture_fact("pb", "P", [sources[2]], policy),
                     fixture_fact("qa", "Q", [sources[3]], policy, deps=("pa",)),
                     fixture_fact("qb", "Q", [sources[3]], policy, deps=("pb",))]
            store.commit(nodes={"a": "Node", "b": "Node"}, sources=sources, facts=facts, expected_version=0, key="create")
            withdrawn = [sources[i]["id"] for i in range(4) if not alive[i]]
            store.retract(evidence_ids=withdrawn, expected_version=1, key="withdraw", reason="controlled exhaustive subset")
            actual = any(e["predicate"] == "Q" for e in store.view()["edges"])
            store.audit()
            # Boolean controls deliberately flatten the same four-source expression.
            observed = {"alternative_proofs": actual, "flattened_AND": all(alive), "flattened_OR": any(alive)}
            for name, result in observed.items():
                totals[name]["false_removals"] += expected and not result
                totals[name]["false_retention"] += result and not expected
            cases.append({"withdrawal_mask": mask, "expected_Q": expected, **observed})
        finally:
            store.close()
    return {"evidence_kind": "actual_GraphStore_synthetic_invariant", "cases": cases, "strategies": totals,
            "target_met": not any(totals["alternative_proofs"].values()),
            "limitation": "The sufficient-proof clauses are supplied by the fixture; their extraction from scientific text is not tested."}


def t10() -> dict:
    original = {"links": Relation("Node", "Node"), "backlinks": Relation("Node", "Node")}
    policy = synthetic_policy(original)
    changes = {
        "add_unused": {**original, "unused": Relation("Node", "Node")},
        "allow_self_no_observed_self_edges": {**original, "links": Relation("Node", "Node", allow_self=True)},
        "make_symmetric": {**original, "links": Relation("Node", "Node", symmetric=True)},
        "introduce_inverse": {**original, "backlinks": Relation("Node", "Node", inverse_of="links")},
    }
    cases = []
    for orientation in (0, 1):
        store = GraphStore(":memory:", original, policy)
        source = evidence("schema-source", "v1", "Synthetic migration context")
        try:
            s, o = ("a", "b") if not orientation else ("b", "a")
            store.commit(nodes={n: "Node" for n in "abc"}, sources=[source],
                         facts=[fixture_fact("f", "links", [source], policy, subject=s, object_=o)],
                         expected_version=0, key="create")
            before = store.snapshot()
            queries = [(s, p, o) for p in original for s, o in product("abc", repeat=2)]
            for name, relations in changes.items():
                result = migration_preview(store, relations, queries)
                cases.append({"orientation": orientation, "migration": name, **result})
                if before != store.snapshot():
                    raise AssertionError("Original state changed")
        finally:
            store.close()
    drifting = [r for r in cases if r["type_valid"] and r["changed_answers"]]
    benign = [r for r in cases if r["type_valid"] and r["changed_answers"] == 0]
    false_accepts = sum(r["accepted"] for r in drifting)
    false_rejects = sum(not r["accepted"] for r in benign)
    return {"evidence_kind": "actual_GraphStore_synthetic_invariant", "cases": cases,
            "type_valid_migrations": sum(r["type_valid"] for r in cases), "query_changing_migrations": len(drifting),
            "drift_accepted_by_type_only_gate": len(drifting), "drift_accepted_by_query_gate": false_accepts,
            "benign_rejected_by_query_gate": false_rejects, "original_unchanged": True,
            "target_met": bool(drifting and benign) and false_accepts == false_rejects == 0,
            "limitation": "Only finite unqualified single-edge queries over existing nodes; not future-data equivalence or semantic truth."}
