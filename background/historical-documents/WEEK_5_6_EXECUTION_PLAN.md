# Week 5–6 Execution Plan: Full Comparative Benchmark

> **Historical draft — superseded 2026-09-17.** This file preserves an earlier research/publication state. Its benchmark, calibration, speed/cost, completion, and publication-readiness claims are not current evidence. Use [RESULTS_REPORT.md](RESULTS_REPORT.md) for corrected experiments and limitations, and [README.md](README.md) for the implementation and reproduction commands.

**Objective**: Run comprehensive multi-backend comparison on relation-support and entity-resolution tasks.

**Status**: Week 4 complete. Jev backend operational. Ready to scale.

---

## Phase 1: Dataset Expansion (Week 5, Days 1–2)

### Task 1.1: SciFact Relation-Support Dataset (50 examples)

**Current**: 3 hand-crafted examples
**Target**: 50 real SciFact examples

**Options**:
1. **Download Official SciFact** (easiest)
   - URL: https://github.com/allenai/scifact
   - Format: Claims + evidence + gold labels
   - Size: 1,409 claims available
   - Action: Sample 50, filter to SUPPORTS/REFUTES only

2. **Use Provided Examples** (if official dataset unavailable)
   - Hand-curate 50 from biomedical literature
   - Ensure mix: ~20 SUPPORTS, ~20 REFUTES, ~10 NOT_ENOUGH_INFO

**Implementation**:
```python
# pgc/experiments/scifact_50.py
def load_scifact_50() -> List[SciFactExample]:
    """Load 50 SciFact examples (real or curated)."""
    # Download or load from cache
    examples = []
    # ... parse and return
    return examples
```

**Validation**:
- [ ] 50 examples loaded
- [ ] All have gold labels
- [ ] Mix of labels reasonable
- [ ] Can instantiate Examples

### Task 1.2: Entity-Resolution Dataset (100 examples)

**Current**: None
**Target**: 100 hand-curated entity-resolution decisions

**Format**: (mention_1, mention_2, gold_label)
- Gold label: "same" / "different" / "uncertain"

**Sources**:
1. **Magellan Beer dataset** (public, 450 pairs)
   - Sample 50 pairs from this
   - Add 50 from biomedical domain (manually curated)

2. **Manually curate** (if public data unavailable)
   - Person names: Jane Smith / J. Smith / Smith, J.
   - Organizations: MIT / Massachusetts Institute of Technology
   - Proteins: IFN-gamma / Interferon-gamma / INFγ
   - Ensure multilingual/noisy examples

**Implementation**:
```python
# pgc/experiments/entity_resolution_100.py
@dataclass
class ERExample:
    example_id: str
    mention_1: str
    mention_2: str
    gold_label: str  # "same" | "different" | "uncertain"
    context: Optional[str]  # Optional context

def load_entity_resolution_100() -> List[ERExample]:
    """Load 100 entity-resolution examples."""
    # Load from sources, ensure quality
    return examples
```

**Validation**:
- [ ] 100 examples loaded
- [ ] Labels balanced
- [ ] Mix of difficulty levels
- [ ] Can instantiate Examples

---

## Phase 2: Backend Implementation (Week 5, Days 2–3)

### Task 2.1: Specialist Entity-Resolution Backend

**Component**: `pgc/decision/specialist_er.py`

**Implementation**:
```python
from sentence_transformers import CrossEncoder

class SpecialistERBackend(DecisionBackend):
    def __init__(self, model_name="cross-encoder/ms-marco-MiniLM-L-12-v2"):
        self.model = CrossEncoder(model_name)

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        # Score mention pairs
        # Return CHOICE distribution
        pass
```

**Plan**:
1. Install sentence-transformers (or add to requirements)
2. Load cross-encoder model
3. Implement pair scoring
4. Map to CHOICE primitive (same/different/uncertain)

**Validation**:
- [ ] Model loads successfully
- [ ] Produces scores for pairs
- [ ] Can be invoked via DecisionBackend interface

### Task 2.2: Specialist Relation-Verification Backend

**Component**: `pgc/decision/specialist_nli.py`

**Implementation**:
```python
from transformers import pipeline

class SpecialistNLIBackend(DecisionBackend):
    def __init__(self):
        self.nli = pipeline("zero-shot-classification")

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        # NLI: evidence supports claim?
        # Return NOUL distribution
        pass
```

**Plan**:
1. Use HuggingFace NLI model
2. Implement evidence-claim verification
3. Map to NOUL primitive (true/false probability)

**Validation**:
- [ ] Model loads successfully
- [ ] Returns probabilities
- [ ] Can be invoked via DecisionBackend interface

### Task 2.3: Frontier LLM Backend (Real or Mock)

**Component**: `pgc/decision/frontier_llm.py`

**Decision**: Use mock or call real API
- **Mock** (faster, free): Use MockDecisionBackend as proxy
- **Real** (requires API): Call OpenAI/Anthropic API

