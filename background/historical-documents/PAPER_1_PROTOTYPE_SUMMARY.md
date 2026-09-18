# Paper 1: Typed Probabilistic Graph Compiler — Prototype Summary

> **Historical draft — superseded 2026-09-17.** This file preserves an earlier research/publication state. Its benchmark, calibration, speed/cost, completion, and publication-readiness claims are not current evidence. Use [RESULTS_REPORT.md](RESULTS_REPORT.md) for corrected experiments and limitations, and [README.md](README.md) for the implementation and reproduction commands.

**Status**: Week 4 complete. Minimal viable implementation with end-to-end walkthrough and benchmark framework ready for Week 5–6 experiments.

**Total implementation**: ~3,000 lines of Python + documentation.

## What Has Been Built

### 1. Intermediate Representations (IR) ✓
**File**: `pgc/ir/__init__.py` (700+ lines)

Complete type system for the compilation pipeline:

| IR | Purpose | Key Fields |
|---|---|---|
| **Evidence** | Immutable source material | source_id, location, parser, parser_version, timestamp |
| **Candidate** | Proposed entities/edges/schema | mention, evidence_links, candidate_values, types |
| **Decision** | Typed semantic judgments | primitive (NOUL/CHOICE/SCORE), model_version, distribution, confidence |
| **Constraint** | Formal validation rules | type, description, formal_spec, status |
| **Mutation** | Staged graph operations | operation, preconditions, evidence_links, decision_links, inverse_operation |
| **Transaction** | Atomic commits | mutations, graph_version_before, graph_version_after, read_set, affected_set |
| **Provenance** | Causal chains | entity_id, evidence, decisions, constraints, mutations, graph_version |

**Design principle**: Every mutation is traceable to evidence + decisions + constraints. Nothing is optimized away.

### 2. Decision Backend Interface ✓
**Files**: `pgc/decision/__init__.py` (300+ lines), `pgc/decision/reference_impl.py` (200+ lines)

Pluggable interface for swappable decision models:

```python
class DecisionBackend:
    def decide(request: DecisionRequest) -> DecisionResponse
    def batch_decide(requests: List[DecisionRequest]) -> List[DecisionResponse]
```

**Implementations provided**:
- `FrontierLLMBackend` (stub): GPT-4o via prompting
- `SpecialistClassifierBackend` (stub): Task-specific classifier
- `JevBackend` (stub): TypeSafe System One API
- `MockDecisionBackend` ✓: Synthetic realistic decisions
- `CalibrationControlBackend` ✓: Decisions with target confidence
- `NoisyDecisionBackend` ✓: Controlled error injection

**Key design**: Backend is interchangeable. Same IR flows through all models.

### 3. Graph Compilation Orchestrator ✓
**File**: `pgc/compiler/orchestrator.py` (600+ lines)

Five-stage pipeline:

```
Stage 1: Node Decisions
  Entity resolution (CHOICE over candidates)
  Type assignment (CHOICE over ontology)
  Property selection (CHOICE over values)
          ↓
Stage 2: Edge Decisions
  Relation support (NOUL: true/false probability)
  Relation type (CHOICE over predicate vocabulary)
          ↓
Stage 3: Constraint Validation
  Type, cardinality, referential, temporal, logical
          ↓
Stage 4: Mutation Creation
  Convert decisions → staged operations
          ↓
Stage 5: Materialization
  Confidence-based routing (commit or escalate)
```

**Key design**: Decisions made first, mutations created second. Global solver can be inserted between stages.

### 4. End-to-End Walkthrough ✓
**File**: `pgc/experiments/scifact_walkthrough.py` (250+ lines)

Demonstrates full protocol on one claim:
- Claim: "Interferon gamma has therapeutic effect on lupus"
- Evidence: 2 research paper passages
- Candidates: 2 entity nodes, 1 relation edge
- Decisions: 1 NOUL (relation support)
- Constraints: 3 validation rules (all pass)
- Mutations: 1 staged operation
- Result: Escalated to review (confidence 0.63 < threshold 0.85)

**Run**: `python3 -m pgc.experiments.scifact_walkthrough`

**Output**: ~200 lines showing:
- Evidence collection
- Candidate generation
- Decision distribution
- Constraint validation
- Mutation lifecycle
- Full provenance chain

### 5. Benchmark Framework ✓
**File**: `pgc/experiments/scifact_benchmark.py` (400+ lines)

Multi-backend comparative evaluation:

- `SciFactExample`: Claim + evidence + gold label (SUPPORTS/REFUTES/NOT_ENOUGH_INFO)
- `BenchmarkResult`: Per-example metrics (accuracy, Brier, confidence, latency)
- `BenchmarkReport`: Aggregated statistics (accuracy, calibration, tokens, latency)
- `SciFactBenchmark.run()`: Multi-backend comparison

