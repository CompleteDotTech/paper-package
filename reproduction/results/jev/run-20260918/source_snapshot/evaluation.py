"""Task contracts and denominator-explicit metrics for decision experiments.

Brier uses the full sum over classes (range 0..2), not the binary one-coordinate
convention. Log loss clips only the gold probability at 1e-15. Service failures
count against operational accuracy and coverage, never enter probability scores.
"""

from collections import Counter
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from numbers import Real
from pathlib import Path
import platform
import random
import subprocess
import time
from typing import Any, Dict, List, Optional, Sequence


RELATION_LABELS = ("SUPPORTS", "REFUTES", "NOT_ENOUGH_INFO")
ER_LABELS = ("same", "different")
LOG_LOSS_EPSILON = 1e-15
NORMALIZATION_TOLERANCE = 1e-6


class DiagnosticBackend:
    """Explicitly synthetic canonical-label baseline with an isolated random seed."""

    def __init__(self, seed=0, fixed_confidence=None):
        if fixed_confidence is not None and not 0 <= fixed_confidence <= 1:
            raise ValueError("fixed_confidence must be in [0, 1]")
        self.seed = seed
        self.fixed_confidence = fixed_confidence
        self.random = random.Random(seed)

    def name(self):
        return "diagnostic-random" if self.fixed_confidence is None else f"diagnostic-fixed-{self.fixed_confidence:g}"

    def version(self):
        return "canonical-diagnostic-v1"

    def decide(self, request):
        from pgc.decision import DecisionResponse
        labels = request.labels or request.options
        if not labels:
            return DecisionResponse(request.request_id, {}, error="Diagnostic baseline requires explicit labels", execution_mode="mock")
        if self.fixed_confidence is None:
            weights = [self.random.uniform(0.1, 1.0) for _ in labels]
            distribution = {label: weight / sum(weights) for label, weight in zip(labels, weights)}
        elif len(labels) == 1:
            distribution = {labels[0]: 1.0}
        else:
            distribution = {label: (self.fixed_confidence if i == 0 else (1 - self.fixed_confidence) / (len(labels) - 1))
                            for i, label in enumerate(labels)}
        return DecisionResponse(
            request.request_id, distribution, execution_mode="mock",
            confidence=max(distribution.values()), tokens_used={"input": 0, "output": 0},
            metadata={"seed": self.seed, "fixed_confidence": self.fixed_confidence,
                      "description": "Synthetic canonical-label control; no semantic inference"},
        )

    def batch_decide(self, requests):
        return [self.decide(request) for request in requests]

    def estimate_cost(self, requests):
        return {"tokens": 0, "estimated_cost_usd": None, "note": "Synthetic diagnostic control"}


def validate_distribution(distribution, labels: Sequence[str]) -> Dict[str, float]:
    """Validate without repairing, renormalizing, or translating backend output."""
    labels = tuple(labels)
    if not labels or len(labels) != len(set(labels)):
        raise ValueError("Expected labels must be nonempty and unique")
    if not isinstance(distribution, dict) or set(distribution) != set(labels):
        raise ValueError(f"Distribution keys must be exactly {list(labels)}")
    clean = {}
    for label in labels:
        value = distribution[label]
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError(f"Probability for {label} must be numeric")
        value = float(value)
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"Probability for {label} must be finite and in [0, 1]")
        clean[label] = value
    if not math.isclose(sum(clean.values()), 1.0, rel_tol=0.0, abs_tol=NORMALIZATION_TOLERANCE):
        raise ValueError("Probabilities must sum to one")
    return clean


def brier_score(distribution, gold_label, labels=None):
    probabilities = validate_distribution(distribution, labels or tuple(distribution))
    if gold_label not in probabilities:
        raise ValueError("Gold label is outside the semantic label set")
    return sum((p - float(label == gold_label)) ** 2 for label, p in probabilities.items())


