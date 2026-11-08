import tempfile
import unittest
import uuid
from pathlib import Path

from tomos_premiumgen.licence import generate_keypair, verify_licence
from tomos_premiumgen.offline import issue_offline_licence


class OfflineLicenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.private = root / "private.pem"
        self.public = root / "public.pem"
        generate_keypair(self.private, self.public)

    def tearDown(self):
        self.temp.cleanup()

    def test_offline_licence_is_signed_and_bound_to_device_uuid(self):
        device_id = str(uuid.uuid4())
        licence = issue_offline_licence(self.private, device_id, "offline-test")
        self.assertTrue(verify_licence(self.public, licence))
        self.assertEqual(licence["payload"]["device_id"], device_id)
        self.assertEqual(licence["payload"]["licence_type"], "lifetime")

    def test_invalid_device_id_is_rejected(self):
        with self.assertRaises(ValueError):
            issue_offline_licence(self.private, "not-a-device-id")

    def test_device_binding_is_inside_signed_payload(self):
        licence = issue_offline_licence(self.private, str(uuid.uuid4()))
        licence["payload"]["device_id"] = str(uuid.uuid4())
        self.assertFalse(verify_licence(self.public, licence))


if __name__ == "__main__":
    unittest.main()
