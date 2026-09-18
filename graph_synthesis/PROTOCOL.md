# Graph lifecycle replay protocol

Status: **post-hoc exploratory extension**, not preregistration. Original Jev outcomes were known before this extension was designed. Do not overwrite the archived manuscript, prompts, inputs, responses, predictions, or MANIFEST.json.

## Population and unit

Use the original evaluation and calibration inputs from base commit `5b511c88c011524ad6adb71f1d5fa22f3dc941e0`. Reconstruct decisions from raw calls after checking every input artifact against the pinned inventory. Only the original baseline and selected few-shot arms are eligible. No new model API calls, extraction, retrieval, training, or manual adjudication are part of this execution. Pinned public datasets are acquired on demand before offline verification; their six recorded hashes must match, and no standalone dataset is added back to Git.

For SciFact, nodes are original documents and claims. Edges mean that a particular document supports or refutes a supplied claim; they do not assert a biomedical relation directly. Insufficient-information results and service errors produce no edge. For DBLP–ACM, nodes are original record hashes; edges preserve pairwise same/different decisions. Identity views do not delete source records. The identity-disjoint evaluation gives two-record components and cannot test large-cluster resolution.

## Comparisons

Report all argmax decisions, both support and refutation precision/recall, operational failures, and descriptive graph topology. Precision, false-positive rate, and coverage use different explicit denominators. Evaluate the fixed score grid `[0.5,0.85,0.9,0.95,0.99,1.0]` without selecting a test-set optimum. Compare primary actions at the same accepted count, the smaller count available from either arm; rank by predicted-label probability then row identifier, never gold. Resample the original claim/document components or identity-isolated pair units jointly across arms for 1,000 percentile bootstrap draws with seed 20260918. Intervals are exploratory, conditional on the scores and selected sets, with no multiplicity correction.

Select no deployable threshold from evaluation labels. The calibration-only illustration targets 1% conditional false positives among negative pairs, using exact one-sided binomial upper bounds and Bonferroni correction across the six thresholds. Abstain when no threshold qualifies. Repeated calibration components prohibit an independent-binomial qualification: SciFact values are diagnostic, not valid safety certificates. Even an eligible identity threshold would require representative deployment sampling and independent confirmation; this run qualifies none.

## Lifecycle and relationship controls

For each of the four real-decision graphs, withdraw the source snapshot incident to the most accepted assertions (break ties by source hash, no gold). Check actual state, exact incident removal, preservation of assertion history, durable reopen, and audit continuity. These are controlled interventions on recorded sources, not observed scientific retractions. Multi-step dependency cascades, identity split, cannot-links, inverse/symmetric/directed relations, multi-label co-occurrence, qualifier separation, and failure atomicity are tested separately with explicitly synthetic scores, including 30 seeded dependency DAGs. Do not aggregate their outcomes into semantic accuracy.

## Reproduction and evidence

Run portable original replay, the original tests, new tests, and `python -B -m graph_synthesis.study --output ../graph-study.json`. Export graph snapshots with `--export-graphs ../graphs`. The original archive remains byte-for-byte intact. The portable wrapper normalizes only temporary Windows manifest paths, restores the manifest before analysis, reports serializer/roundoff discrepancies, and blocks network sockets. Counts, labels, requests, predictions, and calibration must remain exact; only derived floating-point results permit the disclosed narrow tolerance. Never call a numeric-tolerance match a byte-identical result.

## Boundaries

No KARMA implementation was rerun; its current paper is a design comparison. No graph-level semantic superiority, calibrated per-write risk, independent population replication, complete SHACL/OWL implementation, interval-overlap reasoning, source authenticity, or production scalability is established. Fresh service availability and costs are outside this offline experiment.
