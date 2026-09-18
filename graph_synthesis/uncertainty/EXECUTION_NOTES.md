# Execution and correction record

The remote protocol was committed as `383bab6f559c7f14525ddcef2275f3a816c9caa3` before the first local benchmark run. The first local run exercised all five frozen fixture generators and met all five conditional engineering targets. Its workspace did not contain the full repository or a local protocol copy, so its temporary metadata had a null protocol hash; that output is not the authoritative archived run. The full repository run records the committed protocol hash and is independently replayed in CI.

During unit-test authoring, two tests initially called existing oracle helpers with the wrong signature/return shape (the finite-model oracle accepts two arguments, and the retraction oracle returns a tuple). Those test calls were corrected. No benchmark generator, seed, primary endpoint, threshold, algorithm or unfavorable control was changed in response to observed outcomes.

The numerical LP output is recorded to 12 decimal places for deterministic evidence serialization. Full primary comparisons occur before rounding. Separate rational small-case extrema, finite subset oracles and model-interpretation enumeration remain in the suite. Synthetic fixture counts and repeated snapshot occurrences are not counted as new Jev observations.
