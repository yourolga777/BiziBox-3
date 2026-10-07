import base64
import os

import pytest

from app.config import settings
from app.utils import crypto
from app.utils.crypto import decrypt, encrypt


@pytest.fixture(autouse=True)
def reset_cipher():
    crypto._cipher = None
    yield
    crypto._cipher = None


def _fresh_key() -> bytes:
    return base64.urlsafe_b64encode(os.urandom(32))


def test_roundtrip_encrypt_decrypt():
    text = "hello secret"
    assert decrypt(encrypt(text)) == text


def test_generates_key_on_first_run(monkeypatch, tmp_path):
    key_file = tmp_path / ".encryption_key"
    onboarding = tmp_path / "onboarding.enc"
    monkeypatch.setattr(crypto, "_KEY_FILE", str(key_file))
    monkeypatch.setattr(crypto, "_ONBOARDING_FILE", str(onboarding))
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", "")
    monkeypatch.setattr(settings, "ALLOW_ENCRYPTION_KEY_RESET", False)
    crypto._cipher = None
    key = crypto._load_or_generate_key()
    assert os.path.exists(key_file)
    assert key_file.read_bytes() == key
    assert len(key) == 44


def test_uses_env_key_when_valid(monkeypatch, tmp_path):
    key = _fresh_key()
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", key.decode())
    monkeypatch.setattr(settings, "ALLOW_ENCRYPTION_KEY_RESET", False)
    crypto._cipher = None
    loaded = crypto._load_or_generate_key()
    assert loaded == key


def test_uses_file_key_when_env_invalid(monkeypatch, tmp_path):
    key_file = tmp_path / ".encryption_key"
    key = _fresh_key()
    key_file.write_bytes(key)
    monkeypatch.setattr(crypto, "_KEY_FILE", str(key_file))
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", "change-me-in-production")
    monkeypatch.setattr(settings, "ALLOW_ENCRYPTION_KEY_RESET", False)
    crypto._cipher = None
    loaded = crypto._load_or_generate_key()
    assert loaded == key


def test_invalid_env_key_format_raises(monkeypatch, tmp_path):
    key_file = tmp_path / ".encryption_key"
    key_file.write_bytes(_fresh_key())
    monkeypatch.setattr(crypto, "_KEY_FILE", str(key_file))
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", "not-a-fernet-key-1234567890")
    monkeypatch.setattr(settings, "ALLOW_ENCRYPTION_KEY_RESET", False)
    crypto._cipher = None
    with pytest.raises(RuntimeError, match="not a valid Fernet key"):
        crypto._load_or_generate_key()


def test_encrypted_data_without_key_raises(monkeypatch, tmp_path):
    key_file = tmp_path / ".encryption_key"
    onboarding = tmp_path / "onboarding.enc"
    onboarding.write_text("encrypted", encoding="utf-8")
    monkeypatch.setattr(crypto, "_KEY_FILE", str(key_file))
    monkeypatch.setattr(crypto, "_ONBOARDING_FILE", str(onboarding))
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", "")
    monkeypatch.setattr(settings, "ALLOW_ENCRYPTION_KEY_RESET", False)
    crypto._cipher = None
    with pytest.raises(RuntimeError, match="No encryption key found"):
        crypto._load_or_generate_key()


def test_reset_flag_generates_despite_data(monkeypatch, tmp_path):
    key_file = tmp_path / ".encryption_key"
    onboarding = tmp_path / "onboarding.enc"
    onboarding.write_text("encrypted", encoding="utf-8")
    monkeypatch.setattr(crypto, "_KEY_FILE", str(key_file))
    monkeypatch.setattr(crypto, "_ONBOARDING_FILE", str(onboarding))
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", "")
    monkeypatch.setattr(settings, "ALLOW_ENCRYPTION_KEY_RESET", True)
    crypto._cipher = None
    key = crypto._load_or_generate_key()
    assert os.path.exists(key_file)
    assert len(key) == 44


def test_encrypt_without_existing_file_uses_generated(tmp_path, monkeypatch):
    key_file = tmp_path / ".encryption_key"
    monkeypatch.setattr(crypto, "_KEY_FILE", str(key_file))
    monkeypatch.setattr(crypto, "_ONBOARDING_FILE", str(tmp_path / "onboarding.enc"))
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", "")
    monkeypatch.setattr(settings, "ALLOW_ENCRYPTION_KEY_RESET", False)
    crypto._cipher = None
    text = "payload"
    encrypted = encrypt(text)
    assert decrypt(encrypted) == text
