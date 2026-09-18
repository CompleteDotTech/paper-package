"""Three-way relation-support fixture benchmark with retained provenance."""

import os
import random

from pgc.evaluation import DiagnosticBackend, save_benchmark_artifact
from pgc.experiments.scifact_50 import load_scifact_50
from pgc.experiments.scifact_benchmark import SciFactBenchmark


def run_relation_support_benchmark(*, backends=None, examples=None, output_path=None,
                                   seed=0, manifest=None, dry_run=False):
    """Write a new results/ artifact; the curated fixture is not official SciFact."""
    random.seed(seed)
    examples = load_scifact_50() if examples is None else examples
    if backends is None:
        backends = [DiagnosticBackend(seed=seed), DiagnosticBackend(seed=seed, fixed_confidence=0.85)]
        if not dry_run:
            from pgc.decision.specialist_nli import SpecialistNLIBackend
            backends.insert(0, SpecialistNLIBackend())
        if not dry_run and os.environ.get("TYPESAFE_API_KEY"):
            from pgc.decision.jev_real import JevRealBackend
            backends.append(JevRealBackend(api_key=os.environ["TYPESAFE_API_KEY"]))
    report = SciFactBenchmark(examples).run(backends, dry_run=dry_run)
    summaries = {backend.name(): report.summary(backend.name()) for backend in backends}
    output = save_benchmark_artifact("relation_support_50_curated", examples, report.results,
                                    summaries, output_path=output_path, seed=seed, manifest=manifest)
    report.output_path = str(output)
    print(f"Saved {len(report.results)} records to {output}")
    return report, summaries


if __name__ == "__main__":
    run_relation_support_benchmark()
