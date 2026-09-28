# Reporting correction for ambiguous entity fixtures

The entity primary jobs completed all five real DSPy searches, all 390 calibration
inputs, all 413 held-out pairs, and all 100 fixture inputs. Reporting then rejected
the 12 fixture rows whose original gold label is `uncertain`, outside the task's
fixed binary `same`/`different` label schema. A CI failure at that point is not a
missing inference observation and does not justify paying to repeat completed calls.

This correction restores the original research analyzer's semantic-eligibility
convention: classification metrics and paired comparisons use the 88 binary-labelled
fixtures; all 100 predictions remain in the raw and reconstructed evidence. The 12
uncertain fixtures receive a separate descriptive report of confidence, entropy and
high-confidence decision rates. They are not relabelled, counted as correct or
silently removed from the inventory. No binary Brier, NLL or accuracy is defined for
an uncertain gold label. The complete original source analyzer already excludes
labels outside each task's label schema from semantic metrics and paired intervals.

This is a reporting correction made after the first primary evaluation scores were
available, not a newly preregistered scoring rule. It changes no prompt, seed,
calibrator, search choice, source input or main held-out test metric. Original partial
files are preserved with hashes. Completion succeeds only when every required frozen
search and every raw calibration/test response is present and its request can be
reconstructed exactly. Missing evidence remains a failure; no synthetic prediction
or repeated paid inference substitutes for it.

Completed capture manifests distinguish the original live observations from this
zero-inference report reconstruction. The original workflow status remains recorded
as failed where applicable. Downstream transfer and repeatability runs consume the
verified complete raw observations and frozen prompts, not a fabricated successful
workflow status.
