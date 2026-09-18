"""Synthetic E6 controls using frozen predictions and actual in-memory graphs.

Run with python -B -m pgc.experiments.run_compiler_research. No model or API runs.
The confidence-only comparator deliberately inserts positive edges regardless
of predicted polarity; it is a mechanism control, not a historical benchmark.
"""
from copy import deepcopy
from datetime import datetime
import argparse
import hashlib
import json
from pathlib import Path

from pgc.compiler import GraphCompiler, InMemoryGraphStore, evaluate_constraint
from pgc.decision import DecisionBackend, DecisionResponse
from pgc.ir import (CandidateGraphIR, Constraint, ConstraintSet, EdgeCandidate,
                    Evidence, EvidenceSpan, ObjectKind, PropertyCandidate)


LABELS = ["SUPPORTS", "REFUTES", "NOT_ENOUGH_INFO"]


class FrozenBackend(DecisionBackend):
    def __init__(self, predictions=None):
        self.predictions = deepcopy(predictions or {})
        self.calls = 0

    def name(self):
        return "synthetic-frozen-compiler-control"

    def version(self):
        return "1"

    def decide(self, request):
        self.calls += 1
        if request.task == "relation_support":
            distribution = self.predictions.get(request.payload["claim"],
                                                {"SUPPORTS": .99, "REFUTES": .005, "NOT_ENOUGH_INFO": .005})
        else:
            distribution = {label: float(index == 0) for index, label in enumerate(request.labels)}
        return DecisionResponse(request.request_id, deepcopy(distribution),
                                confidence=max(distribution.values()), execution_mode="mock",
                                metadata={"purpose": "synthetic mechanism control"})

    def batch_decide(self, requests):
        return [self.decide(request) for request in requests]


def source():
    text = "Synthetic fixture evidence; labels and predictions are predetermined for mechanism tests."
    return Evidence("synthetic-source", "synthetic-document", "document", "1",
                    EvidenceSpan("synthetic-document", "1", 0, len(text), text),
                    "synthetic-fixture", "1", datetime(2026, 9, 17))


def constraint_set(extra=None):
    values = {
        "referential": Constraint("referential", "referential", "Endpoints exist", {"rule": "referential"}),
        "no_self_loops": Constraint("no_self_loops", "logical", "No self loops", {"rule": "no_self_loops"}),
    }
    values.update(extra or {})
    return ConstraintSet("synthetic", "1", values)


def candidate(edge_id, subject, object_, ev):
    return EdgeCandidate(edge_id, ObjectKind.EDGE, subject, "knows", object_, [ev],
                         subject_id=subject, object_id=object_)


def make_compiler(nodes, predictions=None):
    backend = FrozenBackend(predictions)
    store = InMemoryGraphStore("synthetic", nodes=nodes)
    return GraphCompiler("synthetic", backend, store=store, allowed_execution_modes={"mock"}), backend


def quality(committed, rows):
    gold = {r["id"] for r in rows if r["gold"] == "SUPPORTS"}
    accepted = set(committed)
    correct = len(accepted & gold)
    return {
        "candidates": len(rows), "committed": len(accepted), "correct_committed": correct,
        "false_committed": len(accepted) - correct, "gold_positive_count": len(gold),
        "committed_precision": correct / len(accepted) if accepted else None,
        "positive_recall": correct / len(gold) if gold else None,
        "coverage": len(accepted) / len(rows), "committed_ids": sorted(accepted),
    }


