"""Сборка графа импортов по каталогу проекта."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .model import Edge, Graph, Node, _excluded, _is_test, _kind
from .parsers import parse_python_imports, parse_ts_imports, resolve_python_import, resolve_ts_import


def _iter_python_files(pkg_root: Path) -> Iterable[Path]:
    if not pkg_root.is_dir():
        return []
    return (p for p in pkg_root.rglob("*.py") if not _excluded(p))


def _iter_ts_files(ts_root: Path) -> Iterable[Path]:
    if not ts_root.is_dir():
        return []
    return (
        p
        for p in list(ts_root.rglob("*.ts")) + list(ts_root.rglob("*.tsx"))
        if not _excluded(p)
    )


def build_graph(root: Path, no_tests: bool = False) -> Graph:
    """Строит граф импортов для проекта с корнем `root`."""
    pkg_root = root / "backend"
    ts_root = root / "frontend" / "src"
    graph = Graph()

    py_files = list(_iter_python_files(pkg_root))
    ts_files = list(_iter_ts_files(ts_root))

    for path in py_files + ts_files:
        if no_tests and _is_test(path):
            continue
        node_id = path.relative_to(root).as_posix()
        lang = "python" if path in py_files else "typescript"
        graph.nodes[node_id] = Node(id=node_id, lang=lang, kind=_kind(path))

    for path in py_files:
        if no_tests and _is_test(path):
            continue
        src_id = path.relative_to(root).as_posix()
        for module, level in parse_python_imports(path):
            target = resolve_python_import(module, level, path, pkg_root)
            if target is None:
                top = (module or "").split(".")[0]
                if level > 0 or top == "app":
                    spec = ("." * level) + (module or "") if level > 0 else (module or "")
                    graph.unresolved.append((src_id, spec))
                continue
            dst_id = target.relative_to(root).as_posix()
            if dst_id in graph.nodes:
                graph.edges.append(Edge(src=src_id, dst=dst_id, kind="import"))

    for path in ts_files:
        if no_tests and _is_test(path):
            continue
        src_id = path.relative_to(root).as_posix()
        for spec, kind in parse_ts_imports(path):
            target = resolve_ts_import(spec, path)
            if target is None:
                continue
            dst_id = target.relative_to(root).as_posix()
            if dst_id in graph.nodes:
                graph.edges.append(Edge(src=src_id, dst=dst_id, kind=kind))

    graph.edges.sort(key=lambda e: (e.src, e.dst, e.kind))
    return graph
