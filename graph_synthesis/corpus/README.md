# Larger-corpus research methodology

**Version 1; prepared 2026-09-18. Proposed, not preregistered; no new model results.**

This prospective methodology complements, rather than rewrites,
[the original replay protocol](../PROTOCOL.md). That protocol studies saved
claim–abstract and identity decisions; this one specifies how to extend the
research to a much larger body of prior art and independently evaluated full
papers. Preserve negative findings and do not present additional publications,
graph nodes or decisions as proof of scientific improvement.

## 1. Questions, units and commitments

Freeze these questions before collecting held-out predictions:

1. On identical evidence and candidates, does a Jev decision backend improve
   strict, independently adjudicated relationship quality over strong baselines,
   at useful coverage and comparable total cost?
2. Does a complete pipeline retrieve the relevant evidence, identify entities,
   discover relationships, preserve qualifiers and repair errors across papers?
3. What breaks as document count, graph size, candidate density and concurrency
   increase, and does independently audited quality degrade?

Keep a ledger of **retrieved records, unique works, full papers, independent
components, candidates, logical decisions, attempts, tokens and graph writes**.
A paper version is not a new independent work; ten repeated calls are not ten
independent scientific observations. Document-to-claim support, entity identity
and domain relations are different tasks with different gold labels.

Commit a dated protocol amendment, corpus snapshot, schema, splits, prompts,
model/version identifiers, extractor/parser versions, seeds, primary endpoint,
practically relevant effect, coverage floor, annotation design, stopping rules
and authorized resource caps **before** examining held-out outcomes. Publicly
archive or timestamp that bundle through a reviewed registration process.
The supplied configuration and content hashes do not do this on their own.
Changes after inspection are exploratory; a new confirmatory claim requires a
new untouched cohort and an amendment that discloses earlier exposure.

## 2. Track A: a living, auditable literature review

### Search and screening

Use a PRISMA-style reporting ledger for discovery, deduplication, title/abstract
screening, full-text eligibility and exclusions [prisma2020]. This is an adapted
reporting practice, not a claim that this software conducts a compliant
systematic review or validates study quality.

Search multiple indexes and primary venues. OpenAlex can supply discovery
metadata [openalexhelp]; ACL Anthology and arXiv can identify primary NLP/AI
work; use PubMed for domain-specific retrieval. Translate, do not blindly reuse,
Boolean syntax between providers. Example concepts to combine are:

```text
("knowledge graph" OR "graph database") AND
(construction OR synthesis OR enrichment OR extraction) AND
("large language model" OR "multi-agent" OR probabilistic OR constrained)

("relation extraction" OR "entity resolution" OR "schema induction") AND
(scientific OR scholarly OR "full text") AND
(provenance OR calibration OR contradiction OR temporal OR benchmark)
```

Maintain `search_log.jsonl` with provider, exact query/filters, executed UTC
time, covered publication interval, endpoint/API version, cursor or snapshot
ID, response checksum, result count and retrieval failures. A fixed query today
is not the same dataset tomorrow. Use provider-supported pagination and exports;
verify current access terms before execution. Do not claim exhaustive retrieval
when a provider truncates results, an export is incomplete or a source fails.

Normalize DOI, arXiv version, PMID/PMCID and provider aliases into a persistent
work identity. Record preprint–publication links and corrections. Preserve every
retrieval hit and exclusion reason in an alias ledger; do not inflate counts
with versions or merge different studies solely because titles look similar.
Retractions/corrections should be flagged, not silently erased.

Use two independent screeners for a planned eligibility sample and adjudicate
disagreements; require independent review of all final included papers. AI may
rank relevance or propose exclusions, but do not automatically discard its
low-ranked tail. Audit a probability sample of excluded records and report
missed-eligible rates with uncertainty. Predeclare the audit size and acceptance
criterion; if the criterion fails, expand screening or redesign it, rather than
asserting recall from an unreviewed ranking. Maintain unresolved/full-text-unavailable
states instead of inventing content from abstracts.

Run two declared rounds of backward and forward citation chaining from included
methods, surveys and strong baselines, including KARMA but not limited to it.
Record parent paper, direction, round and discovery date. Additional rounds or
new queries require a logged amendment. Citation count is not a quality label.

### Structured extraction and reference management

