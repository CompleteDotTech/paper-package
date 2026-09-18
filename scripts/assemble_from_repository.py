"""Collect the paper evidence without changing frozen experiments or source bytes."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "paper-package"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finalize", action="store_true", help="Only refresh the package file manifest")
    args = parser.parse_args()
    PACKAGE.mkdir(exist_ok=True)
    if not args.finalize:
        copied = []

        def copy(source, relative):
            target = PACKAGE / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            copied.append({"source": str(source.relative_to(ROOT)) if source.is_relative_to(ROOT) else str(source),
                           "package_path": relative.as_posix(), "sha256": sha(target), "bytes": target.stat().st_size})

        for directory in ("pgc", "tests", "results"):
            for source in sorted((ROOT / directory).rglob("*")):
                if source.is_file() and "__pycache__" not in source.parts and source.suffix not in {".pyc", ".log"}:
                    copy(source, Path("reproduction") / source.relative_to(ROOT))
        for pattern in ("requirements*.txt", "requirements*.lock", "benchmark*results.json"):
            for source in ROOT.glob(pattern):
                copy(source, Path("reproduction") / source.name)
        for source in (ROOT / ".cache/research-data").iterdir():
            if source.is_file() and source.name in {"scifact-data.tar.gz", "dblp-acm-train.txt", "dblp-acm-valid.txt", "dblp-acm-test.txt", "scifact-prepared.json", "entity_resolution-prepared.json"}:
                copy(source, Path("reproduction/data/sources") / source.name)
        for source in sorted((ROOT.parent / "new-theory").rglob("*")):
            if source.is_file() and "__pycache__" not in source.parts:
                copy(source, Path("background/new-theory") / source.relative_to(ROOT.parent / "new-theory"))
        for source in ROOT.glob("*.md"):
            copy(source, Path("background/historical-documents") / source.name)
        original = Path.home() / "Downloads/deep-research-report (2).md"
        if original.exists():
            copy(original, Path("background/original-research-report.md"))
        for source in (ROOT / "results/jev/run-20260918/figures").glob("*"):
            if source.is_file():
                copy(source, Path("figures") / source.name)
        copy(Path(__file__), Path("scripts/assemble_from_repository.py"))
        write(PACKAGE / "PROVENANCE.json", {
            "assembled_at_utc": datetime.now(timezone.utc).isoformat(),
            "repository": "https://github.com/CompleteTech-LLC-AI-Research/typed-probabilistic-graph-compiler",
            "source_base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "source_worktree": "Includes the documented research changes being committed with this package; file hashes are authoritative.",
            "byte_exact_copies": copied,
            "exclusions": ["API credentials and session logs", "virtual environments", "downloaded model weights and local trained checkpoints", "temporary API launcher", "unavailable workbook/ZIP linked from the supplied report"],
        })
    files = [{"path": p.relative_to(PACKAGE).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)}
             for p in sorted(PACKAGE.rglob("*")) if p.is_file() and p.name != "MANIFEST.json" and "__pycache__" not in p.parts]
    write(PACKAGE / "MANIFEST.json", {"algorithm": "sha256", "scope": "All package files except this manifest and interpreter caches", "files": files})
    print(json.dumps({"package": str(PACKAGE), "files": len(files), "bytes": sum(p["bytes"] for p in files)}))


if __name__ == "__main__":
    main()
