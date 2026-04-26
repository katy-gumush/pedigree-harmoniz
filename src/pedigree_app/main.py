"""Pedigree Explorer – FastAPI application."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pedigree_app.load_csv import Dog, load_dogs
from pedigree_app.pedigree import (
    MAX_GENERATIONS,
    PedigreeNetwork,
    PedigreeNode,
    build_pedigree,
    build_pedigree_network,
    initial_tree_depths,
)

# ---------------------------------------------------------------------------
# Startup – load dataset once at import time so all handlers share it.
# Override via PEDIGREE_CSV_PATH environment variable for corrupted-data tests.
# ---------------------------------------------------------------------------

_DEFAULT_CSV = Path(__file__).parent.parent.parent / "Dogs Pedigree.csv"
_CSV_PATH = Path(os.environ.get("PEDIGREE_CSV_PATH", _DEFAULT_CSV))

DOGS: dict[int, Dog] = load_dogs(_CSV_PATH)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

_THIS_DIR = Path(__file__).parent
app = FastAPI(title="Pedigree Explorer")
app.mount("/static", StaticFiles(directory=_THIS_DIR / "static"), name="static")
templates = Jinja2Templates(directory=_THIS_DIR / "templates")

# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------


@app.get("/api/dogs", tags=["api"])
def list_dogs():
    """Return all dogs as a list of plain dicts."""
    return [_dog_dict(d) for d in sorted(DOGS.values(), key=lambda d: d.id)]


@app.get("/api/dogs/{dog_id}", tags=["api"])
def get_dog(dog_id: int):
    """Return a single dog by id."""
    dog = DOGS.get(dog_id)
    if dog is None:
        raise HTTPException(status_code=404, detail=f"Dog {dog_id} not found")
    return _dog_dict(dog)


@app.get("/api/dogs/{dog_id}/pedigree-network", tags=["api"])
def get_pedigree_network_api(
    dog_id: int,
    ancestors: int = MAX_GENERATIONS,
    descendants: int = MAX_GENERATIONS,
):
    """Nodes and parent→child edges for a subgraph around *dog_id*.

    *ancestors* / *descendants* cap how many generations up or down to include
    (defaults match the full pedigree view).
    """
    if dog_id not in DOGS:
        raise HTTPException(status_code=404, detail=f"Dog {dog_id} not found")
    anc = max(0, min(ancestors, MAX_GENERATIONS))
    desc = max(0, min(descendants, MAX_GENERATIONS))
    net = build_pedigree_network(dog_id, DOGS, anc, desc)
    return _pedigree_network_dict(net)


@app.get("/api/dogs/{dog_id}/pedigree", tags=["api"])
def get_pedigree(dog_id: int):
    """Return ancestors and descendants up to 5 generations.

    Nodes are deduplicated: each dog_id appears at most once across the full
    ancestor list and at most once across the full descendant list.
    """
    if dog_id not in DOGS:
        raise HTTPException(status_code=404, detail=f"Dog {dog_id} not found")
    result = build_pedigree(dog_id, DOGS)
    return {
        "root": _dog_dict(result.root),
        "ancestors": [_node_dict(n) for n in result.ancestors],
        "descendants": [_node_dict(n) for n in result.descendants],
    }


# ---------------------------------------------------------------------------
# HTML UI
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
def dogs_list(request: Request):
    dogs = sorted(DOGS.values(), key=lambda d: d.id)
    return templates.TemplateResponse(request, "dogs_list.html", {"dogs": dogs})


@app.get("/dogs/{dog_id}", response_class=HTMLResponse)
def dog_card(request: Request, dog_id: int):
    dog = DOGS.get(dog_id)
    if dog is None:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"message": f"Dog with id {dog_id} was not found."},
            status_code=404,
        )
    sire = DOGS.get(dog.sire_id) if dog.sire_id else None
    dam = DOGS.get(dog.dam_id) if dog.dam_id else None
    return templates.TemplateResponse(
        request, "dog_card.html", {"dog": dog, "sire": sire, "dam": dam}
    )


@app.get("/dogs/{dog_id}/pedigree", response_class=HTMLResponse)
def dog_pedigree(request: Request, dog_id: int):
    dog = DOGS.get(dog_id)
    if dog is None:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"message": f"Dog with id {dog_id} was not found."},
            status_code=404,
        )
    max_anc, max_desc = initial_tree_depths(dog_id, DOGS)
    result = build_pedigree(
        dog_id, DOGS, max_ancestors=max_anc, max_descendants=max_desc
    )
    net = build_pedigree_network(dog_id, DOGS, max_anc, max_desc)
    anc_depth = {n.dog.id: n.depth for n in result.ancestors}
    desc_depth = {n.dog.id: n.depth for n in result.descendants}
    pedigree_graph = _pedigree_network_dict(net, anc_depth, desc_depth)
    pedigree_graph["page_root_id"] = dog_id
    pedigree_graph["initial_max_ancestors"] = max_anc
    pedigree_graph["initial_max_descendants"] = max_desc
    return templates.TemplateResponse(
        request,
        "dog_pedigree.html",
        {
            "dog": dog,
            "ancestors": result.ancestors,
            "descendants": result.descendants,
            "max_gen_anc": max_anc,
            "max_gen_desc": max_desc,
            "full_pedigree_depth": MAX_GENERATIONS,
            "pedigree_graph": pedigree_graph,
        },
    )


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
