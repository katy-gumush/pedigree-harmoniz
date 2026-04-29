"""CSV / in-memory pedigree integrity checks (Data Level test cases).

Used by ``test_data_level.py``. Pure Python, no FastAPI — suitable for Databricks pytest runs.
"""

from __future__ import annotations

import csv
from pathlib import Path

from pedigree_app.load_csv import Dog


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def fixtures_dir() -> Path:
    return repo_root() / "fixtures" / "csv"


def baseline_csv_path() -> Path:
    return repo_root() / "Dogs Pedigree.csv"


def duplicate_ids_in_csv(path: Path) -> list[int]:
    """Return dog IDs that appear more than once in the ID column."""
    counts: dict[int, int] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            did = int(row["ID"])
            counts[did] = counts.get(did, 0) + 1
    return sorted(did for did, c in counts.items() if c > 1)


def required_columns_present(header: list[str]) -> bool:
    required = {
        "ID",
        "Name",
        "Breed",
        "Sex",
        "Height_cm",
        "Weight_kg",
        "Sire_ID",
        "Dam_ID",
    }
    return required <= set(header)


def validate_parent_references_exist(dogs: dict[int, Dog]) -> list[str]:
    errors: list[str] = []
    for did, d in dogs.items():
        if d.sire_id is not None and d.sire_id not in dogs:
            errors.append(f"dog {did}: sire_id {d.sire_id} not in dataset")
        if d.dam_id is not None and d.dam_id not in dogs:
            errors.append(f"dog {did}: dam_id {d.dam_id} not in dataset")
    return errors


def validate_no_self_parent(dogs: dict[int, Dog]) -> list[str]:
    errors: list[str] = []
    for did, d in dogs.items():
        if d.sire_id == did:
            errors.append(f"dog {did}: sire_id equals own id")
        if d.dam_id == did:
            errors.append(f"dog {did}: dam_id equals own id")
    return errors


def validate_sex_roles(dogs: dict[int, Dog]) -> list[str]:
    """Sire should be Male, dam Female when referenced (D12)."""
    errors: list[str] = []
    for did, d in dogs.items():
        if d.sire_id is not None:
            s = dogs.get(d.sire_id)
            if s is not None and s.sex.strip().lower() != "male":
                errors.append(f"dog {did}: sire {d.sire_id} has sex {s.sex!r}, expected Male")
        if d.dam_id is not None:
            m = dogs.get(d.dam_id)
            if m is not None and m.sex.strip().lower() != "female":
                errors.append(f"dog {did}: dam {d.dam_id} has sex {m.sex!r}, expected Female")
    return errors


def validate_height_weight_sanity(
    dogs: dict[int, Dog],
    *,
    max_height_cm: float = 120.0,
    max_weight_kg: float = 120.0,
) -> list[str]:
    errors: list[str] = []
    for did, d in dogs.items():
        if d.height_cm <= 0 or d.weight_kg <= 0:
            errors.append(f"dog {did}: non-positive height_cm or weight_kg")
        if d.height_cm > max_height_cm or d.weight_kg > max_weight_kg:
            errors.append(
                f"dog {did}: unrealistic height_cm={d.height_cm} weight_kg={d.weight_kg}"
            )
    return errors


def directed_cycle_in_parent_edges(dogs: dict[int, Dog]) -> bool:
    """True if following child → sire/dam (existing IDs only) yields a directed cycle."""
    ids = set(dogs.keys())
    graph: dict[int, list[int]] = {}
    for did, d in dogs.items():
        graph[did] = [
            p
            for p in (d.sire_id, d.dam_id)
            if p is not None and p in ids
        ]

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[int, int] = {i: WHITE for i in ids}

    def dfs(u: int) -> bool:
        color[u] = GRAY
        for v in graph.get(u, []):
            c = color.get(v, WHITE)
            if c == GRAY:
                return True
            if c == WHITE and dfs(v):
                return True
        color[u] = BLACK
        return False

    for nid in ids:
        if color[nid] == WHITE and dfs(nid):
            return True
    return False


def baseline_integrity_errors(path: Path, dogs: dict[int, Dog]) -> list[str]:
    """Aggregate checks for a dataset expected to be clean (D01–D05, D12, D17)."""
    errors: list[str] = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if not required_columns_present(reader.fieldnames or []):
            errors.append("missing required CSV columns")
    dupes = duplicate_ids_in_csv(path)
    if dupes:
        errors.append(f"duplicate IDs in file: {sorted(set(dupes))}")
    errors.extend(validate_parent_references_exist(dogs))
    errors.extend(validate_no_self_parent(dogs))
    errors.extend(validate_sex_roles(dogs))
    errors.extend(validate_height_weight_sanity(dogs))
    return errors
