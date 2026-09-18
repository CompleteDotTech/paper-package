"""Verify the immutable archive and replay it portably from a temporary runtime.

The archived runner uses Windows path strings as native Paths. Only the temporary
runtime manifest's path keys are normalized; the archived manifest is restored
before analysis. Newline and narrowly bounded floating-point differences are reported, not hidden.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import math
from pathlib import Path
import shutil
import socket
import sys
import tempfile
from unittest.mock import patch

from .recorded import checked_file, inventory


def compare_json(left, right):
    """Exact structure/counts; narrowly tolerate floating-point runtime roundoff."""
    changes = []
    def visit(a, b, path):
        if type(a) is not type(b):
            raise ValueError("Changed result type at " + path)
        if isinstance(a, dict):
            if a.keys() != b.keys():
                raise ValueError("Changed result fields at " + path)
            for key in a: visit(a[key], b[key], path + "." + key)
        elif isinstance(a, list):
            if len(a) != len(b): raise ValueError("Changed result length at " + path)
            for index, (x, y) in enumerate(zip(a, b)): visit(x, y, path + f"[{index}]")
        elif a != b:
            if type(a) is not float or not math.isclose(a, b, abs_tol=1e-14, rel_tol=1e-12):
                raise ValueError("Changed result value at " + path)
            changes.append({"path": path, "absolute_difference": abs(a-b)})
    visit(left, right, "result")
    return changes


def verify(repository: Path, *, replay: bool = False, tests: bool = False) -> dict:
    repository = repository.resolve()
    manifest = inventory(repository)
    for relative in manifest:
        checked_file(repository, relative, manifest)
    report = {"archive_files_verified": len(manifest), "original_files_changed": 0}
    if not replay and not tests:
        return report
    if any(name == "pgc" or name.startswith("pgc.") for name in sys.modules):
        raise RuntimeError("Run portable verification in a fresh Python process")
    with tempfile.TemporaryDirectory(prefix="graph-study-verify-") as temporary:
        work = Path(temporary) / "reproduction"
        shutil.copytree(repository / "reproduction", work,
                        ignore=shutil.ignore_patterns(".cache", "__pycache__"))
        shutil.copytree(work / "data/sources", work / ".cache/research-data")
        run = work / "results/jev/run-20260918"
        original_manifest = (run / "manifest.json").read_bytes()
        source_manifest = json.loads(original_manifest)
        source_manifest["source_sha256"] = {name.replace("\\", "/"): value
                                            for name, value in source_manifest["source_sha256"].items()}
        sys.path.insert(0, str(work))
        attempts = []

        def blocked(*args, **kwargs):
            attempts.append(True)
            raise RuntimeError("Network disabled during offline research verification")

        try:
            with ExitStack() as stack:
                stack.enter_context(patch.object(socket.socket, "connect", blocked))
                stack.enter_context(patch.object(socket.socket, "connect_ex", blocked))
                stack.enter_context(patch.object(socket, "create_connection", blocked))
                if replay:
                    from pgc.experiments.verify_jev_artifacts import verify as verify_observations
                    from pgc.experiments.run_jev_research import Runner
                    from pgc.experiments.analyze_jev_research import analyze
                    proof = verify_observations(run)
                    names = ("calls.jsonl", "predictions.jsonl", "calibration.json", "results.json")
                    before = {name: (run / name).read_bytes() for name in names}
                    (run / "manifest.json").write_text(json.dumps(source_manifest), encoding="utf-8")
                    runner = Runner(run, live=False)
                    runner.development()
                    runner.evaluate()
                    (run / "manifest.json").write_bytes(original_manifest)
                    analyze(run)
                    comparisons = {}
                    for name, old in before.items():
                        new = (run / name).read_bytes()
                        equal_normalized = old.replace(b"\r\n", b"\n") == new.replace(b"\r\n", b"\n")
                        comparisons[name] = {"raw_bytes_equal": old == new,
                                             "newline_normalized_bytes_equal": equal_normalized}
                        if not equal_normalized:
                            if name != "results.json":
                                raise ValueError("Replay altered a frozen observation or calibration: " + name)
                            comparisons[name]["floating_point_roundoff"] = compare_json(json.loads(old), json.loads(new))
                            comparisons[name]["numeric_tolerance"] = {"absolute": 1e-14, "relative": 1e-12}
                    report["replay"] = {"calls": proof["n_calls_including_probe"],
                                         "predictions": proof["n_predictions"], "artifacts": comparisons,
                                         "temporary_manifest_path_normalization": True}
                if tests:
                    import unittest
                    suite = unittest.defaultTestLoader.discover(str(work / "tests"))
                    result = unittest.TextTestRunner(verbosity=1).run(suite)
                    report["original_tests"] = {"run": result.testsRun, "failures": len(result.failures),
                                                 "errors": len(result.errors), "skipped": len(result.skipped)}
                    if not result.wasSuccessful() or result.skipped:
                        raise ValueError("Original test suite did not pass completely")
            if attempts:
                raise ValueError("An offline stage attempted network access")
            report["network_attempts"] = len(attempts)
        finally:
            (run / "manifest.json").write_bytes(original_manifest)
            sys.path.remove(str(work))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--tests", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(args.repository, replay=args.replay, tests=args.tests)
    if args.output:
        if args.output.resolve().is_relative_to(args.repository.resolve()):
            parser.error("Write verification results outside the immutable input repository")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("PORTABLE_VERIFICATION=" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
