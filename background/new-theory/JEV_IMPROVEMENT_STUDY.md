# Return to the Jev decision-layer gate

The initial research brief places Jev behind a replaceable decision interface, but asks for a measured Jev comparison before advancing the wider compiler architecture. The earlier specialist/compiler work did not answer that gate. This study keeps Jev as the model and tests ways to improve its results.

The [frozen protocol](../typed-probabilistic-graph-compiler/results/jev/PROTOCOL.md) defines four formulations per task, training-only selection of the best alternative, independent probability calibration, held-out evaluation, fresh API repeat tests, and exact cached replay. The [Jev study entry point](../typed-probabilistic-graph-compiler/results/jev/README.md) links code, raw requests/responses, measured usage, and the result report.

The interventions are explicit task instructions, Choice versus Noul formulations, a conditional binary decomposition for three-way support judgments, and six labeled training demonstrations. The model is pinned to `jev-1.13.0`; there is no new model training or replacement specialist in this experiment. Target candidates and evidence remain fixed, while demonstrations deliberately add training information and prompt cost.

The primary comparison is operational macro-F1 on fixed evaluation examples. Incorrectly normalized or missing service responses remain failures. A valid probability vector does not establish correctness, and temperature fitting is evaluated separately from classification accuracy. Original 50/100 fixtures are secondary diagnostics with their historical limitations preserved.

Repeated remote calls and cached replay answer different questions. Three fresh responses over fixed IDs measure observed service stability during this run. Reconstructing saved outputs tests reproducibility of the local pipeline. Neither guarantees future server behavior.

Further compiler, streaming, or schema work should follow the evidence from this decision-layer evaluation rather than substitute for it.

## Completed Jev evaluation

The frozen study is complete. On 413 held-out DBLP–ACM pairs, explicit identity instructions plus six training demonstrations improved Jev macro-F1 from **0.9605 to 0.9859** and reduced false merges from **8 to 2** among 63 different-entity pairs, at the cost of one missed match. The paired macro-F1 interval is above zero on this split. The SciFact relation result remains inconclusive: **0.8508 to 0.8527** macro-F1 with an interval spanning zero.

All 3,644 predictions reconstruct exactly from recorded responses. An isolated replay with HTTP disabled reproduced byte-identical result artifacts; the selected arms also retained labels over three fresh calls on 20 examples per task, though probabilities varied. Independent verification passed. Recorded input usage implies an estimated **$0.20** cost for 3,405 calls.

The [result summary and reproduction commands](../typed-probabilistic-graph-compiler/results/jev/README.md) document these findings and their limits. Keep the entity formulation for independent confirmation; keep the relation baseline until a newly frozen experiment shows a benefit. This result supports improving Jev's task formulation, without establishing broad Jev superiority or requiring a compiler expansion.
