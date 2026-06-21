"""Audio format helpers and ffmpeg transcoding.

MIMO always returns WAV; the proxy converts to the response_format the client
requested when it differs. Format mapping is pure; the actual conversion is
done by transcode_audio() via ffmpeg.
"""
import subprocess
import tempfile
from pathlib import Path

_CONTENT_TYPES = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "opus": "audio/ogg",
    "ogg": "audio/ogg",
    "flac": "audio/flac",
    "aac": "audio/aac",
    "pcm": "audio/pcm",
}


def content_type_for(fmt):
    return _CONTENT_TYPES.get((fmt or "").lower(), "application/octet-stream")


def needs_transcode(source_format, target_format):
    if not target_format:
        return False
    return target_format.lower() != (source_format or "").lower()


def transcode_audio(wav_bytes, target_format, ffmpeg_path="ffmpeg"):
    target_format = target_format.lower()
    if target_format == "wav":
        return wav_bytes
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as inf:
        inf.write(wav_bytes)
        in_path = inf.name
    out_path = in_path.rsplit(".", 1)[0] + "." + target_format
    try:
        cmd = [ffmpeg_path, "-y", "-loglevel", "error", "-i", in_path]
        if target_format in ("opus", "ogg"):
            cmd += ["-acodec", "libopus", "-ac", "1", "-b:a", "64k"]
        cmd.append(out_path)
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(
                "ffmpeg failed: " + result.stderr.decode("utf-8", "ignore")[:300]
            )
        return Path(out_path).read_bytes()
    finally:
        for p in (in_path, out_path):
            try:
                Path(p).unlink()
            except OSError:
                pass
