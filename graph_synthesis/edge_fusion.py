"""Exploratory relationship fusion over real, frozen Jev observations.

No network access, new semantic model calls, or production authorization. Gold
labels are separate from the objects accepted by inference and graph export.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from typing import Any, Sequence

import numpy as np

from .core import digest
from .recorded import RecordedJev, ScoredDecision, input_state

TASK = "relation_support"
LABELS = ("SUPPORTS", "REFUTES", "NOT_ENOUGH_INFO")
ARMS = ("baseline_choice", "fewshot_contract", "mean_pool", "agreement_gate", "stacked")
REGULARIZATION = (.01, .1, 1., 10.)
VERSION = "relationship-fusion-v1"


@dataclass(frozen=True)
class Observation:
    id: str
    group: str
    probabilities: tuple[tuple[float, ...] | None, tuple[float, ...] | None]
    request_hashes: tuple[str, str]
    call_ids: tuple[str, str]
    model: str


@dataclass(frozen=True)
class Decision:
    label: str
    probabilities: tuple[float, ...] | None
    request_hash: str
    call_ids: tuple[str, ...]
    reason: str | None = None


def load_split(backend: RecordedJev, split: str) -> tuple[list[Observation], list[str]]:
    """Reconstruct from raw calls, retaining errors; never read gold into features."""
    if split not in {"calibration", "evaluation"}:
        raise ValueError("Unsupported source split")
    observations, gold = [], []
    for row in backend.plan["tasks"][TASK][split]:
        scores = [backend.score(TASK, arm, split, row["id"], input_state(TASK, row))
                  for arm in ARMS[:2]]
        probabilities = tuple(None if s.error else tuple(s.probabilities[k] for k in LABELS)
                              for s in scores)
        observations.append(Observation(row["id"], row["group"], probabilities,
                            tuple(s.request_hash for s in scores),
                            tuple(s.call_id for s in scores), scores[0].model))
        gold.append(row["gold_label"])
    if len({o.id for o in observations}) != len(observations):
        raise ValueError("Duplicate observation IDs")
    return observations, gold


def valid(o: Observation) -> bool:
    return all(p is not None for p in o.probabilities)


def fold_for(group: str) -> int:
    return int(hashlib.sha256((VERSION + ":" + group).encode()).hexdigest(), 16) % 5


def feature_vector(o: Observation) -> list[float]:
    if not valid(o):
        raise ValueError("Failed observations have no feature vector")
    result = []
    for p in o.probabilities:
        if len(p) != 3 or any(type(v) not in (int, float) or not math.isfinite(v)
                             or not 0 <= v <= 1 for v in p) or not math.isclose(sum(p), 1, abs_tol=1e-6):
            raise ValueError("Invalid probability vector")
        result.extend(math.log(max(v, 1e-6)) for v in p)
    return result


def softmax(logits: np.ndarray) -> np.ndarray:
    values = np.exp(logits - np.max(logits, axis=1, keepdims=True))
    return values / values.sum(axis=1, keepdims=True)


def objective_gradient(x: np.ndarray, y: np.ndarray, w: np.ndarray,
                       regularization: float) -> tuple[float, np.ndarray]:
    logits = x @ w
    shifted = logits - logits.max(axis=1, keepdims=True)
    loss = np.mean(np.log(np.exp(shifted).sum(axis=1)) - shifted[np.arange(len(y)), y])
    penalty = w.copy()
    penalty[-1] = 0  # Intercept is not penalized.
    loss += regularization * .5 * np.square(penalty).sum()
    residual = softmax(logits)
    residual[np.arange(len(y)), y] -= 1
    return float(loss), x.T @ residual / len(y) + regularization * penalty


def fit_model(observations: Sequence[Observation], gold: Sequence[str],
              regularization: float) -> dict[str, Any]:
    if len(observations) != len(gold) or not observations:
        raise ValueError("Nonempty aligned training data required")
    if not math.isfinite(regularization) or regularization <= 0:
        raise ValueError("Positive regularization required")
    if any(label not in LABELS for label in gold):
        raise ValueError("Unknown gold label")
    if set(gold) != set(LABELS):
        raise ValueError("Training fold must contain every label")
    raw = np.asarray([feature_vector(o) for o in observations], dtype=float)
    mean, scale = raw.mean(axis=0), raw.std(axis=0)
    scale = np.where(scale < 1e-8, 1., scale)
    x = np.column_stack(((raw - mean) / scale, np.ones(len(raw))))
    y = np.asarray([LABELS.index(label) for label in gold])
    w = np.zeros((x.shape[1], 3))
    step = 1 / (.5 * np.linalg.eigvalsh(x.T @ x / len(x))[-1] + regularization)
    initial, _ = objective_gradient(x, y, w, regularization)
    for iteration in range(1, 12001):
        loss, gradient = objective_gradient(x, y, w, regularization)
        norm = float(np.linalg.norm(gradient))
        if norm <= 1e-7:
            break
        w -= step * gradient
    final, gradient = objective_gradient(x, y, w, regularization)
    norm = float(np.linalg.norm(gradient))
    if not np.isfinite(w).all() or final > initial + 1e-10 or norm > 1e-6:
        raise ValueError("Optimizer did not converge within its declared budget")
    # Documented quantization makes derived hashes and graph replays portable.
    return {"version": VERSION, "regularization": regularization,
            "mean": mean.round(8).tolist(), "scale": scale.round(8).tolist(),
            "weights": w.round(8).tolist(), "iterations": iteration,
            "initial_objective": round(initial, 10), "final_objective": round(final, 10),
            "gradient_norm": round(norm, 10), "converged": norm <= 1e-6,
            "training_ids": sorted(o.id for o in observations),
            "training_groups": sorted({o.group for o in observations}),
            "training_fingerprint": digest([{
                "id": o.id, "group": o.group, "probabilities": o.probabilities,
                "requests": o.request_hashes, "calls": o.call_ids, "gold": g}
                for o, g in zip(observations, gold)])}


def model_identity(model: dict[str, Any]) -> str:
    """Bind the deployed transform, not incidental optimizer diagnostics."""
    keys = ("version", "regularization", "mean", "scale", "weights", "training_ids", "training_groups", "training_fingerprint")
    return digest({key: model[key] for key in keys})


def model_probability(o: Observation, model: dict[str, Any]) -> tuple[float, ...]:
    if model["version"] != VERSION:
        raise ValueError("Unsupported model artifact")
    try:
        arrays = [np.asarray(model[k], dtype=float) for k in ("mean", "scale", "weights")]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Malformed fitted model") from exc
    if [a.shape for a in arrays] != [(6,), (6,), (7, 3)] or not all(np.isfinite(a).all() for a in arrays) or (arrays[1] <= 0).any():
        raise ValueError("Invalid fitted model dimensions, scale, or finite values")
    raw = np.asarray(feature_vector(o))
    x = np.append((raw - np.asarray(model["mean"])) / np.asarray(model["scale"]), 1.)
    p = softmax((x @ np.asarray(model["weights"]))[None, :])[0]
    # Eight decimal places, adjusting argmax to preserve the probability sum.
    values = [round(float(v), 8) for v in p]
    largest = int(np.argmax(p))
    values[largest] = round(1 - sum(v for i, v in enumerate(values) if i != largest), 8)
    return tuple(values)


def predict(o: Observation, arm: str, model: dict[str, Any] | None = None) -> Decision:
    """No gold, text-label heuristics, evaluation IDs, or evaluator state accepted."""
    if arm not in ARMS:
        raise ValueError("Unknown experimental arm")
    if arm in ARMS[:2]:
        i = ARMS.index(arm)
        p = o.probabilities[i]
        label = "ERROR" if p is None else LABELS[max(range(3), key=p.__getitem__)]
        return Decision(label, p, o.request_hashes[i], (o.call_ids[i],),
                        "invalid original response" if p is None else None)
    if arm == "stacked" and model is None:
        raise ValueError("Stacked inference requires a fitted artifact")
    fingerprint = digest({"version": VERSION, "arm": arm, "requests": o.request_hashes,
                          "calls": o.call_ids, "probabilities": o.probabilities, "source_model": o.model,
                          "model": model_identity(model) if arm == "stacked" else None})
    if not valid(o):
        return Decision("ERROR", None, fingerprint, o.call_ids, "invalid constituent response")
    for p in o.probabilities:
        # Validate even the non-fitted arms at the inference boundary.
        if len(p) != 3 or any(type(v) not in (int, float) or not math.isfinite(v)
                             or not 0 <= v <= 1 for v in p) or not math.isclose(sum(p), 1, abs_tol=1e-6):
            raise ValueError("Invalid probability vector")
    a, b = o.probabilities
    if arm == "agreement_gate" and max(range(3), key=a.__getitem__) != max(range(3), key=b.__getitem__):
        return Decision("ABSTAIN", None, fingerprint, o.call_ids, "constituent label disagreement")
    p = model_probability(o, model) if arm == "stacked" else tuple((x + y) / 2 for x, y in zip(a, b))
    return Decision(LABELS[max(range(3), key=p.__getitem__)], p, fingerprint, o.call_ids)


def metrics(gold: Sequence[str], decisions: Sequence[Decision]) -> dict[str, Any]:
    if len(gold) != len(decisions) or any(label not in LABELS for label in gold):
        raise ValueError("Aligned canonical gold labels required")
    n = len(gold)
    confusion = {label: {pred: 0 for pred in (*LABELS, "ERROR", "ABSTAIN")} for label in LABELS}
    for truth, decision in zip(gold, decisions):
        confusion[truth][decision.label] += 1
    f1s, relations = [], {}
    for label in LABELS:
        tp = confusion[label][label]
        gold_n = sum(confusion[label].values())
        pred_n = sum(row[label] for row in confusion.values())
        f1s.append(2 * tp / (gold_n + pred_n) if gold_n + pred_n else 0.)
        if label != LABELS[2]:
            relations[label] = {"accepted": pred_n, "correct": tp, "incorrect": pred_n-tp,
                "precision": tp / pred_n if pred_n else None, "recall": tp / gold_n if gold_n else None}
    accepted = sum(v["accepted"] for v in relations.values())
    correct = sum(v["correct"] for v in relations.values())
    gold_edges = sum(g != LABELS[2] for g in gold)
    return {"n": n, "accuracy": sum(g == d.label for g, d in zip(gold, decisions)) / n if n else None,
        "macro_f1": sum(f1s) / 3, "errors": sum(d.label == "ERROR" for d in decisions),
        "abstentions": sum(d.label == "ABSTAIN" for d in decisions), "confusion": confusion,
        "edges": {"accepted": accepted, "correct": correct, "incorrect": accepted-correct,
            "precision": correct / accepted if accepted else None,
            "recall": correct / gold_edges if gold_edges else None,
            "coverage": accepted / n if n else None}, "relations": relations}


def train_policy(observations: Sequence[Observation], gold: Sequence[str], *, split: str) -> dict[str, Any]:
    if split != "calibration":
        raise ValueError("Selection must use calibration, never evaluation")
    if len(observations) != len(gold) or len({o.id for o in observations}) != len(observations):
        raise ValueError("Aligned unique calibration rows required")
    folds = {o.group: fold_for(o.group) for o in observations}
    if set(folds.values()) != set(range(5)):
        raise ValueError("Five nonempty component folds required")
    candidates = []
    for penalty in REGULARIZATION:
        oof = [None] * len(observations)
        diagnostics = []
        for fold in range(5):
            training = [i for i, o in enumerate(observations) if folds[o.group] != fold and valid(o)]
            held = [i for i, o in enumerate(observations) if folds[o.group] == fold]
            model = fit_model([observations[i] for i in training], [gold[i] for i in training], penalty)
            diagnostics.append({"fold": fold, "train_n": len(training), "test_n": len(held),
                                "iterations": model["iterations"], "converged": model["converged"]})
            for i in held:
                oof[i] = predict(observations[i], "stacked", model)
        scored = metrics(gold, oof)
        losses = [-math.log(max(d.probabilities[LABELS.index(g)], 1e-15))
                  for g, d in zip(gold, oof) if d.probabilities is not None]
        candidates.append({"regularization": penalty, "macro_f1": scored["macro_f1"],
            "nll": sum(losses) / len(losses), "errors": scored["errors"], "folds": diagnostics,
            "oof": [{"id": o.id, "label": d.label, "p": d.probabilities}
                    for o, d in zip(observations, oof)]})
    selected = min(candidates, key=lambda c: (-c["macro_f1"], c["nll"], -c["regularization"]))
    kept = [i for i, o in enumerate(observations) if valid(o)]
    model = fit_model([observations[i] for i in kept], [gold[i] for i in kept], selected["regularization"])
    return {"source_split": split, "folds": folds, "candidates": candidates,
            "selected_regularization": selected["regularization"], "model": model,
            "model_hash": model_identity(model), "valid_training_n": len(kept)}


def rank_edges(observations: Sequence[Observation], decisions: Sequence[Decision],
               relation: str | None = None) -> list[int]:
    if len(observations) != len(decisions) or relation not in (None, *LABELS[:2]):
        raise ValueError("Aligned decisions and a supported relation required")
    indices = [i for i, d in enumerate(decisions) if d.label in LABELS[:2]
               and (relation is None or d.label == relation)]
    return sorted(indices, key=lambda i: (-decisions[i].probabilities[LABELS.index(decisions[i].label)],
                                         observations[i].id))


def budget_metrics(gold: Sequence[str], observations: Sequence[Observation],
                   decisions: Sequence[Decision], k: int, relation: str | None = None) -> dict[str, Any]:
    ranked = rank_edges(observations, decisions, relation)
    if type(k) is not int or not 0 <= k <= len(ranked):
        raise ValueError("Edge budget unavailable")
    chosen = ranked[:k]
    true = sum(gold[i] == decisions[i].label for i in chosen)
    boundary_ties = 0
    if k:
        last = decisions[chosen[-1]]
        score = last.probabilities[LABELS.index(last.label)]
        boundary_ties = sum(decisions[i].probabilities[LABELS.index(decisions[i].label)] == score for i in ranked)
    return {"accepted": k, "correct": true, "incorrect": k-true, "precision": true/k if k else None,
            "boundary_ties": boundary_ties, "selected_ids": [observations[i].id for i in chosen]}
