"""API tests: list size vs CSV rows, pedigree JSON vs ``build_pedigree``.

Run:
    pytest tests/test_api.py
    pytest tests/test_api.py --pedigree-csv=fixtures/csv/clean.csv
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from fastapi.testclient import TestClient

from pedigree_app.load_csv import Dog, load_dogs
from pedigree_app.pedigree import build_pedigree


def test_list_count_matches_csv_row_count(
    api_client: TestClient,
    pedigree_dataset_path: Path,
) -> None:
    """``GET /api/dogs`` length equals CSV data-row count; ID mismatch details on failure."""
    raw_rows = _read_csv_data_rows(pedigree_dataset_path)
    expected = len(raw_rows)
    r = api_client.get("/api/dogs")
    assert r.status_code == 200
    body = r.json()
    got = len(body)
    api_ids = {d["id"] for d in body}
    if expected != got:
        extra = _id_mismatch_details(raw_rows, api_ids)
        msg = f"Number of dogs doesn't match expected {expected} got {got}"
        if extra:
            msg += f"\n{extra}"
        raise AssertionError(msg)


# def test_pedigree_matches_library(
#     api_client: TestClient,
#     pedigree_dataset_path: Path,
# ) -> None:
#     """``GET /api/dogs/{id}/pedigree`` matches ``build_pedigree`` for ``min(id)``."""
#     dogs = load_dogs(pedigree_dataset_path)
#     focus_id = _first_dog_id(dogs)
#     expected = build_pedigree(focus_id, dogs)

#     r = api_client.get(f"/api/dogs/{focus_id}/pedigree")
#     assert r.status_code == 200
#     payload = r.json()

#     assert payload["root"]["id"] == expected.root.id
#     assert {n["id"] for n in payload["ancestors"]} == expected.ancestor_ids
#     assert {n["id"] for n in payload["descendants"]} == expected.descendant_ids


# def _first_dog_id(dogs: dict[int, Dog]) -> int:
#     """Stable choice: smallest id in the dataset."""
#     return min(dogs.keys())


def _read_csv_data_rows(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _parse_row_id(row: dict[str, str]) -> int | None:
    raw = row.get("ID")
    if raw is None or not str(raw).strip():
        return None
    try:
        return int(str(raw).strip())
    except ValueError:
        return None


def _id_mismatch_details(
    raw_rows: list[dict[str, str]],
    api_ids: set[int],
) -> str:
    """Compare IDs from CSV rows to API; list rows/ids with no match on either side."""
    lines: list[str] = []
    row_ids: list[tuple[int | None, dict[str, str]]] = [
        (_parse_row_id(r), r) for r in raw_rows
    ]
    file_ids = {i for i, _ in row_ids if i is not None}

    only_csv = sorted(file_ids - api_ids)
    if only_csv:
        lines.append(f"IDs in CSV but not in API: {only_csv}")
        for oid in only_csv:
            for i, row in row_ids:
                if i == oid:
                    lines.append(f"  row: {row}")

    only_api = sorted(api_ids - file_ids)
    if only_api:
        lines.append(f"IDs in API but not in CSV: {only_api}")

    bad_id_rows = [r for i, r in row_ids if i is None]
    if bad_id_rows:
        lines.append("Rows with missing or non-integer ID:")
        for row in bad_id_rows:
            lines.append(f"  {row}")

    by_id: dict[int, list[dict[str, str]]] = defaultdict(list)
    for i, row in row_ids:
        if i is not None:
            by_id[i].append(row)
    surplus: list[dict[str, str]] = []
    for pid in sorted(by_id):
        occ = by_id[pid]
        if len(occ) > 1:
            surplus.extend(occ[:-1])
    if surplus:
        lines.append(
            "Extra CSV rows for an ID that already appears earlier "
            "(API exposes one dog per ID):"
        )
        for row in surplus:
            lines.append(f"  {row}")

    return "\n".join(lines)
