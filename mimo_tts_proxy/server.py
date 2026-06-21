"""HTTP server implementing the OpenAI /v1/audio/speech endpoint."""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import resolve_proxy_api_key
from .emotion import assemble_style_prompt, infer_emotion
from .mimo import build_mimo_request, select_model, synthesize
from .transcode import content_type_for, needs_transcode, transcode_audio
from .voices import build_voice_param, resolve_voice


class ProxyError(Exception):
    def __init__(self, message, status=400, type_="invalid_request_error"):
        super().__init__(message)
        self.status = status
        self.type_ = type_


def check_auth(auth_header, proxy_key):
    """Validate ``Authorization: Bearer <key>`` against the configured proxy key.

    When *proxy_key* is None, auth is not required — all requests pass.
    When *proxy_key* is set, the ``Authorization`` header must contain
    ``Bearer <key>``` (case-insensitive scheme).  Raises ProxyError(401)
    on mismatch.
    """
    if proxy_key is None:
        return
    if not auth_header:
        raise ProxyError("Authorization header missing", 401, "authentication_error")
    parts = auth_header.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise ProxyError("Authorization must be Bearer <key>", 401, "authentication_error")
    if parts[1] != proxy_key:
        raise ProxyError("Invalid proxy API key", 401, "authentication_error")


def handle_speech(body, state):
    input_text = (body.get("input") or "").strip()
    if not input_text:
        raise ProxyError("input is required")
    voice_name = body.get("voice")
    if not voice_name:
        raise ProxyError("voice is required")

    response_format = (
        body.get("response_format") or state.config["audio"]["default_format"]
    ).lower()
    context = body.get("context")

    spec = resolve_voice(voice_name, state.voices)
    voice_param = build_voice_param(spec)

    if context:
        style_prompt = context
    else:
        inferred = None
        if (
            spec.get("emotion_inference")
            and state.config["emotion"].get("enabled")
            and state.emotion_client
        ):
            try:
                inferred = infer_emotion(
                    input_text, state.emotion_client, state.config["emotion"]
                )
            except Exception as e:
                print("emotion inference failed (continuing without): %s" % e, file=sys.stderr)
                inferred = None
        style_prompt = assemble_style_prompt(spec.get("base_style"), inferred)

    model = select_model(spec["kind"], state.config["mimo"])
    payload = build_mimo_request(
        input_text=input_text,
        style_prompt=style_prompt,
        voice_param=voice_param,
        model=model,
        audio_format=state.config["mimo"]["audio_format"],
    )
    wav_bytes = synthesize(state.client, payload)

    source_format = state.config["mimo"]["audio_format"]
    if needs_transcode(source_format, response_format):
        audio_bytes = transcode_audio(
            wav_bytes, response_format, state.config["audio"]["ffmpeg_path"]
        )
    else:
        audio_bytes = wav_bytes
    return audio_bytes, content_type_for(response_format)


def make_handler(state, proxy_key):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):
            return

        def _send_json(self, status, obj):
            data = json.dumps(obj).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            try:
                check_auth(self.headers.get("Authorization"), proxy_key)
            except ProxyError as e:
                self._send_json(e.status, {"error": {"message": str(e), "type": e.type_}})
                return
            if self.path in ("/", "/health"):
                self._send_json(200, {"status": "ok"})
            else:
                self._send_json(404, {"error": {"message": "not found", "type": "not_found"}})

        def do_POST(self):
            try:
                check_auth(self.headers.get("Authorization"), proxy_key)
            except ProxyError as e:
                self._send_json(e.status, {"error": {"message": str(e), "type": e.type_}})
                return
            if self.path != "/v1/audio/speech":
                self._send_json(404, {"error": {"message": "not found", "type": "not_found"}})
                return
            try:
                length = int(self.headers.get("Content-Length", 0) or 0)
                raw = self.rfile.read(length) if length else b""
                body = json.loads(raw or "{}")
            except Exception as e:
                self._send_json(
                    400,
                    {"error": {"message": "invalid JSON: %s" % e, "type": "invalid_request_error"}},
                )
                return
            try:
                audio_bytes, content_type = handle_speech(body, state)
            except ProxyError as e:
                self._send_json(e.status, {"error": {"message": str(e), "type": e.type_}})
                return
            except Exception as e:
                self._send_json(500, {"error": {"message": str(e), "type": "internal_error"}})
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(audio_bytes)))
            self.end_headers()
            self.wfile.write(audio_bytes)

    return Handler


def serve(state, host, port):
    proxy_key = resolve_proxy_api_key()
    if proxy_key:
        print("proxy API key configured — authentication required", file=sys.stderr)
    else:
        print("proxy API key NOT configured — running open (no auth)", file=sys.stderr)
    server = ThreadingHTTPServer((host, port), make_handler(state, proxy_key))
    print("mimo-tts-proxy listening on http://%s:%d/v1/audio/speech" % (host, port))
    server.serve_forever()
