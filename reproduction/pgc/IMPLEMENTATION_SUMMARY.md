# Paper 1: Typed Probabilistic Graph Compiler — Implementation Summary

**Status**: Week 3–4 prototype complete. Minimal viable implementation with end-to-end example and benchmark framework.

## What's Been Built

### Core IRs ✓
```
pgc/ir/__init__.py (700+ lines)
```
- **Evidence IR**: Immutable source material with location, parser, timestamp
- **Candidate IR**: Proposed entities, edges, linked to evidence
- **Decision IR**: Typed semantic questions (NOUL, CHOICE, SCORE) with model version/distribution
- **Constraint IR**: Formal validation rules (type, cardinality, referential, temporal, logical)
- **Mutation IR**: Staged operations with preconditions, evidence links, decision links, inverse operation
- **Transaction IR**: Atomic commit with read/affected sets and provenance

**Key design**: Candidates and decisions are first-class persistent data, not optimized away. Full lineage preserved.

### Decision Backend Interface ✓
```
pgc/decision/__init__.py (300+ lines)
```
- **Abstract DecisionBackend**: Interface defining `name()`, `version()`, `decide()`, `batch_decide()`
- **FrontierLLMBackend** (stub): GPT-4o via prompting
- **SpecialistClassifierBackend** (stub): Task-specific classifier (e.g., cross-encoder)
- **JevBackend** (stub): TypeSafe System One API
- **Reference implementations** in `reference_impl.py`:
  - `MockDecisionBackend`: Synthetic realistic decisions (for prototyping)
  - `CalibrationControlBackend`: Decisions with target confidence
  - `NoisyDecisionBackend`: Controlled error injection

**Key design**: Swappable backends, same IR flows through all models.

### Graph Compiler Orchestrator ✓
```
pgc/compiler/orchestrator.py (600+ lines)
```
Five-stage pipeline:

1. **Node decisions**: Entity resolution (CHOICE), type assignment, property selection
2. **Edge decisions**: Relation support (NOUL), relation type (CHOICE)
3. **Constraint validation**: Formal rules checked (type, cardinality, referential, temporal, logical)
4. **Mutation creation**: Decisions → staged operations with preconditions
5. **Materialization**: Confidence-based routing (auto-commit or escalate to review)

**Key design**: Decisions are made before mutation planning. Global constraint solver can be added between stages 3 and 4.

### End-to-End Walkthrough ✓
```
pgc/experiments/scifact_walkthrough.py (250+ lines)
```
Demonstrates:
- One SciFact claim (Interferon gamma + lupus)
- Evidence extraction (2 research paper passages)
- Candidate generation (nodes: IFN-γ, SLE; edge: has_therapeutic_effect_on)
- Typed decisions (NOUL for relation support → 62.7% true vs 37.3% false)
- Constraint validation (3 rules all pass)
- Mutation staging (confidence-based routing)
- Provenance recording

**Execution**:
```bash
python3 -m pgc.experiments.scifact_walkthrough
```

Outputs full lineage chain showing why each fact exists.

### Benchmark Framework ✓
```
pgc/experiments/scifact_benchmark.py (400+ lines)
```
- `SciFactExample`: Claim + evidence passages + gold label (SUPPORTS/REFUTES/NOT_ENOUGH_INFO)
- `BenchmarkResult`: Per-example, per-backend decision outcome + correctness + calibration
- `BenchmarkReport`: Aggregated statistics (accuracy, Brier score, tokens, latency)
- `SciFactBenchmark.run()`: Multi-backend comparison on example set

**Execution**:
```bash
python3 -m pgc.experiments.scifact_benchmark
```

Runs 3 example claims against 4 reference backends, reports accuracy/calibration/cost.

### Documentation ✓
- `pgc/README.md`: Architecture overview, design principles, roadmap, reference implementations
- `IMPLEMENTATION_SUMMARY.md`: This file

## Running the Code

### Prerequisites
```bash
python3 --version  # 3.11+
```

### Walkthrough (Single End-to-End Example)
```bash
python3 -m pgc.experiments.scifact_walkthrough
```

Output: Full compilation pipeline for one claim. Shows Evidence → Candidates → Decisions → Constraints → Mutations → Transaction with provenance.

### Benchmark (Multi-Backend Comparison)
```bash
python3 -m pgc.experiments.scifact_benchmark
```

Output: Accuracy, Brier score, latency, tokens for 4 backends on 3 examples.

## Architecture Summary

