# Changelog

## 0.3.0-draft — Request Intake and Modular Control Kernel

- トップモールドの責務を「要求契約・ポリシー境界・能力ルーティング・結果・トレース契約」として再整理。
- 原文、正規化目的、原子的要件、明示/推定の区別、仮定、ブロッキング質問、受入条件を持つ Request Intake Packet を追加。
- `core/intake.py` を追加し、構造化パケット検証と READY 時のみ Task Envelope を作る処理を実装。
- `--intake config/intake.example.json` を追加。
- Persona Seed のポータブルな例と、Persona / Capsule / Dials / Session Override / Policy の境界を文書化。
- 初回ダイヤル案内と通常起動を分離。再調整は `--configure` から明示的に開き、高度なダイヤルは `--advanced-dials` で表示。
- 数値ダイヤルをモデル中立の指示オーバーレイに変換する `build_dial_overlay` と、Persona Seed＋Dialsをまとめる `build_personalization_overlay` を追加。
- 汎用性、意図忠実性、接続可能性、失敗回復、複雑度、実行の真実性を別角度から設計レビュー。
- 破損・未登録ダイヤルを含む設定を無言で破棄・上書きしない検証を追加。
- テストを追加し、plan-only の実装境界を明示。

## 0.2.0-draft — Universal Control Plane

- ChatGPT固定の利用フローからプロバイダー中立のタスク契約・能力ルート計画へ拡張。
- Task Envelope / Processor Registry の検証、入力型照合、禁止モード除外、決定論的な経路探索を追加。
- `PROC-XXX` を `MOLD-XXX` と分け、実行候補を共通能力で参照。
- Persona / ダイヤルを必須フローから任意オーバーレイへ再配置。

## 0.1.0-draft — Initial Skeleton

- Persona MD の状態判定、ダイヤル管理、モールド登録、基本デモを用意。
