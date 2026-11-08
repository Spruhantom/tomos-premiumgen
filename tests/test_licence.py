import tempfile
import unittest
from pathlib import Path

from tomos_premiumgen.licence import FEATURES, generate_keypair, issue_licence, verify_licence, write_offline_licence_qr
from tomos_premiumgen.offline import issue_offline_licence

class LicenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.private = root / "private.pem"
        self.public = root / "public.pem"
        generate_keypair(self.private, self.public)

    def tearDown(self):
        self.temp.cleanup()

    def test_signed_lifetime_licence_has_expected_features(self):
        licence = issue_licence(self.private, "test-customer")
        self.assertTrue(verify_licence(self.public, licence))
        self.assertEqual(licence["payload"]["licence_type"], "lifetime")
        self.assertEqual(licence["payload"]["features"], list(FEATURES))

    def test_offline_licence_is_device_bound_and_signed(self):
        device = "123e4567-e89b-12d3-a456-426614174000"
        licence = issue_offline_licence(self.private, device)
        self.assertTrue(verify_licence(self.public, licence))
        self.assertEqual(licence["payload"]["device_id"], device)

    def test_offline_qr_contains_complete_signed_document(self):
        licence = issue_offline_licence(self.private, "123e4567-e89b-12d3-a456-426614174000")
        output = Path(self.temp.name) / "private" / "offline.qr.png"
        write_offline_licence_qr(licence, output)
        self.assertTrue(output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)

    def test_tampered_payload_fails(self):
        licence = issue_licence(self.private)
        licence["payload"]["features"] = []
        self.assertFalse(verify_licence(self.public, licence))

    def test_wrong_public_key_fails(self):
        root = Path(self.temp.name)
        licence = issue_licence(self.private)
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
