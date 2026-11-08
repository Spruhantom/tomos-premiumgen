import unittest

from tomos_premiumgen.cli import build_parser
from tomos_premiumgen.tui import PremiumGeneratorApp


class TerminalInterfaceTests(unittest.TestCase):
    def test_tui_is_available_as_cli_command(self):
        args = build_parser().parse_args(["tui"])
        self.assertEqual(args.command, "tui")

    def test_tui_app_has_expected_actions(self):
        app = PremiumGeneratorApp()
        self.assertEqual(app.title, "TomOS SIP Premium Generator")


if __name__ == "__main__":
    unittest.main()
