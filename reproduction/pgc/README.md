# Typed Probabilistic Graph Compiler (PGC)

A research prototype for **autonomous graph synthesis** via typed probabilistic decisions and transactional compilation.

## Core Hypothesis

Separating **candidate proposal** from **typed semantic acceptance** enables:

1. **Auditability**: Every mutation is traceable to evidence + decision + constraints
2. **Reversibility**: Full inverse operations recorded for rollback
3. **Heterogeneity**: Decision backend is swappable (Jev, LLM, specialist classifier)
4. **Safety**: Deterministic validation before commit; mutations are staged, not direct

## Architecture

```
Evidence IR
  ↓ (immutable source material, versioned)
Candidate IR
  ↓ (entities, edges, schema changes, linked to evidence)
Decision IR
  ↓ (typed semantic questions posed to models)
Constraint IR
  ↓ (formal validation rules)
Mutation IR
  ↓ (staged operations with preconditions)
Transaction
  ↓ (atomic commit + provenance ledger)
Versioned Graph + Audit Trail
```

## Project Structure

```
pgc/
├── ir/                     # Intermediate representations
│   └── __init__.py        # Evidence, Candidate, Decision, Constraint, Mutation IRs
├── decision/              # Pluggable decision backends
│   ├── __init__.py        # Abstract DecisionBackend interface
│   └── reference_impl.py  # Mock/reference implementations
├── compiler/              # Graph compilation orchestrator
│   └── orchestrator.py    # End-to-end compilation workflow
├── experiments/           # Benchmarks and walkthroughs
│   └── scifact_walkthrough.py  # Single end-to-end example
└── README.md
```

## Quick Start

### Run the SciFact Walkthrough

```bash
python3 -m pgc.experiments.scifact_walkthrough
```

This demonstrates:
- Evidence extraction from a research paper passage
- Candidate generation for entities and relations
- Typed semantic decisions (NOUL for relation support)
- Constraint validation
- Staged mutation with confidence-based routing
- Full provenance chain

### Key Classes

**pgc.ir.Evidence**
Immutable record of source material with location, parser, timestamp, and metadata.

**pgc.ir.CandidateGraphIR**
Proposed entities, edges, properties, linked to evidence.

**pgc.ir.Decision**
Typed semantic judgment (CHOICE, NOUL, SCORE) with model version, distribution, confidence.

**pgc.ir.MutationPlan**
Staged graph operation with preconditions, evidence links, decision links, and inverse operation.

**pgc.ir.Transaction**
Atomic commit of mutations with read/affected sets.

**pgc.decision.DecisionBackend**
Abstract interface for models. Implementations:
- `FrontierLLMBackend`: GPT-4o via prompting
- `SpecialistClassifierBackend`: Task-specific cross-encoder
- `JevBackend`: TypeSafe System One (requires API key)
- `MockDecisionBackend`: Synthetic decisions for testing

**pgc.compiler.GraphCompiler**
Orchestrates the compilation pipeline: evidence → decisions → constraints → mutations → transaction.

## Design Principles

### 1. Proposal ≠ Acceptance

Candidates are staged until decisions accept them. Rejected candidates remain in the audit trail.

### 2. Heterogeneous Decision Ownership

Each task is assigned to the best computational mechanism:
- **LLM**: Open-world candidate discovery, naming
- **Jev/classifier**: Bounded semantic choices (entity match, relation type, contradiction resolution)
- **Graph model**: Structural prediction and anomaly detection
- **Deterministic**: Constraint validation, transaction semantics

### 3. Evidence Preservation

Every fact carries lineage:
- Source evidence + location
- Candidate that proposed it
- Decisions that accepted it
- Constraints that validated it
- Model versions involved

### 4. Transactional Safety

Mutations are never directly applied:
1. Staged (preconditions + postconditions)
2. Shadow-executed (dry-run)
3. Validated (constraints checked)
4. Committed atomically (with read/affected sets)
5. Recorded (transaction + provenance ledgers)

### 5. Swappable Decision Backends

The same graph IR flows through different decision models. Architecture is not coupled to Jev (or any single model).

## Roadmap: Weeks 1–6 Prototype

### Week 1–2: IR Design ✓
- Evidence, Candidate, Decision, Constraint, Mutation IRs
- Lifecycle states (PROPOSED → EVIDENCE_SUPPORTED → CONSTRAINT_VALID → AUTO_COMMITTABLE / REVIEW_REQUIRED)
- Serialization helpers

### Week 3–4: Single End-to-End Example ✓
- SciFact claim walkthrough
- Mock decision backend
- Demonstrate compilation protocol
- Show provenance recording

### Week 5–6: Three Decision Backend Comparison
- Frontier LLM (via prompting)
- Specialist classifier (cross-encoder for ER, NLI for relation support)
- Jev (once TypeSafe SDK available)

**Run on same:**
- Dataset: 50 SciFact examples + 100 entity-resolution pairs
- Candidates: LLM-generated, fixed retrieval
- Constraints: Fixed biomedical schema
- Metrics: Accuracy, calibration (ECE), cost (tokens/decision), latency

