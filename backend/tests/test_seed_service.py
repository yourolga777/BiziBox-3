from sqlalchemy import create_engine, text

from app.services.seed_service import seed_default_owner


def _make_conn():
    eng = create_engine("sqlite://")
    conn = eng.connect()
    conn.execute(
        text(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, "
            "password_hash TEXT, is_active INTEGER)"
        )
    )
    return conn


def test_seed_default_owner_creates_owner_when_empty():
    conn = _make_conn()
    try:
        seed_default_owner(conn)
        row = conn.execute(text("SELECT username FROM users WHERE id = 1")).fetchone()
        assert row is not None
        assert row[0] == "owner"
    finally:
        conn.close()


def test_seed_default_owner_is_idempotent_when_id1_occupied():
    conn = _make_conn()
    try:
        conn.execute(
            text(
                "INSERT INTO users (id, username, password_hash, is_active) "
                "VALUES (1, 'your_olga', '', 1)"
            )
        )
        # Раньше бросало ValueError «users.id=1 is already occupied by ...».
        seed_default_owner(conn)
        row = conn.execute(text("SELECT username FROM users WHERE id = 1")).fetchone()
        assert row is not None
        assert row[0] == "your_olga"
    finally:
        conn.close()
