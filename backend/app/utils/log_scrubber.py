import logging

SENSITIVE_KEYS = frozenset({
    "password",
    "api_hash",
    "api_id",
    "session_string",
    "encryption_key",
    "secret_key",
    "secret",
    "token",
    "api_key",
})

MASK = "***"
MAX_DEPTH = 5


def mask_sensitive(value: object, depth: int = 0) -> object:
    if depth > MAX_DEPTH:
        return MASK
    if isinstance(value, dict):
        return {
            str(k): mask_sensitive(MASK if str(k) in SENSITIVE_KEYS else v, depth + 1)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [mask_sensitive(v, depth + 1) for v in value]
    return value


class SensitiveFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, (dict, list, tuple)):
            record.msg = mask_sensitive(record.msg)
        if record.args and isinstance(record.args, dict):
            record.args = mask_sensitive(record.args)  # type: ignore[assignment]
        return True
