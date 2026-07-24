from __future__ import annotations

import ast
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite
from types import MappingProxyType
from typing import Any

from serenity_alpha_lab.quant.factors.definitions import FactorDefinition, FactorInput, FactorWindow


FACTOR_DSL_ENGINE_VERSION = "serenity_factor_dsl@1.0.0"
FACTOR_DSL_SCHEMA_NAME = "quant.factor_dsl_plan"
FACTOR_DSL_SCHEMA_VERSION = "1.0.0"


class FactorDslError(ValueError):
    """Raised when a factor DSL expression cannot be safely parsed or compiled."""


class FactorDslValueType(StrEnum):
    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    STRING = "string"


@dataclass(frozen=True, slots=True)
class FactorExpressionNode:
    operation: str
    value_type: FactorDslValueType | str
    children: Sequence[FactorExpressionNode] = ()
    value: float | str | bool | None = None
    parameters: Mapping[str, Any] = field(default_factory=dict)
    source: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "operation", _required_string("operation", self.operation))
        object.__setattr__(self, "value_type", FactorDslValueType(self.value_type))
        children = tuple(self.children)
        for child in children:
            if type(child) is not FactorExpressionNode:
                raise FactorDslError("children must contain FactorExpressionNode values")
        object.__setattr__(self, "children", children)
        object.__setattr__(self, "parameters", _freeze_mapping(self.parameters))
        object.__setattr__(self, "source", _optional_string(self.source))

    def to_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "operation": self.operation,
            "value_type": self.value_type.value,
        }
        if self.value is not None:
            record["value"] = self.value
        if self.parameters:
            record["parameters"] = _thaw_value(self.parameters)
        if self.children:
            record["children"] = [child.to_record() for child in self.children]
        if self.source is not None:
            record["source"] = self.source
        return record


@dataclass(frozen=True, slots=True)
class FactorExpressionPlan:
    expression: str
    node: FactorExpressionNode
    required_inputs: Sequence[str]
    required_operators: Sequence[str]
    lookback_periods: int
    dataset_versions: Mapping[str, str] = field(default_factory=dict)
    definition_id: str | None = None
    semantic_version: str | None = None
    engine_version: str = FACTOR_DSL_ENGINE_VERSION
    schema_name: str = FACTOR_DSL_SCHEMA_NAME
    schema_version: str = FACTOR_DSL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "expression", _required_string("expression", self.expression))
        if type(self.node) is not FactorExpressionNode:
            raise FactorDslError("node must be a FactorExpressionNode")
        object.__setattr__(self, "required_inputs", _string_tuple("required input", self.required_inputs))
        object.__setattr__(self, "required_operators", _string_tuple("required operator", self.required_operators))
        if type(self.lookback_periods) is not int or self.lookback_periods < 0:
            raise FactorDslError("lookback_periods must be a non-negative integer")
        object.__setattr__(self, "dataset_versions", _freeze_string_mapping(self.dataset_versions))
        object.__setattr__(self, "definition_id", _optional_string(self.definition_id))
        object.__setattr__(self, "semantic_version", _optional_string(self.semantic_version))
        object.__setattr__(self, "engine_version", _required_string("engine_version", self.engine_version))
        object.__setattr__(self, "schema_name", _required_string("schema_name", self.schema_name))
        object.__setattr__(self, "schema_version", _required_string("schema_version", self.schema_version))

    def to_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "engine_version": self.engine_version,
            "expression": self.expression,
            "required_inputs": list(self.required_inputs),
            "required_operators": list(self.required_operators),
            "lookback_periods": self.lookback_periods,
            "dataset_versions": dict(self.dataset_versions),
            "node": self.node.to_record(),
        }
        if self.definition_id is not None:
            record["definition_id"] = self.definition_id
        if self.semantic_version is not None:
            record["semantic_version"] = self.semantic_version
        return record


@dataclass(frozen=True, slots=True)
class _CompiledNode:
    node: FactorExpressionNode
    required_inputs: frozenset[str]
    required_operators: frozenset[str]
    lookback_periods: int


@dataclass(frozen=True, slots=True)
class _CompileContext:
    inputs_by_id: Mapping[str, FactorInput]
    declared_window_lengths: frozenset[int]


_BINARY_OPERATIONS: dict[type[ast.operator], str] = {
    ast.Add: "add",
    ast.Sub: "sub",
    ast.Mult: "mul",
    ast.Div: "guarded_divide",
}

