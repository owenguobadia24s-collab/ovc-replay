# OPT-B.C1 v2 B1-G2 operator decision

## Decision

`PASS — EXACT FROZEN DISCOVERY AND DEVELOPMENT RELEASES ACCEPTED AS PUBLICATION-READY; WP5 R2 PUBLICATION AUTHORISED.`

B1-G2 reviewed the exact outputs of WP4F workflow run `30187276514`. The accepted publication sources are limited to:

- `OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1` with manifest `MANIFEST.C1.OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1.r1` and manifest SHA-256 `6abd6d1fb74e7f3797e9add2435eaa5e487b612efd2f4b5f4f4c59679820d5d2`;
- `OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1` with manifest `MANIFEST.C1.OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1.r1` and manifest SHA-256 `ca83f2d9d948be426f3d80ebc91cc981f92546dfdd07268d71938d618c51f017`.

The review confirms 192 frozen record files, 212,764 C1 records and 36,170,710 manifest-accounted bytes across the two release roots. Every manifest-listed file must be re-read and verified again during publication.

## Publication authority granted

WP5 may download only the exact WP4F artifacts recorded in `B1_G2_GATE_PACKET.json`, perform a non-destructive collision preflight, upload immutable payload files first, upload each manifest last and then stream every remote object for size and SHA-256 verification.

The GitHub Actions source artifacts expire on 24 October 2026. Their finite retention does not create market authority; it defines the deadline before which WP5 must either publish these exact verified bytes or return the programme to a new freeze execution.

## Authority not granted

B1-G2 does not authorise:

- a C1 selector change;
- C2 consumption or a C1-to-C2 handoff;
- Validation release consumption or construction;
- overwrite of any existing R2 object;
- publication from a rebuilt, substituted or locally altered release root;
- probability, exposure, trading or execution behaviour.

C1 selectors remain `NONE`. Validation remains `LOCKED_UNCONSUMED`.

## Stop conditions

WP5 must stop without manifest publication if any source artifact, descriptor, manifest, payload hash, release-parent binding or target remote namespace differs from the B1-G2 packet. A partial payload upload without its manifest remains non-authoritative and cannot become a selector target.

## Rollback

Before successful full remote verification, rollback is `WP4F_RELEASE_FROZEN_LOCAL_VERIFIED_NO_PUBLICATION`. After any failed publication attempt, selectors remain `NONE`; no historical or legacy release may be reactivated.

## Next packet

`OPT-B.C1 v2 WP5 — R2 publication and full remote verification`.
