"""UI Level tests (testCases/UI Level.html). Playwright — requires running app + Chromium.

Run manually after ``playwright install chromium``::

    PYTHONPATH=src uvicorn pedigree_app.main:app --port 8000
    pytest -m ui

Databricks notebook excludes ``ui`` tests (see ``databricks/run_unit_tests.py``).
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.ui

# Golden dog (full baseline): Henry, parents Max #1 and Lucy #2
KNOWN_ID = 51
KNOWN_NAME = "Henry"
SIRE_NAME = "Max"
DAM_NAME = "Lucy"
FOUNDER_ID = 3  # Maggie — founder with descendants
DEEP_TREE_ID = 452  # Louie — exercises dedup / depth in Java suite
UNKNOWN_ID = 99999


def _goto(page: Page, base_url: str, path: str) -> None:
    page.goto(f"{base_url}{path}", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")


def _select_dataset(page: Page, key: str) -> None:
    """Navbar dropdown POSTs /dataset and redirects; wait so the next ``goto`` does not race."""
    with page.expect_navigation(timeout=30_000):
        page.locator("[data-testid='dataset-select']").select_option(key)
    page.wait_for_load_state("domcontentloaded")


def _wait_pedigree_tree(page: Page) -> None:
    page.locator("[data-testid='pedigree-root']").wait_for(state="visible", timeout=30_000)
    page.locator("#pedigree-tree-mount svg").wait_for(state="visible", timeout=30_000)


def test_u01_home_page_displays_dogs_table(page: Page, base_url: str) -> None:
    _goto(page, base_url, "/")
    table = page.locator("[data-testid='dog-table']")
    expect(table).to_be_visible()
    rows = page.locator("[data-testid^='dog-row-']")
    expect(rows.first).to_be_visible()
    assert rows.count() > 100


def test_u02_known_dog_appears_in_list(page: Page, base_url: str) -> None:
    _goto(page, base_url, "/")
    row = page.locator(f"[data-testid='dog-row-{KNOWN_ID}']")
    expect(row).to_be_visible()
    assert KNOWN_NAME in (row.inner_text() or "")


def test_u03_search_filters_list(page: Page, base_url: str) -> None:
    _goto(page, base_url, "/")
    search = page.locator("[data-testid='dog-search-input']")
    search.fill("zzzznomatch999")
    expect(page.locator(f"[data-testid='dog-row-{KNOWN_ID}']")).not_to_be_visible()
    search.fill(KNOWN_NAME)
    expect(page.locator(f"[data-testid='dog-row-{KNOWN_ID}']")).to_be_visible()


def test_u04_open_dog_card_from_list(page: Page, base_url: str) -> None:
    _goto(page, base_url, "/")
    page.locator(f"[data-testid='dog-link-{KNOWN_ID}']").click()
    page.wait_for_load_state("networkidle")
    expect(page.locator("[data-testid='dog-card']")).to_be_visible()


def test_u05_dog_card_required_fields(page: Page, base_url: str) -> None:
    _goto(page, base_url, f"/dogs/{KNOWN_ID}")
    for tid in (
        "dog-card-id",
        "dog-card-name",
        "dog-card-breed",
        "dog-card-sex",
        "dog-card-height",
        "dog-card-weight",
    ):
        el = page.locator(f"[data-testid='{tid}']")
        expect(el).to_be_visible()
        assert el.inner_text().strip() != ""
    assert page.locator("[data-testid='dog-card-name']").inner_text().strip() == KNOWN_NAME


def test_u06_dog_card_parent_names(page: Page, base_url: str) -> None:
    _goto(page, base_url, f"/dogs/{KNOWN_ID}")
    sire = page.locator("[data-testid='dog-card-sire']").inner_text() or ""
    dam = page.locator("[data-testid='dog-card-dam']").inner_text() or ""
    assert SIRE_NAME in sire
    assert DAM_NAME in dam


def test_u07_open_pedigree_view(page: Page, base_url: str) -> None:
    _goto(page, base_url, f"/dogs/{KNOWN_ID}")
    page.locator("[data-testid='pedigree-link']").click()
    page.wait_for_load_state("networkidle")
    assert page.url.rstrip("/").endswith(f"/dogs/{KNOWN_ID}/pedigree")


def test_u08_pedigree_root_shows_selected_dog(page: Page, base_url: str) -> None:
    _goto(page, base_url, f"/dogs/{KNOWN_ID}/pedigree")
    root = page.locator("[data-testid='pedigree-root']")
    expect(root).to_be_visible()
    text = root.inner_text() or ""
    assert KNOWN_NAME in text
    assert str(KNOWN_ID) in text
    assert root.get_attribute("data-dog-id") == str(KNOWN_ID)


def test_u09_immediate_ancestors_displayed(page: Page, base_url: str) -> None:
    _goto(page, base_url, f"/dogs/{KNOWN_ID}/pedigree")
    _wait_pedigree_tree(page)
    anc = page.locator("[data-testid='pedigree-ancestor']")
    expect(anc.first).to_be_visible()
    ids = anc.evaluate_all("els => els.map(e => e.getAttribute('data-dog-id'))")
    assert "1" in ids and "2" in ids


def test_u10_descendants_for_founder(page: Page, base_url: str) -> None:
    _goto(page, base_url, f"/dogs/{FOUNDER_ID}/pedigree")
    _wait_pedigree_tree(page)
    desc = page.locator("[data-testid='pedigree-descendant']")
    assert desc.count() >= 1


def test_u11_founder_empty_ancestor_fallback(page: Page, base_url: str) -> None:
    _goto(page, base_url, f"/dogs/{FOUNDER_ID}/pedigree")
    expect(page.locator("[data-testid='pedigree-no-ancestors']")).to_be_visible()
    assert page.locator("[data-testid='pedigree-ancestor']").count() == 0


def test_u12_no_duplicate_ancestor_ids_complex_tree(page: Page, base_url: str) -> None:
    _goto(page, base_url, f"/dogs/{DEEP_TREE_ID}/pedigree")
    _wait_pedigree_tree(page)
    anc = page.locator("[data-testid='pedigree-ancestor']")
    ids = anc.evaluate_all("els => els.map(e => e.getAttribute('data-dog-id'))")
    assert len(ids) == len(set(ids))


def test_u13_depth_labels_at_most_five(page: Page, base_url: str) -> None:
    _goto(page, base_url, f"/dogs/{KNOWN_ID}/pedigree")
    _wait_pedigree_tree(page)
    for role in ("pedigree-ancestor", "pedigree-descendant"):
        depths = page.locator(f"[data-testid='{role}']").evaluate_all(
            "els => els.map(e => parseInt(e.getAttribute('data-depth') || '0', 10))"
        )
        for d in depths:
            assert d <= 5


def test_u14_unknown_dog_error_page(page: Page, base_url: str) -> None:
    _goto(page, base_url, f"/dogs/{UNKNOWN_ID}")
    expect(page.locator("[data-testid='error-message']")).to_be_visible()
    body = page.locator("body").inner_text() or ""
    assert "Traceback (most recent call last)" not in body


def test_u15_missing_parent_fallback_bad_dataset(page: Page, base_url: str) -> None:
    _goto(page, base_url, "/")
    _select_dataset(page, "bad_parent")
    _goto(page, base_url, "/dogs/3")
    sire = page.locator("[data-testid='dog-card-sire']").inner_text() or ""
    assert "Unknown" in sire or "9999" in sire


def test_u16_cycle_dataset_ui_loads(page: Page, base_url: str) -> None:
    _goto(page, base_url, "/")
    _select_dataset(page, "immediate_loop")
    _goto(page, base_url, "/dogs/1/pedigree")
    _wait_pedigree_tree(page)
    expect(page.locator("[data-testid='pedigree-root']")).to_be_visible()


def test_u17_api_matches_ui_pedigree_ids(page: Page, base_url: str) -> None:
    api = page.request.get(f"{base_url}/api/dogs/{KNOWN_ID}/pedigree")
    assert api.ok
    data = api.json()
    api_anc = {n["id"] for n in data["ancestors"]}
    api_desc = {n["id"] for n in data["descendants"]}

    _goto(page, base_url, f"/dogs/{KNOWN_ID}/pedigree")
    _wait_pedigree_tree(page)
    ui_anc = set(
        page.locator("[data-testid='pedigree-ancestor']").evaluate_all(
            "els => els.map(e => e.getAttribute('data-dog-id')).filter(Boolean)"
        )
    )
    ui_anc_int = {int(x) for x in ui_anc}
    ui_desc = set(
        page.locator("[data-testid='pedigree-descendant']").evaluate_all(
            "els => els.map(e => e.getAttribute('data-dog-id')).filter(Boolean)"
        )
    )
    ui_desc_int = {int(x) for x in ui_desc}
    assert ui_anc_int == api_anc
    assert ui_desc_int == api_desc


def test_u18_table_still_usable_many_rows(page: Page, base_url: str) -> None:
    _goto(page, base_url, "/")
    wrap = page.locator(".table-responsive")
    expect(wrap).to_be_visible()
    assert page.locator("[data-testid='dog-table'] tbody tr").count() > 50


def test_u19_data_refresh_after_dataset_switch(page: Page, base_url: str) -> None:
    _goto(page, base_url, "/")
    _select_dataset(page, "duplicate_id")
    assert page.locator("[data-testid^='dog-row-']").count() <= 5
    _select_dataset(page, "full")
    assert page.locator("[data-testid^='dog-row-']").count() > 100


def test_u20_visual_empty_descendants_leaf(page: Page, base_url: str) -> None:
    res = page.request.get(f"{base_url}/api/dogs")
    assert res.ok
    dogs = res.json()
    leaf_id = None
    for d in reversed(dogs):
        pid = d["id"]
        pr = page.request.get(f"{base_url}/api/dogs/{pid}/pedigree")
        if pr.ok and len(pr.json().get("descendants", [])) == 0:
            leaf_id = pid
            break
    assert leaf_id is not None
    _goto(page, base_url, f"/dogs/{leaf_id}/pedigree")
    expect(page.locator("[data-testid='pedigree-no-descendants']")).to_be_visible()


def test_u21_pedigree_flow_preserves_dog_context(page: Page, base_url: str) -> None:
    _goto(page, base_url, f"/dogs/{KNOWN_ID}")
    page.locator("[data-testid='pedigree-link']").click()
    page.wait_for_load_state("networkidle")
    page.locator(f'.breadcrumb a[href="/dogs/{KNOWN_ID}"]').click()
    page.wait_for_load_state("networkidle")
    assert f"/dogs/{KNOWN_ID}" in page.url
    expect(page.locator("[data-testid='dog-card-name']")).to_contain_text(KNOWN_NAME)


def test_u22_corrupt_data_not_silent_bad_parent_card(page: Page, base_url: str) -> None:
    _goto(page, base_url, "/")
    _select_dataset(page, "bad_parent")
    _goto(page, base_url, "/dogs/3")
    html = page.content()
    assert "Unknown" in html or "danger" in html
