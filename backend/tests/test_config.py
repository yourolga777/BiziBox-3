import pytest
from pydantic import ValidationError

from app.config import Settings


def test_defaults():
    s = Settings()
    assert s.HOST == "127.0.0.1"
    assert s.PORT == 7910
    assert s.ENVIRONMENT == "development"
    assert s.DEBUG is False
    assert "*" not in s.ALLOWED_ORIGINS


def test_env_override(monkeypatch):
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.setenv("PORT", "9999")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "real-secret-key-123")
    monkeypatch.setenv("ENCRYPTION_KEY", "real-encryption-key-456")
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    s = Settings()
    assert s.HOST == "0.0.0.0"
    assert s.PORT == 9999
    assert s.ENVIRONMENT == "production"


def test_default_secret_in_production_raises(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings()


def test_default_encryption_key_in_production_raises(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "real-secret-key-123")
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings()


def test_wildcard_cors_in_production_raises(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "real-secret-key-123")
    monkeypatch.setenv("ENCRYPTION_KEY", "real-encryption-key-456")
    monkeypatch.setenv("ALLOWED_ORIGINS", '["*"]')
    with pytest.raises(ValidationError):
        Settings()


def test_development_allows_defaults(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    s = Settings()
    assert s.ENVIRONMENT == "development"


def test_repr_does_not_leak_secrets(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "averysecretkey1234567890")
    monkeypatch.setenv("ENCRYPTION_KEY", "encryptionsecret4567890")
    s = Settings()
    text = repr(s)
    assert "averysecretkey1234567890" not in text
    assert "encryptionsecret4567890" not in text
    assert "****" in text