def log_loss(distribution, gold_label, labels=None):
    probabilities = validate_distribution(distribution, labels or tuple(distribution))
    if gold_label not in probabilities:
        raise ValueError("Gold label is outside the semantic label set")
    return -math.log(max(probabilities[gold_label], LOG_LOSS_EPSILON))


def json_safe(value):
    """Preserve invalid raw values explicitly while writing standards-compliant JSON."""
    if is_dataclass(value):
        return json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return f"<nonfinite:{value}>"
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "value"):
        return json_safe(value.value)
    if isinstance(value, Real):
        return json_safe(float(value))
    return str(value)


@dataclass
class EvaluationResult:
    # The leading fields retain the former benchmark result constructor surface.
    example_id: str
    backend_name: str
    backend_version: str
    decision_primitive: str
    distribution: Dict[str, float]
    confidence: Optional[float]
    gold_label: str
    predicted_label: str
    correct: bool
    predicted_confidence: float
    latency_ms: Optional[float]
    tokens_used: Optional[Dict[str, int]]
    labels: List[str] = field(default_factory=list)
    semantic_eligible: bool = True
    service_success: bool = False
    error: Optional[str] = None
    raw_error: Optional[str] = None
    validation_error: Optional[str] = None
    execution_mode: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_distribution: Any = None
    reported_confidence: Optional[float] = None
    wall_latency_ms: Optional[float] = None
    request_data: Dict[str, Any] = field(default_factory=dict)

    def brier_score(self):
        if not self.semantic_eligible or not self.service_success:
            return None
        return brier_score(self.distribution, self.gold_label, self.labels)

    def log_loss(self):
        if not self.semantic_eligible or not self.service_success:
            return None
        return log_loss(self.distribution, self.gold_label, self.labels)

    def to_dict(self):
        data = asdict(self)
        data["backend"] = self.backend_name
        data["brier_score"] = self.brier_score()
        data["log_loss"] = self.log_loss()
        return json_safe(data)


def evaluate_request(example_id, gold_label, backend, request, labels, *, excluded_gold_labels=(), dry_run=False):
    """Invoke safely, validate task output, and retain operational failure evidence."""
    from pgc.decision import DecisionResponse

    labels = tuple(labels)
    if gold_label not in labels and gold_label not in excluded_gold_labels:
        raise ValueError(f"Unknown gold label {gold_label!r}")
    started = time.perf_counter()
    try:
        if dry_run:
            response = DecisionResponse(
                request_id=request.request_id,
                distribution={label: 1 / len(labels) for label in labels},
                execution_mode="mock",
                metadata={"dry_run": True},
            )
        else:
            response = backend.decide(request)
    except Exception as exc:
        response = DecisionResponse(
            request_id=request.request_id, distribution={},
            error=f"{type(exc).__name__}: {exc}", execution_mode="unavailable",
            metadata={"raised_exception": type(exc).__name__},
        )
    wall_latency = (time.perf_counter() - started) * 1000
    raw_error = getattr(response, "error", None)
    raw_distribution = getattr(response, "distribution", None)
    validation_error = None
    distribution = {}
    if not raw_error:
        try:
            if getattr(response, "request_id", None) != request.request_id:
                raise ValueError("Response request_id does not match the request")
            distribution = validate_distribution(raw_distribution, labels)
        except (TypeError, ValueError) as exc:
            validation_error = str(exc)
    error = str(raw_error) if raw_error else validation_error
    success = error is None
    predicted_label = max(distribution, key=distribution.get) if success else "ERROR"
    confidence = distribution[predicted_label] if success else None
    eligible = gold_label in labels
    try:
        version = backend.version()
    except Exception as exc:
        version = f"unavailable: {type(exc).__name__}"
    metadata = getattr(response, "metadata", {}) or {}
    if not isinstance(metadata, dict):
        metadata = {"invalid_metadata": json_safe(metadata)}
    return EvaluationResult(
        example_id=example_id, backend_name=backend.name(), backend_version=version,
        decision_primitive=getattr(request.primitive, "value", str(request.primitive)),
        distribution=distribution, confidence=confidence, gold_label=gold_label,
        predicted_label=predicted_label,
        correct=bool(eligible and success and predicted_label == gold_label),
        predicted_confidence=confidence if confidence is not None else 0.0,
        latency_ms=getattr(response, "latency_ms", None),
        tokens_used=getattr(response, "tokens_used", None), labels=list(labels),
        semantic_eligible=eligible, service_success=success,
        error=error, raw_error=str(raw_error) if raw_error else None,
        validation_error=validation_error,
        execution_mode=getattr(response, "execution_mode", None) or "unknown",
        metadata=json_safe(metadata), raw_distribution=json_safe(raw_distribution),
        reported_confidence=getattr(response, "confidence", None),
        wall_latency_ms=wall_latency,
        request_data=json_safe(request),
    )


