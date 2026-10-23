"""Strict, engine-neutral extraction artifacts for the pragmatic C1 sprint."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, TypeVar

from ayxg.expr import ArtifactError, Declaration, TermSort, TypedExpr

_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]*\Z")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_HEX_BYTES_RE = re.compile(r"(?:[0-9a-f]{2})+\Z")
_U64_MAX = (1 << 64) - 1


def _nonnegative(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ArtifactError(f"{field} must be a nonnegative integer")
    return value


def _u64(value: Any, field: str) -> int:
    value = _nonnegative(value, field)
    if value > _U64_MAX:
        raise ArtifactError(f"{field} exceeds unsigned 64-bit range")
    return value


def _identifier(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ArtifactError(f"{field} is not a canonical identifier")
    return value


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ArtifactError(f"{field} must be a nonempty string")
    return value


def _function_name(value: Any, field: str) -> str:
    """Preserve an external function identity; it is not an SMT identifier.

    ELF names and provider root IDs may contain punctuation, whitespace and
    Unicode. Never normalize them: distinct spellings are distinct references.
    """
    return _text(value, field)


def _sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ArtifactError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _object(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ArtifactError(f"{field} must be an object")
    return value


def _array(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ArtifactError(f"{field} must be an array")
    return value


def _fields(value: Mapping[str, Any], expected: set[str], field: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ArtifactError(
            f"{field} fields differ: missing={missing}, extra={extra}"
        )


def _unique(values: tuple[Any, ...], field: str) -> None:
    if len(set(values)) != len(values):
        raise ArtifactError(f"{field} contains duplicates")


def _sorted(values: tuple[Any, ...], key: Callable[[Any], Any], field: str) -> None:
    if values != tuple(sorted(values, key=key)):
        raise ArtifactError(f"{field} must be in canonical order")


BOOL = TermSort.bool()
BV64 = TermSort.bv(64)
MEM64_8 = TermSort.array(64, 8)


@dataclass(frozen=True)
class Assignment:
    name: str
    value: TypedExpr

    def __post_init__(self) -> None:
        _identifier(self.name, "assignment.name")

    def to_data(self) -> dict[str, Any]:
        return {"name": self.name, "value": self.value.to_data()}

    @classmethod
    def from_data(
        cls,
        value: Any,
        field: str = "assignment",
    ) -> Assignment:
        obj = _object(value, field)
        _fields(obj, {"name", "value"}, field)
        return cls(
            _identifier(obj["name"], f"{field}.name"),
            TypedExpr.from_data(obj["value"], f"{field}.value"),
        )


@dataclass(frozen=True, order=True)
class HandlerBinding:
    """Canonical transport identity for one bound primitive contract."""

    handler_id: str
    contract_sha256: str

    def __post_init__(self) -> None:
        _identifier(self.handler_id, "handler_binding.handler_id")
        _sha256(
            self.contract_sha256,
            "handler_binding.contract_sha256",
        )

    def to_data(self) -> dict[str, str]:
        return {
            "handler_id": self.handler_id,
            "contract_sha256": self.contract_sha256,
        }

    @classmethod
    def from_data(
        cls,
        value: Any,
        field: str = "handler_binding",
    ) -> HandlerBinding:
        obj = _object(value, field)
        _fields(obj, {"handler_id", "contract_sha256"}, field)
        return cls(
            _identifier(obj["handler_id"], f"{field}.handler_id"),
            _sha256(
                obj["contract_sha256"],
                f"{field}.contract_sha256",
            ),
        )


@dataclass(frozen=True)
class ExternalEffect:
    """Typed opaque effect whose semantics are supplied by a bound primitive."""

    binding: HandlerBinding
    arguments: tuple[Assignment, ...]
    outputs: tuple[Declaration, ...]

    def __post_init__(self) -> None:
        argument_names = tuple(argument.name for argument in self.arguments)
        output_names = tuple(output.name for output in self.outputs)
        if not self.arguments:
            raise ArtifactError("external_effect.arguments must be nonempty")
        if not self.outputs:
            raise ArtifactError("external_effect.outputs must be nonempty")
        _unique(argument_names, "external_effect.arguments")
        _unique(output_names, "external_effect.outputs")
        _sorted(
            self.arguments,
            lambda argument: argument.name,
            "external_effect.arguments",
        )
        _sorted(
            self.outputs,
            lambda output: output.name,
            "external_effect.outputs",
        )

    def validate(self, declarations: tuple[Declaration, ...]) -> None:
        declared = {
            declaration.name: declaration.sort
            for declaration in declarations
        }
        for output in self.outputs:
            if declared.get(output.name) != output.sort:
                raise ArtifactError(
                    f"external effect output {output.name!r} is absent "
                    "or has the wrong sort"
                )
        for argument in self.arguments:
            for name, sort in argument.value.variable_sorts().items():
                if declared.get(name) != sort:
                    raise ArtifactError(
                        f"external effect argument variable {name!r} is "
                        "absent or has the wrong sort"
                    )

    def to_data(self) -> dict[str, Any]:
        return {
            "binding": self.binding.to_data(),
            "arguments": [
                argument.to_data() for argument in self.arguments
            ],
            "outputs": [output.to_data() for output in self.outputs],
        }

    @classmethod
    def from_data(
        cls,
        value: Any,
        field: str = "external_effect",
    ) -> ExternalEffect:
        obj = _object(value, field)
        _fields(obj, {"binding", "arguments", "outputs"}, field)
        return cls(
            binding=HandlerBinding.from_data(
                obj["binding"], f"{field}.binding"
            ),
            arguments=tuple(
                Assignment.from_data(item, f"{field}.arguments[]")
                for item in _array(
                    obj["arguments"], f"{field}.arguments"
                )
            ),
            outputs=tuple(
                Declaration.from_data(item, f"{field}.outputs[]")
                for item in _array(obj["outputs"], f"{field}.outputs")
            ),
        )


@dataclass(frozen=True, order=True)
class StaticOccurrenceId:
    """Opaque adapter projection into Gate B's static occurrence carrier."""

    value: int

    def __post_init__(self) -> None:
        _nonnegative(self.value, "StaticOccurrenceId.value")


