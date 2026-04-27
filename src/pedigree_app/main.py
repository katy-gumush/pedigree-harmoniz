"""Pedigree Explorer – FastAPI application."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pedigree_app.datasets import (
    COOKIE_NAME,
    DATASET_OPTIONS,
    apply_pedigree_dataset_cookie,
    dataset_keys,
    dogs_for_cookie,
    selected_key_from_cookie,
)
from pedigree_app.load_csv import Dog
from pydantic import BaseModel, Field
from pedigree_app.pedigree import (
    MAX_GENERATIONS,
    PedigreeNetwork,
    PedigreeNode,
    build_pedigree,
    build_pedigree_network,
    initial_tree_depths,
)

# ---------------------------------------------------------------------------
# PEDIGREE_CSV_PATH (optional): overrides which file backs registry key "full"
# only; see pedigree_app.datasets. Switching datasets never requires a restart.
# ---------------------------------------------------------------------------

_THIS_DIR = Path(__file__).parent

app = FastAPI(title="Pedigree Explorer")
app.mount("/static", StaticFiles(directory=_THIS_DIR / "static"), name="static")
templates = Jinja2Templates(directory=_THIS_DIR / "templates")


def _dogs(request: Request) -> dict[int, Dog]:
    return dogs_for_cookie(request.cookies.get(COOKIE_NAME))


def _nav(request: Request) -> dict:
    return {
        "dataset_options": DATASET_OPTIONS,
        "current_dataset": selected_key_from_cookie(request.cookies.get(COOKIE_NAME)),
        "dataset_picker_enabled": True,
    }


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------


@app.get("/api/dogs", tags=["api"])
def list_dogs(request: Request):
    """Return all dogs as a list of plain dicts."""
    dogs = _dogs(request)
    return [_dog_dict(d) for d in sorted(dogs.values(), key=lambda d: d.id)]


@app.get("/api/dogs/{dog_id}", tags=["api"])
def get_dog(request: Request, dog_id: int):
    """Return a single dog by id."""
    dogs = _dogs(request)
    dog = dogs.get(dog_id)
    if dog is None:
        raise HTTPException(status_code=404, detail=f"Dog {dog_id} not found")
    return _dog_dict(dog)


@app.get("/api/dogs/{dog_id}/pedigree-network", tags=["api"])
def get_pedigree_network_api(
    request: Request,
    dog_id: int,
    ancestors: int = MAX_GENERATIONS,
    descendants: int = MAX_GENERATIONS,
):
    """Nodes and parent→child edges for a subgraph around *dog_id*.

    *ancestors* / *descendants* cap how many generations up or down to include
    (defaults match the full pedigree view).
    """
    dogs = _dogs(request)
    if dog_id not in dogs:
        raise HTTPException(status_code=404, detail=f"Dog {dog_id} not found")
    anc = max(0, min(ancestors, MAX_GENERATIONS))
    desc = max(0, min(descendants, MAX_GENERATIONS))
    net = build_pedigree_network(dog_id, dogs, anc, desc)
    return _pedigree_network_dict(net)


@app.get("/api/dogs/{dog_id}/pedigree", tags=["api"])
def get_pedigree(request: Request, dog_id: int):
    """Return ancestors and descendants up to 5 generations.

    Nodes are deduplicated: each dog_id appears at most once across the full
    ancestor list and at most once across the full descendant list.
    """
    dogs = _dogs(request)
    if dog_id not in dogs:
        raise HTTPException(status_code=404, detail=f"Dog {dog_id} not found")
    result = build_pedigree(dog_id, dogs)
    return {
        "root": _dog_dict(result.root),
        "ancestors": [_node_dict(n) for n in result.ancestors],
        "descendants": [_node_dict(n) for n in result.descendants],
    }


class DatasetSelectBody(BaseModel):
    """JSON body for POST /api/dataset."""

    dataset: str = Field(..., min_length=1, max_length=128)


@app.get("/api/dataset", tags=["api"])
def get_dataset_setting(request: Request):
    """Describe the active data source and available options (cookie-backed)."""
    return {
        "switching_enabled": True,
        "dataset": selected_key_from_cookie(request.cookies.get(COOKIE_NAME)),
        "options": [{"key": o.key, "label": o.label} for o in DATASET_OPTIONS],
    }


@app.post("/api/dataset", tags=["api"])
def post_dataset_api(body: DatasetSelectBody):
    """Select a registered CSV; sets ``pedigree_dataset`` cookie for later API/HTML requests."""
    key = body.dataset.strip()
    if key not in dataset_keys():
        raise HTTPException(status_code=400, detail="Unknown dataset")
    response = JSONResponse({"ok": True, "dataset": key})
    apply_pedigree_dataset_cookie(response, key)
    return response


# ---------------------------------------------------------------------------
# Dataset switcher (HTML form; same cookie as POST /api/dataset)
# ---------------------------------------------------------------------------


@app.post("/dataset", response_class=RedirectResponse)
async def set_dataset(request: Request):
    """Set the pedigree_dataset cookie and redirect back (Referer or home)."""
    form = await request.form()
    raw = form.get("dataset")
    key = str(raw).strip() if raw is not None else ""
    if key not in dataset_keys():
        raise HTTPException(status_code=400, detail="Unknown dataset")
    base = str(request.base_url).rstrip("/")
    referer = request.headers.get("referer") or ""
    dest = referer if referer.startswith(base) else "/"
    response = RedirectResponse(url=dest, status_code=303)
    apply_pedigree_dataset_cookie(response, key)
    return response


# ---------------------------------------------------------------------------
# HTML UI
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
def dogs_list(request: Request):
    dogs = sorted(_dogs(request).values(), key=lambda d: d.id)
    ctx = {"dogs": dogs, **_nav(request)}
    return templates.TemplateResponse(request, "dogs_list.html", ctx)


@app.get("/dogs/{dog_id}", response_class=HTMLResponse)
def dog_card(request: Request, dog_id: int):
    dogs = _dogs(request)
    dog = dogs.get(dog_id)
    if dog is None:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"message": f"Dog with id {dog_id} was not found.", **_nav(request)},
            status_code=404,
        )
    sire = dogs.get(dog.sire_id) if dog.sire_id else None
    dam = dogs.get(dog.dam_id) if dog.dam_id else None
    ctx = {"dog": dog, "sire": sire, "dam": dam, **_nav(request)}
    return templates.TemplateResponse(request, "dog_card.html", ctx)


@app.get("/dogs/{dog_id}/pedigree", response_class=HTMLResponse)
def dog_pedigree(request: Request, dog_id: int):
    dogs = _dogs(request)
    dog = dogs.get(dog_id)
    if dog is None:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"message": f"Dog with id {dog_id} was not found.", **_nav(request)},
            status_code=404,
        )
    max_anc, max_desc = initial_tree_depths(dog_id, dogs)
    result = build_pedigree(
        dog_id, dogs, max_ancestors=max_anc, max_descendants=max_desc
    )
    net = build_pedigree_network(dog_id, dogs, max_anc, max_desc)
    anc_depth = {n.dog.id: n.depth for n in result.ancestors}
    desc_depth = {n.dog.id: n.depth for n in result.descendants}
    pedigree_graph = _pedigree_network_dict(net, anc_depth, desc_depth)
    pedigree_graph["page_root_id"] = dog_id
    pedigree_graph["initial_max_ancestors"] = max_anc
    pedigree_graph["initial_max_descendants"] = max_desc
    ctx = {
        "dog": dog,
        "ancestors": result.ancestors,
        "descendants": result.descendants,
        "max_gen_anc": max_anc,
        "max_gen_desc": max_desc,
        "full_pedigree_depth": MAX_GENERATIONS,
        "pedigree_graph": pedigree_graph,
        **_nav(request),
    }
    return templates.TemplateResponse(request, "dog_pedigree.html", ctx)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dog_dict(d: Dog) -> dict:
    return {
        "id": d.id,
        "name": d.name,
        "breed": d.breed,
        "sex": d.sex,
        "height_cm": d.height_cm,
        "weight_kg": d.weight_kg,
        "sire_id": d.sire_id,
        "dam_id": d.dam_id,
    }


def _node_dict(n: PedigreeNode) -> dict:
    return {"depth": n.depth, **_dog_dict(n.dog)}


def _pedigree_network_dict(
    net: PedigreeNetwork,
    ancestor_list_depth: dict[int, int] | None = None,
    descendant_list_depth: dict[int, int] | None = None,
) -> dict:
    ancestor_list_depth = ancestor_list_depth or {}
    descendant_list_depth = descendant_list_depth or {}
    nodes_out: list[dict] = []
    for n in net.nodes:
        d: dict = {
            "id": n.id,
            "name": n.name,
            "breed": n.breed,
            "sex": n.sex,
            "generation": n.generation,
        }
        if n.id in ancestor_list_depth:
            d["ancestor_list_depth"] = ancestor_list_depth[n.id]
        if n.id in descendant_list_depth:
            d["descendant_list_depth"] = descendant_list_depth[n.id]
        nodes_out.append(d)
    return {
        "focus_id": net.focus_id,
        "nodes": nodes_out,
        "edges": [
            {"parent_id": e.parent_id, "child_id": e.child_id} for e in net.edges
        ],
    }
