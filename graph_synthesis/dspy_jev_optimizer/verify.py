"""Verify only this extension; never regenerate or weaken the frozen root inventory."""
from __future__ import annotations

import hashlib
from pathlib import Path

from .core import read_json

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).with_name("artifact-manifest.json")
FROZEN_BLOB = "a8d9f447c266fbedf8837003ceb9639e00778b0e"


def verify(root: Path = ROOT) -> int:
    raw = (root / "MANIFEST.json").read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if blob != FROZEN_BLOB:
        raise ValueError("Frozen research inventory changed")
    manifest = read_json(root / MANIFEST.relative_to(ROOT))
    if manifest["schema_version"] != 1 or not manifest["files"]:
        raise ValueError("Invalid optimizer manifest")
    for name, expected in manifest["files"].items():
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("Unsafe artifact path")
        data = path.read_bytes()
        if len(data) != expected["bytes"] or hashlib.sha256(data).hexdigest() != expected["sha256"]:
            raise ValueError("Optimizer artifact changed: " + name)
    return len(manifest["files"])


if __name__ == "__main__":
    print(f"Verified {verify()} optimizer artifacts and the original research inventory.")
