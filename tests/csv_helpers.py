"""Tiny CSV snippets on disk for data-level loader tests."""

from __future__ import annotations

from pathlib import Path


def write_csv_lines(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
