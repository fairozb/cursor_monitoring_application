"""Application configuration loaded from environment variables."""

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root when present (never commit real .env)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

INSTANCE_DIR = _PROJECT_ROOT / "instance"
SECRET_KEY_FILE = INSTANCE_DIR / ".secret_key"


def _resolve_secret_key() -> str:
    """Use SECRET_KEY from the environment, or a generated per-install key file."""
    env_key = os.environ.get("SECRET_KEY", "").strip()
    if env_key:
        return env_key

    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    if SECRET_KEY_FILE.exists():
        stored = SECRET_KEY_FILE.read_text(encoding="utf-8").strip()
        if stored:
            return stored

    generated = secrets.token_hex(32)
    SECRET_KEY_FILE.write_text(generated + "\n", encoding="utf-8")
    try:
        SECRET_KEY_FILE.chmod(0o600)
    except OSError:
        pass
    return generated


class Config:
    """Base config. No passwords or secret keys are hardcoded in source."""

    SECRET_KEY = _resolve_secret_key()
    HOST = os.environ.get("FLASK_HOST", "127.0.0.1")
    PORT = int(os.environ.get("FLASK_PORT", "5000"))

    DATABASE_PATH = os.environ.get(
        "DATABASE_PATH",
        str(INSTANCE_DIR / "monitor.db"),
    )

    # Session cookie hardening (lab uses HTTP on localhost)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False

    WTF_CSRF_ENABLED = True
