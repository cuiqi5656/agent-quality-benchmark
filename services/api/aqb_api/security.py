from __future__ import annotations

import base64
import hashlib
import re
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


class SecretConfigurationError(RuntimeError):
    pass


def _fernet(key: str | None) -> Fernet:
    if not key:
        raise SecretConfigurationError("AQB_ENCRYPTION_KEY must be configured before storing credentials")
    try:
        decoded = base64.urlsafe_b64decode(key.encode())
        if len(decoded) != 32:
            raise ValueError
        return Fernet(key.encode())
    except (ValueError, TypeError) as error:
        raise SecretConfigurationError("AQB_ENCRYPTION_KEY must be a Fernet-compatible 32-byte key") from error


def encrypt_secret(value: str, key: str | None) -> str:
    return _fernet(key).encrypt(value.encode()).decode()


def decrypt_secret(value: str, key: str | None) -> str:
    try:
        return _fernet(key).decrypt(value.encode()).decode()
    except InvalidToken as error:
        raise SecretConfigurationError("stored credential could not be decrypted") from error


SENSITIVE_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"(?i)(api[_-]?key|authorization|token)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
]


def redact(value: str) -> str:
    result = value
    for pattern in SENSITIVE_PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    return result


def safe_artifact_path(root: Path, identifier: str, suffix: str) -> Path:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    safe_identifier = re.sub(r"[^a-zA-Z0-9._-]", "_", identifier)
    target = (root / (safe_identifier + suffix)).resolve()
    if root not in target.parents:
        raise ValueError("artifact path escaped the configured storage root")
    return target


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
