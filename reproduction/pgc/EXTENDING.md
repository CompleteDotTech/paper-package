# Extending PGC: Developer Guide

This guide explains how to add new decision backends, datasets, and experiment configurations.

## Adding a Decision Backend

### 1. Subclass DecisionBackend

```python
from pgc.decision import DecisionBackend, DecisionRequest, DecisionResponse
from pgc.ir import PrimitiveType

class MySpecialistBackend(DecisionBackend):
    def __init__(self, model_path: str = "my-model.pt"):
        self.model = load_model(model_path)

    def name(self) -> str:
        return "my-specialist"

    def version(self) -> str:
        return "v1.0"

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        """Make a single decision."""
        if request.primitive == PrimitiveType.CHOICE:
            # Score each option
            scores = {}
            for option in request.options or []:
                score = self.model.score(request.state, option)
                scores[option] = score
            
            # Normalize to probabilities
            total = sum(scores.values())
            distribution = {k: v / total for k, v in scores.items()}
            
            return DecisionResponse(
                request_id=request.request_id,
                distribution=distribution,
                confidence=max(distribution.values())
            )
        
        elif request.primitive == PrimitiveType.NOUL:
            # Binary classification
            prob_true = self.model.predict_probability(request.state)
            distribution = {
                "true": prob_true,
                "false": 1.0 - prob_true
            }
            return DecisionResponse(
                request_id=request.request_id,
                distribution=distribution,
                confidence=max(prob_true, 1.0 - prob_true)
            )
        
        return DecisionResponse(
            request_id=request.request_id,
            distribution={},
            error=f"Unsupported primitive: {request.primitive}"
        )

    def batch_decide(self, requests: list) -> list:
        """Optionally optimize for batching."""
        return [self.decide(req) for req in requests]
```

### 2. Register in Benchmark

```python
from pgc.experiments.scifact_benchmark import SciFactBenchmark
from pgc.decision.my_backend import MySpecialistBackend

backends = [
    MySpecialistBackend(model_path="/path/to/model"),
    # ... other backends
]

benchmark = SciFactBenchmark(examples=SCIFACT_EXAMPLES)
report = benchmark.run(backends)
```

### 3. Test the Backend

```python
from pgc.decision import DecisionRequest
from pgc.ir import PrimitiveType

backend = MySpecialistBackend()

# Single decision
request = DecisionRequest(
    request_id="test_001",
    primitive=PrimitiveType.CHOICE,
    question="Which entity?",
    state="Jane Smith worked at Google",
    options=["person_123", "person_456", "new"]
)
response = backend.decide(request)
print(f"Distribution: {response.distribution}")
print(f"Confidence: {response.confidence}")

# Batch decisions
requests = [request] * 10
responses = backend.batch_decide(requests)
print(f"Batch processed {len(responses)} requests")
```

## Adding a Dataset

### 1. Define Example Class

```python
from pgc.experiments.scifact_benchmark import SciFactExample
from pgc.ir import Evidence, EvidenceSpan
from datetime import datetime

examples = [
    SciFactExample(
        claim_id="my_001",
        claim_text="Claim about phenomenon X",
        evidence_passages=[
            "Passage 1 from paper A",
            "Passage 2 from paper B"
        ],
        gold_label="SUPPORTS"  # or "REFUTES" or "NOT_ENOUGH_INFO"
    ),
    SciFactExample(
        claim_id="my_002",
        claim_text="Different claim",
        evidence_passages=["..."],
        gold_label="REFUTES"
    ),
]
```

### 2. Add to Benchmark

```python
from pgc.experiments.scifact_benchmark import SciFactBenchmark

benchmark = SciFactBenchmark(examples=examples)
report = benchmark.run(backends)

# View summary
for backend_name in [b.name() for b in backends]:
    summary = report.summary(backend_name)
    print(summary)
```

### 3. Load from File

