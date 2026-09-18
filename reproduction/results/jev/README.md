# Improving Jev with repeatable experiments

This study keeps **Jev 1.13.0** as the decision model. It compares a corrected Jev baseline against explicit task instructions, alternate typed questions, and six labeled training examples in context. It does not train or substitute another model.

The [frozen protocol](PROTOCOL.md) defines all arms, data uses, metrics, repeat tests and resource caps. The [run directory](run-20260918/) contains the exact plan, prompts, demonstrations, selected IDs, source snapshot, request/response journal, raw predictions, calibration fits and [results](run-20260918/RESULTS.md).

## Measured outcome

The completed run supports a narrow improvement in **Jev entity matching**. Explicit identity instructions plus six training demonstrations (`fewshot_contract`) improved the held-out DBLP–ACM results. The same intervention did **not** establish an improvement in SciFact relation verification.

| Held-out measure | Corrected Jev baseline | Selected Jev formulation |
|---|---:|---:|
| Entity matching: accuracy, 413 pairs | 405/413 (98.06%) | 410/413 (99.27%) |
| Entity matching: macro-F1 | 0.9605 | 0.9859 |
| Entity matching: false merges, 63 different-entity pairs | 8 | 2 |
| Entity matching: missed matches, 350 same-entity pairs | 0 | 1 |
| Relation verification: macro-F1, 339 examples | 0.8508 | 0.8527 |

The paired 95% bootstrap interval for the entity macro-F1 difference is **[+0.0010, +0.0540]**; the relation interval is **[-0.0314, +0.0337]**. These are exploratory, unadjusted intervals on one fixed evaluation split, conditional on development selection. The entity accuracy interval includes zero. The [common-success analysis](run-20260918/common_success_sensitivity.json) reaches the same task-level conclusions after restricting to pairs where both arms returned valid answers.

The original fixtures are secondary diagnostics: entity accuracy improved from **84/88 to 87/88** eligible cases, while relation accuracy fell from **46/50 to 45/50**. Twelve uncertain entity cases receive no correctness credit. Calibration changes probability quality, not labels: it reduced held-out entity Brier and log loss, but relation Brier worsened even as log loss improved. It is not a universal improvement.

**Repeatability was checked in two ways.** An isolated replay with HTTP disabled reproduced all 3,644 predictions and byte-identical results and calibration artifacts ([replay proof](run-20260918/replay_verification.json)). Three fresh service calls on each of 20 fixed examples per task preserved every selected-arm label; their probabilities varied. The relation baseline changed labels on one of its 20 examples. This small repeat panel does not establish future or bitwise determinism.

The run made **3,405 HTTP calls**, used **4,792,778 input tokens**, and cost an estimated **$0.2013** at the recorded [TypeSafe price](https://docs.typesafe.ai/models). Five calls returned probability vectors that failed the frozen normalization rule; they remain failures. The [independent artifact verification](run-20260918/verification.json) passed, including source/data hashes, split isolation, phase completeness, raw-response reconstruction and usage accounting.

All **136 automated tests** pass. The original benchmark JSON files retain their pre-study hashes.

![Paired held-out effects and uncertainty](run-20260918/figures/paired_effects.png)

For subsequent Jev work, retain the selected entity formulation as a candidate and retain the relation baseline. Confirm the entity gain on new independent data before treating it as a general improvement. Any further relation prompt selection needs fresh development data and a new untouched test set. The exact prompts, six demonstrations per task and model pin are preserved in [plan.json](run-20260918/plan.json).

## Integration repairs

The old adapter sent `prompt` and `options` instead of the documented `instructions` and `criteria`, read a Choice distribution from the selected-string field, and supplied a default probability for a missing Noul response. The repaired adapter validates the declared answer space and requested model, maps `probabilities` explicitly, retains errors and raw evidence, and records actual usage once per shared request. Source: [TypeSafe HTTP API](https://docs.typesafe.ai/api).

These repairs establish a valid baseline. They are not counted as an improvement in Jev's semantic ability. Historical error-heavy benchmark results remain separate.

## Reproduce without calling Jev

From the repository root, using the existing Python environment:

```powershell
.venv\Scripts\python.exe -B -m pgc.experiments.verify_jev_artifacts --run-dir results/jev/run-20260918
$replayDir = Join-Path '.cache' ('jev-replay-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $replayDir | Out-Null
Copy-Item -Path 'results/jev/run-20260918/*' -Destination $replayDir -Recurse
.venv\Scripts\python.exe -B -m pgc.experiments.run_jev_research --run-dir $replayDir --stage replay
.venv\Scripts\python.exe -B -m pgc.experiments.analyze_jev_research --run-dir $replayDir
```

Replay reconstructs predictions from saved exact request/response pairs. It fails on a missing response, changed source/plan, or a stored prediction that disagrees with reconstruction. It makes no API calls and does not need a key. The runtime checks source hashes against the captured implementation; retain the matching source snapshot if future code changes.

The commands use a new copy to preserve the original run. Replay adds offline stage records to that copy's manifest, so the regenerated report records a different manifest hash. The saved byte-equality proof additionally restored the copied original manifest before analysis; its recorded calls, predictions, calibration and results all matched exactly.

## Run a fresh comparison

Python 3.12 and [requirements-jev.txt](../../requirements-jev.txt) suffice for this Jev workflow; no GPU or local model download is required. The full repository environment also works. Set `TYPESAFE_API_KEY` in the process environment, then use a **new** directory:

```powershell
.venv\Scripts\python.exe -B -m pgc.experiments.run_jev_research --run-dir results/jev/new-run --stage prepare
.venv\Scripts\python.exe -B -m pgc.experiments.run_jev_research --run-dir results/jev/new-run --stage all --live
```

On first data preparation the runner downloads the public source datasets and verifies their fixed hashes. Preparation freezes the prompts, demonstrations, development/evaluation IDs and source files before research calls. The selected arm is frozen after development; calibration is fitted before evaluation. Running again with the same directory resumes recorded work and reuses its exact response journal. Use a new directory for independent fresh results.

The runner limits concurrency to four and caps HTTP attempts at 4,000 and input-token accounting at 20 million. Unknown usage on failed attempts receives a conservative reservation charge; it is reported separately from measured usage. Monetary charges are estimates at the recorded public price, not a verified invoice. The initial run also includes its tiny authentication/schema probe in the journal and usage totals.

## What repeatability means here

- **Cached replay:** the same recorded outputs reproduce the same predictions, calibration and metrics.
- **Fresh repeats:** three actual service responses on 20 fixed evaluation examples per task measure label and probability variation. Identical cached outputs do not establish fresh-call stability.
- **Batching control:** separate calls are compared with the original development batch on 20 fixed examples per task.

All public-data and original-fixture outcomes remain separate. The fixtures have development history and unadjudicated labels; 12 uncertain ER cases receive no correctness credit. Few-shot prompts add training information and token cost, even though each evaluated candidate and its evidence remain fixed. Quantized service probabilities that fail normalization are retained as errors under the frozen strict policy.

This is a local research runner, not a crash-durable billing system. A hard process failure between an API response and journal append can leave an unrecorded request; a resume may repeat that request. The saved usage is auditable for recorded requests and is not a substitute for provider billing records.
