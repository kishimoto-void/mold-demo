"""
Joint Program - 思考回路モールドとミドルモールドの接続境界
============================================================

役割:
    resources.py の思考回路リソースを、ミドルモールドが扱う
    中立的な契約データへ変換する。依存関係の検証とエラー境界も担当する。

非担当:
    - LLM/APIの呼び出し
    - 思考そのものの実行
    - Persona Seed の管理
    - 用途判断や回路順序の自動最適化

依存:
    resources.py（同じディレクトリに配置）
    Python 標準ライブラリのみ

基本方針:
    - ミドルモールドは ResourceRegistry の内部構造を直接参照しない
    - 受け渡しデータは dataclass の契約型で固定する
    - 入力エラーを明示的な JointError として境界内で報告する
    - 暗黙の補完や自動的な回路並べ替えは行わない
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

try:
    # パッケージとしての利用
    from .resources import (
        RESOURCE_SCHEMA_VERSION,
        ResourceKind,
        ResourceRegistry,
        ThinkingCircuit,
        ThinkingResource,
        DEFAULT_REGISTRY,
    )
except ImportError:
    # 同じディレクトリを Python path に置く単体利用
    from resources import (
        RESOURCE_SCHEMA_VERSION,
        ResourceKind,
        ResourceRegistry,
        ThinkingCircuit,
        ThinkingResource,
        DEFAULT_REGISTRY,
    )


JOINT_CONTRACT_VERSION = "1.0.0"


class JointErrorCode(str, Enum):
    """接続境界で扱うエラー分類。"""

    INVALID_REQUEST = "invalid_request"
    RESOURCE_NOT_FOUND = "resource_not_found"
    RESOURCE_DISABLED = "resource_disabled"
    CONTRACT_VIOLATION = "contract_violation"


class JointError(ValueError):
    """接続境界で発生した、呼び出し側が処理可能なエラー。"""

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


@dataclass(frozen=True)
class ResourceSpec:
    """ミドルモールドに公開する、安定したリソース契約。"""

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
    """ミドルモールドへ渡す、順序付きプロセスの契約。"""

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


class JointProgram:
    """
    思考回路モールドとミドルモールドの接続アダプター。

    middle mold 側は get_resource_spec() / build_process() の戻り値だけを
    利用する。resources.py のクラスを下流に露出させない。
    """

    def __init__(self, registry: Optional[ResourceRegistry] = None) -> None:
        self._registry = registry if registry is not None else DEFAULT_REGISTRY

    @staticmethod
    def _to_resource_spec(resource: ThinkingResource) -> ResourceSpec:
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
        """IDから有効な回路部品を取得し、中立契約に変換する。"""
        if not isinstance(resource_id, str) or not resource_id.strip():
            raise JointError(
                JointErrorCode.INVALID_REQUEST,
                "resource_id must be a non-empty string",
            )
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
        """
        指定順序でプロセス契約を作る。
        順序変更・重複除去・不足リソースの補完はしない。
        """
        if isinstance(resource_ids, (str, bytes)) or not resource_ids:
            raise JointError(
                JointErrorCode.INVALID_REQUEST,
                "resource_ids must be a non-empty sequence of IDs",
            )
        if not isinstance(name, str) or not name.strip():
            raise JointError(
                JointErrorCode.INVALID_REQUEST,
                "name must be a non-empty string",
            )

        ids = tuple(resource_ids)
        if any(not isinstance(item, str) or not item.strip() for item in ids):
            raise JointError(
                JointErrorCode.INVALID_REQUEST,
                "every resource ID must be a non-empty string",
            )
        if len(set(ids)) != len(ids):
            raise JointError(
                JointErrorCode.INVALID_REQUEST,
                "duplicate resource IDs are not allowed",
            )

        specs = tuple(self.get_resource_spec(resource_id) for resource_id in ids)
        normalized_id = process_id or name.strip().lower().replace(" ", "_")
        if not normalized_id.strip():
            raise JointError(
                JointErrorCode.INVALID_REQUEST,
                "process_id must not be empty",
            )

        return ProcessSpec(
            contract_version=JOINT_CONTRACT_VERSION,
            process_id=normalized_id,
            name=name,
            description=description,
            resource_ids=ids,
            resources=specs,
        )

    def validate_process(self, process: ProcessSpec) -> Tuple[str, ...]:
        """契約オブジェクトの基本整合性を検証し、問題点を返す。"""
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
                problems.append(
                    f"unsupported resource contract: {resource.resource_id}"
                )
            if not resource.steps:
                problems.append(f"resource has no steps: {resource.resource_id}")
        return tuple(problems)

    def export_process(self, process: ProcessSpec) -> Dict[str, Any]:
        """検証済みの契約をJSON化可能な辞書へ変換する。"""
        problems = self.validate_process(process)
        if problems:
            raise JointError(
                JointErrorCode.CONTRACT_VIOLATION,
                "; ".join(problems),
            )
        return process.to_dict()


DEFAULT_JOINT = JointProgram()


def get_resource_spec(resource_id: str) -> ResourceSpec:
    """簡易API: リソース契約を取得する。"""
    return DEFAULT_JOINT.get_resource_spec(resource_id)


def build_process(
    resource_ids: Sequence[str],
    *,
    name: str,
    process_id: Optional[str] = None,
    description: str = "",
) -> ProcessSpec:
    """簡易API: ミドルモールド向けプロセス契約を作成する。"""
    return DEFAULT_JOINT.build_process(
        resource_ids,
        name=name,
        process_id=process_id,
        description=description,
    )


if __name__ == "__main__":
    joint = JointProgram()
    process = joint.build_process(
        ["decompose", "hypothesis", "verify", "uncertainty_check", "converge"],
        name="careful_analysis",
        description="構造化して仮説を検証し、不確実性を残して統合する。",
    )
    issues = joint.validate_process(process)
    if issues:
        raise SystemExit("Contract validation failed: " + "; ".join(issues))

    payload = joint.export_process(process)
    print(f"Joint Program v{JOINT_CONTRACT_VERSION}")
    print(f"Resource schema: {RESOURCE_SCHEMA_VERSION}")
    print(f"Process: {payload['process_id']}")
    print("Pipeline: " + " -> ".join(payload["resource_ids"]))
    print("Contract validation: OK")