For each included work, record citation key, Zotero item key (a distinct ID),
version, venue/status, source link, artifact/license status, problem class,
candidate generation, entity resolution, schema handling, decision mechanism,
provenance, temporal/contradiction support, graph mutation, evaluation corpus,
gold-label origin, splits, baselines, uncertainty, cost denominator and limits.
Attach page/section/paragraph or table locators for every extracted claim.
Label entries `author_reported`, `independently_reproduced`, `inferred`, or
`not_verified`. A claimed benchmark score is not a reproduced result.

Use a living Zotero collection and versioned BibTeX export for accepted references.
Keep excluded and pending records in separate collections/tags and retain alias
links. The installed Zotero integration is intended for Zotero Desktop in Codex;
this addition does not access, change or claim to have populated that library.
`references.bib` here contains seed sources verified for this methodology only.

Build an evidence matrix spanning traditional IE, specialist relation/identity
models, constrained single-LLM extraction, multi-agent systems, graph learning,
probabilistic compilation, symbolic validation, provenance and temporal repair.
For every proposed architecture choice, link at least one supporting or
contradicting observation. Add a replicability/risk-of-bias judgment rather than
averaging scores across incompatible corpora or model-based judges.

## 3. Track B: acquiring a rights-reviewed full-paper corpus

Keep the review corpus and the experimental document population separate.
A method paper included as prior art is not automatically a benchmark document.

Prefer structured full text (JATS/XML or validated structured text) so evidence
can retain sections, paragraphs, citations, tables and offsets. Use the PMC
Open Access Subset only through permitted automated services, with per-item
license review; inclusion in PMC does not by itself grant text-mining or
redistribution permission [pmcoa]. Treat OpenAlex as discovery metadata, not a
blanket license to publisher full text [openalexhelp]. S2ORC is a published
example of structured scholarly text, not a guarantee of present-day access
or rights to every version of its data [s2orc2020]. Verify any chosen release
and its current terms separately.

For every selected document retain canonical work ID and aliases, source URL,
retrieval time, publication date/version, license text/URL, rights decision and
reviewer, raw-byte hash, normalized-text hash, parser/version/configuration,
language and quality flags. Store full text outside Git unless redistribution
is explicitly authorized. Publish reproducible identifiers and checksums where
text cannot be redistributed. A review attestation in a manifest is not legal
verification by this planner.

Apply a frozen parser QA rubric. Audit section order, equations, tables,
negation, citation attachment and sentence boundaries by source/domain/format.
Record all missing, malformed and rejected documents in the acquisition ledger.
Do not silently substitute easier papers. PDF-only inputs require a separately
validated parsing route; audit their pages and label the modality explicitly.
Keep parser failures in pipeline denominators even if they cannot reach the
post-QA planner input.

Treat documents as untrusted data: embedded instructions cannot authorize tool
calls, downloads, credentials, publishing or graph writes. Sandbox parsers, cap
file sizes, reject archive traversal, and keep model tools unavailable during
extraction. Adversarial documents belong to a labeled challenge set, not an
undisclosed mixture with natural data.

## 4. Deduplication, dependency groups and holdouts

Before planning, resolve known versions/aliases into one selected document per
work, retaining excluded aliases and the version-selection rule. Resolve exact
text duplicates, near duplicates, reused abstracts, shared study cohorts and
benchmark overlap. Near-duplicate/entity inference is an upstream audited
curation task; `plan.py` only rejects repeated supplied IDs or exact text hashes.

Construct `split_group` as the connected component of **declared leakage
relationships**. Union shared study families, duplicated content, reused gold
claims and shared benchmark observations transitively before assigning splits.
Do not use a common citation or a ubiquitous biomedical entity to connect the
entire corpus. Define a separate entity-disjoint challenge when that is the
estimand, and report exclusions/giant components rather than weakening the rule
silently. Audit random cross-split pairs and all known external benchmark overlaps.

The reference planner hashes `(seed, split_group)` into approximately 20%
development, 20% calibration and 60% test. These are group assignment
probabilities, not promised paper counts or domain balance within every split.
Empty splits are blockers; sparse strata need more groups or a separately
reviewed design, not seed shopping after observing outcomes.

For each stage, select equal domain quotas by stable work-ID hash, then include
**all** members of any selected group, including members in other domains.
Consequently actual counts can exceed the requested target and domain proportions
can shift. Report both; budgets are checked after expansion. Larger stages are
nested for the same frozen manifest. An updated master corpus can change
selection, so snapshot it and create a new cohort/version instead of treating a
live index as a stable sample.

Separately preregister chronological and held-out-domain cohorts, with explicit
dates/domains and family embargoes. The reference planner's publication-year cap
is only an eligibility filter: it does **not** implement a temporal or
leave-one-domain-out split. Audit pretraining contamination where observable;
new publication dates do not prove that proprietary models have never seen text.

