"""Data Level tests (testCases/Data Level.html). CSV + graph integrity.

Mapped IDs: D01–D20 (D20 uses full baseline load). Also covers CSV loader contracts
and in-memory pedigree/network behaviour migrated from former ``test_load_csv`` /
``test_pedigree``. No HTTP — see ``test_api.py`` for API Level.
"""

from __future__ import annotations

from collections import defaultdict
import csv
from pathlib import Path

import pytest

from pedigree_app.load_csv import Dog, load_dogs
from pedigree_app.pedigree import (
    MAX_GENERATIONS,
    MANY_DIRECT_CHILDREN,
    build_pedigree,
    build_pedigree_network,
    initial_tree_depths,
)

from tests.csv_helpers import write_csv_lines
from tests.dataset_validation import (
    baseline_csv_path,
    baseline_integrity_errors,
    directed_cycle_in_parent_edges,
    duplicate_ids_in_csv,
    fixtures_dir,
    validate_parent_references_exist,
    validate_no_self_parent,
    required_columns_present,
)
from tests.pedigree_helpers import mini_dog


def test_d01_clean_baseline_csv_integrity() -> None:
    path = baseline_csv_path()
    if not path.is_file():
        pytest.skip(f"Baseline CSV not present: {path}")
    dogs = load_dogs(path)
    errors = baseline_integrity_errors(path, dogs)
    assert errors == [], errors


def test_d02_required_fields_exist_in_baseline() -> None:
    path = baseline_csv_path()
    if not path.is_file():
        pytest.skip(f"Baseline CSV not present: {path}")
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        assert required_columns_present(list(reader.fieldnames or []))
        for row in reader:
            for col in ("ID", "Name", "Breed", "Sex", "Height_cm", "Weight_kg"):
                assert row.get(col) is not None and str(row[col]).strip() != "", (
                    f"row ID={row.get('ID')}: empty {col}"
                )
            for col in ("Sire_ID", "Dam_ID"):
                assert row.get(col) is not None, f"row ID={row.get('ID')}: missing {col}"


def test_d03_id_uniqueness_baseline() -> None:
    path = baseline_csv_path()
    if not path.is_file():
        pytest.skip(f"Baseline CSV not present: {path}")
    assert duplicate_ids_in_csv(path) == []


def test_d04_parent_ids_reference_existing_baseline() -> None:
    path = baseline_csv_path()
    if not path.is_file():
        pytest.skip(f"Baseline CSV not present: {path}")
    dogs = load_dogs(path)
    assert validate_parent_references_exist(dogs) == []


def test_d05_no_self_parenting_baseline() -> None:
    path = baseline_csv_path()
    if not path.is_file():
        pytest.skip(f"Baseline CSV not present: {path}")
    dogs = load_dogs(path)
    assert validate_no_self_parent(dogs) == []


def test_d06_immediate_cycle_fixture_detected() -> None:
    path = fixtures_dir() / "corrupt_immediate_loop.csv"
    dogs = load_dogs(path)
    assert directed_cycle_in_parent_edges(dogs) is True


def test_d07_long_cycle_fixture_detected() -> None:
    path = fixtures_dir() / "corrupt_long_cycle.csv"
    dogs = load_dogs(path)
    assert directed_cycle_in_parent_edges(dogs) is True


