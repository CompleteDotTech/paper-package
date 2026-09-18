"""Auditable, bounded prompt search. No SDK imports or network access at import time."""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

VERSION = 1


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def parse_json(text: str) -> Any:
    def reject(value):
        raise ValueError("Non-finite JSON number")
    return json.loads(text, object_pairs_hook=_pairs, parse_constant=reject)


def read_json(path: Path) -> Any:
    return parse_json(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    """Replace atomically; never expose a partially written checkpoint."""
    data = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as f:
        temporary = Path(f.name)
        f.write(data)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def text(value: Any, field: str, limit: int = 16000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"Invalid {field}")
    return value


@dataclass(frozen=True)
class JevConfig:
    task: str
    instructions: str
    criteria: dict[str, str]

    @classmethod
    def from_dict(cls, value: Any, base: JevConfig | None = None) -> JevConfig:
        if not isinstance(value, dict) or set(value) != {"task", "instructions", "criteria"}:
            raise ValueError("Expected task, instructions, and criteria only")
        criteria = value["criteria"]
        if not isinstance(criteria, dict) or not 2 <= len(criteria) <= 64:
            raise ValueError("Expected 2..64 criteria")
        criteria = {text(k, "label", 128): text(v, "criterion") for k, v in criteria.items()}
        if base is not None:
            if value["task"] != base.task or set(criteria) != set(base.criteria):
                raise ValueError("Candidate changed task or fixed label schema")
            criteria = {k: criteria[k] for k in base.criteria}
        return cls(text(value["task"], "task"), text(value["instructions"], "instructions"), criteria)

    def question(self) -> dict:
        return {"type": "choice", "instructions": self.instructions, "criteria": self.criteria}

    def fingerprint(self) -> str:
        # Keep option order: its effect on a model must not be assumed away.
        return digest([self.task, self.instructions, list(self.criteria.items())])


@dataclass(frozen=True)
class Example:
    id: str
    state: Any
    label: str
    group_id: str | None = None


def load_data(path: Path, labels: dict[str, str]) -> list[Example]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = parse_json(line)
        if not isinstance(item, dict) or not {"id", "state", "label"} <= set(item):
            raise ValueError(f"{path.name}:{number}: expected id, state, label")
        if set(item) - {"id", "state", "label", "group_id"}:
            raise ValueError("Unknown dataset field")
        if not isinstance(item["state"], (str, dict, list)) or not item["state"]:
            raise ValueError("State must be nonempty text, object, or array")
        canonical(item["state"])
        label = text(item["label"], "label", 128)
        if label not in labels:
            raise ValueError("Unknown ground-truth label")
        group = item.get("group_id")
        rows.append(Example(text(item["id"], "id", 512), item["state"], label,
                            text(group, "group_id", 512) if group is not None else None))
    fingerprints(rows)
    return rows


def fingerprints(rows: list[Example]) -> dict[str, list[str]]:
    if not rows:
        raise ValueError("Dataset is empty")
    ids = [digest(row.id) for row in rows]
    states = [digest(row.state) for row in rows]
    groups = [digest(row.group_id) for row in rows if row.group_id is not None]
    if len(ids) != len(set(ids)) or len(states) != len(set(states)):
        raise ValueError("Duplicate ID or state within split")
    if groups and len(groups) != len(rows):
        raise ValueError("group_id must be present on every row or none")
    return {"ids": sorted(ids), "states": sorted(states), "groups": sorted(set(groups))}


def disjoint(left: dict, right: dict) -> None:
    if bool(left["groups"]) != bool(right["groups"]):
        raise ValueError("All splits must use the same group_id policy")
    for field in ("ids", "states", "groups"):
        if set(left[field]) & set(right[field]):
            raise ValueError(f"Split leakage: overlapping {field}")


def validate_answer(answer: dict, labels: dict[str, str]) -> dict[str, float]:
    choice, probabilities = answer.get("choice"), answer.get("probabilities")
    if choice not in labels or not isinstance(probabilities, dict) or set(probabilities) != set(labels):
        raise ValueError("Answer does not match fixed label schema")
    for p in probabilities.values():
        if isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) or not 0 <= p <= 1:
            raise ValueError("Invalid probability")
    if not math.isclose(sum(probabilities.values()), 1, rel_tol=0, abs_tol=1e-6):
        raise ValueError("Probabilities do not sum to one")
    return {label: float(probabilities[label]) for label in labels}