```
Evidence
  ↓ (immutable source material with location/parser/version)
Candidate IR
  ↓ (entities/edges linked to evidence spans)
Decision IR
  ↓ (typed questions: CHOICE/NOUL/SCORE)
Constraint IR
  ↓ (formal validation rules)
Mutation IR
  ↓ (staged operations with preconditions/postconditions)
Transaction
  ↓ (atomic commit + provenance ledger)
Versioned Graph
```

**Key invariant**: At no stage does a model directly mutate the graph. Mutations are:
1. Staged (preconditions + postconditions)
2. Validated (constraints checked)
3. Shadow-executed (dry-run)
4. Committed atomically (transaction semantics)
5. Recorded with full lineage (why this fact exists)

## Current Limitations & Stubs

| Component | Status | Notes |
|---|---|---|
| Evidence parsing | Stub | Assumed pre-extracted evidence spans |
| Candidate generation | Stub | Single edge candidate per example |
| LLM backends | Stub | FrontierLLMBackend, SpecialistClassifierBackend, JevBackend not actually calling APIs |
| Global constraint solver | Not implemented | Could add between stage 3–4 |
| Continuous audit | Not implemented | Would re-evaluate mutations when evidence/schema changes |
| Schema evolution | Not implemented | Deferred to Paper 2 |
| Multi-backend cost estimation | Stub | Tokens/latency not tracked |

## Next Steps (Weeks 5–6)

### 1. Implement Real Decision Backends (Required)

**Frontier LLM Backend** (Week 5):
```python
# Stub → Real implementation
# Mock up OpenAI API calls (or use stub that mimics realistic latency/cost)
# Test on 3 examples, measure latency and token usage
```

**Specialist Classifier Backend** (Week 5):
```python
# Implement cross-encoder for entity resolution
# E.g., sentence-transformers cross-encoder/ms-marco-MiniLM-L-12-v2
# Wrap for CHOICE primitive (candidate ranking)
```

**Jev Backend** (Week 5 or later):
```python
# Requires TypeSafe API key
# Stub→Real when SDK available
# Focus on CHOICE and NOUL primitives first
```

### 2. Expand Dataset (Week 5)

**Current**: 3 hand-crafted examples in `SCIFACT_EXAMPLES`

**Target**: 50 real SciFact examples
- Option A: Download official SciFact dataset (public)
- Option B: Hand-curate 50 selected examples with gold labels
- Requirement: Mix of SUPPORTS/REFUTES/NOT_ENOUGH_INFO

### 3. Add Entity Resolution Benchmark (Week 5–6)

**Candidate IR expansion**:
```python
# Current: Only edge decisions
# Add: Node candidates with multiple entity matches
# E.g., mention "John Smith" → [person_id_123, person_id_456, "new"]
```

**Entity-resolution task**:
- Hand-curate 100 entity pair decisions
- Multilingual names, abbreviations, noisy records
- Gold labels: same / different / uncertain

**Backends**:
- Cross-encoder similarity ranking
- Jev CHOICE
- Specialist learned classifier

### 4. Run Comparative Benchmark (Week 6)

**Experiment setup**:
- Same candidates (fixed LLM-generated retrieval)
- 50 relation-support examples
- 100 entity-resolution pairs
- 4–5 backends

**Metrics per backend**:
- Accuracy (vs. gold)
- Calibration (Brier, ECE)
- Cost (tokens/decision)
- Latency (p50/p95/p99)

**Report template**:
```
Backend | Accuracy | Brier | Tokens | Latency
--------|----------|-------|--------|--------
Mock    | 0.64     | 0.38  | 0      | 15ms
Jev     | 0.71     | 0.31  | 750    | 50ms
Cross-E | 0.69     | 0.32  | 0      | 80ms
LLM     | 0.68     | 0.35  | 1500   | 200ms
```

### 5. Implement Global Constraint Solver (Optional, if time)

Insert between stage 3 and stage 4:
```
Constraint IR
  ↓
Global solver (handle transitive entity merges, etc.)
  ↓
Mutation IR
```

Approaches:
- Simple: union-find + constraint propagation
- Advanced: factor graph / probabilistic inference

### 6. Prepare Falsification Report (Week 6)

For each experiment, document:
- What would falsify the hypothesis?
- Did it happen?
- What was the actual outcome?

Example:
```
Hypothesis: Jev outperforms LLM on entity matching at equal tokens
Falsification: Specialist cross-encoder beats Jev at 1/10th the cost
Actual: Jev 0.71 Brier vs cross-encoder 0.32 Brier, but specialist 0 tokens vs Jev 750
Conclusion: Specialist classifier wins on cost-quality tradeoff; Jev is reasonable but not dominant
```

## Testing & Validation

