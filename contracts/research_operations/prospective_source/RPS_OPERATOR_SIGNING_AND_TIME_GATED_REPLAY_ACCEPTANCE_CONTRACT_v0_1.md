# RPS Operator Signing and TIME_GATED_REPLAY Acceptance Contract v0.1

## Authority

This contract implements `RPS-WP4` after delegated `RPS-G3` acceptance of:

- source slice `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1`;
- compute run `RPS.RUN.7aeb551335d766ee3bf503e6`;
- source-binding candidate `RPS.BINDING.32fb3003efa072916c11e907`;
- output-manifest SHA-256 `3c6295badd04896a9e94b4b5a3ccb354bb51de52d5927839a86f61a40ed679ff`.

RPS-WP4 is deterministic, operator-local, replay-only and non-activating. It may register an operator signing-binding candidate and produce a signed `TIME_GATED_REPLAY` acceptance candidate. It may not activate research triage, enable LIVE_PROSPECTIVE append, grant canonical write authority or mutate any release or selector.

## Exact compute verification

Before any key or replay-acceptance action, the command must verify:

1. the repository RPS-G3 compact evidence index and approved state;
2. all five compact compute files by byte size and SHA-256;
3. the output-manifest canonical logical SHA-256;
4. every one of the 21 manifest-declared derived payload files by path, size and SHA-256;
5. total payload bytes of `5,557,327`;
6. exact run, binding, source, code-commit, operation-mode and admissible-cutoff identities;
7. `PASS_GAPPED_EXCLUSION` coverage QA;
8. retained non-release and non-activating authority states.

No manifest-only acceptance is allowed at this stage. The operator-local command must re-read every declared derived payload byte.

## Operator identity

The operator identity is explicit and portable:

`OVC.OPERATOR.<UPPERCASE_ID>.V<NUMBER>`

The identity is not inferred from a Windows account name, repository owner, email address or machine path.

## Ed25519 signing profile

The accepted signing profile is:

- algorithm: `ED25519`;
- implementation: operating-system OpenSSH `ssh-keygen`;
- signature envelope: OpenSSH SSHSIG v1;
- namespace: `ovc-rps`;
- private key: external-artifact root only;
- public key and fingerprint: permitted in compact evidence;
- raw private-key material: prohibited in Git, compact receipts, Streamlit, logs and chat uploads.

Key generation is denied in CI. Existing key files are never overwritten. The generated private key is created without an application-managed passphrase, so the operator must apply restrictive operating-system file permissions and explicitly confirm protection before replay acceptance may proceed.

The operator confirmation is an attestation to an external operating-system action; the command does not claim that repository code can prove Windows ACL correctness on every supported host.

## Signing binding

The operator-signing binding records:

- deterministic `RPS.SIGNING.*` identity;
- operator ID;
- Ed25519 public key and SHA-256 fingerprint;
- signature format and namespace;
- exact compute-run and source-binding IDs;
- portable private-key alias, never a machine path;
- private-key protection confirmation;
- `REGISTERED_REPLAY_ONLY_CANDIDATE` status;
- ACTIVE_RESEARCH_TRIAGE false;
- write authority false.

It is not an active writer registration and does not alter the Pattern Discovery evidence bridge authority.

## TIME_GATED_REPLAY acceptance

The signed replay-acceptance payload binds:

- plan and delegated RPS-G3 authority;
- operator and signing-binding identities;
- exact source slice and source-manifest hash;
- exact compute run, binding and output-manifest hash;
- compute code commit and RPS-G3 merge;
- operator execution commit;
- admissible cutoff and eligible-data-through time;
- GAPPED coverage and complete lineage;
- 21 payload files and `5,557,327` payload bytes;
- retained denials.

The acceptance is only `ACCEPTED_FOR_TIME_GATED_REPLAY_ONLY`. Its repository-facing status remains `SIGNED_REPLAY_ACCEPTANCE_CANDIDATE` until compact evidence is reviewed.

## Retained authority denials

All RPS-WP4 outputs must retain:

- release status `NOT_A_RELEASE`;
- selector eligibility `NONE`;
- R2 publication `DENIED`;
- Validation consumption `DENIED`;
- LIVE_PROSPECTIVE append `DENIED`;
- ACTIVE_RESEARCH_TRIAGE false;
- write authority false;
- probability, risk, exposure, trading, execution and agent-write authority `NONE`.

The signed acceptance cannot be used as evidence of active prospective operation.

## RPS-G4 boundary

RPS-WP4 must produce one compact RPS-G4 input identifying the proposed reserved delta:

`ACTIVATE_EXACT_BINDING_FOR_ACTIVE_RESEARCH_TRIAGE_AND_ENABLE_PD_WP5_FIRST_LIVE_PROSPECTIVE_OPERATION`

RPS-G4 requires explicit operator approval. The assistant may prepare the gate packet and recommendation but may not activate the binding, start ACTIVE_RESEARCH_TRIAGE, enable LIVE_PROSPECTIVE append or begin PD-WP5 before approval.

## Storage

Private and public key files, signatures and replay-acceptance artifacts remain under `OVC_EXTERNAL_ARTIFACT_ROOT`. The repository stores implementation, contracts, schemas, tests, QA and compact evidence only.

The four compact files permitted for RPS-G4 review are:

- `operator-signing-binding.json`;
- `time-gated-replay-acceptance.json`;
- `signature-verification-receipt.json`;
- `rps-g4-operator-gate-input.json`.

The private key and raw 21-file derived payload set must not be uploaded.

## Failure and rollback

Any source, compute, payload-byte, key, signature, verification, identity, authority or output failure blocks completion and moves only the new RPS-WP4 staging directory to a separate local quarantine.

Rollback disables or reverts the RPS-WP4 command and acceptance records while preserving the external key pair, accepted source, compute run, signed candidate, rejected attempts and quarantines. Automation is not authorised to delete private keys, rewrite signed evidence or mutate prior external artifacts.
