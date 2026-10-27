"""
Joint Program — Reasoning Circuit Mold
Version: 0.1.0 (prototype)

Responsibilities:
- Assemble explicitly ordered Top / Middle / Bottom mold contracts.
- Validate TM, MB, and TMB boundaries without reordering or auto-repair.
- Keep assembly/validation separate from LLM execution.
- Preserve the legacy resource-to-process API when `resources.py` is importable.

Hypotheses (not yet normative):
- Interface compatibility is based on named data fields.
- A downstream required input must be provided by the immediately preceding mold.
- TMB end-to-end input availability is checked against external_inputs.
- Type-level validation is deferred until interface field types are specified.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple


JOINT_CONTRACT_VERSION = "1.1.0"
ASSEMBLY_SCHEMA_VERSION = "0.1.0"


class JointErrorCode(str, Enum):
    INVALID_REQUEST = "invalid_request"
    RESOURCE_NOT_FOUND = "resource_not_found"
    RESOURCE_DISABLED = "resource_disabled"
    CONTRACT_VIOLATION = "contract_violation"
    CONNECTION_MISMATCH = "connection_mismatch"


class JointError(ValueError):
    """Expected, caller-handleable error raised at the joint boundary."""

    def __init__(
        self,
        code: JointErrorCode,
        message: str,
        *,
        resource_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.resource_id = resource_id

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "code": self.code.value,
            "message": str(self),
            "resource_id": self.resource_id,
        }


class ConnectionMode(str, Enum):
    TM = "TM"
    MB = "MB"
    TMB = "TMB"


class MoldStage(str, Enum):
    TOP = "TOP"
    MIDDLE = "MIDDLE"
    BOTTOM = "BOTTOM"


@dataclass(frozen=True)
class MoldContract:
    """
    Neutral interface contract for a mold.

    `inputs` lists all accepted field names.
    `required_inputs` lists the subset that must be supplied.
    `outputs` lists fields this mold promises to provide.
    The contract describes data interfaces, not the mold's internal algorithm.
    """

    mold_id: str
    stage: MoldStage
    version: str
    inputs: Tuple[str, ...]
    outputs: Tuple[str, ...]
    required_inputs: Tuple[str, ...] = ()
    contract_version: str = JOINT_CONTRACT_VERSION
    enabled: bool = True
    metadata: Tuple[Tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("mold_id", "version", "contract_version"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if not isinstance(self.stage, MoldStage):
            raise ValueError("stage must be a MoldStage")
        for collection_name in ("inputs", "outputs", "required_inputs"):
            values = getattr(self, collection_name)
            if isinstance(values, (str, bytes)):
                raise ValueError(f"{collection_name} must be a sequence of field names")
            if any(not isinstance(x, str) or not x.strip() for x in values):
                raise ValueError(f"{collection_name} must contain non-empty strings")
            if len(set(values)) != len(values):
                raise ValueError(f"{collection_name} must not contain duplicates")
        if not set(self.required_inputs).issubset(set(self.inputs)):
            raise ValueError("required_inputs must be a subset of inputs")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mold_id": self.mold_id,
            "stage": self.stage.value,
            "version": self.version,
            "contract_version": self.contract_version,
            "inputs": list(self.inputs),
            "required_inputs": list(self.required_inputs),
            "outputs": list(self.outputs),
            "enabled": self.enabled,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class BoundaryReport:
    upstream_id: str
    downstream_id: str
    provided: Tuple[str, ...]
    required: Tuple[str, ...]
    missing: Tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.missing

    def to_dict(self) -> Dict[str, Any]:
        return {
            "upstream_id": self.upstream_id,
            "downstream_id": self.downstream_id,
            "provided": list(self.provided),
            "required": list(self.required),
            "missing": list(self.missing),
            "passed": self.passed,
        }


@dataclass(frozen=True)
class AssemblySpec:
    schema_version: str
    joint_contract_version: str
    assembly_id: str
    mode: ConnectionMode
    molds: Tuple[MoldContract, ...]
    boundaries: Tuple[BoundaryReport, ...]
    external_inputs: Tuple[str, ...]
    outputs: Tuple[str, ...]
    validation_issues: Tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        return not self.validation_issues and all(b.passed for b in self.boundaries)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "joint_contract_version": self.joint_contract_version,
            "assembly_id": self.assembly_id,
            "mode": self.mode.value,
            "molds": [m.to_dict() for m in self.molds],
            "boundaries": [b.to_dict() for b in self.boundaries],
            "external_inputs": list(self.external_inputs),
            "outputs": list(self.outputs),
            "validation_issues": list(self.validation_issues),
            "valid": self.valid,
        }


class JointProgram:
    """Assembly and contract-validation boundary; does not execute molds."""

    _EXPECTED_STAGES = {
        ConnectionMode.TM: (MoldStage.TOP, MoldStage.MIDDLE),
        ConnectionMode.MB: (MoldStage.MIDDLE, MoldStage.BOTTOM),
        ConnectionMode.TMB: (MoldStage.TOP, MoldStage.MIDDLE, MoldStage.BOTTOM),
    }

    def assemble(
        self,
        molds: Sequence[MoldContract],
        *,
        mode: ConnectionMode = ConnectionMode.TMB,
        assembly_id: str = "reasoning_circuit",
        external_inputs: Sequence[str] = ("user_input",),
        expected_outputs: Optional[Sequence[str]] = None,
    ) -> AssemblySpec:
        if isinstance(molds, (str, bytes)) or not molds:
            raise JointError(JointErrorCode.INVALID_REQUEST, "molds must be a non-empty sequence")
        if not isinstance(mode, ConnectionMode):
            raise JointError(JointErrorCode.INVALID_REQUEST, "mode must be a ConnectionMode")
        if not isinstance(assembly_id, str) or not assembly_id.strip():
            raise JointError(JointErrorCode.INVALID_REQUEST, "assembly_id must be a non-empty string")
        if isinstance(external_inputs, (str, bytes)) or any(
            not isinstance(x, str) or not x.strip() for x in external_inputs
        ):
            raise JointError(JointErrorCode.INVALID_REQUEST, "external_inputs must contain non-empty field names")
        if len(set(external_inputs)) != len(tuple(external_inputs)):
            raise JointError(JointErrorCode.INVALID_REQUEST, "external_inputs must not contain duplicates")

        mold_tuple = tuple(molds)
        if any(not isinstance(mold, MoldContract) for mold in mold_tuple):
            raise JointError(JointErrorCode.INVALID_REQUEST, "every mold must be a MoldContract")

        issues = []
        expected_stages = self._EXPECTED_STAGES[mode]
        actual_stages = tuple(m.stage for m in mold_tuple)
        if actual_stages != expected_stages:
            issues.append(
                f"stage order mismatch for {mode.value}: expected "
                f"{' -> '.join(s.value for s in expected_stages)}, got "
                f"{' -> '.join(s.value for s in actual_stages)}"
            )

        ids = tuple(m.mold_id for m in mold_tuple)
        if len(set(ids)) != len(ids):
            issues.append("duplicate mold_id")
        for mold in mold_tuple:
            if not mold.enabled:
                issues.append(f"mold is disabled: {mold.mold_id}")
            if mold.contract_version != JOINT_CONTRACT_VERSION:
                issues.append(
                    f"unsupported joint contract version for {mold.mold_id}: "
                    f"{mold.contract_version}"
                )

        boundaries = []
        for upstream, downstream in zip(mold_tuple, mold_tuple[1:]):
            missing = tuple(sorted(set(downstream.required_inputs) - set(upstream.outputs)))
            boundaries.append(
                BoundaryReport(
                    upstream_id=upstream.mold_id,
                    downstream_id=downstream.mold_id,
                    provided=tuple(upstream.outputs),
                    required=tuple(downstream.required_inputs),
                    missing=missing,
                )
            )
            if missing:
                issues.append(
                    f"connection mismatch {upstream.mold_id} -> {downstream.mold_id}: "
                    f"missing {', '.join(missing)}"
                )

        # Whole-configuration checks apply to TMB. Pair modes validate their
        # own stages and boundary only, by design.
        if mode == ConnectionMode.TMB and mold_tuple:
            missing_external = tuple(
                sorted(set(mold_tuple[0].required_inputs) - set(external_inputs))
            )
            if missing_external:
                issues.append(
                    "external inputs missing for TOP: " + ", ".join(missing_external)
                )
            final_outputs = tuple(mold_tuple[-1].outputs)
            if not final_outputs:
                issues.append("BOTTOM exposes no outputs")
            if expected_outputs is not None:
                missing_expected = tuple(sorted(set(expected_outputs) - set(final_outputs)))
                if missing_expected:
                    issues.append(
                        "expected outputs missing from BOTTOM: " + ", ".join(missing_expected)
                    )
        else:
            final_outputs = tuple(mold_tuple[-1].outputs)

        spec = AssemblySpec(
            schema_version=ASSEMBLY_SCHEMA_VERSION,
            joint_contract_version=JOINT_CONTRACT_VERSION,
            assembly_id=assembly_id.strip(),
            mode=mode,
            molds=mold_tuple,
            boundaries=tuple(boundaries),
            external_inputs=tuple(external_inputs),
            outputs=final_outputs,
            validation_issues=tuple(issues),
        )
        return spec

    def validate(self, spec: AssemblySpec) -> Tuple[str, ...]:
        """Recompute structural checks; return issues instead of auto-repairing."""
        if not isinstance(spec, AssemblySpec):
            raise JointError(JointErrorCode.INVALID_REQUEST, "spec must be an AssemblySpec")
        rebuilt = self.assemble(
            spec.molds,
            mode=spec.mode,
            assembly_id=spec.assembly_id,
            external_inputs=spec.external_inputs,
            expected_outputs=spec.outputs if spec.mode == ConnectionMode.TMB else None,
        )
        return rebuilt.validation_issues

    def export(self, spec: AssemblySpec) -> Dict[str, Any]:
        issues = self.validate(spec)
        if issues:
            raise JointError(JointErrorCode.CONTRACT_VIOLATION, "; ".join(issues))
        return spec.to_dict()


# Optional backward-compatible resource adapter. This preserves the existing
# resource-to-process contract when the caller supplies a registry or when the
# legacy `resources.py` module is importable.
try:
    from .resources import (
        RESOURCE_SCHEMA_VERSION,
        ResourceRegistry,
        ThinkingResource,
        DEFAULT_REGISTRY,
    )
except (ImportError, ModuleNotFoundError):
    try:
        from resources import (
            RESOURCE_SCHEMA_VERSION,
            ResourceRegistry,
            ThinkingResource,
            DEFAULT_REGISTRY,
        )
    except (ImportError, ModuleNotFoundError):
        RESOURCE_SCHEMA_VERSION = "unavailable"
        ResourceRegistry = Any  # type: ignore[misc,assignment]
        ThinkingResource = Any  # type: ignore[misc,assignment]
        DEFAULT_REGISTRY = None


@dataclass(frozen=True)
class ResourceSpec:
    contract_version: str
    resource_id: str
    name: str
    kind: str
    purpose: str
    description: str
    steps: Tuple[str, ...]
    inputs: Tuple[str, ...]
    outputs: Tuple[str, ...]
    tags: Tuple[str, ...]
    constraints: Tuple[str, ...]
    resource_version: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "resource_id": self.resource_id,
            "name": self.name,
            "kind": self.kind,
            "purpose": self.purpose,
            "description": self.description,
            "steps": list(self.steps),
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "tags": list(self.tags),
            "constraints": list(self.constraints),
            "resource_version": self.resource_version,
        }


@dataclass(frozen=True)
class ProcessSpec:
    contract_version: str
    process_id: str
    name: str
    description: str
    resource_ids: Tuple[str, ...]
    resources: Tuple[ResourceSpec, ...]
    inputs: Tuple[str, ...] = ("user_input",)
    outputs: Tuple[str, ...] = ("result", "rationale", "uncertainties")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "process_id": self.process_id,
            "name": self.name,
            "description": self.description,
            "resource_ids": list(self.resource_ids),
            "resources": [item.to_dict() for item in self.resources],
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
        }


class LegacyResourceJoint:
    """Backward-compatible adapter for the existing ResourceRegistry API."""

    def __init__(self, registry: Optional[Any] = None) -> None:
        if registry is None:
            registry = DEFAULT_REGISTRY
        if registry is None:
            raise JointError(
                JointErrorCode.RESOURCE_NOT_FOUND,
                "resources.py is not importable; pass a ResourceRegistry explicitly",
            )
        self._registry = registry

    @staticmethod
    def _to_resource_spec(resource: Any) -> ResourceSpec:
        return ResourceSpec(
            contract_version=JOINT_CONTRACT_VERSION,
            resource_id=resource.resource_id,
            name=resource.name,
            kind=resource.kind.value,
            purpose=resource.purpose,
            description=resource.description,
            steps=tuple(resource.steps),
            inputs=tuple(resource.inputs),
            outputs=tuple(resource.outputs),
            tags=tuple(sorted(resource.tags)),
            constraints=tuple(resource.constraints),
            resource_version=resource.version,
        )

    def get_resource_spec(self, resource_id: str) -> ResourceSpec:
        if not isinstance(resource_id, str) or not resource_id.strip():
            raise JointError(JointErrorCode.INVALID_REQUEST, "resource_id must be a non-empty string")
        try:
            resource = self._registry.get(resource_id)
        except KeyError as exc:
            raise JointError(
                JointErrorCode.RESOURCE_NOT_FOUND,
                f"resource not found: {resource_id}",
                resource_id=resource_id,
            ) from exc
        if not resource.enabled:
            raise JointError(
                JointErrorCode.RESOURCE_DISABLED,
                f"resource is disabled: {resource_id}",
                resource_id=resource_id,
            )
        return self._to_resource_spec(resource)

    def build_process(
        self,
        resource_ids: Sequence[str],
        *,
        name: str,
        process_id: Optional[str] = None,
        description: str = "",
    ) -> ProcessSpec:
        if isinstance(resource_ids, (str, bytes)) or not resource_ids:
            raise JointError(JointErrorCode.INVALID_REQUEST, "resource_ids must be a non-empty sequence of IDs")
        if not isinstance(name, str) or not name.strip():
            raise JointError(JointErrorCode.INVALID_REQUEST, "name must be a non-empty string")
        ids = tuple(resource_ids)
        if any(not isinstance(item, str) or not item.strip() for item in ids):
            raise JointError(JointErrorCode.INVALID_REQUEST, "every resource ID must be a non-empty string")
        if len(set(ids)) != len(ids):
            raise JointError(JointErrorCode.INVALID_REQUEST, "duplicate resource IDs are not allowed")
        specs = tuple(self.get_resource_spec(resource_id) for resource_id in ids)
        normalized_id = process_id or name.strip().lower().replace(" ", "_")
        if not normalized_id.strip():
            raise JointError(JointErrorCode.INVALID_REQUEST, "process_id must not be empty")
        return ProcessSpec(
            contract_version=JOINT_CONTRACT_VERSION,
            process_id=normalized_id,
            name=name,
            description=description,
            resource_ids=ids,
            resources=specs,
        )

    def validate_process(self, process: ProcessSpec) -> Tuple[str, ...]:
        problems = []
        if process.contract_version != JOINT_CONTRACT_VERSION:
            problems.append("unsupported contract_version")
        if not process.process_id.strip():
            problems.append("process_id is empty")
        if not process.resource_ids:
            problems.append("resource_ids is empty")
        if len(process.resource_ids) != len(process.resources):
            problems.append("resource_ids/resources length mismatch")
        if tuple(item.resource_id for item in process.resources) != process.resource_ids:
            problems.append("resource order or identity mismatch")
        for resource in process.resources:
            if resource.contract_version != JOINT_CONTRACT_VERSION:
                problems.append(f"unsupported resource contract: {resource.resource_id}")
            if not resource.steps:
                problems.append(f"resource has no steps: {resource.resource_id}")
        return tuple(problems)

    def export_process(self, process: ProcessSpec) -> Dict[str, Any]:
        problems = self.validate_process(process)
        if problems:
            raise JointError(JointErrorCode.CONTRACT_VIOLATION, "; ".join(problems))
        return process.to_dict()


def demo_contracts() -> Tuple[MoldContract, MoldContract, MoldContract]:
    """Small explicit example; field names are illustrative, not normative."""
    top = MoldContract(
        mold_id="top-default",
        stage=MoldStage.TOP,
        version="0.1.0",
        inputs=("user_input",),
        required_inputs=("user_input",),
        outputs=("goal", "constraints", "context"),
    )
    middle = MoldContract(
        mold_id="middle-default",
        stage=MoldStage.MIDDLE,
        version="0.1.0",
        inputs=("goal", "constraints", "context"),
        required_inputs=("goal", "constraints"),
        outputs=("process_plan", "knowns", "hypotheses", "unknowns"),
    )
    bottom = MoldContract(
        mold_id="bottom-default",
        stage=MoldStage.BOTTOM,
        version="0.1.0",
        inputs=("process_plan", "knowns", "hypotheses", "unknowns"),
        required_inputs=("process_plan",),
        outputs=("result", "evidence_summary", "uncertainties"),
    )
    return top, middle, bottom


if __name__ == "__main__":
    joint = JointProgram()
    assembly = joint.assemble(demo_contracts(), mode=ConnectionMode.TMB)
    if not assembly.valid:
        raise SystemExit("Assembly validation failed:\n- " + "\n- ".join(assembly.validation_issues))
    print(f"Joint Program v{JOINT_CONTRACT_VERSION}")
    print("Pipeline: " + " -> ".join(m.stage.value for m in assembly.molds))
    print("Boundaries checked:", len(assembly.boundaries))
    print("Whole-configuration validation: OK")
    print("Export schema:", ASSEMBLY_SCHEMA_VERSION)
