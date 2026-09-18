# Implementation and execution record

The protocol was committed before implementation/execution as `ef8fc308d0a50cd37a6cdd3b7546e050093349c8`, against main `a62a3257645d8e35cd4e45be53bfa9511d27724b`. Seed, populations, comparison methods, budgets and primary endpoints were not retuned after results were observed. These are exploratory extensions informed by published outcomes, not independent preregistration.

The first local execution produced H1=true, H2=false, H3=true, H4=true, H5=true. Subsequent validation tightened malformed atom-ID handling to reject mixed string/nonstring primitive IDs with ValueError before sorting. This does not change any valid-input benchmark output. All 75 new regression tests pass. Complete numerical replay and archived-inventory verification are performed separately; their exact outputs are in the committed logs.

H2 is retained as a negative result even though the modeled optimization objective improves over one comparator. No threshold, detector assumption or cost mapping was chosen using its evaluation outcomes. Controls retain errors under misspecified source metadata, incorrectly prioritized review risks, false high-priority graph assertions, unsupported graph topologies and exhausted state budgets.

`execution.log` is actual execution output. `tests.log` is actual unittest output, including its environment-dependent elapsed time. `replay.log` is the recorded deterministic numerical replay output. `original-inventory.json` is the archived-evidence verifier result. `artifact-manifest.json` binds extension bytes; the current manuscript uses its independent `.build.json` source/renderer/PDF record. The result journal binds the full generating specifications and source/code hashes; it does not claim provider-signed provenance.

No new Jev requests, credentials, network model execution, production graph writes or default compiler changes are made. The renderer uses repository-local image assets only. Python/numpy numeric replay uses the repository's existing explicit float tolerances; SVG/PNG and Markdown regeneration is checked byte-for-byte under pinned rendering dependencies.
