# Visual and methodological revision record

## Scope

This is a documented self-review and visual reanalysis, not independent peer review, new annotation, new Jev inference, or publication approval. It extends repository snapshot `c3db4b81bed46b497143b30d1e26c73937ee3d67`. The original 161-file inventory is not modified. The named author remains responsible for approving the manuscript and its disclosures.

## Changes that improve assessment

| Review concern | Change | Evidence / control |
|---|---|---|
| Precision can improve merely by accepting fewer edges | Display correct, incorrect and no-edge yields for all candidates; add precision-recall and original matched-count intervals | Figures 1–3; frozen graph and relationship results |
| Generic classification can obscure relationship polarity | Treat wrong support/refutation polarity as an incorrect edge and a missed gold edge; retain NEI, errors and abstention | Confusion figures A2–A3; denominator tests |
| Confidence can be mistaken for calibrated reliability | Reconstruct raw probabilities; show classwise reliability and tie-block risk-coverage curves, including errors at score 1.0 | Figures 4, A1, A4–A6; valid-row and bin-boundary tests |
| Attractive graph pictures can hide missing nodes | Preserve all candidate nodes; plot component node mass and isolates; select an actual changed component without consulting gold | Figures 5–6; node-mass and gold-invariance tests |
| Fusion gains can be overstated | Include all existing fusion arms and paired group-bootstrap intervals; show historical input-token demand separately | Figures 7–8; effect-orientation test; no new benchmark claim |
| Retraction demonstrations can be mistaken for semantic quality | Separate lifecycle accounting from factual accuracy and preserve assertion history | Figure A7; history-conservation tests |
| Plot values can silently drift from saved observations | Reconstruct original outputs, cross-check summary counts, bind source/code/figure hashes, test corruption failure | `visualize.py --check`; `test_visualize.py` |

## Interpretation that must remain visible

The selected SciFact formulation accepts 172 correct and 20 incorrect typed evidence edges rather than 187 and 37. It therefore loses fifteen correct edges while reducing errors by seventeen. Candidate-node isolates rise from 180 to 241 out of 583. The agreement rule does not improve the fixed-budget result over the score-ranked selected arm. None of the existing paired fusion macro-F1 contrasts against the selected formulation excludes zero. High returned scores are not certificates: five of the selected arm's 73 edges scored 1.0 are incorrect.

These observations support investigation of an auditable acceptance-and-repair layer. They do not establish robust automatic extraction, ontology induction, deployment calibration, or performance against KARMA. Identity evaluation still consists of disjoint candidate pairs rather than difficult multi-record components. SciFact evidence relations are document-to-claim links, not arbitrary entity–predicate–entity facts. The illustrative calibration qualification accepts no threshold.

## Checks and evidence categories

The added unit tests verify denominator conservation, complete score-tie admission, missing-value handling, classwise rather than argmax-only reliability, polarity errors, gold-independent selection, effect orientation, topology mass, manifest integrity and failure on altered summaries. Existing graph and relationship tests remain separate. The original graph-study result is recomputed and compared with its committed structured report. CI also performs the original network-blocked replay after acquiring hash-pinned standalone datasets.

Figure images are rendered for visual inspection, and the illustrated PDF is built from the exact Markdown and SVGs. Build logs and the PDF receipt are execution evidence; a test assertion or a historical source report alone is not evidence that a new execution passed. The figure manifest checks reviewed committed assets rather than promising byte-identical rendering across platforms.

## Remaining scientific work

Independent out-of-domain evaluation, candidate-generation recall, cluster-level identity errors, blinded multi-label relation annotation, qualified acceptance thresholds, controlled ablations, real correction streams, query-level utility and end-to-end comparisons remain unmeasured. A future benchmark should freeze these decisions before reading its test labels, retain rejected candidates, use dependence-aware uncertainty, and separate discovery quality from selective commitment.
