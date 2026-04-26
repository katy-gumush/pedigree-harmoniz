"""Generate deliberately corrupted CSV fixtures for pedigree integrity testing.

Produces three files in the target directory (default: java-tests/src/test/resources/fixtures/):

  clean.csv
      Exact copy of the baseline. Data tests must pass against this.

  corrupt_bad_parent_id.csv
      Dog 52 (Oliver) has its Sire_ID changed from 1 to 9999 — a non-existent id.
      Expected failure: "Sire_ID 9999 does not reference an existing dog" on row 52.

  corrupt_duplicate_id.csv
      Dog 582 (last row, Moose) has its ID changed to 1 — a duplicate of the first dog.
      Expected failure: "Duplicate ID 1" integrity check.

  corrupt_immediate_loop.csv
      Dog 1 (Max, a founder) gets Dam_ID=51, while dog 51 already has Sire_ID=1.
      This creates the immediate loop: 51 is child of 1, and 1 is child of 51.
      Expected failure: directed parent-graph cycle check.

  corrupt_long_cycle.csv
      Dogs 4→5→6 are founders in the baseline; each is given a single Sire_ID so
      4→5→6→4 forms a 3-node cycle (not detectable as an immediate two-dog swap).
      Expected failure: same directed cycle rule as corrupt_immediate_loop.csv.
"""

import csv
import shutil
from pathlib import Path

BASELINE = Path(__file__).parent.parent / "Dogs Pedigree.csv"
OUTPUT_DIR = Path(__file__).parent.parent / "java-tests/src/test/resources/fixtures"

FIELDNAMES = ["ID", "Name", "Breed", "Sex", "Height_cm", "Weight_kg", "Sire_ID", "Dam_ID"]


def _read_rows() -> list[dict]:
    with open(BASELINE, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  wrote {len(rows)} rows → {path.relative_to(Path.cwd()) if path.is_relative_to(Path.cwd()) else path}")


def generate_clean(rows: list[dict]) -> None:
    _write(OUTPUT_DIR / "clean.csv", rows)


def generate_bad_parent_id(rows: list[dict]) -> None:
    """Change dog 52's Sire_ID to a non-existent value (9999)."""
    mutated = []
    for row in rows:
        if row["ID"] == "52":
            row = dict(row, Sire_ID="9999")
        mutated.append(row)
    _write(OUTPUT_DIR / "corrupt_bad_parent_id.csv", mutated)


def generate_duplicate_id(rows: list[dict]) -> None:
    """Set the last row's ID to 1, colliding with the very first dog."""
    mutated = list(rows)
    mutated[-1] = dict(mutated[-1], ID="1")
    _write(OUTPUT_DIR / "corrupt_duplicate_id.csv", mutated)


def generate_immediate_loop(rows: list[dict]) -> None:
    """Make dog 1 (Max, a founder) a child of dog 51 (Henry), who is already a child of dog 1.
    This is the minimal A→B and B→A cycle the assignment describes.
    """
    mutated = []
    for row in rows:
        if row["ID"] == "1":
            row = dict(row, Dam_ID="51")
        mutated.append(row)
    _write(OUTPUT_DIR / "corrupt_immediate_loop.csv", mutated)


def generate_long_cycle(rows: list[dict]) -> None:
    """Close a 3-cycle on dogs 4, 5, 6 (Gracie → Riley → Gus → Gracie via Sire_ID only)."""
    mutated = []
    for row in rows:
        rid = row["ID"]
        if rid == "4":
            row = dict(row, Sire_ID="5", Dam_ID="")
        elif rid == "5":
            row = dict(row, Sire_ID="6", Dam_ID="")
        elif rid == "6":
            row = dict(row, Sire_ID="4", Dam_ID="")
        mutated.append(row)
    _write(OUTPUT_DIR / "corrupt_long_cycle.csv", mutated)


if __name__ == "__main__":
    print(f"Reading baseline: {BASELINE}")
    rows = _read_rows()
    print(f"Generating fixtures in: {OUTPUT_DIR}\n")
    generate_clean(rows)
    generate_bad_parent_id(rows)
    generate_duplicate_id(rows)
    generate_immediate_loop(rows)
    generate_long_cycle(rows)
    print("\nDone.")
