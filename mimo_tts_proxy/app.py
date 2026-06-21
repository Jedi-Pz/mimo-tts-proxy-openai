"""Entry point: load config, build the MIMO client, serve."""
import sys
from types import SimpleNamespace

from openai import OpenAI

from .config import load_config, load_voices, resolve_api_key
from .server import serve


def main():
    config = load_config()
    voices = load_voices()

    mimo_key = resolve_api_key(config["mimo"])
    if not mimo_key:
        print(
            "MIMO API key not set (env %s)" % config["mimo"].get("api_key_env"),
            file=sys.stderr,
        )
        sys.exit(1)
    client = OpenAI(api_key=mimo_key, base_url=config["mimo"]["base_url"])

    emotion_client = None
    if config["emotion"].get("enabled"):
        ekey = resolve_api_key(config["emotion"]) or mimo_key
        emotion_client = OpenAI(api_key=ekey, base_url=config["emotion"]["base_url"])

    state = SimpleNamespace(
        config=config, voices=voices, client=client, emotion_client=emotion_client
    )
    serve(state, config["server"]["host"], config["server"]["port"])


if __name__ == "__main__":
    main()
