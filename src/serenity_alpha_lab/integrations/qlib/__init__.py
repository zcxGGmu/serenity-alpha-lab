"""Qlib integration boundary.

SAL-P4-005 freezes dependency/isolation policy and SAL-P4-006 adds the
offline Dataset conversion boundary. The adapter and runtime initialization
are introduced by later P4 tasks.
"""

from serenity_alpha_lab.integrations.qlib.runtime_policy import (
    QLIB_PACKAGE_NAME,
    QLIB_PACKAGE_VERSION,
    QLIB_RUNTIME_SCOPE,
    QlibRuntimeIsolationPolicy,
    default_qlib_runtime_policy,
)
from serenity_alpha_lab.integrations.qlib.dataset_converter import (
    QLIB_CALENDAR_SCHEMA_NAME,
    QLIB_DATASET_CONVERSION_SCHEMA_NAME,
    QLIB_FEATURE_SCHEMA_NAME,
    QLIB_FIELD_MAPPING_SCHEMA_NAME,
    QLIB_INSTRUMENT_SCHEMA_NAME,
    QlibConvertedDatasetBundle,
    QlibDatasetConversionArtifacts,
    QlibDatasetConversionError,
    QlibDatasetConversionSpec,
    QlibFeatureRecord,
    QlibFieldMapping,
    QlibFieldMappingDirection,
    QlibInstrumentRecord,
    convert_datasets_to_qlib,
)
from serenity_alpha_lab.integrations.qlib.quant_engine_adapter import (
    QLIB_QUANT_ENGINE_ADAPTER_SCOPE,
    QLIB_QUANT_ENGINE_ADAPTER_VERSION,
    QLIB_QUANT_ENGINE_RUN_REPORT_SCHEMA_NAME,
    QLIB_QUANT_ENGINE_STEP_SCHEMA_NAME,
    LazyQlibQuantEngineFacade,
    QlibQuantEngineAdapter,
    QlibQuantEngineConfig,
    QlibQuantEngineError,
    QlibQuantEngineFacade,
    QlibQuantEngineOperation,
    QlibQuantEngineRequest,
    QlibQuantEngineRunReport,
    QlibQuantEngineStepResult,
    QlibQuantEngineTemplate,
    QlibRecorderSnapshot,
)

__all__ = [
    "QLIB_CALENDAR_SCHEMA_NAME",
    "QLIB_DATASET_CONVERSION_SCHEMA_NAME",
    "QLIB_FEATURE_SCHEMA_NAME",
    "QLIB_FIELD_MAPPING_SCHEMA_NAME",
    "QLIB_INSTRUMENT_SCHEMA_NAME",
    "QLIB_PACKAGE_NAME",
    "QLIB_PACKAGE_VERSION",
    "QLIB_QUANT_ENGINE_ADAPTER_SCOPE",
    "QLIB_QUANT_ENGINE_ADAPTER_VERSION",
    "QLIB_QUANT_ENGINE_RUN_REPORT_SCHEMA_NAME",
    "QLIB_QUANT_ENGINE_STEP_SCHEMA_NAME",
    "QLIB_RUNTIME_SCOPE",
    "LazyQlibQuantEngineFacade",
    "QlibConvertedDatasetBundle",
    "QlibDatasetConversionArtifacts",
    "QlibDatasetConversionError",
    "QlibDatasetConversionSpec",
    "QlibFeatureRecord",
    "QlibFieldMapping",
    "QlibFieldMappingDirection",
    "QlibInstrumentRecord",
    "QlibQuantEngineAdapter",
    "QlibQuantEngineConfig",
    "QlibQuantEngineError",
    "QlibQuantEngineFacade",
    "QlibQuantEngineOperation",
    "QlibQuantEngineRequest",
    "QlibQuantEngineRunReport",
    "QlibQuantEngineStepResult",
    "QlibQuantEngineTemplate",
    "QlibRecorderSnapshot",
    "QlibRuntimeIsolationPolicy",
    "convert_datasets_to_qlib",
    "default_qlib_runtime_policy",
]
