"""Pedigree traversal: ancestors and descendants up to MAX_GENERATIONS deep."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from pedigree_app.load_csv import Dog

MAX_GENERATIONS = 5

# Initial HTML tree: cap descendant depth when a dog has this many direct offspring.
MANY_DIRECT_CHILDREN = 5


@dataclass
class PedigreeNode:
    dog: Dog
    depth: int
    sire: Optional["PedigreeNode"] = field(default=None, repr=False)
    dam: Optional["PedigreeNode"] = field(default=None, repr=False)


@dataclass
class PedigreeResult:
    root: Dog
    ancestors: list[PedigreeNode]
    descendants: list[PedigreeNode]
    # ids seen in ancestor walk (flat, deduplicated)
    ancestor_ids: set[int] = field(default_factory=set)
    descendant_ids: set[int] = field(default_factory=set)


def build_pedigree(
    root_id: int,
    dogs: dict[int, Dog],
    *,
    max_ancestors: int | None = None,
    max_descendants: int | None = None,
) -> PedigreeResult:
    """Walk ancestors and descendants of *root_id*.

    Depth limits default to MAX_GENERATIONS.  Both walks are BFS; visited sets
    prevent duplicate nodes when a common ancestor appears through multiple lineages.
    """
    root = dogs[root_id]
    ma = MAX_GENERATIONS if max_ancestors is None else max(0, min(max_ancestors, MAX_GENERATIONS))
    md = MAX_GENERATIONS if max_descendants is None else max(0, min(max_descendants, MAX_GENERATIONS))

    ancestors = _walk_ancestors(root_id, dogs, ma)
    descendants = _walk_descendants(root_id, dogs, md)

    return PedigreeResult(
        root=root,
        ancestors=ancestors,
        ancestor_ids={n.dog.id for n in ancestors},
        descendants=descendants,
        descendant_ids={n.dog.id for n in descendants},
    )


def initial_tree_depths(dog_id: int, dogs: dict[int, Dog]) -> tuple[int, int]:
    """Return (max_ancestors, max_descendants) for the pedigree HTML tree.

    * No recorded parents **and** no direct offspring → use a small ±2 window.
    * More than MANY_DIRECT_CHILDREN direct offspring → keep full ancestors but
      cap descendants at 2 generations so the first row is not overwhelming.
    * Otherwise → full MAX_GENERATIONS both ways.
    """
    dog = dogs[dog_id]
    has_parents = bool(dog.sire_id or dog.dam_id)
    n_direct = sum(1 for d in dogs.values() if d.sire_id == dog_id or d.dam_id == dog_id)
    if not has_parents and n_direct == 0:
        return (2, 2)
    if n_direct > MANY_DIRECT_CHILDREN:
        return (MAX_GENERATIONS, 2)
    return (MAX_GENERATIONS, MAX_GENERATIONS)


def _walk_ancestors(root_id: int, dogs: dict[int, Dog], max_generations: int) -> list[PedigreeNode]:
    """BFS upward through sire/dam links; stops at *max_generations*."""
    visited: set[int] = set()
    result: list[PedigreeNode] = []
    queue: list[tuple[int, int]] = []  # (dog_id, depth)

    root = dogs.get(root_id)
    if root is None:
        return result

    for parent_id in _parent_ids(root):
        if parent_id not in visited:
            queue.append((parent_id, 1))

    while queue:
        dog_id, depth = queue.pop(0)
        if dog_id in visited or depth > max_generations:
            continue
        dog = dogs.get(dog_id)
        if dog is None:
            # broken reference – skip silently so the app stays up
            continue
        visited.add(dog_id)
        node = PedigreeNode(dog=dog, depth=depth)
        result.append(node)
        if depth < max_generations:
            for parent_id in _parent_ids(dog):
                if parent_id not in visited:
                    queue.append((parent_id, depth + 1))

    return result


def _walk_descendants(
    root_id: int, dogs: dict[int, Dog], max_generations: int
) -> list[PedigreeNode]:
    """BFS downward through child relationships; stops at *max_generations*."""
    # Build a reverse index: parent_id → list[child Dog]
    children: dict[int, list[Dog]] = {}
    for dog in dogs.values():
        for parent_id in _parent_ids(dog):
            children.setdefault(parent_id, []).append(dog)

    visited: set[int] = set()
    result: list[PedigreeNode] = []
    queue: list[tuple[int, int]] = []

    for child in children.get(root_id, []):
        queue.append((child.id, 1))

    while queue:
        dog_id, depth = queue.pop(0)
        if dog_id in visited or depth > max_generations:
            continue
        dog = dogs.get(dog_id)
        if dog is None:
            continue
        visited.add(dog_id)
        result.append(PedigreeNode(dog=dog, depth=depth))
        if depth < max_generations:
            for child in children.get(dog_id, []):
                if child.id not in visited:
                    queue.append((child.id, depth + 1))

    return result


def _parent_ids(dog: Dog) -> list[int]:
    return [pid for pid in (dog.sire_id, dog.dam_id) if pid is not None]


@dataclass(frozen=True)
class PedigreeNetworkNode:
    """*generation* is 0 at the focus dog, negative toward ancestors, positive toward descendants."""

    id: int
    name: str
    breed: str
    sex: str
    generation: int


@dataclass(frozen=True)
class PedigreeNetworkEdge:
    parent_id: int
    child_id: int


@dataclass
class PedigreeNetwork:
    focus_id: int
    nodes: list[PedigreeNetworkNode]
    edges: list[PedigreeNetworkEdge]


def build_pedigree_network(
    focus_id: int,
    dogs: dict[int, Dog],
    max_ancestor_depth: int,
    max_descendant_depth: int,
) -> PedigreeNetwork:
    """Collect all dogs within *max_ancestor_depth* / *max_descendant_depth* of *focus_id*.

    Edges are parent → child links where both endpoints lie in the subgraph.
    """
    if focus_id not in dogs:
        return PedigreeNetwork(focus_id=focus_id, nodes=[], edges=[])

    gen_map = _generation_map_bfs(
        focus_id, dogs, max_ancestor_depth, max_descendant_depth
    )
    if not gen_map:
        return PedigreeNetwork(focus_id=focus_id, nodes=[], edges=[])

    node_ids = sorted(gen_map.keys(), key=lambda i: (gen_map[i], i))
    nodes = [
        PedigreeNetworkNode(
            id=i,
            name=dogs[i].name,
            breed=dogs[i].breed,
            sex=dogs[i].sex,
            generation=gen_map[i],
        )
        for i in node_ids
    ]

    edges: list[PedigreeNetworkEdge] = []
    for cid in node_ids:
        dog = dogs[cid]
        for pid in _parent_ids(dog):
            if pid in gen_map:
                edges.append(PedigreeNetworkEdge(parent_id=pid, child_id=cid))

    return PedigreeNetwork(focus_id=focus_id, nodes=nodes, edges=edges)


def _children_index(dogs: dict[int, Dog]) -> dict[int, list[int]]:
    children: dict[int, list[int]] = {}
    for d in dogs.values():
        for p in _parent_ids(d):
            children.setdefault(p, []).append(d.id)
    return children


def _generation_map_bfs(
    focus_id: int,
    dogs: dict[int, Dog],
    max_ancestor_depth: int,
    max_descendant_depth: int,
) -> dict[int, int]:
    """Map dog id → signed generation: parent links only upward, child links only downward."""
    anc_gen = _bfs_ancestors_only(focus_id, dogs, max_ancestor_depth)
    desc_gen = _bfs_descendants_only(focus_id, dogs, max_descendant_depth, _children_index(dogs))
    merged: dict[int, int] = dict(anc_gen)
    for did, g in desc_gen.items():
        if did not in merged:
            merged[did] = g
    return merged


def _bfs_ancestors_only(
    focus_id: int, dogs: dict[int, Dog], max_ancestor_depth: int
) -> dict[int, int]:
    gen: dict[int, int] = {focus_id: 0}
    q: deque[int] = deque([focus_id])
    while q:
        did = q.popleft()
        g = gen[did]
        if g <= -max_ancestor_depth:
            continue
        dog = dogs.get(did)
        if dog is None:
            continue
        for pid in _parent_ids(dog):
            if pid not in dogs:
                continue
            ng = g - 1
            if ng < -max_ancestor_depth:
                continue
            if pid not in gen:
                gen[pid] = ng
                q.append(pid)
    return gen


def _bfs_descendants_only(
    focus_id: int,
    dogs: dict[int, Dog],
    max_descendant_depth: int,
    children: dict[int, list[int]],
) -> dict[int, int]:
    gen: dict[int, int] = {focus_id: 0}
    q: deque[int] = deque([focus_id])
    while q:
        did = q.popleft()
        g = gen[did]
        if g >= max_descendant_depth:
            continue
        for cid in children.get(did, []):
            if cid not in dogs:
                continue
            ng = g + 1
            if ng > max_descendant_depth:
                continue
            if cid not in gen:
                gen[cid] = ng
                q.append(cid)
    return gen