**Run**: `python3 -m pgc.experiments.scifact_benchmark`

**Output**: Comparative results table:
```
Backend               | Accuracy | Brier | Tokens | Latency
mock-realistic        | 0.333    | 0.433 | 0      | 15.6ms
calibration-control   | 0.333    | 0.423 | 0      | 0ms
noisy-backend         | 0.333    | 0.419 | 0      | 32.5ms
```

### 6. Documentation ✓

| Document | Purpose | Audience |
|---|---|---|
| `README.md` | Architecture overview, design principles, roadmap | Researchers |
| `QUICKSTART.md` | 5-minute tutorial, code examples | Users/Developers |
| `IMPLEMENTATION_SUMMARY.md` | What's built, what's stubbed, next steps | Project leads |
| `EXTENDING.md` | Developer guide for adding backends/datasets | Contributors |
| `PAPER_1_PROTOTYPE_SUMMARY.md` | This file | Stakeholders |

## Alignment with Research Brief

### Core Hypothesis ✓
**Brief**: "Generative systems propose possibilities while typed probabilistic models decide among them"

**Implementation**: 
- Candidates = proposals from LLM/IE/graph-ML
- Decisions = typed questions (CHOICE/NOUL/SCORE) posed to any backend
- Architecture separates proposal from acceptance

### Central Contribution ✓
**Brief**: "Evidence-preserving, dependency-aware graph compiler"

**Implementation**:
- Evidence IR preserves source spans, parser, version
- Candidate IR links to evidence
- Decision IR links to candidates
- Mutation IR links to decisions
- Provenance IR traces full causal chain
- Transaction IR provides atomicity

### Decision Primitives ✓
**Brief**: "Use Jev to build graphs" → Test hypothesis, not assume

**Implementation**:
- NOUL (yes/no probability) for relation support, entity match confidence
- CHOICE (select from alternatives) for entity ID, type, relation type
- SCORE (ordered rubric) for quality/severity assessment
- Backends are swappable: Jev, LLM, specialist classifier

### Transaction Semantics ✓
**Brief**: "Mutations are staged, validated, reversible"

**Implementation**:
- `MutationStatus` lifecycle: PROPOSED → EVIDENCE_SUPPORTED → CONSTRAINT_VALID → AUTO_COMMITTABLE/REVIEW_REQUIRED → COMMITTED
- Preconditions checked before commit
- Postconditions defined
- Inverse operations recorded
- Full transaction ledger maintained

### Falsification Targets ✓
**Brief**: "Architecture must be tested against simpler alternatives"

**Implementation**:
- Benchmark compares: Mock, CalibrationControl, Noisy backends
- Easy to swap in: LLM baseline, specialist classifier, Jev
- Framework tracks: accuracy, calibration, cost, latency
- Same candidates for all backends (fair comparison)

## Key Files

```
pgc/
├── QUICKSTART.md                    ← Start here
├── README.md                        ← Architecture overview
├── IMPLEMENTATION_SUMMARY.md        ← What's done, what's stubbed
├── EXTENDING.md                     ← Developer guide
│
├── ir/
│   └── __init__.py                 (700+ lines) Evidence/Candidate/Decision/Constraint/Mutation/Transaction IRs
│
├── decision/
│   ├── __init__.py                 (300+ lines) DecisionBackend interface + stubs
│   └── reference_impl.py           (200+ lines) Mock/Calibration/Noisy implementations
│
├── compiler/
│   └── orchestrator.py             (600+ lines) Five-stage compilation pipeline
│
└── experiments/
    ├── scifact_walkthrough.py      (250+ lines) End-to-end example on one claim
    └── scifact_benchmark.py        (400+ lines) Multi-backend comparison framework
```

**Total**: ~3,000 lines of Python

## Running the Prototype

### Walkthrough (Single End-to-End Example)
```bash
python3 -m pgc.experiments.scifact_walkthrough
```
Shows full compilation pipeline. ~2 minute output demonstrating protocol flow.

### Benchmark (Multi-Backend Comparison)
```bash
python3 -m pgc.experiments.scifact_benchmark
```
Compares decision backends on 3 example claims. ~1 minute output with comparative metrics.

## Current State vs. Readiness

