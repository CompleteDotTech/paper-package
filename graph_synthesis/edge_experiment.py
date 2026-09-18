"""Execute and audit the frozen relationship-fusion protocol, without networking."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import csv
import gzip
import hashlib
import io
import itertools
import json
from pathlib import Path
import platform
import time
import zipfile
from typing import Any

import numpy as np

from .core import canonical, digest
from .edge_fusion import (ARMS, LABELS, TASK, VERSION, Decision, Observation,
    budget_metrics, load_split, metrics, predict, rank_edges, train_policy, valid)
from .recorded import RecordedJev, ScoredDecision
from .study import make_graph

PROTOCOL_COMMIT = "51803661e3b8913f1a81cfc394954f0b517e95a0"
DRAW_COUNT = 2000
BUDGETS = (25, 50, 75, 100, 125, 150, 175, 200)


def bootstrap_weights(observations: list[Observation]) -> tuple[list[str], np.ndarray]:
    groups = sorted({o.group for o in observations})
    if not groups:
        raise ValueError("Bootstrap needs at least one component")
    weights = np.random.default_rng(20260918).multinomial(len(groups), np.full(len(groups), 1/len(groups)), DRAW_COUNT)
    return groups, weights


def interval(values: np.ndarray) -> dict[str, Any]:
    values = values[np.isfinite(values)]
    return {"draws": DRAW_COUNT, "valid_draws": len(values),
            "interval": np.quantile(values, [.025, .975]).tolist() if len(values) else None}


def bootstrap_f1(gold: list[str], observations: list[Observation], decisions: list[Decision],
                 groups: list[str], weights: np.ndarray) -> np.ndarray:
    counts = np.zeros((len(groups), 3, 5), dtype=np.int64)
    group_index = {group: i for i, group in enumerate(groups)}
    outcomes = (*LABELS, "ERROR", "ABSTAIN")
    for g, o, d in zip(gold, observations, decisions):
        counts[group_index[o.group], LABELS.index(g), outcomes.index(d.label)] += 1
    sampled = (weights @ counts.reshape(len(groups), 15)).reshape(-1, 3, 5)
    tp = np.stack([sampled[:, i, i] for i in range(3)], axis=1)
    denominator = sampled.sum(axis=2) + sampled[:, :, :3].sum(axis=1)
    return np.divide(2*tp, denominator, out=np.zeros_like(tp, dtype=float), where=denominator != 0).mean(axis=1)


def bootstrap_precision(gold: list[str], observations: list[Observation], decisions: list[Decision],
                        selected: list[int], groups: list[str], weights: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    counts = np.zeros((len(groups), 2), dtype=np.int64)
    group_index = {group: i for i, group in enumerate(groups)}
    for i in selected:
        counts[group_index[observations[i].group]] += [gold[i] == decisions[i].label, 1]
    sampled = weights @ counts
    return (np.divide(sampled[:, 0], sampled[:, 1], out=np.full(len(weights), np.nan),
                      where=sampled[:, 1] != 0), sampled[:, 1])


def comparison(gold, observations, left, right, groups, weights, *, relation=None):
    k = min(len(rank_edges(observations, left, relation)), len(rank_edges(observations, right, relation)))
    lm = budget_metrics(gold, observations, left, k, relation)
    rm = budget_metrics(gold, observations, right, k, relation)
    lp, ln = bootstrap_precision(gold, observations, left, rank_edges(observations, left, relation)[:k], groups, weights)
    rp, rn = bootstrap_precision(gold, observations, right, rank_edges(observations, right, relation)[:k], groups, weights)
    for value in (lm, rm):
        value.pop("selected_ids")
    return {"k": k, "left": lm, "right": rm,
            "precision_delta": rm["precision"]-lm["precision"] if k else None,
            "bootstrap": {**interval(rp-lp), "unequal_denominator_draws": int(np.sum(ln != rn)),
                "left_denominator_range": [int(ln.min()), int(ln.max())],
                "right_denominator_range": [int(rn.min()), int(rn.max())]},
            "interpretation": "Score-only exact-K sets; intervals condition on these sets, no reranking or refitting."}


def graph_for(backend, observations, gold, decisions):
    rows = []
    for o, g, d in zip(observations, gold, decisions):
        p = dict(zip(LABELS, d.probabilities)) if d.probabilities is not None else {}
        raw = backend.rows[TASK, "evaluation", o.id]
        score = ScoredDecision(p, d.label, o.model if len(d.call_ids) == 1 else o.model + "/" + VERSION, "recorded", d.request_hash,
                               "derived:" + d.request_hash if len(d.call_ids) == 2 else d.call_ids[0],
                               d.reason if d.label == "ERROR" else None)
        rows.append({"id": o.id, "group": o.group, "gold": g, "label": d.label,
                     "score": p.get(d.label, 0), "decision": score, "row": raw})
    result = make_graph(rows, TASK)
    return {key: result[key] for key in ("metrics", "audit", "lifecycle", "committed_label_correct", "committed_label_incorrect")}


def compact_journal(observations, gold, outputs, model_hash) -> bytes:
    """All labels + fitted probabilities; other probabilities resolve from frozen inputs.

    IDs index the immutable plan/calls. Combined request hashes are deterministically
    recomputed from those inputs and the committed fitted model, never fabricated
    vendor call IDs. The full expanded journal is also emitted in CI artifacts.
    """
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["model_hash", model_hash])
    writer.writerow(["id", "gold", *ARMS, "stacked_support", "stacked_refute", "stacked_nei"])
    for i, (o, truth) in enumerate(zip(observations, gold)):
        values = outputs["stacked"][i].probabilities
        writer.writerow([o.id, truth, *(outputs[a][i].label for a in ARMS), *(values or ("", "", ""))])
    compressed = io.BytesIO()
    with gzip.GzipFile(fileobj=compressed, mode="wb", filename="", mtime=0) as target:
        target.write(stream.getvalue().encode())
    return compressed.getvalue()


def run(repository: Path, output: Path) -> dict[str, Any]:
    started = time.perf_counter()
    backend = RecordedJev(repository)
    calibration, cg = load_split(backend, "calibration")
    observations, gold = load_split(backend, "evaluation")
    if {o.group for o in calibration} & {o.group for o in observations} or {o.id for o in calibration} & {o.id for o in observations}:
        raise ValueError("Calibration/evaluation overlap")
    fitted = train_policy(calibration, cg, split="calibration")
    selection_seconds = time.perf_counter()-started
    outputs = {arm: [predict(o, arm, fitted["model"] if arm == "stacked" else None) for o in observations] for arm in ARMS}
    groups, weights = bootstrap_weights(observations)
    common = [i for i, o in enumerate(observations) if valid(o)]
    results = {"version": VERSION, "protocol_commit": PROTOCOL_COMMIT,
        "study_type": "exploratory post-hoc score fusion over frozen Jev inference",
        "fresh_http_calls": 0, "source_hashes": backend.hashes, "model_hash": fitted["model_hash"],
        "code_sha256": {name: hashlib.sha256((repository/"graph_synthesis"/name).read_bytes()).hexdigest()
                        for name in ("edge_fusion.py", "edge_experiment.py", "core.py", "recorded.py", "study.py")},
        "calibration_rows": len(calibration), "calibration_components": len({o.group for o in calibration}),
        "evaluation_rows": len(observations), "evaluation_components": len(groups),
        "common_success_n": len(common), "selected_regularization": fitted["selected_regularization"],
        "arms": {}, "comparisons": {}, "limitations": [
            "Previously inspected evaluation; not independent confirmation or new inference.",
            "Document-to-claim support/refutation only; no extraction/retrieval recall.",
            "Correlated same-model formulations, not independent evidentiary sources.",
            "Two constituent calls for every ensemble; no silent fallback on invalid responses.",
            "Unadjusted component-bootstrap intervals condition on fitted models and fixed ranked sets.",
            "No risk certificate or production acceptance policy is enabled.",
            "Model coefficients and features are rounded to 8 decimals; stacked probabilities to 8 decimals with sum correction."]}
    f1_samples = {}
    for arm, decisions in outputs.items():
        curves = []
        for k in BUDGETS:
            if k <= len(rank_edges(observations, decisions)):
                value = budget_metrics(gold, observations, decisions, k)
                value.pop("selected_ids")
                curves.append(value)
        calls = {c for d in decisions for c in d.call_ids}
        usage = [backend.calls[c]["tokens_used"] for c in calls]
        graph = graph_for(backend, observations, gold, decisions)
        point = metrics(gold, decisions)
        if graph["committed_label_correct"] != point["edges"]["correct"] or graph["committed_label_incorrect"] != point["edges"]["incorrect"]:
            raise AssertionError("Graph and edge metrics disagree")
        results["arms"][arm] = {"operational": point,
            "common_success": metrics([gold[i] for i in common], [decisions[i] for i in common]),
            "budget_curve": curves, "graph": graph,
            "recorded_usage": {"calls": len(calls), "input_tokens": sum(u["input"] for u in usage),
                               "output_tokens": sum(u["output"] for u in usage)}}
        f1_samples[arm] = bootstrap_f1(gold, observations, decisions, groups, weights)
    for left, right in itertools.combinations(ARMS, 2):
        results["comparisons"][left + "__vs__" + right] = {
            "macro_f1_delta": results["arms"][right]["operational"]["macro_f1"]-results["arms"][left]["operational"]["macro_f1"],
            "macro_f1_bootstrap": interval(f1_samples[right]-f1_samples[left]),
            "matched_edges": comparison(gold, observations, outputs[left], outputs[right], groups, weights),
            "matched_relations": {relation: comparison(gold, observations, outputs[left], outputs[right], groups, weights, relation=relation)
                                  for relation in LABELS[:2]}}
    output.mkdir(parents=True, exist_ok=True)
    for name, value in (("results.json", results), ("selection.json", fitted)):
        (output/name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+"\n", encoding="utf-8")
    (output/"decisions.csv.gz").write_bytes(compact_journal(observations, gold, outputs, fitted["model_hash"]))
    with (output/"expanded-decisions.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for i, o in enumerate(observations):
            f.write(canonical({"input": asdict(o), "evaluation_gold": gold[i], "model_hash": fitted["model_hash"],
                               "outputs": {arm: asdict(outputs[arm][i]) for arm in ARMS}})+"\n")
    (output/"environment.json").write_text(json.dumps({"python": platform.python_version(), "numpy": np.__version__,
        "selection_seconds": selection_seconds, "total_seconds": time.perf_counter()-started}, indent=2)+"\n", encoding="utf-8")
    (output/"TABLES.md").write_text(render_tables(results), encoding="utf-8")
    return results


def render_tables(results):
    lines = ["# Executed relationship experiments", "", "Post-hoc frozen-inference analysis; zero fresh Jev calls.", "",
             "| Arm | Macro-F1 | Correct edges | Incorrect edges | Precision | Recall | Errors | Abstentions |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for arm, result in results["arms"].items():
        m = result["operational"]; e = m["edges"]
        lines.append(f"| {arm} | {m['macro_f1']:.6f} | {e['correct']} | {e['incorrect']} | {e['precision']:.6f} | {e['recall']:.6f} | {m['errors']} | {m['abstentions']} |")
    lines += ["", "## Matched accepted-edge volume", "", "Intervals are exploratory, conditional on the original selected sets, and unadjusted.", "",
        "| Left | Right | K | Left correct/incorrect | Right correct/incorrect | Precision delta | Paired 95% interval |",
        "|---|---|---:|---:|---:|---:|---|"]
    for key, item in results["comparisons"].items():
        left, right = key.split("__vs__"); m = item["matched_edges"]
        lo, hi = m["bootstrap"]["interval"]
        lines.append(f"| {left} | {right} | {m['k']} | {m['left']['correct']}/{m['left']['incorrect']} | {m['right']['correct']}/{m['right']['incorrect']} | {m['precision_delta']:.6f} | [{lo:.6f}, {hi:.6f}] |")
    return "\n".join(lines)+"\n"


def compare_reference(actual: Any, expected: Any, path: str = "root") -> None:
    """Floats tolerate arithmetic noise; labels, hashes, counts and structures do not."""
    if type(actual) != type(expected):
        raise AssertionError("Type mismatch at " + path)
    if isinstance(actual, dict):
        if actual.keys() != expected.keys():
            raise AssertionError("Key mismatch at " + path)
        for key in actual:
            compare_reference(actual[key], expected[key], path+"."+key)
    elif isinstance(actual, list):
        if len(actual) != len(expected):
            raise AssertionError("Length mismatch at " + path)
        for i, (a, e) in enumerate(zip(actual, expected)):
            compare_reference(a, e, path+"."+str(i))
    elif isinstance(actual, float):
        if not np.isclose(actual, expected, atol=1e-8, rtol=1e-8):
            raise AssertionError("Float mismatch at " + path)
    elif actual != expected:
        raise AssertionError("Value mismatch at " + path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", type=Path, help="Directory or ZIP of committed reference results")
    args = parser.parse_args()
    if args.check and args.output.resolve() == args.check.resolve():
        parser.error("Output must not overwrite reference evidence")
    result = run(args.repository, args.output)
    if args.check:
        archive = zipfile.ZipFile(args.check) if args.check.is_file() else None
        try:
            def reference(name):
                return archive.read(name) if archive else (args.check/name).read_bytes()
            for name in ("results.json", "selection.json"):
                compare_reference(json.loads((args.output/name).read_text(encoding="utf-8")),
                                  json.loads(reference(name)))
            if gzip.decompress((args.output/"decisions.csv.gz").read_bytes()) != gzip.decompress(reference("decisions.csv.gz")):
                raise AssertionError("Decision journal differs")
        finally:
            if archive:
                archive.close()
    print(render_tables(result))


if __name__ == "__main__":
    main()
