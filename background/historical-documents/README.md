# Typed probabilistic graph compiler

**Current focus: improving Jev results.** The completed [Jev study](results/jev/README.md) improved entity-matching macro-F1 from **0.9605 to 0.9859**, reducing false merges from **8 to 2** on 413 held-out pairs. Relation verification showed no resolved improvement. The same pinned model was used throughout, with development-only selection, separate calibration, exact cached replay and fresh-call repeat tests.

The self-contained [paper package](paper-package/README.md) brings the manuscript draft, verified bibliography, methods, tables, figures, original research context, complete Jev evidence and executable reproduction materials into one directory.

This repository also contains earlier specialist experiments and an in-memory graph compiler. Their [results and limitations](RESULTS_REPORT.md) remain available separately and do not establish a Jev improvement. Historical publication drafts are retained with supersession notices; their headline comparisons are not the current evidence.

The theory and original audit live in [../new-theory](../new-theory/README.md). The implementation covers canonical support/refute/unknown decisions, trained pairwise identity classification, calibrated probabilities, typed mutations, atomic graph/provenance transactions, and controlled experiments on evidence dependence, joint identity inference, dependency risk, and query allocation.

## Earlier specialist and compiler work

| Experiment | Data and execution | Main observation |
|---|---|---|
| Evidence and calibration | Real pinned NLI model; 339 unique held-out SciFact claim/document pairs | Full evidence: 47.20% accuracy versus 40.41% with 80 characters; calibration lowers full-evidence Brier from 0.9496 to 0.6136 |
| Identity training and ablations | Three locally trained models; 413 identity-disjoint DBLP–ACM pairs | Full context: 98.06% versus 95.64% lexical; context-only gain unresolved |
| Original fixture diagnostics | Real models through repaired 50/100-example harnesses | ER transfer is poor: 51.14% on 88 binary-labeled examples versus 86.36% always-same |
| Compiler and advanced policies | Deterministic graph scenarios and explicitly synthetic simulations | State invariants pass; policy benefits depend on assumptions and can reverse under shift |

Accuracy numbers across these rows describe different tasks and cannot be compared as one benchmark. See the report for paired intervals, class imbalance, source hashes, and negative results.

## Install and verify

Tested on Windows with Python 3.12.10, an RTX 3060, PyTorch 2.8.0+cu128, and Transformers 4.57.6. These PowerShell commands create the tested environment; the lock records all installed packages. Public data and model downloads are required on first use. No API keys are needed.

```powershell
uv venv --python 3.12.10 .venv
uv pip install --python .venv\Scripts\python.exe torch==2.8.0 --index-url https://download.pytorch.org/whl/cu128
uv pip install --python .venv\Scripts\python.exe -r requirements-research.lock
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.venv\Scripts\python.exe -B -m pgc.experiments.scifact_walkthrough
```

The walkthrough uses an explicitly enabled deterministic diagnostic backend. See [compiler quickstart](pgc/QUICKSTART.md) for real adapters and graph operations. NLI/ER research and fixture runners support CPU inference with `--device cpu`; these recorded neural runs and the separate CUDA-only compiler smoke used CUDA. Bitwise training equality across different hardware/library versions is not promised.

## Reproduce the experiments

Original artifacts are in [results/research](results/research/). Use a fresh output location for reruns:

```powershell
.venv\Scripts\python.exe -B -m pgc.experiments.research_data
.venv\Scripts\python.exe -B -m pgc.experiments.run_nli_research --device cuda --output results/reproduction/nli/nli_results.json
.venv\Scripts\python.exe -B -m pgc.experiments.run_er_research --device cuda --epochs 2 --batch-size 8 --max-length 256 --reuse-checkpoints --output-dir results/reproduction/er
.venv\Scripts\python.exe -B -m pgc.experiments.run_fixture_diagnostics --device cuda --output results/reproduction/fixtures/fixture_diagnostics.json
.venv\Scripts\python.exe -B -m pgc.experiments.run_compiler_research --output-dir results/reproduction/compiler
.venv\Scripts\python.exe -B -m pgc.research.advanced_experiments --output results/reproduction/advanced/advanced_experiments.json
.venv\Scripts\python.exe -B -m pgc.experiments.run_real_compiler_smoke
.venv\Scripts\python.exe -B -m pgc.experiments.verify_research_artifacts
.venv\Scripts\python.exe -B -m pgc.experiments.plot_research_results
```

On a fresh checkout, `--reuse-checkpoints` trains missing ER checkpoints. On this machine it reuses the three existing local checkpoints only after verifying the training configuration and data hash. For a fresh training replication, omit that flag and pass a new directory such as `--checkpoint-dir .cache/models-replication`. Fixture diagnostics use `.cache/models/er-full-context`. Checkpoints, downloaded data, and the Python environment are ignored by Git; model/configuration hashes and predictions are recorded in the result files. The complete pinned public NLI revision is `fa2804872c3b4bd748f38c0185cc85775361e735`.

The verifier checks the primary saved artifacts and prepared data without model calls. Data preparation verifies download hashes and isolation; it writes the current data manifest. Plotting reads the primary saved JSON and regenerates SVG/PNG figures. Synthetic and fixture reruns and the integration smoke regenerate their selected output files. NLI and ER refuse to replace a completed primary result.

## Code map and boundaries

- [Evaluation](pgc/evaluation.py): declared labels, finite normalized probabilities, proper scores, errors and coverage.
- [Local adapters](pgc/decision/): actual model inference or explicit failure, raw logits and execution provenance. ER requires a trained identity checkpoint.
- [Compiler](pgc/compiler/orchestrator.py) and [graph store](pgc/compiler/graph_store.py): typed decisions, evidence binding, declarative constraints, atomic application, version checks and idempotent retries.
- [Research policies](pgc/research/policies.py): independent-source aggregation, bounded exact identity clustering, dependency accounting and routing.
- [Tests](tests/) and [artifact verification](results/research/validation.json): behavioral regressions and reproducibility checks.

The store is in memory, with no crash-durable database adapter. Supported mutations are node/edge creation, type addition, and property assignment; physical entity merges and schema migrations reject. Pairwise ER predictions do not directly implement the compiler's entity-ID choice protocol. Internal certificate hashes bind records but do not authenticate sources or prove semantic truth. Estimated neural probabilities do not establish formal risk guarantees.
