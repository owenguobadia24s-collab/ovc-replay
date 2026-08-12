# C2P Candidate / Tracklet Contract v0.2
Status: FROZEN_INACTIVE_CONFORMANCE / authority_effect=NONE

Candidate extraction reads only ObjectPack-declared upstream fields and emits either one immutable candidate or an explicit typed non-emission/evidence state. Every emitted Candidate binds exact source refs/lineage, role, geometry kind, canonical geometry, effective interval, FVT, cutoff and evidence/computability state.

Tracklets are provisional continuity hypotheses. They preserve append-only member candidate IDs, an exact decision frontier, bitemporal chronology, and orthogonal observability/evaluation state. Lawful states are `OPEN`, `AMBIGUOUS`, `CONFIRMED`, `EXPIRED`, and `CENSORED`; `TRACKLET_PROMOTED` is the event that moves an OPEN/AMBIGUOUS Tracklet to `CONFIRMED`, not a Tracklet state named PROMOTED.

A Tracklet may confirm only after the frozen ObjectPack confirmation contract and absence of an unresolved equally-lawful competitor. Censoring is not expiry. Expired/censored tracks do not become durable identities. Tracklets are forbidden as canonical C2.5/C3 referents.
