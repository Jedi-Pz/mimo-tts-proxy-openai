import json
import unittest
from unittest.mock import patch, MagicMock

from mimo_tts_proxy.server import check_auth, ProxyError


class CheckAuthTest(unittest.TestCase):
    def test_passes_when_no_proxy_key_configured(self):
        """If no PROXY_API_KEY is set, all requests pass."""
        check_auth("anything", None)

    def test_passes_when_bearer_matches(self):
        check_auth("Bearer my-secret", "my-secret")
        check_auth("bearer my-secret", "my-secret")

    def test_raises_when_no_authorization_header(self):
        with self.assertRaises(ProxyError) as ctx:
            check_auth(None, "required-key")
        self.assertEqual(ctx.exception.status, 401)
        self.assertIn("missing", str(ctx.exception).lower())

    def test_raises_when_empty_authorization_header(self):
        with self.assertRaises(ProxyError) as ctx:
            check_auth("", "required-key")
        self.assertEqual(ctx.exception.status, 401)

    def test_raises_when_not_bearer_format(self):
        with self.assertRaises(ProxyError) as ctx:
            check_auth("Basic dXNlcjpwYXNz", "required-key")
        self.assertEqual(ctx.exception.status, 401)

    def test_raises_when_bearer_key_mismatch(self):
        with self.assertRaises(ProxyError) as ctx:
            check_auth("Bearer wrong-key", "correct-key")
        self.assertEqual(ctx.exception.status, 401)
        self.assertIn("invalid", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
