# Bottom Mold — LLM向け統合仕様 v0.3-draft

> Status: Draft / Reference Specification  
> Purpose: 共通基盤の意味論・数式モデル・Python参照実装・適合テストを一つの文書にまとめる。  
> This document defines observable evaluation behavior. It does **not** claim to control an LLM's hidden internal reasoning.

---

## 0. この文書の読み方

この文書は、Bottom Mold を利用・実装・拡張する LLM と開発者向けの基準文書である。

優先順位は次のとおり。

1. **不変条件**（Invariant）
2. **型・状態・APIの定義**
3. **数式と状態遷移**
4. **Python参照実装**
5. **使用例・拡張案**

説明用の例や拡張案が、上位の不変条件と矛盾する場合は不変条件を優先する。定義済みの挙動と、将来の候補機能を混同しないこと。

## 1. 目的

Bottom Mold は、異なる目的・ペルソナ・プロセスモールドから共通利用できる、評価のための最小基盤である。

主な役割:

- パーソナライズに関する観測を、軸ごとに記録・分類する。
- 正方向と負方向の観測を、根拠なく相殺しない。
- 明示的な中立と、観測不足を別状態として保持する。
- 厳密評価をパーソナライズの好みから独立させる。
- 上位レイヤーが安全に拡張できる明示的な境界を提供する。

Bottom Mold 自体は、ユーザーの人格を確定診断したり、LLM内部の思考過程を直接制御したり、会話だけで自動的に永続学習したりする機能ではない。

## 2. 不変条件

### I-1. 評価系の分離

パーソナライズ評価と厳密評価は別API・別結果として扱う。

- パーソナライズ上の好みは、数学的・論理的な正誤を変更しない。
- 厳密評価の PASS / FAIL を、ユーザーの希望や会話の雰囲気で上書きしない。
- 片方の評価結果を、もう片方の評価結果として再利用しない。

### I-2. 観測を相殺しない

正方向と負方向の観測が同じ軸に存在しても、合計値で相殺して消去しない。

例: 「短い説明が好き」という観測と、「この説明は短すぎた」という観測があった場合、両方を保持し、暫定状態を `MIXED_PROVISIONAL_NEUTRAL` とする。これは「差がゼロ」や「最適解が見つかった」を意味しない。

### I-3. `≌` の意味

本仕様で `≌` は、差異や未確定要素を残したまま扱う**暫定的な収束・保留状態**を表す概念記号である。

`≌` は次のいずれも意味しない。

- 算術的なゼロ
- 正負の差が消えたこと
- 成功・正解・最適であること
- 十分な観測が存在すること

状態コードは意味の曖昧さを避けるため、単一の `≌` ではなく、以下の具体的な状態を使用する。

### I-4. 根拠と確度を混同しない

観測には、その情報が観測・ユーザー反応・推論・仮説のどれに由来するかを記録する。推論や仮説を、確認済みの事実として扱わない。

### I-5. 未定義の尺度を集計しない

`magnitude` は記録用の任意値であり、本仕様では評価方向の決定、加重平均、総合スコアの計算に使わない。比較可能な尺度と集計ルールが別途定義・検証されるまで、集計は禁止する。

### I-6. 更新は明示的に行う

この基盤は、観測を受け取っただけで Persona Seed や設定を永続的に書き換えない。上位レイヤーが、ユーザーの承認・更新ポリシー・保存機構に従って変更を決定する。

## 3. 用語とデータモデル

### 3.1 Direction

- `POSITIVE`: 対象の評価軸に沿って望ましい方向の観測
- `NEGATIVE`: 対象の評価軸に沿って望ましくない方向の観測
- `NEUTRAL`: 観測者が明示的に中立と判断した観測

方向は絶対的な善悪を表さない。必ず `axis` と組み合わせて解釈する。

### 3.2 ObservationKind

- `OBSERVED`: 観測可能な出来事・測定値・実際の出力
- `USER_REACTION`: ユーザーが明示した反応・評価
- `INFERENCE`: 既存情報から導いた推論
- `HYPOTHESIS`: 未検証の仮説

`INFERENCE` と `HYPOTHESIS` は、直接確認された事実と同等の証拠として扱わない。

### 3.3 Axis

`axis` は評価対象の軸を示す文字列。例:

- `explanation_length`
- `detail_level`
- `tone_warmth`
- `exploration`
- `strict_correctness`

