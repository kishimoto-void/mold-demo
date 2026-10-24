# Top Mold — Universal Control Skeleton Specification

- **Version:** `0.3.0-draft`
- **Goal:** LLM・専門領域・端末に依存しない交換可能な上位制御素体
- **Runtime:** Python 3.10+ / standard library only
- **Implementation level:** intake contract validation + route planning; execution is not implemented

## 1. 基本定義

トップモールドは、すべての推論を自分の中に詰め込む巨大な思考回路ではない。**要求を構造化し、制約を確認し、処理資源を選択・接続し、結果と未解決事項を可視化する制御面**である。

トップに持たせるのは、再利用される共通規約・選択規則・状態管理・検証境界。専門知識やドメイン固有の推論、LLM固有のプロンプト、外部実行機能は独立モールドやアダプターへ分ける。

## 2. 制御フロー

```text
[Raw Request]
  ↓
[Intent Compiler: LLM / local / human / other mold]
  ↓ structured Request Packet
[Intake Validator]
  ↓
[Task Envelope + Policy Gate]
  ↓
[Capability Planner] ← [Registries]
  ↓
[Execution Adapter] → [Bottom LLM / Code / Tool / Manual]
  ↓
[Result Contract]
  ↓
[Verification / Reconciliation]
  ↓
[Output + Trace]

Persona Seed / Dials / Session Overrides = optional cross-cutting overlay
```

現行コードは `Intake Validator` と `Capability Planner` までを実装。Intent Compiler の意味解釈、アダプター実行、結果統合は未実装である。

## 3. トップに含めるべき必須責任

1. **Request Contract** — 元の要求と正規化された目標を保持し、要求を原子的な要件に分ける共通形式を定義。
2. **Policy Boundary** — 制約、リスク、承認要件、実行禁止モードを明示して、Personaより強い境界として管理。
3. **Registry & Capability Planner** — モールド、能力プロセッサ、アダプターの宣言を照合し、決定論的な経路案を生成。
4. **Result Contract** — success / partial / failed / skipped を区別し、根拠・仮定・未解決項目を保持。
5. **State & Trace Contract** — 使用した契約・バージョン・ルート・実行環境・失敗を追跡可能にする。
6. **Persona Overlay Interface** — Seed、Capsule、Dials、今回限りの上書きを共通ポリシーへ変換する境界を用意する。

## 4. トップに詰め込まないもの

- 特定LLMの隠れた内部動作を制御できるという前提
- 特定ドメインの専門推論や大量の知識
- ChatGPT / Gemini / Grok 固有の引数・API処理
- 端末固有のUIロジック・認証情報
- Personaの好みで安全境界や実行許可を弱める仕組み
- 根拠のない自動再試行・自動修復・曖昧な成功判定

それらは専門モールド、アダプター、ポリシー実装、または実行環境に配置する。

## 5. 3面構造

| 面 | 責務 | 例 |
|---|---|---|
| 制御面 | 要求契約、ポリシー、能力選択、状態遷移 | Task Envelope、Route Planner |
| 実行面 | LLM、関数、外部ツール、手動ハンドオフ | ChatGPT adapter、local processor |
| 横断面 | Persona、ダイヤル、ログ、バージョン、トレース | Persona Seed、Trace Record |

横断面は制御面の判断を勝手に上書きしない。実行面はアダプター契約に従い、結果を標準形式で返す。

## 6. Persona / Dials / Session Overrides

- **Persona Seed**：安定したコミュニケーション傾向と作業の好みを表す。
- **Persona Capsule**：特定のタスクやエージェントへ渡す、実行可能な短い指示パッケージ。
- **Dials**：利用者が見て調整できる、限られた数の直感的な目盛り。
- **Session Override**：現在の依頼にだけ適用する指示。
- **Hard Policy**：セキュリティ、権限、同意、必須制約。

Seed / Capsule / Dials は振る舞いの方向付けであり、能力・事実・権限を生成しない。現在の依頼で「短く」と指定された場合のようなタスク固有指定は、安定したスタイル好みより優先される。ただし、安全境界・実行権限・検証済み能力は設定上書きの対象外。

## 7. 要求の細分化・洗練

構造化要求では次を分離する。

- `raw_request`: 原文。正規化で失わない。
- `normalized_goal`: 目的の明文化。
- `atomic_requirements`: 1項目1要件、優先度、明示/推定の別、受入条件。
- `known_constraints`: 明示された制約。
- `assumptions`: 仮定、確信度、影響度。
- `open_questions`: 未解決事項とブロッキング性。
- `acceptance_criteria`: 完成判定の条件。
- `routing`: 実行したい能力順序と Task Envelope の情報。
- `decision`: READY / CLARIFICATION_REQUIRED / BLOCKED。

洗練は以下の独立した観点で行う：意図への忠実性、要件の完全性、汎用性、交換可能性、実行可能性、失敗回復性、複雑さ、再現性。洗練の名目でユーザーの目的を別物へ置き換えない。

## 8. 確認質問の基準

- 回答が安全、権限、費用、不可逆な変更、成果物の根本構造を変えるならブロッキング質問にする。
- 影響が小さく、元に戻せる判断なら、仮定と影響を明示して作業を進める。
- すでに文脈から答えが得られる事項を再質問しない。
- `READY` と `blocking=true` の未解決質問を同時に成立させない。
- ブロック中にルートを正常完了扱いにしない。

## 9. 起動とダイヤルUI

- 初回セットアップでは基本8ダイヤルを示し、利用者が初期値を調整できる。
- 2回目以降の通常起動で設定UIを繰り返し出さない。
- 再調整は明示要求または `--configure` で開く。
- 高度なダイヤルは必要時だけ見せる。
- 有効ダイヤルが10個以上なら、重複整理・グループ化を提案するだけで自動変更しない。
- 未設定・空・読込エラーを区別し、既存ファイルを確認なしに上書きしない。

## 10. 成立条件

- 同じ Task Envelope と同じ Registry から同じ経路を生成する。
- `READY` 以外の Intake Packet から実行計画を開始しない。
- 能力不足・型不一致・禁止モード・出力契約不足を表示する。
- Personaなしでも計画ができる。
- 計画成功と実行成功を混同しない。
- 実装・テストが成立した端末（スマートフォン / PC / サーバー）、OS、Python、アダプター、バージョンを実測値で記録する。

## 11. 実装境界

このリポジトリは、契約を検証して計画JSONを生成するローカル骨格である。LLM内部、ChatGPTアプリ、別モデル、スマートフォンのGUIを直接操作する能力は含まない。外部実行の追加は、アダプター契約・権限境界・結果契約・テストを揃えて段階導入する。
