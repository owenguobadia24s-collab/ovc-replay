# canonical-json-v1 — ESLI-WP2

Authority: deterministic inactive conformance only. This contract creates no selector, representation, family, semantic, Validation, publication or exposure authority.

## Byte contract

- UTF-8 output.
- Object keys are Unicode-codepoint lexicographic and emitted without insignificant whitespace.
- `null`, empty array, empty object and omission remain distinct.
- Booleans remain booleans; integer and finite decimal numbers use normalized base-10 notation with no redundant fractional zeros. NaN, infinities and negative zero are rejected.
- Schema-declared set-like arrays are ordered deterministically. Bootstrap facet order is `LOCATION`, `MOTION`, `ORGANISATION`, `INTERACTION`; declared reference/reason/generation arrays are lexical; dependency refs are ordered by `ref_id`. Other arrays preserve schema/input order.
- Timestamps are schema/contract validated as UTC `Z` before identity hashing; canonicalization itself does not reinterpret time.

## Identity

SHA-256 is computed over exact canonical bytes. A record's own top-level identifier/hash fields are excluded from its identity projection; referenced upstream/frontier IDs remain included. `occurrence_record_id = "so1:" + lowercase_hex_sha256`.

EvidenceFrontier uses the same profile and excludes only its own `evidence_frontier_id` / `logical_hash` when computing its logical hash.

## Independent proof

`canonical.py` is the production implementation. `canonical_reference.py` is an independently written standard-library reference and MUST NOT import the production serializer. The five Appendix-G traces must produce byte-identical A/B output and exact golden hashes. The first normative trace MUST retain `so1:db177687a9bff538d4dfc0fb96506af230fa50d7ba6fdf99c327e7f0d4c487a4`.