```python
import json
from pgc.experiments.scifact_benchmark import SciFactExample

with open("my_dataset.json") as f:
    data = json.load(f)

examples = [
    SciFactExample(
        claim_id=ex["id"],
        claim_text=ex["claim"],
        evidence_passages=ex["evidence"],
        gold_label=ex["label"]
    )
    for ex in data["examples"]
]
```

## Extending the IR

### Adding a New Constraint Type

```python
from pgc.ir import Constraint, ConstraintStatus

constraint = Constraint(
    constraint_id="c_custom",
    constraint_type="custom",  # Use string for extensibility
    description="My custom invariant",
    formal_spec="∀x: custom_property(x) > 0",
    evaluated=False,
    status=ConstraintStatus.UNKNOWN
)
```

### Adding a New Decision Primitive

Currently supported: NOUL, CHOICE, SCORE, RULE, GRAPH_MODEL

To add (e.g., RANKING):

```python
# In pgc/ir/__init__.py
class PrimitiveType(Enum):
    # ... existing ...
    RANKING = "ranking"  # New

# In your backend
def decide(self, request: DecisionRequest) -> DecisionResponse:
    if request.primitive == PrimitiveType.RANKING:
        # Return ranked items with scores
        ranked = sorted(
            [(opt, score) for opt, score in item_scores],
            key=lambda x: x[1],
            reverse=True
        )
        distribution = {
            item: (1.0 / (1 + i)) for i, (item, score) in enumerate(ranked)
        }
        return DecisionResponse(
            request_id=request.request_id,
            distribution=distribution,
            confidence=max(distribution.values())
        )
```

## Extending the Compiler

### Custom Decision Stage

```python
from pgc.compiler.orchestrator import GraphCompiler

class CustomGraphCompiler(GraphCompiler):
    def _custom_decision_stage(self, ctx):
        """Add a custom decision stage."""
        print("Running custom stage...")
        # Your logic here
        pass

    def compile(self, evidence, candidate_graph, constraints, dry_run=False):
        """Override to add custom stage."""
        ctx = CompilationContext(...)
        
        # Standard stages
        self._stage_node_decisions(ctx)
        self._stage_edge_decisions(ctx)
        
        # Custom stage
        self._custom_decision_stage(ctx)
        
        # Continue standard stages
        self._validate_constraints(ctx)
        self._create_mutations(ctx)
        self._materialize(ctx, dry_run)
        
        return transaction, ctx
```

### Custom Constraint Validator

```python
def _validate_constraints(self, ctx):
    """Override constraint validation."""
    for constraint_id, constraint in ctx.constraints.items():
        if constraint.constraint_type == "my_type":
            # Custom validation
            result = my_validator(constraint, ctx)
            constraint.status = result
        else:
            # Use default
            constraint.status = ConstraintStatus.PASS
        constraint.evaluated = True
```

## Running Experiments

### Basic Experiment

```python
from pgc.experiments.scifact_benchmark import (
    SciFactBenchmark,
    SciFactExample
)
from pgc.decision.reference_impl import MockDecisionBackend

# Define examples
examples = [
    SciFactExample(
        claim_id="test_001",
        claim_text="Example claim",
        evidence_passages=["Supporting text"],
        gold_label="SUPPORTS"
    )
]

# Create backends
backends = [MockDecisionBackend()]

# Run benchmark
benchmark = SciFactBenchmark(examples)
report = benchmark.run(backends)

# View results
summary = report.summary("mock-backend")
print(f"Accuracy: {summary['accuracy']}")
```

### Comparative Experiment

```python
from pgc.decision.reference_impl import (
    MockDecisionBackend,
    CalibrationControlBackend,
    NoisyDecisionBackend
)

backends = [
    MockDecisionBackend(name_prefix="realistic"),
    CalibrationControlBackend(confidence_level=0.85),
    CalibrationControlBackend(confidence_level=0.70),
    NoisyDecisionBackend(error_rate=0.05),
    NoisyDecisionBackend(error_rate=0.20),
]

benchmark = SciFactBenchmark(examples)
report = benchmark.run(backends)

# Compare all backends
for backend in [b.name() for b in backends]:
    summary = report.summary(backend)
    print(f"{backend}:")
    print(f"  Accuracy: {summary['accuracy']:.3f}")
    print(f"  Brier: {summary['brier_score']:.3f}")
    print(f"  Latency: {summary['mean_latency_ms']:.1f}ms")
```