def _mean(values):
    values = list(values)
    return sum(values) / len(values) if values else None


def _classification(rows, labels):
    confusion = {gold: {predicted: 0 for predicted in (*labels, "ERROR")} for gold in labels}
    for row in rows:
        confusion[row.gold_label][row.predicted_label if row.predicted_label in labels else "ERROR"] += 1
    per_class = {}
    for label in labels:
        tp = confusion[label][label]
        support = sum(confusion[label].values())
        predicted = sum(confusion[gold][label] for gold in labels)
        precision = tp / predicted if predicted else 0.0
        recall = tp / support if support else None
        f1 = 2 * tp / (support + predicted) if support + predicted else 0.0
        per_class[label] = {"support": support, "precision": precision, "recall": recall, "f1": f1}
    return {
        "n_examples": len(rows),
        "accuracy": sum(row.correct for row in rows) / len(rows) if rows else None,
        "macro_f1": _mean(item["f1"] for item in per_class.values()) if rows else None,
        "balanced_accuracy": _mean(item["recall"] for item in per_class.values() if item["recall"] is not None),
        "confusion": confusion, "per_class": per_class,
    }


def summarize_results(results, labels=None):
    if not results:
        return {}
    labels = tuple(labels or results[0].labels)
    eligible = [row for row in results if row.semantic_eligible]
    valid = [row for row in eligible if row.service_success]
    excluded = [row for row in results if not row.semantic_eligible]
    operational = _classification(eligible, labels)
    conditional = _classification(valid, labels)
    reliability = []
    for index in range(10):
        selected = [row for row in valid if min(9, int(row.confidence * 10)) == index]
        reliability.append({"lower": index / 10, "upper": (index + 1) / 10,
                            "count": len(selected), "mean_confidence": _mean(row.confidence for row in selected),
                            "accuracy": _mean(float(row.correct) for row in selected)})
    ece = sum(item["count"] * abs(item["mean_confidence"] - item["accuracy"])
              for item in reliability if item["count"]) / len(valid) if valid else None
    latency = [row.wall_latency_ms for row in results if isinstance(row.wall_latency_ms, Real) and math.isfinite(row.wall_latency_ms)]
    token_rows = [row for row in results if isinstance(row.tokens_used, dict)
                  and all(isinstance(row.tokens_used.get(key), int) and row.tokens_used[key] >= 0 for key in ("input", "output"))]
    total_input = sum(row.tokens_used["input"] for row in token_rows)
    total_output = sum(row.tokens_used["output"] for row in token_rows)
    thresholds = []
    for threshold in (0.0, 0.5, 0.7, 0.8, 0.9, 0.95):
        selected = [row for row in valid if row.confidence >= threshold]
        thresholds.append({"threshold": threshold, "accepted_count": len(selected),
                           "coverage": len(selected) / len(eligible) if eligible else None,
                           "accuracy": _mean(float(row.correct) for row in selected)})
    return {
        "backend": results[0].backend_name, "n_examples": len(results),
        "n_semantic_examples": len(eligible), "n_excluded_gold": len(excluded),
        "excluded_gold_labels": dict(Counter(row.gold_label for row in excluded)),
        "excluded_gold_predictions": dict(Counter(row.predicted_label for row in excluded)),
        "n_service_success": sum(row.service_success for row in results),
        "n_semantic_service_success": len(valid),
        "n_errors": sum(not row.service_success for row in results),
        "n_validation_errors": sum(row.validation_error is not None for row in results),
        "service_success_rate": sum(row.service_success for row in results) / len(results),
        "semantic_coverage": len(valid) / len(eligible) if eligible else None,
        "accuracy": operational["accuracy"], "operational_accuracy": operational["accuracy"],
        "conditional_accuracy": conditional["accuracy"],
        "macro_f1": operational["macro_f1"], "balanced_accuracy": operational["balanced_accuracy"],
        "confusion": operational["confusion"], "operational": operational, "conditional": conditional,
        "brier_score": _mean(row.brier_score() for row in valid),
        "brier_convention": "sum_over_all_classes", "log_loss": _mean(row.log_loss() for row in valid),
        "log_loss_epsilon": LOG_LOSS_EPSILON,
        "n_log_loss_clipped": sum(row.distribution[row.gold_label] < LOG_LOSS_EPSILON for row in valid),
        "probability_score_denominator": len(valid),
        "mean_confidence": _mean(row.confidence for row in valid),
        "ece_10_bins": ece, "reliability_bins": reliability, "selective_accuracy": thresholds,
        "mean_latency_ms": _mean(latency), "latency_source": "measured_perf_counter_wall_time",
        "latency_denominator": len(latency), "total_input_tokens": total_input if token_rows else None,
        "total_output_tokens": total_output if token_rows else None,
        "total_tokens": total_input + total_output if token_rows else None,
        "token_usage_denominator": len(token_rows),
        "tokens_per_example": (total_input + total_output) / len(token_rows) if token_rows else None,
        "execution_modes": dict(Counter(row.execution_mode for row in results)),
        "metric_notes": ["Operational metrics include failed eligible requests as errors.",
                         "Conditional/probabilistic metrics use valid eligible responses only.",
                         "Macro F1 includes every canonical label; balanced accuracy averages labels with gold support.",
                         "Token mean includes only rows with both reported token counts; absent usage is unknown."],
    }


