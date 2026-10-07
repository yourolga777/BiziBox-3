from typing import Any

from sqlalchemy import case, func
from sqlalchemy.sql.elements import ColumnElement

from .translit import to_cyrillic, to_latin


def search_variants(text: str) -> list[str]:
    """Варианты строки поиска: оригинал + транслитерация в обе стороны.

    SQLite-функция lower() не понимает кириллицу, поэтому сравнение идёт по
    lower_utf8(); транслитерация закрывает поиск «Андрей Юмашев» → Andrey Yumashev
    и наоборот.
    """
    out: list[str] = []
    for v in (text, to_latin(text), to_cyrillic(text)):
        v = v.strip()
        if v and v not in out:
            out.append(v)
    return out


def _escaped_like_pattern(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def like_predicate(column: Any, term: str) -> ColumnElement[Any]:
    """Регистронезависимое подобие через custom SQLite-функцию lower_utf8.

    Python str.lower() корректно работает с кириллицей, в отличие от встроенной
    SQLite lower().
    """
    pattern = func.lower_utf8(_escaped_like_pattern(term))
    return func.lower_utf8(column).like(pattern, escape="\\")


def _digits_only(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def _phone_candidates(digits: str) -> list[str]:
    """Возвращает варианты цифрового запроса для поиска телефона."""
    candidates = {digits}
    if len(digits) >= 3:
        full = digits
        if len(full) == 11 and full.startswith("8"):
            full = "7" + full[1:]
        candidates.add(full)
        if len(full) == 11 and full.startswith("7"):
            candidates.add(full[1:])
    return sorted(candidates, key=len, reverse=True)


def phone_search_predicates(phone_column: Any, query: str) -> list[Any]:
    """Предикаты LIKE для телефона, нормализующие +7/8 и код страны.

    Поддерживает: '+7 (900) 123-45-67', '8 900 123 45 67', '79001234567',
    '9001234567', а также короткие подстроки из 3+ цифр.
    """
    digits = _digits_only(query)
    if len(digits) < 3:
        return []

    candidates = _phone_candidates(digits)

    phone_clean = func.replace(
        func.replace(
            func.replace(func.replace(phone_column, "-", ""), " ", ""),
            "(",
            "",
        ),
        ")",
        "",
    )
    phone_norm = case(
        (
            (func.length(phone_clean) == 11)
            & (func.substr(phone_clean, 1, 1) == "8"),
            func.concat("7", func.substr(phone_clean, 2)),
        ),
        else_=phone_clean,
    )
    phone_local = func.substr(phone_norm, -10)

    predicates: list[Any] = []
    for candidate in candidates:
        pattern = _escaped_like_pattern(candidate)
        if len(candidate) == 10:
            predicates.append(phone_local.like(pattern, escape="\\"))
        else:
            predicates.append(phone_norm.like(pattern, escape="\\"))
    return predicates
