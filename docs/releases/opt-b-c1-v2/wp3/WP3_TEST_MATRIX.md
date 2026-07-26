# WP3 test matrix

| Area | Required proof |
|---|---|
| Arithmetic | Exact Decimal outputs for representative bar geometry |
| Determinism | Same inputs produce identical record IDs and canonical bytes |
| Null policy | Zero range and unavailable prior close remain explicit |
| Chronology | Future first-valid time is rejected |
| Contiguity | Gaps are never bridged |
| Identity | Release, manifest, instrument, clock and side mismatches block prior-close use |
| Source authority | Historical v1, control clocks and locked Validation are rejected |
| Package boundary | No legacy, downstream, network or remote-write dependency |
| Authority | Synthetic outputs remain `NONE`; all C1 selectors remain `NONE` |
