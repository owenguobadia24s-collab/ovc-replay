from __future__ import annotations

import unittest

from ovc.opt_b.market_grammar import PredicateDomain, infer_domain


class PredicateDomainPrecedenceTests(unittest.TestCase):
    def test_exact_object_binding_precedes_generic_record_id_suffix(self) -> None:
        self.assertIs(PredicateDomain.PROVENANCE, infer_domain("record_id"))
        self.assertIs(
            PredicateDomain.OBJECT_BINDING,
            infer_domain("parent_record_id"),
        )
        self.assertIs(
            PredicateDomain.OBJECT_BINDING,
            infer_domain("episode_id"),
        )
        self.assertIs(
            PredicateDomain.PROVENANCE,
            infer_domain("source_observation_record_id"),
        )


if __name__ == "__main__":
    unittest.main()
