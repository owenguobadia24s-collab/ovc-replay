from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
EXPECTED_TOP_LEVEL = {"ovc", "ovc_evidence_store"}
EXPECTED_OVC_PACKAGES = {
    "ovc",
    "ovc.console_vnext",
    "ovc.console_vnext.adapters",
    "ovc.console_vnext.application",
    "ovc.context",
    "ovc.context.occurrence_context",
    "ovc.development",
    "ovc.development.skills",
    "ovc.development.skills.cers",
    "ovc.opt_a",
    "ovc.opt_b",
    "ovc.opt_b.c1",
    "ovc.opt_b.c2",
    "ovc.opt_b.c2_vnext",
    "ovc.opt_b.c2e_v2",
    "ovc.opt_b.c2p_v0_2",
    "ovc.opt_b.esl",
    "ovc.opt_b.market_grammar",
    "ovc.opt_b.sfc",
    "ovc.opt_b.srfd",
    "ovc.programme_genesis",
    "ovc.programme_genesis.grt_v0_2",
    "ovc.research_operations",
    "ovc.research_operations.asocs",
    "ovc.research_operations.c2_csm_reference",
    "ovc.research_operations.p1cdi",
    "ovc.research_operations.prsc",
    "ovc.research_operations.rccr",
    "ovc.research_operations.p2cti",
    "ovc.research_operations.sff",
    "ovc.research_operations.v0_2",
    "ovc.research_operations.v0_3",
    "ovc.research_operations.v0_4",
    "ovc.research_operations.pattern_discovery",
    "ovc.research_operations.mta",
    "ovc.research_operations.mcarb",
    "ovc.research_orchestration",
    "ovc.shared_systems",
    "ovc.system_atlas",
}


