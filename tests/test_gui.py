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


if __name__ == "__main__":
    unittest.main()