def metrics(predictions: list[dict], labels: dict[str, str]) -> dict:
    if not predictions:
        raise ValueError("Cannot score an empty evaluation")
    confusion = {gold: {pred: 0 for pred in labels} for gold in labels}
    brier = log_loss = ece = 0.0
    bins: list[list[tuple[float, int]]] = [[] for _ in range(10)]
    for row in predictions:
        probs = validate_answer(row, labels)
        gold, choice = row["gold"], row["choice"]
        if gold not in labels:
            raise ValueError("Unknown gold label")
        confusion[gold][choice] += 1
        brier += sum((probs[label] - int(label == gold)) ** 2 for label in labels)
        log_loss -= math.log(max(1e-15, probs[gold]))
        confidence = probs[choice]  # NOT Jev's separate concentration/confidence field.
        bins[min(9, int(confidence * 10))].append((confidence, int(choice == gold)))
    n = len(predictions)
    correct = sum(confusion[k][k] for k in labels)
    truth = {k: sum(confusion[k].values()) for k in labels}
    pred = {k: sum(confusion[g][k] for g in labels) for k in labels}
    f1 = sum(2 * confusion[k][k] / (truth[k] + pred[k]) if truth[k] + pred[k] else 0 for k in labels) / len(labels)
    denominator = math.sqrt((n*n - sum(v*v for v in truth.values())) * (n*n - sum(v*v for v in pred.values())))
    mcc = (correct*n - sum(truth[k]*pred[k] for k in labels)) / denominator if denominator else 0.0
    for bucket in bins:
        if bucket:
            ece += abs(sum(p for p, _ in bucket) - sum(y for _, y in bucket)) / n
    return {"n": n, "accuracy": correct/n, "macro_f1": f1, "mcc": mcc,
            "brier": brier/n, "log_loss": log_loss/n, "ece": ece,
            "composite": .55*f1 + .20*correct/n + .15*(1-brier/n/2) + .10*(mcc+1)/2,
            "confusion_matrix": confusion, "class_counts": truth}


class Backend(Protocol):
    identity: dict
    def predict(self, config: JevConfig, state: Any) -> dict: ...


class Proposer(Protocol):
    identity: dict
    def propose(self, config: JevConfig, feedback: list[dict], iteration: int, history: list[dict]) -> dict: ...


class BudgetExhausted(RuntimeError):
    pass


class Cache:
    """SQLite transactions plus content hashes detect damaged cached responses."""
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=30)
        self.db.execute("CREATE TABLE IF NOT EXISTS responses (key TEXT PRIMARY KEY, value TEXT NOT NULL, digest TEXT NOT NULL)")

    def get(self, key: str) -> dict | None:
        row = self.db.execute("SELECT value, digest FROM responses WHERE key=?", (key,)).fetchone()
        if row is None:
            return None
        result = parse_json(row[0])
        if digest(result) != row[1]:
            raise ValueError("Cache integrity failure")
        return result

    def put(self, key: str, value: dict) -> None:
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO responses VALUES (?, ?, ?)", (key, canonical(value), digest(value)))

    def close(self) -> None:
        self.db.close()


