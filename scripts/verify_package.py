"""Verify package integrity, then optionally replay the Jev study with networking disabled.

All runtime writes are made to a temporary copy. This directory remains unchanged.
Python 3.12 and NumPy are sufficient for --replay; --tests uses the full research environment.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile

PACKAGE = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--tests", action="store_true")
    parser.add_argument("--output", type=Path, help="Optional report outside the package")
    args = parser.parse_args()
    if args.output and args.output.resolve().is_relative_to(PACKAGE):
        parser.error("Write the report outside the immutable package, then deliberately refresh its manifest if archiving it.")
    manifest = json.loads((PACKAGE / "MANIFEST.json").read_text(encoding="utf-8"))
    expected = {row["path"]: row for row in manifest["files"]}
    actual = {p.relative_to(PACKAGE).as_posix() for p in PACKAGE.rglob("*")
              if p.is_file() and p.name != "MANIFEST.json" and "__pycache__" not in p.parts}
    if actual != set(expected):
        raise ValueError("Package inventory differs from its manifest")
    for name, row in expected.items():
        path = (PACKAGE / name).resolve()
        if not path.is_relative_to(PACKAGE) or path.stat().st_size != row["bytes"] or sha(path) != row["sha256"]:
            raise ValueError("Package file failed integrity check: " + name)
    report = {"status": "passed", "verified_at_utc": datetime.now(timezone.utc).isoformat(),
              "package_files_verified": len(expected), "package_manifest_sha256": sha(PACKAGE / "MANIFEST.json")}
    if args.replay or args.tests:
        with tempfile.TemporaryDirectory(prefix="jev-paper-reproduction-") as temporary:
            work = Path(temporary) / "reproduction"
            shutil.copytree(PACKAGE / "reproduction", work)
            shutil.copytree(work / "data/sources", work / ".cache/research-data")
            if args.replay:
                sys.path.insert(0, str(work))
                attempted_network = []

                def blocked(*args, **kwargs):
                    attempted_network.append(True)
                    raise RuntimeError("Networking is disabled during paper reproduction")

                original_connect, original_connect_ex, original_connection = socket.socket.connect, socket.socket.connect_ex, socket.create_connection
                socket.socket.connect = socket.socket.connect_ex = socket.create_connection = blocked
                try:
                    from pgc.experiments.verify_jev_artifacts import verify
                    from pgc.experiments.run_jev_research import Runner
                    from pgc.experiments.analyze_jev_research import analyze
                    run = work / "results/jev/run-20260918"
                    proof = verify(run)
                    original_manifest = (run / "manifest.json").read_bytes()
                    protected = {name: sha(run / name) for name in ("calls.jsonl", "predictions.jsonl", "calibration.json", "results.json")}
                    runner = Runner(run, live=False)
                    runner.development()
                    runner.evaluate()
                    (run / "manifest.json").write_bytes(original_manifest)
                    analyze(run)
                    equality = {name: sha(run / name) == digest for name, digest in protected.items()}
                    if not all(equality.values()) or attempted_network:
                        raise ValueError("Exact network-free reproduction failed")
                    report["replay"] = {"network_attempts": len(attempted_network), "exact_byte_equality": equality,
                                        "calls": proof["n_calls_including_probe"], "predictions": proof["n_predictions"]}
                finally:
                    socket.socket.connect, socket.socket.connect_ex, socket.create_connection = original_connect, original_connect_ex, original_connection
            if args.tests:
                process = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests"], cwd=work, text=True, capture_output=True)
                if process.returncode:
                    raise RuntimeError(process.stdout + process.stderr)
                report["tests"] = {"exit_code": process.returncode, "output": process.stdout + process.stderr}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
