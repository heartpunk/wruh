"""Strict, engine-neutral extraction artifacts for the pragmatic C1 sprint."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from ayxg.expr import ArtifactError, Declaration, TermSort, TypedExpr

_ID_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._:-]*\Z")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_HEX_BYTES_RE = re.compile(r"(?:[0-9a-f]{2})+\Z")
_U64_MAX = (1 << 64) - 1
_FAULT_KIND_PAIRS = {
    ("Ijk_SigFPE_IntDiv", "integer_division"),
    ("Ijk_SigILL", "invalid_opcode"),
    ("Ijk_SigTRAP", "signal_trap"),
    ("Ijk_SigTRAP", "general_protection"),
}


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
    object_offset: int | None = None
    mapped_base: int | None = None

    kind = "decoded_instruction"

    def __post_init__(self) -> None:
        _sha256(self.image_sha256, "decoded.image_sha256")
        _u64(self.canonical_address, "decoded.canonical_address")
        if (self.object_offset is None) != (self.mapped_base is None):
            raise ArtifactError("decoded object offset and mapped base must occur together")
        if self.object_offset is not None:
            _u64(self.object_offset, "decoded.object_offset")
            _u64(self.mapped_base, "decoded.mapped_base")
            if self.object_offset + self.mapped_base != self.canonical_address:
                raise ArtifactError("decoded object mapping does not match address")
        if not _HEX_BYTES_RE.fullmatch(self.instruction_bytes):
            raise ArtifactError(
                "decoded.instruction_bytes must be nonempty lowercase hex bytes"
            )
        _identifier(self.architecture, "decoded.architecture")
        _identifier(self.decode_mode, "decoded.decode_mode")
        _text(self.instruction_identity, "decoded.instruction_identity")

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
            **({"object_offset": self.object_offset, "mapped_base": self.mapped_base}
               if self.object_offset is not None else {}),
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
            } | ({"object_offset", "mapped_base"} if "object_offset" in obj or "mapped_base" in obj else set()),
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
            object_offset=obj.get("object_offset"),
            mapped_base=obj.get("mapped_base"),
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
        _identifier(self.symbol, "primitive.symbol")
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
            symbol=_identifier(obj["symbol"], "primitive.symbol"),
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
class LocalEdge:
    id: EdgeId
    source: int
    summary: StepSummary
    jumpkind: str | None = None
    fault_kind: str | None = None

    def __post_init__(self) -> None:
        _u64(self.source, "local_edge.source")
        if (self.jumpkind is None) != (self.fault_kind is None):
            raise ArtifactError(
                "local_edge.jumpkind and local_edge.fault_kind must appear together"
            )
        if self.jumpkind is not None:
            _identifier(self.jumpkind, "local_edge.jumpkind")
            if (self.jumpkind, self.fault_kind) not in _FAULT_KIND_PAIRS:
                raise ArtifactError(
                    "local_edge fault_kind conflicts with jumpkind"
                )

    def to_data(self) -> dict[str, Any]:
        result = {
            "edge_id": self.id.to_data(),
            "source": self.source,
            "summary": self.summary.to_data(),
        }
        if self.jumpkind is not None:
            result["jumpkind"] = self.jumpkind
            result["fault_kind"] = self.fault_kind
        return result

    @classmethod
    def from_data(cls, value: Any) -> LocalEdge:
        obj = _object(value, "local_edge")
        expected = {"edge_id", "source", "summary"}
        if "jumpkind" in obj:
            expected.add("jumpkind")
        if "fault_kind" in obj:
            expected.add("fault_kind")
        _fields(obj, expected, "local_edge")
        return cls(
            id=EdgeId.from_data(obj["edge_id"], "local_edge.edge_id"),
            source=_u64(obj["source"], "local_edge.source"),
            summary=StepSummary.from_data(
                obj["summary"], "local_edge.summary"
            ),
            jumpkind=(
                _identifier(obj["jumpkind"], "local_edge.jumpkind")
                if "jumpkind" in obj
                else None
            ),
            fault_kind=(
                _text(obj["fault_kind"], "local_edge.fault_kind")
                if "fault_kind" in obj
                else None
            ),
        )
