import os
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from mimo_tts_proxy.config import _read_dotenv_key, resolve_api_key


class ReadDotenvKeyTest(unittest.TestCase):
    def test_reads_key_from_env_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("MIMO_API_KEY=sk-test-key-123\n")
            f.flush()
            path = f.name
        try:
            self.assertEqual(_read_dotenv_key(path), "sk-test-key-123")
        finally:
            os.unlink(path)

    def test_handles_quoted_value(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write('MIMO_API_KEY="sk-quoted-key"\n')
            f.flush()
            path = f.name
        try:
            self.assertEqual(_read_dotenv_key(path), "sk-quoted-key")
        finally:
            os.unlink(path)

    def test_handles_single_quoted_value(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("MIMO_API_KEY='sk-single-quoted'\n")
            f.flush()
            path = f.name
        try:
            self.assertEqual(_read_dotenv_key(path), "sk-single-quoted")
        finally:
            os.unlink(path)

    def test_skips_comments_and_empty_lines(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("# This is a comment\n")
            f.write("\n")
            f.write("MIMO_API_KEY=sk-after-comment\n")
            f.flush()
            path = f.name
        try:
            self.assertEqual(_read_dotenv_key(path), "sk-after-comment")
        finally:
            os.unlink(path)

    def test_returns_none_when_key_missing(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("OTHER_VAR=value\n")
            f.flush()
            path = f.name
        try:
            self.assertIsNone(_read_dotenv_key(path))
        finally:
            os.unlink(path)

    def test_returns_none_when_file_absent(self):
        self.assertIsNone(_read_dotenv_key("/nonexistent/path/.env"))

    def test_returns_none_when_key_empty(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("MIMO_API_KEY=\n")
            f.flush()
            path = f.name
        try:
            self.assertIsNone(_read_dotenv_key(path))
        finally:
            os.unlink(path)


class ResolveApiKeyTest(unittest.TestCase):
    def test_exits_when_no_env_file_and_no_env_var(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("sys.exit") as mock_exit:
                resolve_api_key()
                mock_exit.assert_called_once_with(1)

    def test_exits_when_key_not_in_env_file_and_no_env_var(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("OTHER=value\n")
            f.flush()
            path = f.name
        try:
            with patch.dict(os.environ, {"MIMO_TTS_PROXY_DOTENV": path}, clear=True):
                with patch("sys.exit") as mock_exit:
                    resolve_api_key()
                    mock_exit.assert_called_once_with(1)
        finally:
            os.unlink(path)

    def test_returns_key_when_found_in_dotenv(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("MIMO_API_KEY=sk-found\n")
            f.flush()
            path = f.name
        try:
            with patch.dict(os.environ, {"MIMO_TTS_PROXY_DOTENV": path}, clear=True):
                self.assertEqual(resolve_api_key(), "sk-found")
        finally:
            os.unlink(path)

    def test_falls_back_to_env_var_when_no_dotenv(self):
        with patch.dict(os.environ, {"MIMO_API_KEY": "sk-from-env"}, clear=True):
            self.assertEqual(resolve_api_key(), "sk-from-env")

    def test_falls_back_to_default_dotenv_path(self):
        """When MIMO_TTS_PROXY_DOTENV is not set, reads from BASE_DIR/.env."""
        import mimo_tts_proxy.config as cfg

        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = os.path.join(tmpdir, ".env")
            with open(env_path, "w") as f:
                f.write("MIMO_API_KEY=sk-default-path\n")
            with patch.dict(os.environ, {}, clear=True):
                with patch.object(cfg, "BASE_DIR", Path(tmpdir)):
                    self.assertEqual(resolve_api_key(), "sk-default-path")


if __name__ == "__main__":
    unittest.main()
