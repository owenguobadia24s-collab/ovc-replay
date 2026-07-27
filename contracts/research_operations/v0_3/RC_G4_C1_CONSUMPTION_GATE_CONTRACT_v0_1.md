# RC-G4 — Research Console C1 Consumption Gate Contract v0.1

Owner: `OPERATOR`

Classification: `OPERATOR_REQUIRED` / `NOT_AUTO_RATIFIABLE`

Prerequisite: merged `RO3-G4` with accepted adapters, complete evidence, and live route disabled.

## Exact proposed authority delta

`LOCAL_READ_ONLY_C1_PRESENTATION`

This permits Research Console v0.3 to consume exact accepted RO3-G4 projections for local read-only C1 fact presentation. It grants no append-only action beyond the already accepted Research Operations v0.1 service and no market, formula, selector, release, threshold, semantic, probability, risk, exposure, trading, execution or agent-write authority.

## Minimum decision packet

- gate ID, plan/version and operator owner;
- exact RO3-G4 merge SHA and candidate branch/head;
- approved projection schema IDs and hashes;
- route/capability registry delta;
- fixture and source-bound presentation evidence;
- no-write, Validation-denial, stale-projection and mixed-panel rejection tests;
- proof that C1 null reasons and C2 transitions cannot co-render in a compact object;
- permanent downstream authority banner evidence;
- warnings and unresolved issues;
- changed files and rollback;
- exact operator decision: PASS, DEFER, BLOCK, QUARANTINE or SUPERSEDE.

## Rollback

Disable the C1 route and return the Research Console to the prior accepted RO2/RC state. Preserve RO3 objects, QA, decisions and upstream authority; do not alter C1, C2, Pattern Discovery, selectors or R2.
