"""Data-level test: no directed cycles in the parent (sire/dam) graph.

Run:
    pytest tests/test_data_level.py
    pytest tests/test_data_level.py --pedigree-csv=fixtures/csv/corrupt_immediate_loop.csv
"""

from __future__ import annotations
from pathlib import Path
from pedigree_app.load_csv import load_dogs

def test_parent_graph_has_no_directed_cycles(pedigree_dataset_path: Path) -> None:
    dogs = load_dogs(pedigree_dataset_path)
    cycle = _find_directed_cycle_path(dogs)
    if cycle is not None:
        path_str = " -> ".join(str(x) for x in cycle)
        raise AssertionError(f"Illegal cycle detected\n{path_str}")


def _find_directed_cycle_path(dogs: dict[int, Dog]) -> list[int] | None:
    """Return one cycle as ``[n1, n2, ..., nk, n1]``, or ``None`` if acyclic."""
    ids = set(dogs.keys())
    graph: dict[int, list[int]] = {}
    for did, d in dogs.items():
        graph[did] = [
            p
            for p in (d.sire_id, d.dam_id)
            if p is not None and p in ids
        ]

    white, gray, black = 0, 1, 2
    color: dict[int, int] = {i: white for i in ids}
    stack: list[int] = []

    def dfs(u: int) -> list[int] | None:
        color[u] = gray
        stack.append(u)
        for v in graph.get(u, []):
            if color.get(v) == gray:
                i = stack.index(v)
                return stack[i:] + [v]
            if color.get(v) == white:
                found = dfs(v)
                if found is not None:
                    return found
        stack.pop()
        color[u] = black
        return None

    for nid in ids:
        if color[nid] == white:
            cycle = dfs(nid)
            if cycle is not None:
                return cycle
    return None
