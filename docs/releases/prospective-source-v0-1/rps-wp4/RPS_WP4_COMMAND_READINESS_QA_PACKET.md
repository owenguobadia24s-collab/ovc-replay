# RPS-WP4 — Operator Signing and Replay-Acceptance Command-Readiness QA

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1` v0.1
- Packet: `RPS-WP4`
- Baseline main: `c8429ebdf8774a876d5a33e495cb313e31c8d034`
- Prerequisite: RPS-G3 PASS and merged
- Candidate branch: `build/rps-wp4-operator-signing-replay-acceptance`
- QA recommendation: `PASS_COMMAND_READY`
- Packet state after merge: `RUNNING_AWAITING_OPERATOR_LOCAL_SIGNING_AND_REPLAY_ACCEPTANCE`

## Implemented

1. Exact repository verification of the approved RPS-G3 evidence state.
2. Operator-local re-verification of all five compact compute files.
3. Full-byte verification of all 21 manifest-declared derived payload files and 5,557,327 bytes.
4. Explicit portable operator identity validation.
5. OpenSSH Ed25519 key generation outside Git with overwrite denial.
6. Mandatory operator confirmation of restrictive OS private-key protection.
7. Deterministic operator signing-binding candidate.
8. Canonical TIME_GATED_REPLAY acceptance payload.
9. OpenSSH SSHSIG signing and local signature verification under namespace `ovc-rps`.
10. Compact signature-verification receipt and RPS-G4 operator-gate input.
11. Staging quarantine on failure.
12. Windows wrapper, contract, four schemas, tests and dedicated CI.

## Test matrix

- exact RPS-G3 run, binding and manifest constants remain pinned;
- operator identity normalises deterministically and rejects email-like identities;
- key setup and acceptance are denied in CI;
- exact `RPS-G3` delegated gate is required;
- replay acceptance requires explicit private-key protection confirmation;
- real OpenSSH Ed25519 SSHSIG sign/verify round trip passes when `ssh-keygen` is available;
- generated output remains non-activating;
- RPS-G4 input requires operator approval;
- focused and canonical repository suites pass;
- private-key material is absent from repository output.

## Authority assessment

The implementation is auto-executable preparation within the ratified RPS plan. It creates no real signing key or replay acceptance in GitHub because the accepted compute run and external key root are unavailable to CI.

The command never activates the source binding. It produces only:

- `REGISTERED_REPLAY_ONLY_CANDIDATE` signing status;
- `SIGNED_REPLAY_ACCEPTANCE_CANDIDATE` replay status;
- `RPS_G4_EVIDENCE_CANDIDATE` gate input.

The following remain denied:

- provider access;
- source or compute mutation;
- release and selector mutation;
- R2 publication;
- Validation consumption;
- LIVE_PROSPECTIVE append;
- ACTIVE_RESEARCH_TRIAGE;
- canonical evidence writes;
- semantic or theory promotion;
- probability, risk, exposure, trading, execution and agent write.

## Security warning

The key-generation command uses OpenSSH with no application-managed passphrase so that it can run deterministically in the operator-local Windows environment. Replay acceptance is blocked until the operator applies restrictive Windows file permissions and explicitly confirms private-key protection. The private key must never be uploaded or committed.

This confirmation does not purport to be a cross-platform proof of ACL state. It is an operator attestation attached to the signed acceptance candidate.

## External-artifact boundary

GitHub cannot access the accepted local compute payloads or create/protect the operator key. Therefore it cannot produce the final signing-binding ID, replay-acceptance ID, public-key fingerprint or RPS-G4 evidence packet.

This is an expected operator-local boundary, not an implementation defect.

## Rollback

Revert the bounded RPS-WP4 command implementation. Preserve the RPS-G3 compute run, source slice and all local keys, signed candidates and quarantines. No automated key deletion, artifact mutation, relabelling or history rewrite is authorised.

## Recommendation

`PASS_COMMAND_READY` — merge the tested non-activating command, then stop for operator-local preflight, key setup, OS protection and signed replay acceptance. Resume with exactly four compact files for the operator-required RPS-G4 decision.
