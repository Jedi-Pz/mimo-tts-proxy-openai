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
    """Read MIMO_API_KEY from the project .env file.

    The *section* parameter is accepted for compatibility but ignored:
    all services share the same key now.  The .env file path can be
    overridden via the MIMO_TTS_PROXY_DOTENV environment variable
    (needed for Docker / launchd / systemd where the default
    BASE_DIR/.env may not be accessible).
    """
    dotenv_path = os.environ.get("MIMO_TTS_PROXY_DOTENV", str(BASE_DIR / ".env"))
    key = _read_dotenv_key(dotenv_path)
    if not key:
        print(
            "MIMO_API_KEY not found in %s" % dotenv_path,
            file=sys.stderr,
        )
        print("Create a .env file in the project root with:", file=sys.stderr)
        print("    MIMO_API_KEY=sk-your-key", file=sys.stderr)
        print("Or run ./deploy.sh to set up interactively.", file=sys.stderr)
        sys.exit(1)
    return key


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
