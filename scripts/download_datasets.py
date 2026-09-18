"""Download pinned public datasets and regenerate the study's prepared splits.

Uses only the Python standard library. Files are stored in an ignored directory;
existing files are verified rather than downloaded again.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

PACKAGE = Path(__file__).resolve().parents[1]


def verify_datasets(directory):
    records = json.loads((PACKAGE / "scripts/datasets.json").read_text(encoding="utf-8"))
    for row in records:
        path = directory / row["name"]
        if not path.is_file():
            raise ValueError(f"Missing {path}; run python -B scripts/download_datasets.py first")
        content = path.read_bytes()
        if len(content) != row["bytes"] or hashlib.sha256(content).hexdigest() != row["sha256"]:
            raise ValueError(f"Dataset integrity check failed: {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify local files without downloading")
    args = parser.parse_args()
    destination = PACKAGE / "reproduction/data/sources"
    if not args.check:
        sys.path.insert(0, str(PACKAGE / "reproduction"))
        from pgc.experiments import research_data

        destination.mkdir(parents=True, exist_ok=True)
        # Use the frozen preparation code without modifying archived source hashes.
        research_data.DATA_ROOT = destination
        for name, loader in (("scifact", research_data.scifact),
                             ("entity_resolution", research_data.entity_resolution)):
            splits, _ = loader()
            # Archived prepared files were written with Windows CRLF newlines.
            content = json.dumps(splits, indent=2).replace("\n", "\r\n").encode("utf-8")
            target = destination / f"{name}-prepared.json"
            with tempfile.NamedTemporaryFile(dir=destination, delete=False) as output:
                temporary = Path(output.name)
                output.write(content)
            try:
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
    verify_datasets(destination)
    print("Verified all six dataset files against the archived SHA-256 hashes.")


if __name__ == "__main__":
    main()
