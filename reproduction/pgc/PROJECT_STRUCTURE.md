# PGC Project Structure & Workflow

## File Organization

```
pgc/                                    # Typed Probabilistic Graph Compiler
├── README.md                           # Architecture overview & design principles
├── QUICKSTART.md                       # 5-minute tutorial
├── IMPLEMENTATION_SUMMARY.md           # Implementation status & next steps
├── EXTENDING.md                        # Developer guide
├── PROJECT_STRUCTURE.md                # This file
│
├── __init__.py                         # Package initialization
│
├── ir/                                 # Intermediate Representations (IRs)
│   ├── __init__.py                     # ~700 lines
│   │   ├── class Evidence              # Immutable source material
│   │   ├── class Candidate*            # Proposed nodes/edges/schema
│   │   ├── class Decision              # Typed semantic questions
│   │   ├── class Constraint            # Formal validation rules
│   │   ├── class MutationPlan          # Staged operations
│   │   ├── class Transaction           # Atomic commits
│   │   ├── class ProvenanceEntry       # Causal chains
│   │   └── Enums                       # ObjectKind, PrimitiveType, etc.
│   └── __pycache__/
│
├── decision/                           # Decision Backend Interface
│   ├── __init__.py                     # ~300 lines
│   │   ├── class DecisionBackend       # Abstract interface
│   │   ├── class DecisionRequest       # Standardized question
│   │   ├── class DecisionResponse      # Standardized output
│   │   ├── class FrontierLLMBackend    # Stub: GPT-4o via prompting
│   │   ├── class SpecialistClassifierBackend  # Stub: task-specific
│   │   └── class JevBackend            # Stub: TypeSafe API
│   ├── reference_impl.py               # ~200 lines
│   │   ├── class MockDecisionBackend   # Synthetic but realistic
│   │   ├── class CalibrationControlBackend  # Target confidence level
│   │   └── class NoisyDecisionBackend  # Controlled error injection
│   └── __pycache__/
│
├── compiler/                           # Graph Compilation Orchestrator
│   ├── __init__.py                     # Empty
│   ├── orchestrator.py                 # ~600 lines
│   │   ├── class CompilationContext    # State during compilation
│   │   └── class GraphCompiler         # Five-stage pipeline
│   │       ├── _stage_node_decisions()
│   │       ├── _stage_edge_decisions()
│   │       ├── _validate_constraints()
│   │       ├── _create_mutations()
│   │       └── _materialize()
│   └── __pycache__/
│
├── experiments/                        # Benchmarks & Walkthroughs
│   ├── __init__.py                     # Empty
│   ├── scifact_walkthrough.py          # ~250 lines
│   │   ├── build_example_scifact_claim()  # Create IR for one example
│   │   └── run_walkthrough()           # Execute full pipeline
│   ├── scifact_benchmark.py            # ~400 lines
│   │   ├── class SciFactExample        # Claim + evidence + gold label
│   │   ├── class BenchmarkResult       # Per-example metrics
│   │   ├── class BenchmarkReport       # Aggregated results
│   │   ├── class SciFactBenchmark      # Multi-backend harness
│   │   └── SCIFACT_EXAMPLES            # 3 hand-crafted examples
│   └── __pycache__/
│
└── tests/                              # Unit & integration tests (future)
    └── (To be added in Week 5)

```

**Total**: ~2,256 lines of Python code + 1,500+ lines of documentation

## Compilation Pipeline Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ User provides: Evidence, Candidates, Constraints             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ GraphCompiler.compile()                                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Stage 1: Node Decisions                                    │
│  ├─ Entity resolution (CHOICE)                              │
│  ├─ Type assignment (CHOICE)                                │
│  └─ Property selection (CHOICE)                             │
│         ↓                                                    │
│  Stage 2: Edge Decisions                                    │
│  ├─ Relation support (NOUL)                                 │
│  └─ Relation type (CHOICE)                                  │
│         ↓                                                    │
│  Stage 3: Constraint Validation                             │
│  └─ Check: type, cardinality, referential, temporal, logic  │
│         ↓                                                    │
│  Stage 4: Mutation Creation                                 │
│  └─ Convert decisions → staged operations                   │
│         ↓                                                    │
│  Stage 5: Materialization                                   │
│  └─ Confidence-based routing (commit or escalate)           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Output: Transaction + CompilationContext                     │
├─────────────────────────────────────────────────────────────┤
│ ├─ Decision ledger (all questions + answers)                │
│ ├─ Mutations committed (auto-approved)                      │
│ ├─ Mutations escalated (needs review)                       │
│ ├─ Provenance chain (full causal links)                     │
│ └─ Errors (if any)                                          │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow: From Evidence to Transaction

