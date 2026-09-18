"""Independent offline verification of a completed frozen Jev experiment.

Reads local artifacts only; never imports an adapter or reads credentials. Its
sole write is RUN_DIR/verification.json after every check passes. Missing stages
fail rather than producing a partial success report.
"""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
MODEL = "jev-1.13.0"
LABELS = {"relation_support": ("SUPPORTS", "REFUTES", "NOT_ENOUGH_INFO"),
          "entity_resolution": ("same", "different")}
ARMS = {"relation_support": ("baseline_choice", "evidence_contract", "conditional_nouls", "fewshot_contract"),
        "entity_resolution": ("baseline_noul", "identity_contract", "identity_noul", "fewshot_contract")}
STAGES = ("development", "calibration", "evaluation", "fresh_repeat_1", "fresh_repeat_2", "fixtures", "batching")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def lines(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value, compact=False):
    kwargs = {"separators": (",", ":")} if compact else {}
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, **kwargs).encode("utf-8")).hexdigest()


def instant(value):
    return datetime.fromisoformat(value)


def identities(task, row):
    return {row["group"]} if task == "relation_support" else set(row["identity_groups"])


def input_state(task, row):
    if task == "relation_support":
        return {"claim": row["claim"], "evidence": row["evidence"]}
    state = {"record_1": row["record_1"], "record_2": row["record_2"]}
    if row.get("context"):
        state["context"] = row["context"]
    return state


def probability(value):
    require(type(value) in (float, int) and math.isfinite(value) and 0 <= value <= 1, "Invalid raw probability")


def distribution(values, labels):
    require(isinstance(values, dict) and set(values) == set(labels), "Wrong probability label contract")
    for value in values.values():
        probability(value)
    require(math.isclose(sum(values.values()), 1, rel_tol=0, abs_tol=1e-6), "Non-normalized distribution")


def response_valid(call):
    raw, questions = call["response"], call["payload"]["questions"]
    require(isinstance(raw, dict) and "error" not in raw, "Invalid/error service response")
    require(raw.get("model") == MODEL, "Returned model mismatch")
    require(isinstance(raw.get("answers"), dict) and set(raw["answers"]) == set(questions), "Answer ID mismatch")
    for key, question in questions.items():
        answer = raw["answers"][key]
        require(answer.get("type") == question["type"], "Answer primitive mismatch")
        if question["type"] == "noul":
            probability(answer.get("noul"))
        else:
            require(question["type"] == "choice", "Unexpected primitive")
            distribution(answer.get("probabilities"), question["criteria"])
            probability(answer.get("confidence"))
            values = answer["probabilities"]
            require(answer.get("choice") in values and values[answer["choice"]] == max(values.values()),
                    "Choice is not a maximal canonical option")


def scores(rows, task):
    """Recompute point scores without importing the research analysis module."""
    labels = LABELS[task]
    eligible = [row for row in rows if row["gold_label"] in labels]
    valid = [row for row in eligible if not row["error"]]
    counts = {label: Counter() for label in labels}
    for row in eligible:
        predicted = max(labels, key=lambda key: row["distribution"][key]) if not row["error"] else "ERROR"
        counts[row["gold_label"]][predicted] += 1
    correct, f1 = sum(counts[label][label] for label in labels), []
    for label in labels:
        denominator = sum(counts[label].values()) + sum(counts[gold][label] for gold in labels)
        f1.append(2 * counts[label][label] / denominator if denominator else 0)
    brier = [sum((row["distribution"][label] - int(label == row["gold_label"])) ** 2 for label in labels) for row in valid]
    loss = [-math.log(max(row["distribution"][row["gold_label"]], 1e-15)) for row in valid]
    return {"n_examples": len(rows), "n_semantic_examples": len(eligible), "n_excluded_gold": len(rows) - len(eligible),
            "n_errors": sum(bool(row["error"]) for row in rows), "probability_score_denominator": len(valid),
            "accuracy": correct / len(eligible) if eligible else None,
            "macro_f1": sum(f1) / len(labels) if eligible else None,
            "brier_score": sum(brier) / len(valid) if valid else None, "log_loss": sum(loss) / len(valid) if valid else None}


