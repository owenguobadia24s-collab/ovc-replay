from __future__ import annotations
import json,unittest
from pathlib import Path
from ovc.opt_b.market_grammar.clock_alignment import ClockProfile,ClockRecord,ContextStatus,build_alignment_ledger,resolve_parent
ROOT=Path(__file__).resolve().parents[2]; FIXTURE=ROOT/'fixtures/market_grammar/wp5/clock_alignment_cases.json'
def load(): return json.loads(FIXTURE.read_text(encoding='utf-8'))
class ClockAlignmentTests(unittest.TestCase):
 def test_fixture_valid_cases(self):
  fixture=load(); self.assertEqual('SYNTHETIC_NON_AUTHORITATIVE',fixture['authority']); self.assertEqual(4,len(fixture['valid_cases'])); self.assertEqual(3,len(fixture['invalid_cases']))
  for case in fixture['valid_cases']:
   result=resolve_parent(case['child'],case['parents']); expected=case['expected']; self.assertEqual(expected['status'],result.status.value); self.assertEqual(expected['parent_record_id'],result.parent_record_id); self.assertEqual(expected['parent_age_seconds'],result.parent_age_seconds)
   if result.parent_first_valid_time is not None: self.assertLessEqual(result.parent_first_valid_time,result.child_first_valid_time)
 def test_order_independent_ledger_and_future_parent_ignored(self):
  children=[{'record_id':'C1','source_release_id':'REL.TEST.v1','instrument_id':'GBPUSD','side':'BID','clock_id':'15M','first_valid_time':'2026-06-01T02:15:00Z'},{'record_id':'C2','source_release_id':'REL.TEST.v1','instrument_id':'GBPUSD','side':'BID','clock_id':'15M','first_valid_time':'2026-06-01T02:30:00Z'}]
  parents=[{'record_id':'P0','source_release_id':'REL.TEST.v1','instrument_id':'GBPUSD','side':'BID','clock_id':'2H_A_L','first_valid_time':'2026-06-01T02:00:00Z'},{'record_id':'PF','source_release_id':'REL.TEST.v1','instrument_id':'GBPUSD','side':'BID','clock_id':'2H_A_L','first_valid_time':'2026-06-01T04:00:00Z'}]
  a=build_alignment_ledger(children,parents); b=build_alignment_ledger(reversed(children),reversed(parents)); self.assertEqual(a.to_dict(),b.to_dict()); self.assertTrue(all(x.parent_record_id=='P0' for x in a.resolutions)); self.assertNotIn('/tmp',json.dumps(a.to_dict()))
 def test_cross_release_side_instrument_never_falls_back(self):
  child={'record_id':'C','source_release_id':'REL.TEST.v1','instrument_id':'GBPUSD','side':'BID','clock_id':'15M','first_valid_time':'2026-06-01T02:15:00Z'}
  parents=[{'record_id':'SIDE','source_release_id':'REL.TEST.v1','instrument_id':'GBPUSD','side':'ASK','clock_id':'2H_A_L','first_valid_time':'2026-06-01T02:00:00Z'},{'record_id':'REL','source_release_id':'REL.OTHER.v1','instrument_id':'GBPUSD','side':'BID','clock_id':'2H_A_L','first_valid_time':'2026-06-01T02:00:00Z'},{'record_id':'INST','source_release_id':'REL.TEST.v1','instrument_id':'EURUSD','side':'BID','clock_id':'2H_A_L','first_valid_time':'2026-06-01T02:00:00Z'}]
  result=resolve_parent(child,parents); self.assertEqual(ContextStatus.UNAVAILABLE,result.status); self.assertIsNone(result.parent_record_id); self.assertEqual('NO_EXACT_ASOF_PARENT',result.reason)
 def test_invalid_cases_fail_closed(self):
  base={'record_id':'C','source_release_id':'REL.TEST.v1','instrument_id':'GBPUSD','side':'BID','clock_id':'15M','first_valid_time':'2026-06-01T02:15:00Z'}; parent={'record_id':'P','source_release_id':'REL.TEST.v1','instrument_id':'GBPUSD','side':'BID','clock_id':'2H_A_L','first_valid_time':'2026-06-01T02:00:00Z'}
  with self.assertRaisesRegex(ValueError,'profile child clock'): resolve_parent({**base,'clock_id':'H1'},[parent])
  with self.assertRaisesRegex(ValueError,'duplicate parent record_id'): resolve_parent(base,[parent,{**parent,'first_valid_time':'2026-06-01T00:00:00Z'}])
  with self.assertRaisesRegex(ValueError,'ambiguous exact parent'): resolve_parent(base,[parent,{**parent,'record_id':'P2'}])
 def test_profile_is_frozen_noncanonical_and_parent_not_evaluable_explicit(self):
  profile=ClockProfile(); self.assertFalse(profile.canonical); self.assertEqual(7200,profile.max_parent_age_seconds)
  with self.assertRaisesRegex(ValueError,'cannot be canonical'): ClockProfile(canonical=True)
  child=ClockRecord.from_mapping({'record_id':'C','source_release_id':'REL.TEST.v1','instrument_id':'GBPUSD','side':'BID','clock_id':'15M','first_valid_time':'2026-06-01T02:15:00Z'}); parent=ClockRecord.from_mapping({'record_id':'P','source_release_id':'REL.TEST.v1','instrument_id':'GBPUSD','side':'BID','clock_id':'2H_A_L','first_valid_time':'2026-06-01T02:00:00Z','computability_status':'NOT_EVALUABLE','not_evaluable_reason':'MISSING_AXIS'}); result=resolve_parent(child,[parent]); self.assertEqual(ContextStatus.NOT_EVALUABLE,result.status); self.assertEqual('MISSING_AXIS',result.reason)
if __name__=='__main__': unittest.main()
