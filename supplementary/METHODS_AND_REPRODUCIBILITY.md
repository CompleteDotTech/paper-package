# Methods and reproducibility supplement

This supplement describes the executed Jev study, not a proposed experiment. The authoritative record is [the frozen protocol](../reproduction/results/jev/run-20260918/PROTOCOL.md), [plan](../reproduction/results/jev/run-20260918/plan.json), [request journal](../reproduction/results/jev/run-20260918/calls.jsonl), and [analysis output](../reproduction/results/jev/run-20260918/results.json). [Compact tables](../tables/TABLES.md) are generated from the saved results; they retain full precision in [tables.json](../tables/tables.json).

## Study question and scope

The experiment asks whether a bounded formulation change improves decisions from the same remote model, `jev-1.13.0`, with the evaluated candidates and evidence held fixed. There was no fine-tuning, alternative model training, candidate retrieval change, graph construction, or database mutation in this Jev experiment. Scalar probability calibration is postprocessing, not replacement-model training. Earlier specialist-model and compiler experiments in the repository are separate historical work and do not establish a Jev advantage.

Two tasks were evaluated separately: bibliographic identity matching on DBLP–ACM and three-way support/refutation/insufficient-evidence classification on cited SciFact abstracts. The principal result is an improvement on one identity-matching split. Relation verification did not show a resolved macro-F1 improvement. Do not pool these tasks into a single accuracy or describe the study as a general model leaderboard.

## Freeze and execution chronology

The local protocol was frozen at **2026-09-18 00:41:53 UTC**, before research development calls. Its SHA-256 is `58739c60a5520b5d8c51e6d5005d249977d20052106e1ff43782a25dd449123a`. Executable preparation completed at `2026-09-18T00:50:06.838003+00:00`; the saved plan hash is `7ed8622f2022b263f3d0b9cda413b4caafe50ebcf0589b05b886dbd615987040`. Arm selection was frozen at `2026-09-18T00:50:49.691652+00:00`. Calibration was fitted and hashed before evaluation. The recorded research request-start window extends from `00:50:07.557183` to `00:56:57.263451 UTC` on September 18. This corresponds to the evening of September 17 in the machine's America/New_York timezone.

A preceding toy authentication/schema probe contained no research examples; its usage remains in the journal. The protocol was locally timestamped, not externally preregistered. The public data and fixture labels had prior use in this repository: evaluation was held out from this Jev arm-selection procedure, but was not independently blinded from all prior project work. Later documents and the paper package organize an already completed study and must not be presented as advance preregistration.

## Source data and deterministic preprocessing

All preparation uses [research_data.py](../reproduction/pgc/experiments/research_data.py) and the [data manifest](../reproduction/results/research/data_manifest.json). Downloaded source bytes are checked against pinned SHA-256 values. The seed for seeded selections and bootstrap resampling is `20260917`. Hash functions serialize nonbyte objects as sorted-key, Unicode-preserving JSON and apply SHA-256; executable details matter for exact membership.

### SciFact

The source is the original SciFact archive at the URL recorded in the manifest, with byte hash `11c621288d41ac144d29b13b0f8503b3820b7d6e8b1f6ff24dff335c196d76be`. The preparation reads corpus, training claims and development claims, excluding archive cross-validation variants. Each example is a claim paired with each supplied unique cited document. It includes the complete ordered abstract sentence list. The model receives the claim and full abstract, not rationale sentence IDs or gold labels; the document title is retained in source metadata but is not a model input in this run.

The label for a cited document is mapped from `SUPPORT` to `SUPPORTS`, `CONTRADICT` to `REFUTES`, and absence of a document annotation to `NOT_ENOUGH_INFO`. Conflicting document labels cause preparation to fail. This task is **classification of supplied cited abstracts**, not open-corpus retrieval, evidence-sentence selection, or official leaderboard test performance.

Official development claims supply the evaluation examples. From official training claims, the procedure purges the entire claim if any cited document ID or exact abstract-content hash overlaps evaluation. It removed **272 training claims**. A union-find connects claim IDs, document IDs and duplicate-abstract hashes; these connected components define independence units. Remaining training components are placed in calibration when the integer from the first eight hex digits of the component digest modulo four is zero; the rest form prepared training. This particular component partition is hash-based but does not insert the global seed into its digest. Document and abstract-content disjointness is checked across splits.