def frozen_quality_comparison():
    settings = [
        ("valid_high", "SUPPORTS", .99, "SUPPORTS"),
        ("confident_refutation", "REFUTES", .99, "REFUTES"),
        ("confident_unknown", "NOT_ENOUGH_INFO", .98, "NOT_ENOUGH_INFO"),
        ("valid_second", "SUPPORTS", .97, "SUPPORTS"),
        ("semantic_false_positive", "SUPPORTS", .96, "REFUTES"),
        ("semantic_false_negative", "REFUTES", .95, "SUPPORTS"),
        ("weak_true_positive", "SUPPORTS", .60, "SUPPORTS"),
    ]
    ev, nodes, rows, predictions, edges = source(), {}, [], {}, []
    for index, (edge_id, prediction, confidence, gold) in enumerate(settings):
        subject, object_ = "s" + str(index), "o" + str(index)
        nodes[subject] = {"types": ["Person"]}
        nodes[object_] = {"types": ["Person"]}
        edge = candidate(edge_id, subject, object_, ev)
        edges.append(edge)
        distribution = {label: confidence if label == prediction else (1-confidence)/2 for label in LABELS}
        predictions[subject + " knows " + object_] = distribution
        rows.append({"id": edge_id, "distribution": distribution, "gold": gold,
                     "subject": subject, "object": object_, "predicate": "knows"})
    proposals = CandidateGraphIR("synthetic", "v1", datetime(2026, 9, 17), edges=edges)
    compiler, backend = make_compiler(nodes, predictions)
    tx, ctx = compiler.compile([ev], proposals, constraint_set())
    if tx.status != "committed":
        raise AssertionError(ctx.errors)
    typed_graph = compiler.store.snapshot()
    eligible = [row for row in rows if max(row["distribution"].values()) >= .85]
    # This comparator writes a graph with real edge records, deliberately omitting
    # outcome interpretation. All endpoint/schema checks are satisfied here.
    baseline_graph = {"nodes": deepcopy(nodes), "edges": {r["id"]: {"subject": r["subject"],
                      "predicate": r["predicate"], "object": r["object"]} for r in eligible}}
    count = len(typed_graph.edges)
    matched_rows = sorted(eligible, key=lambda row: (-max(row["distribution"].values()), row["id"]))[:count]
    matched_graph = {r["id"]: baseline_graph["edges"][r["id"]] for r in matched_rows}
    assert len(matched_graph) == len(typed_graph.edges)
    assert backend.calls == len(rows)
    assert len(typed_graph.provenance) == len(typed_graph.edges)
    return {
        "design": "Same seven candidate edges and frozen probability vectors; no fitting or model calls",
        "comparator": "Confidence-only positive-edge application is a deliberately flawed mechanism baseline",
        "threshold": .85, "threshold_eligible_candidates": len(eligible),
        "frozen_predictions_sha256": hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest(),
        "frozen_rows": rows,
        "same_candidate_pool": {
            "confidence_only_positive": quality(baseline_graph["edges"], rows),
            "typed_actions": quality(typed_graph.edges, rows)},
        "matched_committed_count": {
            "selection": "Baseline takes the K highest max-class confidences, lexicographic ID tie-break; K equals typed commits",
            "confidence_only_positive": quality(matched_graph, rows),
            "typed_actions": quality(typed_graph.edges, rows)},
        "typed_backend_calls": backend.calls,
        "typed_provenance_entries": len(typed_graph.provenance),
        "interpretation": "Typed polarity removes known negative proposals but retains a semantic false positive and misses positives; no generalization claim",
    }


def graph_scenarios():
    results = []
    for name in ("positive_valid", "referential_failure", "domain_type_failure", "unique_property_failure",
                 "cardinality_failure", "self_loop_failure", "unsupported_rule", "stale_version",
                 "apply_failure", "idempotent_replay", "retry_payload_conflict"):
        ev = source()
        nodes = {"a": {"types": ["Person"], "properties": {"identifier": "A"}},
                 "b": {"types": ["Person"], "properties": {"identifier": "B"}},
                 "c": {"types": ["Person"], "properties": {"identifier": "C"}}}
        compiler, backend = make_compiler(nodes)
        graph = CandidateGraphIR("synthetic", "v1", datetime(2026, 9, 17), edges=[candidate("ab", "a", "b", ev)])
        constraints = constraint_set()
        kwargs, expected = {}, "rejected"
        if name == "positive_valid":
            expected = "committed"
        elif name == "referential_failure":
            graph.edges[0].object_id = "missing"
        elif name == "domain_type_failure":
            constraints.constraints["domain"] = Constraint("domain", "type", "Relation requires organization subject",
                                                           {"rule": "domain_range", "predicate": "knows", "domain": "Organization"})
        elif name == "unique_property_failure":
            graph.edges = []
            graph.properties = [PropertyCandidate("duplicate_identifier", "b", "identifier", "A", [ev])]
            constraints.constraints["unique"] = Constraint("unique", "uniqueness", "Unique identifier",
                                                           {"rule": "unique_property", "property": "identifier"})
        elif name == "cardinality_failure":
            graph.edges.append(candidate("ac", "a", "c", ev))
            constraints.constraints["one"] = Constraint("one", "cardinality", "At most one target",
                                                        {"rule": "cardinality", "predicate": "knows", "max": 1})
        elif name == "self_loop_failure":
            graph.edges[0].object_id = "a"
        elif name == "unsupported_rule":
            constraints.constraints["unknown"] = Constraint("unknown", "logical", "No executable specifications", "arbitrary_code()")
        elif name == "stale_version":
            kwargs["expected_version"], expected = "v0", "conflict"
        elif name == "apply_failure":
            graph.edges.append(candidate("ac", "a", "c", ev))
            kwargs["failure_after"] = 1
        elif name in ("idempotent_replay", "retry_payload_conflict"):
            kwargs["idempotency_key"] = "frozen-retry"
            initial, _ = compiler.compile([ev], graph, constraints, **kwargs)
            assert initial.status == "committed"
            if name == "retry_payload_conflict":
                graph.edges[0].predicate_mention = "different_relation"
                expected = "conflict"
            else:
                expected = "committed"
        before, calls_before = compiler.store.snapshot(), backend.calls
        initial_rule_results = {key: evaluate_constraint(value, before)[0].value
                                for key, value in constraints.constraints.items()}
        tx, ctx = compiler.compile([ev], graph, constraints, **kwargs)
        after = compiler.store.snapshot()
        assert tx.status == expected, (name, tx.status, ctx.errors)
        if name == "positive_valid":
            assert len(after.edges) == 1 and len(after.provenance) == 1 and after.version == "v2"
            assert tx.transaction_id in after.transactions
        else:
            assert after == before, name
        if name == "idempotent_replay":
            assert tx.transaction_id == initial.transaction_id and backend.calls == calls_before
        results.append({
            "scenario": name, "expected_status": expected, "status": tx.status,
            "initial_rule_results": initial_rule_results,
            "initial_graph_satisfies_relevant_rules": None if "unknown" in initial_rule_results.values()
                else all(value == "pass" for value in initial_rule_results.values()),
            "candidate_mutations": len(graph.edges) + len(graph.properties),
            "planned_mutations": len(ctx.mutations),
            "new_committed_mutations": len(after.provenance) - len(before.provenance),
            "coverage_of_this_attempt": (len(after.provenance) - len(before.provenance)) / (len(graph.edges) + len(graph.properties)),
            "edges_before": len(before.edges), "edges_after": len(after.edges),
            "provenance_before": len(before.provenance), "provenance_after": len(after.provenance),
            "version_before": before.version, "version_after": after.version,
            "unchanged_snapshot": before == after, "backend_calls_this_attempt": backend.calls - calls_before,
            "reasons": ctx.errors, "rule_results": {key: value.status.value for key, value in ctx.constraints.items()},
        })
    return results


