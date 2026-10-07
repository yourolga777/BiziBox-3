"""Карта графа импортов кода + CLI-навигация по зависимостям.

Вершины — файлы проекта (.py / .ts / .tsx), рёбра — импорты.
Ребро A -> B значит «A использует B». Агент ходит по стрелкам,
а не держит весь код в контексте.
"""

from .build import build_graph
from .model import Edge, Graph, Node, load_graph, save_graph
from .nav import (
    cycles,
    downstream,
    entrypoints,
    find_node,
    neighbors,
    orphans,
    shortest_path,
    stats,
    upstream,
)
from .parsers import (
    parse_python_imports,
    parse_ts_imports,
    resolve_python_import,
    resolve_ts_import,
)

__all__ = [
    "Edge",
    "Graph",
    "Node",
    "build_graph",
    "cycles",
    "downstream",
    "entrypoints",
    "find_node",
    "load_graph",
    "neighbors",
    "orphans",
    "parse_python_imports",
    "parse_ts_imports",
    "resolve_python_import",
    "resolve_ts_import",
    "save_graph",
    "shortest_path",
    "stats",
    "upstream",
]
