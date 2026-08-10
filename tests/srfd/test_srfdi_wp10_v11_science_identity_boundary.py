from __future__ import annotations

import unittest

from ovc.opt_b.srfd.wp10_v10_interface import SCIENCE_BINDING, SCIENCE_IDENTITY_SHA256
from ovc.opt_b.srfd.wp10_v11_interface import (
    FROZEN_ENVIRONMENT_PROFILE_SHA256,
    HARDENING_REHEARSAL_SHA256,
    RunBindingV11,
    WP10V11InterfaceError,
    verify_science_unchanged,
)


def make_binding(*, packet_id: str = "SRFDI-WP10-v1.1", eligible_ids_sha256: str | None = None) -> RunBindingV11:
    return RunBindingV11(
        programme_id=SCIENCE_BINDING["programme_id"],
        packet_id=packet_id,
        population_id=SCIENCE_BINDING["population_id"],
        eligible_ids_sha256=eligible_ids_sha256 or SCIENCE_BINDING["eligible_ids_sha256"],
        scientific_manifest_sha256=SCIENCE_BINDING["scientific_manifest_sha256"],
        preregistration_sha256=SCIENCE_BINDING["preregistration_sha256"],
        representation_pack_sha256=SCIENCE_BINDING["representation_pack_sha256"],
        segmentation_pack_sha256=SCIENCE_BINDING["segmentation_pack_sha256"],
        stability_pack_sha256=SCIENCE_BINDING["stability_pack_sha256"],
        source_binding_sha256=SCIENCE_BINDING["source_binding_sha256"],
        capacity_grid_sha256=SCIENCE_BINDING["capacity_grid_sha256"],
        science_identity_sha256=SCIENCE_IDENTITY_SHA256,
        capacity_envelope_sha256="11" * 32,
        storage_binding_sha256="22" * 32,
        execution_binding_sha256="33" * 32,
        execution_environment_profile_sha256=FROZEN_ENVIRONMENT_PROFILE_SHA256,
        hardening_rehearsal_sha256=HARDENING_REHEARSAL_SHA256,
        implementation_commit="44" * 20,
    )


class SRFDIWP10V11ScienceIdentityBoundaryTests(unittest.TestCase):
    def test_v11_packet_generation_may_change_while_science_remains_exact(self):
        binding = make_binding()
        verify_science_unchanged(binding)
        self.assertEqual("SRFDI-WP10-v1.1", binding.packet_id)
        self.assertNotEqual(SCIENCE_BINDING["packet_id"], binding.packet_id)

    def test_wrong_v11_packet_id_still_fails_governance_identity(self):
        with self.assertRaises(WP10V11InterfaceError) as ctx:
            verify_science_unchanged(make_binding(packet_id="SRFDI-WP10-v1.2"))
        self.assertEqual("V11_IDENTITY_DRIFT", ctx.exception.reason_code)

    def test_actual_scientific_binding_drift_still_fails_closed(self):
        drift = ("00" * 32) if SCIENCE_BINDING["eligible_ids_sha256"] != ("00" * 32) else ("ff" * 32)
        with self.assertRaises(WP10V11InterfaceError) as ctx:
            verify_science_unchanged(make_binding(eligible_ids_sha256=drift))
        self.assertEqual("V11_SCIENCE_BINDING_DRIFT", ctx.exception.reason_code)


if __name__ == "__main__":
    unittest.main()
