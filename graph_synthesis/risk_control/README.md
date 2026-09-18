# Five risk-controlled Jev follow-ups

Read the [executed report](RESULTS.md), [frozen protocol](PROTOCOL.md), [claim map](CLAIM_EVIDENCE.md), and [machine-readable results](results.json). These experiments extend PR #15, without altering the original evidence or any default compiler policy.

**Zero fresh Jev calls.** Three saved-response policy tests, one observed-label review simulation plus independent allocation oracles, and one controlled conflict-optimization suite are distinct evidence classes. H1-H4 miss their frozen primary targets. H5 meets the bounded algorithmic target, not a semantic-accuracy target.

```bash
python -B -m unittest discover -s graph_synthesis/risk_control/tests -v
python -B -m graph_synthesis.risk_control.run --check
python -B -m graph_synthesis.risk_control.report --figures --update-paper
python -B -m graph_synthesis.render_current_paper --output manuscript/paper-current.pdf
```

The original multicall development/evaluation split is preserved. Every decision and charged physical call is retained in predictions.json. The protocol's source hashes and source-response reconstruction are checked by the runner. Result, source, figure and validation hashes are in artifact-manifest.json. The full current paper preserves earlier sections and their original conclusions/limitations. This is an author-review draft, not a claim of external peer review.
