# Fresh Jev run and updated paper

Executed September 18, 2026, starting from repository commit `8b6a861` (merged PR #10).

Start with [PAPER_UPDATE.md](PAPER_UPDATE.md), the [full current manuscript](../../manuscript/paper-current.md), or its [PDF](../../manuscript/paper-current.pdf).

## Evidence

- Main run: 3,404 fresh HTTP calls; 3,644 prediction records across all seven protocol phases.
- Challenge: 48 additional fresh calls. Public synthetic labels need human review.
- `calls.jsonl`, `predictions.jsonl`, `plan.json`, `manifest.json`, `calibration.json`, `source_snapshot/`: full auditable main-run evidence.
- `verification.json`: independent raw-response, input, split, selection, phase and usage verification.
- `replay-verification.json`: byte-identical offline replay, with networking prohibited.
- `comparison.json`: original-versus-fresh metrics and per-example stability.
- `challenge/`: exact gold-free inputs, raw provider responses, predictions, evaluation and separate execution audit.
- `figures/`: five SVG/PNG pairs: fresh paired effects, original/fresh comparison, fresh calibration, synthetic challenge and archived candidate-loss intervention.
- `archive-figures/` and `archive-evidence-figures/`: regenerated 15- and 10-figure original-evidence suites. These are not fresh-inference analyses.
- `archive-verification.json`: all 161 original files unchanged; original replay and 136 original tests passed.
- `artifact-manifest.json`: SHA-256 inventory of run artifacts, excluding itself.

The fresh run omits the original one-call toy preflight, explaining 3,404 versus 3,405 calls. The main runner is unchanged. The additive fresh verifier adapts the original verifier only for repository paths and optional manifest-declared preflight; it still rejects every unplanned call.

## Offline reproduction

From repository root, use Python 3.12 and `graph_synthesis/requirements-figures.txt`. Download and hash-check datasets with `scripts/download_datasets.py`; copy `reproduction/data/sources/` into `reproduction/.cache/research-data/` before verifying the fresh run. The generated normalized dataset JSON is included among those six pinned files.

```sh
python -B -m graph_synthesis.verify_fresh_jev --run-dir experiments/jev-rerun-20260918
python -B -m graph_synthesis.replay_fresh_jev --run-dir experiments/jev-rerun-20260918
python -B -m graph_synthesis.report_fresh_run --run-dir experiments/jev-rerun-20260918
python -B -m graph_synthesis.semantic_challenge --predictions experiments/jev-rerun-20260918/challenge/predictions.jsonl --output challenge-evaluation.json
python -B -m graph_synthesis.render_current_paper --output manuscript/paper-current.pdf
python -B -m graph_synthesis.falsification --check
```

PDF rendering needs WeasyPrint's native font/Pango dependencies; this PDF was built with the pinned renderer in an isolated WSL Python package directory. No global environment or WSL service was restarted. HTML is also provided. PDF bytes can vary with fonts and platform.

For another **paid live run**, set `TYPESAFE_API_KEY` in the process environment, set `PYTHONPATH` to `reproduction`, and execute `python -B -m pgc.experiments.run_jev_research --run-dir NEW_DIRECTORY --stage all --live`. Use a new directory, not this evidence directory. The existing protocol caps concurrency at four, HTTP attempts at 4,000 and input-token accounting at 20 million. The separate challenge uses `python -B -m graph_synthesis.run_challenge_live --output NEW_CHALLENGE_DIRECTORY --live` and makes at most 48 attempts with no retries.

No credentials are stored in this package. Reproduction reuses saved outputs; fresh inference can change labels and probabilities even with a pinned model identifier. This is the same previously inspected dataset, not a new independent scientific sample.
