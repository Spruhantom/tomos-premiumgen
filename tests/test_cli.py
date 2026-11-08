import contextlib
import io
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tomos_premiumgen.cli import main
from tomos_premiumgen.licence import generate_keypair, issue_licence, write_json


class LicenceImportCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.private = root / "private.pem"
        self.public = root / "public.pem"
        self.licence = root / "licence.json"
        self.database = root / "private" / "licences.sqlite3"
        generate_keypair(self.private, self.public)
        self.code, self.document = issue_licence(self.private, "cli-import-test")
        write_json(self.licence, self.document)

    def tearDown(self):
        self.temp.cleanup()

    def run_register(self, code=None):
        args = [
            "tomos-premiumgen", "register",
            "--public-key", str(self.public),
            "--licence", str(self.licence),
            "--activation-code", code or self.code,
            "--database", str(self.database),
        ]
        output = io.StringIO()
        with patch.object(sys, "argv", args), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            result = main()
        return result, output.getvalue()

    def test_register_creates_owner_only_database(self):
        result, _ = self.run_register()
        self.assertEqual(result, 0)
        self.assertEqual(self.database.stat().st_mode & 0o777, 0o600)
        with sqlite3.connect(self.database) as db:
            row = db.execute("SELECT licence_id FROM licences").fetchone()
        self.assertEqual(row[0], self.document["payload"]["licence_id"])

    def test_duplicate_registration_is_rejected(self):
        self.assertEqual(self.run_register()[0], 0)
        result, output = self.run_register()
        self.assertEqual(result, 1)
        self.assertIn("already been registered", output)

    def test_invalid_signature_is_not_imported(self):
        self.document["payload"]["customer_reference"] = "tampered"
        write_json(self.licence, self.document)
        result, output = self.run_register()
        self.assertEqual(result, 1)
        self.assertIn("invalid", output.lower())
        self.assertFalse(self.database.exists())


if __name__ == "__main__":
    unittest.main()
