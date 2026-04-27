"""Minimal in-memory `Dog` graphs for pedigree logic tests (no CSV / HTTP)."""

from __future__ import annotations

from pedigree_app.load_csv import Dog


def mini_dog(
    dog_id: int,
    *,
    sire_id: int | None = None,
    dam_id: int | None = None,
) -> Dog:
    return Dog(
        id=dog_id,
        name=f"dog{dog_id}",
        breed="B",
        sex="M",
        height_cm=1.0,
        weight_kg=1.0,
        sire_id=sire_id,
        dam_id=dam_id,
    )
