# Testing Strategy

Automated coverage spans three layers. All tests are in `tests/` and run with pytest.


| Layer      | File                           | Needs running app?                    |
| ---------- | ------------------------------ | ------------------------------------- |
| Data / CSV | `tests/test_data_level.py`     | No                                    |
| REST API   | `tests/test_api.py`            | No (FastAPI `TestClient`, in-process) |
| UI         | `tests/ui/test_pedigree_ui.py` | Yes + Playwright Chromium             |


## CSV path (no named dataset registry)

The app and tests load **one** file, controlled by environment variable `**PEDIGREE_CSV_PATH`**. 

**Pytest** sets `PEDIGREE_CSV_PATH` from (highest to lowest priority):

1. `--pedigree-csv /path/to/file.csv`
2. `PEDIGREE_TEST_CSV` environment variable
3. Default: `**<repo>/fixtures/csv/clean.csv`**

For a **running uvicorn** (UI tests), export the same path so the browser hits the same data:

```bash
export PEDIGREE_CSV_PATH=/abs/path/to/file.csv
uvicorn pedigree_app.main:app --port 8000

# RUN tests
uv run pytest tests/ui -m ui
```

  


## Tests per suite

### Data (`tests/test_data_level.py`)


| Test                                       | What it checks                                                                     |
| ------------------------------------------ | ---------------------------------------------------------------------------------- |
| `test_parent_graph_has_no_directed_cycles` | After `load_dogs`, sire/dam edges among loaded ids must not form a directed cycle. |


### API (`tests/test_api.py`)


| Test                            | What it checks                                                                                                          |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `test_pedigree_matches_library` | `GET /api/dogs/{id}/pedigree` matches `build_pedigree` for **min(dog id)** (same code path as the app for loaded data). |


### UI (`tests/ui/test_pedigree_ui.py`)


| Test                     | What it checks                                        |
| ------------------------ | ----------------------------------------------------- |
| `test_pedigree_e2e_flow` | Table → card → pedigree using dogs from the live API. |
|                          |                                                       |


## Expected outcomes

**Default** (`fixtures/csv/clean.csv`): all tests pass

**CSV with a parent cycle:** the **data** test fails with `Illegal cycle detected` (`tests/pedigree_parent_cycle.py`). The **API** pedigree match test does not include that check.  
cycle CSVs still load and `build_pedigree` matches the HTTP response.

## Databricks

`databricks/run_unit_tests.py` runs `pytest tests -m "not ui"`. Without overrides, pytest uses `fixtures/csv/clean.csv`. Set `PEDIGREE_TEST_CSV` (or `PEDIGREE_CSV_PATH` before pytest) to point at another file if needed.

