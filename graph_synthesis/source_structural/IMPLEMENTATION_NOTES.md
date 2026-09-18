# Implementation and measurement boundaries

The protocol anchor is `b92009c6c36d87d9f3cbf0c92c2dad9f9615d726`; its contents are unchanged. The run uses the frozen thresholds, grids, fixtures, budgets and development/evaluation populations. Code was implemented and tested after that commit, before recording the final executed artifacts.

The archived group field represents connected claim/document/duplicate-abstract source groups, not necessarily an individual document. H2 charges the frozen setup cost once per such group. Thus the protocol's document-opening motivation is operationalized as a hypothetical group-opening charge. Neither actual document-opening counts nor human review time are measured. This distinction is explicit in the report and is not evidence that review becomes cheaper in practice.

The H3 input/proof limits apply after canonicalization to the new frontier method; validation, duplicate/subsumption processing and fallback evaluation are outside its state-transition cap. H4's work cap covers residual-edge inspections, not every allocation or graph-validation step. H5 counts fact reevaluations and reverse-index touches, not total CPU time; snapshots and independent full recomputation used by the benchmark are validation overhead. These are bounded research interfaces, not hardened database services.

Zero fresh Jev calls are made. Inference functions receive no evaluation gold; development fitting and evaluation reuse remain explicitly separated. Hypothesis failures are not software test failures: H1 and H2 fail their frozen scientific targets, while tests verify that their unfavorable outcomes and all structural controls are faithfully recorded.
