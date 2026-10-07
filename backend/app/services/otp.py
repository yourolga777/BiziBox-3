import re
from typing import Optional

_KEYWORDS = r"(?:код|пароль|code|password|otp|pin|одноразовый)"
_DIGITS = r"((?<!\d)\d(?:[\s-]*\d){3,7}(?!\d))"

_AFTER_KEYWORD = re.compile(
    _KEYWORDS + r"\b[^\d\n]{0,25}" + _DIGITS,
    re.IGNORECASE,
)
_BEFORE_KEYWORD = re.compile(
    _DIGITS + r"[^\d\n]{0,25}" + _KEYWORDS,
    re.IGNORECASE,
)


def extract_otp(content: Optional[str]) -> Optional[str]:
    """Извлекает 4-8 значный код/пароль из текста сообщения.

    Возвращает строку из цифр без разделителей либо None, если код не найден
    или рядом с ключевым словом (код/пароль/code/password/otp/pin) нет
    подходящей последовательности.
    """
    if not content:
        return None
    for pattern in (_AFTER_KEYWORD, _BEFORE_KEYWORD):
        match = pattern.search(content)
        if match:
            digits = re.sub(r"\D", "", match.group(1))
            if 4 <= len(digits) <= 8:
                return digits
    return None