class Evaluator:
    def __init__(self, backend: Backend, cache: Cache, output: Path, max_calls: int):
        if max_calls < 1:
            raise ValueError("max_calls must be positive")
        self.backend, self.cache, self.output = backend, cache, output
        self.max_calls, self.calls, self.cache_hits = max_calls, 0, 0
        self.usage = {"input_tokens": 0, "output_tokens": 0}

    def event(self, event: dict) -> None:
        self.output.mkdir(parents=True, exist_ok=True)
        with (self.output / "calls.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(canonical(event) + "\n")

    def evaluate(self, config: JevConfig, rows: list[Example], phase: str) -> tuple[dict, list[dict]]:
        predictions = []
        for row in rows:
            key = digest({"schema": VERSION, "backend": self.backend.identity,
                          "config": config.fingerprint(), "state": row.state})
            response = self.cache.get(key)
            cached = response is not None
            if cached:
                self.cache_hits += 1
            else:
                if self.calls >= self.max_calls:
                    raise BudgetExhausted("Jev logical-call budget exhausted")
                self.calls += 1
                self.event({"event": "request", "key": key, "phase": phase,
                            "state": row.state, "question": config.question(), "backend": self.backend.identity})
                try:
                    response = self.backend.predict(config, parse_json(canonical(row.state)))
                    validate_answer(response, config.criteria)
                    if response.get("model") != self.backend.identity["model"]:
                        raise ValueError("Returned Jev model differs from pinned model")
                    for token in self.usage:
                        count = response.get("usage", {}).get(token, 0)
                        if type(count) is not int or count < 0:
                            raise ValueError("Invalid token usage")
                        self.usage[token] += count
                    self.cache.put(key, response)
                except Exception as exc:
                    self.event({"event": "request_failed", "key": key, "error_type": type(exc).__name__})
                    raise
            validate_answer(response, config.criteria)
            if response.get("model") != self.backend.identity["model"]:
                raise ValueError("Cached model mismatch")
            self.event({"event": "cache_hit" if cached else "response", "key": key, "phase": phase, "response": response})
            predictions.append({"id": row.id, "gold": row.label, "choice": response["choice"],
                                "probabilities": response["probabilities"], "request_sha256": key})
        return metrics(predictions, config.criteria), predictions

    def summary(self) -> dict:
        return {"logical_calls": self.calls, "cache_hits": self.cache_hits,
                "successful_uncached_usage": self.usage.copy(), "cost_usd": None}


def feedback(rows: list[Example], predictions: list[dict], limit: int) -> list[dict]:
    if limit < 1:
        raise ValueError("feedback limit must be positive")
    states = {r.id: r.state for r in rows}
    ranked = sorted(predictions, key=lambda p: (p["choice"] == p["gold"], p["probabilities"][p["gold"]]))
    result = []
    for pred in ranked[:limit]:
        value = canonical(states[pred["id"]])
        result.append({"id": pred["id"], "state": states[pred["id"]] if len(value) <= 6000 else value[:6000],
                       "state_truncated": len(value) > 6000, "gold": pred["gold"],
                       "choice": pred["choice"], "probabilities": pred["probabilities"]})
    return result


def source_hashes() -> dict:
    root = Path(__file__).parent
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.glob("*.py"))}


def optimize(config: JevConfig, train: list[Example], validation: list[Example],
             proposer: Proposer, evaluator: Evaluator, output: Path, *, iterations: int = 12,
             selection_metric: str = "accuracy", failure_sample: int = 12, patience: int = 0) -> dict:
    if iterations < 0 or patience < 0 or not 1 <= failure_sample <= 50:
        raise ValueError("Invalid search budget")
    if selection_metric not in {"accuracy", "macro_f1", "composite"}:
        raise ValueError("Unsupported selection metric")
    train_fp, val_fp = fingerprints(train), fingerprints(validation)
    disjoint(train_fp, val_fp)
    if any(row.label not in config.criteria for row in train + validation):
        raise ValueError("Unknown dataset label")
    if evaluator.output != output:
        raise ValueError("Search audit log must stay in the run directory")
    output.mkdir(parents=True, exist_ok=False)
    protocol = {"schema_version": VERSION, "backend": evaluator.backend.identity, "proposer": proposer.identity,
                "python": sys.version.split()[0], "source_sha256": source_hashes(),
                "baseline": asdict(config), "train_sha256": digest([asdict(r) for r in train]),
                "validation_sha256": digest([asdict(r) for r in validation]),
                "train_fingerprints": train_fp, "validation_fingerprints": val_fp,
                "iterations": iterations, "max_logical_jev_calls": evaluator.max_calls,
                "selection_metric": selection_metric, "failure_sample": failure_sample, "patience": patience}
    write_json(output / "protocol.json", protocol)
    ledger: list[dict] = []
    incumbent, seen, stalls = config, {config.fingerprint()}, 0
    stop = "iteration_budget"

    def checkpoint():
        write_json(output / "ledger.json", ledger)
        write_json(output / "optimized-config.json", asdict(incumbent))
        write_json(output / "usage.json", evaluator.summary())

    try:
        best, _ = evaluator.evaluate(incumbent, validation, "validation-baseline")
        baseline_metrics = best
        ledger.append({"iteration": 0, "status": "baseline", "config": asdict(config), "validation": best})
        checkpoint()  # Persist even when iterations == 0.
        for iteration in range(1, iterations + 1):
            try:
                _, training_predictions = evaluator.evaluate(incumbent, train, "train")
                history = [{"iteration": x["iteration"], "status": x["status"], "config": x.get("config")} for x in ledger[-5:]]
                proposal = proposer.propose(incumbent, feedback(train, training_predictions, failure_sample), iteration, history)
                row = {"iteration": iteration, "proposal": proposal}
                try:
                    candidate = JevConfig.from_dict(proposal, config)
                except (ValueError, TypeError, KeyError):
                    row["status"] = "invalid_candidate"
                else:
                    row["config"] = asdict(candidate)
                    if candidate.fingerprint() in seen:
                        row["status"] = "duplicate_candidate"
                    else:
                        seen.add(candidate.fingerprint())
                        ledger.append({**row, "status": "evaluating"})
                        checkpoint()
                        score, _ = evaluator.evaluate(candidate, validation, "validation-candidate")
                        ledger.pop()
                        row["validation"] = score
                        accepted = score[selection_metric] > best[selection_metric]
                        row["status"] = "accepted" if accepted else "rejected"
                        if accepted:
                            incumbent, best = candidate, score
                ledger.append(row)
                stalls = 0 if row["status"] == "accepted" else stalls + 1
                checkpoint()
                if patience and stalls >= patience:
                    stop = "patience"
                    break
            except BudgetExhausted:
                if ledger[-1]["status"] == "evaluating":
                    ledger[-1]["status"] = "budget_exhausted"
                stop = "jev_call_budget"
                break
        checkpoint()
        freeze = {"schema_version": VERSION, "protocol_sha256": digest(protocol), "ledger_sha256": digest(ledger),
                  "champion": asdict(incumbent), "champion_fingerprint": incumbent.fingerprint(),
                  "baseline_fingerprint": config.fingerprint(), "baseline_validation": baseline_metrics,
                  "champion_validation": best, "stop_reason": stop, "usage": evaluator.summary()}
        write_json(output / "freeze.json", {"payload": freeze, "sha256": digest(freeze)})
        return freeze
    except Exception as exc:
        checkpoint()
        write_json(output / "failure.json", {"error_type": type(exc).__name__, "usage": evaluator.summary()})
        raise


