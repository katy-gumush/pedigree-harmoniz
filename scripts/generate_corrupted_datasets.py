"""Write pedigree CSV fixtures for integrity tests.

Outputs to java-tests/src/test/resources/fixtures/:

  clean.csv
      Full copy of the repo baseline ``Dogs Pedigree.csv`` (all dogs).

  corrupt_bad_parent_id.csv
      Child lists Sire_ID=9999 (non-existent).

  corrupt_duplicate_id.csv
      Two rows share ID 1 (dict loader keeps last row).

  corrupt_immediate_loop.csv
      Dog 1 has Dam_ID=2; dog 2 has Sire_ID=1 — minimal two-node parent cycle.

  corrupt_long_cycle.csv
      Sire-only ring 1→2→3→1 (three-node cycle).

Corrupt fixtures stay small (one issue each). ``clean.csv`` is the full dataset
so ``cleanCsvPassesAll`` exercises the same row count as production.
"""

from __future__ import annotations

import csv
import shutil
from pathlib import Path

BASELINE = Path(__file__).parent.parent / "Dogs Pedigree.csv"
OUTPUT_DIR = Path(__file__).parent.parent / "java-tests/src/test/resources/fixtures"

FIELDNAMES = ["ID", "Name", "Breed", "Sex", "Height_cm", "Weight_kg", "Sire_ID", "Dam_ID"]


def _copy_clean() -> None:
    dest = OUTPUT_DIR / "clean.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(BASELINE, dest)
    print(f"  copied baseline → {dest} ({BASELINE.name})")


def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  wrote {len(rows)} rows → {path}")


def main() -> None:
    print(f"Reading baseline: {BASELINE}")
    print(f"Generating fixtures in: {OUTPUT_DIR}\n")

    _copy_clean()
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
