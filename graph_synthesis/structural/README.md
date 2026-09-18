# Five structural refinements

[Executed report](RESULTS.md) | [Frozen protocol](PROTOCOL.md) | [Claim audit](CLAIM_EVIDENCE.md)

Exploratory response replay and controlled algorithm experiments. **Zero fresh Jev calls.** No production-policy change. H1-H3 miss their frozen primary targets; H4-H5 meet controlled exactness/capacity targets, not semantic-accuracy targets.

```bash
python -m pip install -r graph_synthesis/requirements-figures.txt
python -B -m graph_synthesis.structural.run --check
python -B -m unittest discover -s graph_synthesis/structural/tests -v
python -B -m graph_synthesis.structural.report --figures --update-paper
python -B -m graph_synthesis.render_current_paper --output manuscript/paper-current.pdf
python -B -m graph_synthesis.verify --output /tmp/original-inventory.json
```

Omit `--check` to regenerate results. Figure/Markdown generation is deterministic with the pinned dependencies. PDF bytes may vary with renderer/fonts; `paper-current.build.json` records the actual artifact hashes. Source fitting and gold-free policy execution are separate interfaces. Every operational failure remains in the captured evidence.

## Concurrent integration

PR #17 completed in parallel from the same PR #16 baseline. Its exact-lineage and cycle-cutset mechanisms overlap with H4/H5 here. This extension adds the specified larger lineage-capacity evaluation and separate cyclic fixtures; it does not claim those mechanisms are newly introduced relative to PR #17. Both studies remain separate exploratory evidence, not independent semantic samples. The shared manuscript preserves both sections.
