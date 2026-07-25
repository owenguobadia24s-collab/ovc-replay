# OVC R0 Repository Freeze, Quarantine and v2 Foundation Reset

**Implementation Plan v0.1**  
**Document ID:** `OVC-R0-REPOSITORY-RESET-IMPLEMENTATION-PLAN-0.1`  
**Prepared:** 25 July 2026  
**Status:** `RATIFIED_FOR_R0_EXECUTION`

## Authority notice

This record authorises bounded repository preparation and reset work only. It does not authorise provider download, creation or publication of an OPT-A v2 market-data release, R2 canonical publication, activation of OPT-A, C1 or C2 selectors, construction of C2E, C2.5, C3, OPT-C or OPT-D, market claims, probability, exposure or execution.

## Repository baseline

- Repository: `owenguobadia24s-collab/ovc-replay`
- Local working copy: `C:\Users\Owner\OVIS\ovc-replay`
- Baseline branch: `main`
- Baseline commit: `c0ad7ba22618babdde731e2a338f68f688d4210c`
- Reset branch: `build/v2-foundation-reset`
- R2 evidence bucket: `ovc-evidence`
- Canonical prefix: `canonical/` - indefinitely locked

## Primary decision

Freeze the current repository state as the historical v1 court record, quarantine the old mixed ABCD implementation under one non-importable legacy root, retain the tested evidence-store and immutable historical records, establish a deliberately small active v2 repository template, and install synthetic OPT-A, C1 and C2 fixture foundations before any new provider intake or market replay begins.

R0 is a repository-authority transition. It is not OPT-A WP1, C1 WP1 or C2 WP1. Those programmes begin only after R0 passes.

## Non-negotiable outcomes

- Historical repository baseline: `FROZEN_AND_ADDRESSABLE`
- Old executable ABCD engine: `HISTORICAL_QUARANTINED`
- Historical release records: `RETAINED_IMMUTABLE`
- Evidence-store package: `RETAINED_ACTIVE_INFRASTRUCTURE`
- OPT-A v2 namespace: `SCAFFOLDED_FIXTURE_ONLY`
- C1 v2 namespace: `SCAFFOLDED_FIXTURE_ONLY`
- C2 v2 namespace: `SCAFFOLDED_FIXTURE_ONLY`
- Raw market data in Git: `PROHIBITED`
- New market replay: `NOT_AUTHORISED`
- Selector activation: `NOT_AUTHORISED`
- Legacy rollback target: `PROHIBITED`

## Work packets

1. **R0-1 Baseline preflight and freeze** - verify the exact branch parent, run the pre-reset suite, inventory and hash every tracked file, capture selectors and write the freeze packet.
2. **R0-2 Classification packet** - classify every tracked file as `RETAIN_ACTIVE`, `RETAIN_HISTORICAL`, `MOVE_TO_QUARANTINE`, `REBUILD_V2`, `REMOVE_GENERATED` or `UNRESOLVED`. No moves occur while any row is unresolved.
3. **R0-3 Quarantine migration** - move approved legacy implementation under `legacy/quarantine/abcd-engine-v1-c0ad7ba/`, preserve source crosswalks, deny imports and test discovery, and leave `docs/history/releases/` in place.
4. **R0-4 Active-tree foundation** - create the new OPT-A, C1 and C2 namespaces, authority and implementation registries, storage boundary, and accurate current-status documentation while retaining `ovc_evidence_store`.
5. **R0-5 Synthetic fixture packs** - install compact, hand-verifiable OPT-A, C1 and C2 fixtures only; no discovery or historical market data.
6. **R0-6 Authority guard suite** - prohibit quarantine imports, legacy selectors, old discovery seeds, reverse dependencies and raw market data in Git.
7. **R0-7 Final validation and operator packet** - reconcile inventories and hashes, run the complete post-reset suite, report unresolved issues and present the final authority matrix for operator decision.

## Quarantine authority

```yaml
authority_state: HISTORICAL_QUARANTINED
package_discovery: EXCLUDED
test_discovery: EXCLUDED
selector_eligibility: DENIED
runtime_imports: DENIED
release_parent_eligibility: DENIED
rollback_target: DENIED
```

Historical A-D releases and decisions remain immutable. The old 202 stories, 58 research candidates, old thresholds and B-state outputs may be referenced for audit but may not seed the new discovery line, fixture expectations, parameter selection or promotion criteria.

## Branch and commit discipline

- Work only on `build/v2-foundation-reset`; do not work directly on `main`.
- Test before every repository-bound commit.
- Do not commit raw provider data, generated state streams, caches, logs, credentials or bulky evidence.
- Use bounded commits for the freeze packet, classification packet, quarantine migration, v2 scaffold, fixture packs, and authority tests/final status.
- Never force-push or rewrite history.
- Final merge requires explicit operator review of the exact diff and final R0 packet.

## Authority immediately after R0

```yaml
opt_a_v1: {state: HISTORICAL_SUPERSEDED, active: false}
opt_a_v2: {state: DESIGN_AND_FIXTURES_ONLY, active: false}
opt_b_c1_v2: {state: DESIGN_AND_FIXTURES_ONLY, active: false}
opt_b_c2_v2: {state: DESIGN_AND_FIXTURES_ONLY, active: false}
c2e: {state: DEFERRED}
c2_5: {state: DEFERRED}
c3: {state: DEFERRED}
opt_c: {state: HISTORICAL_QUARANTINED}
opt_d: {state: HISTORICAL_QUARANTINED}
evidence_store: {state: ACTIVE_INFRASTRUCTURE}
```

The complete formatted implementation plan is maintained as the operator-reviewed DOCX artifact for this decision.