from copy import deepcopy
from pathlib import Path
import random
import tempfile
import unittest

from graph_synthesis.core import (GraphStore, Policy, Relation, bind, candidate,
    digest, distribution, evidence, graph_metrics, select_identity)

RELATIONS = {
    "supports": Relation("Document", "Claim", incompatible=("refutes",)),
    "refutes": Relation("Document", "Claim", incompatible=("supports",)),
    "supported_by": Relation("Claim", "Document", inverse_of="supports"),
    "same_as": Relation("*", "*", symmetric=True, transitive=True),
    "different_from": Relation("*", "*", symmetric=True),
    "interacts": Relation("Entity", "Entity", symmetric=True),
    "causes": Relation("Entity", "Entity"),
    "parent": Relation("Entity", "Entity", transitive=True),
}
CONTRACTS = {p: ("SUPPORTS", "REFUTES", "NOT_ENOUGH_INFO") for p in RELATIONS}
CONTRACTS["refutes"] = ("REFUTES", "SUPPORTS", "NOT_ENOUGH_INFO")
CONTRACTS["same_as"] = ("same", "different")
CONTRACTS["different_from"] = ("different", "same")
POLICY = Policy("test-v1", {p: .85 for p in RELATIONS}, CONTRACTS, ("synthetic",))
EV = evidence("source", "v1", "Source text for a controlled mechanism test.")


