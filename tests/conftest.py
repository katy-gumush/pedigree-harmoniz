"""Shared pytest configuration: CSV path and API client.

Tests use a single filesystem path to the pedigree CSV:

  1. ``--pedigree-csv`` CLI option
  2. ``PEDIGREE_TEST_CSV`` environment variable
  3. Default: ``<repo>/fixtures/csv/clean.csv``

That path is written to ``PEDIGREE_CSV_PATH`` for the session so the FastAPI app
(``TestClient`` and any running uvicorn with the same env) loads the same file.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pedigree_app.datasets import COOKIE_NAME, clear_load_cache
from pedigree_app.main import app

_REPO_ROOT = Path(__file__).resolve().parent.parent

collect_ignore = ["ui"]


@pytest.fixture(scope="session")
def base_url() -> str:
    """Base URL for UI (Playwright) tests. Override with PEDIGREE_UI_BASE_URL."""
    return os.environ.get("PEDIGREE_UI_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--pedigree-csv",
        default=None,
        help="Path to Dogs CSV for tests (default: PEDIGREE_TEST_CSV or fixtures/csv/clean.csv).",
    )


@pytest.fixture(scope="session")
def pedigree_dataset_path(request: pytest.FixtureRequest) -> Path:
    """Absolute path to the active pedigree CSV for this test session."""
    opt = request.config.getoption("--pedigree-csv")
    env = os.environ.get("PEDIGREE_TEST_CSV")
    raw = opt or env
    if raw:
        p = Path(raw).expanduser().resolve()
    else:
        p = (_REPO_ROOT / "fixtures" / "csv" / "clean.csv").resolve()
    if not p.is_file():
        raise FileNotFoundError(f"Pedigree CSV not found: {p}")
    return p


@pytest.fixture(scope="session", autouse=True)
def _pedigree_csv_env(pedigree_dataset_path: Path) -> None:
    os.environ["PEDIGREE_CSV_PATH"] = str(pedigree_dataset_path)
    clear_load_cache()


@pytest.fixture
def api_client() -> TestClient:
    """HTTP client against the app (loads dogs from ``PEDIGREE_CSV_PATH``)."""
    client = TestClient(app)
    client.cookies.set(COOKIE_NAME, "full")
    return client
