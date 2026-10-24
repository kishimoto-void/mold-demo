"""Interactive local prototype for the Top Mold universal control skeleton."""
import argparse
import json
import shutil
from pathlib import Path

from core.personalization import (
    complexity_advice,
    build_personalization_overlay,
    select_visible_dials,
    load_dial_catalog,
    load_settings,
    save_settings,
    update_dial,
    DialConfigError,
)
from core.registry import load_mold_registry
from core.startup import inspect_persona_file
from core.demo_runner import run_demo
from core.planner import build_plan, PlanningError
from core.intake import IntakeError, validate_intake_packet, task_from_intake

ROOT = Path(__file__).resolve().parent


def prompt_choice(prompt: str, allowed: set[str], default: str) -> str:
    while True:
        answer = input(f"{prompt} [{'/'.join(sorted(allowed))}] (default {default}): ").strip()
        if not answer:
            return default
        if answer in allowed:
            return answer
        print("選択肢にある値を入力してください。")


def show_dials(catalog: dict, settings: dict) -> None:
    print("\n--- 現在のダイヤル ---")
    for dial_id in settings["active_dial_ids"]:
        spec = catalog[dial_id]
        print(f"{dial_id} | {spec['name']} | 値={settings['values'].get(dial_id, 3)} | {spec['description']}")
    print("\n値の目安：1=控えめ / 2=やや控えめ / 3=標準 / 4=やや強め / 5=強め")


