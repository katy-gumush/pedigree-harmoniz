"""Unit tests for pedigree_app.load_csv (CSV → Dog records)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pedigree_app.load_csv import Dog, load_dogs


def _write_csv(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_load_dogs_parses_row_and_null_parents(tmp_path: Path) -> None:
    csv_path = tmp_path / "dogs.csv"
    _write_csv(
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


def test_load_dogs_parent_ids(tmp_path: Path) -> None:
    csv_path = tmp_path / "dogs.csv"
    _write_csv(
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


def test_load_dogs_strips_name_breed_sex(tmp_path: Path) -> None:
    csv_path = tmp_path / "dogs.csv"
    _write_csv(
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


def test_load_dogs_duplicate_id_last_row_wins(tmp_path: Path) -> None:
    csv_path = tmp_path / "dogs.csv"
    _write_csv(
        csv_path,
        [
            "ID,Name,Breed,Sex,Height_cm,Weight_kg,Sire_ID,Dam_ID",
            "1,First,Boxer,Male,1.0,1.0,,",
            "1,Second,Beagle,Female,2.0,2.0,,",
        ],
    )
    assert load_dogs(csv_path)[1].name == "Second"


def test_load_dogs_invalid_id_raises(tmp_path: Path) -> None:
    csv_path = tmp_path / "dogs.csv"
    _write_csv(
        csv_path,
        [
            "ID,Name,Breed,Sex,Height_cm,Weight_kg,Sire_ID,Dam_ID",
            "x,A,Boxer,Male,1.0,1.0,,",
        ],
    )
    with pytest.raises(ValueError):
        load_dogs(csv_path)
