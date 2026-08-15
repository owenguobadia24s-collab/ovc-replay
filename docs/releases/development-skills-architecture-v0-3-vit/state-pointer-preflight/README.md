# Programme-state / current-pointer consistency preflight

Run before expensive repository-wide / FINAL_HEAD assurance:

```bash
python scripts/development/ovc_programme_state_preflight.py
```

The check is read-only and fail-closed for canonical `ovc-programme-current-state-pointer/v1` records. It validates that each pointer resolves to an existing programme-state JSON record and that overlapping programme/status/packet/gate/next-packet fields agree. It also catches completed-packet and already-completed-successor contradictions when the referenced state exposes `completed_packets`.

It deliberately skips noncanonical/legacy pointer schemas instead of reinterpreting them. It never repairs state or grants authority.
