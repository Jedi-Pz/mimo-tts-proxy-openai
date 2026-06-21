"""Config and voice-registry loading."""
import os
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


def resolve_api_key(section):
    env_name = section.get("api_key_env")
    return os.environ.get(env_name) if env_name else None