def run(output_directory=None):
    directory = Path(output_directory) if output_directory else Path(__file__).resolve().parents[2] / "results" / "research"
    directory.mkdir(parents=True, exist_ok=True)
    quality_results, scenarios = frozen_quality_comparison(), graph_scenarios()
    root = Path(__file__).resolve().parents[2]
    source_files = ("pgc/compiler/orchestrator.py", "pgc/compiler/graph_store.py",
                    "pgc/ir/__init__.py", "pgc/experiments/run_compiler_research.py")
    result = {"execution_mode": "mock", "study": "synthetic controlled compiler mechanisms",
              "neural_or_api_execution": False,
              "source_sha256": {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in source_files},
              "quality_comparison": quality_results, "scenarios": scenarios}
    (directory / "compiler_results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    lines = ["# Synthetic compiler mechanism results", "", "These are controlled offline examples with predetermined predictions and gold labels. They demonstrate implementation behavior; they do not estimate performance on a real population.", "",
             "## Frozen-score graph quality", "", "Both policies receive the same seven candidates. The baseline deliberately applies positive edges from high max-class confidence without interpreting polarity. It is a diagnostic comparator, not a historical graph benchmark.", "",
             "| Comparison | Policy | Commits | False commits | Precision | Positive recall | Coverage |",
             "|---|---|---:|---:|---:|---:|---:|"]
    for comparison in ("same_candidate_pool", "matched_committed_count"):
        for policy in ("confidence_only_positive", "typed_actions"):
            metric = quality_results[comparison][policy]
            lines.append(f"| {comparison} | {policy} | {metric['committed']} | {metric['false_committed']} | {metric['committed_precision']:.3f} | {metric['positive_recall']:.3f} | {metric['coverage']:.3f} |")
    lines += ["", "The matched-count baseline takes the three highest max-class confidences using a fixed ID tie-break. The typed policy still commits one semantically false edge and misses correct edges; deterministic verification does not establish truth.", "",
              "## Actual graph-state scenarios", "", "| Scenario | Status | New commits | Graph/provenance unchanged | Reason |", "|---|---|---:|---|---|"]
    for row in scenarios:
        fallback = "Valid control" if row["scenario"] == "positive_valid" else "Existing transaction replayed without applying again"
        reason = "; ".join(row["reasons"]) or fallback
        lines.append(f"| {row['scenario']} | {row['status']} | {row['new_committed_mutations']} | {row['unchanged_snapshot']} | {reason} |")
    lines += ["", "Every scenario asserts the actual node/edge/provenance/version snapshot. Failure injection occurs after the first shadow mutation; no partial state is published. Retry coverage here counts newly applied mutations, so a correct replay reports zero new commits. The JSON contains frozen inputs, source-score hash, counts, constraint outcomes, and invocation counts.", "",
              "Reproduce: `python -B -m pgc.experiments.run_compiler_research`.", ""]
    (directory / "COMPILER_RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="Directory for JSON and Markdown results")
    args = parser.parse_args()
    result = run(args.output_dir)
    print(json.dumps({"study": result["study"], "scenarios": len(result["scenarios"]),
                      "synthetic_quality": result["quality_comparison"]["same_candidate_pool"]}, indent=2))
