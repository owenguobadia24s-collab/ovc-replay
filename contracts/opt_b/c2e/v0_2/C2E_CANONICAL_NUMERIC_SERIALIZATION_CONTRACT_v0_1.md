# C2E Canonical Numeric Serialization Contract v0.1

Identity/hash-bearing semantic numerics use contract-declared canonical decimal text, never runtime `repr(float)`.

Rules: UTF-8 JSON, deterministic keys/enums, explicit null, no NaN or infinity; exponent notation is denied unless an exact field contract separately admits and canonicalizes it; negative zero normalizes to canonical zero; precision/quantization is field- or parameter-owned and there is no global decimal precision; values that exceed declared precision fail closed rather than being silently rounded; parameter ordering and diagnostic metadata cannot alter identity; identity-defining value or precision changes must alter identity.

Binary floating point may be used internally only where separately permitted, but it is never accepted directly into the identity serializer. Logical identity must be independent of `PYTHONHASHSEED`, worker layout, machine, path and process runtime.
