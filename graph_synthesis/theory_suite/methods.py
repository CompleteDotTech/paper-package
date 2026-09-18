"""Gold-free inference helpers and explicitly calibration-only fitting.

No networking, service credentials, or mutation of the default graph compiler.
"""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations
import math
from typing import Any, Iterable, Mapping, Sequence

from graph_synthesis.core import GraphStore, Relation, digest, distribution, normalize, probability


def macro_f1(gold: Sequence[str], predicted: Sequence[str], labels: Sequence[str]) -> float:
    if len(gold) != len(predicted) or not gold or not labels:
        raise ValueError("Aligned, nonempty observations and labels required")
    values = []
    for label in labels:
        tp = sum(a == b == label for a, b in zip(gold, predicted))
        fp = sum(a != label and b == label for a, b in zip(gold, predicted))
        fn = sum(a == label and b != label for a, b in zip(gold, predicted))
        values.append(2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0)
    return sum(values) / len(values)


def conformal_fit(rows: Sequence[Mapping[str, Any]], labels: Sequence[str], *,
                  split: str, alpha: float = .1) -> dict[str, Any]:
    if split != "calibration" or not 0 < alpha < 1:
        raise ValueError("Calibration split and alpha in (0,1) required")
    maxima: dict[str, float] = {}
    for row in rows:
        probs = distribution(row["probabilities"], labels) if not row["error"] else {}
        score = 1 - probs.get(row["gold"], 0.0)
        maxima[row["group"]] = max(maxima.get(row["group"], 0.0), score)
    scores = sorted(maxima.values())
    rank = math.ceil((len(scores) + 1) * (1 - alpha))
    return {"alpha": alpha, "groups": len(scores), "rank": rank,
            "universal": rank > len(scores),
            "quantile": scores[rank - 1] if rank <= len(scores) else 1.0}


def prediction_set(probabilities: Mapping[str, float], labels: Sequence[str],
                   fit: Mapping[str, Any], *, error: bool = False) -> tuple[str, ...]:
    if error or fit["universal"]:
        return tuple(labels)
    probs = distribution(probabilities, labels)
    return tuple(label for label in labels if 1 - probs[label] <= fit["quantile"] + 1e-12)


def projected_precision(tpr: float, fpr: float, prevalence: float) -> float | None:
    tpr, fpr, prevalence = map(probability, (tpr, fpr, prevalence))
    denominator = prevalence * tpr + (1 - prevalence) * fpr
    return prevalence * tpr / denominator if denominator else None


def admit_budget(features: Sequence[Mapping[str, Any]], budget: float = .05) -> set[str]:
    budget = probability(budget)
    used: dict[str, float] = defaultdict(float)
    accepted: set[str] = set()
    if len({r["id"] for r in features}) != len(features):
        raise ValueError("Duplicate candidate identifiers")
    for row in sorted(features, key=lambda r: (-probability(r["score"]), r["id"])):
        cost = 1 - row["score"]
        if used[row["group"]] + cost <= budget + 1e-12:
            accepted.add(row["id"])
            used[row["group"]] += cost
    return accepted


def review_selection(features: Sequence[Mapping[str, Any]], count: int, *, topology: bool) -> set[str]:
    if type(count) is not int or not 0 <= count <= len(features):
        raise ValueError("Review count out of range")
    if len({r["id"] for r in features}) != len(features):
        raise ValueError("Duplicate candidate identifiers")
    incident: dict[str, set[str]] = defaultdict(set)
    for row in features:
        probability(row["score"])
        for node in row["endpoints"]:
            incident[node].add(row["id"])
    def priority(row: Mapping[str, Any]) -> tuple[float, str]:
        impact = len(set().union(*(incident[n] for n in row["endpoints"]))) if topology else 1
        return (-(1 - row["score"]) * impact, row["id"])
    return {row["id"] for row in sorted(features, key=priority)[:count]}


THRESHOLDS = (0, .5, .7, .85, .9, .95, .99, 1, 1.000001)


def cascade_predict(base: Sequence[Mapping[str, Any]], selected: Sequence[Mapping[str, Any]],
                    threshold: float) -> tuple[list[str], int, int]:
    if len(base) != len(selected) or not math.isfinite(threshold) or threshold < 0:
        raise ValueError("Aligned observations and finite nonnegative threshold required")
    predictions, tokens, escalations = [], 0, 0
    for a, b in zip(base, selected):
        if a["id"] != b["id"]:
            raise ValueError("Misaligned candidate identifiers")
        for row in (a, b):
            if type(row["input_tokens"]) is not int or row["input_tokens"] < 0:
                raise ValueError("Recorded input-token counts required")
        fallback = bool(a["error"]) or a["score"] < threshold
        predictions.append(b["label"] if fallback else a["label"])
        tokens += a["input_tokens"] + (b["input_tokens"] if fallback else 0)
        escalations += fallback
    return predictions, tokens, escalations


