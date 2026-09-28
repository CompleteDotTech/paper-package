# Transactional fault-injection follow-up

This is a separate precommitted study. The original PR #33 H2 result remains **failed (63/64)**.

New conjunction: **met**.

| Endpoint | Passed / total |
|---|---:|
| accepted | 320/320 |
| affected injection | 64/64 |
| stale revision | 64/64 |
| malformed update | 64/64 |
| unaffected noop | 64/64 |
| cycle rejection | 8/8 |
| connected boundary | 16/16 |

Local derived evaluations: 8,153 / 81,920 full recomputation evaluations (90.05% reduction).
Connected control mean saving: 0.00%; reported separately.

Affected injections require an actual derived dependency and an exception. Unaffected primitive updates correctly commit without derived evaluation. This measures in-memory behavior only; it does not establish crash durability, concurrency isolation, semantic accuracy, or wall-clock performance.

See [the frozen protocol](PROTOCOL.md) and [all control records](results.json).