```
Evidence
  │ (immutable source material with location/parser/version)
  ├─ source_id: "pmid_12345678"
  ├─ location: EvidenceSpan(start_char=1000, end_char=1200, content="...")
  └─ parser: "pdf_text_extractor v2.1"
  │
  ↓ (Candidates link to Evidence)
Candidate
  │ (proposed entity/edge/schema)
  ├─ mention: "Interferon gamma"
  ├─ evidence: [Evidence(...)]
  └─ candidate_entities: [("CHEBI:59879", 0.95), ("uniprot:P01579", 0.88)]
  │
  ↓ (Backend receives DecisionRequest with state + candidates)
Decision
  │ (typed semantic judgment)
  ├─ primitive: PrimitiveType.CHOICE
  ├─ question: "Which entity does mention refer to?"
  ├─ model_family: "jev-backend"
  ├─ model_version: "jev-1.13.0"
  └─ distribution: {"CHEBI:59879": 0.92, "uniprot:P01579": 0.07, "new": 0.01}
  │
  ↓ (Decisions + Evidence → Mutations)
Mutation
  │ (staged operation with full lineage)
  ├─ operation: MutationOperation.CREATE_EDGE
  ├─ preconditions: ["subject_exists", "object_exists"]
  ├─ evidence_links: [Evidence(...)]
  ├─ decision_links: ["decision_id_001"]
  ├─ status: MutationStatus.AUTO_COMMITTABLE
  └─ inverse_operation: MutationPlan(...)
  │
  ↓ (Materialization checks + Constraints)
Transaction
  │ (atomic commit with provenance)
  ├─ transaction_id: "tx_001"
  ├─ mutations: [MutationPlan(...)]
  ├─ graph_version_before: "v1"
  ├─ graph_version_after: "v2"
  └─ read_set: {"entity_123", "entity_456"}
  │
  ↓
Versioned Graph + Provenance Ledger
```

## Decision Primitive Mapping

```
Task                          Primitive   Model Options
─────────────────────────────────────────────────────────────
Entity resolution             CHOICE      cross-encoder, Jev, LLM
(mention → entity_id)         
                              
Entity type assignment        CHOICE      classifier, Jev, LLM
(what is this entity?)        
                              
Property value selection      CHOICE      classifier, Jev, LLM
                              
Relation support              NOUL        NLI, Jev, LLM
(does evidence justify edge?) 
                              
Relation type                 CHOICE      classifier, Jev, LLM
(what kind of relation?)      
                              
Contradiction detection       NOUL/       rules, classifier, LLM
                              CHOICE      
                              
Source credibility            SCORE       truth-discovery, Jev
(how reliable is source?)     
                              
Severity/impact               SCORE       LIME, domain-specific
```

## Backend Interface

```python
class DecisionBackend(ABC):
    def name() -> str
        # Identifier for this backend
        
    def version() -> str
        # Model/version string for reproducibility
        
    def decide(request: DecisionRequest) -> DecisionResponse
        # Make a single typed decision
        # Returns: distribution, confidence, latency
        
    def batch_decide(requests: List[DecisionRequest]) -> List[DecisionResponse]
        # Process multiple decisions (may batch internally)
        
    def estimate_cost(requests) -> Dict
        # Estimate tokens and cost for a batch
```

## Example Workflow: SciFact Walkthrough

```
Step 1: Load Example
  ├─ Claim: "Interferon gamma has therapeutic effect on lupus"
  ├─ Evidence passages: [passage_1, passage_2]
  └─ Gold label: SUPPORTS

Step 2: Convert to IR
  ├─ Evidence IR: [Evidence(...), Evidence(...)]
  ├─ Candidate IR: NodeCandidate(...), EdgeCandidate(...)
  └─ Constraint IR: 3 constraints (type, referential, logical)

Step 3: Initialize Compiler
  ├─ Backend: MockDecisionBackend
  └─ GraphCompiler(graph_id="scifact_example", decision_backend=backend)

Step 4: Run Compilation
  ├─ compile(evidence, candidates, constraints, dry_run=True)
  └─ Returns: (Transaction, CompilationContext)

Step 5: Inspect Results
  ├─ Decision Ledger
  │  ├─ decision_id_001
  │  │  ├─ Question: "Does evidence support relation?"
  │  │  ├─ Primitive: NOUL
  │  │  ├─ Distribution: {true: 0.627, false: 0.373}
  │  │  └─ Confidence: 0.627
  │  └─ (other decisions...)
  │
  ├─ Mutations
  │  ├─ Committed: 0 (confidence 0.627 < threshold 0.85)
  │  └─ Escalated: 1 (needs review)
  │
  └─ Transaction
     ├─ ID: tx_abc123
     ├─ Status: staged (dry_run)
     └─ Mutations: [MutationPlan(...)]

Step 6: Output Provenance
  └─ Full causal chain for each decision:
     ├─ Evidence: original text spans
     ├─ Candidate: proposed by IE/LLM
     ├─ Decision: typed question + model output
     ├─ Constraints: validation results
     ├─ Mutation: staged operation
     └─ Transaction: atomic commit record
```

## Benchmark Workflow: Multi-Backend Comparison