def close(actual, expected):
    return actual is None if expected is None else (actual == expected if not isinstance(expected, float)
                                                    else math.isclose(actual, expected, rel_tol=1e-11, abs_tol=1e-12))


def scale(values, temperature):
    weights = {key: math.log(max(value, 1e-15)) / temperature for key, value in values.items()}
    top = max(weights.values())
    weights = {key: math.exp(value - top) for key, value in weights.items()}
    return {key: value / sum(weights.values()) for key, value in weights.items()}


def expected_jobs(plan, selection):
    for task, data in plan["tasks"].items():
        retained = [selection[task][key] for key in ("baseline", "selected")]
        specifications = [("development", "development", data["development"], list(ARMS[task]), 0, "batched")]
        specifications += [(split, split, data[split], retained, 0, "batched") for split in ("calibration", "evaluation", "fixtures")]
        repeat_rows = [row for row in data["evaluation"] if row["id"] in data["repeatability_ids"]]
        specifications += [("fresh_repeat_" + str(number), "repeatability", repeat_rows, retained, number, "batched") for number in (1, 2)]
        specifications += [("batching", "batching", [row for row in data["development"] if row["id"] in data["batching_ids"]],
                            [arm for arm in ARMS[task] if arm != "fewshot_contract"], 0, "separate")]
        for stage, split, rows, arms, repeat, condition in specifications:
            for row in rows:
                state = input_state(task, row)
                ordinary = [arm for arm in arms if arm != "fewshot_contract"]
                grouped = [(state, [arm]) for arm in ordinary] if condition == "separate" else ([(state, ordinary)] if ordinary else [])
                if "fewshot_contract" in arms:
                    demos = [{"input": input_state(task, item), "answer": item["gold_label"]} for item in data["demonstrations"]]
                    grouped.append(({"labeled_examples": demos, "input": state}, ["fewshot_contract"]))
                for shared, members in grouped:
                    questions = {key: value for arm in members for key, value in plan["question_specs"][task][arm].items()}
                    payload = {"state": shared, "model": MODEL, "questions": questions}
                    key = digest({"task": task, "split": split, "id": row["id"], "repeat": repeat,
                                  "condition": condition, "payload": payload})
                    yield stage, task, split, row, members, repeat, condition, payload, key


def credential_scan(directory):
    """Pattern-only screen; never reads environment variables or emits matches."""
    patterns = (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}"),
                re.compile(r"\b(?:sk|ts|jev)[_-](?:proj[-_])?[A-Za-z0-9_-]{24,}"),
                re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
                re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"))
    scanned, binary_skipped = 0, 0
    for path in directory.rglob("*"):
        if not path.is_file() or path.name == "verification.json":
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".pdf"}:
            binary_skipped += 1
            continue
        text = path.read_text(encoding="utf-8")
        require(not any(pattern.search(text) for pattern in patterns),
                "Potential credential pattern found in artifact " + str(path.relative_to(directory)))
        if path.suffix in (".json", ".jsonl"):
            stack = lines(path) if path.suffix == ".jsonl" else [read(path)]
            while stack:
                item = stack.pop()
                if isinstance(item, dict):
                    for key, value in item.items():
                        if key.lower() in {"authorization", "api_key", "access_token", "refresh_token", "secret_key"}:
                            require(value in (None, "", "[REDACTED]"), "Credential-valued field found in artifact " + str(path.relative_to(directory)))
                        stack.append(value)
                elif isinstance(item, list):
                    stack.extend(item)
        scanned += 1
    return {"text_files_scanned": scanned, "binary_figures_skipped": binary_skipped, "matches": 0,
            "limitation": "Text patterns and structured fields only; binary figures skipped, no environment/key comparison, no proof of absence of every possible secret."}


