import hashlib
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from tomos_premiumgen import server
from tomos_premiumgen.licence import (
    generate_activation_code,
    generate_keypair,
    issue_licence,
    verify_licence,
)


class RedemptionApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / "licences.sqlite3"
        self.db_patch = patch.object(server, "DB_PATH", self.database)
        self.db_patch.start()
        self.code = generate_activation_code()
        self.document = {"payload": {"licence_id": "test-licence"}, "signature": "test"}
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


    def test_database_file_is_owner_only(self):
        self.assertEqual(self.database.stat().st_mode & 0o777, 0o600)

    def test_concurrent_redemption_by_different_devices_has_one_winner(self):
        barrier = Barrier(3)

        def attempt(device_id):
            barrier.wait()
            try:
                server.redeem(server.RedeemRequest(
                    activation_code=self.code,
                    device_id=device_id,
                ))
                return 200
            except HTTPException as error:
                return error.status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(attempt, "device-race-test-0001")
            second = pool.submit(attempt, "device-race-test-0002")
            barrier.wait()
            results = [first.result(timeout=15), second.result(timeout=15)]

        self.assertCountEqual(results, [200, 409])

    def test_admin_import_endpoint_stays_disabled(self):
        with self.assertRaises(HTTPException) as caught:
            server.import_licence()
        self.assertEqual(caught.exception.status_code, 405)

    def test_real_signed_licence_survives_redemption_api(self):
        private_key = Path(self.temp.name) / "private.pem"
        public_key = Path(self.temp.name) / "public.pem"
        generate_keypair(private_key, public_key)
        code, signed_document = issue_licence(private_key, "integration-test")
        payload = signed_document["payload"]
        digest = hashlib.sha256(code.encode("ascii")).hexdigest()
        with server.connect() as db:
            db.execute(
                "INSERT INTO licences (code_hash, licence_id, licence_json) VALUES (?, ?, ?)",
                (digest, payload["licence_id"], json.dumps(signed_document)),
            )

        response = server.redeem(
            server.RedeemRequest(activation_code=code, device_id="android-installation-0001")
        )
        self.assertEqual(response.licence, signed_document)
        self.assertTrue(verify_licence(public_key, response.licence))
        self.assertEqual(response.licence["payload"]["features"], [
            "multiple_sip_accounts",
            "advanced_codec_controls",
            "encrypted_backup",
        ])


if __name__ == "__main__":
    unittest.main()
