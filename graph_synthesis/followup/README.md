# Five evidence-driven follow-up improvements

Start with [RESULTS.md](RESULTS.md). The [protocol](PROTOCOL.md) was committed before this suite was executed, after the existing original and rerun findings were known. That makes these exploratory follow-ups, not independent confirmation.

The strongest empirical lead is **edge-aware routing**: on the same-data rerun, the selected calibration-only policy emits 173 correct and 19 wrong relationship edges, matching all-few-shot aggregate counts with 63.52% fewer recorded input tokens. It differs on two labels, so identical counts do not mean identical outputs. This is a token-accounting counterfactual, not a measured fresh-service speedup. The guarded calibration primary target and cross-run stability primary target fail. Interval-aware validation and lineage bounds pass their controlled finite tests, with explicit assumptions and negative controls.

## Execute

```bash
python -B -m unittest discover -s graph_synthesis/followup/tests -v
python -B -m graph_synthesis.followup.run --check
python -B -m graph_synthesis.followup.report --figures --update-paper
python -B -m graph_synthesis.render_current_paper --output manuscript/paper-current.pdf
```

Numerical execution uses the Python standard library and existing repository adapters. Rendering uses the existing pinned `graph_synthesis/requirements-figures.txt` environment. The output JSON includes original/rerun observation hashes, source-component purge audit, all calibration grids, per-arm/run metrics, operational failures, descriptive intervals and controlled-case hashes. Five plots are supplied as SVG and high-resolution PNG. The current full manuscript incorporates the report ahead of the unchanged original study; the 161-file frozen archive remains intact.

## What is implemented

`methods.py` supplies gold-free transformation/routing/stability execution, calibration-only fit functions, a three-way interval/scope conflict guard, and duplicate/shared-lineage probability bounds. `run.py` verifies exact captured inputs and raw answers, executes all five benchmarks, and checks regeneration. `report.py` derives tables, plots and the additive current-paper section from computed results. `tests/` tests failure paths, no-label-leakage interfaces, full-denominator recall, finite oracles and reproducibility across hash seeds.

None of these methods replaces the default compiler. Missing/unsupported scope must be staged by a caller; the guard only identifies conflicts and does not choose truth. Input-token savings exclude execution infrastructure and review cost. The repeated evaluations must not be counted as independent documents.

## Why the lineage bounds hold under the stated model

Each proof is the conjunction of supplied independent primitive events. Its probability is the product of its distinct atom probabilities. Within a connected shared-atom component, the probability of the union is at least the largest proof probability and at most the sum of proof probabilities, capped at one. Different components use disjoint primitive sets, so under the supplied primitive-independence assumption they are independent. Applying `1 - product(1 - p)` to their lower and upper bounds preserves order and bounds the total union. Duplicating a proof does not change its set of atoms and is removed before calculation.

This is not a guarantee for arbitrary Jev confidence scores, correlated unrecorded sources or incorrectly discovered lineage. A deliberately corrupted-lineage control produces a false 0.96 lower bound for an actual 0.80 event. The finite oracle and random property tests are implementation checks, not a substitute for the assumptions above.
