import unittest

from mimo_tts_proxy.voices import resolve_voice


class ResolveVoiceTest(unittest.TestCase):
    def test_registered_clone_voice_uses_clone_kind(self):
        registry = {
            "voices": {
                "zhuangfangyi": {
                    "sample_file": "/tmp/voice.wav",
                    "base_style": "温柔女声",
                    "emotion_inference": True,
                }
            }
        }
        spec = resolve_voice("zhuangfangyi", registry)
        self.assertEqual(spec["kind"], "clone")
        self.assertEqual(spec["sample_file"], "/tmp/voice.wav")
        self.assertEqual(spec["base_style"], "温柔女声")
        self.assertTrue(spec["emotion_inference"])

    def test_registered_preset_voice_uses_preset_kind(self):
        registry = {
            "voices": {
                "bingtang": {
                    "preset": "冰糖",
                    "base_style": "活泼少女",
                    "emotion_inference": False,
                }
            }
        }
        spec = resolve_voice("bingtang", registry)
        self.assertEqual(spec["kind"], "preset")
        self.assertEqual(spec["preset"], "冰糖")
        self.assertEqual(spec["base_style"], "活泼少女")
        self.assertFalse(spec["emotion_inference"])

    def test_unknown_voice_falls_back_to_preset_using_the_name(self):
        spec = resolve_voice("alloy", {"voices": {}})
        self.assertEqual(spec["kind"], "preset")
        self.assertEqual(spec["preset"], "alloy")
        self.assertFalse(spec["emotion_inference"])


if __name__ == "__main__":
    unittest.main()
