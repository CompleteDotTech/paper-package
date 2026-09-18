# Reproducing the paper package

Use Python 3.12. The package is self-contained for offline Jev reproduction after installing NumPy. First run `py -3.12 -B scripts/download_datasets.py` from this directory. This downloads the four public source files, regenerates both prepared splits, and verifies all six files against the archived SHA-256 hashes. Downloads require network access; subsequent replay is offline. The files are stored in the Git-ignored `reproduction/data/sources/` directory. Use `--check` to verify them again without network access. The verifier uses a temporary copy and leaves the evidence directory unchanged.

From this directory on Windows, create the environment outside the package so its archival file inventory stays unchanged:

```powershell
py -3.12 -m venv ../jev-paper-venv
..\jev-paper-venv\Scripts\python.exe -m pip install -r reproduction/requirements-jev.txt
..\jev-paper-venv\Scripts\python.exe -B scripts/verify_package.py --replay
```

The manifest verifier rejects extra or missing package files, excluding Git metadata, interpreter caches, and local dataset/cache directories. Downloaded datasets are checked separately before replay or tests. On Linux or macOS, use `python3.12` and the environment's `bin/python` equivalent. Frozen manifests contain Windows path strings; the verifier normalizes them when resolving source paths.

An existing full research environment can also run (after downloading the datasets):

```powershell
..\.venv\Scripts\python.exe -B scripts/verify_package.py --replay --tests
```

`--tests` runs the complete copied test suite and requires the broader dependencies in `reproduction/requirements-research.lock`; it is not required for NumPy-only Jev replay. Model downloads and live inference are not performed by the copied offline tests.

## What is checked

1. Every archived file matches its size and SHA-256 in `MANIFEST.json`.
2. Raw and prepared data match the frozen hashes; splits, demonstrations and development examples satisfy the recorded identity/component separation.
3. Planned phases, requests and predictions are complete and reconstruct from actual saved responses. Invalid probability vectors remain failures.
4. The local runner replays all phases with network access disabled. It restores the copied original run manifest before deterministic analysis, then checks byte equality for calls, predictions, calibration and results.
5. Optional tests run from that copied runtime. The original package receives no new experiment records.

The verifier can write a machine-readable report using `--output PATH` outside the package. `validation/package-validation.json` records the executed portable-copy check. Its recorded manifest hash refers to the pre-validation inventory: archiving the validation report and finishing the prose necessarily creates a later package manifest. Integrity is always checked against the current `MANIFEST.json`.

## Regenerate presentation artifacts

From the package directory, using the required dependencies:

```powershell
python -B scripts/generate_tables.py
python -B reproduction/pgc/experiments/plot_jev_results.py --run-dir reproduction/results/jev/run-20260918
```

The figure generator additionally requires Matplotlib. These commands derive presentation artifacts from existing results and do not call Jev. Run them on a copy when preserving the exact package manifest.

## Optional fresh service experiment

Fresh calls require a TypeSafe key supplied through `TYPESAFE_API_KEY`, consume paid service usage and need network access. They are not part of the offline verification above. In a writable copy of `reproduction/`, populate `.cache/research-data` from `data/sources/`, then:

```powershell
python -B -m pgc.experiments.run_jev_research --run-dir results/jev/new-run --stage prepare
python -B -m pgc.experiments.run_jev_research --run-dir results/jev/new-run --stage all --live
```

Use a new run directory. The recorded pin is `jev-1.13.0`; current availability and pricing may change. The code caps attempts, input-token accounting and concurrency as specified in the frozen protocol. The inference source snapshot covers five core modules; the package additionally captures the complete project source needed by their imports. Neither this snapshot nor fresh repeats establish vendor weight immutability or training-data independence.

## Assembly provenance

The repository-level `scripts/assemble_paper_package.py` collects byte-exact copies, then writes the package inventory. The copy `scripts/assemble_from_repository.py` is an archived assembly source, intended to be run from its original repository layout, not an additional standalone reproduction entry point. Final assembly uses `--finalize` after manuscript files and validation reports are complete.
