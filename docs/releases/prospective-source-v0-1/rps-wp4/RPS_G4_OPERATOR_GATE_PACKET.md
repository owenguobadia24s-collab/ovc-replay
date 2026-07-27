# RPS-G4 — Active Research Triage and First LIVE_PROSPECTIVE Operation Gate

## Gate identity

- Gate ID: `RPS-G4`
- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1`
- Plan version: `0.1`
- Packet: `RPS-WP4`
- Baseline main: `32d878f651d7edc832d75bccf839df41f14201e4`
- Candidate branch: `gate/rps-g4-active-research-triage`
- Tested evidence commit: `c157397dedd2d2d1cc8f57d91b06bdbac0cf70e8`
- Pull request: `#112`
- Decision authority: `OPERATOR`
- Allowed decisions: `PASS`, `DEFER`, `BLOCK`, `QUARANTINE`, `SUPERSEDE`

## Completed prerequisites

The following programme work is complete:

1. PD-G4 approved the bounded local Pattern Discovery review surface and governed human-operated evidence bridge.
2. RPS-G1A approved the exact June Dukascopy intake scope.
3. RPS-G1B approved checksum-pinned GAPPED-source acceptance.
4. RPS-G2 accepted the exact frozen source evidence with incomplete parents excluded and no synthesis.
5. RPS-G3 accepted deterministic local 15M/2H C1/C2 computation and the non-activating source-binding candidate.
6. RPS-WP4 command readiness passed and merged.
7. The operator created and protected one external Ed25519 key, signed the exact TIME_GATED_REPLAY acceptance and supplied the four permitted compact evidence files.
8. The signature, deterministic identities, original CRLF file hashes, lineage and retained denials were independently validated.
9. Focused and repository-wide CI passed on the tested evidence head.

## Baseline and candidate identities

- Source slice: `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1`
- Source-manifest SHA-256: `429b7b568b7a43d04893c1873773f0b1b567730f2d5d4122d6a1c06dd40e3e41`
- Compute run: `RPS.RUN.7aeb551335d766ee3bf503e6`
- Output-manifest SHA-256: `3c6295badd04896a9e94b4b5a3ccb354bb51de52d5927839a86f61a40ed679ff`
- Source binding: `RPS.BINDING.32fb3003efa072916c11e907`
- Operator: `OVC.OPERATOR.PRIMARY.LOCAL.V1`
- Signing binding: `RPS.SIGNING.50092c28981fef08f53a6cb5`
- Replay acceptance: `RPS.REPLAY-ACCEPT.0844eddf74e144ced487cc48`
- Public-key fingerprint: `SHA256:mCaINWRJxmHTChbwy366euz8AMLVFVKQNPiRqYP88kY`
- Signed-payload SHA-256: `acd3c5653678780523b969d201bb08382f02a081c3fb814386f4fab7a9e6ca82`
- Signature SHA-256: `9383c582814809fc0a0408aec1674307e2771b51cad472c06fb86efc3e0c93b8`

## Current authority

Current repository and runtime authority remains:

- operation mode accepted: `TIME_GATED_REPLAY` only;
- active binding: `null`;
- ACTIVE_RESEARCH_TRIAGE: false;
- LIVE_PROSPECTIVE append: `DENIED` by the RPS binding;
- source-binding write authority: false;
- PD-G4 governed human append bridge: approved but not yet supplied with an active prospective source binding;
- release status: `NOT_A_RELEASE`;
- selector eligibility: `NONE`;
- R2 publication: `DENIED`;
- Validation consumption: `DENIED`;
- active novelty ranking: `NONE`;
- semantic, family, archetype, C2E, C2.5 and C3 promotion: `NONE`;
- probability, risk, exposure, trading, execution and agent-write authority: `NONE`.

## Proposed authority delta

`PASS` would authorise exactly:

1. register `RPS.SIGNING.50092c28981fef08f53a6cb5` as the sole approved local human operator signing binding for this programme stage;
2. set the active prospective source binding to `RPS.BINDING.32fb3003efa072916c11e907`;
3. set `ACTIVE_RESEARCH_TRIAGE` true for the bounded GBP/USD Discovery research line using the existing active C2 model `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1`;
4. satisfy the remaining RPS prerequisite for `PD-WP5`;
5. permit one first bounded `LIVE_PROSPECTIVE` Pattern Discovery operation under PD-WP5;
6. permit explicit human append through the already approved PD-G4 bridge only for the five accepted evidence classes, with automatic immutable source resolution, explicit freeze confirmation, nonce/sequence controls and Ed25519 signing;
7. require the first batch and all produced evidence to stop at `PD-G5` for operator review.

The activation must be implemented through a separate post-approval decision/activation packet. Approval of this gate packet alone does not mutate `main`, start a process or append evidence.

## Authority not granted

`PASS` would not authorise:

- relabelling the June TIME_GATED_REPLAY outputs as LIVE_PROSPECTIVE evidence;
- retrospective backfill into the canonical prospective ledger;
- automatic evidence creation or agent writes;
- live autonomous Pattern Discovery processing beyond the first bounded operator-supervised batch;
- active novelty-ranking weights;
- semantic cluster naming, family/archetype promotion or theory promotion;
- C2 mutation, C2E, C2.5, C3, OPT-C or OPT-D authority;
- a new instrument, market, clock, side, provider or model;
- selector or release mutation;
- canonical or R2 publication;
- Validation consumption;
- probability, risk, exposure, position, trading or execution authority.

