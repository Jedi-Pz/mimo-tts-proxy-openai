"""HTTP server implementing the OpenAI /v1/audio/speech endpoint."""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .emotion import assemble_style_prompt, infer_emotion
from .mimo import build_mimo_request, select_model, synthesize
from .transcode import content_type_for, needs_transcode, transcode_audio
from .voices import build_voice_param, resolve_voice


class ProxyError(Exception):
    def __init__(self, message, status=400, type_="invalid_request_error"):
        super().__init__(message)
        self.status = status
        self.type_ = type_


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


def make_handler(state):
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
            if self.path in ("/", "/health"):
                self._send_json(200, {"status": "ok"})
            else:
                self._send_json(404, {"error": {"message": "not found", "type": "not_found"}})

        def do_POST(self):
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
    server = ThreadingHTTPServer((host, port), make_handler(state))
    print("mimo-tts-proxy listening on http://%s:%d/v1/audio/speech" % (host, port))
    server.serve_forever()
