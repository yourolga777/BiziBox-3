import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.graph import (  # noqa: E402
    build_graph,
    cycles,
    downstream,
    entrypoints,
    find_node,
    neighbors,
    orphans,
    parse_python_imports,
    parse_ts_imports,
    resolve_python_import,
    resolve_ts_import,
    shortest_path,
    stats,
    upstream,
)


def _write(root: Path, rel: str, content: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture
def project(tmp_path: Path):
    files = {
        "backend/app/__init__.py": "",
        "backend/app/main.py": "from app.services.order import make_order\n",
        "backend/app/services/__init__.py": "",
        "backend/app/services/order.py": "from ..models import OrderModel\nfrom ..main import bootstrap\n",
        "backend/app/models/__init__.py": "from .order import OrderModel\n",
        "backend/app/models/order.py": "import sqlalchemy\nfrom ..nonexistent import X\n",
        "frontend/src/main.tsx": "import App from './App'\n",
        "frontend/src/App.tsx": "import type { Order } from './types/order'\n",
        "frontend/src/types/order.ts": "export interface Order { id: string }\n",
        "frontend/src/api/client.ts": "export const request = () => {}\n",
        "frontend/src/utils.ts": "export const helper = () => {}\n",
    }
    for rel, content in files.items():
        _write(tmp_path, rel, content)
    return tmp_path, build_graph(tmp_path)


def test_parse_python_imports(tmp_path: Path) -> None:
    f = tmp_path / "x.py"
    f.write_text(
        "import os\n"
        "from ..models import OrderModel\n"
        "from .task_extractor import TaskExtractor\n"
        "from app.services.order import x\n",
        encoding="utf-8",
    )
    imports = parse_python_imports(f)
    assert ("os", 0) in imports
    assert ("models", 2) in imports
    assert ("task_extractor", 1) in imports
    assert ("app.services.order", 0) in imports


def test_resolve_python_relative(tmp_path: Path) -> None:
    pkg = tmp_path / "backend"
    (pkg / "app" / "models").mkdir(parents=True)
    (pkg / "app" / "models" / "__init__.py").write_text("", encoding="utf-8")
    current = pkg / "app" / "services" / "order.py"
    assert resolve_python_import("models", 2, current, pkg) == pkg / "app" / "models" / "__init__.py"


def test_resolve_python_absolute(tmp_path: Path) -> None:
    pkg = tmp_path / "backend"
    (pkg / "app" / "services").mkdir(parents=True)
    (pkg / "app" / "services" / "order.py").write_text("", encoding="utf-8")
    current = pkg / "app" / "main.py"
    assert resolve_python_import("app.services.order", 0, current, pkg) == pkg / "app" / "services" / "order.py"


def test_parse_ts_imports(tmp_path: Path) -> None:
    f = tmp_path / "x.ts"
    f.write_text(
        "import { a } from './a'\n"
        "import type { B } from './b'\n"
        "const c = require('./c')\n"
        "const d = await import('./d')\n"
        "import { e } from 'react'\n",
        encoding="utf-8",
    )
    imports = parse_ts_imports(f)
    assert ("./a", "import") in imports
    assert ("./b", "type") in imports
    assert ("./c", "import") in imports
    assert ("./d", "import") in imports
    assert ("react", "import") in imports


def test_resolve_ts_import(tmp_path: Path) -> None:
    src = tmp_path / "frontend" / "src"
    (src / "types").mkdir(parents=True)
    (src / "types" / "order.ts").write_text("", encoding="utf-8")
    current = src / "App.tsx"
    assert resolve_ts_import("./types/order", current) == src / "types" / "order.ts"
    assert resolve_ts_import("react", current) is None


def test_build_graph_nodes(project) -> None:
    _, graph = project
    assert len(graph.nodes) == 11
    assert graph.nodes["backend/app/services/order.py"].lang == "python"
    assert graph.nodes["frontend/src/App.tsx"].lang == "typescript"


def test_build_graph_edges(project) -> None:
    _, graph = project
    pairs = {(e.src, e.dst, e.kind) for e in graph.edges}
    assert ("backend/app/main.py", "backend/app/services/order.py", "import") in pairs
    assert ("backend/app/services/order.py", "backend/app/models/__init__.py", "import") in pairs
    assert ("backend/app/services/order.py", "backend/app/main.py", "import") in pairs
    assert ("backend/app/models/__init__.py", "backend/app/models/order.py", "import") in pairs
    assert ("frontend/src/main.tsx", "frontend/src/App.tsx", "import") in pairs
    assert ("frontend/src/App.tsx", "frontend/src/types/order.ts", "type") in pairs
    assert len(graph.edges) == 6


def test_third_party_ignored(project) -> None:
    _, graph = project
    assert all("sqlalchemy" not in nid for nid in graph.nodes)
    assert all("sqlalchemy" not in e.dst for e in graph.edges)


def test_unresolved_not_fatal(project) -> None:
    _, graph = project
    assert graph.unresolved == [("backend/app/models/order.py", "..nonexistent")]
    assert len(graph.nodes) == 11


def test_entrypoints(project) -> None:
    _, graph = project
    eps = set(entrypoints(graph))
    assert "frontend/src/main.tsx" in eps
    assert "backend/app/main.py" not in eps
    assert "backend/app/services/__init__.py" in eps


def test_orphans(project) -> None:
    _, graph = project
    orph = set(orphans(graph))
    assert "frontend/src/api/client.ts" in orph
    assert "frontend/src/utils.ts" in orph


def test_neighbors(project) -> None:
    _, graph = project
    res = neighbors(graph, "backend/app/services/order.py")
    assert res["incoming"] == ["backend/app/main.py"]
    assert res["outgoing"] == ["backend/app/main.py", "backend/app/models/__init__.py"]


def test_downstream_depth(project) -> None:
    _, graph = project
    assert downstream(graph, "backend/app/main.py", depth=1) == ["backend/app/services/order.py"]
    assert downstream(graph, "backend/app/main.py", depth=2) == [
        "backend/app/services/order.py",
        "backend/app/models/__init__.py",
    ]


def test_upstream(project) -> None:
    _, graph = project
    assert upstream(graph, "backend/app/models/__init__.py") == [
        "backend/app/services/order.py",
        "backend/app/main.py",
    ]


def test_shortest_path(project) -> None:
    _, graph = project
    assert shortest_path(graph, "backend/app/main.py", "backend/app/models/order.py") == [
        "backend/app/main.py",
        "backend/app/services/order.py",
        "backend/app/models/__init__.py",
        "backend/app/models/order.py",
    ]


def test_cycles(project) -> None:
    _, graph = project
    joined = [set(c) for c in cycles(graph)]
    assert {"backend/app/main.py", "backend/app/services/order.py"} in joined


def test_find_node(project) -> None:
    _, graph = project
    assert find_node(graph, "backend/app/main.py") == "backend/app/main.py"
    assert find_node(graph, "models/order.py") == "backend/app/models/order.py"
    with pytest.raises(ValueError):
        find_node(graph, "order.py")
    with pytest.raises(ValueError):
        find_node(graph, "no_such_file.py")


def test_stats(project) -> None:
    _, graph = project
    s = stats(graph)
    assert s["nodes"] == 11
    assert s["edges"] == 6
    assert s["unresolved"] == 1
