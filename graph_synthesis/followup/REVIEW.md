# Internal review and corrections

This is an AI-assisted internal review, not independent scientific peer review.

The execution protocol was committed before running this suite, while the original/rerun aggregate findings were already known. No target or policy grid was changed after results were observed. All negative primary results remain visible.

Review caught and corrected implementation/presentation issues before final verification: stability-panel recall initially used the accepted subset rather than all 209 gold-positive relation candidates; a synthetic case fingerprint inherited set-order floating-point nondeterminism; and the current-paper renderer did not wrap Markdown images in the figure styling, causing oversized images. Regression tests now enforce full-denominator recall and hash-seed-invariant fingerprints. The current renderer wraps images and removes internal insertion markers; PDF pages were rendered and inspected. A final chart review also caught a JSON-key-order mismatch between the interval bars and their display labels; explicit keyed series and a serialization-order regression test now prevent that mismatch.

The edge-aware routing point result matches all-few-shot aggregate counts, but two labels differ. Its paired correct-edge rate interval includes zero. Reported token savings are replay counterfactuals, not live speedup or billing measurements. The observed 19 wrong relationship edges still prevent an autonomous semantic-safety claim.

The H4 finite oracle directly enumerates time instants rather than invoking the overlap implementation. H5 independently enumerates primitive-event truth assignments, includes randomized finite-oracle tests, duplicate/permutation properties, and a failing corrupted-lineage control. Neither test evaluates Jev's extraction of qualifiers or lineage.

The 161-file original inventory, default GraphStore/compiler and original response journals are unmodified. New methods are opt-in. Current manuscript Markdown/HTML/PDF and entry-point links are updated separately from historical evidence. CI must complete on the final reviewed PR head before merge.

Windows CI found a locale-dependent decoding failure in a new captured-data reader. All new runner/report text reads now specify UTF-8 explicitly, with an AST regression check and Windows integration replay; input bytes and benchmark outcomes are unchanged.
