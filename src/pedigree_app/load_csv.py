"""Load and index dog records from a CSV file."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Dog:
    id: int
    name: str
    breed: str
    sex: str
    height_cm: float
    weight_kg: float
    sire_id: Optional[int]
    dam_id: Optional[int]


def load_dogs(csv_path: Path | str) -> dict[int, Dog]:
    """Parse the CSV and return a mapping of id → Dog.

    Empty sire_id / dam_id cells are normalized to None.
    Raises ValueError if a required field is missing or id is not an integer.
    """
    dogs: dict[int, Dog] = {}
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            dog_id = int(row["ID"])
            dogs[dog_id] = Dog(
                id=dog_id,
                name=row["Name"].strip(),
                breed=row["Breed"].strip(),
                sex=row["Sex"].strip(),
                height_cm=float(row["Height_cm"]),
                weight_kg=float(row["Weight_kg"]),
                sire_id=int(row["Sire_ID"]) if row["Sire_ID"].strip() else None,
                dam_id=int(row["Dam_ID"]) if row["Dam_ID"].strip() else None,
            )
    return dogs
