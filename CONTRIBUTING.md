# Contributing

Changes must preserve deterministic replay and the authority boundary.

Before opening a pull request:

1. State which contract or version the change affects.
2. Do not alter sealed inputs or historical manifests in place.
3. Add a new contract/decision record for semantic changes.
4. Add tests for no-lookahead, gap safety, deterministic ordering, and symmetry
   where applicable.
5. Run `PYTHONPATH=src python3 -m unittest discover -s tests -v`.
6. Do not describe structural observations as trades, wins, edge, or execution
   authority.

Large generated outputs belong outside ordinary Git and must be hash-addressed
from a manifest.