def interactive_adjustment(catalog: dict, settings: dict, settings_path: Path, *, include_advanced: bool = False) -> dict:
    answer = prompt_choice("ダイヤルを調整しますか？", {"y", "n"}, "n")
    if answer != "y":
        return settings

    visible_catalog = select_visible_dials(catalog, settings, include_advanced=include_advanced)
    if include_advanced:
        print("\n基本ダイヤルと高度なダイヤル（D-001〜D-013）")
    else:
        print("\n基本ダイヤルと現在有効なダイヤル")
        print("高度なダイヤルを追加する場合は --configure --advanced-dials を指定してください。")
    for dial_id, spec in visible_catalog.items():
        marker = "有効" if dial_id in settings["active_dial_ids"] else "追加候補"
        print(f"{dial_id} [{marker}] {spec['name']}: {spec['description']}")

    while True:
        dial_id = input("変更する ID（終了は Enter）: ").strip().upper()
        if not dial_id:
            break
        if dial_id not in catalog:
            print("その ID は登録されていません。")
            continue
        raw = input("値（1〜5）: ").strip()
        try:
            value = int(raw)
            settings = update_dial(settings, catalog, dial_id, value)
        except (ValueError, DialConfigError) as exc:
            print(f"更新できませんでした: {exc}")
            continue
        save_settings(settings_path, settings)
        print(f"更新しました: {dial_id} = {value}")
        advice = complexity_advice(settings, threshold=10)
        if advice:
            print("\n--- 拡張提案 ---")
            print(advice)
            print("--- 提案ここまで ---\n")
    return settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Top Mold — 汎用制御骨格デモ")
    parser.add_argument("--demo", choices=["DEMO-001", "DEMO-002", "DEMO-003", "DEMO-004", "DEMO-005"])
    parser.add_argument("--task", help="汎用ルート計画に使う Task Envelope JSON のパス")
    parser.add_argument("--intake", help="要求分解パケットを検証し、READY の場合はルート計画も生成する JSON のパス")
    parser.add_argument("--configure", action="store_true", help="パーソナライズとダイヤル設定を明示的に開く")
    parser.add_argument("--advanced-dials", action="store_true", help="--configure と併用して高度なダイヤルも一覧表示する")
    parser.add_argument("--show-overlay", action="store_true", help="Persona Seedとダイヤルの中立オーバーレイJSONを表示する")
    parser.add_argument("--persona-seed", default=str(ROOT / "config" / "persona_seed.json"), help="任意の Persona Seed JSON のパス")
    parser.add_argument("--processor-registry", default=str(ROOT / "config" / "processor_registry.json"), help="能力・プロセッサレジストリの JSON パス")
    parser.add_argument("--persona", default=str(ROOT / "config" / "persona.md"), help="任意のパーソナライズ MD のパス")
    args = parser.parse_args()
    if args.advanced_dials and not args.configure:
        parser.error("--advanced-dials は --configure と併用してください。")
    if args.configure and (args.demo or args.task or args.intake or args.show_overlay):
        parser.error("--configure はデモ・タスク計画・オーバーレイ表示とは別に実行してください。")

    if args.show_overlay:
        seed_path = Path(args.persona_seed)
        if not seed_path.is_absolute():
            seed_path = ROOT / seed_path
        try:
            catalog = load_dial_catalog(ROOT / "config" / "dials.json")
            settings = load_settings(ROOT / "runtime" / "personalization.json", catalog)
            seed = json.loads(seed_path.read_text(encoding="utf-8")) if seed_path.exists() else None
            overlay = build_personalization_overlay(settings, catalog, seed)
        except (OSError, UnicodeError, json.JSONDecodeError, DialConfigError) as exc:
            print(f"パーソナライズオーバーレイを生成できませんでした。設定ファイルは変更していません: {exc}")
            return 2
        print(json.dumps(overlay, ensure_ascii=False, indent=2))
        return 0

    if args.demo:
        print(run_demo(args.demo, ROOT))
        return 0

    if args.intake:
        intake_path = Path(args.intake)
        registry_path = Path(args.processor_registry)
        if not intake_path.is_absolute():
            intake_path = ROOT / intake_path
        if not registry_path.is_absolute():
            registry_path = ROOT / registry_path
        try:
            packet = json.loads(intake_path.read_text(encoding="utf-8"))
            registry_data = json.loads(registry_path.read_text(encoding="utf-8"))
            normalized = validate_intake_packet(packet)
            result = {"intake": normalized, "planning": None}
            if normalized["decision"]["status"] == "READY":
                result["planning"] = build_plan(task_from_intake(normalized), registry_data)
        except (OSError, UnicodeError, json.JSONDecodeError, PlanningError, IntakeError) as exc:
            print(f"要求パケットを検証できませんでした: {exc}")
            return 2
        print(json.dumps(result, ensure_ascii=False, indent=2))
        status = normalized["decision"]["status"]
        if status != "READY":
            return 3
        return 0 if result["planning"]["plan_status"] == "COMPLETE" else 2

    if args.task:
        task_path = Path(args.task)
        registry_path = Path(args.processor_registry)
        if not task_path.is_absolute():
            task_path = ROOT / task_path
        if not registry_path.is_absolute():
            registry_path = ROOT / registry_path
        try:
            task = json.loads(task_path.read_text(encoding="utf-8"))
            processor_registry = json.loads(registry_path.read_text(encoding="utf-8"))
            plan = build_plan(task, processor_registry)
        except (OSError, UnicodeError, json.JSONDecodeError, PlanningError) as exc:
            print(f"ルート計画を生成できませんでした: {exc}")
            return 2
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0 if plan["plan_status"] == "COMPLETE" else 2

    try:
        registry = load_mold_registry(ROOT / "config" / "mold_registry.json")
        catalog = load_dial_catalog(ROOT / "config" / "dials.json")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"モールド/ダイヤル設定を読み込めませんでした: {exc}")
        return 2
    settings_path = ROOT / "runtime" / "personalization.json"
    persona_path = Path(args.persona)
    if not persona_path.is_absolute():
        persona_path = ROOT / persona_path

    first_setup = not settings_path.exists()

    print("=" * 58)
    print("Top Mold — 汎用制御骨格")
    print(f"登録モールド: {len(registry)} 件")
    print(f"起動モード: {'初回セットアップ' if first_setup else ('設定調整' if args.configure else '通常起動')}")
    print("=" * 58)

    state = inspect_persona_file(persona_path)
    print(f"MD 状態: {state.status}")
    print(state.message)

    # Initial onboarding is shown only during first setup or explicit reconfiguration.
    if state.status in {"ABSENT", "EMPTY", "ERROR"} and (first_setup or args.configure):
        print("\n1) 案内付き設定  2) 標準設定のまま試す  3) 終了")
        choice = prompt_choice("選択", {"1", "2", "3"}, "2")
        if choice == "3":
            print("変更せず終了します。")
            return 0
        if choice == "1":
            if state.status == "EMPTY":
                overwrite = prompt_choice("空の MD を雛形で置き換えますか？", {"y", "n"}, "n")
                if overwrite == "y":
                    shutil.copyfile(ROOT / "config" / "persona.example.md", persona_path)
                    print(f"雛形を作成しました: {persona_path}")
                else:
                    print("MD は変更していません。必要に応じて手動で編集してください。")
            elif state.status == "ABSENT":
                persona_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / "config" / "persona.example.md", persona_path)
                print(f"雛形を作成しました: {persona_path}")
            else:
                print("読み込み先の問題を解消してから、MD を設定してください。標準設定で続行します。")
    elif state.status in {"ABSENT", "EMPTY", "ERROR"}:
        print("パーソナライズ設定の案内は通常起動では繰り返しません。必要な場合は --configure を指定してください。")

    try:
        settings = load_settings(settings_path, catalog)
    except (OSError, UnicodeError, json.JSONDecodeError, DialConfigError) as exc:
        print(f"ダイヤル設定を読み込めませんでした。既存ファイルは変更していません: {exc}")
        return 2
    if first_setup or args.configure:
        show_dials(catalog, settings)
        settings = interactive_adjustment(catalog, settings, settings_path, include_advanced=args.advanced_dials)
        save_settings(settings_path, settings)
    else:
        print(f"ダイヤル設定を読み込みました（有効 {len(settings['active_dial_ids'])} 個）。")
        print("調整画面は通常起動では表示しません。変更する場合は --configure を指定してください。")

    advice = complexity_advice(settings, threshold=10)
    if advice:
        print("\n--- ダイヤル構成の案内 ---")
        print(advice)

    print("\n初期骨格の確認が完了しました。")
    print("注：この CLI はローカル骨格の確認用です。LLMアプリ・モデル内部・外部サービスを直接操作しません。")
    print("起動デモ: python main.py --demo DEMO-001")
    print("能力ルート計画: python main.py --demo DEMO-005")
    print("独自タスク: python main.py --task config/task.example.json")
    print("要求分解パケット: python main.py --intake config/intake.example.json")
    print("ダイヤル再調整: python main.py --configure")
    print("高度なダイヤル: python main.py --configure --advanced-dials")
    print("ダイヤル指示JSON: python main.py --show-overlay")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
