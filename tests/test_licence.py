import tempfile
import unittest
from pathlib import Path

from tomos_premiumgen.licence import FEATURES, activation_code_matches, generate_keypair, issue_licence, verify_licence


class LicenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.private = root / "private.pem"
        self.public = root / "public.pem"
        generate_keypair(self.private, self.public)

    def tearDown(self):
        self.temp.cleanup()

    def test_lifetime_licence_signature_and_features(self):
        code, licence = issue_licence(self.private, "test-customer")
        self.assertTrue(code.startswith("TOMOS-PREM-"))
        self.assertTrue(verify_licence(self.public, licence))
        self.assertEqual(licence["payload"]["licence_type"], "lifetime")
        self.assertEqual(licence["payload"]["features"], list(FEATURES))

    def test_activation_code_matches_only_its_licence(self):
        code, licence = issue_licence(self.private)
        self.assertTrue(activation_code_matches(code, licence))
        self.assertTrue(activation_code_matches(code.lower(), licence))
        self.assertTrue(activation_code_matches("  " + code.replace("-", " - ") + "  ", licence))
        self.assertFalse(activation_code_matches("TOMOS-PREM-AAAA-BBBB-CCCC-DDDD", licence))

    def test_activation_code_rejects_malformed_and_unicode_input(self):
        code, licence = issue_licence(self.private)
        for invalid in (code + "!", code + "é", code.replace("-", ""), "TOMOS-PREM-0000-0000-0000-0000", None):
            with self.subTest(invalid=invalid):
                self.assertFalse(activation_code_matches(invalid, licence))

    def test_activation_code_rejects_malformed_document(self):
        code, licence = issue_licence(self.private)
        self.assertFalse(activation_code_matches(code, {}))
        self.assertFalse(activation_code_matches(code, {"payload": None}))

    def test_tampered_payload_fails(self):
        _, licence = issue_licence(self.private)
        licence["payload"]["features"] = []
        self.assertFalse(verify_licence(self.public, licence))

    def test_wrong_public_key_fails(self):
        root = Path(self.temp.name)
        _, licence = issue_licence(self.private)
        other_private, other_public = root / "other.pem", root / "other.pub"
        generate_keypair(other_private, other_public)
        self.assertFalse(verify_licence(other_public, licence))

    def test_private_key_permissions(self):
        self.assertEqual(self.private.stat().st_mode & 0o777, 0o600)

    def test_keygen_refuses_overwrite(self):
        with self.assertRaises(FileExistsError):
            generate_keypair(self.private, self.public)

    def test_key_paths_must_differ(self):
        with self.assertRaises(ValueError):
            generate_keypair(self.private, self.private)

    def test_customer_reference_limit(self):
        with self.assertRaises(ValueError):
            issue_licence(self.private, "x" * 121)


if __name__ == "__main__":
    unittest.main()
