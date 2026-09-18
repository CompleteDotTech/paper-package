# Jev same-model experiment protocol

Status: **Design frozen at 2026-09-18 00:41:53 UTC, before live development.** The coordinator agreed the arm design and resource caps before this freeze. Before live development calls, the executable manifest must also record this document's hash, exact prompt/payload hashes, subset IDs, code/data hashes, UTC timestamp, and any departures. This local protocol is not an external preregistration. Existing public and fixture labels have already been used in repository research; these are held out from this Jev selection procedure, not an independently blinded benchmark.

## Question and invariants

Can a corrected Jev integration, explicit evidence-sensitive instructions, training-only demonstrations, or a task-appropriate Jev primitive improve decisions from **`jev-1.13.0`**, while preserving candidate records and canonical output meanings? No alternative model family, new learned classifier, fine-tuning, or architecture is part of this experiment.

Hold claim/record pairs, candidate evidence bytes, label order and definitions, parser validation, scoring code, and model version fixed. Few-shot arms deliberately add six training demonstrations but retain identical evidence for the evaluated candidate. Full-versus-prefix evidence comparisons are deferred from this run; they would change evidence availability and need their own declared comparison. Do not select evidence with gold labels or rationale sentence IDs.

The corrected baseline must use the same valid API schema and label mapping as every new arm. Report any old integration failure separately; do not count repairing malformed output parsing as a semantic modeling improvement. Record the requested model ID and any model/version returned by the service. A pinned request identifier alone does not prove immutable server weights.

## Data and use of labels

Use the already prepared files under `.cache/research-data/` and their source/split hashes in `results/research/data_manifest.json`; do not regenerate membership after examining Jev scores.

| Task | Prepared train | Calibration | Evaluation | Independent evaluation unit |
| --- | ---: | ---: | ---: | --- |
| SciFact cited-abstract relation | 459 | 150 | 339 | 247 connected claim/document/duplicate-abstract components |
| DBLP-ACM identity matching | 4,592 | 390 | 413 | One pair; held-out pairs have disjoint underlying identities |

SciFact evaluation is classification of supplied cited abstracts from official development claims, not open-corpus retrieval or official leaderboard test performance. DBLP-ACM evaluation follows the repository's identity-group split and held-out maximal matching; its label mixture differs substantially from training. Keep task results separate.

Select six **training** demonstration examples per task by a deterministic rule: SciFact two per canonical class from distinct components; ER three `same` and three `different`, prioritizing negative examples with the executable selector's lexical similarity of at least `0.65`. Save the similarity definition, ordering, fallback if too few qualify, and selected IDs in the manifest. Demonstration labels are permitted training information. Do not choose demonstrations by Jev development outcomes.

Use exactly 60 additional **training** examples per task for arm selection. Freeze the selection function and exact IDs before calls. For SciFact, rank components by a seeded SHA-256 digest and choose one row per component, excluding every demonstration component. For ER, greedily select 60 identity-disjoint rows in a seeded hash order, excluding every row sharing either identity group with a demonstration. ER's prepared `group` field is a row ID, so it is not an adequate identity-exclusion key; use `identity_groups`. Seed: `20260917`. Record achieved counts explicitly and stop preparation if this disjoint subset cannot be obtained.

The remaining training rows are unused. The calibration split is reserved exclusively for the predeclared temperature fit after arm selection; it must not choose prompts, primitives, evidence length, or the winning arm. Evaluation and fixture labels must not drive any of those choices. Any later change informed by evaluation outcomes is a new exploratory experiment and must be named as such.

Fixtures are secondary integration/domain-transfer diagnostics: 50 relation examples and 100 ER examples. Score only the 88 binary ER labels for binary correctness/probability metrics; report the 12 `uncertain` cases and predictions separately. Do not map `uncertain` to either binary label or count it as a service error.

## Agreed arms

| Task | Arm | Change from corrected baseline |
| --- | --- | --- |
| Relation | `baseline_choice` | Correct Choice transport, canonical labels, full supplied abstract and actual claim, generic task instructions |
| Relation | `evidence_contract` | Choice with explicit SUPPORTS/REFUTES/NOT_ENOUGH_INFO definitions; require evidence for the actual claim, distinguishing contradiction from missing evidence |
| Relation | `conditional_nouls` | Two binary questions: support probability `s`, and refutation probability `r` conditional on absence of support; fixed chain mapping below |
| Relation | `fewshot_contract` | Evidence-contract Choice plus six training-only demonstrations |
| ER | `baseline_noul` | Generic same-entity question, full supplied record fields, corrected Noul transport |
| ER | `identity_contract` | Choice with explicit same-entity identity test using all supplied fields; distinguish related records from aliases |
| ER | `identity_noul` | Refined identity criterion in Noul form, `P(same)=p`, `P(different)=1-p` |
| ER | `fewshot_contract` | Identity-contract Choice plus six training-only demonstrations |

