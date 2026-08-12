# OVC Python test runner migration policy v0.1

## Decision

OVC is adopting **pytest** as the eventual unified Python test runner. Existing `unittest.TestCase` tests remain first-class tests and are not rewritten, deleted or weakened merely to complete the runner migration.

Authority effect: **NONE**. This is development-assurance infrastructure only.

## PYT-WP1 / PYT-G1 — exact legacy parity proof

CI runs three independent checks on the same pull-request head:

1. the preserved standalone command `PYTHONPATH=src python3 -m unittest discover -s tests -v`;
2. pytest executing the exact source/test population discovered by the legacy unittest loader; and
3. a collection proof that the pytest legacy surface contains exactly the same unittest cases.

The pytest parity surface is intentionally limited to the existing unittest-discovered population. Pytest-native tests that were never part of the legacy runner are not silently admitted into the parity gate; they require explicit later admission under the unified-runner cutover programme.

`PYT-G1` may pass only when all three checks pass with zero missing or unexpected legacy unittest cases.

## PYT-WP2 / PYT-G2 — unified-runner cutover

The standalone unittest CI command may be removed only after a merged-main `PYT-G1 PASS` receipt identifies the exact parity-proved main commit and successful workflow run. PYT-WP2 must separately inventory/admit pytest-native tests and prove the intended unified pytest surface is green before the old standalone command is removed.

The unittest tests themselves remain and continue to execute through pytest's unittest compatibility layer.

## Rollback

Restore the prior standalone unittest-only workflow or the dual-run parity workflow. Never delete or weaken unittest tests as rollback or migration remediation.
