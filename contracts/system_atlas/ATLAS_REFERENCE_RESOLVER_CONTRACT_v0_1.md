# Atlas Reference Resolver Contract v0.1

## Pipeline

The reference resolver executes this fixed order:

1. normalize identity only through explicit continuity bindings;
2. preserve the exact supplied scope and reject missing required dimensions;
3. normalize declared relationship aliases;
4. apply `AtlasPredicateAuthorityRegistry` source and evidence admission;
5. enforce exactly-one owner cardinality without heuristic selection;
6. intersect authority grant, denial, reservation, scope, runtime permission,
   security policy, prerequisite state, and currentness;
7. emit currentness and conflict evidence; and
8. produce a reference resolution result.

Paths, recency, lexical order, confidence, graph adjacency, storage,
projection, and consumption MUST NOT select an owner or grant authority.
Candidate and inferred GRT evidence cannot satisfy a high-risk predicate.

## Relationship reconciliation

The declared/observed/forbidden matrix produces `RECONCILED`,
`DECLARED_ONLY`, `OBSERVED_ONLY`, `FORBIDDEN_OBSERVED`, `CONFLICTING`, or
`UNRESOLVED` exactly as ratified. Conflicting evidence is preserved, not
discarded after a winner is chosen.

## Owner and authority failure bias

Multiple distinct admissible current values for an exactly-one owner role emit
`OWNER_CONFLICT`; predicate precedence does not silently select among them.
An explicit authority denial controls a grant, and a reservation controls in
the absence of denial. A grant is reconciled only when every required
intersection factor is explicitly `ALLOW`. Missing or unknown factors never
become granted authority.

## Independent gate

Until `ATLAS-G4-ALG` has an eligible reproducible independent `PASS`, reference
results remain `DENIED_PENDING_ATLAS_G4_ALG` and `canonical_assertions` remains
empty. The implementation author cannot self-review or manufacture that gate.

VIT `CURRENT`, `ACTIVE`, and `AUTHORISED` projections MUST consume
`ovc.development.skills.vit_current_state.resolve_current_vit_query` without
historical fallback. Atlas MUST NOT reconstruct or override that current status
from historical VIT plans, gates, filenames, or general candidate precedence.
