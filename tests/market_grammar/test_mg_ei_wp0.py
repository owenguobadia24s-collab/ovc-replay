from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / 'docs/plans/OVC_MARKET_GRAMMAR_EMPIRICAL_INTEGRATION_JUNE_IMPLEMENTATION_PLAN_v0_1.md'
CONTRACT = ROOT / 'contracts/opt_b/market_grammar/OVC_MG_EI_JUNE_AUTHORITY_AND_EVIDENCE_CONTRACT_v0_1.md'
BASE = ROOT / 'docs/releases/market-grammar-empirical-integration-june-v0-1/ei-wp0'
STATE = ROOT / 'registries/opt_b/market_grammar/OVC_MG_EI_JUNE_PROGRAMME_STATE_v0_1.jsonc'
ADMISSIONS = ROOT / 'registries/governance/programme_genesis/post_snapshot/PGN_POST_SNAPSHOT_PROGRAMME_ADMISSION_LEDGER_v0_1.json'
PARENT = ROOT / 'docs/releases/c2e-c2g-c2p-market-grammar-v0-1/mg-wp10/MG_WP10_OPERATOR_DECISION.json'

def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise AssertionError(f'not object: {path}')
    return value

class MarketGrammarEmpiricalIntegrationWp0Tests(unittest.TestCase):
    def test_plan_and_contract_are_materialised(self) -> None:
        self.assertTrue(PLAN.exists())
        self.assertTrue(CONTRACT.exists())
        plan = PLAN.read_text(encoding='utf-8')
        contract = CONTRACT.read_text(encoding='utf-8')
        self.assertIn('OVC-MARKET-GRAMMAR-EMPIRICAL-INTEGRATION-JUNE-v0.1', plan)
        self.assertIn('MG-WP10', plan)
        self.assertIn('SHADOW_EXPERIMENT', contract)
        for denied in ('selector', 'canonical', 'C3', 'publication', 'probability', 'risk', 'exposure', 'execution'):
            self.assertIn(denied.lower(), contract.lower())

    def test_parent_operator_pass_authorises_only_bounded_next_programme(self) -> None:
        parent = load(PARENT)
        self.assertEqual('PASS', parent['decision'])
        self.assertEqual('OPERATOR_EXPLICIT', parent['decision_authority'])
        nxt = parent['next_programme']
        self.assertEqual('OVC-MARKET-GRAMMAR-EMPIRICAL-INTEGRATION-JUNE-v0.1', nxt['programme_id'])
        self.assertIn('accepted June evidence', nxt['scope'])
        self.assertIn('canonical selection', nxt['stop_before'])
        self.assertIn('publication', nxt['stop_before'])

    def test_raw_source_preflight_reproduces_all_four_accepted_objects(self) -> None:
        preflight = load(BASE / 'EI_WP0_EVIDENCE_PREFLIGHT.json')
        self.assertEqual('PASS_RAW_SOURCE_REPRODUCIBLE', preflight['status'])
        self.assertEqual('READ_ONLY_RECOVERY_OF_ALREADY_ACCEPTED_EVIDENCE_NOT_PROVIDER_INTAKE', preflight['retrieval_class'])
        self.assertEqual(4, len(preflight['objects']))
        for item in preflight['objects']:
            self.assertEqual('PASS', item['result'])
            self.assertEqual(item['expected_bytes'], item['observed_bytes'])
            self.assertEqual(item['expected_sha256'], item['observed_sha256'])
        self.assertEqual('126a703b89bf8fc60a4beb1248b20b424621334c8fff254c122555e44663f8', preflight['accepted_binding']['binding_sha256'])
        self.assertEqual('3f1089e3a4eefe94147c8c2f912e77899e4ed21fe8b3b8b85993e47bf7151ee7', preflight['accepted_population']['logical_population_sha256'])
        self.assertEqual(33320, preflight['accepted_population']['counts']['requested'])

    def test_post_snapshot_admission_is_second_append_only_entry(self) -> None:
        ledger = load(ADMISSIONS)
        self.assertEqual('ACTIVE_APPEND_ONLY', ledger['status'])
        self.assertEqual(2, ledger['admission_count'])
        self.assertEqual(2, len(ledger['admissions']))
        first, second = ledger['admissions']
        self.assertEqual('PGN-POST-SNAPSHOT-MG-001', first['admission_id'])
        self.assertEqual('OVC-C2E-C2G-C2P-MARKET-GRAMMAR-REMEDIATION-v0.1', first['programme_id'])
        self.assertEqual('PGN-POST-SNAPSHOT-MG-EI-JUNE-002', second['admission_id'])
        self.assertEqual('OVC-MARKET-GRAMMAR-EMPIRICAL-INTEGRATION-JUNE-v0.1', second['programme_id'])
        self.assertEqual('NONE', second['frozen_snapshot_effect'])
        self.assertEqual('NONE', second['sealed_sixteen_candidate_population_effect'])
        self.assertEqual('NONE', second['authority']['selector_activation'])
        self.assertEqual('NONE', second['authority']['canonical_family_sensitivity_grammar'])
        frozen = ledger['frozen_snapshot']
        self.assertEqual(108, frozen['object_count'])
        self.assertEqual(72, frozen['exclusion_count'])
        self.assertEqual(16, frozen['candidate_portfolio_count'])
        self.assertEqual('PROHIBITED', frozen['mutation'])

    def test_programme_state_is_delegated_approved_and_routes_to_wp1(self) -> None:
        state = load(STATE)
        self.assertEqual('APPROVED', state['status'])
        self.assertEqual('SATISFIED_DELEGATED_DECISION', state['authority_required'])
        self.assertEqual([], state['blockers'])
        packets = {item['packet_id']: item for item in state['packets']}
        self.assertEqual('APPROVED', packets['EI-WP0']['status'])
        self.assertEqual('SATISFIED_DELEGATED_DECISION', packets['EI-WP0']['authority_required'])
        self.assertEqual('PLANNED', packets['EI-WP1']['status'])
        self.assertEqual('READ_ONLY_REAL_REVISED_C2_SHADOW_ADAPTER_ONLY', packets['EI-WP1']['authority_delta'])
        self.assertIn('OPERATOR_REQUIRED', packets['EI-WP4']['authority_required'])
        self.assertEqual('EI-WP0', state['next_packet'])

    def test_wp0_qa_and_delegated_decision_have_zero_reserved_delta(self) -> None:
        qa = load(BASE / 'EI_WP0_QA_PACKET.json')
        decision = load(BASE / 'EI_WP0_DELEGATED_DECISION.json')
        assurance = load(BASE / 'EI_WP0_PREDECISION_ASSURANCE.json')
        self.assertEqual('PASS', qa['status'])
        self.assertEqual([], qa['blockers'])
        self.assertEqual('PASS_ZERO', qa['checks']['new_provider_intake'])
        self.assertEqual('PASS_ZERO', qa['checks']['selector_or_canonical_controls'])
        self.assertEqual('PASS_ZERO', qa['checks']['promotion_publication_c3_active_authority'])
        self.assertEqual('PASS_ZERO', qa['checks']['probability_risk_exposure_execution'])
        self.assertEqual('PASS', decision['decision'])
        self.assertEqual('NONE', decision['reserved_authority_delta'])
        self.assertEqual('PASS_IMPLEMENTATION_HEAD', assurance['result'])
        self.assertEqual(0, assurance['checks']['unresolved_review_threads'])

if __name__ == '__main__':
    unittest.main()
