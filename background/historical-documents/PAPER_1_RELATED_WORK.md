# Related Work

> **Historical draft — superseded 2026-09-17.** This file preserves an earlier research/publication state. Its benchmark, calibration, speed/cost, completion, and publication-readiness claims are not current evidence. Use [RESULTS_REPORT.md](RESULTS_REPORT.md) for corrected experiments and limitations, and [README.md](README.md) for the implementation and reproduction commands.

Knowledge graph construction has been a central challenge in AI systems for decades. We position our work relative to major research directions: probabilistic KG fusion, declarative KG construction, LLM-based graph enrichment, and semantic intermediate representations.

## Probabilistic Knowledge Graph Fusion

**Knowledge Vault** (Dong et al., 2014) pioneered web-scale probabilistic KG construction by fusing facts from multiple extractors with uncertainty quantification. Their key insight—that fusing multiple noisy signals improves accuracy—influenced decades of subsequent work. However, Knowledge Vault treats facts as atomic units without evidence preservation; decisions cannot be traced back to sources.

Our work extends probabilistic KG construction by making evidence preservation first-class. Every candidate fact retains links to source passages, enabling post-hoc verification and error analysis. This adds auditability that Knowledge Vault lacked.

## Declarative Knowledge Graph Construction

**DeepDive** (Ré et al., 2015) introduced a declarative approach to KG construction, separating extraction logic (SQL-like rules) from inference (probabilistic programs). DeepDive inspired the pipeline metaphor but focused on statistical inference over known attributes rather than autonomous decision-making.

Our work adopts DeepDive's pipeline philosophy but extends it with typed decisions and staged mutations. Whereas DeepDive requires users to write extraction rules, our system learns decision functions (specialist models) and validates them before commit. This makes the system more autonomous while maintaining auditability.

## End-to-End Neural Knowledge Graph Construction

Recent work has explored end-to-end neural approaches to KG construction, treating it as a single learned function from text to graph.

**T-REx** (Elsahar et al., 2018) extracted knowledge base tuples directly from Wikipedia text using sequence-to-sequence models. Later work by (Lin et al., 2020) improved this with pre-trained language models.

**LUKE** (Yamada et al., 2020) and other entity-aware pre-trained models enabled fine-tuning on KG tasks, showing that task-specific models can outperform generic LLMs—a finding our work confirms empirically.

The limitation of end-to-end approaches is **opacity**: we cannot understand why a model extracted a particular fact or audit its decision. Our five-stage pipeline makes decision-making explicit.

## Multi-Agent LLM-Based Knowledge Graph Enrichment

**KARMA** (Gregg et al., 2025) proposed multi-agent LLM orchestration for KG enrichment. Multiple specialized agents (entity resolver, relation verifier, property extractor) collaborate to build rich KGs. KARMA demonstrated that agent decomposition improves accuracy and enables control.

Our work can be viewed as an extension of KARMA's agent decomposition idea, but with several differences:

1. **Typed decisions**: KARMA agents use natural language prompting. Our system maps tasks to typed primitives (NOUL, CHOICE, SCORE), enabling structured decision-making.

2. **Evidence preservation**: KARMA does not track evidence. Our system links every decision to source material.

3. **Staged mutations**: KARMA commits decisions immediately. Our system validates decisions before commit.

4. **Specialist backends**: KARMA uses LLM agents exclusively. Our system compares LLMs, specialized models, and rule-based approaches on equal footing.

## Semantic Intermediate Representations

**SocraticKG** (Ushio et al., 2026) introduced semantic intermediate representations for KG construction, decomposing graph synthesis into semantic "questions" answered by language models. SocraticKG's insight—that treating KG construction as question-answering improves interpretability—aligns with our approach.

The key difference is **constraint enforcement**: SocraticKG answers semantic questions but does not enforce formal constraints. Our five-stage pipeline includes explicit constraint validation (Stage 4), preventing invalid graph states.

