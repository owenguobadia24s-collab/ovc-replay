# WP3 implementation summary

The reference engine implements exact Decimal arithmetic for the frozen 18-field C1 formula surface, strict OPT-A v2 input admissibility, immediate contiguous-prior-close resolution, deterministic identity, canonical serialization and local validation.

The implementation is deliberately bounded:

- synthetic/golden fixture computation only;
- no market replay or external release workspace;
- no network or R2 write path;
- no C1 selector mutation;
- no Validation consumption;
- no C2, outcome, semantic, probability, exposure or execution dependency.
