# Top Mold — Universal Control Skeleton

> **Version:** `0.3.0-draft`  
> **State:** provider-neutral control-plane prototype  
> **Runtime:** Python 3.10+ / standard library only  
> **Execution boundary:** planning and contract validation only; no LLM/API is invoked

トップモールドを、特定のAI向けプロンプト集ではなく、**ユーザー要求を構造化し、制約を確認し、適切なモールド・思考回路・LLM・ツールを接続するための上位制御素体**として定義する。

## 1. v0.3 の設計判断

v0.1 のペルソナ・ダイヤル・起動案内、v0.2 の能力ルート計画を残しつつ、責務と設定の境界を明確にした。

- **要求の分解**：元の要求、正規化した目的、原子的要件、前提、未解決質問、受入条件を別々に保持する。
- **意味解釈と検証の分離**：自由文を理解する処理は交換可能な Intent Compiler に委ね、トップの共通コードはその構造化出力を検証する。
- **制御面と実行面の分離**：能力を計画する処理と、LLM/API/ツールを実際に呼び出す処理を混同しない。
- **ペルソナの独立**：Persona Seed は安定した好み、ダイヤルは調整用つまみ、タスク指定は今回限りの指示として分ける。
- **初回設定と通常起動の分離**：初回にダイヤルを見せ、以降は `--configure` を明示した場合だけ調整画面を開く。
- **汎用性の検証**：LLM名・専門領域・端末をトップの共通ロジックに埋め込まない。
- **不成立を可視化**：不足能力、入力型の不一致、確認待ち、未検証、実行失敗を成功扱いにしない。

## 2. 全体構造

```text
Raw User Request
  ↓
Request Intake / Intent Compiler (pluggable)
  ↓ structured Intake Packet
Intake Contract Validation
  ↓
Task Envelope + Policy Gate
  ↓
Capability Route Planner ← Mold / Processor / Adapter Registries
  ↓ plan only in this prototype
Execution Boundary (LLM / local mold / tool / manual handoff)
  ↓
Result Envelope → Verification / Reconciliation → Output

Cross-cutting overlays: Persona Seed / Dials / Session Overrides
Cross-cutting record: Trace / Versions / Device & Platform / Known Failures
```

このリポジトリで実装しているのは、構造化要求パケットの検証、Task Envelope への変換、決定論的なルート計画、起動設定、ダイヤル管理まで。自由文を自動で理解する LLM 呼び出し、外部実行、結果の自動統合は未実装。

## 3. クイックスタート

```bash
# 通常起動。初回だけ調整UIを提示し、以降は設定を読み込んでUI表示を省略
python main.py

# ダイヤルや Persona の設定を明示的に調整
python main.py --configure

# 高度なダイヤルも表示
python main.py --configure --advanced-dials

# 能力ルート計画デモ
python main.py --demo DEMO-005

# Task Envelope を直接計画
python main.py --task config/task.example.json

# 構造化した要求分解パケットを検証して、READY ならルート計画
python main.py --intake config/intake.example.json

# Persona Seedとダイヤルを中立オーバーレイJSONとして確認
python main.py --show-overlay --persona-seed config/persona_seed.example.json

# 全テスト
python -m unittest discover -s tests -v
```

終了コードの目安：`0` 成立、`2` 入力不正または計画不成立、`3` 追加確認が必要かブロック中。実行エンジンが呼び出されたという意味ではない。

## 4. 重要なファイル

| ファイル | 責任 |
|---|---|
| `core/intake.py` | 要求分解パケットの構造検証、READY時の Task Envelope 変換 |
| `core/planner.py` | 能力、入力型、制約、出力契約を照合する決定論的ルート計画 |
| `core/personalization.py` | 1〜5のダイヤル、設定保存、複雑度の整理提案、モデル中立オーバーレイ生成 |
| `core/startup.py` | Persona MD の `ABSENT / PRESENT / EMPTY / ERROR` 判定 |
| `config/intake.example.json` | 細分化・前提・未解決質問・受入条件を含む要求パケット例 |
| `config/persona_seed.example.json` | LLMや実装に移植しやすい Persona Seed の例（実利用時は `config/persona_seed.json` としてコピー・編集） |
| `config/processor_registry.json` | 能力・入出力型・実行方式・登録状態の宣言 |
| `docs/design_review.md` | 別の設計角度からの判断・トレードオフ |

## 5. 要求分解の共通ルール

1. 元の要求は `raw_request` に保持し、正規化した目標で置き換えない。
2. 要件は原子的に分け、`must / should / could` と `explicit / inferred` を付ける。
3. 推定した要件は、ユーザーが明示した要件と同じ確度で扱わない。
4. 仮定は確信度と影響度を添える。重要な未確定事項はブロッキング質問にする。
5. 結果を左右しない細部は、低影響の仮定として明記したうえで先へ進める。
6. 受入条件を定め、生成物が「できた」と言える基準を先に決める。
7. 構造化のあとで、目的への忠実性・汎用性・接続可能性・失敗時の回復性・実装コストを別角度から確認する。

## 6. パーソナライズの責務

- **Persona Seed / Capsule**：長期的な応答の好み・作業方針。
- **Dials**：詳しさ、構造化、検証、批判的検討などの調整可能な目盛り。
- **Session Override**：今回の依頼だけに適用する指定。
- **Policy / Permission**：実行可否、承認、データ取扱いなどの強制境界。

Persona や Dials は能力を増やしたり、権限を付与したり、ハード制約を解除したりしない。初期画面では基本8ダイヤルを提示し、追加5ダイヤルは必要なときだけ開く。10個以上の独立ダイヤルは整理を**提案**するだけで、自動統合しない。

## 7. 実装済み / 未実装

### 実装済み
- Persona MD の状態判定と既存ファイルを保護する起動フロー
- 初回セットアップと `--configure` の分離
- 1〜5のダイヤル管理と10個以上の整理提案
- 要求パケットの項目、優先度、質問状態、ルーティング契約の検証
- 要求パケットを Task Envelope に変換する処理
- 能力・入力型・実行方式・最終出力契約による決定論的なルート計画
- 不足や不整合を明示するユニットテスト

### 未実装
- 自由文から Intake Packet を生成する LLM / 人間向けUI
- ChatGPT / Gemini / Grok 等の API 接続と実行アダプター
- 認証、実行権限の強制、タイムアウト、再試行、レート制限
- 実行結果の出典照合、複数結果の差分統合、意味的な完成判定
- 実端末でのスマートフォン / PC 別の検証

## 8. 設計原則

- 共通契約を安定させ、モデル・専門思考回路・ドメイン固有処理は交換可能にする。
- 「計画できる」「実行できる」「実行して成功した」を別状態として扱う。
- 不明点は、ブロックすべきものと仮定して進められるものに分ける。
- 設定・推定・失敗理由を隠さない。利用者の既存設定を勝手に上書きしない。
- 機能数の多さを汎用性と誤認しない。追加は接続契約とテストが揃う場合に行う。
