"""Model-neutral reference decision engine for Top Mold v0.1.

This engine only classifies explicit request signals. It does not inspect hidden
states, infer intent from topic nouns alone, call an LLM, or prove the LLM obeyed
TOP_MOLD.md. The normative behavior contract lives in SPEC.md and TOP_MOLD.md.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import json
import re
from pathlib import Path

MODES = ("work", "verify", "design", "research", "chat")
MODE_JA = {
    "work": "作業",
    "verify": "検証",
    "design": "設計",
    "research": "調査",
    "chat": "雑談",
}

# The patterns aim to identify a requested activity, not merely a topic mention.
# Scores allow compound requests to retain secondary modes (e.g. create + test).
MODE_PATTERNS: Dict[str, Sequence[Tuple[str, int]]] = {
    "verify": (
        (r"厳密にテスト", 100), (r"テスト(?:を)?(?:追加|実施|して|しよう|してみて|してくれ)", 95),
        (r"動作確認(?:して|しよう|をして)", 95), (r"検証(?:して|しよう|してみて|を行って)", 90),
        (r"照合(?:して|しよう|してみて)", 90), (r"監査(?:して|しよう)", 85),
        (r"確認(?:して|しよう|してみて|を取って|してくれ)", 70),
        (r"境界条件.{0,8}(?:確かめ|テスト|検証)", 90),
        (r"(?:please\s+)?(?:verify|validate|test|audit)\s+(?:it|this|the\s+code|the\s+build|the\s+result|the\s+output|all\s+cases)\b", 70),
    ),
    "work": (
        (r"(?:ファイル|ファイル一式|パッケージ|ZIP|zip|成果物).{0,10}(?:作成|生成|用意|出力|まとめ)", 95),
        (r"(?:修正して|変更して|改良して|直して|更新して|修正しよう|変更しよう|改良しよう)", 85),
        (r"(?:作成して|作って|作ってみて|実装して|実装しよう|生成して|書いて|組んで|構築して|パッケージ化して)", 85),
        (r"(?:コード|プログラム|スクリプト).{0,8}(?:書いて|作って|実装して|生成して)", 90),
        (r"(?:build|implement|create|generate|package)\s+(?:it|this|a|the|me|a file|a zip)?", 70),
    ),
    "design": (
        (r"設計(?:しよう|して|してみて|を考え|案を出|してくれ)", 90),
        (r"デザイン(?:しよう|して|してみて|案を出)", 90),
        (r"骨格(?:を|だけ)?(?:作ろう|作って|整理して|考えよう)", 80),
        (r"構想(?:を|について)?(?:整理|考え|練ろう|詰めよう)", 75),
        (r"design\s+(?:it|this|a|the)?", 70),
    ),
    "research": (
        (r"(?:最新情報|出典|根拠|一次資料|現状).{0,12}(?:調べ|検索|探し|確認)", 90),
        (r"(?:調べて|調べよう|検索して|探して|リサーチして|情報を集めて)", 85),
        (r"(?:最新|現在|今日|今週).{0,12}(?:どうなって|何が起き|価格|規則|状況).{0,8}(?:調べ|教えて)", 80),
        (r"(?:research|look up|search for)\s+(?:it|this|the|latest)?", 70),
    ),
    "chat": (
        (r"雑談(?:しよう|しよ|したい|しませんか)", 100),
        (r"(?:ちょっと|少し)?話そう", 70),
        (r"(?:今は|今日は)?(?:ただ|普通に)?雑談(?:で|モード)?", 90),
        (r"let'?s chat", 80),
    ),
}

FREE_OPINION_PATTERNS: Sequence[str] = (
    r"ChatGPT的にどう(?:思う|考える)",
    r"(?:率直に|正直に)?どう思う[？?]?$",
    r"あなたならどう考える",
    r"意見を聞かせて",
    r"これどうすればいい",
    r"君ならどうする",
    r"what do you think",
    r"give me your opinion",
)

EXPERT_PATTERNS: Sequence[str] = (
    r"専門家(?:モード)?", r"徹底的に", r"深く分析", r"深掘り", r"網羅的に",
    r"厳密な分析", r"expert mode", r"deep analysis", r"in depth",
)
CONCISE_PATTERNS: Sequence[str] = (
    r"要点だけ", r"簡潔に", r"短く(?:説明|まとめ|答え)", r"一言で", r"結論だけ",
    r"keep it brief", r"concise(?:ly)?",
)
OUTPUT_PATTERNS: Sequence[Tuple[str, Sequence[str]]] = (
    ("zip", (r"(?<![A-Za-z])ZIP(?![A-Za-z])", r"zipファイル", r"圧縮ファイル")),
    ("json", (r"JSON(?:形式|で|にして|を出力)?", r"\.json")),
    ("code", (r"コードだけ", r"コードで出して", r"プログラムとして", r"ソースコード")),
    ("markdown", (r"Markdown(?:形式|で|にして)?", r"\.mdファイル", r"MDファイル", r"マークダウン")),
    ("table", (r"表にして", r"表形式", r"テーブルで")),
    ("document", (r"文書にして", r"報告書にして", r"メモにして", r"レポート形式")),
)

EXPLICIT_LOCK_PATTERNS: Sequence[Tuple[str, str]] = tuple(
    (mode, pattern)
    for mode, ja in MODE_JA.items()
    for pattern in (
        rf"(?:今日は|この会話は|今回)?\s*{ja}モード(?:で|に)?\s*固定",
        rf"モード固定\s*[:：=]?\s*{ja}",
        rf"mode_lock\s*[:=]\s*{mode}",
    )
)

EXPLICIT_UNLOCK_PATTERNS: Sequence[str] = (
    r"モード固定を解除", r"モードロックを解除", r"ロック解除", r"unlock mode", r"clear mode lock",
)

@dataclass(frozen=True)
class ModeSignal:
    mode: str
    score: int
    matched_pattern: str
    position: int

@dataclass(frozen=True)
class Decision:
    primary_mode: str
    secondary_modes: List[str]
    mode_locked: bool
    free_opinion: bool
    depth: str
    output_contract: str
    output_only: bool
    signals: List[Dict[str, Any]]
    notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _has_any(text: str, patterns: Iterable[str], flags: int = re.IGNORECASE) -> bool:
    return any(re.search(pattern, text, flags) is not None for pattern in patterns)


def parse_mode_lock_command(text: str) -> Tuple[Optional[str], bool]:
    """Return (new_lock, unlock_requested); None means no mode-lock command."""
    if _has_any(text, EXPLICIT_UNLOCK_PATTERNS):
        return None, True
    for mode, pattern in EXPLICIT_LOCK_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return mode, False
    return None, False


def detect_mode_signals(text: str) -> List[ModeSignal]:
    signals: List[ModeSignal] = []
    for mode, patterns in MODE_PATTERNS.items():
        best: Optional[ModeSignal] = None
        for pattern, score in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match is not None:
                candidate = ModeSignal(mode=mode, score=score, matched_pattern=pattern, position=match.start())
                if best is None or (candidate.position, -candidate.score) < (best.position, -best.score):
                    best = candidate
        if best is not None:
            signals.append(best)
    # Keep the user's action order: e.g. "create this, then test it" keeps work
    # primary and verification secondary, while "test this, then modify it" does the reverse.
    return sorted(signals, key=lambda s: (s.position, -s.score, MODES.index(s.mode)))


def detect_output_contract(text: str) -> Tuple[str, bool]:
    contract = "auto"
    for name, patterns in OUTPUT_PATTERNS:
        if _has_any(text, patterns):
            contract = name
            break
    output_only = _has_any(text, (r"ZIPだけ", r"ZIPのみ", r"ファイルだけ(?:で|を)?", r"余計な説明なし", r"説明不要", r"output only", r"no extra explanation"))
    return contract, output_only


def decide(
    text: str,
    *,
    mode_lock: Optional[str] = None,
    default_mode: str = "chat",
) -> Decision:
    """Produce a transparent task plan from user text and optional session lock.

    Lock semantics: pass the currently active lock in `mode_lock`; a lock wins over
    automatic mode classification until caller explicitly clears/replaces it using
    `parse_mode_lock_command`. Output format and depth remain independent axes.
    """
    if not isinstance(text, str):
        raise TypeError("text must be str")
    if mode_lock is not None and mode_lock not in MODES:
        raise ValueError(f"mode_lock must be one of {MODES} or None")
    if default_mode not in MODES:
        raise ValueError(f"default_mode must be one of {MODES}")

    signals = detect_mode_signals(text)
    opinion = _has_any(text, FREE_OPINION_PATTERNS)
    depth = "expert" if _has_any(text, EXPERT_PATTERNS) else ("concise" if _has_any(text, CONCISE_PATTERNS) else "normal")
    output_contract, output_only = detect_output_contract(text)

    notes: List[str] = []
    if mode_lock is not None:
        primary = mode_lock
        secondaries: List[str] = []
        notes.append("active_mode_lock_overrides_automatic_classification")
    elif signals:
        primary = signals[0].mode
        secondaries = [s.mode for s in signals[1:] if s.mode != primary]
        notes.append("classification_uses_action_signals_not_topic_nouns_alone")
    else:
        primary = default_mode
        secondaries = []
        notes.append("no_strong_task_signal_fell_back_to_default_mode")

    if opinion:
        notes.append("free_opinion_enabled_without_disabling_fact_hypothesis_separation")
    if output_contract != "auto":
        notes.append("output_contract_is_independent_of_task_mode")
    if output_only:
        notes.append("output_only_requested")

    return Decision(
        primary_mode=primary,
        secondary_modes=secondaries,
        mode_locked=mode_lock is not None,
        free_opinion=opinion,
        depth=depth,
        output_contract=output_contract,
        output_only=output_only,
        signals=[asdict(s) for s in signals],
        notes=notes,
    )


def update_lock(current_lock: Optional[str], text: str) -> Tuple[Optional[str], str]:
    """Apply explicit lock/unlock command and return (new_lock, status)."""
    new_lock, unlock = parse_mode_lock_command(text)
    if unlock:
        return None, "unlocked"
    if new_lock is not None:
        return new_lock, "locked"
    return current_lock, "unchanged"


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load config JSON. Defaults to ../config/top_mold.json from this module."""
    config_path = Path(path) if path else Path(__file__).resolve().parents[1] / "config" / "top_mold.json"
    with config_path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    validate_config(obj)
    return obj