| Prepared split | Rows | Connected components | SUPPORTS | REFUTES | NOT_ENOUGH_INFO |
| --- | ---: | ---: | ---: | ---: | ---: |
| Training | 459 | 255 | 179 | 82 | 198 |
| Calibration | 150 | 73 | 65 | 30 | 55 |
| Evaluation | 339 | 247 | 138 | 71 | 130 |

### DBLP–ACM

The source is Ditto's serialized ER-Magellan `Structured/DBLP-ACM` data at revision `52985564a93fb11308439516d3e17a033d43ec8f`. The original `train.txt`, `valid.txt`, and `test.txt` are pooled, parsed into attribute dictionaries, deduplicated, and **repartitioned by identity**. Original source split names survive only as provenance; an example ID containing `test` can legitimately belong to the new training partition. This study does not report performance on Ditto's original test split.

The parser reads `COL ... VAL ...` fields. Entity keys are hashes of the complete parsed attribute dictionary. Positive pair labels define connected identity components for splitting. Conflicting serialized pairs identify ambiguous records; their original positive components are quarantined so aliases through removed records cannot conceal leakage. There were **seven conflicting pairs, 12 quarantined record hashes, and 92 excluded pairs**. No remaining negative pair lay within a positive component; the second consistency quarantine removed zero pairs.

Each identity component is assigned to training/calibration/evaluation by the first eight hex digits of `SHA256([20260917, component])`, modulo ten, with buckets `0–5`, `6–7`, and `8–9` respectively. Pairs whose two identities fall in different splits are dropped: **5,623 pairs**. Calibration and evaluation then use a deterministic greedy maximal matching, ordered by the hash of row ID, which accepts a pair only if neither identity component has appeared earlier in that split. This removes another **457 calibration and 536 evaluation pairs**. Isolation is checked using both retained components and original pre-quarantine positive components.

| Prepared split | Rows | Same | Different |
| --- | ---: | ---: | ---: |
| Training | 4,592 | 1,309 | 3,283 |
| Calibration | 390 | 334 | 56 |
| Evaluation | 413 | 350 | 63 |

Positive labels are used to define isolation groups, never as evaluated-candidate features. Calibration/evaluation pairs are disjoint in the available identity annotation; this does not prove absence of every unannotated alias. The stored `group` field is a row ID and cannot be used to exclude shared training identities; the runner uses `identity_groups` for that purpose. The 413 evaluation rows use 476 distinct identity/component keys (one for a positive pair, two for a negative pair).

The drop/matching procedure changes the label mixture substantially: evaluation contains 350/413 same pairs, compared with 1,309/4,592 in prepared training. This improves separation of evaluation units but is a material external-validity limitation. These results are not estimates of operational duplicate prevalence, candidate retrieval recall, or cluster-level merge safety.

## Training demonstrations and development selection

Exactly **six demonstrations and 60 additional development rows per task** are selected from prepared training. No remaining prepared training rows are used by Jev. Demonstrations are selected before service calls, not by observed model performance. SciFact takes two rows per class, all from different components. ER takes three same and three different pairs, excluding shared identities; different-pair candidates whose lowercase-title `difflib.SequenceMatcher(None, title_1, title_2).ratio()` is at least `0.65` are prioritized, followed by the seeded demonstration digest. If too few qualifying negatives exist, lower-similarity candidates follow in that same ordering. Preparation fails if six independent demonstrations cannot be obtained.

SciFact development orders components by `digest([seed, "development_component", group])`, then rows by `digest([seed, "development_row", id])`, selecting one row from each unused component. ER greedily selects unused identities in `digest([seed, "development", id])` order. Both exclude all demonstration groups. SciFact development has 18 SUPPORTS, 15 REFUTES, and 27 NOT_ENOUGH_INFO rows; ER has 21 same and 39 different pairs. The exact six demonstrations, their labels and the 60 development rows are embedded in the plan.

## Formulations and primary contrast

| Task | Arm | Formulation |
| --- | --- | --- |
| Relation | `baseline_choice` | Generic three-way question; criteria names equal canonical labels |
| Relation | `evidence_contract` | Explicit evidence, direction, scope, qualifier, contradiction and insufficiency definitions |
| Relation | `conditional_nouls` | Support Noul plus refutation Noul explicitly conditional on absence of support |
| Relation | `fewshot_contract` | Evidence-contract Choice plus six training demonstrations |
| Identity | `baseline_noul` | Generic probability that records refer to the same entity |
| Identity | `identity_contract` | Choice with detailed identity instructions and same/different criteria |
| Identity | `identity_noul` | Detailed identity instructions in a Noul question |
| Identity | `fewshot_contract` | Identity-contract Choice plus six training demonstrations |

