import unittest
from dataclasses import replace

from app.config import settings


class SettingsTests(unittest.TestCase):
    def test_empty_cors_falls_back_to_localhost_not_wildcard(self):
        configured = replace(settings, cors_origin="")
        self.assertEqual(configured.cors_origins, ("http://localhost:3000",))

    def test_multiple_explicit_origins_are_trimmed(self):
        configured = replace(
            settings,
            cors_origin="https://game.example, https://admin.example ",
        )
        self.assertEqual(
            configured.cors_origins,
            ("https://game.example", "https://admin.example"),
        )


if __name__ == "__main__":
    unittest.main()
