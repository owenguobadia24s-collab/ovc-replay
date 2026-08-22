# OVC Shared Systems Identity/Profile Contract v0.1

Programme: `OVC-SHARED-SYSTEMS-v0.1`  
Packet / gate: `SHSI-WP1 / SHSI-G1`  
Mode: `INACTIVE_REFERENCE`; authority effect `NONE`.

## Separation law

`hash_algorithm_id`, `serialization_profile_id`, and `identity_projection_id` are
independent, mandatory bindings. A hash-algorithm label never selects a serializer or
projection. A profile identifier is globally unambiguous within one registry
generation; the same identifier attached to different semantics is a collision and
fails closed.

## SerializationProfile

A profile declares its exact character encoding, Unicode handling, key order, numeric
and negative-zero handling, collection meaning, null/timestamp/string rules, identity
projection, self-ID exclusion, storage framing, hash algorithm and conformance vectors.
Logical canonical bytes exclude physical storage framing. Unicode marked
`REQUIRE_NFC` must already be NFC; the implementation never silently changes identity
bytes. Generic array sorting is prohibited except for a profile explicitly declaring
`SEMANTIC_SET`.

## IdentityProjection

The owner declares required identity-bearing fields, conditionally identity-bearing
fields, excluded fields, self-ID fields and descriptive-only fields. Serialization
determines bytes; projection determines content. Missing required fields, conflicting
roles, undeclared projection bindings and non-canonical payloads fail closed.

## LegacySerializationBinding

Historical identifiers, digests and bytes are immutable. Resolution requires the exact
legacy identifier plus owner, pack and generation context. It returns the registered
historical profile/projection/hash rule and stored digest; it never reserializes or
rehashes the historical object. Zero matches is unknown and multiple matches is
ambiguous; both fail closed.

## Invariants

- Machine path, hostname, PID, worker arrival order, local timestamp and presentation
  fields are excluded unless an owner projection explicitly makes them semantic.
- The same logical identity with different immutable bytes is an integrity failure,
  never last-write-wins.
- Physical blob digest and logical identity digest remain distinct when framing differs.
- Unknown algorithms, profiles, projections, extensions and non-finite numbers fail
  closed.
- The maintained reference implementation remains standard-library-only and below the
  steady-state registry/resolution runtime, preserving the Stage-0 bootstrap DAG.

## Rollback

Before integration, preserve or close the bounded WP1 branch. After integration,
correct forward with a new profile/projection/binding generation. Never rewrite a
historical digest, Stage-0 record, ratified design/plan identity or GRT owner binding.
