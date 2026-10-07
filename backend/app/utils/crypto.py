import base64
import logging
import os

from cryptography.fernet import Fernet

from ..config import _DEFAULT_ENCRYPTION_KEYS, settings
from ..paths import get_data_dir

logger = logging.getLogger(__name__)

_DATA_DIR = get_data_dir()
_KEY_FILE = _DATA_DIR / ".encryption_key"
_ONBOARDING_FILE = _DATA_DIR / "onboarding.enc"

_cipher: Fernet | None = None


def _is_valid_fernet_key(raw: bytes) -> bool:
    try:
        Fernet(raw)
        return True
    except Exception:
        return False


def _encrypted_data_exists() -> bool:
    return os.path.exists(_ONBOARDING_FILE)


def _load_or_generate_key() -> bytes:
    raw_val = settings.ENCRYPTION_KEY
    if isinstance(raw_val, str):
        raw: bytes = raw_val.encode()
    else:
        raw = raw_val

    if _is_valid_fernet_key(raw):
        logger.info("Encryption key source: environment variable")
        return raw

    if raw and settings.ENCRYPTION_KEY not in _DEFAULT_ENCRYPTION_KEYS:
        raise RuntimeError(
            "ENCRYPTION_KEY in .env is not a valid Fernet key. "
            "Fix it or remove it to fall back to the file-based key."
        )

    if os.path.exists(_KEY_FILE):
        with open(_KEY_FILE, "rb") as f:
            file_key = f.read().strip()
        if _is_valid_fernet_key(file_key):
            logger.info("Encryption key source: %s", _KEY_FILE)
            return file_key
        logger.error("Encryption key file %s is corrupt", _KEY_FILE)
        raise RuntimeError(
            f"Encryption key file {_KEY_FILE} is corrupt. "
            "Restore it from backup or set a valid ENCRYPTION_KEY in .env."
        )

    if not _encrypted_data_exists() or settings.ALLOW_ENCRYPTION_KEY_RESET:
        key = base64.urlsafe_b64encode(os.urandom(32))
        os.makedirs(os.path.dirname(_KEY_FILE), exist_ok=True)
        with open(_KEY_FILE, "wb") as f:
            f.write(key)
        if settings.ALLOW_ENCRYPTION_KEY_RESET:
            logger.warning(
                "Encryption key reset confirmed via ALLOW_ENCRYPTION_KEY_RESET=1 — "
                "existing encrypted data may become undecryptable"
            )
        else:
            logger.info("Encryption key source: generated (first run)")
        return key

    raise RuntimeError(
        f"No encryption key found. Restore {_KEY_FILE} from backup "
        "or explicitly confirm reset by setting ALLOW_ENCRYPTION_KEY_RESET=1 in .env. "
        "Otherwise encrypted data (channels, onboarding) cannot be decrypted."
    )


def _get_cipher() -> Fernet:
    global _cipher
    if _cipher is None:
        _cipher = Fernet(_load_or_generate_key())
    return _cipher


def encrypt(text: str) -> str:
    encrypted: bytes = _get_cipher().encrypt(text.encode())
    return encrypted.decode()


def decrypt(encrypted: str) -> str:
    return _get_cipher().decrypt(encrypted.encode()).decode()
