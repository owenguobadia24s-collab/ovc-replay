# RCCR Source Precedence Contract v0.1

RCCR never creates owner authority. Resolution order is owner court record -> exact source generation -> source-faithful requirement interpretation -> RCCR derived assessment. Title similarity, filename similarity, recency metadata, external prose, or RCCR convenience cannot override an owner identity, authority state, first-valid-time, protocol boundary, or supersession relation.

Conflicts are fail-closed. When two sources claim the same logical role but identity/authority/first-valid-time cannot be reconciled source-faithfully, RCCR records an unresolved source discrepancy and routes to human review; it does not pick a winner by heuristic. External material may supply provenance or methodological pressure, but may not mint OVC owner authority. Same wording from distinct source generations remains distinct unless the authoritative owner explicitly certifies semantic equivalence.

Circular sourcing is prohibited: no RCCR-generated object may be used as the authority source that establishes the owner state on which that same RCCR object depends. RCCR read models have no source-precedence authority.

Validation payloads remain inaccessible; EC1 real-source execution remains ungranted by this contract. `authority_effect = NONE` is invariant.
