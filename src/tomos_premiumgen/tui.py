"""Interactive Textual interface for administering TomOS Premium licences."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Label, Static

from .licence import generate_keypair, read_json, verify_licence, write_activation_qr, write_json, issue_licence
from .offline import issue_offline_licence


class PremiumGeneratorApp(App[None]):
    """A local TUI; private signing keys never leave this machine."""

    TITLE = "TomOS SIP Premium Generator"
    SUB_TITLE = "Ed25519 lifetime licence administration"
    CSS = """
    Screen { padding: 1 2; }
    #form { height: auto; border: round $accent; padding: 1 2; }
    .field-label { margin-top: 1; color: $text-muted; }
    Input { margin-bottom: 0; }
    #actions { height: auto; margin-top: 1; }
    #actions Button { margin-right: 1; }
    #status { border: round $primary; padding: 1; height: 5; margin-top: 1; }
    #warning { color: $warning; margin: 1 0; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="form"):
            yield Label("Signing key (private key stays on this computer)", classes="field-label")
            yield Input(str(Path.home() / ".config/tomos-premiumgen/private.pem"), id="private")
            yield Label("Public verification key", classes="field-label")
            yield Input(str(Path.home() / ".config/tomos-premiumgen/public.pem"), id="public")
            yield Label("Customer reference (optional; avoid personal data)", classes="field-label")
            yield Input(placeholder="Order reference", id="customer")
            yield Label("Device UUID — required for offline licence", classes="field-label")
            yield Input(placeholder="123e4567-e89b-12d3-a456-426614174000", id="device")
            yield Label("Output licence file", classes="field-label")
            yield Input("./licences/customer.json", id="output")
            yield Label("Licence file to verify", classes="field-label")
            yield Input("./licences/customer.json", id="licence")
            yield Static("Keep the private key and generated activation credentials confidential.", id="warning")
        with Horizontal(id="actions"):
            yield Button("Generate keys", id="keygen", variant="primary")
            yield Button("Online licence", id="online")
            yield Button("Offline licence", id="offline")
            yield Button("Verify licence", id="verify")
            yield Button("Quit", id="quit", variant="error")
        yield Static("Choose an action. Results will appear here.", id="status")
        yield Footer()

    def value(self, widget_id: str) -> str:
        return self.query_one(f"#{widget_id}", Input).value.strip()

    def report(self, message: str) -> None:
        self.query_one("#status", Static).update(message)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        action = event.button.id
        if action == "quit":
            self.exit()
            return
        private = Path(self.value("private")).expanduser()
        public = Path(self.value("public")).expanduser()
        output = Path(self.value("output")).expanduser()
        customer = self.value("customer")
        try:
            if action == "keygen":
                generate_keypair(private, public)
                self.report(f"Keys created. Private key: {private} (keep secret; mode 0600). Public key: {public}")
            elif action == "online":
                if not private.is_file():
                    raise FileNotFoundError(f"Private key not found: {private}")
                code, document = issue_licence(private, customer)
                write_json(output, document)
                qr = output.with_suffix(".qr.png")
                write_activation_qr(code, qr)
                self.report(f"Online lifetime licence created: {output}\nActivation code (deliver privately): {code}\nPrivate QR image: {qr}")
            elif action == "offline":
                if not private.is_file():
                    raise FileNotFoundError(f"Private key not found: {private}")
                if not self.value("device"):
                    raise ValueError("Enter the device UUID shown in TomOS SIP.")
                document = issue_offline_licence(private, self.value("device"), customer)
                write_json(output, document)
                self.report(f"Device-bound offline licence created: {output}\nDevice: {document['payload']['device_id']}\nTransfer the file securely to this device.")
            elif action == "verify":
                if not public.is_file():
                    raise FileNotFoundError(f"Public key not found: {public}")
                licence_path = Path(self.value("licence")).expanduser()
                valid = verify_licence(public, read_json(licence_path))
                self.report("VALID: signed TomOS SIP Premium lifetime licence." if valid else "INVALID: signature or licence contents did not validate.")
            else:
                self.report("Unknown action.")
        except (OSError, ValueError) as error:
            self.report(f"Error: {error}")


def run_tui() -> None:
    """Launch the interactive terminal application."""
    PremiumGeneratorApp().run()