def save_benchmark_artifact(dataset, examples, results, summaries, *, output_path=None, seed=0, manifest=None):
    """Write a new artifact exclusively; historical results are never overwritten."""
    now = datetime.now(timezone.utc)
    path = Path(output_path) if output_path else Path("results") / f"{dataset}_{now.strftime('%Y%m%dT%H%M%S%fZ')}.json"
    data_json = json.dumps(json_safe(examples), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, timeout=5, check=True).stdout.strip())
    except (OSError, subprocess.SubprocessError):
        revision, dirty = None, None
    artifact = {
        "schema_version": 2, "timestamp": now.isoformat(), "dataset": dataset,
        "n_examples": len(examples), "n_backends": len(summaries), "seed": seed,
        "manifest": {"repository_commit": revision, "repository_dirty": dirty,
                     "python_version": platform.python_version(),
                     "dataset_sha256": hashlib.sha256(data_json.encode("utf-8")).hexdigest(),
                     "dataset_examples": json_safe(examples), "supplied": json_safe(manifest or {})},
        "backends": summaries, "raw_results": [row.to_dict() for row in results],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(artifact, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")
    return path


def group_split(group_ids, *, seed=0, calibration_fraction=0.2):
    """Deterministic group-disjoint fit/calibration indices, independent of labels."""
    if not 0 < calibration_fraction < 1:
        raise ValueError("calibration_fraction must lie strictly between zero and one")
    groups = sorted(set(group_ids))
    if len(groups) < 2:
        raise ValueError("At least two independent groups are required")
    random.Random(seed).shuffle(groups)
    count = max(1, min(len(groups) - 1, round(len(groups) * calibration_fraction)))
    calibration = set(groups[:count])
    return ([i for i, group in enumerate(group_ids) if group not in calibration],
            [i for i, group in enumerate(group_ids) if group in calibration])
