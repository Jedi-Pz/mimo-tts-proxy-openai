"""MIMO TTS request building and synthesis.

MIMO exposes TTS through the OpenAI-compatible chat completions endpoint:
the text to synthesize goes in an `assistant` message, optional style
direction in a preceding `user` message, and the voice (a preset name or a
data URL of a clone sample) via the `audio.voice` field. The response carries
base64 WAV in message.audio.data.
"""
import base64


def select_model(kind, mimo_config):
    if kind == "clone":
        return mimo_config["tts_model_clone"]
    return mimo_config["tts_model_preset"]


def build_mimo_request(input_text, style_prompt, voice_param, model, audio_format):
    messages = []
    if style_prompt:
        messages.append({"role": "user", "content": style_prompt})
    messages.append({"role": "assistant", "content": input_text})
    return {
        "model": model,
        "messages": messages,
        "audio": {"format": audio_format, "voice": voice_param},
    }


def synthesize(client, payload):
    completion = client.chat.completions.create(
        model=payload["model"],
        messages=payload["messages"],
        audio=payload["audio"],
    )
    message = completion.choices[0].message
    audio = getattr(message, "audio", None)
    if audio is None or not getattr(audio, "data", None):
        raise RuntimeError("MIMO returned no audio data")
    return base64.b64decode(audio.data)
