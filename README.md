# Pedigree Explorer

A small web application that exposes a dogs pedigree dataset as a REST API and HTML UI, together with a complete automated test suite covering data integrity, API contracts, and UI behavior.

## Project structure

```
pedigree/
  Dogs Pedigree.csv              baseline dataset (581 dogs)
  pyproject.toml                 Python app build definition
  src/pedigree_app/
    load_csv.py                  CSV → typed Dog records
    pedigree.py                  BFS ancestor/descendant traversal, depth ≤ 5
    main.py                      FastAPI app (REST + Jinja2 UI)
    templates/                   HTML pages with data-testid attributes
    static/                      CSS
  scripts/
    generate_corrupted_datasets.py   copies baseline to clean.csv; writes small corrupt fixtures
  tests/
    test_load_csv.py, test_pedigree.py   pytest unit tests for `pedigree_app` (CSV + pedigree logic)
  databricks/
    run_unit_tests.py              Databricks notebook source: `%pip` + pytest on `tests/` (Repos)
  java-tests/
    pom.xml                      Maven project (JUnit 5 + Commons CSV + REST Assured + Playwright)
    src/test/java/com/pedigree/
      data/PedigreeCsvIntegrityTest.java    data-layer tests
      api/PedigreeApiTest.java              API-layer tests
      ui/PedigreeUiTest.java                UI-layer Playwright tests
    src/test/resources/fixtures/   clean (full baseline) + minimal corrupt CSVs (generated)
  TESTING.md                     test strategy and error scenario explanations
```

## Requirements

| Toolchain | Minimum version |
|-----------|----------------|
| Python    | 3.11            |
| Java      | 21 (Temurin)    |
| Maven     | 3.9             |

## Quick start

### 1 — Install Python dependencies

```bash
# from the repo root
uv venv .venv                    # or: python -m venv .venv
uv pip install -e .              # installs fastapi, uvicorn, jinja2, etc.
```

### 2 — Generate test fixtures (corrupted CSVs)

```bash
.venv/bin/python scripts/generate_corrupted_datasets.py
```

This copies `Dogs Pedigree.csv` to `clean.csv` and writes four small corrupted variants into `java-tests/src/test/resources/fixtures/` (one issue per corrupt file).

### 3 — Start the application

```bash
PYTHONPATH=src .venv/bin/uvicorn pedigree_app.main:app --reload
```

The app listens on `http://127.0.0.1:8000` by default.

**Switching data:** The navbar **Data source** dropdown and **`POST /api/dataset`**
(JSON `{"dataset":"<key>"}`) set the same cookie—no restart. Registry includes the
primary CSV (`full`), baseline copy (`clean`), and minimal corrupt fixtures.

Optional **`PEDIGREE_CSV_PATH`** overrides which file backs the **`full`** key only
(CI path to the baseline); you can still switch to fixtures via UI or API.

```bash
PEDIGREE_CSV_PATH=/absolute/path/to/Dogs\ Pedigree.csv \
  PYTHONPATH=src .venv/bin/uvicorn pedigree_app.main:app
```

### 4 — Install Playwright browser (first time only)

```bash
cd java-tests
JAVA_HOME=$(/usr/libexec/java_home -v 21) \
  mvn exec:java \
    -Dexec.mainClass=com.microsoft.playwright.CLI \
    -Dexec.args="install chromium" \
    -Dexec.classpathScope=test
```

### 5 — Run all tests

**Python (pytest)** — from the repo root, no running app required:

```bash
uv pip install -e ".[dev]"
pytest
```

On **Databricks**, clone this repo as a [Repo](https://docs.databricks.com/aws/en/repos/git-operations-with-repos), open `databricks/run_unit_tests.py` as a notebook, attach a cluster, and run all cells (see [unit testing for notebooks](https://docs.databricks.com/aws/en/notebooks/testing)).

**Java** — with the app running on port 8000:

```bash
cd java-tests
JAVA_HOME=$(/usr/libexec/java_home -v 21) mvn test
```

Expected output:

```
Tests run: 4,  Failures: 0  -- com.pedigree.data.PedigreeCsvIntegrityTest
Tests run: 19, Failures: 0  -- com.pedigree.api.PedigreeApiTest
Tests run: 11, Failures: 0  -- com.pedigree.ui.PedigreeUiTest
BUILD SUCCESS
```

### 6 — Run a single test layer

```bash
# data tests only — no running app needed
mvn test -Dgroups=data

# API tests only
mvn test -Dgroups=api

# UI tests only
mvn test -Dgroups=ui
```

Override the base URL if the app runs on a different port:

```bash
mvn test -Dbase.url=http://127.0.0.1:9000
```

## Application endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | HTML dogs table |
| GET | `/dogs/{id}` | HTML dog card (birth certificate) |
| GET | `/dogs/{id}/pedigree` | HTML pedigree view (±5 generations) |
| GET | `/api/dogs` | JSON list of all dogs |
| GET | `/api/dogs/{id}` | JSON single dog |
| GET | `/api/dogs/{id}/pedigree` | JSON ancestors + descendants, depth ≤ 5 |
| GET | `/api/dogs/{id}/pedigree-network` | JSON nodes + edges for a local tree window |
| GET | `/api/dataset` | JSON: `switching_enabled` (always true), current cookie key, `{key,label}` options |
| POST | `/api/dataset` | JSON body `{"dataset":"<registry_key>"}`; sets `pedigree_dataset` cookie; returns `{ok, dataset}` |
| POST | `/dataset` | Form field `dataset` = registry key; sets cookie and redirects (HTML navbar picker) |

Interactive API docs: `http://127.0.0.1:8000/docs`
