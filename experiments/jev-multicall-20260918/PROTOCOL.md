# Additional Jev call and information tests — frozen execution protocol

Written before this experiment's live calls. This is an exploratory extension, not externally preregistered research. Earlier SciFact and Jev results have been inspected. The new cases are previously unused within the archived Jev runs, but are public SciFact training data, not a new domain or guaranteed absent from vendor training.

## Data and execution

Use all remaining normalized SciFact training rows after excluding connected source groups represented by the prior demonstrations, development, calibration or evaluation panels. Hash-order groups with seed 20260918: first 40 groups are development; all remaining groups are test. Freeze exact rows, original six training demonstrations, all questions, six synthetic contrast examples, code hashes and this protocol before calls. Keep whole claim/document/duplicate-abstract groups together. No test-label prompt selection. Development is a separate diagnostic; no tuning is planned in this execution.

Model jev-1.13.0, four workers, no retries, at most 3,500 HTTP attempts and 20 million conservatively charged input tokens. All nine calls per case are newly executed; distinct repeat call sites must never collapse identical payloads into one cached call. Resume retains existing sites, including failures. Authentication failures stop execution. Journal complete payloads, raw responses, versions, usage, timestamps, errors and hashes. No gold label, rationale or group metadata enters test requests. A process crash between response and durable append can leave unrecorded billing; this is not a provider invoice.

## Fixed arms

1. **Single:** original explicit relation contract and six original training demonstrations, one Choice call.
2. **Repeat vote:** three fresh identical-payload calls, majority label; all-distinct votes abstain. Any failed call makes the arm fail. Rank accepted edges by the arithmetic mean probability of the winning label, not a claimed calibrated joint probability.
3. **Blind vote:** single-call answer plus two independently executed alternative question formulations. The two reviewers see original evidence but neither another answer nor the original demonstrations. Majority/abstention/failure rules as above. This changes both question and demonstration context; it does not isolate wording alone and does not create independent models.
4. **Targeted:** single call, one six-question request checking entity identity, direction, negation, time, population and causality, then one adjudication call seeing original evidence and fallible checks/candidate. A failed prerequisite makes this arm fail. No probability multiplication. Three HTTP calls but eight typed decisions: report this distinction and tokens.
5. **Structured:** original single-call contract/demos, with every evidence sentence explicitly indexed. No evidence deleted, selected from gold rationale, or added.
6. **Contrastive:** original question with six fixed synthetic boundary examples replacing the original demonstrations. This is an information/example-content and token-budget change, not an isolated wording test.
7. **Selective:** use single unless its raw maximum score is below 0.90 or it fails; then use targeted. Threshold fixed before calls, not fitted. Report as a retrospective routing policy using authentic newly executed branch outputs; the experiment actually runs all branches. Score 0.90 is not a safety guarantee.

Do not introduce extra retrieved evidence in this experiment; parsing/formatting cannot create missing facts. No ground-truth changes based on observed mistakes.

## Endpoints and inference

Primary exploratory comparison: wrong typed SUPPORTS/REFUTES edges at matched accepted-edge volume, with correct-edge recall and operational macro-F1. Evaluate both unchanged operating points and a common K equal to the smallest accepted count across compared arms. Rank by each arm's declared score, then ID. Report that matching volume is an evaluation diagnostic, not a fitted deployment threshold. Invalid responses, missing outputs and abstentions remain in classification denominators. Wrong polarity counts as a false accepted edge and a missed gold edge. NOT_ENOUGH_INFO is a valid classification but no materialized positive edge.

Use 2,000 paired source-group bootstrap draws (seed 20260918), including all rows in resampled groups. Compare each arm to single; intervals are pointwise, unadjusted and exploratory, conditional on frozen prompts and observed groups. For matched-volume intervals freeze selected ID sets before resampling; do not silently re-rank each draw. Report undefined precision when no edge is accepted. The small panel cannot qualify low production error rates.

Report shared errors and wrong-label agreements for repeated and alternative judgments, conditional accuracy, precision, recall, F1, confusion, status counts, actual whole-study calls/tokens, per-arm required calls/tokens (shared calls counted in each hypothetical policy), latency and token-normalized utility. Distinguish observed execution cost from counterfactual selective routing cost. Equal call counts do not imply equal tokens or latency. Retain unfavorable and null outcomes. Do not infer an advantage from a precision improvement accompanied by lost recall alone.

## Deliverables

Raw and derived JSON, CSV outcome tables, paired intervals, precision/recall and error-yield charts, cost comparison, error-overlap heatmap, illustrative evidence graph selected by ID rather than visual attractiveness, report and updated current manuscript/PDF. Reproduction uses only journals and makes no model calls. Synthetic compiler guarantees and original findings remain separate. Merge after tests, immutable-evidence verification and live CI; no production policy is promoted by this experiment.
