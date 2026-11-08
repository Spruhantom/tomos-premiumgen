import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
from tomos_premiumgen.cli import build_parser, main
from tomos_premiumgen.licence import generate_keypair

class OfflineCliTests(unittest.TestCase):
    def test_online_commands_are_not_available(self):
        parser = build_parser()
        for args in (["generate"], ["register"]):
            with self.subTest(args=args), self.assertRaises(SystemExit):
                parser.parse_args(args)

    def test_offline_licence_command_issues_json_and_qr(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            private, public = root / "private.pem", root / "public.pem"
            generate_keypair(private, public)
            output = root / "licence.json"
            args = ["tomos-premiumgen", "issue-offline", "--private-key", str(private),
                    "--device-id", "123e4567-e89b-12d3-a456-426614174000", "--output", str(output)]
            with patch.object(sys, "argv", args):
                self.assertEqual(main(), 0)
            self.assertTrue(output.is_file())
            self.assertTrue(output.with_suffix(".qr.png").is_file())

if __name__ == "__main__":
    unittest.main()