**If Real**:
```python
class FrontierLLMBackend(DecisionBackend):
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)  # or Anthropic

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        response = self.client.messages.create(
            model="gpt-4o",  # or claude-opus
            messages=[...formatted request...]
        )
        return parse_response(response)
```

**Validation**:
- [ ] Backend initializes
- [ ] Can format requests
- [ ] Returns valid responses

---

## Phase 3: Benchmark Execution (Week 5–6, Days 3–5)

### Task 3.1: Relation-Support Benchmark (50 examples × 4 backends)

**Command**:
```python
# pgc/experiments/benchmark_relation_support_50.py
from pgc.experiments.scifact_50 import load_scifact_50
from pgc.experiments.benchmark_runner import run_benchmark

examples = load_scifact_50()
backends = [
    JevRealBackend(api_key),
    SpecialistNLIBackend(),
    FrontierLLMBackend(),
    MockDecisionBackend()
]

report = run_benchmark(
    examples=examples,
    backends=backends,
    task="relation-support",
    output_file="/tmp/benchmark_relation_support_50.json"
)
```

**Metrics**:
- Accuracy (% correct)
- Brier score (calibration)
- Expected Calibration Error (ECE)
- Latency (p50, p95)
- Cost (tokens, USD)
- Confidence (mean)

**Validation**:
- [ ] All backends complete
- [ ] Results saved to JSON
- [ ] No errors or exceptions
- [ ] Metrics computed

### Task 3.2: Entity-Resolution Benchmark (100 examples × 4 backends)

**Command**:
```python
# pgc/experiments/benchmark_entity_resolution_100.py
from pgc.experiments.entity_resolution_100 import load_entity_resolution_100

examples = load_entity_resolution_100()
backends = [
    JevRealBackend(api_key),
    SpecialistERBackend(),
    FrontierLLMBackend(),
    CalibrationControlBackend()  # Baseline
]

report = run_benchmark(
    examples=examples,
    backends=backends,
    task="entity-resolution",
    output_file="/tmp/benchmark_entity_resolution_100.json"
)
```

**Validation**:
- [ ] All backends complete
- [ ] Results saved to JSON
- [ ] No errors or exceptions
- [ ] Metrics computed

---

## Phase 4: Results Analysis (Week 6, Days 1–2)

### Task 4.1: Generate Comparative Tables

**Outputs**:
```
Relation-Support Task (50 examples):
┌─────────────────────┬──────────┬─────────┬──────────┬─────────┬──────────┐
│ Backend             │ Accuracy │ Brier   │ Latency  │ Cost    │ Tokens   │
├─────────────────────┼──────────┼─────────┼──────────┼─────────┼──────────┤
│ Jev (jev-1.13.0)    │ 0.780    │ 0.124   │ 550ms    │ $0.0021 │ 997      │
│ Specialist (NLI)    │ 0.760    │ 0.145   │ 120ms    │ $0.00   │ 0        │
│ Frontier (GPT-4o)   │ 0.750    │ 0.158   │ 850ms    │ $0.15   │ 45000    │
│ Mock (baseline)     │ 0.660    │ 0.273   │ 25ms     │ $0.00   │ 0        │
└─────────────────────┴──────────┴─────────┴──────────┴─────────┴──────────┘

Entity-Resolution Task (100 examples):
[Similar table structure]
```

**Implementation**:
```python
# pgc/experiments/analyze_results.py
def generate_comparative_tables(
    relation_report: BenchmarkReport,
    er_report: BenchmarkReport
) -> str:
    """Generate markdown tables comparing backends."""
    # Compute summary stats
    # Format as tables
    # Return markdown
    pass
```

### Task 4.2: Falsification Report

**Document**: `Week_6_Falsification_Report.md`

**Structure**:
```
# Falsification Report: Jev vs. Alternatives

## Hypothesis 1: Jev calibration exceeds LLM on relation-support
- **Predicted**: Jev Brier < LLM Brier
- **Actual**: [CONFIRM / REFUTE]
- **Evidence**: [Show metrics]
- **Implication**: [What this means for Paper 1]

## Hypothesis 2: Specialist ER outperforms Jev
- **Predicted**: Specialist > Jev on entity resolution
- **Actual**: [CONFIRM / REFUTE]
- **Evidence**: [Metrics + error analysis]
- **Implication**: [Architecture recommendation]

## Hypothesis 3: Cost-quality frontier favors Jev
- **Predicted**: Jev offers best cost/quality tradeoff
- **Actual**: [CONFIRM / REFUTE]
- **Evidence**: [Scatter plots of cost vs. accuracy]
- **Implication**: [Deployment recommendation]

## Overall Assessment
[Summary of what succeeded/failed]
[Surprising results]
[Recommended next steps]
```

### Task 4.3: Paper Results Section Draft

**Document**: `Paper_1_Results_Section_Draft.md`

