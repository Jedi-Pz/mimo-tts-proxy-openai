import unittest

from mimo_tts_proxy.emotion import assemble_style_prompt


class AssembleStylePromptTest(unittest.TestCase):
    def test_both_base_and_inferred_are_combined(self):
        result = assemble_style_prompt("温柔女声", "语调上扬，带着惊喜")
        self.assertIn("温柔女声", result)
        self.assertIn("语调上扬，带着惊喜", result)

    def test_only_base_style(self):
        self.assertEqual(assemble_style_prompt("温柔女声", None), "温柔女声")

    def test_only_inferred_emotion(self):
        self.assertEqual(assemble_style_prompt(None, "语调上扬"), "语调上扬")

    def test_neither_returns_none(self):
        self.assertIsNone(assemble_style_prompt(None, None))


if __name__ == "__main__":
    unittest.main()
