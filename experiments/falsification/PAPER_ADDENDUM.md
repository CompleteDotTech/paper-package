# When cleaner decisions do not yield complete graphs

## A falsification-oriented addendum to the Jev graph-synthesis study

**Status:** AI-assisted research draft for author review. Post-hoc exploratory
analysis of existing recorded observations, with explicitly constructed stress
experiments. No fresh model evaluation, external scientific peer review, or
production qualification is claimed.

### Abstract

We extend the fixed-candidate Jev evaluation with component-level completeness,
error dependence, candidate-availability interventions, prevalence sensitivity,
and deterministic-runtime counterexamples. The selected formulation retains
fewer incorrect SciFact evidence links than the generic formulation, but also
reduces completely recovered, error-free gold-positive components from 140/164
to 126/164. Among 336 common-success examples, 34 errors occur in both arms and
31 cases receive the same wrong label. Candidate removal demonstrates a recall
ceiling that no downstream decision layer can overcome. Constructed witnesses
show that schema-correct assertions may be false, overlapping temporal
contradictions may pass exact-qualifier checking, and a single wrong identity
bridge can induce 10,000 false cross-identity pairs. Conversely, explicit bridge
retraction repairs the identity view, and 20 randomized dependency-DAG episodes
match an independent repair oracle. These results support a bounded, auditable
judgment-layer use case, not autonomous end-to-end graph synthesis.

### 1. Research question and evidence boundaries

The question is not whether typed output can be compiled into a graph, but
whether this yields useful, complete and reliable knowledge. TypeSafe's public
documentation describes state-conditioned typed judgments and atomic
composition [1]. KARMA addresses a wider pipeline, including extraction,
schema alignment, conflict resolution, and integration [2]. We therefore keep
three evidence categories separate: authentic saved Jev outputs; synthetic
candidate or runtime interventions; and analytical projections. The original
labels had already been inspected, so none of these analyses constitutes a new
held-out replication. Our added semantic challenge is prospective infrastructure,
not an executed model experiment.

### 2. Component-level utility and the precision–completeness trade-off

We form weak components of the complete candidate graph, not just accepted
edges. A positive relationship is `SUPPORTS` or `REFUTES`; a positive identity
action is `same`. A component is **complete and clean** only if it contains at
least one gold-positive candidate, all such candidates are correctly committed,
and no incorrect positive action is committed. Empty graphs cannot earn this
success label merely by avoiding errors. This is completeness relative to the
supplied candidate set, not an unknown open-corpus ground truth.

On 339 SciFact candidates, 247 candidate components include 164 gold-positive
components. At the original unmodified operating points:

| Metric | Generic Jev | Selected formulation |
|---|---:|---:|
| Correct / accepted typed evidence edges | 187 / 224 | 172 / 192 |
| Incorrect accepted edges | 37 | 20 |
| Complete and clean components | 140 / 164 (85.37%) | 126 / 164 (76.83%) |
| Contaminated / active components | 37 / 182 | 20 / 153 |

A 2,000-draw paired endpoint-component bootstrap gives a selected-minus-generic
complete-and-clean difference interval of approximately **−13.30 to −3.70
percentage points**. The precision difference interval is **+2.74 to +9.69
percentage points**. Both are exploratory pointwise intervals, conditional on
independent observed components; unseen source dependence remains possible.
They concern **unequal accepted volumes**, not prior matched-budget comparisons.
No claim of universal superiority, familywise significance, or equivalence
follows. The apparent improvement depends on which graph objective is valued.

The DBLP–ACM sample consists of 413 disconnected candidate pairs, so its
component score is not evidence about difficult multi-candidate identity
clusters. Generic Jev retains all 350 positive matches plus eight false merges;
the selected arm retains 349 positive matches plus two false merges. The
constructed identity tests below address a different, explicitly synthetic risk.

### 3. Error dependence and confidence

Among 336 SciFact rows with successful outputs in both arms, each arm has 49
classification errors; 34 are shared. Independent errors with those marginal
rates would produce approximately 7.15 shared errors. The observed/independent
ratio is approximately 4.76. In 31 cases the two arms agree on the wrong label.
This is a descriptive dependence diagnostic, not a formal independence test,
and does not make two formulations independent corroborating sources. The
three operationally excluded rows remain represented in full-cohort metrics.

For positive relationship actions with score exactly 1.0, generic Jev has six
incorrect edges among 125 accepted and the selected formulation has five among
73. These counts differ from all-class certainty counts because no-information
predictions are not positive graph writes. Exact numerical confidence cannot
be interpreted as a semantic certificate. For one fixed, preselected policy,
zero errors among independent representative accepted actions requires at least
299 observations to obtain a one-sided 95% exact binomial upper bound below 1%,
or 2,995 for 0.1%. These are planning calculations, not achieved safety bounds.

### 4. Candidate availability and prevalence

