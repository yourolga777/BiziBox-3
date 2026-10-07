"""CLI-интерфейс карты графа импортов."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from .build import build_graph
from .model import Graph, load_graph, save_graph
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

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GRAPH = "graph.json"


def _fmt_lines(items: Iterable[str]) -> str:
    lines = list(items)
    return "\n".join(lines) if lines else "(пусто)"


def _load(path: Path) -> Graph:
    if not path.is_file():
        raise SystemExit(f"graph.json не найден: {path}. Сначала запустите `graph.py build`.")
    return load_graph(path)


def _add_file_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("file", help="файл (id или суффикс)")


def _add_graph_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--graph", default=str(PROJECT_ROOT / DEFAULT_GRAPH))
    parser.add_argument("--json", action="store_true")


def build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="graph.py", description="Карта графа импортов + навигация")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build", help="собрать graph.json")
    p_build.add_argument("--root", default=str(PROJECT_ROOT))
    p_build.add_argument("--out", default=DEFAULT_GRAPH)
    p_build.add_argument("--no-tests", action="store_true")
    p_build.add_argument("--json", action="store_true")

    p_neighbors = sub.add_parser("neighbors", help="кто меня импортирует / кого я импортирую")
    _add_file_arg(p_neighbors)
    _add_graph_args(p_neighbors)

    p_up = sub.add_parser("upstream", help="по стрелкам вверх (кто зависит от файла)")
    _add_file_arg(p_up)
    p_up.add_argument("--depth", type=int, default=None)
    _add_graph_args(p_up)

    p_down = sub.add_parser("downstream", help="по стрелкам вниз (что файл тянет за собой)")
    _add_file_arg(p_down)
    p_down.add_argument("--depth", type=int, default=None)
    _add_graph_args(p_down)

    p_path = sub.add_parser("path", help="кратчайший путь зависимости A -> B")
    p_path.add_argument("start")
    p_path.add_argument("end")
    _add_graph_args(p_path)

    for name in ("entrypoints", "orphans", "cycles", "stats"):
        sub.add_parser(name, help=name)
        _add_graph_args(sub.choices[name])

    return parser


def _emit(obj: object, as_json: bool) -> None:
    if as_json:
        print(json.dumps(obj, ensure_ascii=False, indent=2))
    elif isinstance(obj, list):
        print(_fmt_lines(str(x) for x in obj))
    elif isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, list):
                print(f"{key}:")
                print(_fmt_lines(f"  {v}" for v in value))
            else:
                print(f"{key}: {value}")
    else:
        print(obj)


def main(argv: list[str] | None = None) -> int:
    parser = build_cli()
    args = parser.parse_args(argv)

    if args.cmd == "build":
        graph = build_graph(Path(args.root), no_tests=args.no_tests)
        save_graph(graph, Path(args.out))
        _emit(stats(graph), args.json)
        if graph.unresolved:
            print("\nunresolved (локальные импорты без файла):")
            for file, spec in graph.unresolved:
                print(f"  {file} -> {spec}")
        return 0

    graph = _load(Path(args.graph))
    cmd = args.cmd

    if cmd == "neighbors":
        _emit(neighbors(graph, find_node(graph, args.file)), args.json)
    elif cmd == "upstream":
        _emit(upstream(graph, find_node(graph, args.file), args.depth), args.json)
    elif cmd == "downstream":
        _emit(downstream(graph, find_node(graph, args.file), args.depth), args.json)
    elif cmd == "path":
        start = find_node(graph, args.start)
        end = find_node(graph, args.end)
        path = shortest_path(graph, start, end)
        _emit(path if path is not None else [], args.json)
    elif cmd == "entrypoints":
        _emit(entrypoints(graph), args.json)
    elif cmd == "orphans":
        _emit(orphans(graph), args.json)
    elif cmd == "cycles":
        _emit([", ".join(c) for c in cycles(graph)], args.json)
    elif cmd == "stats":
        _emit(stats(graph), args.json)
    return 0
