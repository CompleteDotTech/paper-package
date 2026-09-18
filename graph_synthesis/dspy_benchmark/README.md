# Repeated DSPy versus Jev benchmark comparison

**Live comparison status: blocked, not completed.** The first CI preflight found
`TYPESAFE_API_KEY` populated, but none of the three explicitly mapped generative
provider keys (`OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`). It stopped
before inference. The next diagnostic was marked `action_required` before any job
ran. The approval gate has not been bypassed. The diagnostic was reduced to
explicit named keys and made manual-only.

## Registered comparison

| Dimension | Fixed configuration |
|---|---|
| Jev target | `jev-1.13.0` |
| Repeats | Seeds 11, 23, 37, 53, 71; fresh isolated cache namespace per repeat |
| Tasks | SciFact relation support; DBLP-ACM entity resolution |
| No-DSPy controls | All four original native formulations for each task, including Noul and few-shot controls |
| DSPy searches | Accuracy and composite objectives; five runs per objective per task = 20 searches |
| Search budget | Eight candidate proposals per search; no test-based early stopping |
| Calibration | Raw; temperature; regularized bias + temperature |
| Calibration-size sensitivity | 25%, 50%, 100% source-group prefixes; raw is reported once |
| Selection data | 29 training and 31 validation examples per task, split from original development only |
| Calibration data | Original 150 relation / 390 entity calibration examples |
| Primary test | Original 339 relation / 413 entity evaluation examples |
| Transfer panels | 50 relation fixtures, 100 entity fixtures, 48 semantic challenges, and the 73/263 multicall input panels |

The full matrix contains 1,470 metric records when every run succeeds. These are
not 1,470 independent experiments. Each frozen prompt is evaluated once per input
panel per repeat; alternative calibration transforms reuse those probabilities.
Twelve entity fixtures labeled `uncertain` remain in prediction files but cannot
be scored against the binary label schema. Their exclusion count is explicit.

The original eight formulations are issued with their original Choice/Noul
question types and demonstrations. DSPy optimizes the contracted Choice baseline
for each task. It does not optimize Jev weights, evolve graph topology, or run
GEPA/MIPROv2. The seven historical multicall execution policies are not replaced
by seven fake DSPy arms: this matrix applies the frozen direct-decision prompts
to their input panels. Existing graph-policy/algorithm suites are separately
replayed; those results are not new model comparisons.

## Boundaries and interpretation

All candidates use training states/labels only in proposal feedback. Validation
selects the winner. All prompt searches for a task are frozen before fitting any
calibrator, and all calibrators for that task are frozen before test inference.
Split hashes and source/entity identity separation are checked. Historical plans
are public and their evaluation sets were previously examined; "held out" means
held out from this optimization, not a never-seen external benchmark.

Temperature scaling leaves decisions unchanged. Bias/temperature can change
labels. The latter uses fixed regularization 0.01 and bounded parameters, never
test-tuned regularization. Probability zeros are clipped to 1e-15 before logs.
Confidence metrics use class probabilities, not Jev's distribution-concentration
field. Lower Brier/log loss/ECE is better; higher accuracy/F1/MCC is better.

Report all seeds, including unsuccessful searches and null/negative gains. Never
pick the best seed using test accuracy. Report means and sample standard deviations;
repeated runs on one test set are not independent datasets. `paired_interval` is
an optional fixed-fit, provided-group bootstrap helper; its intervals are not
simultaneous or multiplicity-adjusted. No significance claim is produced by the
aggregate report.

## Execute, after resolving CI credentials and approval

Use Python 3.12 or newer. From the repository root:

```bash
python -m pip install -r graph_synthesis/dspy_benchmark/requirements.txt
python -B -m unittest discover -s graph_synthesis/dspy_benchmark/tests -v
python -B -m graph_synthesis.dspy_benchmark.run \
  --seed 11 --iterations 8 --workers 4 \
  --output graph_synthesis/dspy_benchmark/runs/seed-11
python -B -m graph_synthesis.dspy_benchmark.report \
  --directory graph_synthesis/dspy_benchmark/runs
```

Set `TYPESAFE_API_KEY`, `DSPY_PROPOSER_MODEL`, and the provider credential required
by that DSPy model. Keys must stay in the CI secret store; do not commit or paste
them into reports. The manual [workflow](../../.github/workflows/dspy-benchmark.yml)
has a five-seed matrix with at most two simultaneous jobs. It never injects keys
into pull-request tests. Select the desired branch when manually dispatching.
Approval/environment protections remain applicable. `--baseline-only` is an
explicit partial-run mode and never counts as a completed DSPy comparison.

The registered eight-iteration matrix has an upper bound of 65,000 logical Jev
requests across five seeds before cache savings, with at most two SDK retries per
request, and 160 DSPy proposal invocations. This is not a dollar-denominated budget
or a guarantee of provider determinism. Each CI seed job has a 120-minute timeout.

Every run writes protocol/config/source hashes, proposals, raw requests and
responses, probability files, calibration parameters, metrics and usage. HTTP
credentials and complete LM configuration dictionaries are not serialized. Each
run directory is new; accidental overwriting is refused. Missing/malformed model
responses terminate the run rather than being silently assigned an accuracy.

## What was actually executed in this change

See [the execution record](../../experiments/dspy-comparison-20260918/STATUS.md).
It distinguishes fresh local regressions, deterministic archived replay, the
blocked live preflight, and [exploratory archived-output recalibration](../../experiments/dspy-comparison-20260918/archive-calibration/RESULTS.md).
The latter contains **zero new model calls and zero DSPy runs**. It must not be
presented as evidence for DSPy gains.

The root immutable `MANIFEST.json` and all archived research files are unchanged.
New files have their own integrity inventory. SDK dependency versions are pinned;
CI also records its complete resolved environment. Method references:
[temperature scaling](https://proceedings.mlr.press/v70/guo17a.html),
[TypeSafe probabilities](https://docs.typesafe.ai/primitives/choice),
[DSPy programs](https://dspy.ai/).
