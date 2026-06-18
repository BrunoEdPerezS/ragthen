"""Obsidian vault operations for Raghtena — minimal read-only."""

from pathlib import Path

_LOG_TAG = "[ragthtena]"


def resolve(path: str | None = None) -> str | None:
    from ragthtena_core.config import load_config
    p = path or load_config().get("vault_path", "")
    if not p:
        return None
    return str(Path(p).expanduser().resolve())


def scan_notes(vault: str) -> dict[str, list[Path]]:
    vault_p = Path(vault).expanduser().resolve()
    if not vault_p.is_dir():
        return {}
    notes: dict[str, list[Path]] = {}
    for md_file in vault_p.rglob("*.md"):
        if any(p.startswith(".") for p in md_file.relative_to(vault_p).parts):
            continue
        key = md_file.stem.lower()
        notes.setdefault(key, []).append(md_file)
    return notes


def read_note(vault: str, rel_path: str) -> str | None:
    vault_p = Path(vault).expanduser().resolve()
    fp = (vault_p / rel_path).with_suffix(".md")
    if not fp.exists():
        return None
    return fp.read_text(encoding="utf-8")
