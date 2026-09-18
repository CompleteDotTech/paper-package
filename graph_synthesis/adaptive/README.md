# Adaptive Jev improvement study

[Executed report](RESULTS.md) | [Frozen protocol](PROTOCOL.md) | [Machine-readable results](results.json) | [Figures](figures/)

Five exploratory improvements after PR #14: compact disagreement routing, dependency-safe fallback, redundancy-capped voting, group-aware review and joint conflict optimization. The first three reuse authentic Jev responses; the last two are simulated-review and finite-oracle tests. Zero new service calls and no default compiler changes.

The methods consume validated archived call records. `run.py` verifies their byte hashes, request/response contracts and original replay before policy evaluation. A raw unvalidated service response must not be passed directly to the methods. Fitted clusters and risks use development labels only; policy execution and review selection receive no test gold labels.

```bash
python -B -m unittest discover -s graph_synthesis/adaptive/tests -v
python -B -m graph_synthesis.adaptive.run --check
python -B -m graph_synthesis.adaptive.report --figures --update-paper
python -B -m graph_synthesis.render_current_paper --output manuscript/paper-current.pdf
```

When rebuilding earlier manuscript generators, run the adaptive `report --update-paper` afterwards to restore the current additive section; the updated CI does this explicitly. Do not edit immutable historical manuscripts to accommodate later experiments.
