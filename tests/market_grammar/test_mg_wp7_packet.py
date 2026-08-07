from __future__ import annotations
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"docs/releases/c2e-c2g-c2p-market-grammar-v0-1/mg-wp7"
STATE=ROOT/"registries/opt_b/market_grammar/OVC_MARKET_GRAMMAR_PROGRAMME_STATE_v0_1.jsonc"
REG=ROOT/"registries/opt_b/market_grammar/MG_WP7_IMPLEMENTATION_REGISTRY_v0_1.json"
LEDGER=ROOT/"registries/opt_b/market_grammar/MG_CEAR_G10_MIGRATION_LEDGER_v0_1.json"
FEATURES=ROOT/"registries/opt_b/market_grammar/MG_CEAR_G10_TYPED_FEATURE_MIGRATION_REGISTRY_v0_1.json"
SCHEMAS=ROOT/"schemas/opt_b/market_grammar"
def load(path): return json.loads(path.read_text(encoding="utf-8"))
class MarketGrammarWp7PacketTests(unittest.TestCase):
 def test_completed_packet_preserves_inactive_noncanonical_boundary(self):
  reg=load(REG); ledger=load(LEDGER); features=load(FEATURES); qa=load(BASE/"MG_WP7_QA_PACKET.json"); manifest=load(BASE/"MG_WP7_IMPLEMENTATION_MANIFEST.json"); decision=load(BASE/"MG_WP7_DELEGATED_DECISION.json")
  self.assertEqual(14,reg["candidate_count"]); self.assertEqual({"MAPPED":14},ledger["migration_status_counts"]); self.assertFalse(ledger["canonical"]); self.assertEqual("NONE",ledger["promotion_authority"]); self.assertEqual(ledger["feature_registry_sha256"],features["registry_sha256"]); self.assertFalse(features["canonical"]); self.assertFalse(reg["candidate_promotion"]); self.assertFalse(reg["canonical_grammar"]); self.assertEqual("PASS",qa["status"]); self.assertEqual([],qa["blockers"]); self.assertEqual("COMPLETED",manifest["status"]); self.assertEqual("PASS",decision["decision"]); self.assertEqual("NONE",decision["reserved_authority_delta"])
 def test_c2_candidate_migration_schemas_are_closed(self):
  for name in ("c2_candidate_migration_v0_1.schema.json","c2_candidate_migration_ledger_v0_1.schema.json","c2_candidate_feature_migration_registry_v0_1.schema.json"):
   schema=load(SCHEMAS/name); self.assertFalse(schema["additionalProperties"]); self.assertEqual("https://json-schema.org/draft/2020-12/schema",schema["$schema"])
 def test_state_completes_wp7_and_unlocks_only_wp8(self):
  state=load(STATE); packets={x["packet_id"]:x for x in state["packets"]}; self.assertEqual("COMPLETED",packets["MG-WP7"]["status"]); self.assertEqual("SATISFIED_DELEGATED_DECISION",packets["MG-WP7"]["authority_required"]); self.assertEqual("READY",packets["MG-WP8"]["status"]); self.assertEqual("PLANNED",packets["MG-WP9"]["status"]); self.assertEqual("OPERATOR_REQUIRED",packets["MG-WP10"]["authority_required"]); self.assertEqual("MG-WP8",state["next_packet"]); self.assertNotIn(state["status"],{"BLOCKED","QUARANTINED"})
if __name__=="__main__": unittest.main()
