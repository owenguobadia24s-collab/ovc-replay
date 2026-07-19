# External artifacts

Ordinary Git contains the deterministic code and canonical project-control
surface. It contains no OHLCV/market CSVs, raw provider data, canonical bar
tables, generated state/outcome streams, caches, duplicate engine ZIPs, or
bulky replay evidence.

Historical manifests under `docs/history/releases/` retain the exact expected
artifact names and hashes. A manifest can reference an external file that is not
checked into Git; that is intentional, not an assertion that the compact history
directory is a self-contained replay bundle.

The local sibling folder `ovc-replay-external-artifacts` holds the data-bearing
files, preserved package archives, cache quarantine, and its own SHA-256 index.
That folder is deliberately not part of this repository.

Do not commit raw provider feeds, derived market tables, or generated replay
streams directly. Treat them as external dependencies and preserve the existing
manifest hashes rather than recompressing or renaming them silently.
