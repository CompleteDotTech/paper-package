# Executed relationship experiments

Post-hoc frozen-inference analysis; zero fresh Jev calls.

| Arm | Macro-F1 | Correct edges | Incorrect edges | Precision | Recall | Errors | Abstentions |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline_choice | 0.850824 | 187 | 37 | 0.834821 | 0.894737 | 1 | 0 |
| fewshot_contract | 0.852728 | 172 | 20 | 0.895833 | 0.822967 | 2 | 0 |
| mean_pool | 0.853759 | 179 | 27 | 0.868932 | 0.856459 | 3 | 0 |
| agreement_gate | 0.847081 | 171 | 19 | 0.900000 | 0.818182 | 3 | 33 |
| stacked | 0.834220 | 177 | 35 | 0.834906 | 0.846890 | 3 | 0 |

## Matched accepted-edge volume

Intervals are exploratory, conditional on the original selected sets, and unadjusted.

| Left | Right | K | Left correct/incorrect | Right correct/incorrect | Precision delta | Paired 95% interval |
|---|---|---:|---:|---:|---:|---|
| baseline_choice | fewshot_contract | 192 | 171/21 | 172/20 | 0.005208 | [-0.019380, 0.030145] |
| baseline_choice | mean_pool | 206 | 179/27 | 179/27 | 0.000000 | [-0.020644, 0.020409] |
| baseline_choice | agreement_gate | 190 | 169/21 | 171/19 | 0.010526 | [-0.011732, 0.034717] |
| baseline_choice | stacked | 212 | 181/31 | 177/35 | -0.018868 | [-0.053697, 0.017671] |
| fewshot_contract | mean_pool | 192 | 172/20 | 171/21 | -0.005208 | [-0.027071, 0.014936] |
| fewshot_contract | agreement_gate | 190 | 171/19 | 171/19 | 0.000000 | [-0.013890, 0.013683] |
| fewshot_contract | stacked | 192 | 172/20 | 170/22 | -0.010417 | [-0.038927, 0.018921] |
| mean_pool | agreement_gate | 190 | 171/19 | 171/19 | 0.000000 | [-0.019396, 0.019479] |
| mean_pool | stacked | 206 | 179/27 | 176/30 | -0.014563 | [-0.040087, 0.010120] |
| agreement_gate | stacked | 190 | 171/19 | 168/22 | -0.015789 | [-0.046314, 0.014983] |