_COMPARISON_OPERATIONS: dict[type[ast.cmpop], str] = {
    ast.Gt: "comparison.gt",
    ast.GtE: "comparison.gte",
    ast.Lt: "comparison.lt",
    ast.LtE: "comparison.lte",
    ast.Eq: "comparison.eq",
    ast.NotEq: "comparison.ne",
}

_ROLLING_OPERATIONS = frozenset(
    {
        "rolling_mean",
        "rolling_sum",
        "rolling_std",
        "rolling_min",
        "rolling_max",
    }
)

_UNARY_NUMERIC_FUNCTIONS = frozenset({"abs", "log", "sqrt", "rank"})

_NUMERIC_INPUT_DATA_TYPES = frozenset(
    {
        "decimal",
        "double",
        "float",
        "float32",
        "float64",
        "int",
        "int32",
        "int64",
        "integer",
        "number",
        "numeric",
        "uint32",
        "uint64",
    }
)


def compile_factor_definition(definition: FactorDefinition) -> FactorExpressionPlan:
    if type(definition) is not FactorDefinition:
        raise FactorDslError("definition must be a FactorDefinition")
    if definition.formula.language != "serenity_factor_dsl":
        raise FactorDslError("FactorDefinition formula language must be serenity_factor_dsl")
    return compile_factor_expression(
        definition.formula.expression,
        inputs=definition.inputs,
        windows=definition.windows,
        definition_id=definition.definition_id,
        semantic_version=definition.semantic_version,
    )


def compile_factor_expression(
    expression: str,
    *,
    inputs: Sequence[FactorInput],
    windows: Sequence[FactorWindow] = (),
    definition_id: str | None = None,
    semantic_version: str | None = None,
) -> FactorExpressionPlan:
    normalized_expression = _required_string("expression", expression)
    context = _compile_context(inputs=inputs, windows=windows)
    try:
        parsed = ast.parse(normalized_expression, mode="eval")
    except SyntaxError as exc:
        raise FactorDslError(f"factor DSL expression is not valid syntax: {exc.msg}") from exc
    compiled = _compile_ast_node(parsed.body, context)
    return FactorExpressionPlan(
        expression=normalized_expression,
        node=compiled.node,
        required_inputs=tuple(sorted(compiled.required_inputs)),
        required_operators=tuple(sorted(compiled.required_operators)),
        lookback_periods=compiled.lookback_periods,
        dataset_versions=_dataset_versions(context.inputs_by_id, compiled.required_inputs),
        definition_id=definition_id,
        semantic_version=semantic_version,
    )


def _compile_ast_node(node: ast.AST, context: _CompileContext) -> _CompiledNode:
    if isinstance(node, ast.Name):
        input_spec = context.inputs_by_id.get(node.id)
        if input_spec is None:
            raise FactorDslError(f"unknown input: {node.id}")
        _require_numeric_input_data_type(input_spec)
        return _compiled_leaf(
            FactorExpressionNode(
                operation="input",
                value_type=FactorDslValueType.NUMERIC,
                value=input_spec.input_id,
                parameters={
                    "dataset_name": input_spec.dataset_name,
                    "dataset_version": input_spec.dataset_version,
                    "field_name": input_spec.field_name,
                },
                source=node.id,
            ),
            inputs={input_spec.input_id},
        )

    if isinstance(node, ast.Constant):
        return _compile_constant(node)

    if isinstance(node, ast.UnaryOp):
        return _compile_unary(node, context)

    if isinstance(node, ast.BinOp):
        return _compile_binary(node, context)

    if isinstance(node, ast.Compare):
        return _compile_comparison(node, context)

    if isinstance(node, ast.BoolOp):
        return _compile_bool_op(node, context)

    if isinstance(node, ast.IfExp):
        return _compile_where(
            condition=_compile_ast_node(node.test, context),
            true_value=_compile_ast_node(node.body, context),
            false_value=_compile_ast_node(node.orelse, context),
        )

    if isinstance(node, ast.Call):
        return _compile_call(node, context)

    raise FactorDslError(f"syntax node is not allowed in factor DSL: {type(node).__name__}")