## Acceptance conditions

RPS-G4 may pass only if all of the following remain true:

1. all four compact evidence files match their pinned byte sizes and SHA-256 values;
2. deterministic signing-binding and replay-acceptance IDs reproduce;
3. the Ed25519 public-key fingerprint reproduces;
4. OpenSSH verifies the SSHSIG signature over the exact canonical payload under namespace `ovc-rps`;
5. the source, compute, manifest, cutoff and binding identities close exactly;
6. the source remains explicitly `GAPPED`, with incomplete parents excluded and no repair or synthesis;
7. private-key material is absent from Git and compact evidence;
8. the signing-binding remains a single local human operator identity;
9. current state remains non-activating until the operator decision is recorded and merged;
10. focused and repository-wide CI pass on the final gate-ready branch;
11. QA recommends `PASS` and there are no unresolved reviews or blocking warnings;
12. rollback preserves all source, compute, key, signature, evidence and quarantine artifacts.

## Tests and QA

- Focused test: `tests/research_operations/prospective_source/test_rps_g4_signed_replay_evidence.py`
- Focused workflow: `30298056893`
- Focused job: `90083869457` — PASS
- Canonical workflow: `30298056638`
- Canonical job: `90083867686` — PASS
- QA packet: `docs/releases/prospective-source-v0-1/rps-wp4/RPS_WP4_SIGNED_ACCEPTANCE_QA_PACKET.md`
- QA recommendation: `PASS_OPERATOR_GATE_READY`

The focused run verifies byte inventory, deterministic IDs, public-key fingerprint, Ed25519 SSHSIG, cross-record lineage, retained denials and the operator gate stop. It also confirms no private key is committed. The canonical repository suite passed separately.

## Changed files

The bounded gate branch contains only:

- the four compact RPS-WP4 evidence files;
- one compact evidence index;
- one signed-evidence QA packet;
- this consolidated operator gate packet;
- one machine-readable RPS-G4 gate state;
- one focused validation test;
- one focused CI workflow;
- the bounded RPS-WP4 programme-state update.

No market data, derived payload set, private key, cache, ledger or machine-specific path is committed.

## External artifact hashes

- operator signing binding: `db230c4efa5b13c87d740a5b0e9791861209d3cd5ba3e7c9b9263243b0ba0266`
- signed replay acceptance: `773840f308d4ca04c1810e891172a02806bf6df3d4be57eb44c8d629e4129e02`
- signature-verification receipt: `719412220fed45f894f3c2e74d4b176776261b2bf2eeafacc5d35bfa0e042436`
- RPS-G4 gate input: `2145d4b64a19f346ad51b57ac0ae7392d280b891520d6dbc74412d81f7dc4c08`

## Warnings

1. The source evidence ends at `2026-06-25T00:00:00Z` and is GAPPED. It is readiness evidence, not proof that a July live batch has already occurred.
2. The external private-key ACL is supported by operator attestation; repository QA cannot independently prove Windows permission state.
3. Approval must not cause replay contamination. TIME_GATED_REPLAY records remain non-canonical for LIVE_PROSPECTIVE evidence.
4. The first live batch must remain bounded and must stop at PD-G5 before any semantic, novelty or broader research authority is considered.
5. No autonomous or agent-driven write path is permitted.

## Unresolved issues

None blocking. The explicit operator decision is the only remaining gate condition.

## Rollback

Before activation, rollback is a simple revert of the gate-preparation branch while preserving every external artifact.

After an approved activation, rollback must:

1. set `active_research_triage` false;
2. clear the active RPS binding;
3. set LIVE_PROSPECTIVE append availability back to denied for the RPS line;
4. stop PD-WP5 processing;
5. preserve all committed evidence, audit events, rejected requests, signatures, source/compute artifacts and quarantines;
6. never delete or rewrite canonical append-only evidence or the operator private key.

## Recommended decision

`PASS`.

The evidence closes the operator identity, signature, exact source/compute binding and non-activating replay acceptance. The proposed delta is necessary to begin the first bounded human-governed prospective discovery batch, while all selector, release, R2, Validation, semantic, probability, risk, exposure, trading, execution and agent-write prohibitions remain intact.

## Exact work after approval

After `OVC APPROVE RPS-G4`:

1. record the operator PASS decision and exact authority delta;
2. implement a fail-closed activation record for the exact signing and source bindings;
3. update RPS and Pattern Discovery programme state to `ACTIVE_RESEARCH_TRIAGE_APPROVED` and `PD-WP5 READY`;
4. run focused and repository-wide tests;
5. squash-merge the decision/activation packet;
6. begin the one bounded PD-WP5 LIVE_PROSPECTIVE operation;
7. preserve deterministic source, candidate, fingerprint, queue, review and audit lineage;
8. stop at PD-G5 with the first-batch evidence and no semantic or C2E promotion.
