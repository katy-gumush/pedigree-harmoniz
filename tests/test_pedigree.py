"""Unit tests for pedigree_app.pedigree (BFS pedigree and network)."""

from __future__ import annotations

from pedigree_app.load_csv import Dog
from pedigree_app.pedigree import (
    MAX_GENERATIONS,
    MANY_DIRECT_CHILDREN,
    build_pedigree,
    build_pedigree_network,
    initial_tree_depths,
)


def _dog(
    dog_id: int,
    *,
    sire_id: int | None = None,
    dam_id: int | None = None,
) -> Dog:
    return Dog(
        id=dog_id,
        name=f"dog{dog_id}",
        breed="B",
        sex="M",
        height_cm=1.0,
        weight_kg=1.0,
        sire_id=sire_id,
        dam_id=dam_id,
    )


def test_build_pedigree_ancestors_chain() -> None:
    # 1 <- 2 <- 3 (sire chain)
    dogs = {1: _dog(1), 2: _dog(2, sire_id=1), 3: _dog(3, sire_id=2)}
    r = build_pedigree(3, dogs)
    assert r.root.id == 3
    assert {n.dog.id for n in r.ancestors} == {1, 2}
    assert r.ancestor_ids == {1, 2}
    depths = {n.dog.id: n.depth for n in r.ancestors}
    assert depths[2] == 1
    assert depths[1] == 2


def test_build_pedigree_descendants() -> None:
    dogs = {1: _dog(1), 2: _dog(2, sire_id=1), 3: _dog(3, sire_id=1)}
    r = build_pedigree(1, dogs)
    assert {n.dog.id for n in r.descendants} == {2, 3}
    assert r.descendant_ids == {2, 3}


def test_build_pedigree_max_depth_clamp() -> None:
    dogs = {1: _dog(1), 2: _dog(2, sire_id=1), 3: _dog(3, sire_id=2), 4: _dog(4, sire_id=3)}
    r = build_pedigree(4, dogs, max_ancestors=1, max_descendants=0)
    assert {n.dog.id for n in r.ancestors} == {3}
    assert r.descendants == []


def test_build_pedigree_skips_missing_parent_id() -> None:
    dogs = {2: _dog(2, sire_id=999)}
    r = build_pedigree(2, dogs)
    assert r.ancestors == []


def test_initial_tree_depths_no_parents_no_children() -> None:
    dogs = {1: _dog(1)}
    assert initial_tree_depths(1, dogs) == (2, 2)


def test_initial_tree_depths_many_direct_children_caps_descendants() -> None:
    # root 1 with MANY_DIRECT_CHILDREN + 1 direct children as sire only
    children = {1: _dog(1)}
    for i in range(2, 2 + MANY_DIRECT_CHILDREN + 1):
        children[i] = _dog(i, sire_id=1)
    assert initial_tree_depths(1, children) == (MAX_GENERATIONS, 2)


def test_initial_tree_depths_full_when_moderate_children_and_parents() -> None:
    dogs = {
        1: _dog(1),
        2: _dog(2, sire_id=1),
        3: _dog(3, sire_id=1),
    }
    assert initial_tree_depths(1, dogs) == (MAX_GENERATIONS, MAX_GENERATIONS)


def test_build_pedigree_network_unknown_focus() -> None:
    dogs = {1: _dog(1)}
    net = build_pedigree_network(99, dogs, max_ancestor_depth=2, max_descendant_depth=2)
    assert net.nodes == []
    assert net.edges == []


def test_build_pedigree_network_edges() -> None:
    dogs = {1: _dog(1), 2: _dog(2, sire_id=1), 3: _dog(3, dam_id=2)}
    net = build_pedigree_network(3, dogs, max_ancestor_depth=5, max_descendant_depth=5)
    ids = {n.id for n in net.nodes}
    assert ids == {1, 2, 3}
    edge_set = {(e.parent_id, e.child_id) for e in net.edges}
    assert (1, 2) in edge_set
    assert (2, 3) in edge_set