We remove complete source-ID blocks at predeclared loss levels using 100 seeded
orderings. The masks are nested and identical across arms. Candidate content is
not modified; old predictions are never reused on changed text. Recall uses the
original gold-positive denominator, and a surviving-gold oracle gives a ceiling.
At 25% document-source loss, mean relation recall becomes 67.30% for generic Jev
and 61.91% for the selected formulation, compared with an oracle ceiling of
75.02%. At 50% loss, these values are 45.14%, 41.58%, and 50.27% respectively.
Percentile ranges describe variation across constructed masks, not statistical
confidence or real retrieval-system performance.

Conditional label-shift calculations hold empirical sensitivity and false-
positive rate fixed while changing prevalence. At a hypothetical 1% positive
prevalence, selected-arm precision projects to 24.09% for identity merges,
16.83% for support, and 16.46% for refutation. These are NOT observed domain-shift
results: empirical rate uncertainty and changing conditional distributions can
invalidate them. Their value is to expose why performance on a curated,
positive-rich candidate set cannot be transported unchanged to open discovery.

### 5. Runtime counterexamples and successful repair

All scores in this section are constructed as 1.0 with the explicit model tag
`constructed-not-Jev`. They test guarantees of the existing deterministic
compiler, not model accuracy.

**Semantic truth.** An assertion whose evidence explicitly denies its claim is
accepted when supplied with an otherwise valid bound positive decision. The
same runtime atomically rejects a declared endpoint-type violation. This
separates structural validity from factual correctness.

**Temporal overlap.** The current runtime checks incompatible predicates within
identical qualifier dictionaries. It accepts an opposing pair with intervals
2020–2025 and 2024–2026 because their dictionaries differ, despite overlap.
The negative test deliberately records this limitation rather than quietly
modifying the compiler or advertising complete temporal reasoning.

**Copied sources.** Ten evidence records with one origin yield one derived edge,
not ten independent facts. Withdrawing one evidence ID leaves nine active
supporting assertions. Explicitly withdrawing all evidence IDs for the origin
removes them. The caller therefore needs an origin-aware withdrawal policy;
content hashes alone are not independent-source verification.

**Identity damage.** One false bridge between two distinct 100-record identity
clusters induces 10,000 false cross-cluster identity pairs. Removing that bridge
restores two components and zero false cross-cluster pairs. This proves the
constructed failure and repair behavior, not its prevalence in actual Jev
outputs. Smaller 2- and 10-record examples give the expected 4 and 100 pairs.

**Dependency repair.** Twenty seeded DAG episodes contain 1,600 assertions.
An independent adjacency/BFS oracle predicts 782 cascading retractions, all
matched by the runtime. Each episode also checks rollback before publication,
idempotent retries, retained assertion history, audit validity and durable
reopening. This is encouraging mechanism evidence, not a production load,
concurrency, or natural-retraction benchmark.

### 6. New semantic tests and remaining decisive experiments

A 48-case public synthetic challenge covers direction, negation, temporal and
population qualifiers, causal overstatement, coreference, missing multi-hop
context, source conflict/correction, schema typing, prompt injection and
irrelevant context. The exporter omits answer and family metadata and hashes
state, task instruction and allowed labels. The evaluator retains missing,
error and abstaining cases in denominators and rejects changed inputs,
duplicate IDs, malformed probabilities and mixed model arms. It does not
certify supplied provenance hashes as authentic provider execution.

**These 48 cases have not been run through Jev or another external model.**
Their AI-assisted synthetic gold labels require human review. Future decisive
experiments need an independently adjudicated natural corpus, candidate recall,
full-document extraction, a matched-input structured LLM plus validator,
specialist NLI/entity resolution and graph-ML baselines, and a fidelity-audited
KARMA implementation. They must report total cost, retries, latency, review
burden, graph completeness, incorrect mutation damage, and recovery. The
current results neither replace those experiments nor imply a KARMA win.

### 7. Conclusion

Jev remains plausible as a replaceable typed decision component in an
evidence-preserving workflow with abstention, explicit candidate generation,
independent validation and reversible writes. The new evidence weakens the
stronger claim that cleaner local predictions alone establish autonomous graph
synthesis. Precision gains can coincide with lower neighborhood completeness,
shared errors undermine naive corroboration, omitted candidates cap recall,
and deterministic type safety leaves semantic and temporal gaps. Reversible
provenance and dependency-aware repair remain useful regardless of which
inference backend is selected.

### References

[1] TypeSafe AI. *Introduction*. Live documentation, consulted September 18, 2026.
https://docs.typesafe.ai/introduction

[2] Lu, Y., Wu, W., Zhao, X., Peng, R., and Wang, J. *KARMA: Leveraging Multi-Agent
LLMs for Automated Knowledge Graph Enrichment*. arXiv:2502.06472v2, January 11,
2026. https://arxiv.org/html/2502.06472v2

Numerical claims derive from `results.json`, generated by
`graph_synthesis.falsification`; the original observations are bound by its
`source_hashes`. The protocol documents the post-hoc status and fixed panels.
