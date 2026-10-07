def _lower_utf8(value: object) -> object:
    """str.lower(), понимающий кириллицу (встроенная SQLite lower() — ASCII-only)."""
    if isinstance(value, str):
        return value.lower()
    return value


def register_sqlite_functions(dbapi_connection: object, _connection_record: object = None) -> None:
    """Регистрирует lower_utf8 на сыром соединении SQLite.

    Вызывается из event "connect" (два позиционных аргумента) для продакшен-
    и тестового движков.
    """
    conn = getattr(dbapi_connection, "dbapi_connection", dbapi_connection)
    create_function = getattr(conn, "create_function", None)
    if create_function is not None:
        create_function("lower_utf8", 1, _lower_utf8)
