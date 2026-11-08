"""Lightweight checks for the optional GTK desktop entry point."""
from pathlib import Path
import tomos_premiumgen.gui as gui


def test_gui_entrypoint_is_lazy():
    # Importing the module must not require a graphical session or PyGObject.
    assert callable(gui.run_gui)


def test_gui_module_has_security_warning():
    source = Path(gui.__file__).read_text(encoding="utf-8")
    assert "private signing key stays on this computer" in source
    assert "get_clipboard().set(code)" in source
