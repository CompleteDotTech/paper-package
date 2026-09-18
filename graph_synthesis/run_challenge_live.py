"""Bounded live execution of the exact public synthetic challenge inputs.

One attempt per case, no retries or resume. Credentials are environment-only.
Raw provider evidence is retained; labels remain provisional human-review fixtures.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from .core import digest
from .semantic_challenge import evaluate, load_cases, public_inputs


def run(output: Path):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "reproduction"))
    from pgc.decision.jev_real import JevRealBackend, JevAPIError
    backend = JevRealBackend(max_retries=0)
    if not backend.available:
        raise ValueError("TYPESAFE_API_KEY required")
    output.mkdir(parents=True, exist_ok=False)
    cases = load_cases()
    inputs = public_inputs(cases)
    (output / "inputs.jsonl").write_text("".join(json.dumps(x) + "\n" for x in inputs), encoding="utf-8")
    predictions, raw = [], []
    for row in inputs:
        questions = {"decision": {"type": "choice", "instructions": row["question"],
                                  "criteria": {k: k for k in row["labels"]}}}
        payload = {"state": row["state"], "model": backend.model, "questions": questions}
        record = {"id": row["id"], "request": payload,
                  "created_at": datetime.now(timezone.utc).isoformat()}
        prediction = {"id": row["id"], "input_hash": row["input_hash"],
                      "model": backend.model + "/public-challenge-contract-v1", "request_hash": digest(payload)}
        stop = False
        try:
            result = backend.send_payload(row["state"], questions)
            record.update(result)
            values = result["response"]["answers"]["decision"]["probabilities"]
            prediction.update(status="ok", probabilities=values, label=max(values, key=values.get))
        except JevAPIError as error:
            record.update(response=error.raw_response, error=str(error), metadata=error.metadata,
                          tokens_used=error.tokens_used, execution_mode="real")
            prediction.update(status="error", error=str(error))
            stop = error.status_code in (401, 403)
        prediction["response_hash"] = digest(record["response"])
        raw.append(record)
        predictions.append(prediction)
        for name, value in (("raw.jsonl", record), ("predictions.jsonl", prediction)):
            with (output / name).open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(value, allow_nan=False) + "\n")
        print(json.dumps({"completed": len(predictions), "total": len(inputs), "status": prediction["status"]}), flush=True)
        if stop:
            break
    result = evaluate(cases, predictions)
    (output / "evaluation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    # Separate audit: the generic imported-journal evaluator deliberately remains unverified.
    audit = {"execution": "live_https_provider_responses", "model": backend.model,
             "requests": len(raw), "input_tokens": sum((r.get("tokens_used") or {}).get("input", 0) for r in raw),
             "request_response_hashes_verified": all(p["request_hash"] == digest(r["request"]) and
                  p["response_hash"] == digest(r["response"]) for p, r in zip(predictions, raw)),
             "limitations": "Public synthetic labels need human review; not independent benchmark evidence or provider-signed attestation."}
    (output / "execution-audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live", action="store_true", required=True)
    run(parser.parse_args().output)