def frozen_run(run: Path) -> tuple[dict, dict]:
    envelope, protocol, ledger = read_json(run / "freeze.json"), read_json(run / "protocol.json"), read_json(run / "ledger.json")
    freeze = envelope["payload"]
    if (digest(freeze) != envelope["sha256"] or digest(protocol) != freeze["protocol_sha256"]
            or digest(ledger) != freeze["ledger_sha256"]):
        raise ValueError("Frozen run integrity check failed")
    if (JevConfig.from_dict(freeze["champion"]).fingerprint() != freeze["champion_fingerprint"]
            or JevConfig.from_dict(protocol["baseline"]).fingerprint() != freeze["baseline_fingerprint"]):
        raise ValueError("Frozen option order changed")
    return protocol, freeze


def evaluate_frozen(run: Path, test_path: Path, evaluator: Evaluator) -> dict:
    protocol, freeze = frozen_run(run)
    final = run / "final"
    if final.exists():
        raise FileExistsError("This run already has a final audit")
    if evaluator.output != final:
        raise ValueError("Final audit log must stay in run/final")
    if evaluator.backend.identity != protocol["backend"]:
        raise ValueError("Final evaluation must use the frozen backend/model/SDK")
    if source_hashes() != protocol["source_sha256"]:
        raise ValueError("Implementation changed after freeze")
    champion = JevConfig.from_dict(freeze["champion"])
    baseline = JevConfig.from_dict(protocol["baseline"])
    rows = load_data(test_path, champion.criteria)
    test_fp = fingerprints(rows)
    for key in ("train_fingerprints", "validation_fingerprints"):
        disjoint(protocol[key], test_fp)
    final.mkdir(exist_ok=False)  # At most one final evaluation per frozen run.
    write_json(final / "status.json", {"status": "started", "test_sha256": digest([asdict(r) for r in rows])})
    try:
        base_metrics, base_predictions = evaluator.evaluate(baseline, rows, "test-baseline")
        test_metrics, test_predictions = evaluator.evaluate(champion, rows, "test-champion")
        result = {"baseline": base_metrics, "champion": test_metrics,
                  "accuracy_delta": test_metrics["accuracy"]-base_metrics["accuracy"],
                  "freeze_sha256": digest(freeze), "usage": evaluator.summary(),
                  "note": "Descriptive held-out comparison, not a guarantee of improvement."}
        write_json(final / "metrics.json", result)
        write_json(final / "predictions.json", {"baseline": base_predictions, "champion": test_predictions})
        write_json(final / "status.json", {"status": "completed", "test_sha256": digest([asdict(r) for r in rows])})
        return result
    except Exception as exc:
        write_json(final / "status.json", {"status": "failed", "error_type": type(exc).__name__})
        raise
