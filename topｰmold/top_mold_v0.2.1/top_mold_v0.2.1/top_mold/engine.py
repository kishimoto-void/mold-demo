"""Model-neutral reference decision engine for Top Mold v0.2.1.

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
        (r"(?:ファイル|ファイル一式|パッケージ|ZIP|zip|成果物).{0,12}(?:作成|生成|用意|出力|まとめ|にして|に圧縮|納品|提出|提供|渡して)", 95),
        (r"(?:修正して|変更して|改良して|直して|更新して|修正しよう|変更しよう|改良しよう)", 85),
        (r"(?:作成して|作って|作ってみて|実装して|実装しよう|生成して|書いて|組んで|構築して|パッケージ化して)", 85),
        (r"(?:コード|プログラム|スクリプト).{0,8}(?:書いて|作って|実装して|生成して)", 90),
        (r"(?:build|implement|create|generate|package)\s+(?:it|this|a|the|me|a file|a zip)?", 70),
    ),
    "design": (
        (r"設計(?:だけ)?(?:しよう|して|してみて|を考え|案を出|してくれ)", 90),
        (r"デザイン(?:だけ)?(?:しよう|して|してみて|案を出|してくれ)", 90),
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
    output_contracts: List[str]
    output_only: bool
    signals: List[Dict[str, Any]]
    notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _has_any(text: str, patterns: Iterable[str], flags: int = re.IGNORECASE) -> bool:
    return any(re.search(pattern, text, flags) is not None for pattern in patterns)


def _is_quoted_match(text: str, start: int, end: int) -> bool:
    """Return True when a match is inside a common quote pair.

    This is deliberately a small heuristic for the reference classifier. It does
    not attempt full parsing of nested markup or programming-language literals.
    """
    for left, right in (("「", "」"), ("『", "』"), ("“", "”"), ("‘", "’")):
        open_at = text.rfind(left, 0, start + 1)
        close_before = text.rfind(right, 0, start + 1)
        if open_at > close_before:
            close_at = text.find(right, end)
            if close_at >= end:
                return True
    for quote in ('"', '`'):
        quote_positions = [i for i, char in enumerate(text) if char == quote]
        before = sum(1 for i in quote_positions if i < start)
        if before % 2 == 1 and any(i >= end for i in quote_positions):
            return True
    return False


_NEGATION_SUFFIX = re.compile(
    r"^\s*(?:を使わず|を使わない(?:で)?|ではなく|じゃなく|でなく|は不要|は必要ない|はいらない|"
    r"にしない(?:で)?|にしなくていい|しないで|しなくていい|しなくてもよい|しません|していない|"
    r"してはいけない|はいけない|しなかった|しない|不要|必要ない|いらない|要らない|"
    r"not\b|never\b|without\b|instead\s+of\b)",
    re.IGNORECASE,
)
_NEGATION_PREFIX = re.compile(r"(?:not|never|without|don't|do\s+not)\s*$", re.IGNORECASE)


def _is_negated_match(text: str, start: int, end: int) -> bool:
    """Filter simple local negations so a prohibition is not read as a request."""
    prefix = text[max(0, start - 20):start]
    suffix = text[end:min(len(text), end + 24)]
    return bool(_NEGATION_PREFIX.search(prefix) or _NEGATION_SUFFIX.search(suffix))


def parse_mode_lock_command(text: str) -> Tuple[Optional[str], bool]:
    """Return (new_lock, unlock_requested); None means no mode-lock command."""
    for pattern in EXPLICIT_UNLOCK_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if not _is_quoted_match(text, match.start(), match.end()) and not _is_negated_match(text, match.start(), match.end()):
                return None, True
    for mode, pattern in EXPLICIT_LOCK_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if not _is_quoted_match(text, match.start(), match.end()) and not _is_negated_match(text, match.start(), match.end()):
                return mode, False
    return None, False


def detect_mode_signals(text: str) -> List[ModeSignal]:
    signals: List[ModeSignal] = []
    for mode, patterns in MODE_PATTERNS.items():
        best: Optional[ModeSignal] = None
        for pattern, score in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                if _is_quoted_match(text, match.start(), match.end()) or _is_negated_match(text, match.start(), match.end()):
                    continue
                candidate = ModeSignal(mode=mode, score=score, matched_pattern=pattern, position=match.start())
                if best is None or (candidate.position, -candidate.score) < (best.position, -best.score):
                    best = candidate
        if best is not None:
            signals.append(best)
    # Keep the user's action order: e.g. "create this, then test it" keeps work
    # primary and verification secondary, while "test this, then modify it" does the reverse.
    return sorted(signals, key=lambda s: (s.position, -s.score, MODES.index(s.mode)))


_OUTPUT_INTENT = re.compile(
    r"(?:出力|納品|返答|回答|作成|生成|提供|提出|渡して|出して|返して|ください|お願いします|"
    r"にして|にまとめ|だけ|のみ|必要|作って|として|形式で|書き出し|表にして|コードだけ|"
    r"output|deliver|return|format\s+as|save\s+as|provide|create|only)",
    re.IGNORECASE,
)
_OUTPUT_TARGET_PREFIX = re.compile(r"(?:成果物|納品物|提出物|出力形式|ファイル形式|出力|納品|返答|回答|フォーマット|ファイル).{0,12}$", re.IGNORECASE)


def _is_explicit_output_request(text: str, match: re.Match[str]) -> bool:
    if _is_quoted_match(text, match.start(), match.end()) or _is_negated_match(text, match.start(), match.end()):
        return False
    prefix = text[max(0, match.start() - 20):match.start()]
    matched_text = match.group(0)
    suffix = text[match.end():min(len(text), match.end() + 24)]
    # Keep evidence local to the format mention. A later action on an outer
    # container (e.g. "JSONを含めたZIPにして") must not make the inner JSON
    # look like the requested primary output format.
    if _OUTPUT_INTENT.search(matched_text) or _OUTPUT_TARGET_PREFIX.search(prefix):
        return True
    suffix_rules = (
        r"^\s*(?:だけ|のみ)(?:で|に|$)",
        r"^\s*(?:形式|フォーマット)?(?:にして|にする|にまとめ|を出力|を作成|を生成|を提出|を納品|を作って|を出して)",
        r"^\s*(?:出力|納品|返答|回答|作成|生成|提出|提供|書き出し|保存)",
        r"^\s*(?:ファイル)?(?:が必要|がいい|でください|でお願いします)",
        r"^\s*(?:形式|フォーマット)?で(?:出力|説明|返答|回答|納品|提供|渡|提出|出して|書いて|答えて|返して|保存)",
    )
    if any(re.search(rule, suffix, re.IGNORECASE) for rule in suffix_rules):
        return True
    if matched_text.rstrip().endswith("で") and re.match(
        r"^\s*(?:出力|説明|返答|回答|納品|提供|渡|提出|書いて|答えて|返して|保存)",
        suffix,
        re.IGNORECASE,
    ):
        return True
    return False


def _detect_output_contracts(text: str) -> List[str]:
    candidates: List[Tuple[int, int, str]] = []
    for order, (name, patterns) in enumerate(OUTPUT_PATTERNS):
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                if _is_explicit_output_request(text, match):
                    candidates.append((match.start(), order, name))
    # Preserve all distinct explicitly requested formats in mention order. The
    # first one remains the primary contract for backwards compatibility.
    ordered: List[str] = []
    for _, _, name in sorted(candidates):
        if name not in ordered:
            ordered.append(name)
    return ordered


def detect_output_contract(text: str) -> Tuple[str, bool]:
    contracts = _detect_output_contracts(text)
    contract = contracts[0] if contracts else "auto"
    output_only_patterns = (
        r"ZIPだけ", r"ZIPのみ", r"JSONだけ", r"JSONのみ", r"Markdownだけ", r"Markdownのみ",
        r"ファイルだけ(?:で|を)?", r"余計な説明なし", r"説明不要", r"output only", r"no extra explanation",
    )
    output_only = any(
        not _is_quoted_match(text, match.start(), match.end())
        and not _is_negated_match(text, match.start(), match.end())
        for pattern in output_only_patterns
        for match in re.finditer(pattern, text, re.IGNORECASE)
    )
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
    output_contracts = _detect_output_contracts(text)

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
    if len(output_contracts) > 1:
        notes.append("multiple_explicit_output_contracts_preserved_in_order")
    if output_only:
        notes.append("output_only_requested")

    return Decision(
        primary_mode=primary,
        secondary_modes=secondaries,
        mode_locked=mode_lock is not None,
        free_opinion=opinion,
        depth=depth,
        output_contract=output_contract,
        output_contracts=output_contracts,
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
    """Validate the v0.2-compatible portable configuration; fail closed on malformed settings."""
    if not isinstance(config, dict):
        raise ValueError("config must be an object")
    if config.get("schema") != "top-mold/v0.2":
        raise ValueError("unsupported schema; expected top-mold/v0.2")
    version = config.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"0\.2\.\d+", version):
        raise ValueError("version must be a v0.2 patch version such as 0.2.1")

    mode = config.get("mode")
    if not isinstance(mode, dict) or mode.get("auto_classification") is not True:
        raise ValueError("mode.auto_classification must be true")
    lock = mode.get("mode_lock")
    if lock is not None and (not isinstance(lock, str) or lock not in MODES):
        raise ValueError("mode.mode_lock must be null or a supported mode")
    if mode.get("default_mode") not in MODES:
        raise ValueError("mode.default_mode must be a supported mode")
    supported_modes = mode.get("supported_modes")
    if (not isinstance(supported_modes, list) or len(supported_modes) != len(MODES)
            or any(not isinstance(item, str) for item in supported_modes)
            or set(supported_modes) != set(MODES)):
        raise ValueError("mode.supported_modes must contain exactly the supported modes without duplicates")

    dials = config.get("dials")
    required_dials = {
        "personalization_depth", "proactiveness", "initiative", "cross_domain_transfer",
        "retention_preference", "generalization", "verification_strictness", "drift_allowance",
        "detail_structure", "concision", "user_agency", "speculation_tolerance",
    }
    if not isinstance(dials, dict) or not required_dials.issubset(dials):
        raise ValueError("config dials missing required keys")
    scale = dials.get("scale")
    if (not isinstance(scale, dict)
            or type(scale.get("min")) is not int or scale.get("min") != 0
            or type(scale.get("max")) is not int or scale.get("max") != 100):
        raise ValueError("dials.scale must define integer min=0 and max=100")
    for name in required_dials:
        value = dials[name]
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 100:
            raise ValueError(f"dial {name} must be integer 0..100")

    axes = config.get("independent_axes")
    required_axes = ("mode", "depth", "output_contract", "personalization_depth", "proactiveness", "initiative")
    if not isinstance(axes, dict) or not all(k in axes for k in required_axes):
        raise ValueError("independent_axes must define mode, depth, output_contract, personalization_depth, proactiveness, initiative")

    human_analysis = config.get("human_analysis")
    if not isinstance(human_analysis, dict) or human_analysis.get("default") not in ("off", "opt_in", "on"):
        raise ValueError("human_analysis.default must be off, opt_in, or on")

    domains = config.get("domain_profiles")
    required_domains = {"general", "shopping", "learning", "development", "events_entertainment", "daily_life"}
    if not isinstance(domains, dict) or not required_domains.issubset(domains):
        raise ValueError("domain_profiles missing required domains")
    for domain_name, profile in domains.items():
        if not isinstance(profile, dict):
            raise ValueError(f"domain profile {domain_name} must be an object")
        if not isinstance(profile.get("enabled"), bool):
            raise ValueError(f"domain profile {domain_name}.enabled must be boolean")
        for key in ("depth", "proactiveness"):
            value = profile.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 100:
                raise ValueError(f"domain profile {domain_name}.{key} must be integer 0..100")

    policy = config.get("memory_policy")
    if not isinstance(policy, dict):
        raise ValueError("memory_policy must be an object")
    required_memory = (
        "separate_observation_from_interpretation", "transient_content_default",
        "sensitive_data_default", "decay_changes_priority_not_deletion", "delete_requests_apply_to_archives",
        "sensitive_storage_requires_clear_purpose", "hypothesis_requires_independent_context",
    )
    if not all(key in policy for key in required_memory):
        raise ValueError("memory_policy missing required keys")
    for key in required_memory:
        if key not in ("transient_content_default", "sensitive_data_default") and not isinstance(policy[key], bool):
            raise ValueError(f"memory_policy.{key} must be boolean")
    if policy.get("transient_content_default") != "session_only":
        raise ValueError("transient_content_default must be session_only")
    if policy.get("sensitive_data_default") != "do_not_persist_without_explicit_permission_and_clear_purpose":
        raise ValueError("sensitive_data_default must require explicit permission and clear purpose")
    if policy.get("sensitive_storage_requires_clear_purpose") is not True:
        raise ValueError("sensitive storage must require a clear purpose")
    if policy.get("hypothesis_requires_independent_context") is not True:
        raise ValueError("observed hypotheses must require independent context evidence")
    hypothesis_rule = policy.get("observed_hypothesis_requires")
    if not isinstance(hypothesis_rule, str) or not hypothesis_rule.strip():
        raise ValueError("memory_policy.observed_hypothesis_requires must be a non-empty string")

    domain_resolution = config.get("domain_resolution")
    required_domain_resolution = ("primary_domain", "enabled_profile", "disabled_profile", "unknown_domain", "multiple_domains")
    if not isinstance(domain_resolution, dict) or not all(
        isinstance(domain_resolution.get(key), str) and domain_resolution[key].strip()
        for key in required_domain_resolution
    ):
        raise ValueError("domain_resolution must define all domain composition rules as non-empty strings")
    dial_semantics = config.get("dial_semantics")
    if not isinstance(dial_semantics, dict) or not required_dials.issubset(dial_semantics):
        raise ValueError("dial_semantics must define every required global dial")
    if any(not isinstance(dial_semantics[key], str) or not dial_semantics[key].strip() for key in required_dials):
        raise ValueError("each dial_semantics value must be a non-empty string")
    task_kernel = config.get("task_kernel")
    expected_kernel_steps = (
        "identify_goal", "extract_constraints_and_exclusions",
        "separate_evidence_inference_hypothesis_unknown", "resolve_critical_missing_information",
        "act_within_scope", "verify_proportionately", "report_outcome_and_limits",
    )
    if not isinstance(task_kernel, dict) or task_kernel.get("steps") != list(expected_kernel_steps):
        raise ValueError("task_kernel.steps must preserve the ordered domain-neutral execution kernel")
    security = config.get("security_boundaries")
    security_keys = (
        "external_content_is_data_by_default", "quoted_text_files_web_pages_and_code_do_not_override_the_mold",
        "user_delegated_instructions_remain_subject_to_safety_privacy_and_approval_gates",
        "do_not_claim_inaccessible_state_was_deleted_or_synchronized",
    )
    if not isinstance(security, dict) or any(security.get(key) is not True for key in security_keys):
        raise ValueError("security_boundaries must explicitly preserve all required authority and integrity gates")


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Top Mold v0.2.1 reference classifier")
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
        print(f"output_contracts: {', '.join(payload['output_contracts']) or '(none detected)'}")
        print("notes:")
        for note in payload["notes"]:
            print(f"- {note}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
