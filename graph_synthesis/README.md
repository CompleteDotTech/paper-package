# Evidence-preserving graph synthesis extension

This additive extension turns exact saved Jev observations into durable, source-bound graph assertions, analyzes relationships and topology, and exercises correction/retraction. It preserves all 161 files in the current baseline MANIFEST inventory. Standalone datasets remain ignored and are acquired through the existing pinned downloader. Read [the research paper](paper.md), [results](RESULTS.md), [protocol](PROTOCOL.md), and [relationship design notes](RELATIONSHIPS.md).

## Run

From the repository root, use Python 3.12 and the original NumPy pin for closest replay compatibility:

```sh
python -m pip install -r graph_synthesis/requirements-verification.txt
python -B scripts/download_datasets.py
python -B -m graph_synthesis.verify --replay --tests --output ../original-verification.json
python -B -m unittest discover -s graph_synthesis/tests -v
python -B -m graph_synthesis.study --output ../graph-study.json --export-graphs ../graphs
```

The extension itself uses the standard library; NumPy is required by the preserved replay and SciPy by four original calibration regression tests. Dataset acquisition uses the network once and checks six dataset hashes. Subsequent replay and tests make **no model calls**; the portable verifier blocks network connections during its replay and original tests. The verified full machine-readable result is `results/graph-study.json.gz` (standard gzip-compressed JSON); GitHub Actions publishes a fresh uncompressed result with verification logs. Graph exports contain the initial graph, accepted view, and post-withdrawal graph with evidence and decision hashes for each arm/task. They can contain original scientific text; existing dataset rights and notices still apply.

The original `scripts/verify_package.py` expects a closed inventory and cannot run directly against an expanded checkout; use the extension verifier. It also works around original Windows path keys in a temporary copy rather than changing frozen experiment bytes. Reported numerical tolerance is not bitwise determinism.

## Components

- `core.py`: SQLite transactions, exact assertion binding, per-predicate outcome contracts, typed relationships, scope-sensitive incompatibility, inverse/symmetric normalization, reversible identity/cannot-links, dependency retraction, review-attributed schema migration, and audit hashes.
- `recorded.py`: exact frozen input/prompt/response reconstruction; optional explicitly enabled `JevFormulation` over an injected existing Jev adapter with a call cap. No credentials are read by the extension. Applications must journal any new responses; no live calls were executed here.
- `study.py`: graph construction, source-withdrawal episodes, relationship/topology statistics, support/refute/match metrics, score frontiers, matched-count comparison, and calibration-only qualification with abstention.
- `verify.py`: strict original artifact integrity, network-blocked replay, original regression tests, and explicit cross-runtime discrepancy reporting.

## Scope and safe use

This is a tested research implementation, not an open-corpus extractor or a production database. The study compiles document-to-claim evidence links and pairwise record identity links, not a newly extracted biomedical ontology. Candidate discovery and semantic schema alignment remain external responsibilities. Supply separate decisions for nonexclusive predicates rather than forcing all graph relations into one Choice. Code checks declared constraints, not world truth.

The durable store keeps a complete JSON state per transaction and an operation journal; it is deliberately small and inspectable. Original facts are not destructively merged or deleted. Retraction marks assertions inactive and repairs the derived view. Evidence alternatives are separate assertions; evidence/dependencies within an assertion are AND prerequisites. Source hashes detect changes, not maliciously forged origins. Authorization, key management, external signatures, operational backups, and production load testing belong to the embedding application. No deployment threshold was qualified by this study.

The draft paper is for Timothy Wayne Gregg's review. No submission, authorship certification, institution, funding, ethics approval, or independent peer review is implied.