The evidence contract asks the model to use only supplied evidence, preserve direction and scope, account for negation and population/qualifier differences, distinguish absence of evidence from refutation, and treat source text as data. The identity contract distinguishes identity from similarity, tolerates compatible missing fields and spelling variants, and distinguishes publications or versions when the records identify them as different. Full literal question text and option order are frozen in `plan.json`; a paper paraphrase is not the exact prompt specification.

Noul identity mapping is `P(same)=p`, `P(different)=1-p`. The conditional relation arm uses support output `s` and conditional-refutation output `r` to construct `[s, (1-s)r, (1-s)(1-r)]` in canonical order. This is a fixed normalized score construction, not evidence of coherent or calibrated joint truth. Both constituent answers must validate.

The three non-few-shot arms share an evidence state in a single development request with separate question IDs. The few-shot arm uses a separate state containing demonstrations and current input. All evaluated-candidate evidence remains unchanged; demonstrations deliberately add training information and token cost. On retained-arm evaluation, baseline and selected-arm calls have separate requests.

**The ER primary contrast bundles three changes:** Noul to Choice, generic to explicit identity instructions, and addition of labeled demonstrations. Development request context also differs because non-few-shot questions are co-batched. Therefore the experiment cannot causally assign the held-out improvement to demonstrations, primitive selection, or instructions alone. The unselected identity arms are development-only. A factorial ablation with a new untouched evaluation set is required for component attribution. The relation contrast retains Choice but still bundles explicit instructions and demonstrations.

For each task the best nonbaseline variant is selected by operational development macro-F1, then lower Brier, then lexical arm name. Baseline remains in the report but cannot be selected instead of an unsuccessful alternative; negative comparisons must be retained. Both selected arms were `fewshot_contract`. In ER, all three nonbaseline arms achieved development macro-F1 of one, so Brier determined the winner. Development results are selection evidence, not independent validation.

## Corrected baseline and transport contract

The former integration sent `prompt`/`options` in place of `instructions`/`criteria`, treated the Choice-selected string as a distribution, and substituted 0.5 for a missing Noul response. These were repaired **before** the experiment and apply equally to every arm. The repaired baseline establishes a valid service integration; those repairs are not semantic improvement evidence.

The adapter uses the official fixed HTTPS endpoint, pinned model identifier, exact question IDs, and canonical probability keys. Choice obtains the distribution from `probabilities`; Noul obtains its scalar from `noul`. Returned model metadata is recorded and checked against the request. Choice confidence is retained separately from the selected probability; Noul has no independent confidence field. A requested/returned model string does not establish immutable server weights or training-data absence.

Missing, nonnumeric, Boolean, nonfinite, negative, greater-than-one, wrong-key, or non-normalized probabilities fail validation. The absolute sum tolerance is **1e-6**, relative tolerance zero. No renormalization or fallback prediction is applied. Five physical calls returned probabilities that failed this rule; all were retained as failures. One failed development request affected three co-batched arm predictions. There were no HTTP retries. This strict policy may reject rounded but otherwise usable vendor outputs; alternate tolerances would be a separately declared sensitivity analysis, not retroactive repair of the frozen result.

## Calibration

Each task's corrected baseline and selected arm receives an independent scalar temperature fitted only on its calibration split's valid responses. With `epsilon=1e-15`, the transformation is `softmax(log(max(p_k, epsilon))/T)`. These are logs of returned probabilities, not access to hidden logits. The fitting objective is mean calibration log loss with `T` constrained to `[0.05,20]`; 80 golden-section iterations in log-temperature are compared with both endpoints and `T=1`. Exact objective ties prefer the first candidate, `T=1`. No fit reaches a boundary.

| Task / arm | Valid / planned | T | Fitted class counts | Probability coordinates clipped |
| --- | ---: | ---: | --- | ---: |
| Relation baseline | 149 / 150 | 4.803020132038449 | 65 support, 29 refute, 55 insufficient | 176 |
| Relation selected | 150 / 150 | 3.1499754428309736 | 65 support, 30 refute, 55 insufficient | 178 |
| ER baseline | 390 / 390 | 0.2997078260089508 | 334 same, 56 different | 0 |
| ER selected | 390 / 390 | 0.6238873352858962 | 334 same, 56 different | 304 |