@dataclass(frozen=True, order=True)
class OutcomeId:
    value: int

    def __post_init__(self) -> None:
        _nonnegative(self.value, "OutcomeId.value")


@dataclass(frozen=True, order=True)
class EdgeId:
    occurrence: StaticOccurrenceId
    outcome: OutcomeId

    def to_data(self) -> dict[str, int]:
        return {
            "static_occurrence_id": self.occurrence.value,
            "outcome_id": self.outcome.value,
        }

    @classmethod
    def from_data(cls, value: Any, field: str = "edge_id") -> EdgeId:
        obj = _object(value, field)
        _fields(obj, {"static_occurrence_id", "outcome_id"}, field)
        return cls(
            StaticOccurrenceId(
                _nonnegative(
                    obj["static_occurrence_id"],
                    f"{field}.static_occurrence_id",
                )
            ),
            OutcomeId(_nonnegative(obj["outcome_id"], f"{field}.outcome_id")),
        )


@dataclass(frozen=True)
class DecodedInstructionEvidence:
    image_sha256: str
    canonical_address: int
    instruction_bytes: str
    architecture: str
    decode_mode: str
    instruction_identity: str
    function_owners: tuple[str, ...]

    kind = "decoded_instruction"

    def __post_init__(self) -> None:
        _sha256(self.image_sha256, "decoded.image_sha256")
        _u64(self.canonical_address, "decoded.canonical_address")
        if not _HEX_BYTES_RE.fullmatch(self.instruction_bytes):
            raise ArtifactError(
                "decoded.instruction_bytes must be nonempty lowercase hex bytes"
            )
        _identifier(self.architecture, "decoded.architecture")
        _identifier(self.decode_mode, "decoded.decode_mode")
        _text(self.instruction_identity, "decoded.instruction_identity")
        if not self.function_owners:
            raise ArtifactError("decoded.function_owners must be nonempty")
        for owner in self.function_owners:
            _function_name(owner, "decoded.function_owners[]")
        _unique(self.function_owners, "decoded.function_owners")
        if self.function_owners != tuple(sorted(self.function_owners)):
            raise ArtifactError("decoded.function_owners must be sorted")

    @property
    def source(self) -> int:
        return self.canonical_address

    def to_data(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "image_sha256": self.image_sha256,
            "canonical_address": self.canonical_address,
            "instruction_bytes": self.instruction_bytes,
            "architecture": self.architecture,
            "decode_mode": self.decode_mode,
            "instruction_identity": self.instruction_identity,
            "function_owners": list(self.function_owners),
        }

    @classmethod
    def from_data(cls, value: Any) -> DecodedInstructionEvidence:
        obj = _object(value, "decoded origin")
        _fields(
            obj,
            {
                "kind",
                "image_sha256",
                "canonical_address",
                "instruction_bytes",
                "architecture",
                "decode_mode",
                "instruction_identity",
                "function_owners",
            },
            "decoded origin",
        )
        if obj["kind"] != cls.kind:
            raise ArtifactError("decoded origin has wrong kind")
        return cls(
            image_sha256=_sha256(obj["image_sha256"], "decoded.image_sha256"),
            canonical_address=_u64(
                obj["canonical_address"], "decoded.canonical_address"
            ),
            instruction_bytes=_text(
                obj["instruction_bytes"], "decoded.instruction_bytes"
            ),
            architecture=_identifier(
                obj["architecture"], "decoded.architecture"
            ),
            decode_mode=_identifier(obj["decode_mode"], "decoded.decode_mode"),
            instruction_identity=_text(
                obj["instruction_identity"], "decoded.instruction_identity"
            ),
            function_owners=tuple(
                _function_name(owner, "decoded.function_owners[]")
                for owner in _array(
                    obj["function_owners"], "decoded.function_owners"
                )
            ),
        )


