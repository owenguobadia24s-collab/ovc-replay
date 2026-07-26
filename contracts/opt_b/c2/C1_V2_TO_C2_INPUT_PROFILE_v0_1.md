# C1 v2 to C2 Input Profile v0.1

Accepted parents are exact active C1 v2 Discovery and Development records only. Required authority states are ACTIVE_DISCOVERY and ACTIVE_DEVELOPMENT. Allowed clocks are 15M and 2H_A_L; allowed sides are BID and ASK. Every input must expose exact C1/OPT-A release, manifest, record and source-bar identities; all 18 C1 measurements with versions; quality/null reasons; close time and first-valid time.

Reject wrong role, clock, side, schema, authority, release, manifest, unsealed parent, C1 Validation, legacy B-STATE, quarantined runtime imports or future fields. C2 may not repair or write back to C1.