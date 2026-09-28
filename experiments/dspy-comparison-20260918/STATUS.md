# DSPy / Jev comparison: actual execution status

## Current live execution (2026-09-28)

Seed 11 completed in [run 36484331133](https://github.com/CompleteDotTech/paper-package/actions/runs/36484331133)
with 294 metric rows, all 32 accepted proposals, and a verified artifact ZIP.
It is retained as standalone evidence. Independent review found a budget
dispatch flaw and an insufficient aggregate provenance check; the runner and
report have been corrected. [Seed 23 run 36487767662](https://github.com/CompleteDotTech/paper-package/actions/runs/36487767662)
was canceled with its partial artifact preserved so the final five seeds can
be executed on one source/data/dependency snapshot. The comparable five-seed
matrix remains incomplete. See the [run plan](LIVE_RUN_PLAN.md) for exact costs,
failed attempts, and execution amendments. No aggregate gain is claimed.

The sections below preserve the preauthorization and offline audit history;
their earlier “blocked” status describes that historical phase.

## Authorized follow-up preparation (2026-09-28)

The user authorized a new live comparison with a $50 total cap and the existing
restricted OmniRoute DeepSeek route for DSPy proposals. The manual workflow now
selects one seed per dispatch and records a conservative $8 per-seed estimated
spend limit. See [the run plan](LIVE_RUN_PLAN.md). This preparation creates no
new five-seed result; the historical status and blockers below remain the
record of what had been executed before this authorization.

**Live with/without-DSPy comparison: NOT COMPLETED. No new Jev inference calls and no new DSPy inference runs were completed.**

## Live execution blockers

[Preflight run 35355158096](https://github.com/CompleteDotTech/paper-package/actions/runs/35355158096) found the mapped TypeSafe key populated, but none of `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY`. It stopped before calling Jev. This does not establish whether differently named or environment-scoped provider credentials exist, or whether the TypeSafe key is valid.

[Diagnostic run 35355491970](https://github.com/CompleteDotTech/paper-package/actions/runs/35355491970) was marked `action_required` with zero jobs. Its gate was left intact. Broad secret-context diagnostics were removed; preflight and live runs are manual-only and use explicitly named keys. Secret values are not in these reports.

## Executed offline checks

**1,092 tests passed; 6 skipped; 16 test suites completed. All 11 deterministic experiment replays passed.** The original 161-file inventory and the existing optimizer inventory also passed verification.

Four SDK contract tests were skipped because SDK packages were not installed in this local runtime; two archived reproduction tests also reported skips. Skips are not counted as passes. An initial reproduction invocation lacked PYTHONPATH; the corrected invocation passed. A later combined wrapper timed out on two replay processes; the individual replay commands recorded below had already passed. Neither failed attempt is treated as an additional successful test.

| Check | Tests discovered | Skipped | Result |
|---|---:|---:|---|
| replay-adaptive | 0 | 0 | passed |
| replay-assumption_aware | 0 | 0 | passed |
| replay-followup | 0 | 0 | passed |
| replay-frontier | 0 | 0 | passed |
| replay-novel_mechanisms | 0 | 0 | passed |
| replay-reliability | 0 | 0 | passed |
| replay-risk_control | 0 | 0 | passed |
| replay-source_structural | 0 | 0 | passed |
| replay-structural | 0 | 0 | passed |
| replay-theory_suite | 0 | 0 | passed |
| replay-uncertainty | 0 | 0 | passed |
| test-graph_synthesis-adaptive-tests | 64 | 0 | passed |
| test-graph_synthesis-assumption_aware-tests | 47 | 0 | passed |
| test-graph_synthesis-corpus-tests | 32 | 0 | passed |
| test-graph_synthesis-dspy_benchmark-tests | 26 | 0 | passed |
| test-graph_synthesis-dspy_jev_optimizer-tests | 35 | 4 | passed |
| test-graph_synthesis-followup-tests | 67 | 0 | passed |
| test-graph_synthesis-frontier-tests | 75 | 0 | passed |
| test-graph_synthesis-novel_mechanisms-tests | 92 | 0 | passed |
| test-graph_synthesis-reliability-tests | 63 | 0 | passed |
| test-graph_synthesis-risk_control-tests | 66 | 0 | passed |
| test-graph_synthesis-source_structural-tests | 86 | 0 | passed |
| test-graph_synthesis-structural-tests | 36 | 0 | passed |
| test-graph_synthesis-tests | 200 | 0 | passed |
| test-graph_synthesis-theory_suite-tests | 37 | 0 | passed |
| test-graph_synthesis-uncertainty-tests | 36 | 0 | passed |
| test-reproduction-tests | 136 | 2 | passed |
| verify-frozen | 0 | 0 | passed |
| verify-optimizer | 0 | 0 | passed |

The machine-readable [validation record](offline-validation-summary.json) includes per-suite status and counts; the downloadable audit bundle also includes commands, durations and log hashes. These runs disabled socket connections and used no inference keys. They reproduce saved observations and algorithm fixtures, not newly optimized model predictions.

## Separate archived calibration analysis

[Archived calibration results](archive-calibration/RESULTS.md) refit fixed calibrators on the original calibration split and score saved test responses. They contain zero fresh inference and zero DSPy runs. Invalid archived response exclusions and denominators are explicit. Do not attribute these results to DSPy.

## Ready-to-run live comparison

[Protocol and commands](../../graph_synthesis/dspy_benchmark/README.md) cover five repeats, two DSPy search objectives, eight original native formulations, seven calibration settings and seven task/panel combinations. The code was tested with controlled doubles, not substituted for live inference.

To execute live, map an authorized generative-provider credential and model into the workflow, resolve the repository Actions approval requirement, and manually run the live workflow. Original manuscripts, predictions and the immutable root manifest remain unchanged.

## Offline integration correction

The comparison workflow is now manual-only and has its own filename so it can
coexist with the separate DSPy optimizer study. A full comparison requires at
least one proposal iteration and verifies the configured proposer's matching
credential before constructing a Jev target backend. Each completed seed writes
a hash inventory of its run files; the downstream report verifies those files,
retains missing/invalid seed statuses, and marks the five-seed matrix incomplete
until all five completed artifacts validate. Baseline-only observations have a
separate summary and cannot fill the primary DSPy table. These corrections were
checked with offline tests and test doubles. The live comparison remains blocked
and no new provider calls or DSPy results were produced by this correction.
