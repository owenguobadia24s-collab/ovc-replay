# P2CTI State, Currentness & Pointer Contract v0.1

Programme: `OVC-P2CTI-CONFORMANCE-v0.1`  
Packet: `P2CTII-WP1`  
Authority effect: **NONE**.

## Orthogonal state planes

A theory/inventory subject has no single authoritative status. P2CTI stores separate projections for lifecycle, evidence, Path-2 frontier, formalisation, candidate relation, authority and currentness. Owner-controlled planes carry owner references; P2CTI must not infer them from another plane.

## Currentness vocabulary

Base currentness values are `CURRENT`, `CURRENT_WITH_LIMITATION`, `REASSESSMENT_REQUIRED`, `SOURCE_GENERATION_ADVANCED`, `AUTHORITY_FRONTIER_CHANGED`, `HISTORICAL`, and `UNRESOLVED`.

`TheoryInventoryCurrentPointer` is only a locator to one accepted inventory/relation generation. It does not grant scientific or operational authority. Routine pointer/index refresh is rebuildable runtime state and should remain outside Git; compact milestone/incident/activation receipts may enter Git.

## Fail-closed rules

A missing owner source, conflicting source generations, authority ambiguity or unresolved currentness cannot be converted to CURRENT by recency, lexical order, path, title or cached value. WP2 implements owner precedence and the two-point source-frontier check; until `P2CTII-G2-ALG` passes, its decision-bearing current pointer remains non-operational/advisory.

Historical generations remain addressable. A source advance creates new currentness evidence rather than deleting or rewriting historical projections.