All canonical classes appear in valid calibration rows. The complete fit IDs, class counts, hash, clipping counts, objective and temperatures are in `calibration.json`. Positive scalar temperature preserves probability ordering except possible clipping ties; it does not account for an ordinary accuracy improvement. Held-out ER Brier and log loss improve after calibration. Held-out relation log loss improves but Brier worsens; calibration is not uniformly beneficial and does not certify deployment calibration under distribution shift.

## Endpoints, denominators and statistical analysis

The primary endpoint per task is selected-minus-baseline **operational macro-F1** on all eligible evaluation rows. Failure is an `ERROR` prediction: it remains in accuracy denominators and contributes a false negative for its gold class, while ERROR itself is not a class in the macro average. Macro-F1 averages all canonical labels, assigning zero when a class F1 denominator is zero. Balanced accuracy averages recalls for classes with gold support. Confidence for reliability diagnostics is maximum predicted probability, not the vendor's separate confidence field.

Brier is the full sum of squared errors over every class (range 0–2), including both coordinates for binary ER. Log loss uses natural logarithms and clips gold-label probabilities at `1e-15`. These probability metrics exclude invalid responses and report their denominator. Thus SciFact raw arm scores have probability denominators **338 baseline and 337 selected**, while operational classification retains **339**. ER has **413/413** valid responses in both arms. Pairwise probability differences are computed only on the **336 common-success SciFact rows** and all 413 ER rows. The [common-success sensitivity analysis](../reproduction/results/jev/run-20260918/common_success_sensitivity.json) also recomputes classification on that paired successful population; it leaves the task-level interpretation unchanged.

False-merge count is the number of gold-different pairs predicted same; its denominator includes every gold-different pair, with service errors counted separately. On ER evaluation this is **8/63 baseline versus 2/63 selected**, alongside **0 versus 1 missed same-entity pair among 350**. The term describes pair classification; the study does not physically merge graph clusters or measure downstream transitive damage.

Paired 95% percentile bootstrap intervals use **2,000 draws** and NumPy `default_rng(20260917)`. SciFact samples 247 sorted component keys with replacement and retains all rows in each sampled component. ER samples 413 identity-disjoint row IDs with replacement. Both arms use identical draws, and nonlinear confusion-derived metrics are recomputed per draw. Quantiles are computed at 0.025 and 0.975 using NumPy's default method. Brier contributions use common-success pairs; false-merge rates use resampled negative-class counts. Finite-resample counts are recorded.

The ER macro-F1 difference is **+0.0254082223**, interval **[+0.0009601134,+0.0539639335]**. Its accuracy difference is **+0.0121065375**, interval **[0,+0.0242130751]**. SciFact macro-F1 difference is **+0.0019035615**, interval approximately **[-0.031390,+0.033734]**. These intervals condition on the fixed split, selected formulations, fitted temperatures and observed service outputs. They do not resample development selection, demonstrations, calibration fitting, vendor deployments, or training uncertainty. They are unadjusted for multiple task/metric comparisons and are exploratory rather than familywise confirmatory evidence.

Reliability diagnostics use ten fixed confidence bins and report each bin's count, mean confidence and accuracy, plus ECE. Selective accuracy/coverage is reported at fixed thresholds `0,.5,.7,.8,.9,.95`. These thresholds are descriptive; choosing the best held-out threshold would not validate a deployment policy. ECE depends on bins and sample size; it is not a guarantee on each prediction or subgroup.

## Secondary fixture diagnostics

The repository fixtures contain 50 relation and 100 ER examples. ER has 88 binary-eligible examples and 12 `uncertain` labels; all responses remain archived, but uncertain labels are excluded from binary correctness and probability scores, not reclassified or counted as errors. Relation accuracy is 46/50 baseline versus 45/50 selected. ER is 84/88 versus 87/88, with false merges 3/12 versus 0/12 negative cases and one missed match in either arm. These fixtures have prior development use and unadjudicated labels; they are integration/domain-transfer diagnostics, not independent natural-data validation.

## Repeated service calls and batching controls

Before outcome inspection, 20 evaluation IDs per task were selected by a seeded ID digest. Baseline and selected arm each receive three service responses per example: the original evaluation call and two additional rounds with local-cache bypass. All complete semantic payloads, including question IDs and option order, are identical across rounds. Distinct journaled HTTP attempts establish local fresh calls; the experiment cannot determine whether the vendor internally caches requests.

