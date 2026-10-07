from typing import List


def detect_delimiter(text: str) -> str:
    """Определяет разделитель CSV по первой строке (заголовку).

    Приоритет: ';' → ',' → '\\t'. По умолчанию ','.
    """
    first_line = next((ln for ln in text.splitlines() if ln.strip()), "")
    counts = {"\\t": first_line.count("\\t")}
    for ch in (";", ","):
        counts[ch] = first_line.count(ch)
    for d, n in counts.items():
        if n:
            return d
    return ","


def parse_items_text(items_text: str) -> List[tuple[str, float]]:
    """Разбирает строку позиций вида ``Пицца x2, Кофе x1``.

    Возвращает [(name, quantity)]. Количество необязательно: без ``xN`` — 1.
    """
    items: List[tuple[str, float]] = []
    if not items_text:
        return items
    for part in items_text.split(","):
        part = part.strip()
        if not part:
            continue
        import re

        m = re.match(r"^(.*?)\s*[хxХX]\s*([\d.,]+)$", part, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            try:
                qty = float(m.group(2).replace(",", "."))
            except ValueError:
                qty = 1.0
        else:
            name = part
            qty = 1.0
        if name:
            items.append((name, qty))
    return items
