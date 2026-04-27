"""Shared pytest fixtures for API tests (FastAPI TestClient + dataset cookie)."""

from __future__ import annotations

# Exclude Playwright UI tests from default collection; run with ``pytest tests/ui``.
collect_ignore = ["ui"]

import pytest
from fastapi.testclient import TestClient

from pedigree_app.datasets import COOKIE_NAME
from pedigree_app.main import app


@pytest.fixture
def api_client() -> TestClient:
    """Unconfigured client — set cookies per request or use ``client_with_dataset``."""
    return TestClient(app)


@pytest.fixture
def client_clean(api_client: TestClient) -> TestClient:
    """API client using the ``clean`` fixture CSV (subset / baseline copy)."""
    api_client.cookies.set(COOKIE_NAME, "clean")
    return api_client


@pytest.fixture
def client_dataset(api_client: TestClient):
    """Factory: ``client_dataset(\"bad_parent\")`` sets the pedigree_dataset cookie."""

    def _set(key: str) -> TestClient:
        api_client.cookies.set(COOKIE_NAME, key)
        return api_client

    return _set