@dataclass(frozen=True)
class PrimitiveModelEvidence:
    image_sha256: str
    boundary_address: int
    symbol: str
    boundary_resolution: str
    abi: str
    model_name: str
    model_sha256: str
    domain: str
    semantic_update: str
    target_rule: str
    qualification_evidence: tuple[str, ...]

    kind = "modeled_primitive"

    def __post_init__(self) -> None:
        _sha256(self.image_sha256, "primitive.image_sha256")
        _u64(self.boundary_address, "primitive.boundary_address")
        _function_name(self.symbol, "primitive.symbol")
        _identifier(self.boundary_resolution, "primitive.boundary_resolution")
        _identifier(self.abi, "primitive.abi")
        _identifier(self.model_name, "primitive.model_name")
        _sha256(self.model_sha256, "primitive.model_sha256")
        _text(self.domain, "primitive.domain")
        _text(self.semantic_update, "primitive.semantic_update")
        _text(self.target_rule, "primitive.target_rule")
        if not self.qualification_evidence:
            raise ArtifactError(
                "primitive.qualification_evidence must be nonempty"
            )
        for evidence in self.qualification_evidence:
            _identifier(evidence, "primitive.qualification_evidence[]")
        _unique(
            self.qualification_evidence, "primitive.qualification_evidence"
        )
        if self.qualification_evidence != tuple(
            sorted(self.qualification_evidence)
        ):
            raise ArtifactError(
                "primitive.qualification_evidence must be sorted"
            )

    @property
    def source(self) -> int:
        return self.boundary_address

    def to_data(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "image_sha256": self.image_sha256,
            "boundary_address": self.boundary_address,
            "symbol": self.symbol,
            "boundary_resolution": self.boundary_resolution,
            "abi": self.abi,
            "model_name": self.model_name,
            "model_sha256": self.model_sha256,
            "domain": self.domain,
            "semantic_update": self.semantic_update,
            "target_rule": self.target_rule,
            "qualification_evidence": list(self.qualification_evidence),
        }

    @classmethod
    def from_data(cls, value: Any) -> PrimitiveModelEvidence:
        obj = _object(value, "primitive origin")
        _fields(
            obj,
            {
                "kind",
                "image_sha256",
                "boundary_address",
                "symbol",
                "boundary_resolution",
                "abi",
                "model_name",
                "model_sha256",
                "domain",
                "semantic_update",
                "target_rule",
                "qualification_evidence",
            },
            "primitive origin",
        )
        if obj["kind"] != cls.kind:
            raise ArtifactError("primitive origin has wrong kind")
        return cls(
            image_sha256=_sha256(obj["image_sha256"], "primitive.image_sha256"),
            boundary_address=_u64(
                obj["boundary_address"], "primitive.boundary_address"
            ),
            symbol=_function_name(obj["symbol"], "primitive.symbol"),
            boundary_resolution=_identifier(
                obj["boundary_resolution"], "primitive.boundary_resolution"
            ),
            abi=_identifier(obj["abi"], "primitive.abi"),
            model_name=_identifier(obj["model_name"], "primitive.model_name"),
            model_sha256=_sha256(
                obj["model_sha256"], "primitive.model_sha256"
            ),
            domain=_text(obj["domain"], "primitive.domain"),
            semantic_update=_text(
                obj["semantic_update"], "primitive.semantic_update"
            ),
            target_rule=_text(obj["target_rule"], "primitive.target_rule"),
            qualification_evidence=tuple(
                _identifier(item, "primitive.qualification_evidence[]")
                for item in _array(
                    obj["qualification_evidence"],
                    "primitive.qualification_evidence",
                )
            ),
        )


OccurrenceOrigin = DecodedInstructionEvidence | PrimitiveModelEvidence


def _origin_from_data(value: Any) -> OccurrenceOrigin:
    obj = _object(value, "occurrence.origin")
    kind = obj.get("kind")
    if kind == DecodedInstructionEvidence.kind:
        return DecodedInstructionEvidence.from_data(obj)
    if kind == PrimitiveModelEvidence.kind:
        return PrimitiveModelEvidence.from_data(obj)
    raise ArtifactError(f"unknown occurrence origin kind: {kind!r}")


@dataclass(frozen=True)
class Occurrence:
    id: StaticOccurrenceId
    origin: OccurrenceOrigin

    def to_data(self) -> dict[str, Any]:
        return {
            "static_occurrence_id": self.id.value,
            "origin": self.origin.to_data(),
        }

    @classmethod
    def from_data(cls, value: Any) -> Occurrence:
        obj = _object(value, "occurrence")
        _fields(obj, {"static_occurrence_id", "origin"}, "occurrence")
        return cls(
            StaticOccurrenceId(
                _nonnegative(
                    obj["static_occurrence_id"],
                    "occurrence.static_occurrence_id",
                )
            ),
            _origin_from_data(obj["origin"]),
        )


@dataclass(frozen=True)
class Target:
    kind: str
    value: int | TypedExpr | None = None

    def __post_init__(self) -> None:
        if self.kind == "address":
            _u64(self.value, "target.value")
        elif self.kind == "symbolic":
            if not isinstance(self.value, TypedExpr) or self.value.sort != BV64:
                raise ArtifactError("symbolic target must be a typed BV64 expression")
        elif self.kind in {"halt", "error", "stuck"}:
            if self.value is not None:
                raise ArtifactError(f"{self.kind} target must not have a value")
        else:
            raise ArtifactError(f"unknown target kind: {self.kind!r}")

    def to_data(self) -> dict[str, Any]:
        result: dict[str, Any] = {"kind": self.kind}
        if self.value is not None:
            result["value"] = (
                self.value.to_data()
                if isinstance(self.value, TypedExpr)
                else self.value
            )
        return result

    @classmethod
    def from_data(cls, value: Any, field: str = "target") -> Target:
        obj = _object(value, field)
        kind = obj.get("kind")
        expected = {"kind"} if kind in {"halt", "error", "stuck"} else {
            "kind",
            "value",
        }
        _fields(obj, expected, field)
        parsed_kind = _text(kind, f"{field}.kind")
        raw_value = obj.get("value")
        return cls(
            kind=parsed_kind,
            value=(
                TypedExpr.from_data(raw_value, f"{field}.value")
                if parsed_kind == "symbolic"
                else raw_value
            ),
        )


