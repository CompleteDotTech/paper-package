"""Evidence-bound adapters for the frozen Jev study. No network calls on import.

Gold labels remain in the evaluation dataset, not in score requests. This adapter
only reuses a score when the exact frozen input and formulation match. Replayed
observations are always labeled recorded, never fresh live inference.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .core import digest, distribution

BASE_COMMIT = "d4e61e642976e933e1650284cfa13de20cec756a"
INVENTORY_BLOB = "3837504455f0bac580496858f3f0ba99f795fe6c"
RUN_PATH = "reproduction/results/jev/run-20260918"
LABELS = {"relation_support": ("SUPPORTS", "REFUTES", "NOT_ENOUGH_INFO"),
          "entity_resolution": ("same", "different")}
BASELINES = {"relation_support": "baseline_choice", "entity_resolution": "baseline_noul"}


def inventory(repository: Path) -> dict[str, Any]:
    raw = (repository / "MANIFEST.json").read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if blob != INVENTORY_BLOB:
        raise ValueError("The immutable baseline inventory differs from the pinned commit")
    return {row["path"]: row for row in json.loads(raw)["files"]}


def checked_file(repository: Path, relative: str, manifest: Mapping[str, Any]) -> bytes:
    root = repository.resolve()
    path = root / relative
    if path.is_symlink() or not path.resolve().is_relative_to(root) or relative not in manifest:
        raise ValueError("Unmanifested or unsafe source path")
    raw = path.read_bytes()
    expected = manifest[relative]
    if len(raw) != expected["bytes"] or hashlib.sha256(raw).hexdigest() != expected["sha256"]:
        raise ValueError("Changed frozen artifact: " + relative)
    return raw


def input_state(task: str, row: Mapping[str, Any]) -> dict[str, Any]:
    if task == "relation_support":
        return {"claim": row["claim"], "evidence": deepcopy(row["evidence"])}
    if task != "entity_resolution":
        raise ValueError("Unsupported decision task")
    state = {"record_1": deepcopy(row["record_1"]), "record_2": deepcopy(row["record_2"])}
    if row.get("context"):
        state["context"] = row["context"]
    return state


def payload_for(plan: Mapping[str, Any], task: str, arm: str, state: Mapping[str, Any]) -> dict[str, Any]:
    if task not in LABELS or arm not in {BASELINES[task], "fewshot_contract"}:
        raise ValueError("Only the frozen primary formulations are supported")
    required = {"claim", "evidence"} if task == "relation_support" else {"record_1", "record_2"}
    allowed = required if task == "relation_support" else required | {"context"}
    if not required <= state.keys() or set(state) - allowed:
        raise ValueError("Unexpected input fields; gold labels and evaluation metadata are not model inputs")
    state = deepcopy(dict(state))
    if arm == "fewshot_contract":
        demos = plan["tasks"][task]["demonstrations"]
        state = {"labeled_examples": [{"input": input_state(task, demo), "answer": demo["gold_label"]}
                                      for demo in demos], "input": state}
    return {"state": state, "model": plan["model"],
            "questions": deepcopy(plan["question_specs"][task][arm])}


@dataclass(frozen=True)
class ScoredDecision:
    probabilities: Mapping[str, float]
    label: str
    model: str
    mode: str
    request_hash: str
    call_id: str
    error: str | None = None


def parse_answer(response: Mapping[str, Any], task: str, arm: str, model: str) -> dict[str, float]:
    if response.get("model") != model:
        raise ValueError("Returned model differs from the frozen request")
    key = arm + "__decision"
    answers = response.get("answers", {})
    if set(answers) != {key}:
        raise ValueError("Wrong or missing decision identifiers")
    answer = answers[key]
    if task == "entity_resolution" and arm == "baseline_noul":
        if answer.get("type") != "noul":
            raise ValueError("Wrong primitive")
        from .core import probability
        same = probability(answer.get("noul"))
        values = {"same": same, "different": 1-same}
    else:
        if answer.get("type") != "choice":
            raise ValueError("Wrong primitive")
        values = distribution(answer.get("probabilities", {}), LABELS[task])
        chosen = answer.get("choice")
        if chosen not in values or values[chosen] != max(values.values()):
            raise ValueError("Choice does not match the maximal probability")
    return distribution(values, LABELS[task])


class RecordedJev:
    def __init__(self, repository: Path):
        self.repository = repository.resolve()
        manifest = inventory(self.repository)
        self.hashes = {}
        data = {}
        for name in ("plan.json", "predictions.jsonl", "calls.jsonl"):
            raw = checked_file(self.repository, RUN_PATH + "/" + name, manifest)
            self.hashes[name] = hashlib.sha256(raw).hexdigest()
            data[name] = ([json.loads(line) for line in raw.splitlines() if line.strip()]
                          if name.endswith(".jsonl") else json.loads(raw))
        self.plan = data["plan.json"]
        self.calls = {row["call_id"]: row for row in data["calls.jsonl"]}
        if len(self.calls) != len(data["calls.jsonl"]):
            raise ValueError("Duplicate original call identifiers")
        self.predictions = {}
        for row in data["predictions.jsonl"]:
            if row["split"] in {"calibration", "evaluation"}:
                key = (row["task"], row["arm"], row["split"], row["id"])
                if key in self.predictions or row["repeat"] != 0 or row["condition"] != "batched":
                    raise ValueError("Ambiguous frozen observation")
                self.predictions[key] = row
        self.rows = {(task, split, row["id"]): row for task in LABELS
                     for split in ("calibration", "evaluation")
                     for row in self.plan["tasks"][task][split]}

    def score(self, task: str, arm: str, split: str, id_: str,
              state: Mapping[str, Any]) -> ScoredDecision:
        if task not in LABELS or split not in {"calibration", "evaluation"} or arm not in {BASELINES[task], "fewshot_contract"}:
            raise ValueError("Only the frozen primary comparison can be replayed")
        row = self.rows[task, split, id_]
        if state != input_state(task, row):
            raise ValueError("Changed evidence or record requires a new decision")
        record = self.predictions[task, arm, split, id_]
        if len(record["call_ids"]) != 1 or record["execution_mode"] != "real":
            raise ValueError("Missing provenance for a real recorded observation")
        call = self.calls[record["call_ids"][0]]
        expected = payload_for(self.plan, task, arm, state)
        if call["payload"] != expected or call["execution_mode"] != "real":
            raise ValueError("Input/formulation does not match the recorded service call")
        if call["error"] != record["error"]:
            raise ValueError("Stored error differs from service observation")
        if record["error"]:
            if record["distribution"]:
                raise ValueError("Failed decisions must not contain invented probabilities")
            return ScoredDecision({}, "ERROR", self.plan["model"], "recorded", digest(expected),
                                  call["call_id"], str(record["error"]))
        values = parse_answer(call["response"], task, arm, self.plan["model"])
        if values != record["distribution"]:
            raise ValueError("Prediction does not reconstruct from raw service response")
        label = max(LABELS[task], key=values.get)
        return ScoredDecision(values, label, self.plan["model"], "recorded", digest(expected), call["call_id"])


class JevFormulation:
    """Opt-in integration for new inputs using an injected existing Jev adapter.

    The caller must explicitly supply a configured pgc.decision.jev_real backend.
    This class never finds keys, contacts a service in its constructor, or changes
    the archived prompt. New outputs must be journaled by the consuming application.
    """
    def __init__(self, plan: Mapping[str, Any], backend: Any, *, allow_live: bool = False,
                 max_calls: int = 100):
        if not allow_live or type(max_calls) is not int or max_calls < 1:
            raise ValueError("New inference requires explicit consent and a positive call cap")
        if backend.version() != plan["model"]:
            raise ValueError("Backend and formulation model versions differ")
        self.plan, self.backend, self.max_calls, self.calls = deepcopy(plan), backend, max_calls, 0

    def score(self, task: str, arm: str, state: Mapping[str, Any]) -> ScoredDecision:
        if task not in LABELS or arm not in {BASELINES[task], "fewshot_contract"}:
            raise ValueError("Unvalidated formulation")
        if self.calls >= self.max_calls:
            raise RuntimeError("Declared new-inference call budget exhausted")
        payload = payload_for(self.plan, task, arm, state)
        self.calls += 1  # Failed calls consume budget too.
        result = self.backend.send_payload(payload["state"], payload["questions"])
        values = parse_answer(result["response"], task, arm, self.plan["model"])
        mode = "live" if result["execution_mode"] == "real" else "synthetic"
        return ScoredDecision(values, max(LABELS[task], key=values.get), self.plan["model"], mode,
                              digest(payload), "new-call-" + str(self.calls))
