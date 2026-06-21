#!/usr/bin/env python3
"""End-to-end smoke test for the MIMO TTS proxy.

Starts the proxy server, sends two /v1/audio/speech requests (a cloned voice
with emotion inference, and a preset voice), verifies the responses are valid
audio, and prints the result. Requires MIMO_API_KEY in the environment.

Run with the project env python:
    /Users/pz/miniforge3/envs/mimo-tts-proxy/bin/python smoke_test.py
"""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:9880"


def wait_for_server(proc, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return False, "server process exited"
        try:
            with urllib.request.urlopen(BASE_URL + "/health", timeout=2) as r:
                if r.status == 200:
                    return True, None
        except Exception:
            time.sleep(0.5)
    return False, "timed out waiting for /health"


def speech(body):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + "/v1/audio/speech",
        data=data,
        headers={"Content-Type": "application/json", "Authorization": "Bearer smoke"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.status, r.headers.get("Content-Type"), r.read()


def verify_audio(path, fmt):
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        r = subprocess.run(
            [ffprobe, "-v", "error", "-show_format", path],
            capture_output=True, timeout=30,
        )
        return r.returncode == 0
    head = open(path, "rb").read(12)
    if fmt == "wav":
        return head[:4] == b"RIFF"
    if fmt == "mp3":
        return head[:3] == b"ID3" or (head[0] & 0xFF) == 0xFF
    return len(head) > 0


def main():
    if not os.environ.get("MIMO_API_KEY"):
        print("MIMO_API_KEY not set; cannot run smoke test", file=sys.stderr)
        return 1

    proc = subprocess.Popen(
        [sys.executable, "-m", "mimo_tts_proxy.app"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    try:
        ok, reason = wait_for_server(proc)
        if not ok:
            out = proc.stdout.read().decode("utf-8", "ignore") if proc.stdout else ""
            print(f"server did not come up ({reason}):\n{out}", file=sys.stderr)
            return 1
        print("server is up at", BASE_URL)

        # 1) cloned voice + emotion inference -> mp3
        status, ctype, audio = speech({
            "model": "tts-1",
            "input": "哇，今天天气真好，我们一起出去玩吧！",
            "voice": "zhuangfangyi",
            "response_format": "mp3",
        })
        assert status == 200, f"clone: status {status}"
        assert ctype == "audio/mpeg", f"clone: content-type {ctype}"
        assert len(audio) > 2000, f"clone: audio too small ({len(audio)} bytes)"
        path1 = "/tmp/mimo_proxy_smoke_clone.mp3"
        open(path1, "wb").write(audio)
        assert verify_audio(path1, "mp3"), "clone: invalid audio"
        print(f"[clone ] {len(audio)} bytes  {ctype}  -> {path1}")

        # 2) preset voice -> wav
        status, ctype, audio = speech({
            "model": "tts-1",
            "input": "你好，这是预置音色测试。",
            "voice": "bingtang",
            "response_format": "wav",
        })
        assert status == 200, f"preset: status {status}"
        assert ctype == "audio/wav", f"preset: content-type {ctype}"
        path2 = "/tmp/mimo_proxy_smoke_preset.wav"
        open(path2, "wb").write(audio)
        assert verify_audio(path2, "wav"), "preset: invalid audio"
        print(f"[preset] {len(audio)} bytes  {ctype}  -> {path2}")

        print("\nSMOKE TEST PASSED")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())
