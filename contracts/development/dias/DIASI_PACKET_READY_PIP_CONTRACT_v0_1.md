# DIASI PACKET_READY / immutable PIP contract v0.1

`PacketReadyRecord` freezes packet semantics before placement. `ImmutablePacketIntegrationPayload` binds the ready identity, authority, dependency frontier, logical changes, apply preconditions, assurance class, and completion transition. Reconstructing it in a fresh process produces the same PIP identity.

Ordinary main movement, provider reruns, lease loss, ruleset drift, and process restart are placement/revalidation events. They do not reopen development while apply preconditions still hold. Semantic development reopens only for `PACKET_DEFECT`, a failed apply precondition, or `MEANING_BEARING_OWNER_CONFLICT`. Unknown cross-boundary events block without inventing a reopen.

Assurance classes are `A0`, `AA1`, `AA2`, `AA3`, and `CROSS_BOUNDARY_UNKNOWN`. The classifier is closed-world and cannot grant authority. This contract has no live write, scheduler, or cutover effect.
