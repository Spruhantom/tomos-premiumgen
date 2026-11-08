"""Lightweight checks for the optional GTK desktop entry point."""
from pathlib import Path
import unittest

import tomos_premiumgen.gui as gui


class GtkEntryPointTests(unittest.TestCase):
    def test_gui_entrypoint_is_lazy(self):
        # Importing the module must not require a graphical session or PyGObject.
        self.assertTrue(callable(gui.run_gui))

    def test_gui_module_has_security_warning_and_clipboard(self):
        source = Path(gui.__file__).read_text(encoding="utf-8")
        self.assertIn("private signing key stays on this computer", source)
        self.assertIn("self.get_clipboard().set(code)", source)

    def test_gui_uses_four_separate_guided_tasks(self):
        source = Path(gui.__file__).read_text(encoding="utf-8")
        for page in ("online", "offline", "verify", "keys"):
            with self.subTest(page=page):
                self.assertIn(`self.build_${page}_page()`, source)
                self.assertIn(`self.add_page_footer(page, "${page}"`, source)

    def test_online_and_offline_pages_have_separate_inputs(self):
        source = Path(gui.__file__).read_text(encoding="utf-8")
        self.assertIn('"device", "TomOS SIP device UUID"', source)
        self.assertIn('"customer", "Customer reference (optional)"', source)
        self.assertIn('"output", "Save licence as"', source)
        self.assertIn("Create activation code", source)
        self.assertIn("Create offline licence", source)

    def test_desktop_home_screen_does_not_show_all_form_fields(self):
        source = Path(gui.__file__).read_text(encoding="utf-8")
        home = source.split("def build_home(self)", 1)[1].split("def build_keys_page", 1)[0]
        self.assertNotIn("self.add_field(", home)
        self.assertIn("What would you like to do?", home)


if __name__ == "__main__":
    unittest.main()