| Aspect | Status | Notes |
|---|---|---|
| **IR design** | ✓ Complete | All intermediate representations defined |
| **Backend interface** | ✓ Complete | Pluggable, swappable architecture |
| **Compiler orchestrator** | ✓ Complete | Five-stage pipeline implemented |
| **Mock/reference backends** | ✓ Complete | For testing without external APIs |
| **End-to-end example** | ✓ Complete | Walkthrough demonstrates protocol |
| **Benchmark framework** | ✓ Complete | Ready for multi-backend experiments |
| **LLM backend (real)** | ⏳ Week 5 | Stub exists, needs API integration |
| **Specialist backend (real)** | ⏳ Week 5 | Stub exists, needs model loading |
| **Jev backend (real)** | ⏳ Week 5–6 | Stub exists, requires API key |
| **SciFact dataset (50 examples)** | ⏳ Week 5 | 3 hand-crafted examples; need real data |
| **Entity-resolution benchmark** | ⏳ Week 5–6 | Framework ready, need 100 curated pairs |
| **Comparative results** | ⏳ Week 6 | Framework ready, need real backends |
| **Continuous audit** | ⏳ Paper 2 | Deferred |
| **Schema evolution** | ⏳ Paper 2 | Deferred |

## Roadmap: Weeks 5–6

### Week 5: Real Backends + Dataset Expansion
- [ ] Implement FrontierLLMBackend (mock or with real API)
- [ ] Implement SpecialistClassifierBackend (cross-encoder)
- [ ] Connect JevBackend (requires API key)
- [ ] Load 50 real SciFact examples
- [ ] Curate 100 entity-resolution pairs

### Week 5–6: Comparative Benchmark
- [ ] Run all backends on relation-support task
- [ ] Run all backends on entity-resolution task
- [ ] Measure accuracy, calibration, cost, latency
- [ ] Generate comparative results table
- [ ] Interpret results vs. hypotheses

### Week 6: Paper 1 Materials
- [ ] Falsification report (what could have gone wrong?)
- [ ] Negative results (if any)
- [ ] Cost/quality frontier analysis
- [ ] Draft paper results section

## Intellectual Contributions

### 1. Evidence-Linked Candidate IR
**Claim**: Candidates preserve source material linkage throughout compilation, enabling post-hoc verification.

**Evidence**: `pgc/ir/Candidate*` classes store `evidence: List[Evidence]` with character-level source spans.

### 2. Typed Decision Primitive Mapping
**Claim**: Each graph task decomposes into appropriate decision primitive (NOUL, CHOICE, SCORE), not arbitrary LLM prompts.

**Evidence**: `pgc/experiments/scifact_benchmark.py` maps: entity match → CHOICE, relation support → NOUL, etc.

### 3. Staged Mutation Protocol
**Claim**: Preconditions → shadow execution → constraint validation → atomic transaction improves safety.

**Evidence**: `pgc/ir/MutationStatus` lifecycle + `pgc/compiler/orchestrator.py` materializes this protocol.

### 4. Pluggable Decision Backend
**Claim**: Same IR enables fair comparison of Jev, LLM, specialist classifiers without architectural bias.

**Evidence**: `pgc/decision/DecisionBackend` interface + multiple implementations show interchangeability.

### 5. Benchmark Framework
**Claim**: Static extraction scores miss failures revealed by full-lifecycle testing (candidates, decisions, constraints, mutations).

**Evidence**: `pgc/experiments/scifact_benchmark.py` measures end-to-end correctness, not only extraction F1.

## What NOT to Claim Yet

- ✗ Jev is better than LLM (not measured; needs Week 5–6 experiments)
- ✗ Atomic decisions are always cheaper (true for batches; need cost analysis)
- ✗ Full probabilistic reasoning solved (only local inference implemented)
- ✗ This is production-ready (research prototype only)
- ✗ Schema evolution solved (deferred to Paper 2)
- ✗ Continuous audit works (deferred to Paper 2)

## Next Decision Point

**After Week 6 experiments**, decide:

1. **Paper 1 is ready**: Publish "Typed Probabilistic Graph Compiler" with comparative results
2. **Pivot needed**: Jev underperformed; focus on specialist-classifier architecture
3. **Expand scope**: Add global constraint solver or continuous audit as Paper 1 contribution
4. **Defer**: Results inconclusive; need larger dataset or more backends

---

## How to Use This Code Going Forward

### For experiments (Week 5–6):
1. Implement real decision backends in `pgc/decision/`
2. Expand `SCIFACT_EXAMPLES` or load real dataset
3. Run `pgc.experiments.scifact_benchmark`
4. Collect results in JSON
5. Compare backends on metrics table

### For paper writing:
1. Copy results table from benchmark output
2. Interpret comparative results
3. Report falsification targets (what could have failed?)
4. Discuss tradeoffs (cost vs. quality vs. latency)

### For external reproducibility:
- All code is pure Python, no external dependencies (for now)
- Real backends (LLM, Jev) have optional dependencies
- Mock backends allow testing without APIs
- IR definitions are stable; API unlikely to change

---

**Questions?** See `QUICKSTART.md` for examples or `EXTENDING.md` for developer guide.

**Next milestone**: Real backend implementations + experimental results (Week 6).