Choice options must map explicitly and bijectively to canonical labels. Noul is a binary truth response, not a three-class relation distribution. Reject missing, nonfinite, negative, out-of-range, wrong-key, or non-normalized responses under the existing evaluator's contract. Preserve the raw response for audit. Do not silently replace missing probabilities with 0.5 or repair failed outputs into successful predictions.

The conditional Noul arm maps validated binary outputs to `SUPPORTS=s`, `REFUTES=(1-s)*r`, and `NOT_ENOUGH_INFO=(1-s)*(1-r)`. This nonnegative mapping sums to one by construction; it is not post-hoc repair of malformed service output. The second question must explicitly ask about refutation conditional on lack of support. Preserve both raw binary outputs. The constructed chain score is not guaranteed to be a calibrated joint distribution or semantic truth; coherent normalization alone is insufficient. Fail the whole logical example if either constituent answer fails validation. A standalone Noul answer never substitutes for the three-class relation distribution.

For efficiency, the three non-few-shot variants may share one evidence state through separate questions in a batched API request. Record the exact co-batched questions. Few-shot requests use separate states/calls so baseline requests never receive demonstrations. Changing the co-batched question set can affect a service and must be distinguished from changing candidate evidence.

For each task, select the best **nonbaseline** variant by descending development operational macro-F1 over the canonical labels, then lower full-sum Brier, then stable lexical arm ID. Report Brier denominators and assign an unavailable Brier a worst tie-break value. Report every development score, including baseline, and whether the selected variant beats baseline on development. Selection does not promise improvement: compare the selected variant with baseline even if all variants score worse. Freeze selected identity before accessing calibration labels through the fitting routine or running evaluation requests.

## Calibration

Fit one positive scalar temperature for **each baseline and selected arm** separately on each task's calibration split, using only successful, validated probabilities. Transform fixed probability outputs with

`p_T(k) = exp(log(max(p(k), 1e-15))/T) / sum_j exp(log(max(p(j), 1e-15))/T)`.

Choose `T` in the fixed interval `[0.05, 20]` to minimize calibration mean log loss. Include `T=1` as an explicit candidate, break equal minima toward `T=1`, and report boundary fits, fit IDs/hash, valid and failed counts, class counts, clipping counts, and calibration loss before/after. If calibration has no valid rows, report the fit as unavailable. A missing canonical class among valid calibration responses is an explicit reliability limitation.

Compute calibrated evaluation scores from exactly the same raw calls; calibration needs no new evaluation inference. Report raw and calibrated distributions separately. Positive scalar temperature preserves the ranking and predicted class except possible clipping ties; it cannot be credited with an ordinary accuracy improvement. Normalized probabilities and successful fitting do not certify calibrated semantic truth. This one-parameter fit is postprocessing of Jev outputs, not training a replacement decision model.

## Primary comparison and reporting

The primary endpoint per task is the selected arm's **operational macro-F1 minus the corrected baseline's operational macro-F1** on the full evaluation set. Service failures count as `ERROR` in operational classification, not as abstentions excluded from the denominator. Run both baseline and selected arm on all 339/413 evaluation rows; unselected variants are development-only. Report a negative or inconclusive result without substituting a different variant selected on evaluation scores.

Report paired 95% percentile intervals from 2,000 bootstrap draws with seed `20260917`: resample SciFact components and retain all rows in each sampled component; resample ER evaluation pairs. Recompute the nonlinear metric in each draw. Report intervals for macro-F1 and accuracy. These intervals condition on the selected prompts, model service, fixed selection/calibration data, and observed calls; they do not estimate training or server-version uncertainty. Treat the two task claims and extra arms as separate descriptive comparisons, with no claim of familywise significance from unadjusted intervals.

Also report operational accuracy, balanced accuracy, per-class support/recall/F1 and confusion, total/valid/failed counts, validation errors, and excluded-gold counts. Brier uses the full sum over classes (range 0 to 2), including both coordinates for binary ER. Log loss uses natural logarithms and clips gold probabilities at `1e-15`. Report each probability metric's valid-response denominator and paired score deltas on the **common-success** subset; differing coverage can otherwise confound a comparison.

Calibration diagnostics: raw and calibrated Brier/log loss; ten fixed confidence bins with counts and empirical accuracy; ECE as a descriptive bin-dependent statistic; and accuracy/coverage at the fixed thresholds `0, .5, .7, .8, .9, .95`. Do not choose a threshold on evaluation labels or present the best threshold as a validated deployment policy. Probability reliability is empirical and dataset-specific.

