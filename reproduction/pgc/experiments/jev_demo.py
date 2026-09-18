"""
Demo: Real TypeSafe Jev backend in action.

Compares Jev against mock backends on SciFact examples.
"""

import os
import json
from datetime import datetime
from pgc.decision.jev_real import JevRealBackend
from pgc.decision.reference_impl import MockDecisionBackend, CalibrationControlBackend
from pgc.experiments.scifact_benchmark import SciFactBenchmark, SCIFACT_EXAMPLES


def run_jev_demo(api_key: str):
    """
    Run Jev against 3 SciFact examples and compare with mock backends.

    Args:
        api_key: TypeSafe API key from https://console.typesafe.ai/keys
    """

    print("=" * 80)
    print("JEV REAL BACKEND DEMO: SciFact Benchmark")
    print("=" * 80)

    # Initialize backends
    print("\nInitializing backends...")
    backends = [
        JevRealBackend(api_key=api_key),
        MockDecisionBackend(name_prefix="mock"),
        CalibrationControlBackend(confidence_level=0.85),
    ]

    for backend in backends:
        status = "✓ ready" if (not hasattr(backend, 'available') or backend.available) else "⚠ unavailable"
        print(f"  {backend.name():30} {status}")

    # Run benchmark
    print("\nRunning benchmark on 3 SciFact examples...")
    benchmark = SciFactBenchmark(examples=SCIFACT_EXAMPLES)
    report = benchmark.run(backends, dry_run=False)

    # Print results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    results_table = []
    for backend_name in [b.name() for b in backends]:
        summary = report.summary(backend_name)
        if summary:
            results_table.append(summary)
            print(f"\n{backend_name}")
            print(f"  Accuracy:        {summary['accuracy']:.3f}")
            print(f"  Brier Score:     {summary['brier_score']:.3f}")
            print(f"  Mean Confidence: {summary['mean_confidence']:.3f}")
            print(f"  Tokens/Example:  {summary.get('tokens_per_example', 'N/A')}")
            print(f"  Mean Latency:    {summary['mean_latency_ms']:.1f}ms")

    # Jev API usage
    if backends[0].available:
        stats = backends[0].get_stats()
        print("\n" + "=" * 80)
        print("JEV API USAGE")
        print("=" * 80)
        print(f"  Total input tokens:  {stats['total_input_tokens']:,}")
        print(f"  Total output tokens: {stats['total_output_tokens']:,}")
        print(f"  Estimated cost:      ${stats['cost_usd']:.6f}")
        print(f"  Pricing rate:        {stats['pricing_rate']}")

    # Detailed results
    print("\n" + "=" * 80)
    print("DETAILED RESULTS (JSON)")
    print("=" * 80)

    results_json = {
        "timestamp": report.timestamp.isoformat(),
        "examples": len(report.examples),
        "backends": len(report.backends),
        "summary": results_table,
        "detail": [
            {
                "example_id": r.example_id,
                "backend": r.backend_name,
                "gold_label": r.gold_label,
                "predicted_label": r.predicted_label,
                "correct": r.correct,
                "confidence": r.confidence,
                "distribution": r.distribution,
                "latency_ms": r.latency_ms,
                "tokens": r.tokens_used,
            }
            for r in report.results
        ]
    }

    print(json.dumps(results_json, indent=2))

    # Save results
    output_file = "/tmp/jev_demo_results.json"
    with open(output_file, "w") as f:
        json.dump(results_json, f, indent=2)
    print(f"\n✓ Results saved to {output_file}")

    return report


if __name__ == "__main__":
    import sys

    # Get API key from argument or environment
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
    else:
        api_key = os.environ.get("TYPESAFE_API_KEY")

    if not api_key:
        print("Error: No API key provided")
        print("Usage: python3 -m pgc.experiments.jev_demo <api_key>")
        print("   or: TYPESAFE_API_KEY=<key> python3 -m pgc.experiments.jev_demo")
        sys.exit(1)

    try:
        report = run_jev_demo(api_key)
        print("\n✓ Demo completed successfully")
    except Exception as e:
        print(f"\n✗ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
