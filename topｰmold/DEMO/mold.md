# MOLD-000 — Mold Contract

- **Version:** 0.1.0
- **Status:** Draft / skeleton
- **Purpose:** 全モールドで共通に使う仕様項目、ID、入出力契約、失敗情報の記述方法を定める。

## Input contract
モールドの目的・要件・実装案

## Output contract
共通仕様テンプレートと適合条件

## Dependencies
なし

## Constraints
- 役割は本書で定義した責任範囲に限定する。
- 既存の利用者設定を明示的な選択なしに変更しない。
- 実装済み・デモ済み・未検証を区別して表示する。

## Failure conditions
必須項目の抜け、曖昧な型定義、未記載の実行条件

## Runtime requirements
- Device: スマートフォンまたは PC（実施時に実機を記録）
- External services: 現段階のローカル骨格では不要。外部 LLM / ツールへ接続する場合は、個別アダプターの実装と動作確認が必要。

## Demo / Test
- Demo: 対応する `demos/DEMO-XXX/` を参照
- Test: `tests/` の適合性テストで確認する。

## Implementation status
このファイルは仕様ドラフト。責任の記述はあり、汎用的な実装・本番運用が完成したことを意味しない。
