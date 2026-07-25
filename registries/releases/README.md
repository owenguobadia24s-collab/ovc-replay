# Release governance registries

WP1 registers one historical v1 OPT-A release and the three exact planned v2 role releases. Registration records identity and constraints only; it does not create, publish or activate a market release.

- `OPT_A_RELEASE_REGISTRY.yaml` — v1 disposition plus the discovery, development and validation programme identities.
- `OPT_A_ACTIVE_SELECTORS.yaml` — atomic role selector proposal; all selectors remain `NONE`.
- `OPT_A_VALIDATION_ACCESS_REGISTRY.yaml` — default-deny validation access; 2025 remains `LOCKED_UNCONSUMED`.

The historical v1 release cannot be a publication identity, selector fallback, parameter source or rollback target. New bytes require a new release ID.