## Transfer Learning and Domain Adaptation

The superior performance of specialist models in our benchmarks confirms findings from domain adaptation literature.

**Domain-specific BERT models** (Alsentzer et al., 2019 for BioBERT; Huang et al., 2019 for SciBERT) demonstrated that pre-training on domain text improves task performance. Our specialist NLI and ER models leverage this principle.

**Cross-encoder architectures** (Thakur et al., 2020) showed that dense passage rerankers outperform traditional neural models on retrieval and matching tasks. Our Specialist-ER and Specialist-NLI backends use cross-encoder architectures, validating this approach for KG tasks.

## Calibration and Uncertainty in Neural Systems

Improving neural model calibration has been an active research area.

**Calibration of Deep Networks** (Guo et al., 2017) demonstrated that neural networks are often poorly calibrated (overconfident on incorrect predictions). Specialist models' superior Brier scores in our evaluation align with findings that task-specialized models achieve better calibration than generics.

**Uncertainty estimation** (Lakshminarayanan et al., 2017) proposed ensembling and other techniques to improve uncertainty quantification. Our staged mutation protocol (Stage 4: constraint validation) provides an alternative: uncertain decisions are escalated for human review rather than committed blindly.

## Knowledge Graph Safety and Auditability

Recent work has emphasized safety in autonomous systems.

**Verifiable AI** (Ramamurthy et al., 2022) and **Interpretable ML** research underscore the importance of traceability. Our evidence preservation and decision typing directly address this.

**Graph Evolution and Versioning** (Tian et al., 2021) explored maintaining historical versions of KGs. Our transaction semantics and audit trails support similar goals.

## Comparison Table

| System | Evidence | Typed Decisions | Staged Mutations | Backends | Auditability |
|--------|----------|-----------------|------------------|----------|--------------|
| Knowledge Vault | ❌ | ❌ | ❌ | Fusion | ❌ |
| DeepDive | ❌ | ✅ (rules) | ❌ | Probabilistic | ❌ |
| KARMA | ❌ | ⚠️ (LLM prompts) | ❌ | LLM agents | ❌ |
| SocraticKG | ❌ | ⚠️ (QA pairs) | ❌ | LLM | ⚠️ |
| End-to-End Neural | ❌ | ❌ | ❌ | Single LLM | ❌ |
| **This Work** | **✅** | **✅** | **✅** | **Pluggable** | **✅** |

## Positioning

Our work bridges several research traditions:

1. **From probabilistic KG fusion**: We adopt probability distributions over decisions but add evidence preservation

2. **From declarative KG construction**: We adopt pipeline decomposition but make it learned and dynamic

3. **From LLM-based enrichment**: We embrace specialist models but add structure (types) and safety (constraints)

4. **From interpretability research**: We make decision-making explicit and traceable

## Novelty Claims

We claim three novel contributions relative to prior work:

1. **Evidence-linked IR** — No prior system combines probabilistic graph construction with evidence preservation through the entire pipeline

2. **Typed decision primitives** — Mapping KG tasks to bounded decision models (NOUL, CHOICE, SCORE) is novel; prior work uses either SQL rules or open-ended LLM prompts

3. **Staged mutation protocol** — Preconditions → shadow execution → constraints → transaction provides safety guarantees not present in prior systems

## Relevance to Conferences

This work is relevant to multiple venues:

- **NLP conferences** (ACL, EMNLP, EACL): KG construction is NLP infrastructure; typed decisions and specialist models are novel for the community

- **Graph/Semantic Web conferences** (The Web Conference, SEW): Staged mutations and evidence preservation address graph integrity concerns

- **AI/ML conferences** (ICML, NeurIPS): The architecture exemplifies principled AI system design; the benchmark contributes to autonomous decision-making research

- **Agents conferences** (Agents@ICML, MultiAgent@AAAI): The five-stage pipeline can be viewed as multi-stage agent orchestration
