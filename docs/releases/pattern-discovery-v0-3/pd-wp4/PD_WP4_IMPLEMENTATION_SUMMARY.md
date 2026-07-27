# PD-WP4 — Simple UI and Governed Evidence-Bridge Candidate

## Status

`GATE_READY_PD_G4_OPERATOR_REQUIRED`

## Baseline

- Plan: `OVC C2 Pattern Discovery and Review Layer v0.3`
- Source SHA-256: `03a4c602026950f3a496f6bf2085c378a62292090d334f3b0ea2f17f6463a0aa`
- Approved prerequisite: `PD-G3 PASS`
- Baseline main commit: `b0798b5535f5fb0276a2b524956c801e278b96d4`
- Branch: `build/pd-wp4-simple-ui-evidence-bridge`

## Implemented candidate capability

- one simple local Streamlit surface with exactly Queue, Candidate Detail and Clusters views;
- compact queue filters and explicit empty states;
- candidate source, trigger, timeline, fingerprint, nearest-cluster and provisional-authority projections;
- lightweight exact-OPT-A price strip that cannot outrun represented C2 time;
- cluster member, medoid, dispersion and outlier view with semantic promotion denied;
- five accepted C2 evidence classes in a disabled review form;
- automatic candidate/fingerprint/source identity resolution with no manual canonical ID entry;
- canonical AppendRequest model;
- local-loopback evidence-service candidate with session token, freeze confirmation, operator/signer binding, nonce, sequence, source/cutoff and exposure-field validation;
- globally idempotent request handling;
- atomic transaction envelope containing evidence plus hash-chained AuditEvent;
- explicit candidate-test mode producing non-canonical artifacts only;
- write authority disabled by default and fail-closed `OPERATOR_GATE_REQUIRED` behaviour.

## Authority boundary

The UI is locally operable for read-only fixture review. The evidence bridge is implemented as a candidate but cannot create canonical evidence unless `write_authority` is separately activated after PD-G4 operator approval and an external Ed25519 operator signer is configured.

No active novelty ranking, semantic/archetype promotion, C2E/C3, selector/release/R2 mutation, Validation, probability, exposure, trading, execution or agent authority is introduced.

## Operator-efficiency position

The fixture workflow supports queue filtering, one-step candidate selection, progressive disclosure and zero manual source-ID entry. Keyboard shortcuts and batch dismissal remain deferred until browser/operator testing demonstrates need. Batch evidence creation is prohibited.

The intended acceptance targets remain:

- dismiss/defer median at or below 45 seconds;
- control classification median at or below 45 seconds;
- full evidence review median at or below 3 minutes;
- manual source-ID entry: zero;
- irrecoverable mis-clicks: zero.

Real operator timing must be captured during the PD-G4 acceptance session before canonical write activation.

## Rollback

Disable or omit the Pattern Discovery UI route and leave evidence-bridge write authority false. Preserve any non-canonical fixture transactions for QA or delete/rebuild them. Canonical C2, evidence, selectors, releases and R2 remain unchanged.
