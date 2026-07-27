# RPS-G4 — Operator Decision

- Gate: `RPS-G4`
- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1`
- Plan version: `0.1`
- Packet: `RPS-WP4`
- Baseline main: `32d878f651d7edc832d75bccf839df41f14201e4`
- Gate-ready head: `d88b5e9a5cfa7fb90a924f7efeadd050881cb010`
- Pull request: `#112`
- Operator command: `OVC APPROVE RPS-G4`
- Decision: `PASS`
- Decision authority: `OPERATOR`
- Approved on: `2026-07-27`

## Accepted evidence

The operator accepts the exact signed RPS-WP4 evidence for:

- operator `OVC.OPERATOR.PRIMARY.LOCAL.V1`;
- signing binding `RPS.SIGNING.50092c28981fef08f53a6cb5`;
- replay acceptance `RPS.REPLAY-ACCEPT.0844eddf74e144ced487cc48`;
- source binding `RPS.BINDING.32fb3003efa072916c11e907`;
- compute run `RPS.RUN.7aeb551335d766ee3bf503e6`;
- source slice `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1`.

The compact byte inventory, deterministic identities, public-key fingerprint, canonical signed-payload hash, OpenSSH SSHSIG verification, source/compute lineage and retained denials passed focused and repository-wide CI.

## Authority granted

This decision authorises a separate fail-closed activation packet to:

1. register the exact signing binding as the sole approved local human operator signing identity for this programme stage;
2. activate the exact source binding for bounded GBP/USD `ACTIVE_RESEARCH_TRIAGE`;
3. satisfy the remaining RPS prerequisite for `PD-WP5`;
4. permit one first operator-supervised `LIVE_PROSPECTIVE` Pattern Discovery operation;
5. permit explicit human evidence append through the already approved PD-G4 bridge for only the five accepted evidence classes, with immutable source resolution, explicit freeze confirmation, nonce/sequence controls and Ed25519 signing;
6. require the first operation to stop at `PD-G5` for operator review.

Approval of this decision record does not itself relabel replay output, start a process or append evidence. Activation must be materialised and tested in a separate bounded packet.

## Authority not granted

This decision does not authorise:

- relabelling or backfilling `TIME_GATED_REPLAY` outputs as `LIVE_PROSPECTIVE` evidence;
- automatic evidence creation or agent writes;
- autonomous live processing beyond the one bounded first operation;
- active novelty ranking;
- semantic, family, archetype or theory promotion;
- C2 mutation, C2E, C2.5, C3, OPT-C or OPT-D;
- a new instrument, market, clock, side, provider or model;
- selector or release mutation;
- canonical or R2 publication;
- Validation consumption;
- probability, risk, exposure, position, trading or execution authority.

## Evidence and QA

- Gate workflow `30298429365`, job `90085107077`: PASS
- Canonical workflow `30298429451`, job `90085107425`: PASS
- QA recommendation: `PASS_OPERATOR_GATE_READY`
- Unresolved review threads: none
- Blocking defects: none

## Warnings accepted

1. The accepted source is `GAPPED` and ends at `2026-06-25T00:00:00Z`.
2. The signed replay acceptance remains evidence only for `TIME_GATED_REPLAY` readiness.
3. The first live operation must apply `LIVE_PROSPECTIVE` admissibility at operation time and must not consume replay outputs as canonical prospective evidence.
4. The external private-key protection remains an operator attestation rather than a repository-verifiable Windows ACL proof.
5. The first operation is bounded and must stop at PD-G5.

## Rollback

Before the first operation, disable triage, clear the active source and signing bindings and restore LIVE_PROSPECTIVE availability to denied. After any append, preserve all canonical evidence, audit events, rejected requests, signatures, source/compute artifacts and quarantines. No rollback may delete or rewrite append-only evidence or the operator private key.

## Continuation

1. Commit and merge this RPS-G4 decision packet.
2. Create a separate activation packet from the new lawful `main` tip.
3. Activate only the exact signing and source bindings.
4. Update RPS and Pattern Discovery programme state to `ACTIVE_RESEARCH_TRIAGE_APPROVED` and `PD-WP5 READY`.
5. Test and squash-merge the activation packet.
6. Begin the one bounded PD-WP5 `LIVE_PROSPECTIVE` operation.
7. Stop at `PD-G5` with the complete first-operation evidence packet.
