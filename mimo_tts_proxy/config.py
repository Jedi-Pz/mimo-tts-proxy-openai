"""Config and voice-registry loading.

The only path for the MIMO API key is the project's .env file.
If it's missing or doesn't contain MIMO_API_KEY, the server refuses to start.
"""
import os
import sys
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent


def load_config(path=None):
    path = Path(path) if path else BASE_DIR / "config.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_voices(path=None):
    path = Path(path) if path else BASE_DIR / "voices.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_api_key(section=None):
    """Read MIMO_API_KEY from the project .env file, with an env-var
    fallback for Docker (where ``env_file`` injects vars at runtime).

    The ``section`` parameter is accepted for compatibility but ignored.
    """
    # 1. Try the .env file (primary path for local / launchd / systemd).
    dotenv_path = os.environ.get("MIMO_TTS_PROXY_DOTENV", str(BASE_DIR / ".env"))
    key = _read_dotenv_key(dotenv_path)
    if key:
        return key

    # 2. Fall back to the MIMO_API_KEY environment variable (Docker path).
    key = os.environ.get("MIMO_API_KEY")
    if key:
        return key

    # 3. Neither source available.
    print(
        "MIMO_API_KEY not found.\n"
        "  - Local / macOS launchd / Linux systemd: create a .env file with\n"
        "      MIMO_API_KEY=sk-your-key\n"
        "  - Docker: ensure the .env file exists in the project root and\n"
        "      docker compose uses 'env_file: .env' or '--env-file .env'",
        file=sys.stderr,
    )
    sys.exit(1)


def _read_dotenv_key(path):
    """Parse MIMO_API_KEY=VALUE from a .env file.

    Returns the value as a string, or None when the file doesn't
    exist / the key is missing / the value is empty.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("MIMO_API_KEY="):
                    value = line.split("=", 1)[1].strip()
                    # Strip surrounding quotes if present
                    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                        value = value[1:-1]
                    return value or None
    except FileNotFoundError:
        pass
    return None


def _read_dotenv_value(path, key_name):
    """Parse ``KEY_NAME=VALUE`` from a .env file.

    Returns the value as a string, or None.
    """
    prefix = key_name + "="
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith(prefix):
                    value = line.split("=", 1)[1].strip()
                    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                        value = value[1:-1]
                    return value or None
    except FileNotFoundError:
        pass
    return None


def resolve_proxy_api_key():
    """Read PROXY_API_KEY from the project .env file (optional).

    When set, clients MUST include ``Authorization: Bearer <key>``.
    When unset (None), no auth is required — suitable for isolated LANs.
    """
    dotenv_path = os.environ.get("MIMO_TTS_PROXY_DOTENV", str(BASE_DIR / ".env"))
    key = _read_dotenv_value(dotenv_path, "PROXY_API_KEY")
    if key:
        return key
    return os.environ.get("PROXY_API_KEY") or None
