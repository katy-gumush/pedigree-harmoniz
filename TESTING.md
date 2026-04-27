# Testing Strategy and Error Scenario Explanations

## Overview

The assignment requires verifying a dogs pedigree system at three layers:
data integrity, API contract, and UI display.  All automated tests are written
in Java (JUnit 5) inside a single Maven module (`java-tests/`), while the
application under test is Python (FastAPI).  This keeps toolchain choices
focused: one language for tests, a different one for the server, with no
crossover of testing libraries.

---

## Layer 1: Data tests (`com.pedigree.data.PedigreeCsvIntegrityTest`)

### Goal

Validate the raw CSV file before any server is involved.  These checks catch
problems that would corrupt pedigree answers for every downstream consumer.

### Rules applied

| Rule | Why it matters |
|------|---------------|
| Required fields present (ID, Name, Breed, Sex) | A record missing any of these cannot be displayed on a card or searched. |
| IDs are unique | Duplicate IDs make parent references ambiguous—two dogs would both claim the same id, breaking every lookup. |
| Sire_ID and Dam_ID reference existing IDs | A reference to a non-existent dog silently breaks the ancestor tree: the missing node simply disappears, giving users a false "no parent" result. |
| No dog is its own parent | Self-parenting creates a trivial cycle that hangs any naïve recursive traversal. |
| No directed cycle in parent links (any length) | Following sire/dam edges from child to parent, any cycle (including a two-dog swap or a longer ring) makes the pedigree impossible; walkers use `visited` sets so the UI/API will not hang, but results are wrong. |
| Height and weight are non-negative | Sanity check; data entry errors (negative values) would show impossible measurements on dog cards. |

### Assumptions

- The baseline `Dogs Pedigree.csv` is treated as ground truth.
- Empty `Sire_ID` / `Dam_ID` cells mean "founder" (no known parent).  This is
  valid and must not be flagged as a violation.
- Separate `@Test` methods load each fixture and assert one failing rule per
  corrupted file, so the failure mode stays explicit.

---

## Layer 2: API tests (`com.pedigree.api.PedigreeApiTest`)

### Goal

Confirm that the running server exposes correctly structured JSON, consistent
with the underlying CSV, and that pedigree-specific invariants hold at the HTTP
boundary.

### Assumptions

- The app is started before this test class runs (documented in README).
- `GET/POST /api/dataset` exercises cookie-backed switching (mini fixtures and
  back to `full`) with no restart. Optional `PEDIGREE_CSV_PATH` only changes which
  file backs the `full` key; it does not disable switching.
- "Known dog" golden values are derived directly from `Dogs Pedigree.csv`:
  dog 51 (Henry) has `sire_id=1` and `dam_id=2`; dog 3 (Maggie) is a founder
  with 119+ descendants within 5 generations; dog 452 (Louie) has a 6-level
  ancestor chain, exercising the depth cap.

### Key checks

Tests call a live server (default `http://127.0.0.1:8000`, overridable via
`-Dbase.url=...`).  REST Assured uses a **10s connect** and **30s read** socket
timeout so slow or hung responses fail fast instead of blocking the suite.

- **`GET /api/dataset`** / **`POST /api/dataset`**
  - **GET** returns `switching_enabled` (**true**), `dataset` (current cookie key),
    and `options` (`key` + `label` per registry entry).
  - **POST** JSON `{"dataset":"…"}` validates the key, returns **400** for unknown
    keys, otherwise **200** with `{ok, dataset}` and `Set-Cookie: pedigree_dataset=…`.
    Follow-up **`GET /api/dogs`** with that cookie must reflect the chosen file
    (e.g. `bad_parent` → 3 dogs); selecting `full` again restores a list with **>500**
    dogs when `full` points at the baseline CSV.

- **`GET /api/dogs`**
  - **200**, `Content-Type: application/json`, body is an array with **more than
    500** dogs (baseline CSV size).
  - First element has non-null `id` and non-empty `name`, `breed`, `sex`.
  - **Field contract** on sampled rows: first, middle, and last list entries,
    plus the row whose `id` is **51**, each include `id`, `name`, `breed`, `sex`,
    `height_cm`, `weight_kg`, `sire_id`, and `dam_id`.

- **`GET /api/dogs/{id}`**
  - **Dog 51 (Henry)**: `name`, `sire_id`, and `dam_id` match the CSV (`1` and
    `2`).
  - **Dog 3 (Maggie, founder)**: `name`, `breed`, and `sex` match the CSV;
    `sire_id` and `dam_id` are JSON **null**.
  - **Unknown id** (e.g. `99999`): **404**, JSON body with `detail` exactly
    `Dog 99999 not found` (FastAPI `HTTPException` shape).
  - **Invalid path** (e.g. `/api/dogs/not-a-number`): **422**, JSON with a
    non-null `detail` (validation error).

- **`GET /api/dogs/{id}/pedigree`**
  - **200** payload has `root`, `ancestors`, and `descendants`; `root.id` equals
    the requested id.
  - **Dog 51**: ancestor list includes **both** parent ids **1** and **2**.
  - **Depth cap (5)**: for dog **452** (Louie), every ancestor `depth` ≤ 5; for
    dog **3** (Maggie), every descendant `depth` ≤ 5.
  - **No duplicate ids** in the ancestor list (452) or descendant list (3).
  - **Dog 3 (founder)**: `ancestors` is an **empty** array.
  - **Unknown id**: **404** with the same `detail` string pattern as the detail
    endpoint.