@dataclass(frozen=True)
class StepSummary:
    guard: TypedExpr
    simultaneous_update: tuple[Assignment, ...]
    target: Target
    mirrored_pc: TypedExpr
    external_effect: ExternalEffect | None = None

    def __post_init__(self) -> None:
        if self.guard.sort != BOOL:
            raise ArtifactError("step_summary.guard must be Bool")
        if self.mirrored_pc.sort != BV64:
            raise ArtifactError("step_summary.mirrored_pc must be BV64")
        names = tuple(assignment.name for assignment in self.simultaneous_update)
        _unique(names, "step_summary.simultaneous_update")

    def to_data(self) -> dict[str, Any]:
        result = {
            "guard": self.guard.to_data(),
            "simultaneous_update": [
                assignment.to_data()
                for assignment in self.simultaneous_update
            ],
            "target": self.target.to_data(),
            "mirrored_pc": self.mirrored_pc.to_data(),
        }
        if self.external_effect is not None:
            result["external_effect"] = self.external_effect.to_data()
        return result

    def validate(self, declarations: tuple[Declaration, ...]) -> None:
        declared = {declaration.name: declaration.sort for declaration in declarations}
        assignments = {
            assignment.name: assignment.value.sort
            for assignment in self.simultaneous_update
        }
        effect_outputs = (
            {}
            if self.external_effect is None
            else {
                output.name: output.sort
                for output in self.external_effect.outputs
            }
        )
        if set(assignments) & set(effect_outputs):
            raise ArtifactError(
                "step_summary assignments and external outputs overlap"
            )
        if assignments | effect_outputs != declared:
            raise ArtifactError(
                "step_summary assignments and external outputs must cover every "
                "declaration exactly once at its declared sort"
            )
        expected_assignment_order = tuple(
            declaration.name
            for declaration in declarations
            if declaration.name not in effect_outputs
        )
        if tuple(
            assignment.name for assignment in self.simultaneous_update
        ) != expected_assignment_order:
            raise ArtifactError(
                "step_summary simultaneous update must follow declaration order"
            )
        expressions = [
            self.guard,
            *(assignment.value for assignment in self.simultaneous_update),
            self.mirrored_pc,
        ]
        if self.target.kind == "symbolic":
            assert isinstance(self.target.value, TypedExpr)
            expressions.append(self.target.value)
        if self.external_effect is not None:
            self.external_effect.validate(declarations)
            expressions.extend(
                argument.value
                for argument in self.external_effect.arguments
            )
        for expression in expressions:
            for name, sort in expression.variable_sorts().items():
                if declared.get(name) != sort:
                    raise ArtifactError(
                        f"expression variable {name!r} is absent or has wrong sort"
                    )

    @classmethod
    def from_data(cls, value: Any, field: str = "step_summary") -> StepSummary:
        obj = _object(value, field)
        expected = {"guard", "simultaneous_update", "target", "mirrored_pc"}
        if "external_effect" in obj:
            expected.add("external_effect")
        _fields(obj, expected, field)
        return cls(
            guard=TypedExpr.from_data(obj["guard"], f"{field}.guard"),
            simultaneous_update=tuple(
                Assignment.from_data(item, f"{field}.simultaneous_update[]")
                for item in _array(
                    obj["simultaneous_update"],
                    f"{field}.simultaneous_update",
                )
            ),
            target=Target.from_data(obj["target"], f"{field}.target"),
            mirrored_pc=TypedExpr.from_data(
                obj["mirrored_pc"], f"{field}.mirrored_pc"
            ),
            external_effect=(
                ExternalEffect.from_data(
                    obj["external_effect"], f"{field}.external_effect"
                )
                if "external_effect" in obj
                else None
            ),
        )


@dataclass(frozen=True)
class PrefixSummary:
    kind: str
    label: str | None = None
    end_control: int | None = None

    def __post_init__(self) -> None:
        if self.kind == "empty":
            if self.label is not None or self.end_control is not None:
                raise ArtifactError("empty prefix must not carry fields")
        elif self.kind == "nonempty":
            _text(self.label, "prefix.label")
            _u64(self.end_control, "prefix.end_control")
        else:
            raise ArtifactError(f"unknown prefix kind: {self.kind!r}")

    @classmethod
    def empty(cls) -> PrefixSummary:
        return cls("empty")

    @classmethod
    def nonempty(cls, label: str, end_control: int) -> PrefixSummary:
        return cls("nonempty", label, end_control)

    def to_data(self) -> dict[str, Any]:
        if self.kind == "empty":
            return {"kind": "empty"}
        return {
            "kind": "nonempty",
            "label": self.label,
            "end_control": self.end_control,
        }

    @classmethod
    def from_data(cls, value: Any, field: str = "prefix") -> PrefixSummary:
        obj = _object(value, field)
        kind = obj.get("kind")
        if kind == "empty":
            _fields(obj, {"kind"}, field)
            return cls.empty()
        if kind == "nonempty":
            _fields(obj, {"kind", "label", "end_control"}, field)
            return cls.nonempty(
                _text(obj["label"], f"{field}.label"),
                _u64(obj["end_control"], f"{field}.end_control"),
            )
        raise ArtifactError(f"unknown prefix kind: {kind!r}")


