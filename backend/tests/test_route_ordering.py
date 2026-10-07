import re

from starlette.routing import Route

from app.main import app


def _segments(path: str) -> list[str]:
    return [p for p in path.split("/") if p]


def _params(path: str) -> list[str]:
    return re.findall(r"\{[^}]+\}", path)


def _conflicts(literal: str, parametrized: str) -> bool:
    """Возвращает True, если запрос к literal попадёт в параметризованный маршрут."""
    ls = _segments(literal)
    ps = _segments(parametrized)
    if len(ls) != len(ps):
        return False
    for lseg, pseg in zip(ls, ps):
        if re.fullmatch(r"\{[^}]+\}", pseg):
            continue
        if lseg != pseg:
            return False
    return True


def test_no_literal_route_after_parametrized_same_segments():
    routes = [r for r in app.routes if isinstance(r, Route)]
    for p, proute in enumerate(routes):
        if not proute.path_format:
            continue
        if not _params(proute.path):
            continue
        for i in range(p + 1, len(routes)):
            literal = routes[i]
            if _params(literal.path) or not literal.methods or not proute.methods:
                continue
            if not (proute.methods & literal.methods):
                continue
            assert not _conflicts(literal.path, proute.path), (
                f"Литеральный маршрут {literal.path} {sorted(literal.methods)} "
                f"объявлен после параметризованного {proute.path} {sorted(proute.methods)} "
                f"и перехватывается им."
            )