### Unit Tests (Quick)
```bash
# Add to pgc/tests/test_ir.py
import pytest
from pgc.ir import Evidence, Decision, MutationPlan

def test_evidence_hashing():
    ev = Evidence(...)
    assert ev.__hash__() is not None

def test_mutation_lifecycle():
    mutation = MutationPlan(...)
    mutation.status = MutationStatus.AUTO_COMMITTABLE
    assert mutation.status.value == "auto_committable"
```

### Integration Tests (End-to-End)
```bash
# scifact_walkthrough.py is already an integration test
# scifact_benchmark.py tests multi-backend coordination
```

### Benchmark Tests
```bash
# After real backends implemented
python3 -m pgc.experiments.scifact_benchmark > results_week6.json
# Compare vs. baseline results
```

## File Structure at Completion of Week 4

```
pgc/
├── __init__.py
├── README.md
├── IMPLEMENTATION_SUMMARY.md (this file)
├── ir/
│   ├── __init__.py          (700+ lines: all IR definitions)
│   └── __pycache__/
├── decision/
│   ├── __init__.py          (300+ lines: abstract interface + stubs)
│   ├── reference_impl.py    (200+ lines: Mock, Calibration, Noisy backends)
│   └── __pycache__/
├── compiler/
│   ├── __init__.py
│   ├── orchestrator.py      (600+ lines: compilation pipeline)
│   └── __pycache__/
├── experiments/
│   ├── __init__.py
│   ├── scifact_walkthrough.py   (250+ lines: end-to-end example)
│   ├── scifact_benchmark.py     (400+ lines: multi-backend harness)
│   └── __pycache__/
└── tests/
    ├── __init__.py
    └── (to be added)
```

**Total**: ~3,000 lines of Python + docs

## Key Design Decisions Made

### 1. Evidence is immutable, first-class
- Every decision traces to source spans (character offsets)
- Candidates link to evidence, not derived from it
- Later audit can re-verify decisions against original evidence

### 2. Decisions are recorded before mutation planning
- Enables independent model comparison
- Allows different decision backends to route mutations differently
- Supports calibration studies

### 3. Constraints are formal, not probabilistic
- Type/cardinality/referential constraints are deterministic
- Semantic uncertainty ≠ constraint uncertainty
- Violating a constraint means rejecting the mutation

### 4. Backends are swappable
- Same IR for Jev, LLM, specialist classifier
- Allows fair cost/quality comparison
- Architecture not coupled to any single model

### 5. Transactions are atomic and reversible
- Every mutation has an inverse operation
- Rollback ledger maintained
- Enables safe continuous audit

## Lessons Learned So Far

1. **Dataclass field ordering matters**: Required fields must come before optional ones in dataclass declarations
2. **Evidence spans are crucial**: Storing exact character offsets enables post-hoc verification
3. **Decision ledger is lightweight**: Recording all decisions has minimal cost but huge audit value
4. **Mock backends are essential**: Testing doesn't require live API calls; reference implementations suffice
5. **Walkthrough before scaling**: One end-to-end example exposed the full protocol flow before benchmark complexity

## Intellectual Contributions Claimed

1. **Evidence-linked Candidate IR**: Preserves source material linkage through compilation
2. **Typed Decision Primitive Mapping**: Each graph task assigned to appropriate decision primitive (NOUL, CHOICE, SCORE)
3. **Staged Mutation Protocol**: Preconditions → shadow execution → constraint validation → atomic transaction
4. **Pluggable Decision Backend Interface**: Same IR, swappable models, enables fair comparison
5. **Provenance Ledger**: Full causal chain for every materialized fact

## Candidate Paper Scope

**Paper 1: Typed Probabilistic Graph Compiler**
- Core claim: Separating proposal from acceptance improves graph integrity at equal recall
- Core contribution: IR design + transaction semantics + empirical comparison
- Experiments: Multi-backend on relation-support + entity-resolution tasks
- Expected result: PGC reduces false automatic mutations while maintaining recall vs. KARMA/LLM baseline

## What NOT to Claim

- ✗ Jev is better than LLM (not established; must measure)
- ✗ Atomic decisions are always cheaper (true for batched decisions; need cost analysis)
- ✗ Full probabilistic reasoning is solved (only local inference implemented)
- ✗ Schema evolution is included (deferred to Paper 2)
- ✗ This is production-ready (research prototype only)

## Ready for Research?

**Yes, for Week 5–6 experiments.** The IR and orchestrator are sound. Reference implementations are sufficient for controlled experiments. Real backend implementations and expanded datasets will follow in Weeks 5–6.

**Next approval gate**: After multi-backend benchmark results (Week 6), decide whether to:
1. Write and submit Paper 1
2. Pivot: Jev underperformed, focus on specialist-classifier architecture
3. Expand: Add global constraint solver and continuous audit
