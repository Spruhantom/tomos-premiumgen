import contextlib
import hashlib
import io
import json
import tempfile
import unittest
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from tomos_premiumgen import server
from tomos_premiumgen.licence import (
    generate_activation_code,
    generate_keypair,
    issue_licence,
    verify_licence,
    write_json,
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


    def test_server_command_binds_to_loopback_by_default(self):
        with patch.object(sys, "argv", ["tomos-premiumgen-server"]), patch("uvicorn.run") as run:
            self.assertEqual(server.main(), 0)
        run.assert_called_once_with(
            "tomos_premiumgen.server:app",
            host="127.0.0.1",
            port=8000,
            log_level="info",
        )

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


    def test_database_symlink_destination_is_rejected(self):
        target = Path(self.temp.name) / "target.sqlite3"
        target.write_bytes(b"do-not-touch")
        link = Path(self.temp.name) / "linked.sqlite3"
        link.symlink_to(target)
        with patch.object(server, "DB_PATH", link):
            with self.assertRaises(OSError):
                server.connect()
        self.assertEqual(target.read_bytes(), b"do-not-touch")

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


    def test_complete_cli_to_http_redemption_first_repeat_and_other_device(self):
        private_key = Path(self.temp.name) / "issuer-private.pem"
        public_key = Path(self.temp.name) / "issuer-public.pem"
        licence_file = Path(self.temp.name) / "issued-licence.json"
        database = Path(self.temp.name) / "registered" / "licences.sqlite3"
        generate_keypair(private_key, public_key)
        code, document = issue_licence(private_key, "cross-component-integration")
        write_json(licence_file, document)

        output = io.StringIO()
        with patch.object(sys, "argv", [
            "tomos-premiumgen", "register",
            "--public-key", str(public_key),
            "--licence", str(licence_file),
            "--activation-code", code,
            "--database", str(database),
        ]), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            self.assertEqual(main(), 0)

        with patch.object(server, "DB_PATH", database):
            client = TestClient(server.app)
            first = client.post("/v1/redeem", json={
                "activation_code": code,
                "device_id": "android-installation-0001",
            })
            self.assertEqual(first.status_code, 200)
            returned = first.json()["licence"]
            self.assertEqual(returned, document)
            self.assertTrue(verify_licence(public_key, returned))

            repeated = client.post("/v1/redeem", json={
                "activation_code": code,
                "device_id": "android-installation-0001",
            })
            self.assertEqual(repeated.status_code, 200)
            self.assertEqual(repeated.json()["licence"], document)

            other_device = client.post("/v1/redeem", json={
                "activation_code": code,
                "device_id": "android-installation-0002",
            })
            self.assertEqual(other_device.status_code, 409)
            self.assertIn("another device", other_device.json()["detail"])

    def test_http_endpoint_rejects_unknown_and_malformed_codes(self):
        with patch.object(server, "DB_PATH", self.database):
            client = TestClient(server.app)
            unknown = client.post("/v1/redeem", json={
                "activation_code": generate_activation_code(),
                "device_id": "android-installation-0003",
            })
            self.assertEqual(unknown.status_code, 404)
            malformed = client.post("/v1/redeem", json={
                "activation_code": "not-a-tomos-code",
                "device_id": "android-installation-0003",
            })
            self.assertEqual(malformed.status_code, 400)

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
