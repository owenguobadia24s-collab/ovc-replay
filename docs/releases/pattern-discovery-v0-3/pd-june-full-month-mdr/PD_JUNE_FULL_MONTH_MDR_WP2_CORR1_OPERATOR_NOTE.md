# PD-JUNE-FM-WP2 CORR1 — Manifest hash validation correction

The accepted A2 source manifest is preserved byte-for-byte. Its exact file SHA-256 is `8080b8def035cb37940b89054287d0c61756149aa7cb4711fc462a0ebbdc1f87`.

A2 changed authority and censoring fields after the intake self-hash was generated. Consequently, the preserved embedded value `1578b555f3d5aa2822b603141261f86a047096030e5faacd4380ef2c6d4f52e3` is not the canonical logical hash of the accepted A2 content. The accepted A2 content hash is `aee0006826b4a9703416a4f171306df02f85b081f7f515e701ac8b0b2b409669`.

WP2 now verifies all three identities independently and does not mutate the frozen source. After the corrective PR is merged, pull `main` and rerun WP2 preflight followed by execute.
