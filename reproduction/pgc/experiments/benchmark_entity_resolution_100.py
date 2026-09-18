"""Entity-resolution fixture benchmark with explicit semantic/service denominators."""

import json
import os
import random
from typing import List

from pgc.decision import DecisionRequest
from pgc.evaluation import DiagnosticBackend, ER_LABELS, EvaluationResult, evaluate_request, summarize_results, save_benchmark_artifact
from pgc.experiments.entity_resolution_100 import load_entity_resolution_100, ERExample
from pgc.ir import PrimitiveType


ERBenchmarkResult = EvaluationResult


class EntityResolutionBenchmark:
    """Binary identity evaluation; uncertain gold cases are retained but unscored."""

    def __init__(self, examples: List[ERExample]):
        self.examples = examples
        if len({example.example_id for example in examples}) != len(examples):
            raise ValueError("Example IDs must be unique within a benchmark")
        for example in examples:
            if example.gold_label not in (*ER_LABELS, "uncertain"):
                raise ValueError(f"Unknown ER gold label: {example.gold_label}")

    def run(self, backends, dry_run=False):
        names = [backend.name() for backend in backends]
        if len(names) != len(set(names)):
            raise ValueError("Backend names must be unique within a benchmark")
        results = [self._run_one(example, backend, dry_run)
                   for example in self.examples for backend in backends]
        return {"results": results, "n_examples": len(self.examples), "n_backends": len(backends)}

    def _run_one(self, example, backend, dry_run=False):
        payload = {"mention_1": example.mention_1, "mention_2": example.mention_2,
                   "context": example.context}
        request = DecisionRequest(
            request_id=f"req_{example.example_id}_{backend.name()}",
            primitive=PrimitiveType.NOUL,
            question="Do these mentions refer to the same entity?",
            state=json.dumps(payload, ensure_ascii=False), labels=list(ER_LABELS),
            task="entity_resolution", payload=payload,
        )
        return evaluate_request(example.example_id, example.gold_label, backend, request,
                                ER_LABELS, excluded_gold_labels=("uncertain",), dry_run=dry_run)


def compute_summary(results):
    return summarize_results(results, ER_LABELS)


def run_entity_resolution_benchmark(*, backends=None, examples=None, output_path=None,
                                    seed=0, manifest=None, dry_run=False):
    """Run and write a new results/ artifact; never overwrite historical JSONs.

    Pass backend instances for controlled experiments. Defaults initialize the
    local specialist and explicitly synthetic controls, plus Jev only when a key
    is present. This fixture benchmark is not an official dataset evaluation.
    """
    random.seed(seed)
    examples = load_entity_resolution_100() if examples is None else examples
    if backends is None:
        backends = [DiagnosticBackend(seed=seed), DiagnosticBackend(seed=seed, fixed_confidence=0.85)]
        if not dry_run:
            from pgc.decision.specialist_er import SpecialistERBackend
            backends.insert(0, SpecialistERBackend())
        if not dry_run and os.environ.get("TYPESAFE_API_KEY"):
            from pgc.decision.jev_real import JevRealBackend
            backends.append(JevRealBackend(api_key=os.environ["TYPESAFE_API_KEY"]))
    report = EntityResolutionBenchmark(examples).run(backends, dry_run=dry_run)
    summaries = {backend.name(): compute_summary([row for row in report["results"]
                                                if row.backend_name == backend.name()])
                 for backend in backends}
    output = save_benchmark_artifact("entity_resolution_100_curated", examples,
                                    report["results"], summaries, output_path=output_path,
                                    seed=seed, manifest=manifest)
    report["output_path"] = str(output)
    print(f"Saved {len(report['results'])} records to {output}")
    return report, summaries


if __name__ == "__main__":
    run_entity_resolution_benchmark()