def verify(directory):
    directory = directory.resolve()
    manifest, plan = read(directory / "manifest.json"), read(directory / "plan.json")
    require(set(STAGES) <= {row["stage"] for row in manifest["stages"]}, "Experiment incomplete: required stages missing")
    require((directory / "results.json").exists(), "Experiment analysis incomplete")
    results = read(directory / "results.json")
    require(results["completeness"]["complete"], "Analysis declares incomplete experiment")
    require(sha(directory / "plan.json") == manifest["plan_sha256"], "Plan hash mismatch")
    require(sha(directory / "PROTOCOL.md") == manifest["protocol_sha256"] == sha(ROOT / "results/jev/PROTOCOL.md"), "Protocol hash mismatch")
    require(plan["seed"] == manifest["seed"] == 20260917 and plan["model"] == manifest["model"] == MODEL, "Frozen seed/model mismatch")
    for name, expected in manifest["source_sha256"].items():
        path = ROOT / Path(name.replace("\\", "/"))
        require(sha(path) == sha(directory / "source_snapshot" / path.name) == expected, "Frozen source hash mismatch: " + name)
    for name, expected in results["input_sha256"].items():
        require(sha(directory / name) == expected, "Analysis input hash mismatch: " + name)
    calls, records = lines(directory / "calls.jsonl"), lines(directory / "predictions.jsonl")
    by_call = {call["call_id"]: call for call in calls}
    require(len(by_call) == len(calls), "Duplicate physical call IDs")
    observation = lambda row: tuple(row[key] for key in ("task", "split", "arm", "id", "repeat", "condition"))
    by_record = {observation(row): row for row in records}
    require(len(by_record) == len(records), "Duplicate prediction observations")

    data_report = {}
    for task, filename, counts in (("relation_support", "scifact-prepared.json", (459, 150, 339)),
                                   ("entity_resolution", "entity_resolution-prepared.json", (4592, 390, 413))):
        data, source = plan["tasks"][task], read(ROOT / ".cache/research-data" / filename)
        require(tuple(len(source[key]) for key in ("train", "calibration", "evaluation")) == counts, "Prepared split sizes changed")
        require(digest(source) == data["data_manifest"]["splits_sha256"], "Prepared split content hash mismatch")
        sources = data["data_manifest"].get("sources", [data["data_manifest"].get("source")])
        for origin in sources:
            require(sha(ROOT / Path(origin["local_file"].replace("\\", "/"))) == origin["sha256"], "Raw dataset source hash mismatch")
        require(data["calibration"] == source["calibration"] and data["evaluation"] == source["evaluation"], "Frozen held-out rows changed")
        train = {row["id"]: row for row in source["train"]}
        require(len(data["demonstrations"]) == 6 and len(data["development"]) == 60, "Wrong development/demonstration count")
        require(Counter(row["gold_label"] for row in data["demonstrations"]) ==
                {label: (2 if task == "relation_support" else 3) for label in LABELS[task]}, "Demonstration balance changed")
        used = set()
        for row in data["demonstrations"] + data["development"]:
            require(train.get(row["id"]) == row, "Demonstration/development row is not unchanged training data")
            keys = identities(task, row)
            require(not keys & used, "Demonstration/development identity leakage")
            used.update(keys)
        split_keys = []
        for split in ("train", "calibration", "evaluation"):
            keys = set().union(*(identities(task, row) for row in source[split]))
            require(not any(keys & previous for previous in split_keys), "Identity/group split leakage")
            split_keys.append(keys)
        require(len(set(data["repeatability_ids"])) == len(set(data["batching_ids"])) == 20, "Wrong repeat/control subset size")
        expected_repeat = [row["id"] for row in sorted(source["evaluation"], key=lambda row: digest([20260917, "repeats", row["id"]]))[:20]]
        require(data["repeatability_ids"] == expected_repeat, "Repeat subset is not frozen ID-only selection")
        require(data["batching_ids"] == [row["id"] for row in data["development"][:20]], "Batching subset changed")
        require(set(plan["question_specs"][task]) == set(ARMS[task]), "Frozen arm set mismatch")
        require(len(data["fixtures"]) == (50 if task == "relation_support" else 100), "Wrong fixture size")
        if task == "entity_resolution":
            require(sum(row["gold_label"] == "uncertain" for row in data["fixtures"]) == 12, "Uncertain fixture denominator changed")
        data_report[task] = {"train": counts[0], "calibration": counts[1], "evaluation": counts[2],
                             "demonstrations": 6, "development": 60, "evaluation_identity_or_component_keys": len(split_keys[2])}

    expected_records, expected_calls, stage_counts, phase_counts = set(), set(), Counter(), Counter()
    call_stage = {}
    for stage, task, split, row, arms, repeat, condition, payload, key in expected_jobs(plan, manifest["selection"]):
        expected_calls.add(key)
        stage_counts[stage] += 1
        require(key in by_call, "Missing planned physical call in " + stage)
        call, call_stage[key] = by_call[key], stage
        require(call["cache_key"] == key and call["payload"] == payload and call["request_sha256"] == digest(payload), "Exact request cache mismatch")
        for arm in arms:
            value = {}
            if not call["error"]:
                answers, prefix = call["response"]["answers"], arm + "__"
                if arm == "conditional_nouls":
                    support, refute = answers[prefix + "support"]["noul"], answers[prefix + "refute_given_not_support"]["noul"]
                    value = {"SUPPORTS": support, "REFUTES": (1-support)*refute, "NOT_ENOUGH_INFO": (1-support)*(1-refute)}
                else:
                    answer = answers[prefix + "decision"]
                    value = ({"same": answer["noul"], "different": 1-answer["noul"]} if answer["type"] == "noul" else answer["probabilities"])
                distribution(value, LABELS[task])
            expected = {"task": task, "split": split, "arm": arm, "id": row["id"], "group": row["group"],
                        "gold_label": row["gold_label"], "distribution": value, "error": call["error"],
                        "execution_mode": call["execution_mode"], "call_ids": [key], "repeat": repeat, "condition": condition}
            obs = observation(expected)
            expected_records.add(obs)
            require(by_record.get(obs) == expected, "Prediction differs from raw call reconstruction")
            phase_counts[(task, split, arm, repeat)] += 1
    require(set(by_record) == expected_records, "Unexpected prediction observations")
    probes = [call for call in calls if call["call_id"] not in expected_calls]
    require(len(probes) == 1 and probes[0].get("purpose", "").startswith("toy authentication/schema probe"), "Unexpected unplanned calls")
    for stage, count in stage_counts.items():
        entries = [entry for entry in manifest["stages"] if entry["stage"] == stage]
        require(entries and all(entry["jobs"] == count for entry in entries), "Stage job count mismatch")

    attempts = input_tokens = output_tokens = token_charge = unknown = 0
    errors, events, all_starts = Counter(), [], []
    for call in calls:
        metadata, payload = call["metadata"], call["payload"]
        require(call["execution_mode"] == "real" and payload["model"] == MODEL and metadata["requested_model"] == MODEL, "Mock/wrong-model call in real evidence")
        require(call["request_sha256"] == digest(payload), "Raw call request hash mismatch")
        number = metadata["attempts"]
        require(type(number) is int and 1 <= number <= 3, "HTTP retry ceiling exceeded")
        attempts += number
        usage = call["tokens_used"]
        if usage is not None:
            require(set(usage) == {"input", "output"} and all(type(value) is int and value >= 0 for value in usage.values()), "Invalid token usage")
            input_tokens += usage["input"]
            output_tokens += usage["output"]
            raw_usage = call["response"]["usage"]
            require(usage == {"input": raw_usage["input_tokens"], "output": raw_usage["output_tokens"]}, "Usage differs from raw service response")
        missing = number - int(usage is not None)
        unknown += missing
        reserve = len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) + 4096 * len(payload["questions"])
        charge = (usage or {}).get("input", 0) + missing * reserve
        require(call["budget_input_token_charge"] == charge, "Token budget charge omitted unknown usage")
        token_charge += charge
        if call["call_id"] in expected_calls:
            require(metadata["request_sha256"] == digest(payload, compact=True), "Adapter request hash mismatch")
            require(len(metadata["attempt_log"]) == number, "Missing HTTP attempt evidence")
            for attempt in metadata["attempt_log"]:
                start = instant(attempt["started_at"])
                require(attempt["latency_ms"] >= 0, "Negative attempt duration")
                events.extend(((start, 1), (start + timedelta(milliseconds=attempt["latency_ms"]), -1)))
                all_starts.append(start)
                require(start >= instant(manifest["created_at"]), "Research request preceded frozen manifest")
                if call_stage[call["call_id"]] != "development":
                    require(start >= instant(manifest["selection_frozen_at"]), "Held-out call preceded frozen selection")
        if call["error"]:
            errors[call["error"]] += 1
            if call["response"] is not None:
                try:
                    response_valid(call)
                except ValueError:
                    pass
                else:
                    require(False, "Failed response unexpectedly satisfies frozen answer contract")
        else:
            response_valid(call)
    active = peak = 0
    for _, difference in sorted(events):
        active += difference
        peak = max(peak, active)
    require(active == 0 and peak <= 4, "Observed HTTP concurrency exceeds protocol")
    require(attempts <= 4000 and token_charge <= 20_000_000, "Run exceeded frozen resource caps")
    expected_usage = {"n_calls": len(calls), "n_http_attempts": attempts, "n_retries": attempts - len(calls),
                      "reported_input_tokens": input_tokens, "reported_output_tokens": output_tokens,
                      "unknown_usage_attempts": unknown, "budget_input_token_charge": token_charge,
                      "n_failed_calls": sum(errors.values()),
                      "n_questions_in_recorded_payloads": sum(len(call["payload"]["questions"]) for call in calls)}
    require(all(results["usage"][key] == value for key, value in expected_usage.items()), "Reported usage differs from raw call accounting")

    calibration = read(directory / "calibration.json")
    require(sha(directory / "calibration.json") == manifest["calibration_sha256"], "Calibration hash mismatch")
    require(instant(calibration["frozen_at"]) >= instant(manifest["selection_frozen_at"]), "Calibration preceded arm selection")
    for key, stage in call_stage.items():
        if stage == "evaluation":
            require(all(instant(attempt["started_at"]) >= instant(calibration["frozen_at"])
                        for attempt in by_call[key]["metadata"]["attempt_log"]), "Evaluation began before calibration freeze")

    comparison_report = {}
    for task, choice in manifest["selection"].items():
        subset = lambda split, arm: [row for row in records if row["task"] == task and row["split"] == split and row["arm"] == arm]
        development = {arm: scores(subset("development", arm), task) for arm in ARMS[task]}
        alternative = sorted((arm for arm in ARMS[task] if arm != choice["baseline"]),
                             key=lambda arm: (-development[arm]["macro_f1"], development[arm]["brier_score"]
                                              if development[arm]["brier_score"] is not None else math.inf, arm))[0]
        require(choice["selected"] == alternative, "Selected arm differs from development-only ranking")
        for arm in (choice["baseline"], choice["selected"]):
            fit = calibration["fits"][task][arm]
            cal_rows = subset("calibration", arm)
            valid = [row for row in cal_rows if not row["error"]]
            require(fit["fit_ids"] == sorted(row["id"] for row in valid), "Fit IDs are not calibration-only valid rows")
            temperature = fit["temperature"]
            require(.05 <= temperature <= 20, "Fitted temperature outside frozen interval")
            before = scores(cal_rows, task)["log_loss"]
            transformed = [{**row, "distribution": scale(row["distribution"], temperature)} if not row["error"] else row for row in cal_rows]
            after = scores(transformed, task)["log_loss"]
            require(close(before, fit["calibration_log_loss_before"]) and close(after, fit["calibration_log_loss_after"]), "Calibration loss reconstruction mismatch")
            require(after <= before + 1e-12, "Calibration did worse than frozen T=1 candidate")
            for split in ("development", "calibration", "evaluation", "fixtures"):
                raw = subset(split, arm)
                versions = {"raw": raw, "calibrated": [{**row, "distribution": scale(row["distribution"], temperature)}
                                                       if not row["error"] else row for row in raw]}
                for version, rows in versions.items():
                    expected = scores(rows, task)
                    observed = results["tasks"][task]["scores"][split][arm][version]
                    require(all(close(observed[key], value) for key, value in expected.items()), "Reported point score differs from independent recomputation")
            for example in plan["tasks"][task]["repeatability_ids"]:
                triplet = [by_record[(task, "evaluation", arm, example, 0, "batched")]]
                triplet += [by_record[(task, "repeatability", arm, example, number, "batched")] for number in (1, 2)]
                physical = [by_call[row["call_ids"][0]] for row in triplet]
                require(len({call["call_id"] for call in physical}) == 3, "Cached response counted as fresh repeat")
                require(all(call["payload"] == physical[0]["payload"] for call in physical), "Repeats changed semantic payload/co-batched questions")
        evaluation = {arm: scores(subset("evaluation", arm), task) for arm in (choice["baseline"], choice["selected"])}
        comparison_report[task] = {"baseline": choice["baseline"], "selected": choice["selected"], "raw_scores": evaluation,
                                   "macro_f1_delta": evaluation[choice["selected"]]["macro_f1"] - evaluation[choice["baseline"]]["macro_f1"]}

    secret_report = credential_scan(directory)
    require(results["n_prediction_records"] == len(records), "Reported prediction count mismatch")
    report = {"status": "passed", "verified_at": datetime.now(timezone.utc).isoformat(), "verifier_sha256": sha(Path(__file__)),
              "run_directory": str(directory.relative_to(ROOT)),
              "inputs_sha256": {name: sha(directory / name) for name in ("manifest.json", "plan.json", "calls.jsonl", "predictions.jsonl", "results.json", "calibration.json", "PROTOCOL.md")},
              "datasets": data_report, "n_calls_including_probe": len(calls), "n_predictions": len(records), "stage_http_jobs": dict(stage_counts),
              "phase_counts": [{"task": task, "split": split, "arm": arm, "repeat": repeat, "count": count}
                               for (task, split, arm, repeat), count in sorted(phase_counts.items())],
              "http_attempts": attempts, "reported_input_tokens": input_tokens, "reported_output_tokens": output_tokens,
              "unknown_usage_attempts": unknown, "input_token_budget_charge": token_charge,
              "estimated_input_usd": input_tokens * .042 / 1_000_000, "estimated_peak_concurrency": peak,
              "research_request_window_utc": {"first_start": min(all_starts).isoformat(), "last_start": max(all_starts).isoformat()},
              "service_errors": dict(errors), "comparisons": comparison_report, "credential_pattern_scan": secret_report,
              "checks": ["Frozen source, protocol, source-data and plan hashes", "Training/demo/development/held-out identity isolation",
                         "Every planned phase observation and HTTP payload", "Independent raw-response validation and probability reconstruction",
                         "Failure persistence and conservative token/retry accounting", "Development-only selection and pre-evaluation calibration freeze",
                         "Independent raw/calibrated point scores", "Three distinct fresh calls with identical semantic payloads per repeat example"],
              "limitations": ["Does not rerun model inference or establish immutable vendor weights.",
                              "Recomputes point scores but does not independently regenerate bootstrap intervals.",
                              "Concurrency is inferred from recorded attempt start times and durations.",
                              "Secret screening uses patterns, not live credential comparison."]}
    (directory / "verification.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=ROOT / "results/jev/run-20260918")
    result = verify(parser.parse_args().run_dir)
    print(json.dumps({key: result[key] for key in ("status", "n_calls_including_probe", "n_predictions", "http_attempts", "reported_input_tokens")}))


if __name__ == "__main__":
    main()