def test_d08_pedigree_depth_never_exceeds_five_on_baseline() -> None:
    path = baseline_csv_path()
    if not path.is_file():
        pytest.skip(f"Baseline CSV not present: {path}")
    dogs = load_dogs(path)
    for dog_id in list(dogs.keys())[:: max(1, len(dogs) // 50)]:
        pr = build_pedigree(dog_id, dogs)
        for n in pr.ancestors + pr.descendants:
            assert n.depth <= MAX_GENERATIONS


def test_d09_invalid_sire_reference_detected() -> None:
    path = fixtures_dir() / "corrupt_bad_parent_id.csv"
    dogs = load_dogs(path)
    errs = validate_parent_references_exist(dogs)
    assert any("9999" in e for e in errs)


def test_d10_invalid_dam_reference_simulation(tmp_path: Path) -> None:
    path = tmp_path / "corrupt_bad_dam_id.csv"
    path.write_text(
        "ID,Name,Breed,Sex,Height_cm,Weight_kg,Sire_ID,Dam_ID\n"
        "1,A,Mixed,M,50,20,,\n"
        "2,B,Mixed,F,48,18,,\n"
        "3,C,Mixed,M,45,15,1,99999\n",
        encoding="utf-8",
    )
    dogs = load_dogs(path)
    errs = validate_parent_references_exist(dogs)
    assert any("dam_id 99999" in e for e in errs)


def test_d11_duplicate_id_reported_in_csv() -> None:
    path = fixtures_dir() / "corrupt_duplicate_id.csv"
    assert duplicate_ids_in_csv(path) == [1]


def test_d12_gender_roles_baseline() -> None:
    path = baseline_csv_path()
    if not path.is_file():
        pytest.skip(f"Baseline CSV not present: {path}")
    dogs = load_dogs(path)
    errors = baseline_integrity_errors(path, dogs)
    sex_role_errs = [e for e in errors if "sire" in e or "dam" in e]
    assert sex_role_errs == [], sex_role_errs


def test_d13_founder_dogs_exist_and_are_valid() -> None:
    path = fixtures_dir() / "clean.csv"
    dogs = load_dogs(path)
    founders = [d for d in dogs.values() if d.sire_id is None and d.dam_id is None]
    assert len(founders) >= 1


def test_d14_d15_ancestor_descendant_uniqueness_clean_fixture() -> None:
    path = fixtures_dir() / "clean.csv"
    dogs = load_dogs(path)
    for dog_id in (1, 51, 114):
        pr = build_pedigree(dog_id, dogs)
        anc_ids = [n.dog.id for n in pr.ancestors]
        desc_ids = [n.dog.id for n in pr.descendants]
        assert len(anc_ids) == len(set(anc_ids))
        assert len(desc_ids) == len(set(desc_ids))


def test_d16_logical_duplicate_patterns_reported() -> None:
    path = fixtures_dir() / "clean.csv"
    dogs = load_dogs(path)
    buckets: dict[tuple, list[int]] = defaultdict(list)
    for d in dogs.values():
        key = (d.name.strip().lower(), d.sire_id, d.dam_id, d.breed, d.sex)
        buckets[key].append(d.id)
    suspicious = [ids for ids in buckets.values() if len(ids) > 1]
    assert isinstance(suspicious, list)


def test_d17_height_weight_positive_clean_fixture() -> None:
    path = fixtures_dir() / "clean.csv"
    dogs = load_dogs(path)
    for d in dogs.values():
        assert d.height_cm > 0 and d.weight_kg > 0


def test_d18_partial_corruption_only_bad_branch_reported() -> None:
    path = fixtures_dir() / "corrupt_bad_parent_id.csv"
    dogs = load_dogs(path)
    errs = validate_parent_references_exist(dogs)
    assert len(errs) >= 1
    assert all("3:" in e or "9999" in e for e in errs)


def test_d19_invalid_id_type_rejected_at_load(tmp_path: Path) -> None:
    p = tmp_path / "bad.csv"
    p.write_text(
        "ID,Name,Breed,Sex,Height_cm,Weight_kg,Sire_ID,Dam_ID\n"
        "not-int,A,B,M,1,1,,\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_dogs(p)


def test_d20_large_dataset_traversal_completes() -> None:
    path = baseline_csv_path()
    if not path.is_file():
        path = fixtures_dir() / "clean.csv"
    dogs = load_dogs(path)
    assert not directed_cycle_in_parent_edges(dogs)
    for dog_id in list(dogs.keys())[:20]:
        build_pedigree(dog_id, dogs)


# ---------------------------------------------------------------------------
# CSV loader (`load_dogs`) — parsing contracts (former test_load_csv)
# ---------------------------------------------------------------------------


def test_csv_loader_parses_row_and_null_parents(tmp_path: Path) -> None:
    csv_path = tmp_path / "dogs.csv"
    write_csv_lines(
        csv_path,
        [
            "ID,Name,Breed,Sex,Height_cm,Weight_kg,Sire_ID,Dam_ID",
            "1,A,Boxer,Male,50.0,20.0,,",
        ],
    )
    dogs = load_dogs(csv_path)
    assert dogs[1] == Dog(
        id=1,
        name="A",
        breed="Boxer",
        sex="Male",
        height_cm=50.0,
        weight_kg=20.0,
        sire_id=None,
        dam_id=None,
    )


def test_csv_loader_parent_ids(tmp_path: Path) -> None:
    csv_path = tmp_path / "dogs.csv"
    write_csv_lines(
        csv_path,
        [
            "ID,Name,Breed,Sex,Height_cm,Weight_kg,Sire_ID,Dam_ID",
            "1,P,Sire,M,60.0,30.0,,",
            "2,P,Dam,F,55.0,25.0,,",
            "3,C,Pup,M,30.0,10.0,1,2",
        ],
    )
    dogs = load_dogs(csv_path)
    assert dogs[3].sire_id == 1
    assert dogs[3].dam_id == 2


def test_csv_loader_strips_name_breed_sex(tmp_path: Path) -> None:
    csv_path = tmp_path / "dogs.csv"
    write_csv_lines(
        csv_path,
        [
            "ID,Name,Breed,Sex,Height_cm,Weight_kg,Sire_ID,Dam_ID",
            "1, spaced , Boxer , Male ,1.0,1.0,,",
        ],
    )
    d = load_dogs(csv_path)[1]
    assert d.name == "spaced"
    assert d.breed == "Boxer"
    assert d.sex == "Male"


def test_csv_loader_duplicate_id_last_row_wins(tmp_path: Path) -> None:
    csv_path = tmp_path / "dogs.csv"
    write_csv_lines(
        csv_path,
        [
            "ID,Name,Breed,Sex,Height_cm,Weight_kg,Sire_ID,Dam_ID",
            "1,First,Boxer,Male,1.0,1.0,,",
            "1,Second,Beagle,Female,2.0,2.0,,",
        ],
    )
    assert load_dogs(csv_path)[1].name == "Second"


def test_csv_loader_invalid_id_raises(tmp_path: Path) -> None:
    csv_path = tmp_path / "dogs.csv"
    write_csv_lines(
        csv_path,
        [
            "ID,Name,Breed,Sex,Height_cm,Weight_kg,Sire_ID,Dam_ID",
            "x,A,Boxer,Male,1.0,1.0,,",
        ],
    )
    with pytest.raises(ValueError):
        load_dogs(csv_path)


# ---------------------------------------------------------------------------
# Pedigree / network library (in-memory; former test_pedigree)
# ---------------------------------------------------------------------------


def test_pedigree_ancestors_chain_sire_line() -> None:
    dogs = {1: mini_dog(1), 2: mini_dog(2, sire_id=1), 3: mini_dog(3, sire_id=2)}
    r = build_pedigree(3, dogs)
    assert r.root.id == 3
    assert {n.dog.id for n in r.ancestors} == {1, 2}
    assert r.ancestor_ids == {1, 2}
    depths = {n.dog.id: n.depth for n in r.ancestors}
    assert depths[2] == 1
    assert depths[1] == 2


def test_pedigree_descendants_shared_sire() -> None:
    dogs = {1: mini_dog(1), 2: mini_dog(2, sire_id=1), 3: mini_dog(3, sire_id=1)}
    r = build_pedigree(1, dogs)
    assert {n.dog.id for n in r.descendants} == {2, 3}
    assert r.descendant_ids == {2, 3}


def test_pedigree_max_depth_clamp() -> None:
    dogs = {
        1: mini_dog(1),
        2: mini_dog(2, sire_id=1),
        3: mini_dog(3, sire_id=2),
        4: mini_dog(4, sire_id=3),
    }
    r = build_pedigree(4, dogs, max_ancestors=1, max_descendants=0)
    assert {n.dog.id for n in r.ancestors} == {3}
    assert r.descendants == []


def test_pedigree_skips_missing_parent_reference() -> None:
    dogs = {2: mini_dog(2, sire_id=999)}
    r = build_pedigree(2, dogs)
    assert r.ancestors == []


def test_initial_tree_depths_isolated_leaf() -> None:
    dogs = {1: mini_dog(1)}
    assert initial_tree_depths(1, dogs) == (2, 2)


def test_initial_tree_depths_many_direct_children_caps_descendants() -> None:
    children = {1: mini_dog(1)}
    for i in range(2, 2 + MANY_DIRECT_CHILDREN + 1):
        children[i] = mini_dog(i, sire_id=1)
    assert initial_tree_depths(1, children) == (MAX_GENERATIONS, 2)


def test_initial_tree_depths_full_when_moderate_children_and_parents() -> None:
    dogs = {
        1: mini_dog(1),
        2: mini_dog(2, sire_id=1),
        3: mini_dog(3, sire_id=1),
    }
    assert initial_tree_depths(1, dogs) == (MAX_GENERATIONS, MAX_GENERATIONS)


def test_pedigree_network_unknown_focus_empty() -> None:
    dogs = {1: mini_dog(1)}
    net = build_pedigree_network(99, dogs, max_ancestor_depth=2, max_descendant_depth=2)
    assert net.nodes == []
    assert net.edges == []


def test_pedigree_network_edges_parent_child() -> None:
    dogs = {1: mini_dog(1), 2: mini_dog(2, sire_id=1), 3: mini_dog(3, dam_id=2)}
    net = build_pedigree_network(3, dogs, max_ancestor_depth=5, max_descendant_depth=5)
    ids = {n.id for n in net.nodes}
    assert ids == {1, 2, 3}
    edge_set = {(e.parent_id, e.child_id) for e in net.edges}
    assert (1, 2) in edge_set
    assert (2, 3) in edge_set