Report token usage and its coverage, elapsed wall time, per-request latency distribution, error/retry counts, and successful cached versus fresh calls. Separate questions, logical examples, physical HTTP requests, and billable attempts if batching or retries make them differ. Do not pool task scores or use fixtures to inflate the public-data denominator.

## Repeatability and replay are separate checks

Before outcome inspection, select 20 evaluation IDs per task by a seeded hash of the ID; do not select by confidence or correctness. Obtain **three total fresh outputs** per ID for baseline and selected arm. The original evaluation call may count as round one only when its complete semantic payload and co-batched questions are identical to the repeat request. Otherwise issue three separate fresh rounds and keep the original call outside this analysis. Bypass the local response cache for every additional round. Preserve question keys and option order; transport trace IDs may differ. Timestamp every attempt and log service model/version metadata if supplied. Label the actual UTC time window; immediate repeated calls do not establish stability across days or model deployments.

Across all three round pairs, report valid-pair count, exact top-label agreement, mean and maximum total variation distance `0.5*sum_k(abs(p_a(k)-p_b(k)))`, maximum absolute coordinate change, exact probability-vector equality, and round-specific errors and metrics. Also report the count of examples with identical labels in all three fresh rounds. Do not treat the 60 observations as 60 independent examples or the pairwise comparisons as independent trials. Three rounds over 20 examples diagnose repeatability; they do not establish long-term determinism or new aggregate accuracy gains. Preserve provenance for whichever fresh evaluation call supplies round one.

On 20 deterministic development rows per task, additionally compare non-few-shot variants' batched answers with fresh separate-question calls. Fix these IDs before inspecting outcomes. The normal development batch can supply the batched observation when its payload matches. Report the same label/probability drift and service-error diagnostics. This exploratory systems control measures batching sensitivity on development examples; it is not another held-out accuracy contest and does not alter arm selection, prompts, or calibration.

An offline cached replay must reconstruct canonical distributions, selected-arm metrics, calibration, and comparisons from saved responses using the same code/data/prompt hashes. Report exact equality of recomputed artifacts or numeric tolerances explicitly. Cached replay exercises the artifact/parser/scoring pipeline; it supplies **no evidence that the remote service repeats fresh predictions**. Never mark a replayed response as a fresh request.

## Budget and execution order

The fixed workload comprises 60 development rows per task through four variants; 150/390 calibration rows through baseline and selected variant; 339/413 evaluation rows through baseline and selected variant; 20 evaluation rows per task with three total fresh outputs per retained variant; 20 development rows per task for batching controls; and all 50 relation/100 ER fixtures through baseline and selected variant. Conditional Noul uses two questions per logical arm prediction. Shared-state batching reduces HTTP requests but not the number of reported logical predictions.

Enforce hard caps of **20 million input tokens** with a conservative per-call reservation and **4,000 HTTP attempts**, at most **four concurrent requests**, and at most **two retries per request**. Every retry consumes the same shared attempt and token budgets; there is no uncounted probe allowance. At the coordinator's documented rate `$0.042 / million input tokens`, the token ceiling corresponds to **$0.84 estimated input-token charges**. Preserve the verified pricing source/date in the manifest; this estimate is not a verified bill and excludes unknown charges. Account for probes, retries, failed requests with known usage, and repeats; preserve absent usage as unknown rather than zero. Stop visibly if reliable reservation/accounting is impossible.

If both selected variants are few-shot and therefore require separate states, the plan requires about 3,404 HTTP requests before retry/probe overhead (240 development; 1,080 calibration; 1,504 evaluation; 160 repeat requests beyond original calls; 300 fixture; 120 separate-arm batching controls, potentially more if conditional questions are sent individually). The 4,000-attempt ceiling includes remaining overhead; repeated errors can still exhaust it. Never silently omit remaining stages or call a capped partial run complete.

Execute in this order: adapter/offline checks and, if needed, a tiny live toy-input authentication/schema check; freeze protocol, arm prompts, demonstrations, development/control/repeat IDs and caps; development calls and selection; freeze selected arm; calibration calls and temperature fit; full evaluation calls; fresh repeats; fixture diagnostics and the independent development batching control; offline analysis/replay and artifact verification. The initial toy check must contain no research examples and cannot select a research prompt or arm. Each stage writes append-only attempt evidence with UTC request times. Credentials are never stored in research artifacts. A correction required after seeing evaluation results must be logged with before/after hashes and may require rerunning every affected comparison; it must not be disguised as the original frozen experiment.

Preserve this frozen document and hash. Any amendment must be a separately timestamped record identifying which calls and results had already been observed. A timestamp generated after requests is not a preregistration.
