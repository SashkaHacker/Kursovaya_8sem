from __future__ import annotations

from pathlib import Path


def ensure_directories(*paths: Path) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def build_export_name(base_name: str) -> str:
    safe_stem = "".join(ch for ch in base_name if ch.isalnum() or ch in {"-", "_"})
    return safe_stem or "recognized_text"
