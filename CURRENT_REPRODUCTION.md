# Reproduce the current repository

Run these commands from the root of a fresh checkout of this repository. Use Python 3.12. Keep the virtual environment and verification report in the parent directory so they are outside the archived package inventory.

## Windows PowerShell

```powershell
py -3.12 -m venv ..\paper-package-verify-venv
..\paper-package-verify-venv\Scripts\python.exe -m pip install -r graph_synthesis/requirements-verification.txt
..\paper-package-verify-venv\Scripts\python.exe -B -m graph_synthesis.datasets
..\paper-package-verify-venv\Scripts\python.exe -B -m graph_synthesis.datasets --check
..\paper-package-verify-venv\Scripts\python.exe -B -m graph_synthesis.verify --replay --tests --output ..\paper-package-verification.json
```

## Linux or macOS shell

```sh
python3.12 -m venv ../paper-package-verify-venv
../paper-package-verify-venv/bin/python -m pip install -r graph_synthesis/requirements-verification.txt
../paper-package-verify-venv/bin/python -B -m graph_synthesis.datasets
../paper-package-verify-venv/bin/python -B -m graph_synthesis.datasets --check
../paper-package-verify-venv/bin/python -B -m graph_synthesis.verify --replay --tests --output ../paper-package-verification.json
```

Dependency installation and dataset acquisition need network access. The downloader obtains four pinned source files, regenerates two prepared splits, and checks the sizes and SHA-256 hashes of all six files against `scripts/datasets.json`. The downloaded files live in the Git-ignored `reproduction/data/sources/` directory. The `--check` command verifies those six local files without downloading them again. See the [dataset acquisition guide](graph_synthesis/DATASETS.md) for the pinned SciFact source and recovery from an exact local archive if that source is unavailable.

The verifier checks all 161 files in the original archive against `MANIFEST.json`, then copies the reproduction runtime to a temporary directory. Replay and the original test suite run there with network connections blocked; they make no live model calls and require no API key. The verifier prints `PORTABLE_VERIFICATION` and writes the same JSON report to `../paper-package-verification.json`. A passing report has `original_files_changed: 0`, `network_attempts: 0`, zero original test failures and errors, and replay artifact comparisons. Newline normalization and narrowly bounded floating-point roundoff are reported explicitly; a passing replay is not a claim of bitwise equality across operating systems.

The root [REPRODUCE.md](REPRODUCE.md) records how to run the original closed 161-file archive. Its `scripts/verify_package.py` command rejects this expanded checkout by design. Use `graph_synthesis.verify` above for current main. The [graph synthesis guide](graph_synthesis/README.md) describes additional experiments and checks. Optional fresh service experiments are described in the archived guide; they require a key, network access, and paid model calls, and are separate from this offline replay.
