# C2P2 RS0 Execution Adapter and One-Run Harness Contract v0.1

## Court-record identity

- programme: `OVC-C2P2-RS0-SHADOW-EVIDENCE-v0.1`
- packet: `C2P2-RS0-EXECUTION-ADAPTER-CLOSEOUT`
- governing gate authority: `C2P2-RS0-GRUN = PASS`
- authority delta: `NONE`
- runtime role: `DISCOVERY_SHADOW_ONLY`
- execution token: exactly one approved A/B/C comparative run; this closeout MUST NOT consume it.

## Purpose

Materialise the deterministic read-only execution surface that was absent at the
post-GRUN preflight. The surface may validate and read an already-materialised
source corpus, execute the frozen A/B/C comparison kernel, checkpoint, seal and
hash a run, and enforce the frozen capacity envelope. It does not fetch market
data, create an upstream C2/C2E corpus, choose a winner, activate C2P, alter EC1,
consume Validation, publish, or create probability/risk/exposure/execution or
agent-write authority.

## Frozen execution bindings

Every launch MUST source-bind to
`C2P2_RS0_GRUN_SOURCE_AUTHORITY_SNAPSHOT_v0_1.json`. The execution-currentness
identity is the exact canonical content of these five frozen sections:

1. `population`
2. `upstream_bindings`
3. `candidate_set`
4. `capacity`
5. `external_artifact_root`

Any change in any of those sections is `RS0_GRUN_CURRENTNESS_MISMATCH` and the
run generation fails closed before token consumption.

The candidate registry MUST remain exactly the three unselected, activation-
ineligible candidates and logical hashes frozen by GRUN. No fourth candidate,
preferred candidate, winner, selected ObjectPack, active ObjectPack or ordering
change is admissible.

## Source locator

The execution adapter accepts only an
`ovc-c2p2-rs0-source-locator/v1` locator whose source bytes are already
materialised beneath the operator-mounted `OVC_EXTERNAL_ARTIFACT_ROOT`.

The locator MUST:

- bind the exact GRUN population, C2 vNext authority, package ID, package
  SHA-256 and authority blob SHA;
- declare `provider_fetch=false`, `provider_intake=false`,
  `legacy_c2_fallback=false`, and `reconstruction=false`;
- declare `materialisation_status=COMPLETE`;
- bind a content-addressed local manifest using a repository-relative safe
  path and SHA-256;
- optionally bind C2E only to the exact GRUN C2E authority and boundary pack;
- never fall back to legacy C2 v2, raw price reconstruction, provider access,
  sampling, reduced precision, or a different population.

A missing local root, manifest, shard or hash mismatch is a hard pre-launch
failure. There is no network/provider fallback in the runtime module.

## Normalised source-fact contract

The materialised source manifest supplies JSONL facts with schema
`ovc-c2p2-rs0-source-fact/v1`. A fact is an identity-evidence transport record,
not a new market semantic assertion. It carries only evidence already resolved
under the frozen upstream authority:

- exact instrument, side and clock;
- causal `first_valid_time` and `evaluation_cutoff`;
- a non-authoritative upstream `source_object_key` used only to carry explicit
  source invalidation/lineage dispositions;
- `structural_role_id` and `geometry_kind_id`;
- exact `geometry_signature`;
- exact `relation_topology_signature`;
- owner-resolved `geometry_compatibility_key`;
- C2 continuity status/segment;
- explicit source references;
- optional declared C2E dependency/availability/compatibility evidence;
- optional explicit `SPLIT`/`MERGE` parent disposition.

If a required identity field cannot be resolved from the frozen upstream
materialisation, the source materialisation MUST fail or omit the fact as
not-evaluable according to its own governed contract. The C2P adapter MUST NOT
infer the missing field from raw price, family labels, C3 semantics, outcomes,
future information or downstream labels.

Raw OHLC/price, family/C3 semantics, OPT-C/OPT-D, Validation, outcomes, future
information, forecast, probability, risk, exposure, trade-signal and execution
fields are forbidden recursively.

## Frozen A/B/C comparative kernel

The deterministic kernel implements only the already-preregistered comparison:

- Candidate A requires exact hard scope and exact geometry signature
  continuity.
- Candidate B requires exact hard scope, stable relation-topology signature and
  owner-resolved geometry compatibility.
- Candidate C requires exact hard scope and owner-resolved geometry
  compatibility; declared episode-relative C2E dependency additionally
  requires available compatible C2E evidence. C2E remains optional otherwise
  and can never be sufficient identity authority.
- source continuity breaks are `CENSORED`, never bridged;
- more than one lawful existing assertion is `AMBIGUOUS`;
- explicit split/merge parent dispositions retire parents and create a new
  assertion;
- confirmation requires three eligible observations;
- provisional assertions do not become dormant; confirmed assertions may
  become dormant and can reappear only when the candidate predicates pass;
- recurrence after retirement creates a new assertion.

The kernel has no scalar score and emits no winner, selection or activation.

## One-run token

`AUTH.C2P2.RS0.ONE_RUN_SHADOW.v0.1` is single-use. A token state may be
constructed and tested synthetically by this packet, but repository authority
state MUST remain unconsumed until a real launch has passed currentness, source,
candidate and capacity preconditions.

A consumed token cannot be consumed again. A second run or new generation
requires a new operator GRUN decision.

## Checkpoint, sealing and capacity

Checkpoint identity binds run ID, next cutoff, source manifest SHA-256,
currentness SHA-256 and all three candidate decision hashes. Recompute-from-
outputs is forbidden.

The final comparative receipt MUST contain all three candidates in A/B/C order
and MUST preserve `winner=null`, `selection=null`, `activation=null`,
`validation=LOCKED_UNCONSUMED`, and `ec1_scientific_effect=NONE`.

Frozen hard limits:

- peak memory: `1,160,593,408` bytes;
- external storage: `6,411,935,744` bytes;
- concurrency: exactly `1`;
- checkpoint cadence: `256` assertions.

Capacity excess fails closed. Sampling, reduced precision, population mutation,
predicate weakening and ObjectPack change remain forbidden.

## Current closeout boundary

This contract and implementation can close the missing adapter/harness defect
without consuming real evidence. It cannot itself create the absent
2021-2023 C2 vNext source corpus. If no exact materialised locator exists after
this packet, the programme MUST stop at a separately governed upstream-source
materialisation boundary rather than reconstructing from legacy C2 or raw
market data.

## Rollback

Forward-supersede the adapter/harness packet. Preserve GRUN, candidate science,
capacity evidence, the one-run token and all negative evidence. No deletion,
force-push or history rewrite.
