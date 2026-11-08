"""Checks for the offline-only GTK desktop entry point."""
from pathlib import Path
import unittest
import tomos_premiumgen.gui as gui

class GtkEntryPointTests(unittest.TestCase):
    def test_gui_entrypoint_is_lazy(self):
        self.assertTrue(callable(gui.run_gui))

    def test_gui_module_warns_about_private_signing_key(self):
        source = Path(gui.__file__).read_text(encoding="utf-8")
        self.assertIn("private signing key stays on this computer", source)

    def test_gui_exposes_only_offline_licence_tasks(self):
        source = Path(gui.__file__).read_text(encoding="utf-8")
        self.assertIn("self.build_offline_page()", source)
        self.assertIn("self.build_verify_page()", source)
        self.assertIn("self.build_keys_page()", source)
        self.assertNotIn("build_online_page", source)
        self.assertNotIn("build_server_page", source)
        self.assertNotIn("install_user_service", source)

    def test_offline_page_uses_device_uuid_and_exports_qr(self):
        source = Path(gui.__file__).read_text(encoding="utf-8")
        self.assertIn('"device", "TomOS SIP device UUID"', source)
        self.assertIn("issue_offline_licence(", source)
        self.assertIn("write_offline_licence_qr(", source)
        self.assertIn("Create offline licence", source)

    def test_gui_has_no_online_activation_or_server_setup(self):
        source = Path(gui.__file__).read_text(encoding="utf-8").lower()
        self.assertNotIn("redemption server", source)
        self.assertNotIn("activation code", source)
        self.assertNotIn("systemctl --user enable --now", source)

if __name__ == "__main__":
    unittest.main()
