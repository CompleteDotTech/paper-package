# Cross-platform review correction

PR #16 validation found that existing adaptive/follow-up paper writers use platform-default newlines: LF input becomes CRLF on Windows. The compatibility test had incorrectly required byte identity from these unchanged legacy writers and left its mutated files for the next test.

The legacy-composition test now compares exact UTF-8 content after universal-newline decoding and restores original bytes in a finally block. The new writer still has strict SHA-256 byte-idempotency assertions, with cleanup even on failure. This avoids expensive multi-hundred-kilobyte unittest diffs and cross-test pollution. CI continues to verify every new artifact hash, original inventory hash and committed paper hash; no tolerance was added to numerical replay and no scientific target, implementation, source response, prediction or figure changed.

Separately, the existing multicall full-rebuild workflow now runs the risk-control report updater after the adaptive updater, before its unchanged-content checks. This restores all committed additive sections rather than deleting the new section.
