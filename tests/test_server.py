import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from tomos_premiumgen import server
from tomos_premiumgen.licence import generate_activation_code


class RedemptionApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / "licences.sqlite3"
        self.db_patch = patch.object(server, "DB_PATH", self.database)
        self.db_patch.start()
        self.code = generate_activation_code()
        self.document = {"payload": {"licence_id": "test-licence"}, "signature": "test"}
        import hashlib
        import json
        digest = hashlib.sha256(self.code.encode("ascii")).hexdigest()
        with server.connect() as db:
            db.execute(
                "INSERT INTO licences (code_hash, licence_id, licence_json) VALUES (?, ?, ?)",
                (digest, "test-licence", json.dumps(self.document)),
            )

    def tearDown(self):
        self.db_patch.stop()
        self.temp.cleanup()

    def test_health_endpoint(self):
        self.assertEqual(server.health(), {"status": "ok"})

    def test_first_device_can_redeem(self):
        response = server.redeem(server.RedeemRequest(activation_code=self.code, device_id="device-identifier-001"))
        self.assertEqual(response.licence, self.document)

    def test_same_device_can_redeem_again(self):
        request = server.RedeemRequest(activation_code=self.code, device_id="device-identifier-001")
        server.redeem(request)
        self.assertEqual(server.redeem(request).licence, self.document)

    def test_different_device_is_rejected(self):
        server.redeem(server.RedeemRequest(activation_code=self.code, device_id="device-identifier-001"))
        with self.assertRaises(HTTPException) as caught:
            server.redeem(server.RedeemRequest(activation_code=self.code, device_id="device-identifier-002"))
        self.assertEqual(caught.exception.status_code, 409)

    def test_malformed_code_is_rejected(self):
        with self.assertRaises(HTTPException) as caught:
            server.redeem(server.RedeemRequest(activation_code=self.code + "é", device_id="device-identifier-001"))
        self.assertEqual(caught.exception.status_code, 400)

    def test_unknown_code_is_rejected(self):
        with self.assertRaises(HTTPException) as caught:
            server.redeem(server.RedeemRequest(activation_code=generate_activation_code(), device_id="device-identifier-001"))
        self.assertEqual(caught.exception.status_code, 404)

    def test_admin_import_endpoint_stays_disabled(self):
        with self.assertRaises(HTTPException) as caught:
            server.import_licence()
        self.assertEqual(caught.exception.status_code, 405)


if __name__ == "__main__":
    unittest.main()