@dataclass(frozen=True)
class Root:
    root_id: str
    function_id: str
    entry_control: int
    abi: str
    initial_admissible: str

    def __post_init__(self) -> None:
        _function_name(self.root_id, "root.root_id")
        _function_name(self.function_id, "root.function_id")
        _u64(self.entry_control, "root.entry_control")
        _identifier(self.abi, "root.abi")
        _text(self.initial_admissible, "root.initial_admissible")

    def to_data(self) -> dict[str, Any]:
        return {
            "root_id": self.root_id,
            "function_id": self.function_id,
            "entry_control": self.entry_control,
            "abi": self.abi,
            "initial_admissible": self.initial_admissible,
        }

    @classmethod
    def from_data(cls, value: Any) -> Root:
        obj = _object(value, "root")
        _fields(
            obj,
            {
                "root_id",
                "function_id",
                "entry_control",
                "abi",
                "initial_admissible",
            },
            "root",
        )
        return cls(
            root_id=_function_name(obj["root_id"], "root.root_id"),
            function_id=_function_name(obj["function_id"], "root.function_id"),
            entry_control=_u64(obj["entry_control"], "root.entry_control"),
            abi=_identifier(obj["abi"], "root.abi"),
            initial_admissible=_text(
                obj["initial_admissible"], "root.initial_admissible"
            ),
        )


@dataclass(frozen=True)
class LocalEdge:
    id: EdgeId
    source: int
    summary: StepSummary

    def __post_init__(self) -> None:
        _u64(self.source, "local_edge.source")

    def to_data(self) -> dict[str, Any]:
        return {
            "edge_id": self.id.to_data(),
            "source": self.source,
            "summary": self.summary.to_data(),
        }

    @classmethod
    def from_data(cls, value: Any) -> LocalEdge:
        obj = _object(value, "local_edge")
        _fields(obj, {"edge_id", "source", "summary"}, "local_edge")
        return cls(
            id=EdgeId.from_data(obj["edge_id"], "local_edge.edge_id"),
            source=_u64(obj["source"], "local_edge.source"),
            summary=StepSummary.from_data(
                obj["summary"], "local_edge.summary"
            ),
        )


@dataclass(frozen=True)
class ContextObservation:
    observation_id: str
    root_id: str
    edge_id: EdgeId
    before: PrefixSummary
    after: StepSummary
    path_condition: str

    def __post_init__(self) -> None:
        _identifier(self.observation_id, "observation.observation_id")
        _function_name(self.root_id, "observation.root_id")
        _text(self.path_condition, "observation.path_condition")

    def to_data(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "root_id": self.root_id,
            "edge_id": self.edge_id.to_data(),
            "before": self.before.to_data(),
            "after": self.after.to_data(),
            "path_condition": self.path_condition,
        }

    @classmethod
    def from_data(cls, value: Any) -> ContextObservation:
        obj = _object(value, "observation")
        _fields(
            obj,
            {
                "observation_id",
                "root_id",
                "edge_id",
                "before",
                "after",
                "path_condition",
            },
            "observation",
        )
        return cls(
            observation_id=_identifier(
                obj["observation_id"], "observation.observation_id"
            ),
            root_id=_function_name(obj["root_id"], "observation.root_id"),
            edge_id=EdgeId.from_data(
                obj["edge_id"], "observation.edge_id"
            ),
            before=PrefixSummary.from_data(
                obj["before"], "observation.before"
            ),
            after=StepSummary.from_data(obj["after"], "observation.after"),
            path_condition=_text(
                obj["path_condition"], "observation.path_condition"
            ),
        )


@dataclass(frozen=True)
class FunctionSummary:
    summary_id: str
    function_id: str
    root_id: str
    precondition: str
    summary: StepSummary
    dependency_summary_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _identifier(self.summary_id, "function_summary.summary_id")
        _function_name(self.function_id, "function_summary.function_id")
        _function_name(self.root_id, "function_summary.root_id")
        _text(self.precondition, "function_summary.precondition")
        for dependency in self.dependency_summary_ids:
            _identifier(
                dependency, "function_summary.dependency_summary_ids[]"
            )
        _unique(
            self.dependency_summary_ids,
            "function_summary.dependency_summary_ids",
        )
        if self.dependency_summary_ids != tuple(
            sorted(self.dependency_summary_ids)
        ):
            raise ArtifactError(
                "function_summary.dependency_summary_ids must be sorted"
            )

    def to_data(self) -> dict[str, Any]:
        return {
            "summary_id": self.summary_id,
            "function_id": self.function_id,
            "root_id": self.root_id,
            "precondition": self.precondition,
            "summary": self.summary.to_data(),
            "dependency_summary_ids": list(self.dependency_summary_ids),
        }

    @classmethod
    def from_data(cls, value: Any) -> FunctionSummary:
        obj = _object(value, "function_summary")
        _fields(
            obj,
            {
                "summary_id",
                "function_id",
                "root_id",
                "precondition",
                "summary",
                "dependency_summary_ids",
            },
            "function_summary",
        )
        return cls(
            summary_id=_identifier(
                obj["summary_id"], "function_summary.summary_id"
            ),
            function_id=_function_name(
                obj["function_id"], "function_summary.function_id"
            ),
            root_id=_function_name(
                obj["root_id"], "function_summary.root_id"
            ),
            precondition=_text(
                obj["precondition"], "function_summary.precondition"
            ),
            summary=StepSummary.from_data(
                obj["summary"], "function_summary.summary"
            ),
            dependency_summary_ids=tuple(
                _identifier(
                    dependency,
                    "function_summary.dependency_summary_ids[]",
                )
                for dependency in _array(
                    obj["dependency_summary_ids"],
                    "function_summary.dependency_summary_ids",
                )
            ),
        )