軸が異なる観測は、デフォルトでは同一状態へ統合しない。上位レイヤーが軸間の関係を定義する場合も、その対応関係を明示する。

### 3.4 Evidence

`evidence` は観測の根拠を説明する非空文字列。これは根拠の品質を自動保証しない。記述内容が事実か、推論か、仮説かは `kind` と合わせて判断する。

### 3.5 観測の十分性

方向を判定できるかどうかは、観測ごとの `direction_evaluable` で明示する。

- `true`: この観測について、指定軸上の方向を分類できる。
- `false`: 情報不足・曖昧さ・軸不一致などにより、方向を分類できない。

方向を判定できない観測は記録に残すが、正・負・中立の状態判定には含めない。全観測の方向が判定不能なら `INSUFFICIENT_OBSERVATION` とする。

このフラグは自己申告・上位レイヤーの判断であり、真偽を自動検証するものではない。

## 4. 数式モデル

### 4.1 観測集合

特定の評価軸 \(a\) に属する観測集合を \(O_a\) とする。

方向が判定可能な観測集合を次で定義する。

\[
E_a = \{o \in O_a \mid o.\text{direction\_evaluable} = \text{true}\}
\]

判定可能な観測のうち、正・負・明示的中立がそれぞれ一つ以上存在するかを示す指示関数を定義する。

\[
P_a = \mathbb{1}[\exists o \in E_a : o.direction = POSITIVE]
\]

\[
N_a = \mathbb{1}[\exists o \in E_a : o.direction = NEGATIVE]
\]

\[
Z_a = \mathbb{1}[\exists o \in E_a : o.direction = NEUTRAL]
\]

ここで \(\mathbb{1}[\cdot]\) は条件が真なら 1、偽なら 0 を返す。これらは存在判定であり、点数や確率ではない。

### 4.2 状態決定関数

状態 \(S_a\) は次の優先順位で決定する。

\[
S_a =
\begin{cases}
INSUFFICIENT\_OBSERVATION & |E_a| = 0 \\
MIXED\_PROVISIONAL\_NEUTRAL & P_a = 1 \land N_a = 1 \\
EXPLICIT\_NEUTRAL & P_a = 0 \land N_a = 0 \land Z_a = 1 \\
POSITIVE\_ONLY & P_a = 1 \land N_a = 0 \land Z_a = 0 \\
NEGATIVE\_ONLY & P_a = 0 \land N_a = 1 \land Z_a = 0 \\
MIXED\_WITH\_NEUTRAL & (P_a \lor N_a) = 1 \land Z_a = 1
\end{cases}
\]

解釈:

- `INSUFFICIENT_OBSERVATION`: 判定可能な観測がない。中立とは限らない。
- `EXPLICIT_NEUTRAL`: 判定可能な観測があり、正負方向はなく、明示的中立が存在する。
- `POSITIVE_ONLY`: 正方向のみ。
- `NEGATIVE_ONLY`: 負方向のみ。
- `MIXED_WITH_NEUTRAL`: 正または負と、明示的中立が併存する。
- `MIXED_PROVISIONAL_NEUTRAL`: 正と負が併存する。相殺せず暫定状態として保持する。

正負が併存する場合、中立観測の有無によって `MIXED_PROVISIONAL_NEUTRAL` の意味を変えない。混在の存在が重要であり、点数の平均値では解決しない。

### 4.3 厳密評価

例として、期待値 \(x\) と実際の値 \(y\) の厳密な等値判定を次で定義する。

\[
Strict(x,y) =
\begin{cases}
PASS & x = y \\
FAIL & x \ne y
\end{cases}
\]

これは**等値比較の参照例**であり、一般的な数学定理証明器・意味論的な正しさ判定器ではない。浮動小数点の許容誤差、単位変換、式の同値性などは別の明示的ルールを必要とする。

### 4.4 分離性の形式的要件

パーソナライズ観測集合 \(O\) を変更しても、厳密評価入力 \(x,y\) が同一である限り、厳密評価結果は変わってはならない。

\[
\forall O_1,O_2,x,y:\quad Strict(x,y \mid O_1)=Strict(x,y \mid O_2)
\]

実装では、厳密評価APIがパーソナライズ観測を引数として受け取らないことで、この分離を構造的に保つ。

## 5. 状態遷移・判定表

