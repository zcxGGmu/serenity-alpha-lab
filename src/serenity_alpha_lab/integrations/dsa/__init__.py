"""Compatibility entry points for the isolated DSA upstream worktree."""

from serenity_alpha_lab.integrations.dsa.provider_adapter import (
    DSA_DAILY_BAR_SCHEMA_NAME,
    DSA_DAILY_BAR_SCHEMA_VERSION,
    DSA_PROVIDER_ID,
    DsaProviderCompatibilityAdapter,
    DsaStockHistoryCompatibilityFacade,
    create_default_dsa_data_fetcher_manager,
)
from serenity_alpha_lab.integrations.dsa.symbol_compatibility import (
    DsaStockCodeCompatibilityMapper,
    DsaStockCodeMapping,
    normalize_stock_code_compatible,
)
from serenity_alpha_lab.integrations.dsa.research_orchestrator import (
    DsaResearchOrchestratorFacade,
    research_result_from_legacy_agent_result,
)
from serenity_alpha_lab.integrations.dsa.task_backend import DsaAnalysisTaskQueueBackend

__all__ = [
    "DSA_DAILY_BAR_SCHEMA_NAME",
    "DSA_DAILY_BAR_SCHEMA_VERSION",
    "DSA_PROVIDER_ID",
    "DsaAnalysisTaskQueueBackend",
    "DsaProviderCompatibilityAdapter",
    "DsaResearchOrchestratorFacade",
    "DsaStockCodeCompatibilityMapper",
    "DsaStockCodeMapping",
    "DsaStockHistoryCompatibilityFacade",
    "create_default_dsa_data_fetcher_manager",
    "normalize_stock_code_compatible",
    "research_result_from_legacy_agent_result",
]
