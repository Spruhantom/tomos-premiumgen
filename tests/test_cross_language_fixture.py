import json
import tempfile
import unittest
from pathlib import Path

from tomos_premiumgen.licence import verify_licence


FIXTURES = Path(__file__).parent / "fixtures"


class CrossLanguageFixtureTests(unittest.TestCase):
    def test_android_verifier_accepts_python_issued_offline_fixture(self):
        licence = json.loads((FIXTURES / "android_offline_licence.json").read_text(encoding="utf-8"))
        public_key = FIXTURES / "android_offline_public.pem"

        self.assertTrue(verify_licence(public_key, licence))
        self.assertEqual(
            licence["payload"]["device_id"],
            "123e4567-e89b-12d3-a456-426614174001",
        )

    def test_android_fixture_rejects_tampered_signature(self):
        licence = json.loads((FIXTURES / "android_offline_licence.json").read_text(encoding="utf-8"))
        licence["signature"] = "A" * 88
        public_key = FIXTURES / "android_offline_public.pem"

        self.assertFalse(verify_licence(public_key, licence))


if __name__ == "__main__":
    unittest.main()
