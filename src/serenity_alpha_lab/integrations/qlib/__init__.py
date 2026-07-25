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

__all__ = [
    "QLIB_CALENDAR_SCHEMA_NAME",
    "QLIB_DATASET_CONVERSION_SCHEMA_NAME",
    "QLIB_FEATURE_SCHEMA_NAME",
    "QLIB_FIELD_MAPPING_SCHEMA_NAME",
    "QLIB_INSTRUMENT_SCHEMA_NAME",
    "QLIB_PACKAGE_NAME",
    "QLIB_PACKAGE_VERSION",
    "QLIB_RUNTIME_SCOPE",
    "QlibConvertedDatasetBundle",
    "QlibDatasetConversionArtifacts",
    "QlibDatasetConversionError",
    "QlibDatasetConversionSpec",
    "QlibFeatureRecord",
    "QlibFieldMapping",
    "QlibFieldMappingDirection",
    "QlibInstrumentRecord",
    "QlibRuntimeIsolationPolicy",
    "convert_datasets_to_qlib",
    "default_qlib_runtime_policy",
]
