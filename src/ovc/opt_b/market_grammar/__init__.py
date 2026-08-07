"""Shadow-only market-grammar research namespace.

This package has no active market or selector authority, no canonical grammar,
no Validation or semantic-promotion authority, and no probability, risk,
exposure or execution authority.
"""
from .episode_ledger import BoundaryCause,C2LedgerInput,ComputabilityStatus,EpisodeBinding,EpisodeBindingRequest,EpisodeLedger,EpisodeRecord,EpisodeStatus,NestingRelation,NotEvaluableRecord,PhaseKind,PhaseRecord,build_episode_ledger,build_nesting_ledger
from .family_hierarchy import AssignmentRecord,AssignmentStatus,FamilyNode,HierarchyEdge,HierarchyLedger,HierarchyRelation,SensitivityPack,SensitivityResult,StructuralRecord,build_hierarchy,build_sensitivity_result,weighted_distance
from .family_variants import CounterexampleRecord,FamilyVariant,VariantAssignmentStatus,VariantExplanation,VariantLedger,build_variant_ledger
from .predicate_domains import ComponentClass,ComponentStats,ExclusivityRule,PredicateDomain,classify_component,infer_domain,migrate_legacy_component,validate_exclusivity_rule,validate_predicate_domain
__all__=['AssignmentRecord','AssignmentStatus','BoundaryCause','C2LedgerInput','ComponentClass','ComponentStats','ComputabilityStatus','CounterexampleRecord','EpisodeBinding','EpisodeBindingRequest','EpisodeLedger','EpisodeRecord','EpisodeStatus','ExclusivityRule','FamilyNode','FamilyVariant','HierarchyEdge','HierarchyLedger','HierarchyRelation','NestingRelation','NotEvaluableRecord','PhaseKind','PhaseRecord','PredicateDomain','SensitivityPack','SensitivityResult','StructuralRecord','VariantAssignmentStatus','VariantExplanation','VariantLedger','build_episode_ledger','build_hierarchy','build_nesting_ledger','build_sensitivity_result','build_variant_ledger','classify_component','infer_domain','migrate_legacy_component','validate_exclusivity_rule','validate_predicate_domain','weighted_distance']
