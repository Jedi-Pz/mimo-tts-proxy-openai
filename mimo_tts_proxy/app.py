"""Entry point: load config, build the MIMO client, serve."""
from types import SimpleNamespace

from openai import OpenAI

from .config import load_config, load_voices, resolve_api_key
from .server import serve


def main():
    config = load_config()
    voices = load_voices()

    # MIMO_API_KEY is read from the project .env file — the only source.
    mimo_key = resolve_api_key()
    client = OpenAI(api_key=mimo_key, base_url=config["mimo"]["base_url"])

    emotion_client = None
    if config["emotion"].get("enabled"):
        emotion_client = OpenAI(api_key=mimo_key, base_url=config["emotion"]["base_url"])

    state = SimpleNamespace(
        config=config, voices=voices, client=client, emotion_client=emotion_client
    )
    serve(state, config["server"]["host"], config["server"]["port"])


if __name__ == "__main__":
    main()
