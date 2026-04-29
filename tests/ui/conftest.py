"""Playwright: session ``base_url`` for UI tests (override with ``PEDIGREE_UI_BASE_URL``)."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.environ.get("PEDIGREE_UI_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