def _compile_constant(node: ast.Constant) -> _CompiledNode:
    if type(node.value) in {int, float}:
        value = float(node.value)
        if not isfinite(value):
            raise FactorDslError("numeric constants must be finite")
        return _compiled_leaf(
            FactorExpressionNode(operation="constant", value_type=FactorDslValueType.NUMERIC, value=value),
        )
    if type(node.value) is bool:
        return _compiled_leaf(
            FactorExpressionNode(operation="constant", value_type=FactorDslValueType.BOOLEAN, value=node.value),
        )
    if type(node.value) is str:
        return _compiled_leaf(
            FactorExpressionNode(operation="constant", value_type=FactorDslValueType.STRING, value=node.value),
        )
    raise FactorDslError("only finite numeric, boolean and string constants are allowed")


def _compile_unary(node: ast.UnaryOp, context: _CompileContext) -> _CompiledNode:
    operand = _compile_ast_node(node.operand, context)
    if isinstance(node.op, ast.Not):
        _require_value_type(operand, FactorDslValueType.BOOLEAN, "not")
        return _compiled_operation("not", FactorDslValueType.BOOLEAN, (operand,))
    if isinstance(node.op, (ast.UAdd, ast.USub)):
        _require_value_type(operand, FactorDslValueType.NUMERIC, "unary arithmetic")
        operation = "neg" if isinstance(node.op, ast.USub) else "pos"
        return _compiled_operation(operation, FactorDslValueType.NUMERIC, (operand,))
    raise FactorDslError(f"unary operator is not allowed: {type(node.op).__name__}")


def _compile_binary(node: ast.BinOp, context: _CompileContext) -> _CompiledNode:
    operation = _BINARY_OPERATIONS.get(type(node.op))
    if operation is None:
        raise FactorDslError(f"binary operator is not allowed: {type(node.op).__name__}")
    left = _compile_ast_node(node.left, context)
    right = _compile_ast_node(node.right, context)
    _require_value_type(left, FactorDslValueType.NUMERIC, operation)
    _require_value_type(right, FactorDslValueType.NUMERIC, operation)
    if operation == "guarded_divide" and _is_literal_zero(right.node):
        raise FactorDslError("division by zero is not allowed; use a non-zero denominator or guarded data input")
    return _compiled_operation(operation, FactorDslValueType.NUMERIC, (left, right))


def _compile_comparison(node: ast.Compare, context: _CompileContext) -> _CompiledNode:
    if len(node.ops) != 1 or len(node.comparators) != 1:
        raise FactorDslError("chained comparisons are not allowed")
    operation = _COMPARISON_OPERATIONS.get(type(node.ops[0]))
    if operation is None:
        raise FactorDslError(f"comparison operator is not allowed: {type(node.ops[0]).__name__}")
    left = _compile_ast_node(node.left, context)
    right = _compile_ast_node(node.comparators[0], context)
    _require_value_type(left, FactorDslValueType.NUMERIC, operation)
    _require_value_type(right, FactorDslValueType.NUMERIC, operation)
    return _compiled_operation(operation, FactorDslValueType.BOOLEAN, (left, right))


def _compile_bool_op(node: ast.BoolOp, context: _CompileContext) -> _CompiledNode:
    if len(node.values) < 2:
        raise FactorDslError("boolean operations require at least two operands")
    operation = "and" if isinstance(node.op, ast.And) else "or" if isinstance(node.op, ast.Or) else None
    if operation is None:
        raise FactorDslError(f"boolean operator is not allowed: {type(node.op).__name__}")
    children = tuple(_compile_ast_node(value, context) for value in node.values)
    for child in children:
        _require_value_type(child, FactorDslValueType.BOOLEAN, operation)
    return _compiled_operation(operation, FactorDslValueType.BOOLEAN, children)


def _compile_call(node: ast.Call, context: _CompileContext) -> _CompiledNode:
    if not isinstance(node.func, ast.Name):
        raise FactorDslError("function calls must use whitelisted operator names")
    if node.keywords:
        raise FactorDslError("factor DSL operators do not accept keyword arguments")
    function_name = node.func.id
    if function_name == "delay":
        return _compile_delay(node, context)
    if function_name in _ROLLING_OPERATIONS:
        return _compile_rolling(node, context, function_name)
    if function_name in _UNARY_NUMERIC_FUNCTIONS:
        return _compile_unary_numeric_function(node, context, function_name)
    if function_name == "where":
        if len(node.args) != 3:
            raise FactorDslError("where expects exactly three arguments")
        return _compile_where(
            condition=_compile_ast_node(node.args[0], context),
            true_value=_compile_ast_node(node.args[1], context),
            false_value=_compile_ast_node(node.args[2], context),
        )
    raise FactorDslError(f"operator is not allowed in factor DSL: {function_name}")


