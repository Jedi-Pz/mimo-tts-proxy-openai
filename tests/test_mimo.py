import unittest

from mimo_tts_proxy.mimo import build_mimo_request, select_model


class SelectModelTest(unittest.TestCase):
    def setUp(self):
        self.config = {
            "tts_model_clone": "mimo-v2.5-tts-voiceclone",
            "tts_model_preset": "mimo-v2.5-tts",
        }

    def test_clone_kind_selects_clone_model(self):
        self.assertEqual(select_model("clone", self.config), "mimo-v2.5-tts-voiceclone")

    def test_preset_kind_selects_preset_model(self):
        self.assertEqual(select_model("preset", self.config), "mimo-v2.5-tts")


class BuildMimoRequestTest(unittest.TestCase):
    def test_with_style_prompt_puts_style_in_user_and_text_in_assistant(self):
        payload = build_mimo_request(
            input_text="你好世界",
            style_prompt="用温柔的语气",
            voice_param="冰糖",
            model="mimo-v2.5-tts",
            audio_format="wav",
        )
        self.assertEqual(payload["model"], "mimo-v2.5-tts")
        self.assertEqual(
            payload["messages"],
            [
                {"role": "user", "content": "用温柔的语气"},
                {"role": "assistant", "content": "你好世界"},
            ],
        )
        self.assertEqual(payload["audio"], {"format": "wav", "voice": "冰糖"})

    def test_without_style_prompt_only_has_assistant_message(self):
        payload = build_mimo_request(
            input_text="你好世界",
            style_prompt=None,
            voice_param="冰糖",
            model="mimo-v2.5-tts",
            audio_format="wav",
        )
        self.assertEqual(
            payload["messages"],
            [{"role": "assistant", "content": "你好世界"}],
        )


if __name__ == "__main__":
    unittest.main()