Each arm yields 60 pairwise round comparisons from only 20 examples; these comparisons are dependent and are not 60 independent samples. Reported diagnostics include three-round label constancy, pair agreement, exact-vector equality, maximum coordinate change and total variation `0.5*sum(abs(p_a-p_b))`. Every selected-arm example retains its label across the three calls. ER baseline also retains all 20 labels; relation baseline changes on one example, yielding 58/60 pairwise label agreement. Selected probabilities vary, with maximum total variation **0.09 ER and 0.22 relation**. These immediate repeats do not establish bitwise or future determinism.

An additional 20 fixed development rows per task compare the three non-few-shot arms' co-batched development answers with fresh separate-arm calls. All six task/arm comparisons show 20/20 label agreement, while probabilities vary. This small exploratory control does not prove absence of batching effects and does not isolate held-out formulation components.

## Usage, errors and resource limits

The runner limits concurrency to four, total HTTP attempts to 4,000, input-token budget charges to 20 million, and retries to at most two per request. Failed attempts with absent usage conservatively reserve tokens rather than count as zero. This run had no absent usage and no retries.

| Stage | Physical research requests |
| --- | ---: |
| Development | 240 |
| Calibration | 1,080 |
| Evaluation | 1,504 |
| Additional fresh repeats | 160 |
| Fixtures | 300 |
| Separate-arm batching controls | 120 |
| Toy preflight | 1 |
| Total | 3,405 |

There are **3,726 question objects**, **3,644 recorded logical predictions**, **4,792,778 reported input tokens** and **139,613 output tokens**. Usage is summed once per request, not per prediction in a shared batch. The five failed calls are included. Summed recorded stage wall time is **378.474 seconds**; summed overlapping call latency is **1,454.044 seconds** and is not wall time. Request p50/p95/p99 latency is approximately **387.5/611.1/1,403.3 ms**.

At the frozen documentation price of $0.042 per million input tokens and zero output-token charge, estimated model charges are **$0.201296676**. This includes all experiment stages, not only held-out deployment inference, and is not a provider invoice. It excludes analyst effort, data preparation, hardware, artifact storage and production integration; it is not full graph-pipeline cost or a demonstrated cost advantage over other models.

## Artifact replay and independent verification

The run stores exact semantic request payloads, raw responses, timestamps, requested/returned model metadata, usage, attempts, canonical predictions, plan IDs, calibration and analysis outputs. Credentials are not part of those artifacts. Five declared core source modules are hash-frozen in the initial manifest; that is not a complete transitive environment freeze. In particular, the runner imports the title-similarity helper from `run_er_research.py`; the paper package includes the full source tree, and the plan independently preserves all selected demonstrations and literal requests. Use the packaged environment/source manifest for the broader reproduction context.

The [independent artifact verifier](../reproduction/results/jev/run-20260918/verification.json) passed source/data hashes, split isolation, phase completeness, request reconstruction, usage accounting, timing order and point-score checks. It does not independently regenerate all bootstrap intervals, prove absence of every possible secret, or requery the model. Its limitations are included in the verifier record.

An isolated replay blocked HTTP and reconstructed **all 3,644 predictions** from saved responses with **zero network calls**. The original manifest was restored only in the replay copy before analysis to preserve the original report provenance; calls, predictions, calibration and results were then byte-identical. See [replay_verification.json](../reproduction/results/jev/run-20260918/replay_verification.json). A normal replay adds offline-stage records to the copied manifest, so report provenance hashes change even if predictions are identical. Neither replay mode is new service-performance evidence.

The local runner is resumable but not a crash-durable billing ledger: a process failure between receiving a response and appending its journal can leave an unrecorded request that a resume repeats. This did not occur in the archived run. Pinned remote identifiers, exact hashes and cached replay support auditability but cannot establish immutable server internals.

## Reproduction entry points

Use the package [README](../README.md) for the portable verification commands and source/data placement. The frozen study [README](../reproduction/results/jev/README.md) explains cached replay versus fresh inference. Always use a new output directory for a new live study, retain failures, and do not overwrite the archived run. A future prompt selected after viewing these held-out labels requires a fresh evaluation set.

The following table-only command reads packaged JSON and performs no inference:

```powershell
python scripts/generate_tables.py
```

Execute it from the package directory; the script resolves defaults relative to its own location and is also callable from another working directory. The generated JSON records the results/data-manifest hashes. Tests, package integrity verification and frozen-study artifact verification address different obligations and should be reported separately.
