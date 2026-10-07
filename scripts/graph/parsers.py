"""Парсеры импортов Python (ast) и TypeScript + резолверы в пути файлов."""

from __future__ import annotations

import ast
import re
from pathlib import Path

_STATIC_IMPORT_RE = re.compile(r'^\s*(?:import|export)\b[^\n]*?["\']([^"\']+)["\']', re.M)
_TYPE_IMPORT_RE = re.compile(r"^\s*(?:import|export)\s+type\b")
_DYNAMIC_IMPORT_RE = re.compile(r"\bimport\s*\(\s*[\"']([^\"']+)[\"']\s*\)")
_REQUIRE_RE = re.compile(r"\brequire\s*\(\s*[\"']([^\"']+)[\"']\s*\)")


def _package_of(path: Path, pkg_root: Path) -> str:
    try:
        rel = path.relative_to(pkg_root)
    except ValueError:
        return ""
    return ".".join(rel.parts[:-1])


def _module_to_path(module: str, pkg_root: Path) -> Path | None:
    rel = Path(*module.split("."))
    file_candidate = pkg_root / rel.with_suffix(".py")
    if file_candidate.is_file():
        return file_candidate
    init_candidate = pkg_root / rel / "__init__.py"
    if init_candidate.is_file():
        return init_candidate
    return None


def resolve_python_import(
    module: str | None, level: int, current: Path, pkg_root: Path
) -> Path | None:
    """Резолвит Python-импорт в путь файла внутри пакета.

    module=None для `from . import X`; level — количество точек в `from ..x import`.
    """
    if level == 0:
        full = module or ""
    else:
        base_parts = _package_of(current, pkg_root).split(".") if _package_of(current, pkg_root) else []
        keep = len(base_parts) - (level - 1)
        parts = list(base_parts[:keep])
        if module:
            parts.extend(module.split("."))
        full = ".".join(parts) if parts else ""
    if not full:
        return None
    return _module_to_path(full, pkg_root)


def parse_python_imports(path: Path) -> list[tuple[str | None, int]]:
    """Возвращает список (module, level) для всех import/import-from в файле."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return []
    result: list[tuple[str | None, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                result.append((alias.name, 0))
        elif isinstance(node, ast.ImportFrom):
            result.append((node.module, node.level))
    return result


def resolve_ts_import(spec: str, current: Path) -> Path | None:
    """Резолвит относительный TS-импорт в путь файла."""
    if not spec.startswith("."):
        return None
    base = (current.parent / spec).resolve()
    candidates = [
        base,
        Path(str(base) + ".ts"),
        Path(str(base) + ".tsx"),
        Path(str(base) + ".d.ts"),
        Path(str(base) + ".js"),
        Path(str(base) + ".jsx"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    for index_name in ("index.ts", "index.tsx", "index.d.ts"):
        candidate = base / index_name
        if candidate.is_file():
            return candidate
    return None


def parse_ts_imports(path: Path) -> list[tuple[str, str]]:
    """Возвращает список (spec, kind) для TS-импортов. kind: import | type."""
    text = path.read_text(encoding="utf-8", errors="replace")
    result: list[tuple[str, str]] = []
    for match in _STATIC_IMPORT_RE.finditer(text):
        spec = match.group(1)
        kind = "type" if _TYPE_IMPORT_RE.match(match.group(0)) else "import"
        result.append((spec, kind))
    for match in _DYNAMIC_IMPORT_RE.finditer(text):
        result.append((match.group(1), "import"))
    for match in _REQUIRE_RE.finditer(text):
        result.append((match.group(1), "import"))
    return result
