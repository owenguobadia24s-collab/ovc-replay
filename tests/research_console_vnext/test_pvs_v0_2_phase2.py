from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[2]
PROD = ROOT / "apps" / "research_console_vnext" / "src" / "production"


class PvsV02Phase2Conformance(unittest.TestCase):
    def test_repository_handoff_is_current_and_non_authoritative(self):
        handoff = json.loads((ROOT / "design" / "research_console" / "figma" / "RCN_Production_Visual_System_Handoff_v0_2.json").read_text())
        self.assertEqual(handoff["schema"], "ovc-rcn-figma-production-handoff/v2")
        self.assertEqual(handoff["figma"]["file_key"], "NUHzyFiLHRuDWOC0hBVYzc")
        self.assertEqual(handoff["figma"]["canonical_manifest"], "269:2")
        self.assertEqual(handoff["figma"]["react_handoff"], "269:705")
        self.assertEqual(handoff["figma"]["counts"]["component_sets"], 93)
        self.assertEqual(handoff["figma"]["counts"]["production_masters"], 35)
        self.assertEqual(handoff["authority_effect"], "NONE")
        self.assertEqual(handoff["transport"], "GET_ONLY")
        self.assertEqual(handoff["mutations"], "DENIED")
        self.assertEqual(handoff["real_source_routes"], "DENIED_UNTIL_RCN_RN_G4")
        self.assertFalse(handoff["wp4d_isolation"]["phase2_may_modify"])

    def test_shell_implements_exact_figma_bindings_and_trust_spine(self):
        shell = (PROD / "PvsShell.tsx").read_text()
        for name, node in {
            "GlobalDomainRail":"44:159", "ApplicationHeader":"46:213", "ContextAuthorityStrip":"47:292",
            "WorkbenchNavigator":"49:338", "EvidenceInspector":"64:277", "EvidenceDock":"65:71", "StatusBar":"50:316",
        }.items():
            self.assertIn(f"function {name}", shell)
            self.assertIn(node, shell)
        for marker in ["SYNTHETIC_FIXTURE", "NON-EVIDENTIARY", "AVAILABLE", "AUTHORISED", "ACTIVE", "AUTHORITY EFFECT", "FVT", "MISSINGNESS", "DENOMINATOR"]:
            self.assertIn(marker, shell)
        self.assertNotIn("fetch(", shell)
        self.assertNotIn("localStorage", shell)
        self.assertNotIn("sessionStorage", shell)

    def test_core_component_layer_materialises_new_control_and_data_contracts(self):
        primitives = (PROD / "PvsPrimitives.tsx").read_text()
        data = (PROD / "PvsData.tsx").read_text()
        for component, node in {
            "ObjectBadge":"22:45", "TypedObjectLink":"21:29", "StatusBadge":"20:77", "AuthorityTriadView":"23:85",
            "DegradedState":"91:221", "IconButton":"24:125", "SearchField":"29:165", "SelectField":"30:175",
            "FilterChip":"31:219", "SegmentedControl":"34:197", "DensityControl":"34:197",
        }.items():
            self.assertIn(f"function {component}", primitives)
            self.assertIn(node, primitives)
        for component, node in {"DataCell":"66:37", "DataTable":"69:805", "LedgerRow":"72:793", "DenominatorFooter":"73:665", "VirtualisationMarker":"74:665"}.items():
            self.assertIn(f"function {component}", data)
            self.assertIn(node, data)
        for marker in ["CAPACITY_EXCEEDED", "no silent sampling", "unrendered ≠ missing", "denominator unchanged"]:
            self.assertIn(marker, data)

    def test_semantic_risk_instruments_are_production_owned_and_fail_honest(self):
        source = (PROD / "PvsSemanticInstruments.tsx").read_text()
        for component, node in {"MatrixView":"70:736", "ProofTimeline":"89:325", "AstRenderer":"90:416", "BoundedGraph":"81:525"}.items():
            self.assertIn(f"function {component}", source)
            self.assertIn(node, source)
        for marker in [
            "no composite winner", "definition ≠ proof", "bindings before truth", "effective ≠ FVT",
            "PENDING remains open", "CENSORED ≠ TERMINATED", "one authoritative AST", "display_projection=true",
            "connectivity ≠ entailment", "sourcePort", "targetPort", "direction", "No silent sampling",
        ]:
            self.assertIn(marker, source)
        self.assertNotIn("Math.random", source)
        self.assertNotIn("fetch(", source)

    def test_all_thirty_esl_r3_r8_component_contracts_are_materialised(self):
        source = (PROD / "PvsEsl.tsx").read_text()
        expected = {
            "EpistemicPlaneTab":"202:40", "EvidenceStateBadge":"203:44", "TopologyCard":"204:26", "EvidenceFrontierRow":"205:32", "QualificationRow":"206:26",
            "WorkflowStep":"224:32", "EvidenceActionRow":"225:32", "CompareScopeReceipt":"226:47", "GovernedActionBoundary":"227:32",
            "ExecutionProfileCard":"239:22", "ProfileAvailabilityState":"239:35", "MarginalEvidenceLedgerRow":"239:56", "CapacityDeltaRow":"239:77",
            "ResearchModeLane":"244:10", "LanguageCandidateBindingCard":"244:31", "QualificationDimensionRow":"244:62", "SemanticAuthorityStage":"244:75", "C3BridgeMaturityState":"244:88",
            "TheoryStatusCard":"249:60", "ExperimentLifecycleCard":"249:89", "EvidenceBalanceRow":"249:115", "HealthDomainSignal":"249:140", "AgentCapabilityState":"249:165", "EHReadinessState":"249:190",
            "AssuranceAssertionCard":"259:52", "AdversarialCaseRow":"259:78", "ViewportAssuranceCard":"259:94", "CapacityBudgetRow":"259:120", "RollbackReceiptCard":"259:141", "AcceptanceCriterionState":"259:162",
        }
        self.assertEqual(len(expected), 30)
        for component, node in expected.items():
            self.assertIn(f"function {component}", source)
            self.assertIn(node, source)
        for marker in [
            "Structure", "Organisation", "Constraint", "Mechanism", "NOT_EVALUABLE", "NULL", "authority_effect=NONE",
            "no aggregate score", "Path 1", "Path 2", "ACTIVE_SEMANTIC_ADMISSION", "technical maturity",
            "support + contradiction", "never self-approving", "NOT EXPOSURE AUTHORITY", "no silent sampling",
            "operator acceptance distinct from assurance PASS",
        ]:
            self.assertIn(marker, source)

    def test_phase2_does_not_create_write_or_real_source_surface(self):
        text = "\n".join(path.read_text() for path in PROD.glob("Pvs*.tsx"))
        for forbidden in ["fetch(", "axios", "useMutation", "localStorage", "sessionStorage"]:
            self.assertNotIn(forbidden, text)
        self.assertNotIn('method:"POST"', text)
        self.assertNotIn('method:"PUT"', text)
        self.assertNotIn('method:"PATCH"', text)
        self.assertNotIn('method:"DELETE"', text)


if __name__ == "__main__":
    unittest.main()
