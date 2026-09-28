# Local research validation

Use Python 3.12 and an isolated environment. Start with the
[graph reproduction guide](../graph_synthesis/README.md#run) for pinned dependency
installation, dataset acquisition, and portable replay. The original archive
instructions describe a closed historical package; expanded checkouts use
`python -B -m graph_synthesis.verify`.

## Common checks

```sh
python -B -m graph_synthesis.verify
python -B scripts/download_datasets.py --check
python -B -m graph_synthesis.verify --replay --tests --output ../original-verification.json
python -B -m unittest discover -s graph_synthesis/tests -v
```

Acquire missing datasets using the current reproduction guide before the second
and third commands. The portable replay blocks network access and reads recorded
responses. Keep output reports outside the repository and retain the command,
environment, commit SHA, and resulting verification report.

## Study map

Run each command from the repository root after installing the pinned requirements
listed in that study's source or report. The historical workflow configurations at
[the audited baseline](https://github.com/CompleteDotTech/paper-package/tree/ad4a103a2f6072b892823dc581098d5b9650c057/.github/workflows)
preserve exact dependency-installation, protocol-ancestry, report-generation,
comparison, and artifact commands for every study.

| Study / workflow | Local verification entry point |
| --- | --- |
| Graph synthesis research | Common checks above; `python -B -m graph_synthesis.study --output ../graph-study.json` |
| Graph evidence figures | `python -B -m graph_synthesis.visualize_evidence --check` |
| Visual assessment | `python -B -m graph_synthesis.visualize --check`; `python -B -m graph_synthesis.render_paper --output ../graph-assessment.pdf` |
| Graph synthesis falsification | `python -B -m graph_synthesis.falsification --check`; `python -B -m graph_synthesis.semantic_challenge --export ../challenge-inputs.jsonl` |
| Relationship experiments | `python -B experiments/relationships/reproduce.py --output ../relationship-results` |
| Jev theory suite | `python -B -m graph_synthesis.theory_suite.run --check` |
| Jev additional-call study | `python -B -m graph_synthesis.analyze_multicall --directory experiments/jev-multicall-20260918 --verify` |
| Adaptive improvement experiments | `python -B -m graph_synthesis.adaptive.run --check` |
| Five improvement follow-up | `python -B -m graph_synthesis.followup.run --check` |
| Risk-controlled improvement experiments | `python -B -m graph_synthesis.risk_control.run --check` |
| Structural refinement experiments | `python -B -m graph_synthesis.structural.run --check` |
| Source-aware structural experiments | `python -B -m graph_synthesis.source_structural.run --check` |
| Reliability and structural experiments | `python -B -m graph_synthesis.reliability.run --check` |
| Assumption-aware graph synthesis | `python -B -m graph_synthesis.assumption_aware.run --check`; `python -B -m graph_synthesis.assumption_aware.verify_artifacts` |
| Structural frontier research | `python -B -m graph_synthesis.frontier.run --check`; `python -B -m graph_synthesis.frontier.verify` |
| New graph-synthesis mechanisms | `python -B -m graph_synthesis.novel_mechanisms.run --check` |
| Uncertainty and grounding experiments | `python -B -m graph_synthesis.uncertainty.run --check` |
| Dependence-aware graph certificates | `python -B -m graph_synthesis.certificates.run --check` |
| Post-certificate research | `python -B -m graph_synthesis.post_certificates.run --check` |
| Corpus methodology | `python -B -m unittest discover -s graph_synthesis/corpus/tests -v` |
| DSPy Jev optimizer | `python -B -m graph_synthesis.dspy_jev_optimizer.verify`; `python -B -m unittest discover -s graph_synthesis/dspy_jev_optimizer/tests -v` |

The study directories also contain their focused regression tests. Installing
rendering dependencies and regenerating reports is separate from numerical replay;
use the study's documented commands and compare any regenerated tracked artifacts.
Do not alter original manifests, scientific results, digests, or tolerance
thresholds to make verification pass. These verification entry points do not
authorize new paid model calls.

## Automation status

All 21 research workflows run only through explicit `workflow_dispatch` requests.
Pull requests and pushes do not start research Actions jobs. In the Actions tab,
select a study and choose **Run workflow** on the revision to verify. Existing
replay and report checks run on the selected revision; the six historical
`execute-and-publish` jobs retain their push-only guards and cannot run through
manual dispatch. No write permission or model-call capability is newly enabled.

For example, an authorized manual graph verification can be started with
`gh workflow run graph-synthesis.yml --ref main`. This is optional; all local
verification commands above remain available.

