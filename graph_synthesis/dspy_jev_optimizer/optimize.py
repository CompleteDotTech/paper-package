#!/usr/bin/env python3
"""DSPy-assisted outer-loop optimization for TypeSafe AI Jev Choice questions.

DSPy proposes candidate Jev instructions/criteria from TRAIN failures.
Jev evaluates each candidate. VALIDATION chooses the incumbent. HIDDEN TEST
is optional and is read only after the optimization budget is frozen.

Dataset JSONL:
    {"id": "...", "state": {...}, "label": "supports"}
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import dspy
from typesafe_sdk import Choice, TypeSafeClient


@dataclass(frozen=True)
class JevConfig:
    task: str
    instructions: str
    criteria: dict[str, str]


@dataclass
class Prediction:
    example_id: str
    gold: str
    predicted: str
    probabilities: dict[str, float]


class ReviseJevQuestion(dspy.Signature):
    """Propose one precise revision to a TypeSafe Jev Choice question.

    Preserve every label key exactly. Improve only the natural-language
    instructions and label definitions. Keep the judgment atomic and do not
    infer or use hidden-test information.
    """

    task: str = dspy.InputField()
    label_keys: str = dspy.InputField(desc="JSON array; preserve keys exactly")
    current_instructions: str = dspy.InputField()
    current_criteria_json: str = dspy.InputField()
    training_failures_json: str = dspy.InputField()
    improved_instructions: str = dspy.OutputField()
    improved_criteria_json: str = dspy.OutputField(
        desc="JSON object with exactly the same keys as label_keys"
    )


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if "state" not in row or "label" not in row:
                raise ValueError(f"{path}:{line_no}: expected state and label")
            row.setdefault("id", f"{path.stem}:{line_no}")
            rows.append(row)
    if not rows:
        raise ValueError(f"{path}: dataset is empty")
    return rows


def load_config(path: Path) -> JevConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cfg = JevConfig(
        task=str(raw["task"]),
        instructions=str(raw["instructions"]),
        criteria={str(k): str(v) for k, v in raw["criteria"].items()},
    )
    if len(cfg.criteria) < 2:
        raise ValueError("Choice optimization requires at least two criteria")
    return cfg


class JsonCache:
    """Persistent cache so repeated candidates do not repay Jev calls."""

    def __init__(self, path: Path):
        self.path = path
        self.data = {}
        if path.exists():
            self.data = json.loads(path.read_text(encoding="utf-8"))

    def get(self, key: str):
        return self.data.get(key)

    def put(self, key: str, value: dict[str, Any]) -> None:
        self.data[key] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.data, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


def prediction_key(state: Any, cfg: JevConfig) -> str:
    payload = canonical_json(
        {
            "state": state,
            "instructions": cfg.instructions,
            "criteria": cfg.criteria,
        }
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def jev_predict(
    client: TypeSafeClient,
    state: Any,
    cfg: JevConfig,
    cache: JsonCache,
) -> tuple[str, dict[str, float]]:
    key = prediction_key(state, cfg)
    cached = cache.get(key)
    if cached is not None:
        return str(cached["choice"]), {
            k: float(v) for k, v in cached["probabilities"].items()
        }

    response = client.system_one(
        state=state,
        questions={
            "target": Choice(
                instructions=cfg.instructions,
                criteria=cfg.criteria,
            )
        },
    )
    answer = response.answers["target"]
    probabilities = {
        str(k): float(v) for k, v in dict(answer.probabilities).items()
    }
    cache.put(key, {"choice": str(answer.choice), "probabilities": probabilities})
    return str(answer.choice), probabilities


def evaluate(
    client: TypeSafeClient,
    cfg: JevConfig,
    rows: Iterable[dict[str, Any]],
    cache: JsonCache,
) -> tuple[dict[str, float], list[Prediction]]:
    labels = list(cfg.criteria)
    label_set = set(labels)
    predictions = []

    for row in rows:
        gold = str(row["label"])
        if gold not in label_set:
            raise ValueError(f"Unknown gold label {gold!r}; expected {labels}")
        predicted, probabilities = jev_predict(client, row["state"], cfg, cache)
        predictions.append(
            Prediction(str(row["id"]), gold, predicted, probabilities)
        )

    n = len(predictions)
    accuracy = sum(p.gold == p.predicted for p in predictions) / n

    f1_values = []
    for label in labels:
        tp = sum(p.gold == label and p.predicted == label for p in predictions)
        fp = sum(p.gold != label and p.predicted == label for p in predictions)
        fn = sum(p.gold == label and p.predicted != label for p in predictions)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1_values.append(
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )
    macro_f1 = sum(f1_values) / len(f1_values)

    brier = 0.0
    log_loss = 0.0
    eps = 1e-12
    for pred in predictions:
        for label in labels:
            p = max(0.0, min(1.0, float(pred.probabilities.get(label, 0.0))))
            y = 1.0 if pred.gold == label else 0.0
            brier += (p - y) ** 2
        gold_p = max(eps, min(1.0, float(pred.probabilities.get(pred.gold, 0.0))))
        log_loss -= math.log(gold_p)
    brier /= n
    log_loss /= n

    true_counts = {label: sum(p.gold == label for p in predictions) for label in labels}
    pred_counts = {
        label: sum(p.predicted == label for p in predictions) for label in labels
    }
    correct = sum(p.gold == p.predicted for p in predictions)
    numerator = correct * n - sum(
        pred_counts[label] * true_counts[label] for label in labels
    )
    left = n * n - sum(v * v for v in pred_counts.values())
    right = n * n - sum(v * v for v in true_counts.values())
    denominator = math.sqrt(max(0.0, left * right))
    mcc = numerator / denominator if denominator else 0.0

    bins = [[] for _ in range(10)]
    for pred in predictions:
        confidence = max(pred.probabilities.values(), default=0.0)
        index = min(9, int(max(0.0, min(0.999999, confidence)) * 10))
        bins[index].append((confidence, 1.0 if pred.gold == pred.predicted else 0.0))
    ece = 0.0
    for bucket in bins:
        if bucket:
            mean_conf = sum(x[0] for x in bucket) / len(bucket)
            mean_acc = sum(x[1] for x in bucket) / len(bucket)
            ece += len(bucket) / n * abs(mean_conf - mean_acc)

    brier_quality = max(0.0, 1.0 - brier / 2.0)
    mcc_quality = (mcc + 1.0) / 2.0
    composite = (
        0.55 * macro_f1
        + 0.20 * accuracy
        + 0.15 * brier_quality
        + 0.10 * mcc_quality
    )

    return {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "mcc": mcc,
        "brier": brier,
        "log_loss": log_loss,
        "ece": ece,
        "composite": composite,
        "n": n,
    }, predictions


def failure_payload(predictions: list[Prediction], limit: int) -> str:
    failures = [p for p in predictions if p.gold != p.predicted]
    failures.sort(
        key=lambda p: p.probabilities.get(p.predicted, 0.0),
        reverse=True,
    )
    payload = [
        {
            "id": p.example_id,
            "gold": p.gold,
            "predicted": p.predicted,
            "probabilities": p.probabilities,
        }
        for p in failures[:limit]
    ]
    return json.dumps(payload, indent=2, sort_keys=True)


def parse_candidate(base: JevConfig, proposal: Any) -> JevConfig:
    instructions = str(proposal.improved_instructions).strip()
    if not instructions:
        raise ValueError("DSPy returned empty instructions")

    raw = json.loads(str(proposal.improved_criteria_json))
    criteria = {str(k): str(v).strip() for k, v in raw.items()}
    if set(criteria) != set(base.criteria):
        raise ValueError("DSPy changed the fixed label schema")
    if any(not value for value in criteria.values()):
        raise ValueError("DSPy returned an empty criterion")
    criteria = {key: criteria[key] for key in base.criteria}
    return JevConfig(base.task, instructions, criteria)


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--test", type=Path)
    parser.add_argument("--iterations", type=int, default=12)
    parser.add_argument(
        "--selection-metric",
        choices=("accuracy", "macro_f1", "composite"),
        default="accuracy",
    )
    parser.add_argument("--failure-sample", type=int, default=20)
    parser.add_argument("--output", type=Path, default=Path("optimizer-output"))
    parser.add_argument("--cache", type=Path, default=Path(".cache/jev-dspy.json"))
    parser.add_argument(
        "--proposer-model",
        default=os.getenv("DSPY_PROPOSER_MODEL", "openai/gpt-5.4-nano"),
    )
    args = parser.parse_args()

    if args.iterations < 0:
        parser.error("--iterations must be >= 0")

    baseline = load_config(args.config)
    train_rows = load_jsonl(args.train)
    validation_rows = load_jsonl(args.validation)
    cache = JsonCache(args.cache)
    jev = TypeSafeClient()

    revise = None
    if args.iterations:
        dspy.configure(lm=dspy.LM(args.proposer_model))
        revise = dspy.Predict(ReviseJevQuestion)

    incumbent = baseline
    incumbent_validation, _ = evaluate(jev, incumbent, validation_rows, cache)
    ledger = [{
        "iteration": 0,
        "accepted": True,
        "kind": "baseline",
        "config": asdict(incumbent),
        "validation": incumbent_validation,
    }]

    for iteration in range(1, args.iterations + 1):
        train_metrics, train_predictions = evaluate(
            jev, incumbent, train_rows, cache
        )
        assert revise is not None
        proposal = revise(
            task=incumbent.task,
            label_keys=json.dumps(list(incumbent.criteria)),
            current_instructions=incumbent.instructions,
            current_criteria_json=json.dumps(incumbent.criteria, indent=2),
            training_failures_json=failure_payload(
                train_predictions, args.failure_sample
            ),
        )

        try:
            candidate = parse_candidate(incumbent, proposal)
            candidate_validation, _ = evaluate(
                jev, candidate, validation_rows, cache
            )
            accepted = (
                candidate_validation[args.selection_metric]
                > incumbent_validation[args.selection_metric]
            )
            row = {
                "iteration": iteration,
                "accepted": accepted,
                "train_incumbent": train_metrics,
                "candidate": asdict(candidate),
                "validation": candidate_validation,
            }
            if accepted:
                incumbent = candidate
                incumbent_validation = candidate_validation
        except Exception as exc:
            row = {
                "iteration": iteration,
                "accepted": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

        ledger.append(row)
        save_json(args.output / "ledger.json", ledger)
        save_json(args.output / "optimized-config.json", asdict(incumbent))
        save_json(args.output / "validation-metrics.json", incumbent_validation)
        print(
            f"iteration={iteration:02d} accepted={row['accepted']} "
            f"selection_metric={args.selection_metric} "
            f"best={incumbent_validation[args.selection_metric]:.6f}"
        )

    # Deliberately outside the search loop.
    if args.test:
        test_rows = load_jsonl(args.test)
        test_metrics, test_predictions = evaluate(
            jev, incumbent, test_rows, cache
        )
        save_json(args.output / "test-metrics.json", test_metrics)
        save_json(
            args.output / "test-predictions.json",
            [asdict(p) for p in test_predictions],
        )
        print("FINAL_HIDDEN_TEST=" + json.dumps(test_metrics, sort_keys=True))


if __name__ == "__main__":
    main()
