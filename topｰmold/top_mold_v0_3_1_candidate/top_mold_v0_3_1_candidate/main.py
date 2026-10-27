"""Top Mold v0.3.1 candidate: local contract validation and plan-only routing."""
import argparse
import json
import shutil
import sys
from pathlib import Path

from core.demo_runner import run_demo
from core.errors import DialConfigError, IntakeError, PlanningError, RegistryError
from core.intake import validate_intake_packet, task_from_intake
from core.personalization import (build_personalization_overlay, complexity_advice,
    load_dial_catalog, load_settings, save_settings, update_dial, select_visible_dials)
from core.planner import build_plan
from core.result_contract import validate_result_envelope
from core.trace import build_trace_record
from core.registry import load_mold_registry, load_processor_registry
from core.startup import inspect_persona_file

ROOT = Path(__file__).resolve().parent


def _path(raw, base=ROOT):
    path = Path(raw)
    return path if path.is_absolute() else base / path


def build_parser():
    parser = argparse.ArgumentParser(description="Top Mold — Universal Control Skeleton v0.3.1 candidate")
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument("--demo", choices=[f"DEMO-{i:03d}" for i in range(1, 6)])
    operation.add_argument("--task", help="Task Envelope JSON path")
    operation.add_argument("--intake", help="Structured Request Intake Packet JSON path")
    operation.add_argument("--result", help="Validate a processor Result Envelope JSON path")
    operation.add_argument("--trace", nargs=2, metavar=("TASK_JSON", "PLAN_JSON"), help="Build a privacy-minimizing trace record from a task and plan JSON")
    operation.add_argument("--configure", action="store_true", help="Open personalization configuration")
    operation.add_argument("--show-overlay", action="store_true", help="Print a declarative personalization overlay")
    parser.add_argument("--advanced-dials", action="store_true", help="Show advanced dials (requires --configure)")
    parser.add_argument("--persona", default="config/persona.md", help="Persona MD path")
    parser.add_argument("--persona-seed", default="config/persona_seed.example.json", help="Persona Seed JSON path")
    parser.add_argument("--processor-registry", default="config/processor_registry.json", help="Processor Registry JSON path")
    parser.add_argument("--mold-registry", default="config/mold_registry.json", help="Mold Registry JSON path")
    parser.add_argument("--settings", default="runtime/personalization.json", help="Personalization settings path")
    parser.add_argument("--dial-catalog", default="config/dials.json", help="Dial catalog path")
    parser.add_argument("--expected-task-id", help="Require this task_id when validating --result")
    parser.add_argument("--fingerprint-request", action="store_true", help="Include an opt-in SHA-256 request fingerprint with --trace")
    return parser


def _read_json(path, label):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} を読み込めませんでした: {exc}") from exc


def _configure(args, catalog, settings):
    visible = select_visible_dials(catalog, settings, include_advanced=args.advanced_dials)
    print("ダイヤル値: 1=控えめ / 2=やや控えめ / 3=標準 / 4=やや強め / 5=強め")
    for dial_id, spec in visible.items():
        print(f"{dial_id} {'[有効]' if dial_id in settings['active_dial_ids'] else '[追加候補]'} {spec['name']}: {spec.get('description', '')}")
    print("変更するダイヤルIDを入力。Enterで終了します。")
    while True:
        dial_id = input("ID> ").strip().upper()
        if not dial_id:
            break
        if dial_id not in visible:
            print("一覧にあるIDを入力してください。")
            continue
        raw = input("値 (1-5)> ").strip()
        try:
            value = int(raw)
            settings = update_dial(settings, catalog, dial_id, value)
        except (ValueError, DialConfigError) as exc:
            print(f"変更できませんでした: {exc}")
            continue
        print(f"更新候補: {dial_id}={value}（まだ保存前）")
    confirm = input("この設定を保存しますか？ [y/N] ").strip().lower()
    if confirm == "y":
        save_settings(_path(args.settings), settings, catalog)
        print("設定を保存しました。")
    else:
        print("設定は保存していません。")
    return 0


def _prompt_choice(prompt, allowed, default):
    while True:
        answer = input(f"{prompt} [{'/'.join(sorted(allowed))}] (default {default}): ").strip()
        if not answer:
            return default
        if answer in allowed:
            return answer
        print("選択肢にある値を入力してください。")


