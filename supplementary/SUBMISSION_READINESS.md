# Submission readiness and remaining research

The package is a detailed research record and manuscript starting point. It contains a completed same-model Jev pilot with a positive bibliographic identity result and an unresolved relation-verification result. It is **not yet an independently replicated, externally preregistered, multi-dataset demonstration of general superiority**, and it does not evaluate autonomous graph compilation end to end.

## Claims supported by the executed study

| Claim | Evidence | Boundary |
| --- | --- | --- |
| A selected Jev formulation improves entity-matching macro-F1 on this split | 0.9604519774 to 0.9858601997; paired unadjusted 95% interval on the difference excludes zero | One selected bundled contrast; one custom split; development-conditioned inference |
| False positive same-entity predictions decrease | 8/63 to 2/63 negative pairs; one additional missed match | Pair decisions, not graph cluster merges or population prevalence |
| The relation variant does not demonstrate improvement | Macro-F1 delta +0.00190356 with interval spanning zero; accuracy 289/339 to 288/339 | Preserve this negative/inconclusive result in abstract and discussion |
| Stored outputs reproduce the recorded results | Offline reconstruction of 3,644 predictions; byte-identical proof with preserved manifest | Cached replay tests artifact processing, not remote determinism |
| Selected labels were stable in an immediate repeat panel | Three responses on each of 20 examples/task retained selected-arm labels | Small within-session sample; probabilities varied; no long-term stability claim |
| Recorded usage is inexpensive under the frozen price | 3,405 requests; about $0.2013 estimated model charges | No invoice or full-pipeline cost; no competitor cost comparison |

Avoid claims that six-shot prompting alone caused the ER gain, that Jev beats specialist models or conventional LLMs, that API probabilities are calibrated by design, that zero errors can be guaranteed by typing, that test data were independently blinded from prior repository work, or that a deployed graph compiler was validated by this run.

## Work required for stronger empirical claims

1. **Independent confirmation.** Before additional prompt search, freeze the selected entity formulation and evaluate untouched, independently sampled data with adjudicated identity labels. Prefer another bibliography source and at least one different entity domain. Preserve source/entity isolation and report the candidate-generation population. The original 63 negative evaluation pairs are too few to establish a very low deployment false-merge rate.
2. **A component-identifying experiment.** Use new development and test partitions for a factorial comparison of generic/identity instructions, Noul/Choice, demonstrations absent/present, and controlled request batching. Retain the same candidate evidence and option meanings. Vary demonstration sets/seeds separately to estimate sensitivity. The current held-out comparison bundles these factors.
3. **Model-neutral baselines.** Compare deterministic identity rules, a specialist matcher, constrained-output LLMs and an interface-matched alternative backend using the same evidence, candidate rows and calibrated-data budget. Historical specialist results are useful context but cannot be imported as a matched Jev head-to-head comparison without checking exact protocols and coverage.
4. **Selection-aware uncertainty.** Increase independent evaluation units, define the principal task/metric and any multiplicity correction before replication, and quantify sensitivity to demonstration/development/calibration splits. Current intervals condition on a single selection and calibration realization. Consider both operational failures and common-success semantic sensitivity.
5. **External validity.** Test realistic candidate pools and class prevalence, difficult negatives, incomplete fields, multilingual/transliterated records, versions and ambiguous aliases. Measure retrieval recall separately. Current identity-disjoint maximal matching drops many negatives and changes the train/test mixture.
6. **Adjudicated error analysis.** Blindly review baseline-only and selected-only errors, plus a random correct sample, with a written annotation guide and independent reviewers. Record agreement, disagreements, resolution, and reviewer knowledge of arm identity. Distinguish label problems, missing evidence, identity ambiguity and true model errors; do not invent explanations from model scores.
7. **Temporal and systems replication.** Repeat the exact panel and full confirmation at multiple times, record model/version metadata, vary batch composition under a declared design, and preserve full attempts. Obtain provider clarification on probability rounding and pinning guarantees. Any tolerance-policy experiment must preserve the frozen strict results and be named separately.
8. **Deployment policy validation.** If proposing automatic merges, select thresholds on calibration data under explicit error costs, then validate on untouched data with sufficient negative examples. Add reversible identity mappings and dependency-aware cluster evaluation before describing graph-level safety. The pilot does not validate such a policy.

## Data, ethics and publication checks

These are research-reporting obligations, not reasons to suppress the completed local results.

| Item | Present status | Before public release/submission |
| --- | --- | --- |
| Source provenance | Exact dataset URLs/revision and byte hashes retained | Cite original dataset creators and redistribution chain |
| Dataset licenses | Provenance is recorded; a complete redistribution-rights determination is not established by the experiment | Review SciFact, underlying abstract/source rights, DBLP–ACM/ER-Magellan and Ditto serialization terms; include exact license notices or publish retrieval scripts if full redistribution is not permitted |
| Remote service use | Model identifier, payloads, usage and frozen price retained | Check API/data publication terms and any acknowledgement requirement applicable to the run |
| Privacy/content | Public scientific/bibliographic text used; records may contain personal author names | Describe the data category and check publication venue/institutional requirements; public availability does not itself settle every requirement |
| Bias/coverage | Limited scientific and bibliographic domains; no demographic fairness assessment | State scope; avoid unsupported subgroup or cross-domain claims; design relevant coverage checks for the intended use |
| Annotation quality | Public benchmark labels and historical fixtures; no new blinded adjudication | Conduct independent error review and document benchmark ambiguities |
| Model contamination | Vendor training corpus is unknown | Disclose possible pretraining exposure to public benchmarks; do not claim contamination-free evaluation |
| Statistical plan | Local pre-call freeze with fixed primary endpoints | Archive a public preregistration for a new confirmation if claiming confirmatory evidence |
| Code license | Existing repository terms must be checked against contributions and copied dependencies | Select/confirm the intended release license and preserve third-party notices |
| Credentials | Research artifacts exclude credentials; scans are recorded | Keep secret-bearing local configuration out of release; publish only sanitized journals |

## Author and venue decisions still required

The authors must approve the final research claims and choose a target venue, paper type and length. Confirm author list/order, affiliations, corresponding author, contribution statements, funding, conflicts, acknowledgements, institutional/ethics declarations when applicable, and any required disclosure of AI-assisted research or writing. Do not fabricate an ethics approval, funding award, author contribution, or institutional affiliation.

Choose the paper's scope deliberately. The strongest completed empirical framing is a reproducible study of typed decision formulation and operational reliability for entity matching, with relation verification as a counterexample to universal improvement. TRACE-GC's compiler, dependency and mutation ideas remain motivation or future work unless separately supported by matching experiments. Claims of novelty require the reference review, focused related-work comparison and author judgment; absence of an identical demo is not proof of priority.

Before submission, audit every numerical sentence against `tables/tables.json` and saved results; preserve all denominators and the negative result. Rebuild tables/figures, run the portable package verifier, record the source commit, and verify citation metadata. Archive immutable artifacts with an appropriate license and persistent identifier when publication terms permit. Select a venue template only after the scientific content and scope are agreed.

## Suggested confirmation protocol

A compact next study can preserve the selected ER formulation verbatim, use a newly collected or independently held-out identity dataset, select no new prompt on its test labels, and compare it with the corrected generic baseline plus one strong task-specific baseline. Set the required negative sample count using the intended false-merge risk target rather than total-pair count alone. Freeze demonstration IDs, evidence, scoring, malformed-response handling, model metadata and resource caps before calls; report confidence intervals and all failures. This would address the main empirical gap without starting an unrelated graph-system project.