def fact(id_="f", s="d", p="supports", o="c", *, deps=(), sources=None, qualifiers=None, score=.99):
    item = candidate(id_, s, p, o, sources or [EV["id"]], depends_on=deps, qualifiers=qualifiers)
    labels = CONTRACTS[p]
    values = {label: (score if i == 0 else (1-score)/(len(labels)-1)) for i, label in enumerate(labels)}
    return bind(item, values, labels[0], model="controlled-not-Jev", mode="synthetic",
                request_hash=digest({"fixture": id_}), policy_version=POLICY.version)


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.store = GraphStore(":memory:", RELATIONS, POLICY)
        self.addCleanup(self.store.close)

    def put(self, facts, nodes=None, sources=None, **kwargs):
        return self.store.commit(nodes=nodes or {"d": "Document", "c": "Claim"},
            sources=sources or [EV], facts=facts, expected_version=kwargs.pop("expected_version", self.store.snapshot()["version"]),
            key=kwargs.pop("key", "put-"+str(self.store.snapshot()["version"])), **kwargs)

    def test_evidence_exact_span(self):
        x = evidence("s", "v", "abcdef", start=1, end=3)
        self.assertEqual(x["span"], "bc")
        for kwargs in ({"start": -1}, {"end": 8}, {"start": 2, "end": 2}, {"start": True}):
            with self.assertRaises(ValueError): evidence("s", "v", "abc", **kwargs)

    def test_probability_contract_failures(self):
        for dist in ({"yes": float("nan"), "no": 0}, {"yes": True, "no": 0},
                     {"yes": .8, "no": .3}, {"yes": .9}, {"yes": -1, "no": 2}):
            with self.assertRaises(ValueError): distribution(dist, ("yes", "no"))

    def test_policy_must_cover_contracts(self):
        with self.assertRaises(ValueError): Policy("v", {"p": .8}, {})

    def test_commits_are_audited(self):
        self.put([fact()])
        self.assertEqual(len(self.store.view()["edges"]), 1)
        self.assertEqual(self.store.audit()["events"], 1)

    def test_unknown_predicate_fails_closed(self):
        f = fact(); f["predicate"] = "unknown"
        f["decision"]["candidate_hash"] = digest({k: v for k, v in f.items() if k != "decision"})
        with self.assertRaises(ValueError): self.put([f])
        self.assertEqual(self.store.snapshot()["version"], 0)

    def test_polarity_cannot_create_positive_assertion(self):
        f = fact()
        f["decision"]["selected"] = "REFUTES"
        f["decision"]["distribution"] = {"SUPPORTS": .01, "REFUTES": .98, "NOT_ENOUGH_INFO": .01}
        with self.assertRaisesRegex(ValueError, "polarity"): self.put([f])

    def test_decision_binding_detects_endpoint_change(self):
        f = fact(); f["object"] = "other"
        with self.assertRaisesRegex(ValueError, "bound"): self.put([f])

    def test_evidence_hash_detects_source_change(self):
        ev = deepcopy(EV); ev["text"] = "changed"
        with self.assertRaises(ValueError): self.put([fact()], sources=[ev])

    def test_missing_endpoint_and_wrong_type(self):
        for nodes in ({"d": "Document"}, {"d": "Claim", "c": "Document"}):
            with self.assertRaises(ValueError): self.put([fact()], nodes=nodes)
        self.assertEqual(self.store.audit()["events"], 0)

    def test_inverse_is_normalized_not_a_second_semantic_relation(self):
        self.put([fact(), fact("g", "c", "supported_by", "d")])
        edges = self.store.view()["edges"]
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]["assertions"], ["f", "g"])

    def test_symmetric_relation_normalization(self):
        self.put([fact("a", "x", "interacts", "y"), fact("b", "y", "interacts", "x")], {"x": "Entity", "y": "Entity"})
        self.assertEqual(len(self.store.view()["edges"]), 1)

    def test_direction_preserved_for_asymmetric_relation(self):
        self.put([fact("a", "x", "causes", "y"), fact("b", "y", "causes", "x")], {"x": "Entity", "y": "Entity"})
        self.assertEqual(len(self.store.view()["edges"]), 2)

    def test_transitivity_annotation_does_not_invent_edges(self):
        self.put([fact("a", "x", "parent", "y"), fact("b", "y", "parent", "z")], {n: "Entity" for n in "xyz"})
        self.assertEqual(len(self.store.view()["edges"]), 2)

    def test_multi_label_relations_can_coexist(self):
        self.put([fact("a", "x", "parent", "y"), fact("b", "x", "causes", "y")], {n: "Entity" for n in "xy"})
        self.assertEqual(len(self.store.view()["edges"]), 2)

    def test_conflict_same_scope_rolls_back_whole_transaction(self):
        with self.assertRaisesRegex(ValueError, "Incompatible"):
            self.put([fact(), fact("r", p="refutes")])
        self.assertEqual(self.store.snapshot()["nodes"], {})

    def test_different_population_qualifiers_remain_distinct(self):
        self.put([fact(qualifiers={"population": "A"}), fact("r", p="refutes", qualifiers={"population": "B"})])
        self.assertEqual(len(self.store.view()["edges"]), 2)

    def test_stale_graph_and_policy_reject(self):
        self.put([fact()])
        with self.assertRaisesRegex(ValueError, "Stale graph"):
            self.put([fact("g")], expected_version=0)
        f = fact("h"); f["decision"]["policy_version"] = "old"
        with self.assertRaisesRegex(ValueError, "Stale decision"): self.put([f])

    def test_fault_injection_is_atomic(self):
        before = self.store.snapshot()
        with self.assertRaises(RuntimeError): self.put([fact()], fail_before_publish=True)
        self.assertEqual(before, self.store.snapshot())
        self.assertEqual(self.store.audit()["events"], 0)

    def test_idempotent_replay_and_payload_conflict(self):
        first = self.put([fact()], key="once", expected_version=0)
        self.assertEqual(first, self.put([fact()], key="once", expected_version=0))
        self.assertEqual(self.store.snapshot()["version"], 1)
        with self.assertRaisesRegex(ValueError, "Idempotency"):
            self.put([fact("other")], key="once", expected_version=0)

    def test_synthetic_scores_require_explicit_opt_in(self):
        store = GraphStore(":memory:", RELATIONS, Policy("test-v1", POLICY.thresholds, CONTRACTS))
        try:
            with self.assertRaisesRegex(ValueError, "prohibited"):
                store.commit(nodes={"d": "Document", "c": "Claim"}, sources=[EV], facts=[fact()], expected_version=0, key="x")
        finally: store.close()

    def test_low_probability_defers_without_mutation(self):
        with self.assertRaisesRegex(ValueError, "insufficient"): self.put([fact(score=.6)])
        self.assertEqual(self.store.snapshot()["version"], 0)

    def test_missing_dependency_and_cycle_reject(self):
        with self.assertRaises(ValueError): self.put([fact(deps=["missing"])])
        with self.assertRaisesRegex(ValueError, "Cyclic"):
            self.put([fact("a", deps=["b"]), fact("b", deps=["a"])])

    def test_cascading_retraction_leaves_independent_support(self):
        self.put([fact("a"), fact("b", deps=["a"]), fact("c", deps=["b"]), fact("independent")])
        self.store.retract(fact_ids=["a"], reason="correction", expected_version=1, key="withdraw")
        active = {k for k, v in self.store.snapshot()["facts"].items() if v["active"]}
        self.assertEqual(active, {"independent"})
        self.assertEqual(len(self.store.view()["edges"]), 1)

    def test_source_withdrawal_preserves_other_source(self):
        ev2 = evidence("other", "v1", "Independent record")
        self.put([fact(), fact("g", sources=[ev2["id"]])], sources=[EV, ev2])
        self.store.retract(evidence_ids=[EV["id"]], reason="source withdrawn", expected_version=1, key="r")
        self.assertEqual(self.store.view()["edges"][0]["assertions"], ["g"])
        with self.assertRaisesRegex(ValueError, "withdrawn"):
            self.put([fact("fresh-id")])

    def test_retracted_assertion_id_cannot_be_reused(self):
        self.put([fact()])
        self.store.retract(fact_ids=["f"], reason="wrong", expected_version=1, key="r")
        with self.assertRaisesRegex(ValueError, "immutable"): self.put([fact()])

    def test_identity_bridge_conflict_rejected(self):
        nodes = {n: "Entity" for n in "xyz"}
        self.put([fact("n", "x", "different_from", "z")], nodes)
        with self.assertRaisesRegex(ValueError, "cannot-link"):
            self.put([fact("a", "x", "same_as", "y"), fact("b", "y", "same_as", "z")], nodes)

    def test_identity_retraction_splits_view_without_data_loss(self):
        nodes = {n: "Entity" for n in "xyz"}
        self.put([fact("a", "x", "same_as", "y"), fact("b", "y", "same_as", "z")], nodes)
        self.assertEqual(len(set(self.store.view()["identities"].values())), 1)
        self.store.retract(fact_ids=["b"], reason="identity repair", expected_version=1, key="r")
        self.assertEqual(len(set(self.store.view()["identities"].values())), 2)
        self.assertEqual(len(self.store.snapshot()["nodes"]), 3)

    def test_identity_cannot_create_forbidden_self_relation(self):
        nodes = {n: "Entity" for n in "xy"}
        self.put([fact("edge", "x", "causes", "y")], nodes)
        with self.assertRaisesRegex(ValueError, "Self"):
            self.put([fact("merge", "x", "same_as", "y")], nodes)

    def test_schema_migration_checks_existing_assertions(self):
        self.put([fact()])
        changed = dict(RELATIONS); changed["supports"] = Relation("Claim", "Document")
        with self.assertRaises(ValueError):
            self.store.migrate(changed, schema_version="bad", reviewed_by="reviewer", reason="test", expected_version=1, key="m")
        self.assertEqual(self.store.snapshot()["schema_version"], "initial")

    def test_schema_migration_requires_review(self):
        with self.assertRaises(ValueError):
            self.store.migrate(RELATIONS, schema_version="2", reviewed_by="", reason="test", expected_version=0, key="m")

    def test_persistent_reopen_and_competing_writer(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp)/"graph.sqlite")
            a, b = GraphStore(path, RELATIONS, POLICY), GraphStore(path, RELATIONS, POLICY)
            try:
                a.commit(nodes={"d": "Document", "c": "Claim"}, sources=[EV], facts=[fact()], expected_version=0, key="one")
                with self.assertRaisesRegex(ValueError, "Stale"):
                    b.commit(nodes={}, sources=[], facts=[], expected_version=0, key="two")
                self.assertEqual(b.audit()["events"], 1)
            finally: a.close(); b.close()
            c = GraphStore(path, RELATIONS, POLICY)
            self.assertEqual(len(c.view()["edges"]), 1)
            c.close()

    def test_audit_detects_corruption(self):
        self.put([fact()])
        self.store.db.execute("UPDATE journal SET hash='bad'")
        with self.assertRaises(ValueError): self.store.audit()

    def test_pairwise_selection_has_abstention(self):
        self.assertEqual(select_identity({"a": .99, "b": .98}, threshold=.9, margin=.05), "defer")
        self.assertEqual(select_identity({"a": .99, "b": .1}, threshold=.9, margin=.05), "a")
        self.assertEqual(select_identity({}, threshold=.9, margin=.05), "defer")
        self.assertEqual(select_identity({}, threshold=.9, margin=.05, new_entity_supported=True), "new")
        self.assertEqual(select_identity({"a": .2}, threshold=.9, margin=.05, new_entity_supported=True), "defer")

    def test_tied_pair_scores_do_not_force_an_identity(self):
        self.assertEqual(select_identity({"a": .99, "b": .99}, threshold=.9, margin=0), "defer")

    def test_graph_metrics_do_not_confuse_edges_with_assertions(self):
        result = graph_metrics("abcd", [{"subject": "a", "predicate": "p", "object": "b"},
                                         {"subject": "a", "predicate": "q", "object": "b"}])
        self.assertEqual((result["typed_edges"], result["distinct_directed_pairs"], result["weak_components"], result["isolates"]), (2, 1, 3, 2))

    def test_random_dependency_retraction_matches_reference(self):
        # Thirty independently seeded synthetic DAGs; not a real-data benchmark.
        for seed in range(30):
            rng = random.Random(seed)
            deps = {str(i): {str(j) for j in range(i) if rng.random() < .15} for i in range(20)}
            target = str(rng.randrange(20))
            expected = {target}
            for _ in range(20): expected |= {i for i, parents in deps.items() if parents & expected}
            store = GraphStore(":memory:", RELATIONS, POLICY)
            try:
                store.commit(nodes={"d": "Document", "c": "Claim"}, sources=[EV],
                    facts=[fact(i, deps=parents) for i, parents in deps.items()], expected_version=0, key="all")
                store.retract(fact_ids=[target], reason="randomized control", expected_version=1, key="r")
                removed = {i for i, value in store.snapshot()["facts"].items() if not value["active"]}
                self.assertEqual(expected, removed)
                self.assertEqual(store.audit()["events"], 2)
            finally: store.close()


if __name__ == "__main__":
    unittest.main()
