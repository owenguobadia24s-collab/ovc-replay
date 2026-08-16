# P2CTI Identity & Generation Contract v0.1

Programme: `OVC-P2CTI-CONFORMANCE-v0.1`  
Packet: `P2CTII-WP1`  
Authority effect: **NONE**.

## Identity planes

P2CTI MUST distinguish `TheorySeries`, exact owner semantic generation, Path-2 work/formalisation generation, inventory generation, evidence assessment and physical execution provenance.

`source_semantic_identity != p2cti_entry_identity != p2cti_generation_identity != branch/pr/run/cache/ui_identity`.

Branch name, PR number, worker, CI run, cache key, local path, physical attempt and UI session are provenance only and MUST NOT participate in logical P2CTI identities.

## Canonicalisation

P2CTI reuses `ovc.research_operations.canonical.canonical_sha256`. Identity-bearing payloads are canonical JSON with sorted keys, compact separators, UTF-8 and NaN/Infinity rejection.

## Entry identity

`Path2TheoryInventoryEntry` identity is derived only from its series, subject lineage identity/class, exact owner object identity and exact owner semantic generation. Source storage location and current projection state do not redefine the source scientific object.

## Generation identity

An inventory generation binds series identity, generation ordinal, exact ordered-independent membership set and exact `P2CTISourceFrontierManifest` identity. Member ordering is canonicalized before hashing. A changed member set or source frontier creates a new generation; historical generations are immutable and remain addressable.

## Corrections

Corrections are forward-only. A material owner proposition/scope/falsifier change is represented by an owner successor semantic generation and therefore a new P2CTI projection; P2CTI never edits owner scientific payload in place. Evidence-state advancement alone need not change owner theory identity and is represented on its separate owner/currentness plane.
