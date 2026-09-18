# Relationship analysis and compiler contract

## Predicate meaning is separate from evidence polarity

A directed fact such as `(drug, treats, condition)` is a candidate domain assertion. `SUPPORTS`, `REFUTES`, and `NOT_ENOUGH_INFO` judge a source against that candidate; they are not interchangeable with the domain predicate. A high-probability refutation must not authorize a positive edge. The compiler therefore requires an explicit allowed outcome for each predicate and binds the distribution to the exact candidate, evidence identifiers, qualifiers, and decision policy.

The measured SciFact graph uses `(document, supports|refutes, claim)` explicitly. A document refuting a claim does not create the opposite biomedical relation. Different documents may disagree about one claim; that disagreement is retained as provenance, not resolved by majority vote. Neither evaluated arm happens to create a claim with opposing source-label edges, so conflict rejection is validated by synthetic tests rather than natural conflicts in this split.

## Implemented relationship rules

| Concern | Implemented behavior | Deliberate boundary |
|---|---|---|
| Direction | Preserve subject and object for asymmetric predicates | No direction guessed from word order |
| Inverse aliases | Normalize declared inverse to canonical predicate and reversed endpoints | Only explicit declarations; no learned alias equivalence |
| Symmetry | Canonicalize endpoint order, including after identity mapping | Requires matching endpoint types |
| Multi-label relations | Distinct compatible predicates may coexist on the same pair | Each needs its own accepted decision; no single exclusive Choice over all predicates |
| Domain and range | Validate endpoint types before commit | No full OWL type inference or SHACL engine |
| Incompatibility | Reject incompatible canonical predicates for identical endpoints and qualifier maps | Partially overlapping time ranges/populations require an external scope resolver |
| Transitivity | Identity views use equivalence closure and cannot-link checks | Other `transitive` annotations do not invent unsupported edges |
| Scope | Preserve time, population, modality, version, and other explicit string qualifiers | No automatic extraction or interpretation of qualifier text |
| Provenance alternatives | Multiple assertions can support one edge; retain separate evidence | No multiplication of correlated model scores or copied sources |
| Identity repair | Retract identity assertions and recompute clusters without deleting records | No independently validated large-component accuracy claim |
| Dependency repair | Withdraw evidence/facts and deactivate all dependent assertions atomically | An alternative proof must be represented as a separate assertion |
| Schema evolution | Explicit version, reviewer attribution, reason, and full active-state validation | Attribution is not authorization; automatic ontology discovery is not implemented |

## Metrics and their interpretation

Report typed edges separately from unique directed endpoint pairs. Preserve isolated candidate nodes rather than dropping them to inflate connectivity. Record degree extrema, weak-component size distribution, reciprocal pairs, multi-label pairs, node types, predicate endpoint-type counts, identity components, and assertion multiplicity. Density uses distinct non-self directed pairs divided by `n(n-1)`; symmetric edges are stored once canonically. Consequently this is a storage-convention statistic, not a biological connectivity estimate. None of these structural metrics proves factual correctness.

## KARMA comparison

KARMA v2 describes relationship extraction with multiple labels, schema alignment, conflict handling, and integration assessment; its evaluation includes graph statistics and human assessment [1, Sections 3.7–3.10 and 4.3]. Our extension instead measures the acceptance and repair of supplied, frozen candidates. This difference precludes score-for-score superiority claims. A future comparison should share candidate/evidence inputs for an acceptance-layer ablation, then separately compare full extraction pipelines at matched cost and coverage. Correctness should be adjudicated independently of either pipeline.

[1] Lu et al., *KARMA: Leveraging Multi-Agent LLMs for Automated Knowledge Graph Enrichment*, arXiv:2502.06472v2 (11 January 2026), https://arxiv.org/html/2502.06472v2.
