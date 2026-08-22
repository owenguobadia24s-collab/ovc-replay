# SHSI-WP8 Research Operations/DMRP shadow-consumer materialisation

Status: implemented candidate pending exact-head repository assurance. Authority
delta: `NONE`. Runtime state: `READ_ONLY_SHADOW_ONLY`.

This packet consumes one governed synthetic corpus and the repository metadata of
one external-artifact binding manifest. It performs no real-source or external-byte
read, creates no store, performs no Research Operations write, and adds no provider,
source, or research role.

The state crosswalk preserves lifecycle literally and proves that `FROZEN` maps to
authority `UNKNOWN`. EvidenceFrontier missing required records are typed
`NOT_EVALUABLE`; repository artifacts produce typed present, missing, and hash
mismatch reachability. Whole-record wrappers round-trip exact identities, and
adapter complexity remains within the immutable WP6 budget.

Validation remains locked and unconsumed. Candidate freeze, source, scientific,
semantic, publication, probability, risk, exposure, and execution authority remain
unchanged.

Rollback: remove inactive WP8 shadow projections while preserving owner records,
historical identities, and comparison evidence.
