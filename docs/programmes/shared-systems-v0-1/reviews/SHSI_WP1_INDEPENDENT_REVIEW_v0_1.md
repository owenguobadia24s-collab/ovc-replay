# SHSI-WP1 Independent Conformance Review

Scope: `SHSI-WP1 / SHSI-G1`; authority delta `NONE`.

Review method: compare the maintained reference implementation with a separately coded,
profile-specific comparator; exercise frozen golden vectors and adversarial collision,
ambiguity, negative-zero, Unicode and projection cases; verify the Stage-0 dependency
boundary remains standard-library-only.

Disposition: `PASS_PENDING_EXACT_HEAD_REPOSITORY_ASSURANCE`.

The implementation distinguishes algorithm, profile, projection, logical content,
profile-bound logical identity and physical blob identity. Legacy resolution returns an
immutable stored digest and has no rehash path. Current consumer implementations remain
unchanged. G1 may auto-ratify only on exact-head full assurance and equivalent physical
materialisation.
