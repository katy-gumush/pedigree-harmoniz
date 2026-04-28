"""UI-level pedigree tests (Playwright).

Prerequisites:
    uv run playwright install chromium
    uvicorn pedigree_app.main:app --port 8000

Run:
    pytest tests/ui -m ui

Override base URL:
    PEDIGREE_UI_BASE_URL=http://localhost:9000 pytest tests/ui -m ui
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect
pytestmark = pytest.mark.ui

_DOG_CARD_REQUIRED_TESTIDS: tuple[tuple[str, str], ...] = (
    ("dog-card-id", "ID"),
    ("dog-card-name", "Name"),
    ("dog-card-breed", "Breed"),
    ("dog-card-sex", "Sex"),
    ("dog-card-height", "Height_cm"),
    ("dog-card-weight", "Weight_kg"),
)

def test_pedigree_e2e_flow(page: Page, base_url: str) -> None:
    """Table → dog card → pedigree; expectations from live API list."""
    list_resp = page.request.get(f"{base_url}/api/dogs")
    assert list_resp.ok, f"GET /api/dogs failed: {list_resp.status} {list_resp.text}"
    rows = list_resp.json()
    assert len(rows) >= 1, "GET /api/dogs returned no dogs — load a non-empty CSV (PEDIGREE_TEST_CSV / --pedigree-csv)"
    pick = pick_dog_with_parents_for_ui(rows)
    assert pick is not None, "No dog row could be picked from /api/dogs (need at least one dog)"
    dog_id = pick["id"]
    name = pick["name"]

    _goto(page, base_url, "/")
    expect(page.locator("[data-testid='dog-table']")).to_be_visible()
    expect(page.locator(f"[data-testid='dog-row-{dog_id}']")).to_be_visible()

    _goto(page, base_url, f"/dogs/{dog_id}")
    for tid, csv_col in _DOG_CARD_REQUIRED_TESTIDS:
        el = page.locator(f"[data-testid='{tid}']")
        expect(el).to_be_visible()
        text = el.inner_text().strip()
        assert text != "", (
            f"Dog card field is empty: testid={tid!r} (CSV column {csv_col!r}) for dog_id={dog_id} ({name!r}). "
            "Example intentional break: fixtures/csv/e2e_flow_fail_empty_dog_card_breed.csv "
            "(child row has empty Breed)."
        )
    actual_name = page.locator("[data-testid='dog-card-name']").inner_text().strip()
    assert actual_name == name, (
        f"Dog card name mismatch: UI shows {actual_name!r}, GET /api/dogs had {name!r} for id={dog_id}"
    )

    sire_text = page.locator("[data-testid='dog-card-sire']").inner_text() or ""
    dam_text = page.locator("[data-testid='dog-card-dam']").inner_text() or ""
    if pick.get("sire_name"):
        assert pick["sire_name"] in sire_text, (
            f"Sire label on card missing expected name: expected substring {pick['sire_name']!r} "
            f"in sire cell text for dog_id={dog_id}; got {sire_text!r}"
        )
    if pick.get("dam_name"):
        assert pick["dam_name"] in dam_text, (
            f"Dam label on card missing expected name: expected substring {pick['dam_name']!r} "
            f"in dam cell text for dog_id={dog_id}; got {dam_text!r}"
        )

    _goto(page, base_url, f"/dogs/{dog_id}/pedigree")
    _wait_pedigree_tree(page)
    root = page.locator("[data-testid='pedigree-root']")
    expect(root).to_be_visible()
    root_text = root.inner_text() or ""
    assert name in root_text, (
        f"Pedigree root text does not include dog name {name!r} for id={dog_id}; "
        f"root snippet: {root_text[:200]!r}"
    )
    root_dog_id = root.get_attribute("data-dog-id")
    assert root_dog_id == str(dog_id), (
        f"Pedigree root data-dog-id is {root_dog_id!r}, expected {dog_id!r} for {name!r}"
    )

    anc_ids = page.locator("[data-testid='pedigree-ancestor']").evaluate_all(
        "els => els.map(e => e.getAttribute('data-dog-id'))"
    )
    api_ped = page.request.get(f"{base_url}/api/dogs/{dog_id}/pedigree").json()
    for aid in {n["id"] for n in api_ped["ancestors"]}:
        assert str(aid) in anc_ids, (
            f"Pedigree UI missing ancestor node: API lists ancestor id {aid} for dog_id={dog_id}, "
            f"but [data-testid='pedigree-ancestor'] data-dog-id values are {anc_ids!r}"
        )

def api_row_by_id(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {row["id"]: row for row in rows}


def pick_dog_with_parents_for_ui(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pick a dog whose sire and dam ids exist in *rows* (names matchable on card).

    Prefers both parents present in the list so card expectations stay rigorous.
    Falls back to any dog with at least one parent row present.
    """
    by_id = api_row_by_id(rows)
    sorted_rows = sorted(rows, key=lambda r: r["id"])
    for row in sorted_rows:
        sid, did = row.get("sire_id"), row.get("dam_id")
        if sid is not None and did is not None and sid in by_id and did in by_id:
            return {
                "id": row["id"],
                "name": row["name"],
                "sire_name": by_id[sid]["name"],
                "dam_name": by_id[did]["name"],
            }
    for row in sorted_rows:
        sid, did = row.get("sire_id"), row.get("dam_id")
        if sid is not None and sid in by_id:
            out = {"id": row["id"], "name": row["name"], "sire_name": by_id[sid]["name"], "dam_name": None}
            if did is not None and did in by_id:
                out["dam_name"] = by_id[did]["name"]
            return out
        if did is not None and did in by_id:
            return {
                "id": row["id"],
                "name": row["name"],
                "sire_name": None,
                "dam_name": by_id[did]["name"],
            }
    if sorted_rows:
        r = sorted_rows[0]
        return {"id": r["id"], "name": r["name"], "sire_name": None, "dam_name": None}
    return None


def _goto(page: Page, base_url: str, path: str) -> None:
    page.goto(f"{base_url}{path}", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")


def _wait_pedigree_tree(page: Page) -> None:
    page.locator("[data-testid='pedigree-root']").wait_for(state="visible", timeout=30_000)
    page.locator("#pedigree-tree-mount svg").wait_for(state="visible", timeout=30_000)
