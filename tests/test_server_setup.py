"""Tests for the guided redemption-server setup helper."""
import tempfile
import unittest
from pathlib import Path

from tomos_premiumgen.server_setup import build_user_service, install_user_service


class ServerSetupTests(unittest.TestCase):
    def test_service_is_loopback_only_and_uses_selected_database_and_port(self):
        content = build_user_service(
            "/home/test user/data/licences.sqlite3",
            8123,
            "/home/test user/venv/bin/python",
        )
        self.assertIn("--host 127.0.0.1 --port 8123", content)
        self.assertIn('Environment="TOMOS_LICENCE_DB=/home/test user/data/licences.sqlite3"', content)
        self.assertIn('ExecStart="/home/test user/venv/bin/python" -m uvicorn', content)
        self.assertNotIn("--host 0.0.0.0", content)

    def test_invalid_ports_are_rejected(self):
        for port in (0, 65536, "not-a-port"):
            with self.subTest(port=port), self.assertRaises(ValueError):
                build_user_service("/tmp/licences.sqlite3", port, "/usr/bin/python3")

    def test_relative_database_path_is_rejected(self):
        with self.assertRaises(ValueError):
            build_user_service("licences.sqlite3", 8000, "/usr/bin/python3")

    def test_install_creates_private_unit_and_database_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            database = Path(temp) / "data" / "licences.sqlite3"
            service = install_user_service(
                database, 8000, home=home, python_executable="/usr/bin/python3"
            )
            self.assertTrue(service.is_file())
            self.assertEqual(service.stat().st_mode & 0o777, 0o600)
            self.assertEqual(service.parent.stat().st_mode & 0o777, 0o700)
            self.assertEqual(database.parent.stat().st_mode & 0o777, 0o700)
            self.assertIn("--host 127.0.0.1 --port 8000", service.read_text())

    def test_existing_unit_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            service = home / ".config/systemd/user/tomos-premiumgen.service"
            service.parent.mkdir(parents=True)
            service.write_text("administrator-managed unit\n")
            with self.assertRaises(FileExistsError):
                install_user_service(
                    Path(temp) / "db/licences.sqlite3",
                    8000,
                    home=home,
                    python_executable="/usr/bin/python3",
                )
            self.assertEqual(service.read_text(), "administrator-managed unit\n")


if __name__ == "__main__":
    unittest.main()