## 5. Stage gates and sample size

| Stage | Requested papers | Required gate before expansion |
|---|---:|---|
| Pilot | 100 | Rights/parser QA, annotation rubric, error taxonomy, preliminary variance and full cost accounting |
| Controlled comparison | 1,200 | Untouched evaluation groups, independent gold, fixed arms/thresholds, approved budget and sample-size justification |
| Generalization | 10,000 | Quality by source/domain, independent temporal/domain challenges, cross-paper relationship and repair tests |
| Stress | 100,000 | Independent quality audit plus measured throughput, failures, durability and resource consumption |

These are capacity targets, not completed collections or statistical power
claims. KARMA's current abstract reports 1,200 PubMed articles and LLM-verified
correctness [karma2026]; matching its document count does not match its sampling
or evaluation. The example domains are biomedicine, computer science and
materials science, explicitly **not** a replication of KARMA's corpus.

Use the pilot to estimate cluster sizes, paired outcome variance, prevalence,
annotation yield and missingness. Choose a practically meaningful effect and
coverage requirement before an independent confirmatory cohort; simulate power
or expected interval width at the **component** level for the actual sampling
and metric. Record assumptions and sensitivity to clustering. No fixed paper
count guarantees precision for rare predicates or infrequent false merges.

Exclude pilot papers from confirmatory evidence. For nested scale stages, freeze
models and analysis before opening their held-out labels; previous-stage test
labels must never become tuning examples for the same confirmatory sequence.
Audit samples may be disjoint by stage, with preregistered sequential error
control, or use one final confirmatory analysis. Repeated looks are not free
additional significance tests. Optional 1M-paper metadata discovery and 1M/10M
logical-decision stress panels require their own budgets and labels; do not
present them as full-paper semantic evaluation.

## 6. Independent gold and relationship semantics

Maintain two evaluation samples with recorded selection probabilities:

* A probability sample of entire documents/components, annotated comprehensively
  for the declared ontology, measures candidate generation and final graph recall.
* A probability sample from the union of all systems' proposed/accepted edges,
  including rare predicates and disagreements with known inclusion probabilities,
  measures accepted-edge precision and operational risk.

Use two independent, suitably qualified annotators blinded to system identity,
with adjudication and versioned rationales. Annotate entities, canonical IDs,
directed predicates, subject/object, negation, hedging, temporal/experimental
qualifiers, evidence spans, contradiction scope and `insufficient_evidence`.
Record disagreement before adjudication and missing/unresolvable judgments.
AI-assisted prelabels are proposals, never independent gold. Where budgets
prevent independent annotation, label the results silver/weakly supervised and
limit claims accordingly.

Score exact supported assertions as `(subject, predicate, object, qualifiers,
evidence)` under a frozen equivalence policy. A document's support for a claim
is not automatically an assertion that the claim is universally true.
`supports` and `refutes` refer to particular evidence; independent predicates may
coexist. Candidate recall needs complete scoped annotation: auditing only the
system's own edges cannot detect omitted relations. Report weighted estimates
for stratified/oversampled edge audits; disagreement-enriched samples alone
cannot estimate population precision without accounting for their sampling.

Include multi-paper coreference, conflicting experiments, qualifiers that change
interpretation, schema mismatch, unseen predicates and missing evidence. Keep
synthetic semantic challenges, injected parser attacks and deterministic graph
invariants separate from naturally observed accuracy.

## 7. Comparisons, ablations and inference

Separate two experimental tracks **within** the full-paper study:

| Comparison | Held constant | What may change |
|---|---|---|
| Decision backend | Documents, parser, candidate/evidence set, ontology, graph state and budgets | Rules, specialist model, constrained LLM, Jev formulation |
| End-to-end pipeline | Document population, gold, allowed resources and output contract | Retrieval, extraction, entity resolution, routing and graph construction |

Plan deterministic rules, a single constrained LLM, a strong LLM plus validator,
a relevant specialist relation/identity model, Jev baseline/selected formulations,
and a faithful KARMA run **only if** its pinned code/data/model setup can be
reproduced. Record unavailable arms explicitly. A placeholder name in the
planning configuration is not an implemented adapter. Call modified substitutes
`KARMA-inspired`; published numbers belong in related work, not in the paired
results table. Document model access, weights/checkpoints, tuning data, prompt
budgets and any resource mismatch.

