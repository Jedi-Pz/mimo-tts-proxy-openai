"""Map a voice name (from the OpenAI TTS client) to a voice spec.

A registered voice with a sample_file is a cloned voice; one with a preset
is a MIMO preset voice. Unregistered names fall back to being treated as a
preset voice name, so clients can pass any MIMO preset directly.
"""
import base64
from pathlib import Path

_SAMPLE_MIME = {".mp3": "audio/mpeg", ".wav": "audio/wav"}


def resolve_voice(name, registry):
    voices = (registry or {}).get("voices", {}) or {}
    entry = voices.get(name)
    base_style = (entry or {}).get("base_style")
    emotion_inference = bool((entry or {}).get("emotion_inference", False))

    if entry is None:
        return {
            "kind": "preset",
            "sample_file": None,
            "preset": name,
            "base_style": base_style,
            "emotion_inference": emotion_inference,
        }

    if entry.get("sample_file"):
        return {
            "kind": "clone",
            "sample_file": entry["sample_file"],
            "preset": None,
            "base_style": base_style,
            "emotion_inference": emotion_inference,
        }

    return {
        "kind": "preset",
        "sample_file": None,
        "preset": entry.get("preset", name),
        "base_style": base_style,
        "emotion_inference": emotion_inference,
    }


def build_voice_param(spec):
    """Return the value for MIMO's audio.voice field: a preset name, or a
    data URL of the clone sample's bytes."""
    if spec["kind"] == "clone":
        return _encode_sample(spec["sample_file"])
    return spec["preset"]


def _encode_sample(file_path):
    path = Path(file_path)
    data = path.read_bytes()
    if len(data) > 10 * 1024 * 1024:
        raise ValueError("voice sample >10MB: %s" % file_path)
    mime = _SAMPLE_MIME.get(path.suffix.lower())
    if not mime:
        raise ValueError("unsupported sample format %s; use mp3 or wav" % path.suffix)
    return "data:%s;base64,%s" % (mime, base64.b64encode(data).decode("ascii"))
