# PD-G4 Operator Decision

- Gate: `PD-G4`
- Plan: `OVC C2 Pattern Discovery and Review Layer v0.3`
- Packet: `PD-WP4`
- Baseline main: `b0798b5535f5fb0276a2b524956c801e278b96d4`
- Candidate implementation commit: `0062b5e212225211c03fd372fc17e3225a2818c2`
- Gate-ready branch: `build/pd-wp4-simple-ui-evidence-bridge`
- Operator command: `OVC APPROVE PD-G4`
- Decision: `PASS`
- Decision authority: `OPERATOR`
- Approved on: `2026-07-27`

## Accepted implementation

The operator accepts the bounded local Pattern Discovery review surface and governed C2 prospective-evidence bridge implemented by PD-WP4.

Accepted capabilities:

- local Queue, Candidate Detail and Clusters views;
- typed review projections and visible immutable source lineage;
- exact OPT-A-bound lightweight price-strip context;
- automatic candidate, fingerprint, release and source-record resolution;
- the five existing C2 prospective-evidence record classes;
- local-loopback AppendRequest processing;
- operator identity and Ed25519 signing boundary;
- session token, explicit freeze confirmation, nonce and sequence controls;
- cutoff and LIVE_PROSPECTIVE admissibility validation;
- idempotent requests;
- atomic evidence-plus-audit transaction envelopes;
- append-only canonical evidence and audit records when the approved bridge is lawfully configured.

## Authority granted

PD-G4 grants bounded human-operated canonical prospective-evidence append authority through the governed bridge. It does not grant manual ledger editing, manual canonical source-ID entry or automatic evidence creation.

The bridge remains subject to:

- a registered human operator signing identity stored outside Git;
- local-loopback operation;
- explicit freeze confirmation for each append;
- exact immutable source resolution;
- accepted C2 record classes only;
- LIVE_PROSPECTIVE operation only for canonical prospective evidence;
- append-only audit and correction-by-supersession behaviour.

## Authority not granted

This decision does not grant:

- live autonomous Pattern Discovery processing;
- active novelty-ranking weight;
- semantic cluster naming or archetype promotion;
- C2 mutation, C2E, C2.5, C3, OPT-C or OPT-D authority;
- Validation consumption;
- selector, release or R2 mutation;
- probability, risk, exposure, trading or execution authority;
- agent proposal or write authority.

## Tests and QA

- PD-WP4 focused workflow `30266028660`: PASS
- Repository-wide canonical workflow `30266028698`: PASS
- QA recommendation: `PASS_PD_G4_CANDIDATE_OPERATOR_REQUIRED`
- Blocking defects: none

## Rollback

Disable canonical bridge writes by setting `write_authority=false`, remove the Pattern Discovery route from normal operation and preserve all already committed append-only evidence and audit records. No rollback may rewrite or delete canonical evidence history.

## Continuation

PD-WP4 is approved for squash integration into `main`.

The next packet is `PD-WP5`, but it may start only when `REAL_PROSPECTIVE_SOURCE_AVAILABLE` is satisfied. PD-WP5 remains the first prospective discovery-batch operation and does not itself grant C2E or semantic-promotion authority.
