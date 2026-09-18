# Scaling research coverage and full-paper graph synthesis

**Status: proposed methodology, not new experimental results or a preregistration.**
This addition starts from `e11ca93be83e4f9c73401bcecd3275e18da21901` and leaves the
original manuscript, observations, graph results and frozen inventory unchanged.

There are two different meanings of "more research papers," and this package
supports both without conflating them:

| Track | What grows | What it establishes |
|---|---|---|
| A: living literature review | Prior-art papers searched, screened, extracted and citation-linked | Coverage of methods and evidence, not Jev accuracy |
| B: full-paper experiment | Unique, rights-reviewed full-text papers processed into evidence graphs | Empirical quality and scale only after independent evaluation |

Read the [complete methodology](graph_synthesis/corpus/README.md), including
search and screening, dataset rights, provenance, gold annotation, leakage
controls, baselines, statistics, budgets, stopping rules and publication gates.
The [primary-source bibliography](graph_synthesis/corpus/references.bib) is a
small verified starting set, **not** the result of an exhaustive literature review.

## Proposed scale ladder

| Stage | Unique full papers requested | Purpose |
|---|---:|---|
| Feasibility pilot | 100 | Debug extraction, annotation, candidates and cost accounting; do not use as confirmatory evidence |
| Controlled full-paper study | 1,200 | Paired backend and pipeline comparisons, domain-specific results and independent adjudication |
| Generalization | 10,000 | Wider sources, cross-paper relationships and separately frozen temporal/domain challenges |
| Operational stress | 100,000 | Measured throughput, failure recovery, storage growth and independently sampled quality audits |

The 1,200-paper stage matches the *reported article count* in KARMA, not its
corpus, population, budget or judge. It is not a KARMA replication. Larger
metadata-only collections and 1M/10M decision stress tests are optional future
experiments, not completed full-paper evaluations. Papers, components,
candidates, decisions, attempts, tokens and graph writes must be counted separately.

## Executable offline planning

The standard-library planner validates a **curated** JSONL manifest, rejects
duplicate paper/work IDs and text hashes, selects deterministic domain quotas,
expands selected dependency groups in full, and keeps each declared group in a
single development/calibration/test split. It reports actual sizes, shortfalls,
budget assumptions and blockers. It does not discover unknown aliases or
scientific dependencies, check the underlying text bytes, or verify legal rights.
Those upstream reviews are required by the methodology.

```sh
python -B -m unittest discover -s graph_synthesis/corpus/tests -v
python -B -m graph_synthesis.corpus.plan --corpus ../corpus.jsonl --protocol graph_synthesis/corpus/protocol.example.json --output ../corpus-plan.json
```

The schema and a clearly synthetic row are documented in the full methodology.
Supply real curated metadata for a real plan; test fixtures are not publications.
The example intentionally leaves prices unknown and the spend cap at zero.
Planning never downloads content, reads credentials, makes model calls, or
authorizes a run. A hash receipt is not a public timestamp or preregistration.

## Delivered versus future work

**Implemented:** methodology, proposed machine-readable planning configuration,
manifest validation, nested sampling, declared-group splitting, conservative
decision-budget accounting, immutable receipt handling and synthetic tests.

**Specified, not executed here:** literature retrieval/screening, Zotero corpus
updates, full-text acquisition/parsing, semantic deduplication and grouping,
expert annotation, statistical power analysis, live Jev/baseline/KARMA adapters,
distributed execution, graph scoring and empirical scaling results.

The existing [graph extension](graph_synthesis/README.md) remains the measured
replay; the new protocol must earn new conclusions with new evidence.