## Experiments: Falsification Targets

| Experiment | Hypothesis | Success Criterion | False Negative |
|---|---|---|---|
| **Relation support (NOUL)** | Jev calibration on SciFact | Jev Brier ≤ LLM Brier | Specialist NLI model wins |
| **Entity resolution (CHOICE)** | ER via candidate-first approach | ER F1 matches embedding baseline | Embedding threshold simpler/faster |
| **Constraint satisfaction** | Deterministic validation prevents errors | 0 constraint violations in committed mutations | Constraints too weak/numerous to matter |
| **Escalation routing** | Confidence-based automation saves review | Cost per accepted mutation < review cost | Model confidence unreliable; escalate everything |
| **End-to-end integrity** | Compilation improves over KARMA | False auto-mutation rate 1–3% at recall parity | Candidate generation dominates; gains negligible |

## Reference Implementations

### MockDecisionBackend
Synthetic but realistic decisions. For prototyping without API calls.

```python
from pgc.decision.reference_impl import MockDecisionBackend
from pgc.compiler.orchestrator import GraphCompiler

backend = MockDecisionBackend(name_prefix="demo")
compiler = GraphCompiler(graph_id="test", decision_backend=backend)
```

### CalibrationControlBackend
Return decisions with target confidence. For testing different automation regimes.

```python
high_confidence = CalibrationControlBackend(confidence_level=0.90)
low_confidence = CalibrationControlBackend(confidence_level=0.70)
```

### NoisyDecisionBackend
Inject controlled error rates. For robustness testing.

```python
noisy = NoisyDecisionBackend(error_rate=0.05)  # 5% error rate
```

## Metrics Definition

### Graph Integrity
- **False automatic mutation rate**: Proportion of auto-committed mutations contradicting gold graph
- **Constraint violation rate**: Post-hoc check for type/cardinality/uniqueness violations
- **Rollback rate**: Fraction of mutations detected as errors during continuous audit

### Decision Quality
- **Accuracy**: Fraction of decisions matching gold standard
- **Calibration**: Expected Calibration Error (ECE), Brier score, reliability diagram
- **Selective accuracy**: Risk/coverage curve (as confidence threshold varies)

### Operational
- **Cost**: Tokens/decision at matched semantic quality
- **Latency**: p50/p95/p99 decision latency
- **Throughput**: Decisions/second
- **Provenance completeness**: % of facts with full lineage recoverable

## Next Steps

1. **Implement three decision backends** for the 50-example benchmark
2. **SciFact benchmark**: Annotate/verify 50 claims with gold relation-support labels
3. **Entity-resolution benchmark**: Hand-curate 100 harder ER pairs (multilingual, noisy records)
4. **Run baseline comparison**: LLM vs. specialist vs. Jev on fixed candidates
5. **Report metrics**: Accuracy, calibration, cost, latency for each model
6. **Negative result readiness**: Plan what falsification of Jev would look like

## Related Work

| System | Contribution | Relation to PGC |
|---|---|---|
| **Knowledge Vault** (2014) | Probabilistic fact fusion | Probabilistic facts; we add transactions + provenance IR |
| **DeepDive** (2015) | Declarative KG construction | Compilation metaphor; we add typed decisions + constraints |
| **KARMA** (2025 NeurIPS) | Multi-agent LLM KG enrichment | Direct baseline; we add IR + deterministic commit |
| **SocraticKG** (2026 EACL) | Semantic intermediate representation | Similar IR idea; we add transaction semantics |
| **PG-HIVE** (2025) | Incremental property-graph schema discovery | Schema evolution; we defer this to later |

## Paper Contributions (Candidate)

**Paper 1: Typed Probabilistic Graph Compiler**
- Formal IR separating Evidence → Candidates → Decisions → Constraints → Mutations
- Transaction protocol with provenance
- Empirical comparison: Architecture improves graph integrity at equal recall vs. KARMA/monolithic LLM
- Benchmark: Multi-domain entity resolution + relation support

## License & Citation

Prototype research. Timothy Gregg (timothy.gregg@complete.tech).

---

## Building This Further

To implement a custom decision backend:

```python
from pgc.decision import DecisionBackend, DecisionRequest, DecisionResponse

class MyBackend(DecisionBackend):
    def name(self) -> str:
        return "my-backend"

    def version(self) -> str:
        return "v1"

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        # Your logic here
        return DecisionResponse(
            request_id=request.request_id,
            distribution={"option1": 0.7, "option2": 0.3},
            confidence=0.7
        )

    def batch_decide(self, requests):
        return [self.decide(r) for r in requests]

# Use it
backend = MyBackend()
compiler = GraphCompiler(graph_id="test", decision_backend=backend)
```

To add constraints:

```python
from pgc.ir import Constraint, ConstraintSet, ConstraintStatus

my_constraint = Constraint(
    constraint_id="c_custom",
    constraint_type="logical",
    description="Custom invariant",
    formal_spec="∀x: property(x) > 0"
)

schema = ConstraintSet(schema_id="custom", schema_version="v1")
schema.constraints["c_custom"] = my_constraint
```
