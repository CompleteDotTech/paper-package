# Amendment v2: fixed proposal schema and explicit probability interpretation

Fixed before inspecting any new test-panel outcome. Initial attempts remain separately
identified as infrastructure/proposal-format pilots, not successful comparison runs.
No earlier frozen record is overwritten or counted as an independent successful seed.

## Observed failures

The first attempt hit DSPy's reserved `instructions` field before inference. The next
attempt captured real Jev train/validation responses but failed serializing nested
SDK token metadata. That serialization was repaired without changing inference.

In the next pilot, all 15 proposals for the relation evidence-contract formulation
had invalid question counts or criterion structures. Traces show that the 1.5B model
often returned a list of instruction sentences instead of one instruction per
question, or schema-like objects instead of label definitions. Those rejected outputs
must not be called valid optimized prompts or silently repaired after seeing results.

That pilot then encountered calibration response probabilities {NOT_ENOUGH_INFO:0.93,
REFUTES:0.05,SUPPORTS:0.01}, summing to 0.99. The raw journal is preserved. The API
reference specifies unit-sum distributions; decimal rounding is a possible explanation,
not a verified provider guarantee. No calibrated or test result is inferred from this.

## Amended adapter

Keep the same local model, 5 seeds, 3 candidate rounds, task definitions, source splits,
validation metric, calibration algorithms, and test panels. Replace the nested
list/dictionary output request with one **fixed flat signature per atomic question**:
one revised-question string plus one named string field per existing criterion.
The application, not the proposer, supplies label keys and question order. A two-Noul
candidate therefore uses two proposal calls per round; report actual proposal calls
separately from candidate count. Keep all model output traces. This is a new adapter
experiment, not continuation of the failed proposal pool. Restart each search from
the original configuration and do not feed any calibration/test observation to DSPy.

## Probability interpretation

For quantitative probability metrics, proportionally normalize a returned vector only
when all values are finite numbers in [0,1], total mass is positive, and either:

- the sum differs from 1 by at most 1e-6; or
- every value is a two-decimal number (within 1e-9) and the mass defect is at most
  K × 0.005 + 1e-8, the maximum sum error under nearest-hundredth rounding of K values.

This is an explicit measurement assumption applied identically to baseline and DSPy,
not a learned calibrator or an accuracy improvement. It preserves argmax. Count and
list every answer with a mass defect above 1e-6; retain original probabilities in raw
responses. Reject larger defects, missing labels, wrong types, negative or nonfinite
values. Service response failures are fatal, not counted as invalid candidate text.

For the seven multi-call workflows, original raw scores, votes, escalation and
adjudication inputs remain unchanged. Only the separately reported probability
forecasts use normalized component distributions. Thus post-hoc calibration still
cannot improve the decision-frozen policy accuracy by construction.

## Reporting

The completed v2 matrix is the primary comparison; report all pilots, failures and
known call/token overhead separately. No favorable test-based selection of adapter,
seed or calibration method is allowed. Summarize mass defects alongside Brier/NLL
and calibration changes. Results remain retrospective, exploratory, and conditional
on this small proposer and limited search budget. Freeze and source hashes distinguish
v2 from the original protocol and all failed attempts.

Sources: https://docs.typesafe.ai/api ; https://dspy.ai/api/signatures/Signature/
