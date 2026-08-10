from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ovc.opt_b.srfd.serialization import canonical_json_bytes, logical_sha256
from ovc.opt_b.srfd.wp10_v07_analysis import analyse_domain
from ovc.opt_b.srfd.wp10_v07_family import frozen_configuration_plan, materialize_prepared_configuration, prepare_domain
from ovc.opt_b.srfd.wp10_v11_streaming_analysis import stream_analyse_domain_to_file
from ovc_evidence_store.streaming import StreamingContentAddressedArtifactStore


def small_records():
    rows=[]
    for index in range(8):
        rows.append({
            'representation_id':f'R{index:02d}',
            'implementation_class_id':'SRFDI-R1',
            'representation_variant_id':None,
            'first_valid_time':f'2026-06-{index+1:02d}T00:00:00Z',
            'structural_raw':{'A.value':'UP' if index%2 else 'DOWN','B.value':f'B{index%3}'},
            'structural_derived':{},'structural_normalized':{},'comparison_only':{},
        })
    return rows


class SRFDIWP10V11StreamingAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records=small_records(); cls.domain_id='SRFD.COMP.V11.STREAM.TEST'; cls.preparation=prepare_domain(cls.records,cls.domain_id)
        cls.catalogs={}
        for descriptor in frozen_configuration_plan(cls.domain_id):
            cls.catalogs[descriptor.configuration_id]=materialize_prepared_configuration(cls.records,cls.preparation,descriptor)['catalog']
        cls.reference=analyse_domain(cls.records,cls.preparation,cls.catalogs)

    def test_streaming_analysis_is_byte_identical_to_reference(self):
        with TemporaryDirectory() as td:
            path=Path(td)/'analysis.json'
            result=stream_analyse_domain_to_file(self.records,self.preparation,self.catalogs,path)
            self.assertEqual(canonical_json_bytes(self.reference),path.read_bytes())
            self.assertEqual(self.reference['logical_hash'],result.logical_hash)
            payload=dict(self.reference); payload.pop('logical_hash')
            self.assertEqual(logical_sha256(payload),result.logical_hash)
            self.assertEqual(len(path.read_bytes()),result.raw_bytes)

    def test_streaming_store_commits_file_without_loading_whole_output(self):
        with TemporaryDirectory() as td:
            root=Path(td); path=root/'analysis.json'; result=stream_analyse_domain_to_file(self.records,self.preparation,self.catalogs,path)
            store=StreamingContentAddressedArtifactStore(root,namespace='test/v11',max_external_bytes=64*1024*1024,chunk_bytes=4096,compression_level=6)
            receipt=store.commit_file(unit_id=f'domain/{self.domain_id}/analysis',raw_output_path=path,logical_output_sha256=result.logical_hash,context={'run':'TEST'})
            self.assertEqual(result.raw_sha256,receipt.raw_output_sha256)
            self.assertEqual(result.raw_bytes,receipt.raw_output_bytes)
            store.verify_receipt_streaming(receipt,expected_context={'run':'TEST'})
            self.assertEqual(path.read_bytes(),store.load_bytes(f'domain/{self.domain_id}/analysis',expected_context={'run':'TEST'}))


if __name__=='__main__': unittest.main()
