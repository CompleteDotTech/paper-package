"""Replay a fresh run in isolation, prohibit networking, and compare artifacts."""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import shutil
import socket
import sys
import tempfile
from unittest.mock import patch


def replay(directory):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "reproduction"))
    from pgc.experiments.run_jev_research import Runner
    from pgc.experiments.analyze_jev_research import analyze
    with tempfile.TemporaryDirectory(prefix="jev-fresh-replay-") as temp:
        work = Path(temp)
        for name in ("plan.json", "manifest.json", "calls.jsonl", "predictions.jsonl", "calibration.json", "results.json"):
            shutil.copyfile(directory / name, work / name)
        original = (work / "manifest.json").read_bytes()
        manifest = json.loads(original)
        manifest["source_sha256"] = {k.replace("\\", "/"):v for k,v in manifest["source_sha256"].items()}
        (work / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with ExitStack() as stack:
            for target in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection"):
                stack.enter_context(patch(target, side_effect=RuntimeError("Replay network prohibited")))
            runner = Runner(work, live=False)
            runner.development()
            runner.evaluate()
            (work / "manifest.json").write_bytes(original)
            analyze(work)
        comparisons = {}
        for name in ("calls.jsonl", "predictions.jsonl", "calibration.json", "results.json"):
            actual, expected = (work / name).read_bytes(), (directory / name).read_bytes()
            comparisons[name] = {"byte_equal": actual == expected, "sha256": hashlib.sha256(actual).hexdigest()}
            if actual != expected:
                raise ValueError("Fresh replay mismatch: " + name)
        report = {"status": "passed", "network_disabled": True, "artifacts": comparisons}
        (directory / "replay-verification.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    replay(parser.parse_args().run_dir)
