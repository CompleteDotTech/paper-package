"""
SciFact benchmark harness.

Evaluate supplied relation-support examples and compare decision backends on:
  - Accuracy (vs. gold labels)
  - Calibration (Brier, ECE)
  - Cost (tokens)
  - Latency
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import json
from datetime import datetime

from pgc.ir import (
    Evidence, EvidenceSpan, CandidateGraphIR, EdgeCandidate,
    ConstraintSet, Constraint, PrimitiveType
)
from pgc.decision import DecisionBackend, DecisionRequest, DecisionResponse
from pgc.evaluation import EvaluationResult, RELATION_LABELS, evaluate_request, summarize_results


@dataclass
class SciFactExample:
    """One SciFact claim with evidence and gold label."""
    claim_id: str
    claim_text: str
    evidence_passages: List[str]  # Supporting or refuting text
    gold_label: str  # "SUPPORTS", "REFUTES", "NOT_ENOUGH_INFO"

    def to_evidence_ir(self, source_id: str) -> List[Evidence]:
        """Convert passages to Evidence IR."""
        evidence_list = []
        for i, passage in enumerate(self.evidence_passages):
            ev = Evidence(
                evidence_id=f"{self.claim_id}_ev_{i}",
                source_id=source_id,
                source_type="document",
                source_version="v1",
                location=EvidenceSpan(
                    source_id=source_id,
                    source_version="v1",
                    start_char=0,
                    end_char=len(passage),
                    content=passage
                ),
                parser="scifact_loader",
                parser_version="v1",
                observed_at=datetime.now()
            )
            evidence_list.append(ev)
        return evidence_list

    def to_candidate_ir(self, evidence: List[Evidence]) -> CandidateGraphIR:
        """Convert claim to candidate edge."""
        candidate_graph = CandidateGraphIR(
            graph_id=f"scifact_{self.claim_id}",
            version="v1",
            timestamp=datetime.now()
        )

        # Simple: one edge candidate per claim
        edge_cand = EdgeCandidate(
            candidate_id=f"cand_{self.claim_id}",
            kind=PrimitiveType.NOUL,
            subject_mention="[subject]",
            predicate_mention="[relation]",
            object_mention="[object]",
            evidence=evidence,
            predicate_candidates=[]  # Not used for support/refute judgment
        )

        candidate_graph.edges = [edge_cand]
        return candidate_graph


# Preserve the public names used by walkthroughs and existing callers.
BenchmarkResult = EvaluationResult


@dataclass
class BenchmarkReport:
    """Results with a fixed relation-support label contract."""
    timestamp: datetime
    backends: List[str]
    examples: List[str]
    results: List[EvaluationResult] = field(default_factory=list)

    def add_result(self, result):
        self.results.append(result)

    def summary(self, backend_name):
        return summarize_results([row for row in self.results if row.backend_name == backend_name], RELATION_LABELS)


class SciFactBenchmark:
    """Evaluate three-way relation support using full evidence and explicit errors."""

    def __init__(self, examples: List[SciFactExample]):
        self.examples = examples
        if len({example.claim_id for example in examples}) != len(examples):
            raise ValueError("Claim IDs must be unique within a benchmark")
        for example in examples:
            if example.gold_label not in RELATION_LABELS:
                raise ValueError(f"Unknown relation gold label: {example.gold_label}")

    def run(self, backends, dry_run=False):
        names = [backend.name() for backend in backends]
        if len(names) != len(set(names)):
            raise ValueError("Backend names must be unique within a benchmark")
        report = BenchmarkReport(datetime.now(), names, [example.claim_id for example in self.examples])
        for example in self.examples:
            for backend in backends:
                report.add_result(self._run_one(example, None, None, backend, dry_run))
        return report

    def _run_one(self, example, evidence=None, candidate_graph=None, backend=None, dry_run=False):
        # evidence/candidate_graph remain accepted for legacy walkthrough callers.
        passages = list(example.evidence_passages)
        payload = {"claim": example.claim_text, "evidence": passages}
        request = DecisionRequest(
            request_id=f"req_{example.claim_id}_{backend.name()}",
            primitive=PrimitiveType.CHOICE,
            question=example.claim_text,
            state=json.dumps(payload, ensure_ascii=False),
            options=list(RELATION_LABELS), labels=list(RELATION_LABELS),
            task="relation_support", payload=payload,
        )
        return evaluate_request(example.claim_id, example.gold_label, backend, request,
                                RELATION_LABELS, dry_run=dry_run)


# ============================================================================
# Example dataset (small for testing)
# ============================================================================

SCIFACT_EXAMPLES = [
    SciFactExample(
        claim_id="scifact_001",
        claim_text="Interferon gamma has a therapeutic effect on systemic lupus erythematosus",
        evidence_passages=[
            "Our findings suggest that recombinant interferon gamma significantly improved outcomes in lupus-prone mice.",
            "IFN-γ treatment resulted in reduced anti-dsDNA antibodies and decreased glomerulonephritis severity."
        ],
        gold_label="SUPPORTS"
    ),
    SciFactExample(
        claim_id="scifact_002",
        claim_text="Aspirin causes type 1 diabetes in children",
        evidence_passages=[
            "Large epidemiological studies found no causal link between aspirin use and type 1 diabetes incidence.",
            "Aspirin remains widely prescribed for fever management without increased diabetes risk in pediatric populations."
        ],
        gold_label="REFUTES"
    ),
    SciFactExample(
        claim_id="scifact_003",
        claim_text="CRISPR gene editing has been used to cure hereditary blindness",
        evidence_passages=[
            "Gene therapy approaches including CRISPR show promise in preclinical models of inherited retinal disease.",
            "Early clinical trials are underway to assess CRISPR safety and efficacy for retinitis pigmentosa."
        ],
        gold_label="NOT_ENOUGH_INFO"
    ),
]


def run_benchmark():
    """Run the small fixture demo with explicitly synthetic reference backends."""
    from pgc.evaluation import DiagnosticBackend
    backends = [DiagnosticBackend(seed=0), DiagnosticBackend(seed=0, fixed_confidence=0.85)]
    report = SciFactBenchmark(SCIFACT_EXAMPLES).run(backends)
    for backend in backends:
        print(json.dumps(report.summary(backend.name()), indent=2))
    return report


if __name__ == "__main__":
    run_benchmark()
