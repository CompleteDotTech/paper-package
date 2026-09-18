# DSPy-assisted Jev prompt optimization

The [implemented optimizer](graph_synthesis/dspy_jev_optimizer/README.md) uses
DSPy to propose Jev instructions and criterion definitions from TRAIN feedback,
selects candidates using VALIDATION accuracy, and separately audits a frozen
winner against a held-out test. It includes live SDK adapters, an offline demo,
version-aware caching, bounded calls, probability validation, and CI tests.

Start with the [run instructions](graph_synthesis/dspy_jev_optimizer/README.md),
[Mermaid diagram](graph_synthesis/dspy_jev_optimizer/architecture.md), or
[CLI](graph_synthesis/dspy_jev_optimizer/optimize.py).

This additive implementation is not a new accuracy result and does not modify the
archived research evidence or default graph compiler policy. Test doubles and
mocked SDK checks verify software behavior, not model performance.
