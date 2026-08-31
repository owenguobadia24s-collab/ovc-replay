# C2-CSM Reference Source Lineage & Confidence Contract v0.1

Programme: `OVC-EML-C2S-SPTO-CONFORMANCE-PREREG-v0.1`  
Packet: `C2S-SPTOI-WP1`

## Confidence classes

- `SOURCE_EXACT`: the cited artifact is an exact source/evidence artifact for the claim it owns. This classification alone does not make it implementation-bearing; exact bytes/code/contract must also be retrievable and content-identifiable for implementation semantics.
- `SOURCE_DERIVED`: lineage/evidence is supported, but the exact load-bearing implementation semantics are not fully recoverable from the artifact. It MUST NOT define implementation behavior.
- `MISSING`: no admissible source artifact was recovered.

## Implementation-binding classes

- `EXACT_IMPLEMENTATION_BOUND`: exact load-bearing implementation source is recoverable and content-identifiable.
- `EXACT_EVIDENCE_ONLY`: exact artifact supports a result, census, interface observation or historical identity, but does not itself define the load-bearing mechanics.
- `DERIVED_NON_IMPLEMENTATION`: source-derived evidence only; prohibited from defining mechanics.
- `UNAVAILABLE`: required exact implementation source was not recovered.

## Load-bearing reference semantics

The source-completeness gate evaluates these independently:

1. `P3_FORMATION_LIFECYCLE`
2. `R5_BOUNDARY_ROLE_SUCCESSION`
3. `T2_ATOMIC_COMPOUND_TRANSITIONS`
4. `S2_SNAPSHOT_SUCCESSION_LEDGER`

`REFERENCE_COMPLETE` is possible only if all four are `EXACT_IMPLEMENTATION_BOUND`. Any other state yields `REFERENCE_PARTIAL_SOURCE_LIMITED`.

## Anti-reconstruction rule

Consumer Pine scripts that import `I8th/OVC_C2_CSM_P3R5T2S2/1`, journal summaries, C2E copied/recomputed helper logic, screenshots, and downstream observations may prove historical use, output shape or lineage. They MUST NOT be promoted into the missing C2 library semantics unless exact source identity and ownership are separately established.

## Current WP1 census conclusion

Repository search at the WP1 baseline found no exact `OVC_C2_CSM_P3R5T2S2` or `C2LIB-0001` library source. The external file census recovered exact result/export/consumer artifacts and source-derived C2LIB lineage, but not a content-identifiable exact published C2 library implementation. Therefore the current reference status is `REFERENCE_PARTIAL_SOURCE_LIMITED`.
