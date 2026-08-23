# OVC Shared Systems — DSAI Active Consumption Contract v0.1

## Scope

This contract governs only the prospective adoption of `OVC-SHARED-SYSTEMS-v0.1` by `OVC-DSAI-v0.1` under operator gate `SHSI-G-DSAI-ADOPTION-1`.

The only admitted Shared Systems consumption surfaces are:

- `ENVIRONMENT`
- `RUN`
- `ASSURANCE`
- `RECEIPT`
- `CURRENTNESS`

No ESL or DMRP binding is admitted by this contract.

## Authority partition

DSAI remains the owner of DSAI semantics, ORCH authority, security decisions, development authority, and all existing domain predicates. Shared Systems supplies common identity-preserving mechanics only. The active consumption route MUST NOT fabricate, reinterpret, promote, or suppress a DSAI semantic field.

The adoption authority delta is exactly `DSAI_ONLY_SHARED_SYSTEMS_CONSUMER_ADOPTION_AND_CURRENT_BINDING_CUTOVER_SUBJECT_TO_EXACT_FINAL_ASSURANCE`.

This contract grants no Validation, publication, probability, risk, exposure, trading, execution, new source/provider/research-role, governance-owner, direct-main, force-push, or history-rewrite authority.

## Identity preservation

Every consumed record is wrapped as an identity-preserving whole-record envelope. The source record remains byte-logically reconstructible, its canonical logical SHA-256 is retained, and unwrapping MUST reproduce the exact source object. Field remapping and semantic invention are forbidden.

## Prospective activation

`SHSI-DSAI-ADOPT-WP0` may construct and qualify an `ACTIVE_CANDIDATE` route, but MUST NOT change the DSAI current binding. A controlling `ACTIVE_CURRENT` route may exist only after the exact candidate passes mandatory-semantic equivalence, DSAI/Shared Systems security-refusal parity, receipt/currentness behavior, rollback rehearsal, unchanged ESL/DMRP proofs, and exact-final repository/VIT/SIQ/GRT assurance.

The historical `SHSI-WP7` shadow contracts and evidence remain immutable and controlling as historical evidence; they MUST NOT be weakened or rewritten to create the active route.

## Fail closed

Unknown surfaces, non-DSAI consumers, missing operator authority, non-exact release identities, semantic invention, source-identity mismatch, writes through the consumption envelope, or an unqualified `ACTIVE_CURRENT` switch MUST fail closed.

## Rollback

Rollback restores the exact pre-adoption DSAI current-binding reference, disables the active Shared Systems consumption route, preserves all adoption evidence and historical shadow evidence, and requires requalification before any later reactivation.