def _initial_setup(catalog, settings, settings_path, persona_path, persona_state):
    """Run the one-time interactive setup; no prompt is shown in non-TTY use."""
    if persona_state.status in {"ABSENT", "EMPTY", "ERROR"}:
        print("\n初回セットアップ: Persona MD")
        choice = _prompt_choice("1) 案内付き設定  2) 標準設定のまま進む  3) 変更せず終了", {"1", "2", "3"}, "2")
        if choice == "3":
            print("設定を変更せず終了します。")
            return 0
        if choice == "1":
            template = ROOT / "config" / "persona.example.md"
            if persona_state.status == "ABSENT":
                persona_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(template, persona_path)
                print(f"Persona MD の雛形を作成しました: {persona_path}")
            elif persona_state.status == "EMPTY":
                replace_empty = _prompt_choice("空の MD を雛形で置き換えますか？", {"y", "n"}, "n")
                if replace_empty == "y":
                    shutil.copyfile(template, persona_path)
                    print(f"Persona MD の雛形を作成しました: {persona_path}")
                else:
                    print("空の MD は変更していません。")
            else:
                print("読み込み先の問題を解消してから Persona MD を設定してください。MD は変更していません。")

    print("\n初期ダイヤル（1=控えめ / 2=やや控えめ / 3=標準 / 4=やや強め / 5=強め）")
    visible = select_visible_dials(catalog, settings, include_advanced=False)
    for dial_id, spec in visible.items():
        print(f"{dial_id} | {spec['name']} | 値={settings['values'].get(dial_id, 3)} | {spec.get('description', '')}")
    adjust = _prompt_choice("初期ダイヤルを調整しますか？", {"y", "n"}, "n")
    if adjust == "y":
        while True:
            dial_id = input("変更するID（終了は Enter）: ").strip().upper()
            if not dial_id:
                break
            if dial_id not in visible:
                print("基本ダイヤルのIDを入力してください。高度なダイヤルは --configure --advanced-dials から追加できます。")
                continue
            raw = input("値（1〜5）: ").strip()
            try:
                settings = update_dial(settings, catalog, dial_id, int(raw))
            except (ValueError, DialConfigError) as exc:
                print(f"変更できませんでした: {exc}")
                continue
    save_settings(settings_path, settings, catalog)
    print("初回設定を保存しました。次回以降の通常起動ではダイヤル画面を繰り返し表示しません。")
    print("あとから調整する場合は --configure を指定してください。")
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.advanced_dials and not args.configure:
        parser.error("--advanced-dials は --configure と併用してください。")
    if args.expected_task_id is not None and not args.result:
        parser.error("--expected-task-id は --result と併用してください。")
    if args.fingerprint_request and not args.trace:
        parser.error("--fingerprint-request は --trace と併用してください。")

    try:
        # Operational paths must remain independent of optional personalization files.
        # A corrupted dial file must not prevent plain Task Envelope routing.
        if args.demo:
            print(run_demo(args.demo, ROOT))
            return 0
        if args.task:
            task = _read_json(_path(args.task), "Task Envelope")
            registry = load_processor_registry(_path(args.processor_registry))
            plan = build_plan(task, registry)
            print(json.dumps(plan, ensure_ascii=False, indent=2))
            return 0 if plan["plan_status"] == "COMPLETE" else 2
        if args.result:
            result_envelope = _read_json(_path(args.result), "Result Envelope")
            validated = validate_result_envelope(result_envelope, expected_task_id=args.expected_task_id)
            print(json.dumps(validated, ensure_ascii=False, indent=2))
            return 0
        if args.trace:
            task_path, plan_path = (_path(x) for x in args.trace)
            task = _read_json(task_path, "Task Envelope")
            plan = _read_json(plan_path, "Plan Result")
            record = build_trace_record(task, plan, include_request_fingerprint=args.fingerprint_request)
            print(json.dumps(record, ensure_ascii=False, indent=2))
            return 0
        if args.intake:
            packet = _read_json(_path(args.intake), "Request Intake Packet")
            normalized = validate_intake_packet(packet)
            result = {"intake": normalized, "planning": None}
            if normalized["decision"]["status"] == "READY":
                registry = load_processor_registry(_path(args.processor_registry))
                result["planning"] = build_plan(task_from_intake(normalized), registry)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if normalized["decision"]["status"] != "READY":
                return 3
            return 0 if result["planning"]["plan_status"] == "COMPLETE" else 2

        if args.configure or args.show_overlay:
            catalog = load_dial_catalog(_path(args.dial_catalog))
            settings = load_settings(_path(args.settings), catalog)
            if args.show_overlay:
                seed_path = _path(args.persona_seed)
                seed = _read_json(seed_path, "Persona Seed") if seed_path.exists() else None
                overlay = build_personalization_overlay(settings, catalog, seed)
                print(json.dumps(overlay, ensure_ascii=False, indent=2))
                return 0
            return _configure(args, catalog, settings)

        # First interactive launch presents the base dials once. Automated/non-TTY
        # runs remain non-blocking and do not persist defaults as a side effect.
        mold_registry = load_mold_registry(_path(args.mold_registry))
        catalog = load_dial_catalog(_path(args.dial_catalog))
        settings_path = _path(args.settings)
        first_setup = not settings_path.exists()
        settings = load_settings(settings_path, catalog)
        persona_path = _path(args.persona)
        state = inspect_persona_file(persona_path)
        if first_setup and sys.stdin.isatty():
            return _initial_setup(catalog, settings, settings_path, persona_path, state)

        print("=" * 58)
        print("Top Mold — Universal Control Skeleton v0.3.1 candidate")
        print(f"Registered molds: {len(mold_registry)}")
        print(f"Persona MD state: {state.status} — {state.message}")
        print(f"Active dials: {len(settings['active_dial_ids'])}; configuration UI is opt-in (--configure)")
        if first_setup:
            print("初回設定は未保存です。対話端末で起動するか、--configure で設定してください。")
        advice = complexity_advice(settings, threshold=10)
        if advice:
            print(advice)
        print("Execution boundary: PLAN_ONLY; no LLM, API, or external tool is called.")
        return 0
    except (OSError, UnicodeError, ValueError, IntakeError, PlanningError, RegistryError, DialConfigError, TypeError, KeyError) as exc:
        print(f"Top Mold error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
