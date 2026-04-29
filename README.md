# Pedigree Explorer

A small web application that exposes a dogs pedigree dataset as a REST API and HTML UI, with automated tests in **Python only** (data, API, UI). For **how tests are organized, how corrupt data is handled, and how to talk about it in an interview**, see [TESTING.md](TESTING.md).

## Project structure

```
pedigree/
  Dogs Pedigree.csv              baseline dataset (~581 dogs)
  fixtures/csv/                  committed: clean copy, corrupt variants, E2E CSVs
  pyproject.toml                 Python app build definition
  uv.lock                        dependency lockfile (uv)
  src/pedigree_app/
    load_csv.py                  CSV → typed Dog records
    pedigree.py                  BFS ancestor/descendant traversal, depth ≤ 5
    datasets.py                  active CSV path + dataset options (API/UI switcher)
    main.py                      FastAPI app (REST + Jinja2 UI)
    templates/                   HTML pages with data-testid attributes
    static/                      CSS + pedigree tree JS
  tests/
    test_api.py, test_data_level.py  pytest: API + data (parent-graph cycle check)
    ui/test_pedigree_ui.py       Playwright UI tests (browser + running app)
    conftest.py                  CSV path → PEDIGREE_CSV_PATH, TestClient, base_url
  databricks/
    run_unit_tests.py            Notebook: pytest API + data only (no Playwright)
  TESTING.md                     full testing + interview study guide
```

## Requirements


| Item                    | Notes                                                                                                                            |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **Python**              | 3.11+ (see `pyproject.toml`)                                                                                                     |
| **uv** (recommended)    | Installs dependencies and runs tools: `uv venv`, `uv pip install`, `uv run`                                                      |
| **App package**         | `uv pip install -e .` — FastAPI, Uvicorn, Jinja2, etc.                                                                           |
| **Dev / test tools**    | `uv pip install -e ".[dev]"` — `pytest`, `httpx` (API tests), `pytest-playwright`, `playwright` (UI tests)                       |
| **Playwright browsers** | Only for **UI** tests: `uv run playwright install chromium` (run once per venv; re-run after upgrading the `playwright` package) |


If `python3 -m pip` fails on macOS with `pyexpat` / `_XML_SetAllocTrackerActivationThreshold`, use `**uv pip`** or reinstall Homebrew Python.

## Install (one-time)

From the repository root:

```bash
uv venv .venv
source .venv/bin/activate          # optional; or use `uv run` for every command
uv pip install -e .
uv pip install -e ".[dev]"
```

## Run the server

The app must be a **Python package** on `PYTHONPATH` (the `src` layout). Use either:

```bash
# from repo root — development (auto-reload on code changes)
PYTHONPATH=src uv run uvicorn pedigree_app.main:app --reload --host 127.0.0.1 --port 8000
```

or, if you prefer `cd` into `src` (not required when using `PYTHONPATH=src`):

```bash
cd src && uv run uvicorn pedigree_app.main:app --reload
```

- **URL:** [http://127.0.0.1:8000](http://127.0.0.1:8000) (default Uvicorn port **8000**).
- **Optional:** set `PEDIGREE_CSV_PATH` to a file **Data source** 

## Run tests

Use `**uv run pytest ...`** so the project venv is used (avoids `pytest: command not found` if the venv is not activated).


| What you want                        | Server running? | Command                                     |
| ------------------------------------ | --------------- | ------------------------------------------- |
| **API + Data** (default; no browser) | **No**          | `uv run pytest`                             |
| **API tests only**                   | No              | `uv run pytest tests/test_api.py -v`        |
| **Data tests only**                  | No              | `uv run pytest tests/test_data_level.py -v` |
| **UI (Playwright)**                  | **Yes**         | See below                                   |


**UI tests** (Chromium + app on **8000** unless you override):

1. One-time (or after upgrading Playwright): `uv run playwright install chromium`
2. Start the server in one terminal: `PYTHONPATH=src uv run uvicorn pedigree_app.main:app --port 8000`
3. In another terminal: `uv run pytest tests/ui -v`
  - If the app uses another host/port: `PEDIGREE_UI_BASE_URL=http://127.0.0.1:PORT uv run pytest tests/ui -v`

**All automated tests in one go (API + Data + UI):** start the server, install Chromium, then:

```bash
uv run pytest tests/test_api.py tests/test_data_level.py tests/ui -v
```

Note: plain `uv run pytest` (no paths) does **not** collect `tests/ui/` by design; pass `tests/ui` explicitly to include Playwright tests.

## Databricks

Clone this repo as a [Databricks Repo](https://docs.databricks.com/aws/en/repos/git-operations-with-repos), open `**databricks/run_unit_tests.py`**, attach a cluster, run all cells. Install dependencies there (e.g. `**%pip install pytest httpx`** and `**%pip install -e .**` after changing to the repo root). That notebook runs **API + Data** tests only — not Playwright/UI.

## Application endpoints


| Method | Path                              | Description        |
| ------ | --------------------------------- | ------------------ |
| GET    | `/`                               | HTML dogs table    |
| GET    | `/dogs/{id}`                      | HTML dog card      |
| GET    | `/dogs/{id}/pedigree`             | HTML pedigree view |
| GET    | `/api/dogs`                       | JSON list          |
| GET    | `/api/dogs/{id}`                  | JSON dog           |
| GET    | `/api/dogs/{id}/pedigree`         | JSON pedigree      |
| GET    | `/api/dogs/{id}/pedigree-network` | JSON nodes + edges |


Interactive API docs: **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**