## Performance Profiling

### Timing Individual Stages

```python
import time

start = time.time()
compiler.compile(evidence, candidates, constraints)
elapsed = time.time() - start

print(f"Total compilation: {elapsed:.3f}s")
```

### Profiling a Backend

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

backend = MySpecialistBackend()
for request in requests:
    backend.decide(request)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats("cumulative")
stats.print_stats(10)  # Top 10 functions
```

## Debugging

### Print Compilation Context

```python
from pgc.compiler.orchestrator import GraphCompiler

compiler = GraphCompiler(graph_id="debug", decision_backend=backend)
transaction, context = compiler.compile(evidence, candidates, constraints)

print(f"Compilation ID: {context.compilation_id}")
print(f"Evidence: {len(context.evidence)}")
print(f"Decisions: {len(context.decision_ledger.decisions)}")
print(f"Mutations committed: {len(context.mutations_committed)}")
print(f"Mutations escalated: {len(context.mutations_escalated)}")
print(f"Errors: {context.errors}")

for error in context.errors:
    print(f"  - {error}")
```

### Inspect Decision Ledger

```python
for decision_id, decision in context.decision_ledger.decisions.items():
    print(f"\nDecision {decision_id}:")
    print(f"  Question: {decision.question}")
    print(f"  Model: {decision.model_family} {decision.model_version}")
    print(f"  Distribution: {decision.distribution}")
    print(f"  Confidence: {decision.confidence}")
```

### Trace Mutations

```python
for mutation in context.mutations:
    print(f"\nMutation {mutation.mutation_id}:")
    print(f"  Operation: {mutation.operation.value}")
    print(f"  Status: {mutation.status.value}")
    print(f"  Evidence: {len(mutation.evidence_links)}")
    print(f"  Decisions: {mutation.decision_links}")
    if mutation.inverse_operation:
        print(f"  Inverse: {mutation.inverse_operation.operation.value}")
```

## Common Patterns

### Confidence-Based Routing

```python
threshold = 0.85

for mutation in mutations:
    decision = decisions[mutation.decision_links[0]]
    if decision.confidence >= threshold:
        mutation.status = MutationStatus.AUTO_COMMITTABLE
        commit(mutation)
    else:
        mutation.status = MutationStatus.REVIEW_REQUIRED
        escalate(mutation)
```

### Risk-Based Thresholding

```python
# Different thresholds for different operation types
risk_thresholds = {
    MutationOperation.CREATE_NODE: 0.80,
    MutationOperation.MERGE_NODES: 0.95,  # High risk
    MutationOperation.CREATE_EDGE: 0.85,
    MutationOperation.SET_PROPERTY: 0.75,
}

for mutation in mutations:
    decision = decisions[mutation.decision_links[0]]
    threshold = risk_thresholds.get(mutation.operation, 0.85)
    if decision.confidence >= threshold:
        commit(mutation)
    else:
        escalate(mutation)
```

### Batching Requests

```python
# Collect all decisions from one compilation pass
all_requests = []
for candidate in candidates.nodes:
    request = DecisionRequest(...)
    all_requests.append(request)

# Batch invoke backend
responses = backend.batch_decide(all_requests)

# Map responses back
for request, response in zip(all_requests, responses):
    # Process response
    pass
```

## Testing Checklist

- [ ] Backend returns DecisionResponse for all primitives
- [ ] Distribution sums to 1.0
- [ ] Confidence is between 0 and 1
- [ ] Latency is reasonable (< 1s per decision)
- [ ] Batch processing produces same results as individual calls
- [ ] Error handling graceful (returns error field, not exception)
- [ ] Dataset examples have valid gold labels
- [ ] Benchmark compiles without errors
- [ ] Results are serializable to JSON
