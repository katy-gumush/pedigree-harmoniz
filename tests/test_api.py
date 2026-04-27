"""API Level tests (testCases/API Level.html). HTTP contract via FastAPI TestClient.

Mapped IDs: A01–A22 (A23 performance skipped here). UI routes are not exercised.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pedigree_app.datasets import COOKIE_NAME
from pedigree_app.load_csv import load_dogs
from pedigree_app.main import _dog_dict
from pedigree_app.pedigree import MAX_GENERATIONS, build_pedigree, build_pedigree_network

from tests.dataset_validation import fixtures_dir

_CLEAN_DOG_IDS_WITH_BOTH_PARENTS = 51  # Henry: sire 1, dam 2 in clean.csv
_FOUNDER_ID = 1
_CLEAN_NET_FOCUS = 114  # Roxy Mixed — has ancestry and descendants in clean subset

DOG_FIELDS = frozenset(
    {"id", "name", "breed", "sex", "height_cm", "weight_kg", "sire_id", "dam_id"}
)


def test_a01_get_dogs_list_ok_nonempty(client_clean: TestClient) -> None:
    r = client_clean.get("/api/dogs")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_a02_dogs_list_schema_sampled_rows(client_clean: TestClient) -> None:
    r = client_clean.get("/api/dogs")
    assert r.status_code == 200
    rows = r.json()
    for dog in rows[:: max(1, len(rows) // 10)]:
        assert DOG_FIELDS <= set(dog.keys())
        assert isinstance(dog["id"], int)


def test_a03_get_dog_by_id_matches_csv(client_clean: TestClient) -> None:
    csv_path = fixtures_dir() / "clean.csv"
    dogs = load_dogs(csv_path)
    did = _CLEAN_DOG_IDS_WITH_BOTH_PARENTS
    r = client_clean.get(f"/api/dogs/{did}")
    assert r.status_code == 200
    body = r.json()
    expected = _dog_dict(dogs[did])
    assert body == expected


def test_a04_unknown_dog_404(client_clean: TestClient) -> None:
    r = client_clean.get("/api/dogs/99999")
    assert r.status_code == 404
    payload = r.json()
    assert "detail" in payload


def test_a05_pedigree_response_shape(client_clean: TestClient) -> None:
    did = _CLEAN_DOG_IDS_WITH_BOTH_PARENTS
    r = client_clean.get(f"/api/dogs/{did}/pedigree")
    assert r.status_code == 200
    payload = r.json()
    assert set(payload.keys()) >= {"root", "ancestors", "descendants"}
    for key in ("root",):
        assert DOG_FIELDS <= set(payload[key].keys())
    for group in ("ancestors", "descendants"):
        for node in payload[group]:
            assert "depth" in node
            assert DOG_FIELDS <= set(node.keys())


def test_a06_pedigree_root_matches_requested_id(client_clean: TestClient) -> None:
    did = 52
    r = client_clean.get(f"/api/dogs/{did}/pedigree")
    assert r.status_code == 200
    assert r.json()["root"]["id"] == did


def test_a07_immediate_ancestors_match_csv(client_clean: TestClient) -> None:
    csv_path = fixtures_dir() / "clean.csv"
    dogs = load_dogs(csv_path)
    did = _CLEAN_DOG_IDS_WITH_BOTH_PARENTS
    d = dogs[did]
    r = client_clean.get(f"/api/dogs/{did}/pedigree")
    assert r.status_code == 200
    anc_by_id = {x["id"]: x for x in r.json()["ancestors"]}
    if d.sire_id is not None:
        assert d.sire_id in anc_by_id
    if d.dam_id is not None:
        assert d.dam_id in anc_by_id


def test_a08_founder_has_empty_ancestors(client_clean: TestClient) -> None:
    r = client_clean.get(f"/api/dogs/{_FOUNDER_ID}/pedigree")
    assert r.status_code == 200
    assert r.json()["ancestors"] == []


def test_a09_descendants_for_founder_when_present(client_clean: TestClient) -> None:
    r = client_clean.get(f"/api/dogs/{_FOUNDER_ID}/pedigree")
    assert r.status_code == 200
    desc = r.json()["descendants"]
    assert isinstance(desc, list)
    assert len(desc) >= 1


def test_a10_a11_ancestor_descendant_depth_at_most_five(client_clean: TestClient) -> None:
    did = _CLEAN_NET_FOCUS
    r = client_clean.get(f"/api/dogs/{did}/pedigree")
    assert r.status_code == 200
    payload = r.json()
    for n in payload["ancestors"]:
        assert n["depth"] <= MAX_GENERATIONS
    for n in payload["descendants"]:
        assert n["depth"] <= MAX_GENERATIONS


def test_a12_a13_no_duplicate_ancestor_or_descendant_ids(client_clean: TestClient) -> None:
    did = _CLEAN_NET_FOCUS
    r = client_clean.get(f"/api/dogs/{did}/pedigree")
    assert r.status_code == 200
    payload = r.json()
    anc_ids = [n["id"] for n in payload["ancestors"]]
    desc_ids = [n["id"] for n in payload["descendants"]]
    assert len(anc_ids) == len(set(anc_ids))
    assert len(desc_ids) == len(set(desc_ids))


def test_a14_api_pedigree_matches_build_pedigree_logic(client_clean: TestClient) -> None:
    csv_path = fixtures_dir() / "clean.csv"
    dogs = load_dogs(csv_path)
    did = _CLEAN_NET_FOCUS
    expected = build_pedigree(did, dogs)
    r = client_clean.get(f"/api/dogs/{did}/pedigree")
    assert r.status_code == 200
    payload = r.json()
    assert payload["root"]["id"] == expected.root.id
    assert {n["id"] for n in payload["ancestors"]} == expected.ancestor_ids
    assert {n["id"] for n in payload["descendants"]} == expected.descendant_ids


def test_a15_bad_parent_dataset_partial_pedigree(api_client: TestClient) -> None:
    api_client.cookies.set(COOKIE_NAME, "bad_parent")
    # Dog 3 lists missing sire 9999 — traversal skips missing parent
    r = api_client.get("/api/dogs/3/pedigree")
    assert r.status_code == 200
    payload = r.json()
    assert payload["root"]["id"] == 3
    ids_anc = {n["id"] for n in payload["ancestors"]}
    assert 9999 not in ids_anc


def test_a16_duplicate_id_dataset_loads_last_row_wins(api_client: TestClient) -> None:
    api_client.cookies.set(COOKIE_NAME, "duplicate_id")
    r = api_client.get("/api/dogs/1")
    assert r.status_code == 200
    assert r.json()["name"] == "Duplicate"


def test_a17_cycle_dataset_pedigree_returns_bounded(api_client: TestClient) -> None:
    for key in ("immediate_loop", "long_cycle"):
        api_client.cookies.set(COOKIE_NAME, key)
        r = api_client.get("/api/dogs/1/pedigree")
        assert r.status_code == 200
        body = r.json()
        assert "root" in body
        for n in body["ancestors"] + body["descendants"]:
            assert n["depth"] <= MAX_GENERATIONS


def test_a18_invalid_path_dog_id_validation_error(api_client: TestClient) -> None:
    r = api_client.get("/api/dogs/not-an-int")
    assert r.status_code == 422


def test_a19_dataset_switching_endpoint(api_client: TestClient) -> None:
    post = api_client.post("/api/dataset", json={"dataset": "clean"})
    assert post.status_code == 200
    assert post.json().get("dataset") == "clean"
    r = api_client.get("/api/dataset")
    assert r.status_code == 200
    assert r.json().get("dataset") == "clean"


def test_a20_detail_matches_loaded_csv_no_drift(client_clean: TestClient) -> None:
    csv_path = fixtures_dir() / "clean.csv"
    dogs = load_dogs(csv_path)
    for did in (1, 51, 114):
        api = client_clean.get(f"/api/dogs/{did}").json()
        assert api == _dog_dict(dogs[did])


def test_a21_pedigree_network_edges_reference_existing_nodes(client_clean: TestClient) -> None:
    did = _CLEAN_NET_FOCUS
    r = client_clean.get(f"/api/dogs/{did}/pedigree-network")
    assert r.status_code == 200
    net = r.json()
    node_ids = {n["id"] for n in net["nodes"]}
    for e in net["edges"]:
        assert e["parent_id"] in node_ids
        assert e["child_id"] in node_ids


def test_a22_error_responses_have_detail_structure(client_clean: TestClient) -> None:
    r = client_clean.get("/api/dogs/99999")
    assert r.status_code == 404
    assert isinstance(r.json().get("detail"), str)

    bad = client_clean.post("/api/dataset", json={"dataset": "nonexistent-key"})
    assert bad.status_code == 400
    assert isinstance(bad.json().get("detail"), str)


@pytest.mark.skip(reason="A23: performance — optional; run manually with large CSV")
def test_a23_performance_placeholder() -> None:
    assert False


def test_network_matches_build_pedigree_network(client_clean: TestClient) -> None:
    """Extra consistency check for /pedigree-network vs library."""
    csv_path = fixtures_dir() / "clean.csv"
    dogs = load_dogs(csv_path)
    did = _CLEAN_NET_FOCUS
    expected = build_pedigree_network(did, dogs, MAX_GENERATIONS, MAX_GENERATIONS)
    r = client_clean.get(f"/api/dogs/{did}/pedigree-network")
    assert r.status_code == 200
    net = r.json()
    assert net["focus_id"] == expected.focus_id
    assert {n["id"] for n in net["nodes"]} == {n.id for n in expected.nodes}
    edges = {(e["parent_id"], e["child_id"]) for e in net["edges"]}
    assert edges == {(e.parent_id, e.child_id) for e in expected.edges}