def validate_config(config: Dict[str, Any]) -> None:
    """Fail closed on unsupported structural values in the portable config."""
    if not isinstance(config, dict):
        raise ValueError("config must be an object")
    if config.get("schema") != "top-mold/v0.1":
        raise ValueError("unsupported schema; expected top-mold/v0.1")
    mode = config.get("mode")
    if not isinstance(mode, dict) or mode.get("auto_classification") is not True:
        raise ValueError("mode.auto_classification must be true")
    lock = mode.get("mode_lock")
    if lock is not None and lock not in MODES:
        raise ValueError("mode.mode_lock must be null or a supported mode")
    dials = config.get("dials")
    required_dials = {
        "proactiveness", "generalization", "verification_strictness", "drift_allowance",
        "detail_structure", "concision", "user_agency", "speculation_tolerance",
    }
    if not isinstance(dials, dict) or not required_dials.issubset(dials):
        raise ValueError("config dials missing required keys")
    for name in required_dials:
        value = dials[name]
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 100:
            raise ValueError(f"dial {name} must be integer 0..100")
    axes = config.get("independent_axes")
    if not isinstance(axes, dict) or not all(k in axes for k in ("mode", "depth", "output_contract")):
        raise ValueError("independent_axes must define mode, depth, output_contract")
    if config.get("human_analysis", {}).get("default") not in ("off", "opt_in", "on"):
        raise ValueError("human_analysis.default must be off, opt_in, or on")


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Top Mold v0.1 reference classifier")
    parser.add_argument("text", nargs="*", help="request text to classify")
    parser.add_argument("--lock", choices=MODES, default=None, help="active session mode lock")
    parser.add_argument("--json", action="store_true", help="emit JSON decision")
    args = parser.parse_args(argv)
    text = " ".join(args.text)
    decision = decide(text, mode_lock=args.lock)
    payload = decision.to_dict()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"primary_mode: {payload['primary_mode']}")
        print(f"secondary_modes: {', '.join(payload['secondary_modes']) or '(none)'}")
        print(f"free_opinion: {payload['free_opinion']}")
        print(f"depth: {payload['depth']}")
        print(f"output_contract: {payload['output_contract']} (output_only={payload['output_only']})")
        print("notes:")
        for note in payload["notes"]:
            print(f"- {note}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
