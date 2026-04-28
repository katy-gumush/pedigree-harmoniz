"""CSV dataset path from ``PEDIGREE_CSV_PATH`` or default ``Dogs Pedigree.csv``.

There is a single active dataset file per process. Override with::

    export PEDIGREE_CSV_PATH=/path/to/file.csv

No registry of named shortcuts — the path is the source of truth.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pedigree_app.load_csv import Dog, load_dogs

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

COOKIE_NAME = "pedigree_dataset"
DEFAULT_DATASET_KEY = "full"


def apply_pedigree_dataset_cookie(response, key: str) -> None:
    """Set the ``pedigree_dataset`` cookie (legacy; loading uses ``PEDIGREE_CSV_PATH`` only)."""
    response.set_cookie(
        COOKIE_NAME,
        key,
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        samesite="lax",
        path="/",
    )


@dataclass(frozen=True)
class DatasetOption:
    """One row for templates / ``GET /api/dataset`` (single CSV)."""

    key: str
    label: str
    path: Path


def primary_csv_path() -> Path:
    """Resolved path to the active CSV (env override or repo baseline)."""
    override = os.environ.get("PEDIGREE_CSV_PATH")
    if override:
        return Path(override).expanduser().resolve()
    return _REPO_ROOT / "Dogs Pedigree.csv"


@lru_cache(maxsize=64)
def _load_dogs_cached(resolved_str: str) -> dict[int, Dog]:
    path = Path(resolved_str)
    if not path.is_file():
        raise FileNotFoundError(f"Dataset file missing: {path}")
    return load_dogs(path)


def dogs_for_cookie(cookie_value: str | None) -> dict[int, Dog]:
    """Return dogs loaded from ``PEDIGREE_CSV_PATH`` (cookie does not select a file)."""
    p = primary_csv_path()
    return _load_dogs_cached(str(p.resolve()))


def dataset_keys() -> frozenset[str]:
    """Legacy API compatibility — only ``full`` is valid."""
    return frozenset({DEFAULT_DATASET_KEY})


def resolve_dataset_key(raw: str | None) -> str:
    return DEFAULT_DATASET_KEY


def selected_key_from_cookie(cookie_value: str | None) -> str:
    return DEFAULT_DATASET_KEY


def get_dataset_options() -> tuple[DatasetOption, ...]:
    """Current CSV for navbar / API listing."""
    p = primary_csv_path()
    return (
        DatasetOption(
            key="full",
            label=p.name,
            path=p,
        ),
    )


def clear_load_cache() -> None:
    """Invalidate cached loads (e.g. tests after changing ``PEDIGREE_CSV_PATH``)."""
    _load_dogs_cached.cache_clear()
