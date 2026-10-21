"""
思考回路モールド - Resources
================================

目的:
    思考プロセスを「再利用可能なリソース」として定義・管理する。
    このモジュールは回路の定義・検索・合成用データを扱い、
    LLMの呼び出しや実際の推論実行は担当しない。

設計方針:
    - 標準ライブラリのみで動作
    - 思考回路は固定手順ではなく、用途に応じて選択・合成できる部品
    - 未知・保留・複数仮説を残せる
    - 内部推論の逐語的な開示ではなく、結論・根拠・不確実性を出力対象にする
    - Persona Seed / Purpose / LLM 実行層とは疎結合にする

使い方:
    from resources import DEFAULT_REGISTRY, ResourceKind

    resource = DEFAULT_REGISTRY.get("decompose")
    candidates = DEFAULT_REGISTRY.search(tags={"analysis"})
    circuit = DEFAULT_REGISTRY.compose(
        ["decompose", "hypothesis", "verify", "uncertainty_check"],
        name="careful_analysis",
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


RESOURCE_SCHEMA_VERSION = "1.0.0"


class ResourceKind(str, Enum):
    """リソースの役割。"""

    THINKING_CIRCUIT = "thinking_circuit"
    EVALUATION = "evaluation"
    CONTROL = "control"
    OUTPUT = "output"


@dataclass(frozen=True)
class ThinkingResource:
    """思考回路を記述する不変データ。実行機能は持たない。"""

    resource_id: str
    name: str
    description: str
    kind: ResourceKind = ResourceKind.THINKING_CIRCUIT
    purpose: str = ""
    steps: Tuple[str, ...] = ()
    inputs: Tuple[str, ...] = ("user_input",)
    outputs: Tuple[str, ...] = ("result", "rationale", "uncertainties")
    tags: frozenset[str] = frozenset()
    constraints: Tuple[str, ...] = ()
    version: str = "1.0.0"
    enabled: bool = True
    metadata: Tuple[Tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.resource_id or not self.resource_id.strip():
            raise ValueError("resource_id must not be empty")
        if not self.name or not self.name.strip():
            raise ValueError("name must not be empty")
        if not self.steps:
            raise ValueError("steps must contain at least one step")
        if len(set(self.steps)) != len(self.steps):
            raise ValueError(f"duplicate steps in resource: {self.resource_id}")

    def to_prompt_spec(self) -> Dict[str, object]:
        """他の層がプロンプト等へ変換できる中立的な仕様を返す。"""
        return {
            "schema_version": RESOURCE_SCHEMA_VERSION,
            "resource_id": self.resource_id,
            "name": self.name,
            "description": self.description,
            "kind": self.kind.value,
            "purpose": self.purpose,
            "steps": list(self.steps),
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "tags": sorted(self.tags),
            "constraints": list(self.constraints),
            "version": self.version,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ThinkingCircuit:
    """複数のリソースを順序付きで束ねた合成回路。"""

    circuit_id: str
    name: str
    resource_ids: Tuple[str, ...]
    description: str = ""
    inputs: Tuple[str, ...] = ("user_input",)
    outputs: Tuple[str, ...] = ("result", "rationale", "uncertainties")

    def __post_init__(self) -> None:
        if not self.circuit_id.strip():
            raise ValueError("circuit_id must not be empty")
        if not self.resource_ids:
            raise ValueError("resource_ids must contain at least one resource")
        if len(set(self.resource_ids)) != len(self.resource_ids):
            raise ValueError(f"duplicate resource ids in circuit: {self.circuit_id}")


class ResourceRegistry:
    """思考リソースの登録・取得・検索・合成を管理する。"""

    def __init__(self, resources: Optional[Iterable[ThinkingResource]] = None) -> None:
        self._resources: Dict[str, ThinkingResource] = {}
        if resources:
            for resource in resources:
                self.register(resource)

    def register(self, resource: ThinkingResource, *, replace: bool = False) -> None:
        if resource.resource_id in self._resources and not replace:
            raise KeyError(f"resource already registered: {resource.resource_id}")
        self._resources[resource.resource_id] = resource

    def get(self, resource_id: str) -> ThinkingResource:
        try:
            return self._resources[resource_id]
        except KeyError as exc:
            raise KeyError(f"unknown resource: {resource_id}") from exc

    def list_resources(
        self,
        *,
        kind: Optional[ResourceKind] = None,
        enabled_only: bool = True,
    ) -> List[ThinkingResource]:
        items = list(self._resources.values())
        if kind is not None:
            items = [item for item in items if item.kind == kind]
        if enabled_only:
            items = [item for item in items if item.enabled]
        return sorted(items, key=lambda item: item.resource_id)

    def search(
        self,
        *,
        tags: Optional[Set[str]] = None,
        query: Optional[str] = None,
        enabled_only: bool = True,
    ) -> List[ThinkingResource]:
        """タグはすべて一致、queryはID/名前/説明/目的に部分一致。"""
        needle = query.casefold().strip() if query else None
        results = []
        for item in self._resources.values():
            if enabled_only and not item.enabled:
                continue
            if tags and not tags.issubset(item.tags):
                continue
            haystack = " ".join(
                (item.resource_id, item.name, item.description, item.purpose)
            ).casefold()
            if needle and needle not in haystack:
                continue
            results.append(item)
        return sorted(results, key=lambda item: item.resource_id)

    def compose(
        self,
        resource_ids: Sequence[str],
        *,
        name: str,
        circuit_id: Optional[str] = None,
        description: str = "",
    ) -> ThinkingCircuit:
        """存在し、enabledなリソースだけで順序付き回路を構成する。"""
        ids = tuple(resource_ids)
        if not ids:
            raise ValueError("at least one resource_id is required")
        for resource_id in ids:
            resource = self.get(resource_id)
            if not resource.enabled:
                raise ValueError(f"resource is disabled: {resource_id}")
        normalized_id = circuit_id or name.strip().lower().replace(" ", "_")
        return ThinkingCircuit(
            circuit_id=normalized_id,
            name=name,
            resource_ids=ids,
            description=description,
        )

    def __len__(self) -> int:
        return len(self._resources)

    def __contains__(self, resource_id: str) -> bool:
        return resource_id in self._resources


_COMMON_CONSTRAINTS = (
    "不足情報を事実として補完しない。不足は不足として示す。",
    "必要に応じて複数の仮説を保持し、早すぎる収束を避ける。",
    "結論と、結論を支える要点・根拠・不確実性を区別する。",
    "ユーザーの目的に不要な工程は省略してよい。",
)


DEFAULT_RESOURCES: Tuple[ThinkingResource, ...] = (
    ThinkingResource(
        resource_id="decompose",
        name="分解",
        description="複雑な課題を、扱える単位と依存関係に分ける。",
        purpose="問題の構造化、学習計画、設計、デバッグ",
        steps=(
            "目的と完了条件を特定する",
            "課題を要素・制約・依存関係に分ける",
            "未確定事項と既知事項を区別する",
            "次に扱う最小単位を選ぶ",
        ),
        tags=frozenset({"analysis", "structure", "planning", "learning"}),
        constraints=_COMMON_CONSTRAINTS,
    ),
    ThinkingResource(
        resource_id="diverge",
        name="発散探索",
        description="複数の可能性を生成し、選択肢を早期に狭めすぎない。",
        purpose="アイデア探索、設計案、原因候補の列挙",
        steps=(
            "前提を明示する",
            "異なる方向から候補を複数生成する",
            "候補ごとの利点・弱点・成立条件を整理する",
            "未検討の方向を残す",
        ),
        tags=frozenset({"exploration", "creativity", "hypothesis"}),
        constraints=_COMMON_CONSTRAINTS,
    ),
    ThinkingResource(
        resource_id="hypothesis",
        name="仮説形成",
        description="観測と解釈を分け、検証可能な仮説を作る。",
        purpose="原因分析、予測、研究、トラブルシュート",
        steps=(
            "観測された事実を列挙する",
            "事実から直接言えることと解釈を分ける",
            "説明候補を複数作る",
            "各仮説が予測する観測結果を記述する",
        ),
        tags=frozenset({"analysis", "hypothesis", "research"}),
        constraints=_COMMON_CONSTRAINTS,
    ),
    ThinkingResource(
        resource_id="compare",
        name="比較評価",
        description="候補を共通の評価軸にそろえて比較する。",
        purpose="選定、意思決定、方式比較",
        steps=(
            "候補と評価目的を明示する",
            "共通の評価軸を定める",
            "各候補を同じ軸で比較する",
            "トレードオフと条件依存性を示す",
        ),
        tags=frozenset({"decision", "evaluation", "comparison"}),
        constraints=_COMMON_CONSTRAINTS,
    ),
    ThinkingResource(
        resource_id="verify",
        name="検証",
        description="主張・計算・コード・前提を、確認可能な方法で点検する。",
        purpose="品質確認、デバッグ、事実確認、推論の誤り検出",
        steps=(
            "検証対象の主張と前提を切り出す",
            "確認可能な証拠・テスト・反例を探す",
            "期待結果と実際の結果を比較する",
            "確認済み・未確認・反証ありを分類する",
        ),
        tags=frozenset({"verification", "testing", "debugging", "evidence"}),
        constraints=_COMMON_CONSTRAINTS + (
            "確認していないテストを実行済みとして報告しない。",
        ),
    ),
    ThinkingResource(
        resource_id="uncertainty_check",
        name="不確実性点検",
        description="確度、情報不足、前提依存、反証可能性を明示する。",
        purpose="曖昧な課題、予測、情報が不完全な意思決定",
        steps=(
            "確定事項・推定・仮定を分ける",
            "結論を左右する不足情報を特定する",
            "別の説明や反例を検討する",
            "確度と、確度を上げるために必要な情報を示す",
        ),
        tags=frozenset({"uncertainty", "verification", "risk"}),
        constraints=_COMMON_CONSTRAINTS,
    ),
    ThinkingResource(
        resource_id="reverse_plan",
        name="逆算計画",
        description="目標から必要条件・中間成果・次の行動を逆算する。",
        purpose="実装計画、学習計画、プロジェクト管理",
        steps=(
            "目標と期限・制約を明示する",
            "完了状態から必要条件を逆算する",
            "依存関係を持つ中間成果に分ける",
            "最初に着手する具体的な一手を決める",
        ),
        tags=frozenset({"planning", "goal", "execution"}),
        constraints=_COMMON_CONSTRAINTS,
    ),
    ThinkingResource(
        resource_id="reflect",
        name="差分振り返り",
        description="初期案と結果の差分から、更新すべき前提や次の試行を抽出する。",
        purpose="反復改善、実験、学習、設計レビュー",
        steps=(
            "当初の予測・前提を記録する",
            "結果と予測の差分を特定する",
            "差分の原因候補を分類する",
            "次の試行で変更する要素を一つ以上定める",
        ),
        tags=frozenset({"iteration", "learning", "evaluation", "drift"}),
        constraints=_COMMON_CONSTRAINTS,
    ),
    ThinkingResource(
        resource_id="boundary_check",
        name="境界・例外点検",
        description="通常ケースだけでなく、適用範囲・境界条件・例外を確認する。",
        purpose="コード設計、仕様策定、安全性、運用設計",
        steps=(
            "適用範囲と対象外を明示する",
            "境界値・例外・失敗条件を列挙する",
            "各ケースの期待動作を定める",
            "未定義のケースを保留事項として残す",
        ),
        tags=frozenset({"engineering", "safety", "edge_cases", "specification"}),
        constraints=_COMMON_CONSTRAINTS,
    ),
    ThinkingResource(
        resource_id="converge",
        name="収束・統合",
        description="候補を目的と証拠に照らして統合し、判断と保留点をまとめる。",
        purpose="分析結果の統合、意思決定、報告",
        steps=(
            "候補・証拠・制約を並べる",
            "目的に対する適合性を評価する",
            "採用案と採用理由を要約する",
            "棄却案・残る不確実性・再検討条件を示す",
        ),
        tags=frozenset({"synthesis", "decision", "reporting"}),
        constraints=_COMMON_CONSTRAINTS,
    ),
)


DEFAULT_REGISTRY = ResourceRegistry(DEFAULT_RESOURCES)


def get_resource(resource_id: str) -> ThinkingResource:
    """デフォルト登録簿からリソースを取得する簡易関数。"""
    return DEFAULT_REGISTRY.get(resource_id)


def list_resources() -> List[ThinkingResource]:
    """デフォルト登録簿の有効なリソースをID順で返す。"""
    return DEFAULT_REGISTRY.list_resources()


def build_circuit(resource_ids: Sequence[str], *, name: str) -> ThinkingCircuit:
    """デフォルト登録簿から回路を合成する簡易関数。"""
    return DEFAULT_REGISTRY.compose(resource_ids, name=name)


if __name__ == "__main__":
    print(f"Thinking Mold Resources v{RESOURCE_SCHEMA_VERSION}")
    print(f"Registered resources: {len(DEFAULT_REGISTRY)}")
    for item in DEFAULT_REGISTRY.list_resources():
        print(f"- {item.resource_id}: {item.name}")

    demo = build_circuit(
        ["decompose", "hypothesis", "verify", "uncertainty_check", "converge"],
        name="careful_analysis",
    )
    print(f"Demo circuit: {demo.circuit_id} -> {' -> '.join(demo.resource_ids)}")