Prioritize controlled ablations: remove Jev, remove symbolic validation, remove
graph feedback, remove confidence routing; separately test provenance and
retraction behavior. Predeclare the smaller confirmatory family and mark other
combinations exploratory. Decompose formulation versus demonstrations without
reusing test labels. All arms receive the same evidence budget in a backend
comparison; total pipeline cost must include retrieval and candidate generation.

Select one primary confirmatory estimand and its minimum coverage before test
inspection. A suitable candidate is the paired difference in strict accepted-edge
precision at a calibration-fixed operating rule, accompanied by recall and
coverage safeguards. Report macro/micro precision, recall and F1; per-predicate
errors; entity false merges/splits; unsupported/incorrect direction/qualifier
rates; abstentions; and all timeout, parse and provider failures. Zero accepted
edges make precision undefined, not perfect.

Add matched-coverage/count and matched-budget frontiers without choosing a
test-optimal threshold. Use frozen tie rules independent of gold. Distinguish
false positives among negatives from errors among accepted edges. Report Brier
score, a predeclared ECE binning scheme and risk–coverage curves only for the
stated label probabilities; typed outputs do not imply calibration.

Resample dependence components jointly across arms, respecting domain and audit
sampling; recompute each metric and its paired difference in each replicate.
Predeclare seed and bootstrap count (for example 10,000), account for survey
weights, and report component counts and small-sample limitations. Use an
appropriate cluster/survey method when simple bootstrap assumptions fail.
Correct the prespecified comparison family (for example Holm), and disclose all
exploratory analyses. Repeated service runs estimate operational variability,
not independent additional documents. Failure to establish superiority is not
proof of equivalence; equivalence/noninferiority needs its own margin/design.

## 8. Graph lifecycle, scaling and execution controls

Measure graph constraint violations, provenance completeness, disconnected or
spurious merges, degree/component distributions, cross-document connectivity,
review burden, rollback correctness and repair blast radius. More edges or
fewer isolated nodes are not necessarily better. Evaluate source withdrawals,
corrected versions, conflicting evidence and schema migrations against expected
history-preserving outcomes; label injected withdrawals as interventions rather
than real retractions.

The existing graph store keeps complete state per transaction [local implementation:
`../README.md`]; do not assume it scales to this ladder. Profile it first and
measure serialization/write amplification, transaction latency, database size,
reopen recovery and idempotent replay. A more scalable store is a future
implementation change with conformance tests, not a property established by this
methodology.

For a future executor, use a persistent queue with per-paper/stage IDs, bounded
workers, request/decision/token/dollar limits, bounded attempts and provider-aware
backoff. Check current provider rules and `Retry-After`; never hard-code an old
quota from a paper. Stop submitting new jobs at caps, checkpoint completed work,
retain failures and unresolved jobs, and reconcile in-flight charges. Keep graph
writes transactional and idempotent. No large-scale run is authorized here.

Cache only when raw and normalized evidence hashes, parser, candidate generator,
ontology, model/version, full prompt, decision contract, calibration and relevant
graph snapshot match. Log cache hits and new calls separately. Graph-conditioned
predictions cannot be reused after a graph change as though they were fresh.
Separate logical decisions from API requests and batched provider usage.

Record p50/p95/p99 latency, papers/s, candidates/s, decisions/s, cold/warm cache
rates, tokens, dollar estimates versus invoices, annotation minutes, storage,
CPU/GPU time and retry/failure rates. Include parsing, extraction, retrieval,
validation, graph writes and human review, not just Jev inference. Report both
per-paper and per-independently-correct-edge cost where estimable. Fixed corpus
replay measures computation; fresh held-out service runs measure model behavior.

Stop expansion for exhausted authorized resources, rights uncertainty, leakage,
failed QA or preregistered futility/quality criteria. Freeze concrete thresholds
and sequential rules before outcomes; unspecified thresholds are unresolved
protocol requirements, not passed gates. Preserve partial/negative results.

## 9. Reference planner contract and reproduction

`plan.py` is standard-library-only and deliberately offline. Its input is the
**eligible, curated** population, not an acquisition log. Required JSONL fields
are shown below with unmistakably synthetic values:

```json
{"paper_id":"synthetic-paper-001","work_id":"synthetic-work-001","split_group":"synthetic-study-001","domain":"biomedicine","year":2025,"source":"synthetic_fixture_not_a_publication","license":"synthetic-test-only","rights_reviewed":true,"full_text":true,"text_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","estimated_candidates":20}
```

