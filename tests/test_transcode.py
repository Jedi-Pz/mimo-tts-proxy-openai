import unittest

from mimo_tts_proxy.transcode import content_type_for, needs_transcode


class ContentTypeTest(unittest.TestCase):
    def test_mp3(self):
        self.assertEqual(content_type_for("mp3"), "audio/mpeg")

    def test_wav(self):
        self.assertEqual(content_type_for("wav"), "audio/wav")

    def test_opus(self):
        self.assertEqual(content_type_for("opus"), "audio/ogg")

    def test_unknown_defaults_to_octet_stream(self):
        self.assertEqual(content_type_for("xyz"), "application/octet-stream")


class NeedsTranscodeTest(unittest.TestCase):
    def test_wav_to_mp3_needs_transcode(self):
        self.assertTrue(needs_transcode("wav", "mp3"))

    def test_wav_to_wav_no_transcode(self):
        self.assertFalse(needs_transcode("wav", "wav"))

    def test_wav_to_none_no_transcode(self):
        self.assertFalse(needs_transcode("wav", None))


if __name__ == "__main__":
    unittest.main()