class ActiveNamespaceAllowlistTests(unittest.TestCase):
    def test_top_level_source_namespaces_match_allowlist(self) -> None:
        actual = {
            path.name
            for path in SRC.iterdir()
            if path.is_dir() and (path / "__init__.py").is_file()
        }
        self.assertEqual(EXPECTED_TOP_LEVEL, actual)

    def test_system_atlas_namespace_is_inactive_read_only_observability_only(self) -> None:
        init_text = (SRC / "ovc" / "system_atlas" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("inactive read-only observability", init_text)
        self.assertIn("no active observability reliance", init_text)
        self.assertIn("source admission", init_text)
        self.assertIn("write", init_text)
        self.assertIn("validation", init_text)
        self.assertIn("scientific semantics", init_text)
        self.assertIn("publication", init_text)
        self.assertIn("execution authority", init_text)
        self.assertIn("fails closed", init_text)

    def test_shared_systems_namespace_is_inactive_reference_only(self) -> None:
        init_text = (SRC / "ovc" / "shared_systems" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("inactive/reference implementation only", init_text)
        self.assertIn("does not activate a shared systems runtime", init_text)
        self.assertIn("replace or restrict any current consumer", init_text)
        self.assertIn("new source/provider/research role", init_text)
        self.assertIn("scientific or semantic", init_text)
        self.assertIn("validation", init_text)
        self.assertIn("publish canon/r2", init_text)
        self.assertIn("probability", init_text)
        self.assertIn("risk", init_text)
        self.assertIn("exposure", init_text)
        self.assertIn("execution", init_text)
        self.assertIn("agent-write authority", init_text)
        self.assertIn("fails closed", init_text)

    def test_ovc_package_names_match_foundation_allowlist(self) -> None:
        package_root = SRC / "ovc"
        actual = {
            ".".join(path.parent.relative_to(SRC).parts)
            for path in package_root.rglob("__init__.py")
        }
        self.assertEqual(EXPECTED_OVC_PACKAGES, actual)

    def test_p1cdi_namespace_is_advisory_non_decision_bearing_conformance_only(self) -> None:
        init_text = (SRC / "ovc" / "research_operations" / "p1cdi" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("advisory", init_text)
        self.assertIn("non-decision-bearing", init_text)
        self.assertIn("p1cdii-g2-alg", init_text)
        self.assertIn("no owner-scientific", init_text)
        self.assertIn("candidate", init_text)
        self.assertIn("validation", init_text)
        self.assertIn("actuation authority", init_text)

    def test_c2_csm_reference_namespace_is_historical_conformance_only(self) -> None:
        init_text = (
            SRC / "ovc" / "research_operations" / "c2_csm_reference" / "__init__.py"
        ).read_text(encoding="utf-8").lower()
        self.assertIn("historical", init_text)
        self.assertIn("reference conformance only", init_text)
        self.assertIn("no current c2", init_text)
        self.assertIn("owner authority", init_text)
        self.assertIn("protected source", init_text)
        self.assertIn("validation", init_text)
        self.assertIn("publish", init_text)
        self.assertIn("probability", init_text)
        self.assertIn("risk", init_text)
        self.assertIn("exposure", init_text)
        self.assertIn("trading", init_text)
        self.assertIn("execution", init_text)
        self.assertIn("agent-write authority", init_text)
        self.assertIn("fail closed", init_text)

    def test_sff_namespace_is_synthetic_conformance_only(self) -> None:
        init_text = (SRC / "ovc" / "research_operations" / "sff" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("synthetic", init_text)
        self.assertIn("conformance only", init_text)
        self.assertIn("no real-source", init_text)
        self.assertIn("target activation", init_text)
        self.assertIn("validation", init_text)
        self.assertIn("opt-f", init_text)
        self.assertIn("probability-as-exposure", init_text)
        self.assertIn("risk", init_text)
        self.assertIn("trading", init_text)
        self.assertIn("execution", init_text)
        self.assertIn("agent-write authority", init_text)
        self.assertIn("fails closed", init_text)

    def test_console_vnext_namespace_is_local_read_only_application_only(self) -> None:
        init_text = (SRC / "ovc" / "console_vnext" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("local read-only application only", init_text)
        self.assertIn("no active market", init_text)
        self.assertIn("selector", init_text)
        self.assertIn("validation", init_text)
        self.assertIn("publication", init_text)
        self.assertIn("execution authority", init_text)
        self.assertIn("agent-write authority", init_text)
        self.assertIn("fail closed", init_text)

    def test_occurrence_context_namespace_is_active_nonstructural_foundation_only(self) -> None:
        context_init = (SRC / "ovc" / "context" / "__init__.py").read_text(encoding="utf-8").lower()
        occurrence_init = (SRC / "ovc" / "context" / "occurrence_context" / "__init__.py").read_text(encoding="utf-8").lower()
        combined = context_init + occurrence_init
        self.assertIn("active-foundation", combined)
        self.assertIn("non-structural", combined)
        self.assertIn("no structural", combined)
        self.assertIn("representation input remains denied", combined)
        self.assertIn("validation", combined)
        self.assertIn("c2p", combined)
        self.assertIn("execution", combined)

    def test_c2_vnext_namespace_exposes_active_core_and_shadow_research_boundary(self) -> None:
        init_text = (SRC / "ovc" / "opt_b" / "c2_vnext" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("active-core", init_text)
        self.assertIn("functional discovery", init_text)
        self.assertIn("candidate dispositions", init_text)
        self.assertIn("remain shadow", init_text)
        self.assertIn("selector replacement", init_text)
        self.assertIn("validation", init_text)
        self.assertIn("execution", init_text)

    def test_c2e_v2_namespace_exposes_active_engine_without_self_granting_reserved_changes(self) -> None:
        init_text = (SRC / "ovc" / "opt_b" / "c2e_v2" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("active-engine", init_text)
        self.assertIn("operator-selected", init_text)
        self.assertIn("exact june population", init_text)
        self.assertIn("no longer activation identities", init_text)
        self.assertIn("replace the boundary pack", init_text)
        self.assertIn("validation", init_text)
        self.assertIn("execution", init_text)

    def test_c2p_v0_2_namespace_is_inactive_conformance_only(self) -> None:
        init_text = (SRC / "ovc" / "opt_b" / "c2p_v0_2" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("inactive", init_text)
        self.assertIn("conformance-only", init_text)
        self.assertIn("no active market", init_text)
        self.assertIn("selector", init_text)
        self.assertIn("empirical objectpack", init_text)
        self.assertIn("real-source replay", init_text)
        self.assertIn("validation", init_text)
        self.assertIn("publication", init_text)
        self.assertIn("execution authority", init_text)
        self.assertIn("agent-write", init_text)
        self.assertIn("fail closed", init_text)

    def test_esl_namespace_is_inactive_conformance_only(self) -> None:
        init_text = (SRC / "ovc" / "opt_b" / "esl" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("inactive", init_text)
        self.assertIn("conformance-only", init_text)
        self.assertIn("no active market", init_text)
        self.assertIn("selector", init_text)
        self.assertIn("canonical representation", init_text)
        self.assertIn("family", init_text)
        self.assertIn("semantic-promotion", init_text)
        self.assertIn("validation", init_text)
        self.assertIn("execution authority", init_text)
        self.assertIn("agent-write authority", init_text)
        self.assertIn("fails closed", init_text)

    def test_market_grammar_namespace_is_shadow_only(self) -> None:
        init_text = (SRC / "ovc" / "opt_b" / "market_grammar" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("shadow-only", init_text)
        self.assertIn("no active market", init_text)
        self.assertIn("selector", init_text)
        self.assertIn("canonical grammar", init_text)
        self.assertIn("validation", init_text)
        self.assertIn("semantic-promotion", init_text)
        self.assertIn("execution authority", init_text)

    def test_sfc_namespace_is_inactive_shadow_conformance_only(self) -> None:
        init_text = (SRC / "ovc" / "opt_b" / "sfc" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("inactive", init_text)
        self.assertIn("shadow-only", init_text)
        self.assertIn("no active market", init_text)
        self.assertIn("selector", init_text)
        self.assertIn("canonical representation", init_text)
        self.assertIn("family", init_text)
        self.assertIn("validation", init_text)
        self.assertIn("semantic-promotion", init_text)
        self.assertIn("execution authority", init_text)

    def test_srfd_namespace_is_fixture_shadow_only(self) -> None:
        init_text = (SRC / "ovc" / "opt_b" / "srfd" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("shadow-only", init_text)
        self.assertIn("no active market", init_text)
        self.assertIn("selector", init_text)
        self.assertIn("canonical representation", init_text)
        self.assertIn("family", init_text)
        self.assertIn("validation", init_text)
        self.assertIn("semantic-promotion", init_text)
        self.assertIn("execution authority", init_text)

    def test_mta_namespace_is_audit_only(self) -> None:
        init_text = (SRC / "ovc" / "research_operations" / "mta" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("no market", init_text)
        self.assertIn("selector", init_text)
        self.assertIn("semantic-promotion", init_text)
        self.assertIn("execution authority", init_text)

    def test_mcarb_namespace_is_research_only(self) -> None:
        init_text = (SRC / "ovc" / "research_operations" / "mcarb" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("research-only", init_text)
        self.assertIn("no market", init_text)
        self.assertIn("selector", init_text)
        self.assertIn("validation", init_text)
        self.assertIn("semantic-promotion", init_text)
        self.assertIn("execution authority", init_text)

    def test_prsc_namespace_is_research_only_and_non_authoritative(self) -> None:
        init_text = (SRC / "ovc" / "research_operations" / "prsc" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("research-only", init_text)
        self.assertIn("non-authoritative", init_text)
        self.assertIn("no market", init_text)
        self.assertIn("selector", init_text)
        self.assertIn("candidate-freeze", init_text)
        self.assertIn("activation authority", init_text)
        self.assertIn("validation", init_text)
        self.assertIn("publication", init_text)
        self.assertIn("probability", init_text)
        self.assertIn("risk", init_text)
        self.assertIn("exposure", init_text)
        self.assertIn("execution authority", init_text)
        self.assertIn("agent-write authority", init_text)
        self.assertIn("real-source", init_text)
        self.assertIn("fails closed", init_text)

    def test_rccr_namespace_is_research_only_non_authoritative_synthesis(self) -> None:
        init_text = (SRC / "ovc" / "research_operations" / "rccr" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("research-only", init_text)
        self.assertIn("non-authoritative synthesis", init_text)
        self.assertIn("no market", init_text)
        self.assertIn("selector", init_text)
        self.assertIn("activation", init_text)
        self.assertIn("validation", init_text)
        self.assertIn("publication", init_text)
        self.assertIn("execution authority", init_text)
        self.assertIn("agent-write authority", init_text)
        self.assertIn("fail closed", init_text)

    def test_programme_genesis_namespace_is_governance_only(self) -> None:
        init_text = (SRC / "ovc" / "programme_genesis" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("governance-only", init_text)
        self.assertIn("no market", init_text)
        self.assertIn("selector", init_text)
        self.assertIn("execution authority", init_text)

    def test_grt_v0_2_namespace_is_read_only_and_non_enforcing(self) -> None:
        init_text = (SRC / "ovc" / "programme_genesis" / "grt_v0_2" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("repository-conformance", init_text)
        self.assertIn("non-enforcing", init_text)
        self.assertIn("operator decisions", init_text)
        self.assertIn("read-only exact-source reconciliation only", init_text)


if __name__ == "__main__":
    unittest.main()
