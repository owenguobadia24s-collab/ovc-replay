from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ovc.opt_b.srfd.serialization import logical_sha256
from ovc.opt_b.srfd.wp10_execution_resilience import RunAuthorityStore
from ovc.opt_b.srfd.wp10_v07_family import frozen_configuration_plan
from ovc.opt_b.srfd.wp10_v10_interface import SCIENCE_BINDING, SCIENCE_IDENTITY_SHA256
from ovc.opt_b.srfd.wp10_v11_execution import ContentAddressedArtifactStoreV11
from ovc.opt_b.srfd.wp10_v11_interface import (
    FROZEN_ENVIRONMENT_PROFILE_SHA256,
    HARDENING_REHEARSAL_SHA256,
    RunBindingV11,
    mint_single_use_token,
)
from ovc.opt_b.srfd.wp10_v11_runner import _run_from_start_v11


def binding() -> RunBindingV11:
    return RunBindingV11(
        programme_id="OVC-SRFD-BENCHMARK-v0.1",
        packet_id="SRFDI-WP10-v1.1",
        population_id=SCIENCE_BINDING["population_id"],
        eligible_ids_sha256=SCIENCE_BINDING["eligible_ids_sha256"],
        scientific_manifest_sha256=SCIENCE_BINDING["scientific_manifest_sha256"],
        preregistration_sha256=SCIENCE_BINDING["preregistration_sha256"],
        representation_pack_sha256=SCIENCE_BINDING["representation_pack_sha256"],
        segmentation_pack_sha256=SCIENCE_BINDING["segmentation_pack_sha256"],
        stability_pack_sha256=SCIENCE_BINDING["stability_pack_sha256"],
        source_binding_sha256=SCIENCE_BINDING["source_binding_sha256"],
        capacity_grid_sha256=SCIENCE_BINDING["capacity_grid_sha256"],
        science_identity_sha256=SCIENCE_IDENTITY_SHA256,
        capacity_envelope_sha256="11"*32,
        storage_binding_sha256="22"*32,
        execution_binding_sha256="33"*32,
        execution_environment_profile_sha256=FROZEN_ENVIRONMENT_PROFILE_SHA256,
        hardening_rehearsal_sha256=HARDENING_REHEARSAL_SHA256,
        implementation_commit="44"*20,
    )


def records():
    result=[]
    for index in range(8):
        result.append({
            "representation_id":f"R{index:02d}",
            "implementation_class_id":"SRFDI-R1",
            "representation_variant_id":None,
            "first_valid_time":f"2026-06-{index+1:02d}T00:00:00Z",
            "structural_raw":{"A.value":"UP" if index%2 else "DOWN","B.value":f"B{index%3}"},
            "structural_derived":{},"structural_normalized":{},"comparison_only":{},
        })
    return result


def sealed_segmentation(method: str):
    body={
        "schema":"ovc-srfdi-wp10-v07-segmentation-output/v1",
        "method_id":method,
        "counts":{"stream_count":1,"segment_count":1,"boundary_count":0},
        "result":{"synthetic":True,"method_id":method},
        "authority_effect":"NONE_EXECUTION_ROUTE_ONLY",
    }
    return {**body,"logical_hash":logical_sha256(body)}


class SRFDIWP10V11ExecutionTests(unittest.TestCase):
    def test_real_route_uses_file_backed_analysis_and_packet_never_loads_analysis_payload(self):
        domain_id="SRFD.COMP.V11.EXEC.TEST"
        plan=["population","segmentation/RUN_CHANGE_SEGMENTATION","segmentation/NULL_BOUNDARY_CONTROL",f"domain/{domain_id}/prepare"]
        plan += [f"domain/{domain_id}/configuration/{d.configuration_id}" for d in frozen_configuration_plan(domain_id)]
        plan += [f"domain/{domain_id}/analysis","packet"]
        b=binding()
        with TemporaryDirectory(prefix="srfd_v11_exec_") as td:
            root=Path(td)
            token=mint_single_use_token(b,operator_decision_id="TEST_ONLY")
            start=RunAuthorityStore(root).consume(token,b)
            original=ContentAddressedArtifactStoreV11.load_output
            def guarded_load(self,start_receipt,run_binding,unit_id):
                if str(unit_id).endswith('/analysis'):
                    raise AssertionError('packet/restart path attempted whole-analysis load')
                return original(self,start_receipt,run_binding,unit_id)
            preflight={
                "source_record_count":9420,"eligible_record_count":8598,
                "eligible_record_ids_sha256":SCIENCE_BINDING["eligible_ids_sha256"],
                "population_id":SCIENCE_BINDING["population_id"],"comparability_domain_count":36,
                "exact_pair_opportunity_count":35380668,"family_configuration_count":1944,"work_unit_count":2020,
            }
            with patch("ovc.opt_b.srfd.wp10_v11_runner.planned_work_units",return_value=tuple(plan)), patch(
                "ovc.opt_b.srfd.wp10_v11_runner.execute_segmentation",
                side_effect=lambda _rows,method:sealed_segmentation(method),
            ), patch.object(ContentAddressedArtifactStoreV11,"load_output",new=guarded_load):
                result=_run_from_start_v11(
                    start=start,binding=b,rows=records(),domains={domain_id:records()},
                    preflight=preflight,durable_root=root,
                )
            self.assertTrue(result["complete"])
            self.assertEqual(len(plan),result["completed_unit_count"])
            self.assertEqual("RECOMPUTE_FROM_FROZEN_PARENTS_NO_UNVERIFIED_HISTORICAL_REUSE",result["reuse_disposition"])
            self.assertIn(f"domain/{domain_id}/analysis",result["unit_output_hashes"])
            store=ContentAddressedArtifactStoreV11(root,max_external_bytes=24*1024**3)
            packet=store.load_output(start,b,"packet")
            self.assertEqual(result["unit_output_hashes"][f"domain/{domain_id}/analysis"],packet["domain_analysis_hashes"][domain_id])
            self.assertEqual("NONE",packet["selector_family_semantic_publication"])
            self.assertEqual("NONE",packet["probability_risk_exposure_execution"])


if __name__=="__main__": unittest.main()
