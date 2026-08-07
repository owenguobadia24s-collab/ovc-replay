"""Shadow-only market-grammar research namespace.

This package has no active market or selector authority, no canonical grammar,
no Validation or semantic-promotion authority, and no probability, risk,
exposure or execution authority.
"""
from .candidate_migration import CandidateMigration,build_feature_migration_registry,build_migration_artifacts,build_migration_ledger,classify_legacy_feature,map_typed_layer,migrate_candidate
from .clock_alignment import AlignmentLedger,ClockProfile,ClockRecord,ContextStatus,ParentResolution,build_alignment_ledger,resolve_parent
from .episode_ledger import BoundaryCause,C2LedgerInput,ComputabilityStatus,EpisodeBinding,EpisodeBindingRequest,EpisodeLedger,EpisodeRecord,EpisodeStatus,NestingRelation,NotEvaluableRecord,PhaseKind,PhaseRecord,build_episode_ledger,build_nesting_ledger
from .family_hierarchy import AssignmentRecord,AssignmentStatus,FamilyNode,HierarchyEdge,HierarchyLedger,HierarchyRelation,SensitivityPack,SensitivityResult,StructuralRecord,build_hierarchy,build_sensitivity_result,weighted_distance
from .family_variants import CounterexampleRecord,FamilyVariant,VariantAssignmentStatus,VariantExplanation,VariantLedger,build_variant_ledger
from .predicate_domains import ComponentClass,ComponentStats,ExclusivityRule,PredicateDomain,classify_component,infer_domain,migrate_legacy_component,validate_exclusivity_rule,validate_predicate_domain
from .topology_smoke import make_checkpoint,resume_topology_smoke,run_topology_smoke
from .typed_grammar import ASTNode,GrammarRelease,ParseResult,ParseStatus,compile_grammar,parse_grammar
__all__=['ASTNode','AlignmentLedger','AssignmentRecord','AssignmentStatus','BoundaryCause','C2LedgerInput','CandidateMigration','ClockProfile','ClockRecord','ComponentClass','ComponentStats','ComputabilityStatus','ContextStatus','CounterexampleRecord','EpisodeBinding','EpisodeBindingRequest','EpisodeLedger','EpisodeRecord','EpisodeStatus','ExclusivityRule','FamilyNode','FamilyVariant','GrammarRelease','HierarchyEdge','HierarchyLedger','HierarchyRelation','NestingRelation','NotEvaluableRecord','ParentResolution','ParseResult','ParseStatus','PhaseKind','PhaseRecord','PredicateDomain','SensitivityPack','SensitivityResult','StructuralRecord','VariantAssignmentStatus','VariantExplanation','VariantLedger','build_alignment_ledger','build_episode_ledger','build_hierarchy','build_feature_migration_registry','build_migration_artifacts','build_migration_ledger','build_nesting_ledger','build_sensitivity_result','build_variant_ledger','classify_component','classify_legacy_feature','compile_grammar','infer_domain','make_checkpoint','map_typed_layer','migrate_candidate','migrate_legacy_component','parse_grammar','resolve_parent','resume_topology_smoke','run_topology_smoke','validate_exclusivity_rule','validate_predicate_domain','weighted_distance']