@dataclass(frozen=True)
class SummaryApplication:
    application_id: str
    root_id: str
    call_edge_id: EdgeId
    callee_function_id: str
    callee_summary_id: str
    abi_instantiation: str
    precondition_result: str
    return_class: str
    continuation: Target
    before: PrefixSummary
    after: StepSummary

    def __post_init__(self) -> None:
        _identifier(self.application_id, "summary_application.application_id")
        _function_name(self.root_id, "summary_application.root_id")
        _function_name(
            self.callee_function_id,
            "summary_application.callee_function_id",
        )
        _identifier(
            self.callee_summary_id,
            "summary_application.callee_summary_id",
        )
        _text(
            self.abi_instantiation,
            "summary_application.abi_instantiation",
        )
        _text(
            self.precondition_result,
            "summary_application.precondition_result",
        )
        _identifier(self.return_class, "summary_application.return_class")
        if self.return_class not in {"ordinary", "nonordinary_control"}:
            raise ArtifactError("unknown summary application return class")
        if self.continuation.kind != "address":
            raise ArtifactError(
                "summary application continuation must be an ordinary address"
            )

    def to_data(self) -> dict[str, Any]:
        return {
            "application_id": self.application_id,
            "root_id": self.root_id,
            "call_edge_id": self.call_edge_id.to_data(),
            "callee_function_id": self.callee_function_id,
            "callee_summary_id": self.callee_summary_id,
            "abi_instantiation": self.abi_instantiation,
            "precondition_result": self.precondition_result,
            "return_class": self.return_class,
            "continuation": self.continuation.to_data(),
            "before": self.before.to_data(),
            "after": self.after.to_data(),
        }

    @classmethod
    def from_data(cls, value: Any) -> SummaryApplication:
        obj = _object(value, "summary_application")
        _fields(
            obj,
            {
                "application_id",
                "root_id",
                "call_edge_id",
                "callee_function_id",
                "callee_summary_id",
                "abi_instantiation",
                "precondition_result",
                "return_class",
                "continuation",
                "before",
                "after",
            },
            "summary_application",
        )
        return cls(
            application_id=_identifier(
                obj["application_id"],
                "summary_application.application_id",
            ),
            root_id=_function_name(
                obj["root_id"], "summary_application.root_id"
            ),
            call_edge_id=EdgeId.from_data(
                obj["call_edge_id"], "summary_application.call_edge_id"
            ),
            callee_function_id=_function_name(
                obj["callee_function_id"],
                "summary_application.callee_function_id",
            ),
            callee_summary_id=_identifier(
                obj["callee_summary_id"],
                "summary_application.callee_summary_id",
            ),
            abi_instantiation=_text(
                obj["abi_instantiation"],
                "summary_application.abi_instantiation",
            ),
            precondition_result=_text(
                obj["precondition_result"],
                "summary_application.precondition_result",
            ),
            return_class=_identifier(
                obj["return_class"],
                "summary_application.return_class",
            ),
            continuation=Target.from_data(
                obj["continuation"],
                "summary_application.continuation",
            ),
            before=PrefixSummary.from_data(
                obj["before"], "summary_application.before"
            ),
            after=StepSummary.from_data(
                obj["after"], "summary_application.after"
            ),
        )


@dataclass(frozen=True)
class RunEvent:
    kind: str
    evidence_id: str

    def __post_init__(self) -> None:
        if self.kind not in {"observation", "summary_application"}:
            raise ArtifactError(f"unknown run event kind: {self.kind!r}")
        _identifier(self.evidence_id, "run_event.evidence_id")

    def to_data(self) -> dict[str, str]:
        return {"kind": self.kind, "evidence_id": self.evidence_id}

    @classmethod
    def from_data(cls, value: Any) -> RunEvent:
        obj = _object(value, "run_event")
        _fields(obj, {"kind", "evidence_id"}, "run_event")
        return cls(
            kind=_text(obj["kind"], "run_event.kind"),
            evidence_id=_identifier(
                obj["evidence_id"], "run_event.evidence_id"
            ),
        )


@dataclass(frozen=True)
class ContextRun:
    run_id: str
    root_id: str
    events: tuple[RunEvent, ...]

    def __post_init__(self) -> None:
        _identifier(self.run_id, "run.run_id")
        _function_name(self.root_id, "run.root_id")
        if not self.events:
            raise ArtifactError("run.events must be nonempty")
        event_keys = tuple((event.kind, event.evidence_id) for event in self.events)
        _unique(event_keys, "run.events")

    def to_data(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "root_id": self.root_id,
            "events": [event.to_data() for event in self.events],
        }

    @classmethod
    def from_data(cls, value: Any) -> ContextRun:
        obj = _object(value, "run")
        _fields(obj, {"run_id", "root_id", "events"}, "run")
        return cls(
            run_id=_identifier(obj["run_id"], "run.run_id"),
            root_id=_function_name(obj["root_id"], "run.root_id"),
            events=tuple(
                RunEvent.from_data(event)
                for event in _array(obj["events"], "run.events")
            ),
        )


T = TypeVar("T")


def _index(
    values: tuple[T, ...],
    key: Callable[[T], Any],
    field: str,
) -> dict[Any, T]:
    result: dict[Any, T] = {}
    for value in values:
        item_key = key(value)
        if item_key in result:
            raise ArtifactError(f"duplicate {field}: {item_key!r}")
        result[item_key] = value
    return result


