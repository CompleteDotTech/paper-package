# DSPy versus Jev benchmark execution

[Comparison protocol and runner](graph_synthesis/dspy_benchmark/README.md) ·
[Actual execution status](experiments/dspy-comparison-20260918/STATUS.md) ·
[Completed five-seed live results](experiments/dspy-comparison-20260918/live-five-seed-20260928/README.md) ·
[Archived-output calibration check](experiments/dspy-comparison-20260918/archive-calibration/RESULTS.md)

The five-seed live comparison **completed** on one source/data/dependency
snapshot. All five raw artifacts and the 294-row aggregate passed inventory,
protocol, matrix, and cost-receipt checks. The full results, per-seed metrics,
run links, guarded spend, failed-attempt history, and raw evidence release are
linked above. The results do not show a uniform DSPy advantage over all
registered no-DSPy controls.

The comparison code registers five isolated repeats, two search objectives, eight
native legacy formulations and seven calibration settings per frozen arm. New
local regression and archived-replay checks are recorded separately from model
performance. Historical evidence and the root immutable manifest are unchanged.
