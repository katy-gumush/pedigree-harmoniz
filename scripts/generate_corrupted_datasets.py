"""Write minimal CSV fixtures for pedigree integrity tests.

Outputs to java-tests/src/test/resources/fixtures/:

  clean.csv
      Three dogs: two founders and one valid child (sire 1, dam 2).

  corrupt_bad_parent_id.csv
      Child lists Sire_ID=9999 (non-existent).

  corrupt_duplicate_id.csv
      Two rows share ID 1 (dict loader keeps last row).

  corrupt_immediate_loop.csv
      Dog 1 has Dam_ID=2; dog 2 has Sire_ID=1 — minimal two-node parent cycle.

  corrupt_long_cycle.csv
      Sire-only ring 1→2→3→1 (three-node cycle).

These files are small on purpose: data tests assert one failing rule per corrupt
file without scanning hundreds of rows.
"""

from __future__ import annotations

import csv
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "java-tests/src/test/resources/fixtures"

FIELDNAMES = ["ID", "Name", "Breed", "Sex", "Height_cm", "Weight_kg", "Sire_ID", "Dam_ID"]


def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  wrote {len(rows)} rows → {path}")


def main() -> None:
    print(f"Generating minimal fixtures in: {OUTPUT_DIR}\n")

    _write(
        OUTPUT_DIR / "clean.csv",
        [
            {"ID": "1", "Name": "Alpha", "Breed": "Mixed", "Sex": "M", "Height_cm": "50.0", "Weight_kg": "20.0", "Sire_ID": "", "Dam_ID": ""},
            {"ID": "2", "Name": "Bravo", "Breed": "Mixed", "Sex": "F", "Height_cm": "48.0", "Weight_kg": "18.0", "Sire_ID": "", "Dam_ID": ""},
            {"ID": "3", "Name": "Charlie", "Breed": "Mixed", "Sex": "M", "Height_cm": "45.0", "Weight_kg": "15.0", "Sire_ID": "1", "Dam_ID": "2"},
        ],
    )
    _write(
        OUTPUT_DIR / "corrupt_bad_parent_id.csv",
        [
            {"ID": "1", "Name": "Alpha", "Breed": "Mixed", "Sex": "M", "Height_cm": "50.0", "Weight_kg": "20.0", "Sire_ID": "", "Dam_ID": ""},
            {"ID": "2", "Name": "Bravo", "Breed": "Mixed", "Sex": "F", "Height_cm": "48.0", "Weight_kg": "18.0", "Sire_ID": "", "Dam_ID": ""},
            {"ID": "3", "Name": "BadKid", "Breed": "Mixed", "Sex": "F", "Height_cm": "45.0", "Weight_kg": "15.0", "Sire_ID": "9999", "Dam_ID": "1"},
        ],
    )
    _write(
        OUTPUT_DIR / "corrupt_duplicate_id.csv",
        [
            {"ID": "1", "Name": "First", "Breed": "Mixed", "Sex": "M", "Height_cm": "50.0", "Weight_kg": "20.0", "Sire_ID": "", "Dam_ID": ""},
            {"ID": "1", "Name": "Duplicate", "Breed": "Mixed", "Sex": "F", "Height_cm": "48.0", "Weight_kg": "18.0", "Sire_ID": "", "Dam_ID": ""},
        ],
    )
    _write(
        OUTPUT_DIR / "corrupt_immediate_loop.csv",
        [
            {"ID": "1", "Name": "A", "Breed": "Mixed", "Sex": "M", "Height_cm": "50.0", "Weight_kg": "20.0", "Sire_ID": "", "Dam_ID": "2"},
            {"ID": "2", "Name": "B", "Breed": "Mixed", "Sex": "F", "Height_cm": "48.0", "Weight_kg": "18.0", "Sire_ID": "1", "Dam_ID": ""},
        ],
    )
    _write(
        OUTPUT_DIR / "corrupt_long_cycle.csv",
        [
            {"ID": "1", "Name": "Gracie", "Breed": "Mixed", "Sex": "F", "Height_cm": "50.0", "Weight_kg": "20.0", "Sire_ID": "2", "Dam_ID": ""},
            {"ID": "2", "Name": "Riley", "Breed": "Mixed", "Sex": "M", "Height_cm": "48.0", "Weight_kg": "18.0", "Sire_ID": "3", "Dam_ID": ""},
            {"ID": "3", "Name": "Gus", "Breed": "Mixed", "Sex": "M", "Height_cm": "45.0", "Weight_kg": "15.0", "Sire_ID": "1", "Dam_ID": ""},
        ],
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
