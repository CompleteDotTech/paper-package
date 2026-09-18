"""Post-hoc graph replay and lifecycle evaluation; never calls a model service.

This is a transformation of existing Jev observations, NOT an independent accuracy
replication or an open-corpus extraction benchmark. Gold is used only by metrics.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import random
import tempfile
from typing import Any

from .core import (GraphStore, Policy, Relation, bind, candidate, canonical,
                   digest, evidence, graph_metrics)
from .recorded import BASE_COMMIT, BASELINES, LABELS, RecordedJev, input_state

THRESHOLDS = (0.5, 0.85, 0.9, 0.95, 0.99, 1.0)
SCHEMA = {
    "supports": Relation("Document", "Claim", incompatible=("refutes",)),
    "refutes": Relation("Document", "Claim", incompatible=("supports",)),
    "same_as": Relation("Record", "Record", symmetric=True, transitive=True, allow_self=True),
    "different_from": Relation("Record", "Record", symmetric=True),
}
CONTRACTS = {"supports": LABELS["relation_support"],
             "refutes": ("REFUTES", "SUPPORTS", "NOT_ENOUGH_INFO"),
             "same_as": LABELS["entity_resolution"], "different_from": ("different", "same")}
PREDICATES = {"SUPPORTS": "supports", "REFUTES": "refutes", "same": "same_as", "different": "different_from"}


def binomial_upper(errors: int, total: int, alpha: float = .05) -> float | None:
    """One-sided exact binomial upper bound, with explicit conditional assumptions."""
    if type(total) is not int or type(errors) is not int or not 0 <= errors <= total or not 0 < alpha < 1:
        raise ValueError("Invalid binomial counts or confidence level")
    if total == 0: return None
    if errors == total: return 1.0
    if errors == 0: return 1 - alpha ** (1 / total)
    coefficients = [math.lgamma(total+1)-math.lgamma(k+1)-math.lgamma(total-k+1) for k in range(errors+1)]
    low, high = 0.0, 1.0
    for _ in range(65):
        p = (low+high)/2
        cdf = sum(math.exp(c + k*math.log(p) + (total-k)*math.log1p(-p))
                  for k, c in enumerate(coefficients))
        if cdf > alpha: low = p
        else: high = p
    return (low+high)/2


def action_metrics(rows: list[dict[str, Any]], accepted: set[str], label: str) -> dict[str, Any]:
    gold_count = sum(row["gold"] == label for row in rows)
    true = sum(row["id"] in accepted and row["gold"] == label for row in rows)
    false = len(accepted)-true
    return {"accepted": len(accepted), "true": true, "false": false,
            "precision": true/len(accepted) if accepted else None,
            "recall": true/gold_count if gold_count else None,
            "coverage": len(accepted)/len(rows) if rows else None,
            "negative_n": len(rows)-gold_count,
            "false_positive_rate": false/(len(rows)-gold_count) if len(rows) != gold_count else None}


def accepted_ids(rows: list[dict[str, Any]], label: str, threshold: float) -> set[str]:
    return {row["id"] for row in rows if row["label"] == label and row["score"] >= threshold}


def calibration_policy(rows: list[dict[str, Any]], label: str, *, split: str,
                       target_false_positive_rate: float = .01) -> dict[str, Any]:
    if split != "calibration":
        raise ValueError("Policy selection must not consume evaluation labels")
    independent_units = len({row["group"] for row in rows}) == len(rows)
    candidates = []
    for threshold in THRESHOLDS:
        metrics = action_metrics(rows, accepted_ids(rows, label, threshold), label)
        upper = binomial_upper(metrics["false"], metrics["negative_n"], .05/len(THRESHOLDS))
        candidates.append({"threshold": threshold, **metrics, "simultaneous_upper_bound": upper})
    feasible = [row for row in candidates if independent_units and row["accepted"] and row["simultaneous_upper_bound"] is not None
                and row["simultaneous_upper_bound"] <= target_false_positive_rate]
    selected = max(feasible, key=lambda row: (row["accepted"], row["threshold"])) if feasible else None
    return {"source_split": split, "label": label, "target_false_positive_rate": target_false_positive_rate,
            "family_alpha": .05, "grid_size": len(THRESHOLDS), "grid": candidates,
            "unique_unit_per_row": independent_units,
            "threshold": selected["threshold"] if selected else None,
            "status": ("dependent_rows_no_binomial_qualification" if not independent_units else
                       "eligible_under_binomial_assumptions" if selected else "insufficient_evidence"),
            "note": "Finite-grid Bonferroni bounds; conditional on independent representative negative units. Not a domain-shift or graph-risk guarantee."}


def read_scores(backend: RecordedJev, task: str, arm: str, split: str) -> list[dict[str, Any]]:
    rows = []
    for row in backend.plan["tasks"][task][split]:
        result = backend.score(task, arm, split, row["id"], input_state(task, row))
        rows.append({"id": row["id"], "group": row["group"], "gold": row["gold_label"],
                     "label": result.label, "score": result.probabilities.get(result.label, 0),
                     "decision": result, "row": row})
    return rows


def make_graph(rows: list[dict[str, Any]], task: str, threshold: float = 0.0,
               export_directory: Path | None = None) -> dict[str, Any]:
    policy = Policy("frozen-argmax-descriptive-v1", {p: threshold for p in SCHEMA}, CONTRACTS)
    nodes, sources, facts, accepted = {}, {}, [], []
    for scored in rows:
        row, result = scored["row"], scored["decision"]
        if task == "relation_support":
            s, o = "document:"+row["document_id"], "claim:"+row["claim_id"]
            nodes.update({s: "Document", o: "Claim"})
            ev = evidence(s, digest(row["evidence"]), "\n".join(row["evidence"]))
            target = evidence(o, digest(row["claim"]), row["claim"])
        else:
            s, o = "record:"+row["entity_1"], "record:"+row["entity_2"]
            nodes.update({s: "Record", o: "Record"})
            ev = evidence(s, digest(row["record_1"]), canonical(row["record_1"]))
            target = evidence(o, digest(row["record_2"]), canonical(row["record_2"]))
        sources.update({ev["id"]: ev, target["id"]: target})
        if result.error or result.label not in PREDICATES or scored["score"] < threshold:
            continue
        item = candidate(row["id"], s, PREDICATES[result.label], o, [ev["id"], target["id"]])
        facts.append(bind(item, result.probabilities, result.label, model=result.model, mode=result.mode,
                          request_hash=result.request_hash, policy_version=policy.version, labels=LABELS[task]))
        accepted.append(scored)
    with tempfile.TemporaryDirectory(prefix="graph-study-") as tmp:
        path = str(Path(tmp)/"graph.sqlite")
        store = GraphStore(path, SCHEMA, policy)
        try:
            store.commit(nodes=nodes, sources=sources.values(), facts=facts, expected_version=0, key="load-frozen")
            initial, view, audit = store.snapshot(), store.view(), store.audit()
            if export_directory is not None:
                export_directory.mkdir(parents=True, exist_ok=True)
                (export_directory / "initial-state.json").write_text(canonical(initial)+"\n", encoding="utf-8")
                (export_directory / "accepted-view.json").write_text(canonical(view)+"\n", encoding="utf-8")
            metrics = graph_metrics(nodes, view["edges"])
            # Select the largest evidence-dependent incident set without consulting gold.
            impact = Counter(ev for item in facts for ev in item["evidence"])
            target_source = min(impact, key=lambda ev: (-impact[ev], ev)) if impact else None
            lifecycle = {"withdrawn_evidence": target_source, "expected_retractions": impact[target_source] if target_source else 0}
            if target_source:
                store.retract(evidence_ids=[target_source], expected_version=1, key="source-withdrawal",
                              reason="controlled withdrawal of an existing recorded source snapshot")
                after = store.snapshot()
                actual = sum(not item["active"] for item in after["facts"].values())
                if actual != impact[target_source]:
                    raise AssertionError("Source withdrawal did not propagate to the incident assertions")
                lifecycle.update(actual_retractions=actual, original_assertions_preserved=len(after["facts"]),
                                 active_after_withdrawal=sum(x["active"] for x in after["facts"].values()))
                store.close()
                store = GraphStore(path, SCHEMA, policy)
                if store.snapshot() != after:
                    raise AssertionError("Durable reopen changed the graph")
                lifecycle["durable_reopen_equal"] = True
                lifecycle["audit_after_withdrawal"] = store.audit()
            by_claim = defaultdict(set)
            for edge in view["edges"]:
                if edge["predicate"] in {"supports", "refutes"}:
                    by_claim[edge["object"]].add(edge["predicate"])
            # Opposing sources are retained as evidence; they are not silently collapsed into world truth.
            metrics["claims_with_opposing_source_labels"] = sum(len(labels) > 1 for labels in by_claim.values())
            metrics["identity_components"] = len(set(view["identities"].values()))
            origins = {(item["origin"], digest(item["text"])) for item in sources.values()}
            metrics["distinct_source_content_origins"] = len(origins)
            metrics["assertions"] = len(facts)
            metrics["node_type_counts"] = dict(sorted(Counter(nodes.values()).items()))
            metrics["relation_endpoint_type_counts"] = dict(sorted(Counter(
                nodes[e["subject"]]+" -> "+e["predicate"]+" -> "+nodes[e["object"]] for e in view["edges"]).items()))
            if export_directory is not None:
                (export_directory / "after-withdrawal.json").write_text(canonical(store.snapshot())+"\n", encoding="utf-8")
            return {"threshold": threshold, "metrics": metrics, "audit": audit, "lifecycle": lifecycle,
                    "committed_label_correct": sum(x["label"] == x["gold"] for x in accepted),
                    "committed_label_incorrect": sum(x["label"] != x["gold"] for x in accepted),
                    "accepted_assertion_ids": sorted(x["id"] for x in accepted),
                    "semantics": "claim-source evidence graph" if task == "relation_support" else "pairwise identity/cannot-link evidence graph",
                    "not_measured": "open-corpus candidate retrieval, biomedical entity/predicate extraction, or independently observed updates"}
        finally:
            store.close()


def paired_precision_interval(left: list[dict[str, Any]], right: list[dict[str, Any]],
                              left_ids: set[str], right_ids: set[str], label: str) -> dict[str, Any]:
    groups = defaultdict(lambda: [0, 0, 0, 0])
    for arm, rows, accepted in ((0, left, left_ids), (2, right, right_ids)):
        for row in rows:
            if row["id"] in accepted:
                groups[row["group"]][arm] += int(row["gold"] == label)
                groups[row["group"]][arm+1] += 1
            else:
                groups[row["group"]]  # Include groups with no committed edge.
    values = list(groups.values())
    rng, differences = random.Random(20260918), []
    for _ in range(1000):
        total = [0, 0, 0, 0]
        for _ in values:
            sample = values[rng.randrange(len(values))]
            total = [a+b for a, b in zip(total, sample)]
        if total[1] and total[3]:
            differences.append(total[2]/total[3] - total[0]/total[1])
    differences.sort()
    def quantile(q):
        index = q*(len(differences)-1)
        lo, hi = math.floor(index), math.ceil(index)
        return differences[lo] + (differences[hi]-differences[lo])*(index-lo)
    return {"units": len(values), "draws": 1000, "valid_draws": len(differences),
            "interval": [quantile(.025), quantile(.975)] if differences else None,
            "note": "Exploratory paired component bootstrap, conditional on frozen decisions and score-only selected sets; no multiplicity correction."}


def run_study(repository: Path, export_directory: Path | None = None) -> dict[str, Any]:
    backend = RecordedJev(repository)
    results = {"base_commit": BASE_COMMIT, "input_sha256": backend.hashes,
               "study_type": "post-hoc frozen-inference graph replay plus controlled source-withdrawal episodes",
               "fresh_model_calls": 0, "tasks": {},
               "limitations": ["No fresh inference or independent test population.",
                   "Supplied candidates only: no extraction/retrieval recall estimate.",
                   "DBLP-ACM evaluation pairs are identity-disjoint; multi-candidate and noisy-bridge generalization remain unmeasured.",
                   "Source-withdrawal episodes are controlled interventions, not observed scientific retractions.",
                   "No direct KARMA execution; graph density/connectivity is not evidence of semantic correctness."]}
    for task in LABELS:
        arms = (BASELINES[task], "fewshot_contract")
        task_result, evaluation = {}, {}
        primary = "SUPPORTS" if task == "relation_support" else "same"
        for arm in arms:
            rows = read_scores(backend, task, arm, "evaluation")
            calibration = read_scores(backend, task, arm, "calibration")
            evaluation[arm] = rows
            actions = {}
            for label in LABELS[task]:
                if label == "NOT_ENOUGH_INFO": continue
                actions[label] = {"argmax": action_metrics(rows, accepted_ids(rows, label, 0), label),
                    "frontier": [{"threshold": t, **action_metrics(rows, accepted_ids(rows, label, t), label)} for t in THRESHOLDS],
                    "calibration_policy": calibration_policy(calibration, label, split="calibration")}
            call_ids = {row["decision"].call_id for row in rows}
            calls = [backend.calls[id_] for id_ in sorted(call_ids)]
            known_usage = [x["tokens_used"] for x in calls if x.get("tokens_used")]
            task_result[arm] = {"eligible": len(rows), "errors": sum(x["label"] == "ERROR" for x in rows),
                "correct": sum(x["label"] == x["gold"] for x in rows),
                "accuracy": sum(x["label"] == x["gold"] for x in rows)/len(rows),
                "confusion": dict(sorted(Counter(x["gold"]+" -> "+x["label"] for x in rows).items())),
                "actions": actions, "graph": make_graph(rows, task, export_directory=(export_directory/task/arm if export_directory else None)),
                "recorded_evaluation_usage": {"calls": len(calls), "missing_usage": len(calls)-len(known_usage),
                    "input_tokens": sum(x["input"] for x in known_usage),
                    "output_tokens": sum(x["output"] for x in known_usage),
                    "sum_original_call_latency_ms": sum(x["latency_ms"] for x in calls),
                    "note": "Historical service measurements; replay has zero new provider usage. Extraction/retrieval/storage/review costs excluded."}}
        left, right = (evaluation[arm] for arm in arms)
        ranked = [sorted((x for x in rows if x["label"] == primary), key=lambda x: (-x["score"], x["id"]))
                  for rows in (left, right)]
        count = min(map(len, ranked))
        accepted = [{row["id"] for row in values[:count]} for values in ranked]
        task_result["matched_primary_action_count"] = {"label": primary, "accepted_per_arm": count,
            "baseline": action_metrics(left, accepted[0], primary),
            "selected": action_metrics(right, accepted[1], primary),
            "paired_precision_difference": paired_precision_interval(left, right, *accepted, primary),
            "selection_rule": "Sort predicted-primary actions by score descending then row ID; common count is the smaller available set. Gold is not used to select actions."}
        results["tasks"][task] = task_result
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--export-graphs", type=Path, help="Optional directory for source-bound graph snapshots")
    args = parser.parse_args()
    from .recorded import inventory
    protected = {args.repository.resolve()/name for name in inventory(args.repository)}
    protected.add(args.repository.resolve()/"MANIFEST.json")
    if args.output.resolve() in protected or args.output.resolve().is_relative_to((args.repository/"reproduction").resolve()):
        parser.error("Do not overwrite the archived experiment")
    if args.export_graphs and args.export_graphs.resolve().is_relative_to(args.repository.resolve()):
        parser.error("Export graphs outside the research repository")
    result = run_study(args.repository, args.export_graphs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False)+"\n", encoding="utf-8")
    summary = {task: {arm: {"eligible": values[arm]["eligible"], "correct": values[arm]["correct"],
                          "graph": values[arm]["graph"]["metrics"], "actions": {label: a["argmax"]
                              for label, a in values[arm]["actions"].items()}}
                     for arm in (BASELINES[task], "fewshot_contract")}
               for task, values in result["tasks"].items()}
    print("GRAPH_STUDY_SUMMARY="+json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