```
Step 1: Create Examples
  └─ SCIFACT_EXAMPLES = [
       SciFactExample(claim_id="001", ...),
       SciFactExample(claim_id="002", ...),
       SciFactExample(claim_id="003", ...),
     ]

Step 2: Create Backends
  └─ backends = [
       MockDecisionBackend(...),
       CalibrationControlBackend(confidence_level=0.85),
       CalibrationControlBackend(confidence_level=0.70),
       NoisyDecisionBackend(error_rate=0.05),
     ]

Step 3: Initialize Benchmark
  └─ benchmark = SciFactBenchmark(examples=SCIFACT_EXAMPLES)

Step 4: Run Benchmark
  ├─ report = benchmark.run(backends)
  └─ For each (example, backend):
     ├─ Create IR
     ├─ Invoke backend.decide(request)
     ├─ Compare output vs. gold label
     └─ Record: accuracy, Brier, confidence, latency

Step 5: Aggregate Results
  ├─ For each backend:
  │  ├─ Accuracy = fraction correct
  │  ├─ Brier = mean squared error
  │  ├─ Mean confidence
  │  └─ Mean latency
  │
  └─ Output: Summary table + JSON results

Step 6: Analyze
  └─ Compare backends:
     ├─ Which is most accurate?
     ├─ Which is best calibrated?
     ├─ Which is fastest?
     └─ What are the cost/quality tradeoffs?
```

## Key Design Decisions Visible in Code

### 1. Evidence is Immutable
- `Evidence` class stores exact location in source (character offsets)
- Enables post-hoc verification against original
- Parser and version captured for reproducibility

### 2. Candidates Link to Evidence
- `Candidate*` classes store `evidence: List[Evidence]`
- Enables tracing back to source at any point
- No derivation information lost

### 3. Decisions are First-Class Data
- `Decision` class records question, model, distribution, confidence
- Full `DecisionLedger` maintained for audit
- Not optimized away or discarded

### 4. Mutations are Staged
- `MutationPlan` has preconditions, postconditions, inverse operation
- `MutationStatus` shows lifecycle
- Never directly applied to graph

### 5. Backends are Pluggable
- `DecisionBackend` interface is model-agnostic
- Same IR flows through Jev, LLM, specialist classifiers
- Enables fair comparison without architectural bias

### 6. Provenance is Designed In
- `ProvenanceEntry` traces full causal chain
- Can answer "Why does this fact exist?"
- Supports rollback and audit

## Navigating the Code

### To understand the IRs:
```
pgc/ir/__init__.py
  → Evidence, EvidenceSpan
  → NodeCandidate, EdgeCandidate, PropertyCandidate, CandidateGraphIR
  → Decision, DecisionLedger
  → Constraint, ConstraintSet
  → MutationPlan, Transaction
  → ProvenanceEntry
```

### To understand the backends:
```
pgc/decision/__init__.py
  → DecisionBackend (abstract interface)
  → DecisionRequest, DecisionResponse
  
pgc/decision/reference_impl.py
  → MockDecisionBackend (realistic but synthetic)
  → CalibrationControlBackend (target confidence)
  → NoisyDecisionBackend (error injection)
```

### To understand the compiler:
```
pgc/compiler/orchestrator.py
  → CompilationContext (state during compilation)
  → GraphCompiler.compile() (five-stage pipeline)
    → _stage_node_decisions()
    → _stage_edge_decisions()
    → _validate_constraints()
    → _create_mutations()
    → _materialize()
```

### To run an example:
```
pgc/experiments/scifact_walkthrough.py
  → build_example_scifact_claim() (create one example IR)
  → run_walkthrough() (execute full pipeline)
```

### To run a benchmark:
```
pgc/experiments/scifact_benchmark.py
  → SciFactExample (claim + evidence + gold label)
  → SciFactBenchmark (multi-backend harness)
    → run(backends) (execute benchmark)
    → summary(backend_name) (aggregate results)
```

## Adding New Components

### New Decision Backend
→ `pgc/decision/my_backend.py`
→ Subclass `DecisionBackend`
→ Implement: `name()`, `version()`, `decide()`, `batch_decide()`
→ See `EXTENDING.md` for full guide

### New Constraint Type
→ `pgc/ir/__init__.py`: Add to `ConstraintType` enum
→ `pgc/compiler/orchestrator.py`: Add validation logic in `_validate_constraints()`

### New Dataset
→ `pgc/experiments/my_dataset.py`
→ Define `MyExample` class (or reuse `SciFactExample`)
→ Create `benchmark = SciFactBenchmark(examples=my_examples)`
→ Run benchmark.run(backends)

### New Decision Primitive
→ `pgc/ir/__init__.py`: Add to `PrimitiveType` enum
→ `pgc/decision/__init__.py`: Update `DecisionRequest` if needed
→ All backends: implement handling in `decide()`

---

**Quick Links**:
- Architecture: `README.md`
- Get started: `QUICKSTART.md`
- Status: `IMPLEMENTATION_SUMMARY.md`
- Extend: `EXTENDING.md`
- Run walkthrough: `python3 -m pgc.experiments.scifact_walkthrough`
- Run benchmark: `python3 -m pgc.experiments.scifact_benchmark`
