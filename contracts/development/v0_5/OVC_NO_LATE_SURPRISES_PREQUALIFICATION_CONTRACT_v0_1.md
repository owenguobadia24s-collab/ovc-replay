# OVC No-Late-Surprises Prequalification Contract v0.1

Status: ACTIVE CONFORMANCE HARDENING

## Purpose

This contract inserts one deterministic prequalification boundary between packet construction and detached exact-head qualification. It does not create new scientific, market, trading, execution or physical-main write authority.

## Core invariant

If a property can be decided without knowing the eventual physical `main`, it MUST be proven before detached qualification is published and MUST NOT be rediscovered as a placement decision later.

The forward VIT route therefore separates:

1. stable logical state: PIP identity, programme/packet identity, authority manifest identity, dependency frontier identity and logical changes;
2. exact-head qualification state: candidate head SHA/tree and detached qualification identity; and
3. ephemeral placement state: current `main`, prospective integration tree, physical predecessor/lease and serialized materialisation state.

Class 3 MUST NOT contaminate classes 1 or 2.

## Prequalification compiler

The canonical prequalification compiler is `tools/ci/vit_no_late_surprises.py`.

For forward late-binding lineage it MUST fail closed unless all of the following hold:

- lineage validates as payload-only `LATE_PHYSICAL_PLACEMENT`;
- every PIP ADD/MODIFY path resolves to the declared exact-head blob and mode;
- every PIP DELETE path is absent from the exact head;
- the PIP does not embed physical-main, predecessor, placement, ordinal or queue-position identity; and
- changed Python tests under `tests/shared_systems/**` use only the Python standard library, repository-local modules and the declared pytest harness dependency.

The compiler emits a deterministic content-addressed PASS receipt. Its identity MUST be invariant under unrelated movement of physical `main` for the same exact candidate head and PIP.

## Enforcement points

`tools/ci/build_vit_pr_lineage.py` MUST execute the compiler before forward detached qualification publication.

`tools/ci/vit_assurance_preflight.py` MUST execute the same compiler at required-assurance entry for late-binding candidates. This is verification of the construction-time contract, not a second independent interpretation of packet semantics.

Historical placement-bearing lineage remains replayable for migration/recovery and is not retroactively rewritten by this contract.

## Shared Systems dependency closure

Shared Systems conformance tests are intentionally dependency-light. A third-party import not present in the authoritative required-test environment MUST fail during prequalification rather than after repository-wide CI fan-out. Adding a new third-party dependency requires an explicit dependency-policy change; local environment availability is not evidence of declaration.

## Placement and queue law

Current `main`, PR number, creation order and absolute queue position are not logical payload identity and MUST NOT invalidate an otherwise unchanged qualified payload.

Only the final serialized integration lane may bind current physical `main`. Movement of `main` invalidates only ephemeral placement unless payload, dependency frontier or authority has independently changed.

The one-writer physical-main invariant, exact-tree equality, SIQ/GRT fail-closed behavior and all existing authority denials remain unchanged.

## Regression requirements

Conformance MUST include evidence that:

- unrelated `main` movement leaves prequalification identity unchanged;
- a forward PIP containing physical-main identity fails;
- an undeclared Shared Systems import such as `jsonschema` fails before detached qualification;
- standard-library, pytest and repository-local Shared Systems imports pass; and
- a declared PIP blob mismatch against the exact head fails.

## Success condition

After activation, deterministic static packet defects covered by this contract are construction/prequalification failures. They MUST NOT first appear after repository-wide test execution, SIQ READY, GRT admission or physical placement.