@dataclass(frozen=True)
class ExtractionArtifact:
    binary_id: str
    declarations: tuple[Declaration, ...]
    occurrences: tuple[Occurrence, ...]
    roots: tuple[Root, ...]
    local_edges: tuple[LocalEdge, ...]
    observations: tuple[ContextObservation, ...]
    summary_applications: tuple[SummaryApplication, ...]
    runs: tuple[ContextRun, ...]
    function_summaries: tuple[FunctionSummary, ...]

    schema = "ghot-pragmatic-extraction-v2"

    def __post_init__(self) -> None:
        _sha256(self.binary_id, "artifact.binary_id")
        if not self.declarations:
            raise ArtifactError("artifact.declarations must be nonempty")
        _index(
            self.declarations,
            lambda value: value.name,
            "declaration name",
        )
        occurrences = _index(
            self.occurrences, lambda value: value.id, "static occurrence id"
        )
        roots = _index(self.roots, lambda value: value.root_id, "root id")
        edges = _index(self.local_edges, lambda value: value.id, "edge id")
        observations = _index(
            self.observations,
            lambda value: value.observation_id,
            "observation id",
        )
        applications = _index(
            self.summary_applications,
            lambda value: value.application_id,
            "summary application id",
        )
        _index(self.runs, lambda value: value.run_id, "run id")
        summaries = _index(
            self.function_summaries,
            lambda value: value.summary_id,
            "function summary id",
        )
        if not occurrences or not roots or not edges:
            raise ArtifactError(
                "artifact occurrences, roots, and local edges must be nonempty"
            )

        for edge in self.local_edges:
            edge.summary.validate(self.declarations)
        for observation in self.observations:
            observation.after.validate(self.declarations)
        for application in self.summary_applications:
            application.after.validate(self.declarations)
        for summary in self.function_summaries:
            summary.summary.validate(self.declarations)
        _sorted(
            self.occurrences,
            lambda value: value.id.value,
            "artifact.occurrences",
        )
        _sorted(self.roots, lambda value: value.root_id, "artifact.roots")
        _sorted(
            self.local_edges,
            lambda value: (
                value.id.occurrence.value,
                value.id.outcome.value,
            ),
            "artifact.local_edges",
        )
        _sorted(
            self.observations,
            lambda value: value.observation_id,
            "artifact.observations",
        )
        _sorted(
            self.summary_applications,
            lambda value: value.application_id,
            "artifact.summary_applications",
        )
        _sorted(self.runs, lambda value: value.run_id, "artifact.runs")
        _sorted(
            self.function_summaries,
            lambda value: value.summary_id,
            "artifact.function_summaries",
        )

        sources: dict[int, StaticOccurrenceId] = {}
        for occurrence in self.occurrences:
            if occurrence.origin.image_sha256 != self.binary_id:
                raise ArtifactError(
                    "occurrence image does not match artifact binary"
                )
            prior = sources.setdefault(occurrence.origin.source, occurrence.id)
            if prior != occurrence.id:
                raise ArtifactError(
                    "one source address has multiple occurrence origins"
                )

        for root in self.roots:
            if root.entry_control not in sources:
                raise ArtifactError("root entry has no materialized occurrence")

        for edge in self.local_edges:
            occurrence = occurrences.get(edge.id.occurrence)
            if occurrence is None:
                raise ArtifactError("edge references unknown occurrence")
            if edge.source != occurrence.origin.source:
                raise ArtifactError("edge source disagrees with occurrence")
        edge_occurrences = {edge.id.occurrence for edge in self.local_edges}
        if edge_occurrences != set(occurrences):
            raise ArtifactError(
                "every occurrence must own at least one local edge"
            )

        for observation in self.observations:
            root = roots.get(observation.root_id)
            edge = edges.get(observation.edge_id)
            if root is None or edge is None:
                raise ArtifactError("observation references unknown root or edge")
            if observation.before.kind == "empty":
                if edge.source != root.entry_control:
                    raise ArtifactError(
                        "empty-prefix observation is not at its root"
                    )
            elif observation.before.end_control != edge.source:
                raise ArtifactError(
                    "observation prefix endpoint disagrees with edge source"
                )

        for summary in self.function_summaries:
            root = roots.get(summary.root_id)
            if root is None or root.function_id != summary.function_id:
                raise ArtifactError(
                    "function summary root/function identity disagrees"
                )
            for dependency in summary.dependency_summary_ids:
                if dependency == summary.summary_id:
                    raise ArtifactError("function summary depends on itself")
                if dependency not in summaries:
                    raise ArtifactError(
                        "function summary references unknown dependency"
                    )

        for application in self.summary_applications:
            if application.root_id not in roots:
                raise ArtifactError("summary application references unknown root")
            call_edge = edges.get(application.call_edge_id)
            if call_edge is None:
                raise ArtifactError(
                    "summary application references unknown call edge"
                )
            call_origin = occurrences[
                call_edge.id.occurrence
            ].origin
            if not isinstance(call_origin, DecodedInstructionEvidence):
                raise ArtifactError(
                    "summary application call edge must be decoded"
                )
            callee = summaries.get(application.callee_summary_id)
            if (
                callee is None
                or callee.function_id != application.callee_function_id
            ):
                raise ArtifactError(
                    "summary application callee identity disagrees"
                )
            callee_root = roots[callee.root_id]
            if call_edge.summary.target != Target(
                "address", callee_root.entry_control
            ):
                raise ArtifactError(
                    "summary application call target disagrees with callee root"
                )
            if (
                application.before.kind != "nonempty"
                or application.before.end_control != callee_root.entry_control
            ):
                raise ArtifactError(
                    "summary application prefix does not end at callee root"
                )
            if application.return_class == "ordinary":
                if application.after.target != application.continuation:
                    raise ArtifactError(
                        "ordinary summary application continuation disagrees "
                        "with after target"
                    )
            elif application.after.target == application.continuation:
                raise ArtifactError(
                    "nonordinary summary application reaches its ordinary "
                    "continuation"
                )

        seen_events: set[tuple[str, str]] = set()
        for run in self.runs:
            if run.root_id not in roots:
                raise ArtifactError("run references unknown root")
            if run.events[0].kind != "observation":
                raise ArtifactError("run must begin with a root observation")
            first_observation = observations.get(run.events[0].evidence_id)
            if first_observation is None or first_observation.before.kind != "empty":
                raise ArtifactError(
                    "run must begin with an empty-prefix observation"
                )
            prior_event: RunEvent | None = None
            for event_index, event in enumerate(run.events):
                key = (event.kind, event.evidence_id)
                if key in seen_events:
                    raise ArtifactError("evidence event appears in multiple runs")
                seen_events.add(key)
                evidence = (
                    observations.get(event.evidence_id)
                    if event.kind == "observation"
                    else applications.get(event.evidence_id)
                )
                if evidence is None or evidence.root_id != run.root_id:
                    raise ArtifactError(
                        "run event is missing or belongs to another root"
                    )
                if event.kind == "summary_application":
                    if prior_event is None or prior_event.kind != "observation":
                        raise ArtifactError(
                            "summary application must follow its call observation"
                        )
                    application = applications[event.evidence_id]
                    observation = observations[prior_event.evidence_id]
                    if observation.edge_id != application.call_edge_id:
                        raise ArtifactError(
                            "summary application does not follow its call edge"
                        )
                    if (
                        application.return_class == "nonordinary_control"
                        and event_index != len(run.events) - 1
                    ):
                        raise ArtifactError(
                            "nonordinary summary application must terminate its run"
                        )
                elif (
                    prior_event is not None
                    and prior_event.kind == "summary_application"
                ):
                    prior_application = applications[prior_event.evidence_id]
                    assert isinstance(prior_application.continuation.value, int)
                    observation = observations[event.evidence_id]
                    if (
                        prior_application.return_class != "ordinary"
                        or observation.before.end_control
                        != prior_application.continuation.value
                    ):
                        raise ArtifactError(
                            "observation does not resume an ordinary summary "
                            "application at its continuation"
                        )
                prior_event = event

        expected_events = {
            ("observation", identifier) for identifier in observations
        } | {
            ("summary_application", identifier) for identifier in applications
        }
        if seen_events != expected_events:
            raise ArtifactError("runs do not partition contextual evidence")

    def to_data(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "binary_id": self.binary_id,
            "declarations": [
                declaration.to_data() for declaration in self.declarations
            ],
            "occurrences": [value.to_data() for value in self.occurrences],
            "roots": [value.to_data() for value in self.roots],
            "local_edges": [value.to_data() for value in self.local_edges],
            "observations": [value.to_data() for value in self.observations],
            "summary_applications": [
                value.to_data() for value in self.summary_applications
            ],
            "runs": [value.to_data() for value in self.runs],
            "function_summaries": [
                value.to_data() for value in self.function_summaries
            ],
        }

    def canonical_json(self) -> bytes:
        return json.dumps(
            self.to_data(),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    @classmethod
    def from_data(cls, value: Any) -> ExtractionArtifact:
        obj = _object(value, "artifact")
        _fields(
            obj,
            {
                "schema",
                "binary_id",
                "declarations",
                "occurrences",
                "roots",
                "local_edges",
                "observations",
                "summary_applications",
                "runs",
                "function_summaries",
            },
            "artifact",
        )
        if obj["schema"] != cls.schema:
            raise ArtifactError("unsupported artifact schema")
        return cls(
            binary_id=_sha256(obj["binary_id"], "artifact.binary_id"),
            declarations=tuple(
                Declaration.from_data(item, "artifact.declarations[]")
                for item in _array(
                    obj["declarations"], "artifact.declarations"
                )
            ),
            occurrences=tuple(
                Occurrence.from_data(item)
                for item in _array(obj["occurrences"], "artifact.occurrences")
            ),
            roots=tuple(
                Root.from_data(item)
                for item in _array(obj["roots"], "artifact.roots")
            ),
            local_edges=tuple(
                LocalEdge.from_data(item)
                for item in _array(obj["local_edges"], "artifact.local_edges")
            ),
            observations=tuple(
                ContextObservation.from_data(item)
                for item in _array(
                    obj["observations"], "artifact.observations"
                )
            ),
            summary_applications=tuple(
                SummaryApplication.from_data(item)
                for item in _array(
                    obj["summary_applications"],
                    "artifact.summary_applications",
                )
            ),
            runs=tuple(
                ContextRun.from_data(item)
                for item in _array(obj["runs"], "artifact.runs")
            ),
            function_summaries=tuple(
                FunctionSummary.from_data(item)
                for item in _array(
                    obj["function_summaries"],
                    "artifact.function_summaries",
                )
            ),
        )

    @classmethod
    def parse(cls, payload: bytes | str) -> ExtractionArtifact:
        def reject_duplicate_pairs(
            pairs: list[tuple[str, Any]],
        ) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise ArtifactError(f"duplicate JSON key: {key}")
                result[key] = value
            return result

        try:
            value = json.loads(
                payload,
                object_pairs_hook=reject_duplicate_pairs,
                parse_float=lambda value: (_ for _ in ()).throw(
                    ArtifactError(f"floating-point value forbidden: {value}")
                ),
                parse_constant=lambda value: (_ for _ in ()).throw(
                    ArtifactError(f"non-finite value forbidden: {value}")
                ),
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ArtifactError(f"invalid JSON: {error}") from error
        return cls.from_data(value)
