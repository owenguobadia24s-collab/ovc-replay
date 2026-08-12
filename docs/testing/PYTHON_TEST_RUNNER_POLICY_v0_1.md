# OVC Python test runner migration policy v0.1

## Decision

OVC is adopting **pytest** as the eventual unified Python test runner. Existing `unittest.TestCase` tests remain first-class tests and are not rewritten, deleted, or weakened merely to complete the runner migration.

Authority effect: **NONE**. This is development-assurance infrastructure only.

## Migration phases

### PYT-WP1 / PYT-G1 — dual-run parity proof

CI must run, on the same exact commit:

1. the existing standalone command `PYTHONPATH=src python3 -m unittest discover -s tests -v`;
2. the candidate unified runner `python3 -m pytest -v`; and
3. `python3 tools/ci/check_pytest_unittest_parity.py`.

`PYT-G1` may pass only when both complete test commands pass and the parity checker proves that every test discovered by legacy unittest discovery is also collected by pytest. Pytest may lawfully collect additional native pytest tests.

### PYT-WP2 / PYT-G2 — unified-runner cutover

The standalone unittest CI command may be removed only after a merged-main `PYT-G1 PASS` receipt identifies the exact parity-proved main commit and successful workflow run. The underlying unittest tests remain unchanged and continue to run through pytest's unittest compatibility support.

The cutover packet must preserve a rollback to dual-run CI. If pytest omits, changes, or cannot execute a preserved unittest test, `PYT-G2` is blocked and the standalone unittest command remains.

## Reproduction

Install the repository test extra and run pytest:

```text
python -m pip install -e ".[test]"
python -m pytest -v
```

During PYT-WP1, also run:

```text
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 tools/ci/check_pytest_unittest_parity.py
```

## Non-goals

This migration does not change market/scientific semantics, selectors, authority, fixtures, test assertions, Validation access, publication, or exposure behaviour. It does not convert unittest source files to pytest style unless a later bounded maintenance packet has an independent reason to do so.