def _compile_delay(node: ast.Call, context: _CompileContext) -> _CompiledNode:
    if len(node.args) != 2:
        raise FactorDslError("delay expects exactly two arguments")
    child = _compile_ast_node(node.args[0], context)
    _require_value_type(child, FactorDslValueType.NUMERIC, "delay")
    periods = _positive_integer_literal(node.args[1], "delay periods")
    if periods not in context.declared_window_lengths:
        raise FactorDslError(f"delay periods {periods} must match a declared FactorWindow")
    return _compiled_operation(
        "delay",
        FactorDslValueType.NUMERIC,
        (child,),
        parameters={"periods": periods},
        lookback_periods=child.lookback_periods + periods,
    )


def _compile_rolling(node: ast.Call, context: _CompileContext, operation: str) -> _CompiledNode:
    if len(node.args) != 2:
        raise FactorDslError(f"{operation} expects exactly two arguments")
    child = _compile_ast_node(node.args[0], context)
    _require_value_type(child, FactorDslValueType.NUMERIC, operation)
    window = _positive_integer_literal(node.args[1], f"{operation} window")
    if window not in context.declared_window_lengths:
        raise FactorDslError(f"{operation} window {window} must match a declared FactorWindow")
    return _compiled_operation(
        operation,
        FactorDslValueType.NUMERIC,
        (child,),
        parameters={"window": window},
        lookback_periods=child.lookback_periods + window,
    )


def _compile_unary_numeric_function(node: ast.Call, context: _CompileContext, operation: str) -> _CompiledNode:
    if len(node.args) != 1:
        raise FactorDslError(f"{operation} expects exactly one argument")
    child = _compile_ast_node(node.args[0], context)
    _require_value_type(child, FactorDslValueType.NUMERIC, operation)
    return _compiled_operation(operation, FactorDslValueType.NUMERIC, (child,))


def _compile_where(
    *,
    condition: _CompiledNode,
    true_value: _CompiledNode,
    false_value: _CompiledNode,
) -> _CompiledNode:
    _require_value_type(condition, FactorDslValueType.BOOLEAN, "where condition")
    _require_value_type(true_value, FactorDslValueType.NUMERIC, "where true branch")
    _require_value_type(false_value, FactorDslValueType.NUMERIC, "where false branch")
    return _compiled_operation("where", FactorDslValueType.NUMERIC, (condition, true_value, false_value))


def _compiled_leaf(
    node: FactorExpressionNode,
    *,
    inputs: set[str] | None = None,
    operators: set[str] | None = None,
    lookback_periods: int = 0,
) -> _CompiledNode:
    return _CompiledNode(
        node=node,
        required_inputs=frozenset(inputs or set()),
        required_operators=frozenset(operators or set()),
        lookback_periods=lookback_periods,
    )


def _compiled_operation(
    operation: str,
    value_type: FactorDslValueType,
    children: Sequence[_CompiledNode],
    *,
    parameters: Mapping[str, Any] | None = None,
    lookback_periods: int | None = None,
) -> _CompiledNode:
    child_tuple = tuple(children)
    node = FactorExpressionNode(
        operation=operation,
        value_type=value_type,
        children=tuple(child.node for child in child_tuple),
        parameters=parameters or {},
    )
    required_inputs: set[str] = set()
    required_operators: set[str] = {operation}
    resolved_lookback = 0
    for child in child_tuple:
        required_inputs.update(child.required_inputs)
        required_operators.update(child.required_operators)
        resolved_lookback = max(resolved_lookback, child.lookback_periods)
    if lookback_periods is not None:
        resolved_lookback = max(resolved_lookback, lookback_periods)
    return _CompiledNode(
        node=node,
        required_inputs=frozenset(required_inputs),
        required_operators=frozenset(required_operators),
        lookback_periods=resolved_lookback,
    )


