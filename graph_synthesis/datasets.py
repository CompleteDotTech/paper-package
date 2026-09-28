"""Acquire pinned study data without modifying the original archived downloader.

SciFact is fetched from an immutable version of the publisher's S3 object before
the frozen downloader prepares and verifies all six original dataset files.
"""
from __future__ import annotations

import argparse
import hashlib
from http.client import HTTPException
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.request import Request, urlopen


REPOSITORY = Path(__file__).resolve().parents[1]
DESTINATION = REPOSITORY / "reproduction/data/sources"
SCIFACT_NAME = "scifact-data.tar.gz"
SCIFACT_LATEST_URL = "https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz"
SCIFACT_VERSION_URL = SCIFACT_LATEST_URL + "?versionId=8LiW3OUBLBvhehDzrRdGD1ibIaXL.6PQ"
SCIFACT_SOURCES = (SCIFACT_VERSION_URL, SCIFACT_LATEST_URL)
SCIFACT_RECORD = next(row for row in json.loads(
    (REPOSITORY / "scripts/datasets.json").read_text(encoding="utf-8")
) if row["name"] == SCIFACT_NAME)


def checked_scifact(content: bytes, source: str) -> str:
    """Reject changed bytes before publishing a downloaded or supplied archive."""
    observed = hashlib.sha256(content).hexdigest()
    if len(content) != SCIFACT_RECORD["bytes"] or observed != SCIFACT_RECORD["sha256"]:
        raise ValueError(
            f"SciFact integrity check failed for {source}: expected "
            f"{SCIFACT_RECORD['bytes']} bytes, SHA-256 {SCIFACT_RECORD['sha256']}; "
            f"observed {len(content)} bytes, SHA-256 {observed}."
        )
    return observed


def recovery_message() -> str:
    return (
        "Supply the original verified archive with "
        "python -B -m graph_synthesis.datasets --scifact-archive PATH. "
        f"Required SHA-256: {SCIFACT_RECORD['sha256']}. "
        "See graph_synthesis/DATASETS.md; do not change the pinned digest."
    )


def install_scifact(content: bytes, destination: Path) -> None:
    """Publish only checked bytes and remove temporary files if writing fails."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as output:
            temporary = Path(output.name)
            output.write(content)
        temporary.replace(destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def ensure_scifact(destination: Path, local_archive: Path | None = None) -> None:
    target = destination / SCIFACT_NAME
    if local_archive is not None:
        content = local_archive.read_bytes()
        source = str(local_archive)
        try:
            observed = checked_scifact(content, source)
        except ValueError as error:
            raise ValueError(f"{error} {recovery_message()}") from error
        install_scifact(content, target)
    elif target.exists():
        source = str(target)
        try:
            observed = checked_scifact(target.read_bytes(), source)
        except ValueError as error:
            raise ValueError(f"{error} {recovery_message()}") from error
    else:
        failures = []
        for source in SCIFACT_SOURCES:
            try:
                request = Request(source, headers={"User-Agent": "pgc-research-reproduction/1"})
                with urlopen(request, timeout=120) as response:
                    # Bound a changed server response instead of reading it without limit.
                    content = response.read(SCIFACT_RECORD["bytes"] + 1)
                observed = checked_scifact(content, source)
            except (OSError, HTTPException, ValueError) as error:
                failure = f"{source}: {error}"
                failures.append(failure)
                print(f"SciFact source rejected: {failure}", file=sys.stderr)
                continue
            install_scifact(content, target)
            break
        else:
            raise ValueError("No verified SciFact source was available. "
                             + "\n".join(failures) + "\n" + recovery_message())
    print(f"Verified SciFact source {source}: {SCIFACT_RECORD['bytes']} bytes, "
          f"expected/observed SHA-256 {observed}.", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    options = parser.add_mutually_exclusive_group()
    options.add_argument("--check", action="store_true", help="Verify all six local files without network access")
    options.add_argument("--scifact-archive", type=Path, help="Use an existing original SciFact tarball after checking its bytes")
    args = parser.parse_args(argv)
    try:
        if not args.check:
            ensure_scifact(DESTINATION, args.scifact_archive)
        command = [sys.executable, "-B", str(REPOSITORY / "scripts/download_datasets.py")]
        if args.check:
            command.append("--check")
        # The archived preparation and six-file integrity rules remain unchanged.
        return subprocess.run(command, cwd=REPOSITORY, check=False).returncode
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
