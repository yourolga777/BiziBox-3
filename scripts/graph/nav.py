"""Навигация по графу: соседи, транзитивные стрелки, пути, циклы, сводка."""

from __future__ import annotations

from collections import defaultdict, deque

from .model import Graph


def _outgoing(graph: Graph) -> dict[str, list[str]]:
    adj: dict[str, list[str]] = defaultdict(list)
    for edge in graph.edges:
        adj[edge.src].append(edge.dst)
    return adj


def _incoming(graph: Graph) -> dict[str, list[str]]:
    adj: dict[str, list[str]] = defaultdict(list)
    for edge in graph.edges:
        adj[edge.dst].append(edge.src)
    return adj


def find_node(graph: Graph, query: str) -> str:
    if query in graph.nodes:
        return query
    matches = [nid for nid in graph.nodes if nid.endswith(query) or nid.endswith("/" + query)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValueError(f"файл не найден в графе: {query}")
    raise ValueError(f"неоднозначный запрос {query!r}, кандидаты: {matches}")


def _bfs(
    graph: Graph, start: str, adjacency: dict[str, list[str]], depth: int | None
) -> list[str]:
    visited: list[str] = []
    seen = {start}
    queue: deque[tuple[str, int]] = deque([(start, 0)])
    while queue:
        node, dist = queue.popleft()
        if dist > 0:
            visited.append(node)
        if depth is not None and dist >= depth:
            continue
        for nxt in adjacency.get(node, []):
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, dist + 1))
    return visited


def neighbors(graph: Graph, node_id: str) -> dict[str, list[str]]:
    return {
        "incoming": sorted(set(_incoming(graph).get(node_id, []))),
        "outgoing": sorted(set(_outgoing(graph).get(node_id, []))),
    }


def upstream(graph: Graph, node_id: str, depth: int | None = None) -> list[str]:
    return _bfs(graph, node_id, _incoming(graph), depth)


def downstream(graph: Graph, node_id: str, depth: int | None = None) -> list[str]:
    return _bfs(graph, node_id, _outgoing(graph), depth)


def shortest_path(graph: Graph, start: str, end: str) -> list[str] | None:
    if start == end:
        return [start]
    adjacency = _outgoing(graph)
    parent: dict[str, str] = {}
    seen = {start}
    queue: deque[str] = deque([start])
    while queue:
        node = queue.popleft()
        if node == end:
            break
        for nxt in adjacency.get(node, []):
            if nxt not in seen:
                seen.add(nxt)
                parent[nxt] = node
                queue.append(nxt)
    if end not in parent:
        return None
    path = [end]
    while path[-1] != start:
        path.append(parent[path[-1]])
    return list(reversed(path))


def entrypoints(graph: Graph) -> list[str]:
    incoming = _incoming(graph)
    return sorted(nid for nid in graph.nodes if not incoming.get(nid))


def orphans(graph: Graph) -> list[str]:
    incoming = _incoming(graph)
    outgoing = _outgoing(graph)
    return sorted(nid for nid in graph.nodes if not incoming.get(nid) and not outgoing.get(nid))


def _scc(graph: Graph) -> list[list[str]]:
    adjacency = _outgoing(graph)
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[list[str]] = []
    counter = [0]

    def dfs(node: str) -> None:
        index[node] = low[node] = counter[0]
        counter[0] += 1
        stack.append(node)
        on_stack.add(node)
        for nxt in adjacency.get(node, []):
            if nxt not in index:
                dfs(nxt)
                low[node] = min(low[node], low[nxt])
            elif nxt in on_stack:
                low[node] = min(low[node], index[nxt])
        if low[node] == index[node]:
            component: list[str] = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                component.append(w)
                if w == node:
                    break
            components.append(component)

    for node in graph.nodes:
        if node not in index:
            dfs(node)
    return components


def cycles(graph: Graph) -> list[list[str]]:
    components = _scc(graph)
    multi = [sorted(c) for c in components if len(c) > 1]
    self_loops = [[edge.src] for edge in graph.edges if edge.src == edge.dst]
    return sorted(multi, key=len, reverse=True) + sorted(self_loops)


def stats(graph: Graph) -> dict[str, object]:
    incoming = _incoming(graph)
    by_lang: dict[str, int] = defaultdict(int)
    for node in graph.nodes.values():
        by_lang[node.lang] += 1
    top = sorted(
        graph.nodes,
        key=lambda nid: len(incoming.get(nid, [])),
        reverse=True,
    )[:10]
    return {
        "nodes": len(graph.nodes),
        "edges": len(graph.edges),
        "unresolved": len(graph.unresolved),
        "by_lang": dict(by_lang),
        "top_incoming": [(nid, len(incoming.get(nid, []))) for nid in top],
    }
