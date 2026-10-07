_CYR_TO_LAT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}

_LAT_TO_CYR = {
    "shch": "щ", "zh": "ж", "kh": "х", "ts": "ц", "ch": "ч", "sh": "ш",
    "yo": "ё", "yu": "ю", "ya": "я", "ye": "е",
    "a": "а", "b": "б", "c": "ц", "d": "д", "e": "е", "f": "ф", "g": "г",
    "h": "х", "i": "и", "j": "й", "k": "к", "l": "л", "m": "м", "n": "н",
    "o": "о", "p": "п", "q": "к", "r": "р", "s": "с", "t": "т", "u": "у",
    "v": "в", "w": "в", "x": "кс", "y": "й", "z": "з",
}


def to_latin(text: str) -> str:
    """Транслитерация кириллицы в латиницу (нижний регистр).

    Некириллические символы сохраняются как есть.
    """
    return "".join(_CYR_TO_LAT.get(ch.lower(), ch) for ch in text)


def to_cyrillic(text: str) -> str:
    """Обратная транслитерация латиницы в кириллицу (best-effort, нижний регистр).

    Неоднозначные буквы (y, h, c) сопоставляются по самому частому варианту.
    """
    out: list[str] = []
    low = text.lower()
    i = 0
    n = len(low)
    while i < n:
        matched = False
        for length in (4, 3, 2, 1):
            if i + length <= n and low[i : i + length] in _LAT_TO_CYR:
                out.append(_LAT_TO_CYR[low[i : i + length]])
                i += length
                matched = True
                break
        if not matched:
            out.append(text[i])
            i += 1
    return "".join(out)
