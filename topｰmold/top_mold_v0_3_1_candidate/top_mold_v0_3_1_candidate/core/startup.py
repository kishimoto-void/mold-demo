"""Read-only startup inspection; never creates or overwrites the inspected file."""
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class PersonaFileState:
    status: str
    message: str


def inspect_persona_file(path: str | Path) -> PersonaFileState:
    target = Path(path)
    if target.is_symlink() and not target.exists():
        return PersonaFileState("ERROR", "指定先が未解決のシンボリックリンクです。欠損ファイルとして自動作成しません。")
    if not target.exists():
        return PersonaFileState("ABSENT", "パーソナライズMDはありません。標準設定で起動できます。")
    if not target.is_file():
        return PersonaFileState("ERROR", "指定先が通常ファイルではありません。既存データは変更していません。")
    try:
        content = target.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return PersonaFileState("ERROR", f"MDを読み込めませんでした（{type(exc).__name__}）。ファイルは変更していません。")
    if not content.strip():
        return PersonaFileState("EMPTY", "MDは存在しますが空です。置き換える場合は明示確認が必要です。")
    return PersonaFileState("PRESENT", "既存のパーソナライズMDを検出しました。自動上書きは行いません。")
