# Frozen follow-up protocol: transactional fault injection

Date: 2026-09-28. Baseline: merged PR #33 at `7a38d854424a1add6912668fc7def1e3bbaac292`.
This protocol must be committed before the new runner, tests, or outcomes. It is a
new study, not a revision of PR #33's frozen H2 fixture population or its failed
63/64 result. No provider or paid model calls are involved.

## Question and causal condition

PR #33 selected one primitive with no affected derived node, so its intended
evaluation-failure control did not inject a failure. An evaluation fault can be
tested only at a derived node in the reverse-dependency closure of a primitive
whose Boolean value actually changes. A primitive with an empty closure is a
valid no-op for derived evaluation and should commit successfully. These two
cases are distinct controls.

## Frozen population and implementation

- Use Python 3.12 and an independent `random.Random(20260929)` stream.
- Construct 64 modular DAGs by calling the already merged
  `graph_synthesis.post_certificate.run.make_modular_dag` once per graph in
  index order. This gives 64 primitives and 256 derived nodes per graph.
- Initialize every primitive from `rng.getrandbits(1)` in numeric order.
- For each graph, execute five accepted transactions. Each draws a module with
  `rng.randrange(8)`, a change count with `rng.randint(1,4)`, then primitives
  via `rng.sample(range(module*8,(module+1)*8), count)`. Toggle each selected
  primitive. Compare the returned values and revision to independent full
  recomputation and the expected revision after every transaction.
- After the five accepted transactions, select the lowest numbered primitive
  with a nonempty reverse-dependency closure. Toggle it and inject failure at
  the lowest numbered derived node in that closure. Require `RuntimeError`,
  unchanged caller-owned values and revision, and no returned partial overlay.
- On each graph, also reject one stale revision (`current-1`) and one malformed
  update targeting derived node 64. Require their specific exceptions and
  unchanged caller-owned state/revision.
- For an unaffected primitive control, use a separate DAG with two primitives
  and one derived node `2 = xor(0)`. Toggle primitive 1 at revision 0; require
  a successful revision-1 transaction, zero derived evaluations, and agreement
  with independent full recomputation. Repeat for 64 initial primitive pairs
  from the same RNG stream; this tests the no-op causal boundary without
  manufacturing a failure.
- Construct eight invalid DAGs with a two-node derived cycle. Require graph
  construction to reject each with `ValueError` before any transaction.
- Reuse the original 16 connected controls from `make_connected_dag`, with
  primitive initialization and transaction specified in PR #33's H2 runner.
  Report their mean saving separately from local modular-DAG savings.

## Predeclared endpoints

The new conjunction passes only if all 320 accepted transactions match full
recomputation and revision, all 64 affected injection controls raise and leave
caller-owned state unchanged, all 64 stale and malformed controls reject with
the expected exception and unchanged state, all 64 unaffected controls commit
with zero derived evaluations and correct values, all eight cycles reject, and
local modular-DAG derived evaluations are at least 80% below 320 full
recomputations of 256 derived nodes each. The connected-control result is a
reported boundary, not part of the 80% denominator.

Retain each control's graph index, primitive, selected fail node, affected
closure size, actual exception class, and pass/fail status. Retain failures in
the denominator. A mutation check must demonstrate that suppressing an expected
injection exception makes the follow-up fail. Publish exact counts, usage-free
work counters, an immutable input/source hash record, and a report that repeats
the original PR #33 H2 failure separately. No semantic accuracy, crash
durability, concurrency isolation, or general performance claim follows.
