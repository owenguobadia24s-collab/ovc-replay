# OVC LSIAC GEN0002 Post-Pass2 Register Materialisation Contract v0.1

**Contract ID:** `OVC-LSIAC-GEN0002-POST-PASS2-REGISTER-MATERIALISATION-CONTRACT-0.1`  
**Programme:** `OVC-LSIAC-v0.1`  
**Packet:** `LSIAC-GEN0002-LSIR-REGISTER-MATERIALISATION`  
**Plan:** `OVC-LSIAC-CONSTITUTION-0.1-REVISED-1` / `0.1-R1-RATIFIED`  
**Generation:** `OVC-LSIAC-ACCESSION-GEN-0002`  
**Authority effect:** `NONE_REGISTER_MATERIALISATION_ONLY`

## Purpose

Materialise the six post-Pass2 Laboratory Scientific Inheritance register surfaces required by the ratified LSIAC sequence without creating new scientific claims, inheritance roles, destinations, architecture actions or authority.

The register bundle is a deterministic zero-copy projection of the already-frozen GEN0002 Pass2 adjudication view. The frozen Pass2 decisions remain the source of truth. Register membership is derived only from exact fields already present in those decisions; no source record is duplicated into independent evidence mass.

## Frozen source binding

A conformant materialisation MUST bind all of the following exactly:

- source universe `d29e1c69399d6f312a7e0544c57e2e47c415f37347760f11ce983b926988114c`;
- frontier receipt `022f6cf4149265cc545e6cffc2d0623a513ec2bf1ab38434c793bbf381a92bbe`;
- source-passport set `f97ba927944326864f1a5cc20ecc69a0a4623743231aa8479d713984bbe68019`;
- post-v0.5 delta `1ed67410854478b2947d62055b3b619ad8081c782907c66efa78bbf1d823a42d`;
- Pass1 virtual view `e9b10aebcae1136c1b5df34fb569392e10bcec0a2bc30e93675588ad4e288c6a`;
- Pass2 virtual view `58b364fbf7b8ce160877fb8bba641cb853ea1b29b5af9c4a4b1a5294648749d8`;
- unchanged protocol binding `15e449ffe15ded1d6419533257515ab9686122a1b5c73f7c82c49cea6e273d4f`;
- operator Pass2 authority decision `7130e987c4ba3900eff0abfc43d4989d9899393ef151e2a975dd5b5d04377c84`;
- exactly 431 effective subjects reconstructed from 434 frozen passports.

Any identity drift fails closed.

## Register projections

1. **Laboratory Scientific Inheritance Register (LSIR).** Exactly one projection entry per Pass2 accession decision. It preserves decision identity, source subject identity, source/scientific/exposure state, claim strength, inheritance roles, lifecycle, docket state and authority state. It MUST NOT reinterpret `NONE` as absence of historical scientific value.
2. **Negative Knowledge Register.** Includes only Pass2 decisions whose exact `scientific_disposition` is `NEGATIVE_SUPPORTED`. It preserves those negative results as negative knowledge; it MUST NOT treat them as evidence for a different theory or architecture.
3. **Supersession Register.** Contains only explicit Pass2 `supersession_edges`. Absence of an edge remains absence; no supersession is inferred from recency, naming or no-forward status.
4. **DestinationBindingSets.** Contains only non-empty declarative Pass2 destination bindings. Empty destination sets remain empty; no destination is inferred.
5. **ArchitectureEffectSets.** Projects the exact Pass2 architecture-effect set for each decision. This packet executes none of those effects. For the frozen GEN0002 view every current effect is expected to remain `NO_FORWARD_IMPLEMENTATION`.
6. **ArchitectureGap Register.** Contains only explicit unresolved source-binding docket debt from Pass2 (`docket_status == SOURCE_BINDING_REQUIRED`). Such an entry is classified as `SOURCE_BINDING_GAP_NOT_ARCHITECTURE_ACTIVATION_REQUEST`. Missing role-admissibility evidence for the broader population MUST NOT be laundered into an architecture need.

## Non-transitivity and anti-inference

- `register presence != scientific promotion`;
- `negative knowledge != replacement theory support`;
- `no-forward inheritance != falsification of historical programme science`;
- `source-binding gap != architecture capability need`;
- `architecture effect record != architecture execution`;
- `destination record != owner/source admission`.

The packet may not grant or alter selector/model/family/theory/semantic authority, C2E boundary packs, C2P/C2.5/C3 activation, ESL vocabulary, SFF forecasting, Validation, publication, ACTIVE_DISCOVERY/DEVELOPMENT/VALIDATION, probability, risk, exposure, E-H, trading, execution or agent-write authority.

## Determinism and evidence identity

Each register is sorted deterministically and receives a canonical SHA-256 over its projected members. The bundle receives a canonical SHA-256 over its source binding, register counts and register hashes. Repeated construction from the same frozen source MUST be byte-equivalent under canonical JSON serialization.

## Acceptance

- LSIR count is exactly 431 with 431 unique source subjects and 431 unique Pass2 decision IDs.
- Every LSIR role projection is identical to its frozen Pass2 role set; current GEN0002 remains singleton `NONE` for all subjects.
- Negative Knowledge entries are a complete filter of `NEGATIVE_SUPPORTED` decisions and nothing else.
- Supersession and destination registers contain no invented records.
- Architecture-effect projection is complete and performs zero execution.
- ArchitectureGap Register contains exactly the explicit source-binding docket debt and no inferred architecture need.
- All source bindings and hashes remain exact.
- Targeted and repository-wide assurance pass.

## Rollback

Forward-only. If materialisation or assurance fails, preserve the frozen Pass2 decisions and failed register evidence, correct only deterministic projection defects inside this packet, or mark the packet BLOCKED/QUARANTINED. Never rewrite GEN0002 source evidence or Pass2 decisions in place.
