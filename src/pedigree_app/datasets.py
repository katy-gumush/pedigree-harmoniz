"""Registered CSV datasets and per-request selection (cookie).

The UI and API read the active dataset via :func:`dogs_for_cookie` (cookie value from the request).
Default is the full ``Dogs Pedigree.csv``; optional entries point at small
fixtures under ``java-tests/src/test/resources/fixtures/`` for manual checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pedigree_app.load_csv import Dog, load_dogs

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_FIXTURES_DIR = _REPO_ROOT / "java-tests" / "src" / "test" / "resources" / "fixtures"

COOKIE_NAME = "pedigree_dataset"
DEFAULT_DATASET_KEY = "full"


@dataclass(frozen=True)
class DatasetOption:
    """One selectable data source shown in the UI."""

    key: str
    label: str
    path: Path


def _options() -> tuple[DatasetOption, ...]:
    return (
        DatasetOption(
            key="full",
            label="Full dataset (Dogs Pedigree.csv)",
            path=_REPO_ROOT / "Dogs Pedigree.csv",
        ),
        DatasetOption(
            key="clean",
            label="Fixture: clean (minimal, valid)",
            path=_FIXTURES_DIR / "clean.csv",
        ),
        DatasetOption(
            key="bad_parent",
            label="Fixture: bad parent id (missing sire)",
            path=_FIXTURES_DIR / "corrupt_bad_parent_id.csv",
        ),
        DatasetOption(
            key="duplicate_id",
            label="Fixture: duplicate id",
            path=_FIXTURES_DIR / "corrupt_duplicate_id.csv",
        ),
        DatasetOption(
            key="immediate_loop",
            label="Fixture: two-dog parent cycle",
            path=_FIXTURES_DIR / "corrupt_immediate_loop.csv",
        ),
        DatasetOption(
            key="long_cycle",
            label="Fixture: three-dog sire cycle",
            path=_FIXTURES_DIR / "corrupt_long_cycle.csv",
        ),
    )


DATASET_OPTIONS: tuple[DatasetOption, ...] = _options()
_DATASET_PATHS: dict[str, Path] = {o.key: o.path for o in DATASET_OPTIONS}


def dataset_keys() -> frozenset[str]:
    return frozenset(_DATASET_PATHS.keys())


def resolve_dataset_key(raw: str | None) -> str:
    if raw and raw in _DATASET_PATHS:
        return raw
    return DEFAULT_DATASET_KEY


@lru_cache(maxsize=len(_DATASET_PATHS))
def _load_dataset(key: str) -> dict[int, Dog]:
    path = _DATASET_PATHS[key]
    if not path.is_file():
        raise FileNotFoundError(f"Dataset file missing for {key!r}: {path}")
    return load_dogs(path)


def dogs_for_cookie(cookie_value: str | None) -> dict[int, Dog]:
    """Return the dog map for the dataset chosen in the cookie (default full)."""
    key = resolve_dataset_key(cookie_value)
    return _load_dataset(key)


def selected_key_from_cookie(cookie_value: str | None) -> str:
    return resolve_dataset_key(cookie_value)