The dummy hash is an example, not a verified document. For real data, verify raw
and normalized hashes against bytes upstream and store those receipts outside
this minimal planning manifest. Use lowercase SHA-256; trimmed nonempty string
IDs; integer year/candidate estimates; and literal booleans. No extra fields or
gold labels are permitted. Normalize identifier spelling/case before planning:
string equality does not resolve DOI URLs, PMC aliases or unknown near duplicates.
The planner cannot verify whether a supplied `split_group` is scientifically complete.

Copy `protocol.example.json` into a new study directory and resolve its settings.
`usd_per_decision` must be a reviewed conservative per-attempt estimate across
planned arms; `fixed_overhead_usd` must include other anticipated costs. Neither
is a live provider quote. Attempted decisions are estimated as:

```text
sum(estimated_candidates for selected papers)
  * number_of_arms * repeats * max_attempts

estimated_cost = attempted_decisions * usd_per_decision + fixed_overhead_usd
```

This is a coarse planning envelope, not a backend-specific billing model.
Deterministic arms are conservatively included as logical decisions. Use separate
measured arm budgets in the actual executor. Every stage is priced as a full
rerun; summing stage estimates gives a conservative program envelope, not an
incremental-only invoice. Group expansion and all selected splits are included.
Unpriced inputs, cap overruns, empty splits, no candidates and domain shortages
are explicit blockers. `within_planning_caps` is not permission to execute:
`execution_authorized` is always false. The example's zero-dollar cap and unknown
prices intentionally do not approve a run.

```sh
python -B -m unittest discover -s graph_synthesis/corpus/tests -v
python -B -m graph_synthesis.corpus.plan --corpus ../corpus.jsonl --protocol graph_synthesis/corpus/protocol.example.json --output ../corpus-plan.json
```

Receipts contain protocol, normalized manifest, planner and plan hashes; actual
stage counts; split assignments; costs and blockers. `plan_sha256` hashes the
canonical UTF-8 JSON object before that field is added. Input record order does
not change the output. An identical receipt can be replayed, but a different
existing receipt is never overwritten. Keep outputs outside the frozen archive.
A partial write after process termination requires investigation and a new
output path; file creation is exclusive, not a transactional distributed ledger.
Hashing detects byte changes, not authenticity, registration time or scientific
correctness. Source line-ending changes can change the planner hash.

The implementation loads/sorts metadata in memory. It is a modest planning tool,
not a demonstrated million-document distributed scheduler. Gold creation,
sampling-weight-aware graph scoring, temporal/entity-disjoint split construction,
live adapters, corpus fetching, Zotero updates and queue execution remain future
work. The tests use synthetic metadata only and do not measure Jev accuracy.

## 10. Evidence release and manuscript gates

Release a query/screening ledger, version/alias map, rights manifest, parser QA,
split/leakage audit, annotation rubric and adjudication records, frozen protocol,
arm implementations/configuration, raw response journal, candidate/graph snapshots,
statistical code, metrics with explicit denominators, cost/failure accounting and
claim-to-evidence map. Respect restrictions on redistributing text and annotator
data. Keep an additive inventory for the new study; never rewrite the original
`MANIFEST.json`, `PROVENANCE.json`, original manuscript or saved observations.

Generate tables/figures from checked outputs, including corpus flow, domain/year
coverage, precision–recall, risk–coverage, calibration, paired uncertainty,
throughput/cost versus scale, graph topology and correction cascades. Blank or
unrun arms remain blank, not estimated victories. Write an empirical manuscript
only from these artifacts; distinguish observed, exploratory, planned and
unsupported claims. An LLM-written report is not independent peer review.
Distinct follow-on papers require genuinely distinct questions/contributions,
transparent shared datasets and no duplicate counting of the same evidence.

### Primary sources checked for this methodology

See [references.bib](references.bib). These sources justify specific design
choices, not a completed literature survey:

- **[prisma2020]** PRISMA 2020 reporting materials: https://www.prisma-statement.org/prisma-2020
- **[karma2026]** KARMA, version 2, 2026-01-11: https://arxiv.org/abs/2502.06472v2
- **[pmcoa]** PMC Open Access Subset and permitted retrieval/rights guidance: https://pmc.ncbi.nlm.nih.gov/tools/openftlist/
- **[openalexhelp]** OpenAlex current access and API documentation portal: https://help.openalex.org/
- **[s2orc2020]** Lo et al., S2ORC, ACL 2020: https://aclanthology.org/2020.acl-main.447/

Current service access/terms must be checked again when an actual run is approved.
