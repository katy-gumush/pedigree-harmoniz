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
    generate_corrupted_datasets.py   produces test fixtures
  java-tests/
    pom.xml                      Maven project (JUnit 5 + Commons CSV + REST Assured + Playwright)
    src/test/java/com/pedigree/
      data/PedigreeCsvIntegrityTest.java    data-layer tests
      api/PedigreeApiTest.java              API-layer tests
      ui/PedigreeUiTest.java                UI-layer Playwright tests
    src/test/resources/fixtures/   clean + corrupted CSV fixtures (generated)
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

This writes `clean.csv` plus four corrupted variants into `java-tests/src/test/resources/fixtures/`.

### 3 — Start the application

```bash
PYTHONPATH=src .venv/bin/uvicorn pedigree_app.main:app --reload
```

The app listens on `http://127.0.0.1:8000` by default.

To run against a corrupted dataset (for manual inspection or API error scenario tests):

```bash
PEDIGREE_CSV_PATH=/path/to/corrupt_bad_parent_id.csv \
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

With the app running on port 8000:

```bash
cd java-tests
JAVA_HOME=$(/usr/libexec/java_home -v 21) mvn test
```

Expected output:

```
Tests run: 4,  Failures: 0  -- com.pedigree.data.PedigreeCsvIntegrityTest
Tests run: 15, Failures: 0  -- com.pedigree.api.PedigreeApiTest
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

Interactive API docs: `http://127.0.0.1:8000/docs`
