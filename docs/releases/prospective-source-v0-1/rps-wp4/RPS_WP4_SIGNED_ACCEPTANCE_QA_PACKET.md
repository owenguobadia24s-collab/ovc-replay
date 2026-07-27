# RPS-WP4 — Signed Acceptance Evidence QA Packet

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1` v0.1
- Packet: `RPS-WP4`
- Gate: `RPS-G4`
- Baseline main: `32d878f651d7edc832d75bccf839df41f14201e4`
- Candidate branch: `gate/rps-g4-active-research-triage`
- QA recommendation: `PASS_OPERATOR_GATE_READY_CANDIDATE`

## Evidence received

The permitted four compact files were received and copied without raw source, derived payload or private-key material:

| File | Bytes | SHA-256 |
|---|---:|---|
| `operator-signing-binding.json` | 1,052 | `db230c4efa5b13c87d740a5b0e9791861209d3cd5ba3e7c9b9263243b0ba0266` |
| `time-gated-replay-acceptance.json` | 2,381 | `773840f308d4ca04c1810e891172a02806bf6df3d4be57eb44c8d629e4129e02` |
| `signature-verification-receipt.json` | 1,043 | `719412220fed45f894f3c2e74d4b176776261b2bf2eeafacc5d35bfa0e042436` |
| `rps-g4-operator-gate-input.json` | 1,405 | `2145d4b64a19f346ad51b57ac0ae7392d280b891520d6dbc74412d81f7dc4c08` |

## Identity verification

The following deterministic identities reproduce exactly:

- operator: `OVC.OPERATOR.PRIMARY.LOCAL.V1`;
- signing binding: `RPS.SIGNING.50092c28981fef08f53a6cb5`;
- replay acceptance: `RPS.REPLAY-ACCEPT.0844eddf74e144ced487cc48`;
- source slice: `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1`;
- compute run: `RPS.RUN.7aeb551335d766ee3bf503e6`;
- source binding: `RPS.BINDING.32fb3003efa072916c11e907`;
- source-manifest SHA-256: `429b7b568b7a43d04893c1873773f0b1b567730f2d5d4122d6a1c06dd40e3e41`;
- output-manifest SHA-256: `3c6295badd04896a9e94b4b5a3ccb354bb51de52d5927839a86f61a40ed679ff`;
- operator execution commit: `32d878f651d7edc832d75bccf839df41f14201e4`.

The replay acceptance records 21 payload files totalling 5,557,327 bytes, GAPPED coverage, complete lineage, admissible cutoff `2026-06-25T00:00:00Z` and `TIME_GATED_REPLAY` operation.

## Signing verification

The following controls close:

1. the public key is Ed25519;
2. the OpenSSH public-key fingerprint reproduces to `SHA256:mCaINWRJxmHTChbwy366euz8AMLVFVKQNPiRqYP88kY`;
3. the public-key file SHA-256 reproduces to `6eff88a0500da9f479889e7a1d4d786e53e545079aa60f4ecd0c3d362a675e43`;
4. the signed canonical payload SHA-256 reproduces to `acd3c5653678780523b969d201bb08382f02a081c3fb814386f4fab7a9e6ca82`;
5. the SSHSIG envelope SHA-256 reproduces to `9383c582814809fc0a0408aec1674307e2771b51cad472c06fb86efc3e0c93b8`;
6. the signature declares namespace `ovc-rps`, format `SSHSIG_OPENSSH_V1` and algorithm `ED25519`;
7. independent OpenSSH verification is included in the focused repository test and must pass on final CI.

The private key is not present in Git or the compact evidence. Protection of the external private key is an explicit operator attestation; repository QA cannot independently prove the Windows ACL state.

## Authority closure

Before RPS-G4 approval, every compact record remains non-activating:

- active binding: `null`;
- ACTIVE_RESEARCH_TRIAGE: false;
- LIVE_PROSPECTIVE append: `DENIED`;
- write authority: false;
- release status: `NOT_A_RELEASE`;
- selector eligibility: `NONE`;
- R2 publication: `DENIED`;
- Validation consumption: `DENIED`;
- probability, exposure, trading, execution and agent-write authority: `NONE`.

The signed acceptance is evidence only of `ACCEPTED_FOR_TIME_GATED_REPLAY_ONLY`. It is not evidence that a live prospective batch has occurred.

## Interaction with PD-G4

PD-G4 already approved bounded human-operated canonical prospective-evidence append through the governed local bridge, but only for LIVE_PROSPECTIVE records with exact immutable source resolution and explicit operator action. RPS-G4 is still required to make the exact source binding available to ACTIVE_RESEARCH_TRIAGE and thereby satisfy the remaining prerequisite for PD-WP5.

Approval must not grant automatic evidence creation, live autonomous processing, active novelty ranking, semantic promotion, selector/release/R2 mutation, Validation use, probability, risk, exposure, trading, execution or agent write.

## Warnings

1. The accepted source and compute evidence are GAPPED and end at `2026-06-25T00:00:00Z`; gaps remain excluded with no synthesis.
2. Approval must not relabel TIME_GATED_REPLAY outputs as LIVE_PROSPECTIVE evidence or backfill them into the canonical prospective ledger.
3. The first PD-WP5 operation must use the exact activated binding and apply LIVE_PROSPECTIVE admissibility at operation time.
4. The private-key protection statement remains an operator attestation rather than a repository-verifiable ACL proof.
5. No active novelty-ranking weight or semantic interpretation is authorised.

## Blocking issues

None in the compact evidence. Final CI remains required before the gate-ready packet is frozen.

## Rollback

Revert the RPS-G4 gate-preparation branch and preserve the accepted source, compute run, external Ed25519 key pair, signed acceptance, compact evidence and all quarantines. Do not delete or rewrite the key, signature or prior append-only evidence.

## Recommendation

`PASS`, subject to final focused and repository-wide CI and explicit operator acceptance of the exact active-triage delta stated in the consolidated RPS-G4 gate packet.
