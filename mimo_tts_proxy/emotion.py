"""Emotion inference and style prompt assembly.

assemble_style_prompt is pure: it layers a per-line inferred emotion on top
of a voice's base style, returning None when there is nothing to direct the
TTS with (in which case no user message is sent to MIMO). infer_emotion
calls an LLM to produce that per-line emotion direction.
"""

_EMOTION_PROMPT = (
    "你是语音合成情绪导演。阅读下面这段将要被朗读的文字，用一句简短的中文描述"
    "该用什么语气和情绪来朗读（语调、语速、情绪色彩等）。只输出这一句描述，"
    "不要朗读原文，不要解释。\n\n文字：\n"
)


def assemble_style_prompt(base_style, inferred_emotion):
    parts = [p for p in (base_style, inferred_emotion) if p]
    if not parts:
        return None
    return "\n".join(parts)


def infer_emotion(text, client, emotion_config):
    if not emotion_config.get("enabled"):
        return None
    max_chars = emotion_config.get("max_input_chars", 1000)
    resp = client.chat.completions.create(
        model=emotion_config["model"],
        messages=[{"role": "user", "content": _EMOTION_PROMPT + text[:max_chars]}],
    )
    return (resp.choices[0].message.content or "").strip() or None
