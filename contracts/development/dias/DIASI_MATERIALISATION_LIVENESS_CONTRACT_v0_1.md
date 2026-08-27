# DIASI materialisation and liveness contract v0.1

## Scope

This contract defines the shadow-only WP4A boundary. It binds repository-protection revalidation, the DGS materialisation receipt chain, deterministic crash reconstruction, successor release, and exact owner-local replacement candidates for the six CERS/PES liveness functions.

It grants no authority to write physical `main`, transfer the detached qualification ledger, activate replacement triggers, quiesce CERS, disable PES, cut over, or retire any incumbent component.

## Admission invariant

A materialisation admission is accepted only when the exact protection manifest, predecessor commit and tree, current fenced writer generation and token, and prospective A3 result tree all match. Any drift fails closed. A successful WP4A assessment still records `physical_write_authorised=false`.

## Receipt chain

Before any future physical materialisation, the controller must persist a `PreMaterialisationAnchor`. A successful physical write must bind that anchor to the observed commit, observed tree, expected result tree, and A3 equality in a `PhysicalMaterialisationReceipt`. Only an A3-exact receipt can issue a `PacketCompletionReceipt` and deterministic successor-release key.

When the writer crashes after an externally visible merge or the receipt store is unavailable, reconstruction uses only the durable anchor, observed physical main, immutable PIP, and deterministic identity rules. Runtime memory, chat state, CERS state, and PES state are not admissible reconstruction inputs.

## Liveness ownership

Each incumbent function has an inactive replacement candidate in an existing owner:

- programme discovery/admission, persistent sweep/heartbeat/lease reclaim, and packet start/successor dispatch: DSAI VIT owner-local;
- detached qualification-ledger envelope write, exact-head publication, and content-addressed replay: VIT qualification owner-local.

The replacement is not a generic supervisor. Activation and authority transfer remain reserved to `DIASI-G-DGS-CUTOVER-DRAIN`; retirement/removal remains reserved to `DIASI-G-DGS-RETIRE-REMOVE`.

## Failure disposition

Protection drift, physical-main movement, stale or unknown writer identity, generation/fence mismatch, and A3 mismatch block admission. Partial liveness coverage or any attempt to activate the shadow candidate is invalid.