def _compile_context(
    *,
    inputs: Sequence[FactorInput],
    windows: Sequence[FactorWindow],
) -> _CompileContext:
    inputs_by_id: dict[str, FactorInput] = {}
    for input_spec in tuple(inputs):
        if type(input_spec) is not FactorInput:
            raise FactorDslError("inputs must contain FactorInput values")
        if input_spec.input_id in inputs_by_id:
            raise FactorDslError(f"duplicate input_id: {input_spec.input_id}")
        inputs_by_id[input_spec.input_id] = input_spec
    if not inputs_by_id:
        raise FactorDslError("factor DSL compilation requires at least one input")
    declared_windows: set[int] = set()
    for window in tuple(windows):
        if type(window) is not FactorWindow:
            raise FactorDslError("windows must contain FactorWindow values")
        declared_windows.add(window.length)
    return _CompileContext(
        inputs_by_id=MappingProxyType(inputs_by_id),
        declared_window_lengths=frozenset(declared_windows),
    )


def _dataset_versions(inputs_by_id: Mapping[str, FactorInput], required_inputs: frozenset[str]) -> Mapping[str, str]:
    dataset_versions: dict[str, str] = {}
    for input_id in sorted(required_inputs):
        input_spec = inputs_by_id[input_id]
        existing = dataset_versions.get(input_spec.dataset_name)
        if existing is not None and existing != input_spec.dataset_version:
            raise FactorDslError(f"dataset {input_spec.dataset_name} has conflicting versions")
        dataset_versions[input_spec.dataset_name] = input_spec.dataset_version
    return MappingProxyType(dataset_versions)


def _positive_integer_literal(node: ast.AST, field_name: str) -> int:
    if isinstance(node, ast.Constant) and type(node.value) is int:
        value = int(node.value)
    elif (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, ast.USub)
        and isinstance(node.operand, ast.Constant)
        and type(node.operand.value) is int
    ):
        value = -int(node.operand.value)
    else:
        raise FactorDslError(f"{field_name} must be a positive integer literal")
    if value <= 0:
        raise FactorDslError(f"{field_name} must be positive and cannot reference future data")
    return value


def _require_value_type(compiled: _CompiledNode, value_type: FactorDslValueType, context: str) -> None:
    if compiled.node.value_type is not value_type:
        raise FactorDslError(f"{context} requires {value_type.value} input")


def _require_numeric_input_data_type(input_spec: FactorInput) -> None:
    if input_spec.data_type is None:
        return
    normalized = input_spec.data_type.strip().lower()
    if normalized not in _NUMERIC_INPUT_DATA_TYPES:
        raise FactorDslError(
            f"input {input_spec.input_id} must declare a numeric data_type for factor DSL expressions"
        )


def _is_literal_zero(node: FactorExpressionNode) -> bool:
    return node.operation == "constant" and type(node.value) in {int, float} and float(node.value) == 0.0


def _required_string(field_name: str, value: object) -> str:
    if type(value) is not str:
        raise FactorDslError(f"{field_name} is required")
    stripped = value.strip()
    if not stripped:
        raise FactorDslError(f"{field_name} is required")
    return stripped


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return _required_string("optional string", value)


def _string_tuple(field_name: str, values: Sequence[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for value in values:
        normalized.append(_required_string(field_name, value))
    return tuple(normalized)


def _freeze_string_mapping(mapping: Mapping[str, str]) -> Mapping[str, str]:
    if not isinstance(mapping, Mapping):
        raise FactorDslError("value must be a mapping")
    return MappingProxyType(
        {
            _required_string("mapping key", key): _required_string("mapping value", value)
            for key, value in mapping.items()
        }
    )


def _freeze_mapping(mapping: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(mapping, Mapping):
        raise FactorDslError("value must be a mapping")
    return MappingProxyType({str(key): _freeze_value(value) for key, value in mapping.items()})


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, list | tuple):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, set | frozenset):
        return tuple(sorted(_freeze_value(item) for item in value))
    if isinstance(value, bytearray):
        return bytes(value)
    return value


def _thaw_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw_value(inner) for key, inner in value.items()}
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


__all__ = [
    "FACTOR_DSL_ENGINE_VERSION",
    "FACTOR_DSL_SCHEMA_NAME",
    "FACTOR_DSL_SCHEMA_VERSION",
    "FactorDslError",
    "FactorDslValueType",
    "FactorExpressionNode",
    "FactorExpressionPlan",
    "compile_factor_definition",
    "compile_factor_expression",
]
