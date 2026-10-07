"""Карта графа импортов кода — модель данных и сериализация."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

_EXCLUDED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
}


@dataclass
class Node:
    id: str
    lang: str
    kind: str


@dataclass
class Edge:
    src: str
    dst: str
    kind: str


@dataclass
class Graph:
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    unresolved: list[tuple[str, str]] = field(default_factory=list)


def _excluded(path: Path) -> bool:
    for part in path.parts:
        if part in _EXCLUDED_PARTS:
            return True
        if part.startswith(".venv") or part == "site-packages":
            return True
    return False


def _is_test(path: Path) -> bool:
    parts = set(path.parts)
    return (
        "test" in path.stem
        or path.name.startswith("test_")
        or "__tests__" in parts
        or "tests" in parts
    )


def _kind(path: Path) -> str:
    if path.name == "__init__.py":
        return "package"
    if _is_test(path):
        return "test"
    return "module"


def save_graph(graph: Graph, out: Path) -> None:
    data = {
        "nodes": [
            {"id": n.id, "lang": n.lang, "kind": n.kind}
            for n in sorted(graph.nodes.values(), key=lambda n: n.id)
        ],
        "edges": [{"from": e.src, "to": e.dst, "kind": e.kind} for e in graph.edges],
        "unresolved": [{"file": f, "spec": s} for f, s in graph.unresolved],
    }
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_graph(path: Path) -> Graph:
    data = json.loads(path.read_text(encoding="utf-8"))
    graph = Graph()
    graph.nodes = {
        n["id"]: Node(id=n["id"], lang=n["lang"], kind=n["kind"])
        for n in data["nodes"]
    }
    graph.edges = [Edge(src=e["from"], dst=e["to"], kind=e["kind"]) for e in data["edges"]]
    graph.unresolved = [(u["file"], u["spec"]) for u in data["unresolved"]]
    return graph