def fit_cascade(base: Sequence[Mapping[str, Any]], selected: Sequence[Mapping[str, Any]],
                gold: Sequence[str], labels: Sequence[str], *, split: str) -> dict[str, Any]:
    if split != "calibration" or not base:
        raise ValueError("Nonempty calibration split required")
    target = macro_f1(gold, [r["label"] for r in selected], labels) - .01
    grid = []
    for threshold in THRESHOLDS:
        predictions, tokens, escalations = cascade_predict(base, selected, threshold)
        grid.append({"threshold": threshold, "macro_f1": macro_f1(gold, predictions, labels),
                     "input_tokens": tokens, "escalations": escalations})
    eligible = [r for r in grid if r["macro_f1"] >= target - 1e-12]
    winner = min(eligible, key=lambda r: (r["input_tokens"], r["threshold"]))
    return {"threshold": winner["threshold"], "calibration_target": target, "grid": grid}


def partitions(n: int) -> tuple[tuple[int, ...], ...]:
    if type(n) is not int or not 1 <= n <= 7:
        raise ValueError("Exact decoding is bounded to 1..7 nodes")
    rows = [(0,)]
    for _ in range(1, n):
        rows = [row + (x,) for row in rows for x in range(max(row) + 2)]
    return tuple(rows)


def partition_objective(partition: Sequence[int], probabilities: Mapping[tuple[int, int], float]) -> float:
    value = 0.0
    for (i, j), p in probabilities.items():
        p = min(1 - 1e-9, max(1e-9, probability(p)))
        value += math.log(p if partition[i] == partition[j] else 1 - p)
    return value


def joint_decode(n: int, probabilities: Mapping[tuple[int, int], float], *,
                 greedy_order: Sequence[tuple[int, int]] | None = None) -> tuple[int, ...]:
    candidates = partitions(n)
    expected = set(combinations(range(n), 2))
    if set(probabilities) != expected:
        raise ValueError("Exactly one probability per unordered pair is required")
    for p in probabilities.values():
        probability(p)
    if greedy_order is None:
        return max(candidates, key=lambda p: partition_objective(p, probabilities))
    if len(greedy_order) != len(expected) or set(greedy_order) != expected:
        raise ValueError("Greedy order must be a permutation of all pairs")
    labels = list(range(n))
    while True:
        changed = False
        for i, j in greedy_order:
            a, b = labels[i], labels[j]
            if a == b:
                continue
            proposed = [a if x == b else x for x in labels]
            if partition_objective(proposed, probabilities) > partition_objective(labels, probabilities) + 1e-12:
                labels, changed = proposed, True
                break
        if not changed:
            mapping: dict[int, int] = {}
            return tuple(mapping.setdefault(x, len(mapping)) for x in labels)


def semantic_key(*, state: Any, question: str, model: str, schema: str, policy: str,
                 dependencies: Mapping[str, int]) -> str:
    if not all(isinstance(s, str) and s for s in (question, model, schema, policy)):
        raise ValueError("Explicit nonempty semantic versions required")
    if any(not isinstance(k, str) or not k or type(v) is not int or v < 0
           for k, v in dependencies.items()):
        raise ValueError("Dependency generations must be nonnegative integers")
    return digest({"state": state, "question": question, "model": model, "schema": schema,
                   "policy": policy, "dependencies": dict(dependencies)})


def query_answers(store: GraphStore, queries: Iterable[tuple[str, str, str]]) -> tuple[bool, ...]:
    """Evaluate finite, unqualified single-edge query contracts, including inverses."""
    snapshot, view = store.snapshot(), store.view()
    if any(edge["qualifiers"] for edge in view["edges"]):
        raise ValueError("This finite query checker does not support qualified edges")
    visible = {(e["subject"], e["predicate"], e["object"]) for e in view["edges"]}
    answers = []
    for subject, predicate, object_ in queries:
        if subject not in snapshot["nodes"] or object_ not in snapshot["nodes"]:
            raise ValueError("Unknown query node")
        subject, object_ = view["identities"][subject], view["identities"][object_]
        answers.append(normalize({"subject": subject, "predicate": predicate, "object": object_},
                                 snapshot["schema"]) in visible)
    return tuple(answers)


def migration_preview(store: GraphStore, relations: Mapping[str, Relation],
                      queries: Sequence[tuple[str, str, str]]) -> dict[str, Any]:
    before = store.snapshot()
    answers = query_answers(store, queries)
    clone = GraphStore(":memory:", {k: Relation(**v) for k, v in before["schema"].items()}, store.policy)
    try:
        store.db.backup(clone.db)
        try:
            clone.migrate(relations, schema_version="theory-preview-v1",
                          reviewed_by="automated finite-query checker; not human review",
                          reason="controlled isolated semantic preview", expected_version=before["version"], key="preview")
            after = query_answers(clone, queries)
        except (KeyError, ValueError) as exc:
            return {"type_valid": False, "accepted": False, "error": type(exc).__name__, "changed_answers": None}
        changed = sum(a != b for a, b in zip(answers, after))
        clone.audit()
        return {"type_valid": True, "accepted": changed == 0, "changed_answers": changed}
    finally:
        clone.close()
        if store.snapshot() != before:
            raise RuntimeError("Preview mutated the original graph")
        store.audit()
