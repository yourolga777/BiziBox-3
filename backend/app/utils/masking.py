"""Утилиты маскирования секретов для ответов API и логирования."""

def mask_secret(value: str | None) -> str | None:
    """Маскирует секрет: первые 4 символа + '****'. Короткие значения маскируются целиком."""
    if not value:
        return value
    if len(value) <= 8:
        return "****"
    return value[:4] + "****"