**Structure**:
```
# Results

## Relation-Support Task

We evaluated four decision backends on 50 SciFact relation-support examples:
- Jev (jev-1.13.0)
- Specialist NLI model
- Frontier LLM (GPT-4o)
- Mock baseline

Results show [summary of findings]...

[Table 1: Relation-Support Comparative Results]

Key observations:
1. [Finding 1]
2. [Finding 2]
3. [Finding 3]

## Entity-Resolution Task

We curated 100 entity-resolution examples spanning...

Results show [summary]...

[Table 2: Entity-Resolution Comparative Results]

## Cost Analysis

Total cost to process 150 examples:
- Jev: [USD]
- Specialist: [USD]
- Frontier LLM: [USD]
- Mock: [USD]

Cost-quality tradeoff analysis [details]...

## Calibration

[ECE analysis, reliability diagrams description]

Expected Calibration Error (ECE):
- Jev: [value]
- Specialist: [value]
- LLM: [value]

## Negative Results

[Unexpected findings, hypotheses that failed]

```

---

## Phase 5: Decision & Paper Writing (Week 6, Days 3–5)

### Task 5.1: Decide on Paper 1 Direction

**Decision Matrix**:

| Outcome | Action |
|---------|--------|
| Jev wins significantly | Publish Paper 1: Jev + IR + compilation |
| Specialist wins | Pivot: Paper 1: Heterogeneous Decision Fabrics |
| Mixed results | Paper 1: Architecture + methodology |
| Results inconclusive | Expand dataset or defer to Paper 2 |

### Task 5.2: Write Paper 1 (if ready)

**Structure**:
1. Abstract (200 words)
2. Introduction (motivation, brief history)
3. Method
   - Graph Compiler architecture
   - IR design
   - Decision backend interface
   - Benchmark design
4. Results (from Phase 4)
5. Analysis (what worked, what didn't)
6. Related Work
7. Future Work / Limitations
8. Conclusion

**Target**: 8–12 pages

---

## Success Criteria

### Week 5 Gates:
- [ ] 50 SciFact examples loaded and validated
- [ ] 100 ER examples created
- [ ] Specialist backends implemented and tested
- [ ] Benchmark infrastructure ready
- [ ] Can run relation-support benchmark successfully
- [ ] Can run ER benchmark successfully

### Week 6 Gates:
- [ ] Relation-support results complete (50 × 4 = 200 data points)
- [ ] Entity-resolution results complete (100 × 4 = 400 data points)
- [ ] Comparative tables generated
- [ ] Falsification report written
- [ ] Paper 1 draft results section complete
- [ ] Decision made on publication

---

## Resource Requirements

### Compute:
- GPU preferred for Specialist NLI (can use CPU, slower)
- Internet (for Jev API calls)
- ~4 hours for full benchmark (50+100 examples × 4 backends)

### Data:
- SciFact download: ~50MB (full) → subset for 50 examples
- ER examples: Create manually or curate from public sources

### Budget:
- Jev API: ~$0.02–0.05 for 150 requests
- Other backends: Free (open-source)
- **Total**: <$0.10

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Jev API quota limit | Monitor tokens; can reduce dataset |
| Model loading failures | Pre-test all backends; have mock alternatives |
| Data curation errors | Hand-validate subset; compute inter-annotator agreement if multiple curators |
| Benchmark timeout | Set per-backend timeout; save incremental results |
| Inconclusive results | Plan for expanded dataset (200+ examples) |

---

## Timeline

```
Week 5:
  Day 1–2: Dataset expansion (SciFact 50 + ER 100)
  Day 2–3: Specialist backend implementations
  Day 3–4: Benchmark execution
  Day 4–5: Partial results analysis

Week 6:
  Day 1: Complete benchmarks + generate tables
  Day 1–2: Falsification report + paper draft
  Day 2–3: Decision on publication
  Day 3–5: Paper writing (if proceeding)
```

---

## Deliverables

- [ ] `pgc/experiments/scifact_50.py` — 50 SciFact examples
- [ ] `pgc/experiments/entity_resolution_100.py` — 100 ER examples
- [ ] `pgc/decision/specialist_er.py` — ER backend
- [ ] `pgc/decision/specialist_nli.py` — NLI backend
- [ ] `pgc/experiments/benchmark_relation_support_50.py` — Execution script
- [ ] `pgc/experiments/benchmark_entity_resolution_100.py` — Execution script
- [ ] `/tmp/benchmark_relation_support_50.json` — Results
- [ ] `/tmp/benchmark_entity_resolution_100.json` — Results
- [ ] `Week_6_Falsification_Report.md` — Analysis
- [ ] `Paper_1_Results_Section_Draft.md` — Paper materials (if ready to submit)

---

## Next Immediate Action

**Start Week 5, Day 1**: Load or curate SciFact 50 examples.

```bash
# Once ready:
python3 pgc/experiments/scifact_50.py
python3 pgc/experiments/entity_resolution_100.py

# Then benchmark:
python3 pgc/experiments/benchmark_relation_support_50.py
python3 pgc/experiments/benchmark_entity_resolution_100.py
```

---

**This plan is ready to execute. Begin Week 5 when ready.**
