# Additional graph-synthesis falsification results

Generated from exact archived Jev responses plus explicitly synthetic interventions.
No fresh Jev, LLM, KARMA, or independent-corpus run is represented here.

## Recorded positive-action and component quality

Identity counts only `same`; relationship counts `SUPPORTS` and `REFUTES`.
Components use all candidate endpoints, including unaccepted pairs.

| Task | Arm | Correct / accepted | Wrong | Complete clean / gold-positive components | Contaminated / active components |
|---|---|---:|---:|---:|---:|
| relation_support | generic | 187 / 224 | 37 | 140 / 164 | 37 / 182 |
| relation_support | fewshot | 172 / 192 | 20 | 126 / 164 | 20 / 153 |
| entity_resolution | generic | 350 / 358 | 8 | 350 / 350 | 8 / 358 |
| entity_resolution | fewshot | 349 / 351 | 2 | 349 / 350 | 2 / 351 |

## Shared errors and certainty

- relation_support: 34 shared errors among 336 common-success rows; 31 wrong-label agreements. Independence would predict 7.146 shared errors from the marginal rates. This is descriptive, not a significance test.
  - generic: score exactly 1.0 yields 6 wrong positive actions out of 125 accepted. Identifiers are in results.json.
  - fewshot: score exactly 1.0 yields 5 wrong positive actions out of 73 accepted. Identifiers are in results.json.
  - Paired component-bootstrap intervals (few-shot minus generic): `{"complete_and_clean_fraction": {"lower": -0.13295761078998072, "upper": -0.03703703703703709, "valid_draws": 2000}, "precision": {"lower": 0.027364640935289754, "upper": 0.09688212207614987, "valid_draws": 2000}}`.
- entity_resolution: 2 shared errors among 413 common-success rows; 2 wrong-label agreements. Independence would predict 0.058 shared errors from the marginal rates. This is descriptive, not a significance test.
  - generic: score exactly 1.0 yields 0 wrong positive actions out of 0 accepted. Identifiers are in results.json.
  - fewshot: score exactly 1.0 yields 0 wrong positive actions out of 260 accepted. Identifiers are in results.json.
  - Paired component-bootstrap intervals (few-shot minus generic): `{"complete_and_clean_fraction": {"lower": -0.008746995038616914, "upper": 0.0, "valid_draws": 2000}, "precision": {"lower": 0.005448952973266691, "upper": 0.03087551448495691, "valid_draws": 2000}}`.

## Candidate loss (original gold denominator)

Seeded, nested source-removal masks are shared across arms. Ranges in JSON are intervention percentiles, not confidence intervals.

| Task | Source loss | Generic mean recall | Few-shot mean recall | Surviving-gold oracle ceiling |
|---|---:|---:|---:|---:|
| relation_support | 0% | 89.47% | 82.30% | 100.00% |
| relation_support | 10% | 80.40% | 73.97% | 89.81% |
| relation_support | 25% | 67.30% | 61.91% | 75.02% |
| relation_support | 50% | 45.14% | 41.58% | 50.27% |
| relation_support | 75% | 22.57% | 20.83% | 25.08% |
| entity_resolution | 0% | 100.00% | 99.71% | 100.00% |
| entity_resolution | 10% | 90.01% | 89.75% | 90.01% |
| entity_resolution | 25% | 75.09% | 74.88% | 75.09% |
| entity_resolution | 50% | 50.09% | 49.95% | 50.09% |
| entity_resolution | 75% | 25.16% | 25.09% | 25.16% |

## Mechanism witnesses (NOT Jev measurements)

```json
{
  "classification": "constructed_synthetic_mechanisms_not_Jev_calls",
  "copied_sources": {
    "active_after_explicit_origin_wide_withdrawal": 0,
    "initial_derived_edges": 1,
    "residual_assertions_after_one_copy_withdrawal": 9,
    "source_records": 10,
    "status": "source_records_are_not_independent_corroborations",
    "unique_origins": 1
  },
  "identity_bridges": [
    {
      "false_cross_identity_pairs_after_repair": 0,
      "false_cross_identity_pairs_before_repair": 4,
      "identity_components_after_repair": 2,
      "injected_wrong_edges": 1,
      "records_per_true_cluster": 2
    },
    {
      "false_cross_identity_pairs_after_repair": 0,
      "false_cross_identity_pairs_before_repair": 100,
      "identity_components_after_repair": 2,
      "injected_wrong_edges": 1,
      "records_per_true_cluster": 10
    },
    {
      "false_cross_identity_pairs_after_repair": 0,
      "false_cross_identity_pairs_before_repair": 10000,
      "identity_components_after_repair": 2,
      "injected_wrong_edges": 1,
      "records_per_true_cluster": 100
    }
  ],
  "repair": {
    "all_oracles_matched": true,
    "episode_digest": "1cefae59755a2953977717aaff560fc0da1843ffad5a23e619ceeb426922ec92",
    "episodes": 20,
    "total_assertions": 1600,
    "total_retractions": 782
  },
  "semantics": {
    "overlapping_temporal_opposites_accepted": 2,
    "schema_invalid_assertion_rejected_atomically": true,
    "status": "limitation_witnesses_not_semantic_model_results",
    "temporal_scope": "Exact qualifier equality is enforced; interval overlap is not interpreted.",
    "valid_but_false_assertions_accepted": 1
  }
}
```

## Interpretation

Passing regression tests means these measurements and counterexamples reproduce; it does not mean every stress scenario is safe. Schema validation cannot establish truth. The current runtime compares qualifier dictionaries exactly, not temporal interval overlap. Repair requires explicit dependencies and source-withdrawal policy.

Zero errors require at least 299 independent accepted actions for a 1% error bound or 2995 for 0.1%, at one-sided 95% confidence for one preselected policy. The current results do not qualify a policy.

Prevalence projections in results.json assume unchanged empirical TPR/FPR and are not new domain-shift observations. All bootstrap intervals are exploratory, pointwise, and conditional on observed component independence.

Fresh semantic challenges, full-document extraction, independently adjudicated data, matched-cost structured LLM/NLI/graph-ML baselines and a fidelity-audited KARMA comparison remain necessary. No superiority or autonomous deployment claim follows.