| 判定可能な観測に含まれる方向 | 結果 |
|---|---|
| なし | `INSUFFICIENT_OBSERVATION` |
| 正のみ | `POSITIVE_ONLY` |
| 負のみ | `NEGATIVE_ONLY` |
| 明示的中立のみ | `EXPLICIT_NEUTRAL` |
| 正 + 負 | `MIXED_PROVISIONAL_NEUTRAL` |
| 正 + 明示的中立 | `MIXED_WITH_NEUTRAL` |
| 負 + 明示的中立 | `MIXED_WITH_NEUTRAL` |
| 正 + 負 + 明示的中立 | `MIXED_PROVISIONAL_NEUTRAL` |

`direction_evaluable=false` の観測はログに残るが、この表の方向集合には加えない。

## 6. Python参照実装

対象: Python 3.10+  
依存: 標準ライブラリのみ

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional


class Direction(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class ObservationKind(str, Enum):
    OBSERVED = "observed"
    USER_REACTION = "user_reaction"
    INFERENCE = "inference"
    HYPOTHESIS = "hypothesis"


class PersonalizationState(str, Enum):
    INSUFFICIENT_OBSERVATION = "insufficient_observation"
    POSITIVE_ONLY = "positive_only"
    NEGATIVE_ONLY = "negative_only"
    EXPLICIT_NEUTRAL = "explicit_neutral"
    MIXED_WITH_NEUTRAL = "mixed_with_neutral"
    MIXED_PROVISIONAL_NEUTRAL = "mixed_provisional_neutral"


class StrictStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"


@dataclass(frozen=True)
class Observation:
    axis: str
    direction: Direction
    kind: ObservationKind
    evidence: str
    direction_evaluable: bool = True
    magnitude: Optional[float] = None
    timestamp: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.axis.strip():
            raise ValueError("axis must be a non-empty string")
        if not self.evidence.strip():
            raise ValueError("evidence must be a non-empty string")
        if isinstance(self.magnitude, bool):
            raise TypeError("magnitude must be a number, not bool")
        if self.magnitude is not None and self.magnitude < 0:
            raise ValueError("magnitude must be non-negative")


@dataclass(frozen=True)
class PersonalizationResult:
    axis: str
    state: PersonalizationState
    positive_count: int
    negative_count: int
    explicit_neutral_count: int
    unevaluable_count: int
    observation_count: int


@dataclass(frozen=True)
class StrictResult:
    status: StrictStatus
    expected: object
    actual: object
    rule: str


def evaluate_personalization(
    observations: Iterable[Observation],
    *,
    axis: str,
) -> PersonalizationResult:
    """Classify observations for exactly one axis.

    `magnitude` is record-only. No averaging, weighting, or score aggregation
    is performed. The function does not update persistent user preferences.
    """
    if not axis.strip():
        raise ValueError("axis must be a non-empty string")

    all_items = tuple(observations)
    relevant = tuple(item for item in all_items if item.axis == axis)
    evaluable = tuple(item for item in relevant if item.direction_evaluable)
    unevaluable_count = sum(not item.direction_evaluable for item in relevant)

    positive_count = sum(item.direction is Direction.POSITIVE for item in evaluable)
    negative_count = sum(item.direction is Direction.NEGATIVE for item in evaluable)
    neutral_count = sum(item.direction is Direction.NEUTRAL for item in evaluable)

    has_positive = positive_count > 0
    has_negative = negative_count > 0
    has_neutral = neutral_count > 0

    if not evaluable:
        state = PersonalizationState.INSUFFICIENT_OBSERVATION
    elif has_positive and has_negative:
        state = PersonalizationState.MIXED_PROVISIONAL_NEUTRAL
    elif (has_positive or has_negative) and has_neutral:
        state = PersonalizationState.MIXED_WITH_NEUTRAL
    elif has_positive:
        state = PersonalizationState.POSITIVE_ONLY
    elif has_negative:
        state = PersonalizationState.NEGATIVE_ONLY
    else:
        state = PersonalizationState.EXPLICIT_NEUTRAL

    return PersonalizationResult(
        axis=axis,
        state=state,
        positive_count=positive_count,
        negative_count=negative_count,
        explicit_neutral_count=neutral_count,
        unevaluable_count=unevaluable_count,
        observation_count=len(relevant),
    )


def require_exact_equality(
    expected: object,
    actual: object,
    *,
    rule: str = "python_equality",
) -> StrictResult:
    """Reference checker for exact equality only; not a theorem prover."""
    if not rule.strip():
        raise ValueError("rule must be a non-empty string")

    status = StrictStatus.PASS if expected == actual else StrictStatus.FAIL
    return StrictResult(
        status=status,
        expected=expected,
        actual=actual,
        rule=rule,
    )


if __name__ == "__main__":
    observations = [
        Observation(
            axis="explanation_length",
            direction=Direction.POSITIVE,
            kind=ObservationKind.USER_REACTION,
            evidence="The user said the concise explanation was helpful.",
        ),
        Observation(
            axis="explanation_length",
            direction=Direction.NEGATIVE,
            kind=ObservationKind.USER_REACTION,
            evidence="The user later said this answer was too short.",
        ),
        Observation(
            axis="tone_warmth",
            direction=Direction.NEUTRAL,
            kind=ObservationKind.OBSERVED,
            evidence="No directional reaction was recorded for this axis.",
        ),
        Observation(
            axis="exploration",
            direction=Direction.POSITIVE,
            kind=ObservationKind.HYPOTHESIS,
            evidence="A tentative hypothesis that exploratory options may help.",
            direction_evaluable=False,
        ),
    ]

    print(evaluate_personalization(observations, axis="explanation_length"))
    print(evaluate_personalization(observations, axis="tone_warmth"))
    print(evaluate_personalization(observations, axis="exploration"))
    print(require_exact_equality(2, 1 + 1, rule="integer_equality"))
```

## 7. 最小適合テスト

以下のテストは、仕様上必須の挙動を固定する。`pytest` が必要なのはテスト実行時のみ。

```python
import pytest

# Assume the implementation above is saved as bottom_mold.py.
from bottom_mold import (
    Direction,
    Observation,
    ObservationKind,
    PersonalizationState,
    StrictStatus,
    evaluate_personalization,
    require_exact_equality,
)


def obs(direction, *, axis="a", evaluable=True):
    return Observation(
        axis=axis,
        direction=direction,
        kind=ObservationKind.USER_REACTION,
        evidence="test evidence",
        direction_evaluable=evaluable,
    )


def test_positive_and_negative_are_preserved_as_mixed():
    result = evaluate_personalization(
        [obs(Direction.POSITIVE), obs(Direction.NEGATIVE)],
        axis="a",
    )
    assert result.state is PersonalizationState.MIXED_PROVISIONAL_NEUTRAL
    assert result.positive_count == 1
    assert result.negative_count == 1


def test_empty_observations_mean_insufficient_not_neutral():
    result = evaluate_personalization([], axis="a")
    assert result.state is PersonalizationState.INSUFFICIENT_OBSERVATION


def test_explicit_neutral_is_distinct_from_insufficient():
    result = evaluate_personalization([obs(Direction.NEUTRAL)], axis="a")
    assert result.state is PersonalizationState.EXPLICIT_NEUTRAL


def test_unevaluable_observation_does_not_decide_direction():
    result = evaluate_personalization(
        [obs(Direction.POSITIVE, evaluable=False)],
        axis="a",
    )
    assert result.state is PersonalizationState.INSUFFICIENT_OBSERVATION
    assert result.unevaluable_count == 1


def test_axis_isolation():
    result = evaluate_personalization(
        [obs(Direction.POSITIVE, axis="a"), obs(Direction.NEGATIVE, axis="b")],
        axis="a",
    )
    assert result.state is PersonalizationState.POSITIVE_ONLY
    assert result.negative_count == 0


def test_negative_magnitude_is_rejected():
    with pytest.raises(ValueError):
        Observation(
            axis="a",
            direction=Direction.POSITIVE,
            kind=ObservationKind.OBSERVED,
            evidence="test",
            magnitude=-1.0,
        )


def test_bool_magnitude_is_rejected():
    with pytest.raises(TypeError):
        Observation(
            axis="a",
            direction=Direction.POSITIVE,
            kind=ObservationKind.OBSERVED,
            evidence="test",
            magnitude=True,
        )


def test_strict_equality_is_independent_of_personalization():
    # The strict API does not accept personalization observations.
    result = require_exact_equality(2, 1 + 1)
    assert result.status is StrictStatus.PASS


def test_strict_failure_is_not_overridden_by_preferences():
    result = require_exact_equality(3, 1 + 1)
    assert result.status is StrictStatus.FAIL
```

## 8. エラー・警告の取り扱い

### 8.1 入力エラー

次は評価を継続せず、例外として扱う。

- 空の `axis`
- 空の `evidence`
- 負の `magnitude`
- 数値としての `bool` の使用
- 空の `rule`

### 8.2 不確実性

次は例外ではなく、結果や上位レイヤーの記録で扱う。

- 方向を判定できない観測
- 仮説・推論に基づく観測
- ひとつの軸に正負が併存すること
- 観測が不足していること

この参照実装は、仮説の信頼性や証拠の品質を自動採点しない。

### 8.3 厳密制約との衝突

この基盤は、パーソナライズ上の希望と厳密制約の衝突を自動解決しない。上位レイヤーは少なくとも次を別々に報告する。

- `strict_status`: 厳密評価の結果
- `personalization_state`: 対象軸の状態
- `conflict`: 両者が要求する出力の両立が難しいか
- `resolution`: どの制約を優先し、何を変更したか

例: ユーザーが「短く答えてほしい」と希望していても、問題の条件が厳密な説明を要求する場合、正確性を保ったうえで可能な範囲で簡潔にする。短さの好みを理由に正誤を変更してはならない。

## 9. LLM向け運用規則

この仕様を使用する LLM は、次の規則を守る。

1. **軸を特定する。** 何に対する正・負なのか不明なら、軸を推測で固定しない。
2. **情報源の種類を分ける。** 観測、ユーザー反応、推論、仮説を混ぜない。
3. **中立と不足を分ける。** 反応がないことを「中立」と推定しない。
4. **混在を保持する。** 正負の観測を平均して消さない。
5. **好みと正確性を分ける。** ユーザーが望む回答と、根拠から支持される回答が異なる場合、その差を説明する。
6. **確度を誇張しない。** この基盤の状態は入力観測の分類であり、ユーザーの本質的な人格や恒久的嗜好の証明ではない。
7. **永続更新を偽装しない。** 保存・更新機構が実際に動作していない場合、「学習した」「今後必ず覚えている」と主張しない。
8. **未実装の機能を補完しない。** 自動重み付け、時間減衰、信頼度スコア、軸間推論などは、別仕様とテストが追加されるまで本機能として扱わない。
9. **衝突を見える化する。** パーソナライズと厳密制約の両立が難しい場合、黙って片方を書き換えず、衝突と優先理由を示す。
10. **拡張は互換性を明記する。** 新しい状態・型・集計方法を加える場合、仕様バージョン、状態遷移、テスト、既存実装への影響を記録する。

## 10. 非目標・未実装

このバージョンでは次を保証しない。

- LLM内部の思考過程を直接操作すること
- 人間の嗜好や人格を完全に推定すること
- 観測の真偽・品質・信頼度を自動判定すること
- `magnitude` による重み付けや総合スコア化
- 時間経過による観測の減衰・忘却
- 複数軸間の因果関係や相互作用の推定
- 永続メモリへの自動書き込み
- 一般的な数学証明・論理証明
- すべてのLLMで同一の出力や内部挙動を保証すること

## 11. 拡張インターフェース候補

将来追加する場合は、最低限、目的・型・数式・失敗時挙動・適合テストを定義する。

- `confidence`: 根拠の信頼度。ただし出所と尺度が必要。
- `observed_at`: 標準化された日時。
- `source_id`: 元データや会話ターンへの参照。
- `resolution_policy`: 衝突時にどの制約を優先するか。
- `axis_schema`: 使用可能な軸と意味の登録。
- `update_proposal`: 上位レイヤーが提案する設定変更。適用と提案を区別する。

これらは現時点では候補であり、本参照実装の機能ではない。

## 12. バージョンと変更履歴

- `v0.3-draft`: 状態の意味を分離し、Observation の型、方向判定可能性、数式、参照実装、最小テスト、衝突報告ルールを統合。
- 次版の候補: 実装・テスト実行後に、型や状態名の互換性を確認してから確定版にする。

## 13. 最終要約

Bottom Mold は、パーソナライズの観測を整理しながら、厳密な正誤判定を独立させる共通基盤である。

- `INSUFFICIENT_OBSERVATION` は中立ではない。
- `EXPLICIT_NEUTRAL` は明示的な中立観測を意味する。
- `MIXED_PROVISIONAL_NEUTRAL` は正負の観測が併存する暫定状態であり、相殺や成功を意味しない。
- `magnitude` は尺度が定義されるまで記録用に留める。
- パーソナライズは回答の届け方を調整できるが、根拠に基づく正誤を改変してはならない。
- 永続的な設定更新は上位レイヤーの責任であり、観測分類だけで自動的に発生しない。