- **`GET /api/dogs/{id}/pedigree-network`** (query `ancestors=2&descendants=2`
  on dog **51**)
  - **200**; `focus_id` is **51**; non-empty `nodes` and `edges`.
  - **Focus** dog id appears among `nodes[].id`.
  - Each **`edges[]`** `parent_id` and `child_id` references an id present in
    `nodes`.
  - Every **`nodes[].generation`** lies in **−2 … +2** (matches the requested
    window).
  - **`nodes`** length stays **≤ 200** so the response cannot accidentally
    return the whole graph for this narrow window.

---

## Layer 3: UI tests (`com.pedigree.ui.PedigreeUiTest`)

### Goal

Drive a real Chromium browser through the full user flow and assert that what
the user sees in the DOM matches the expected pedigree data.

### Flow covered

1. Home page → dogs table visible, row for known dog 51 present.
2. Dog card → all six required fields visible, correct parent names shown.
3. Pedigree link on card → navigates to pedigree page.
4. Pedigree page → `data-testid="pedigree-root"` contains dog name and id;
   ancestor rows include both parent IDs; no duplicate ancestor IDs; founder
   shows no ancestor rows and the "no ancestor" fallback message.
5. Error state → navigating to a non-existent dog renders an error message
   element, no Python traceback in the page body.

### `data-testid` conventions

HTML elements that tests rely on are marked with `data-testid`:

| Attribute value | Element |
|----------------|---------|
| `dog-table` | Dogs list table |
| `dog-row-{id}` | Each `<tr>` in the list |
| `dog-link-{id}` | "View" link per row |
| `dog-card` | Dog card container |
| `dog-card-{field}` | Individual field cells (id, name, breed, sex, height, weight) |
| `dog-card-sire` / `dog-card-dam` | Parent links |
| `pedigree-link` | "View Pedigree" button on card |
| `pedigree-root` | Root dog display on pedigree page |
| `pedigree-ancestor` | Each ancestor row |
| `pedigree-descendant` | Each descendant row |
| `pedigree-no-ancestors` | Fallback message when ancestors list is empty |
| `pedigree-no-descendants` | Fallback message when descendants list is empty |
| `error-message` | Error display on 404 page |
| `dataset-select` | Navbar dropdown to switch CSV data source |

---

## Error scenario details

`clean.csv` is a **full** copy of the baseline `Dogs Pedigree.csv` (written by
`scripts/generate_corrupted_datasets.py`).  The four `corrupt_*.csv` files are
**small** (few rows each) and encode one integrity violation each so failing-rule
tests stay explicit and fast.

### `corrupt_bad_parent_id.csv` — broken parent reference

**What was changed:** Dog `3` lists `Sire_ID=9999`, which does not exist in the
file.

**How the test detects it:** `assertParentReferencesValid` scans every
`Sire_ID` and `Dam_ID` against the set of known IDs. The missing reference
causes an `AssertionError` mentioning dog `3` and `Sire_ID 9999`.

**Effect on the API/UI:** The pedigree service skips broken references silently
(to keep the app running), so the sire simply does not appear in the ancestor
tree.  The data test catches this before it reaches users.

---

### `corrupt_duplicate_id.csv` — duplicate ID

**What was changed:** Two rows share `ID=1` (`First` and `Duplicate`).

**How the test detects it:** `assertUniqueIds` counts occurrences of each ID.
The duplicate triggers an `AssertionError`:
> *"ID 1 appears 2 times"*

**Effect on the API/UI:** The Python loader uses a dict keyed by ID; the last
row overwrites the first, so `id=1` reflects only one of the two rows.  Any test
or user assuming the first row "wins" would get wrong results.

---

### `corrupt_immediate_loop.csv` — two-node parent cycle

**What was changed:** Dog `1` has `Dam_ID=2`; dog `2` has `Sire_ID=1` (minimal
mutual parent links).

**How the test detects it:** `assertNoDirectedParentCycle` walks each dog's
sire/dam links as a directed graph (child → parent) and uses a three-color DFS.
A back edge to a node still on the recursion stack fails the rule with a message
such as:
> *"Dog 1 reaches dog 2 again on the same ancestor walk (cycle)"* (wording may vary by start node)

**Effect on the API/UI:** The BFS pedigree walker guards against cycles with a
`visited` set, so it will not loop infinitely.  However, the reported ancestor
and descendant trees for dogs in the cycle will be misleading—the cycle is silently
truncated.  Without the data-level check users could believe the trees are
correct.

---

### `corrupt_long_cycle.csv` — three-node cycle (not a mutual two-dog swap)

**What was changed:** Dogs `1`, `2`, and `3` form a sire-only ring:
`1→2→3→1` via `Sire_ID`.

**How the test detects it:** The same `assertNoDirectedParentCycle` rule as
above. A naïve "immediate" A↔B check would not necessarily flag this pattern,
because no pair is each other's *direct* parent at the same time.

**Effect on the API/UI:** Same as the two-node loop: traversal stays finite, but
lineage is wrong without catching the cycle in data tests.

---

## UI data source

The navbar **Data source** control (`data-testid="dataset-select"`) posts to
`/dataset`, sets a cookie, and reloads so the HTML UI and JSON API both use the
selected registry entry. Use **`POST /api/dataset`** for the same switch without a
form. Optional `PEDIGREE_CSV_PATH` overrides which file backs the **`full`** key
only (e.g. CI path to the baseline CSV); it does not hide the picker or block switching.
