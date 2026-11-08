"""Simple guided GTK 4 desktop interface for TomOS Premium administration.

Each task has its own short form. Cryptographic and licence operations reuse
the tested core modules; the CLI and Textual interface remain available.
"""
from __future__ import annotations

from pathlib import Path



def run_gui() -> None:
    """Launch the guided GTK 4 desktop application."""
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        from gi.repository import Gio, Gtk
    except (ImportError, ValueError) as error:
        raise RuntimeError(
            "GTK 4 Python bindings are missing. Re-run install.sh to install "
            "the distribution's python-gobject / python3-gi and GTK 4 packages."
        ) from error

    from .licence import (
        generate_keypair,
        read_json,
        verify_licence,
        write_json,
    )
    from .offline import issue_offline_licence

    config_dir = Path.home() / ".config" / "tomos-premiumgen"
    default_private = config_dir / "private.pem"
    default_public = config_dir / "public.pem"
    documents_dir = Path.home() / "Documents" / "TomOS Premium"

    app = Gtk.Application(application_id="uk.co.tomos.premiumgen")

    class PremiumWindow(Gtk.ApplicationWindow):
        def __init__(self, application: Gtk.Application):
            super().__init__(application=application, title="TomOS Premium")
            self.set_default_size(780, 680)
            self.set_resizable(True)
            self.entries: dict[str, dict[str, Gtk.Entry]] = {}
            self.status_labels: dict[str, Gtk.Label] = {}

            header = Gtk.HeaderBar()
            title = Gtk.Label(label="TomOS Premium")
            title.add_css_class("title")
            header.set_title_widget(title)
            self.set_titlebar(header)

            self.root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            self.set_child(self.root)

            self.stack = Gtk.Stack()
            self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
            self.stack.set_transition_duration(120)
            self.stack.set_hexpand(True)
            self.stack.set_vexpand(True)
            self.root.append(self.stack)

            self.build_home()
            self.build_keys_page()
            self.build_offline_page()
            self.build_verify_page()
            self.update_key_status()
            self.stack.set_visible_child_name("home")

        def make_page(self, name: str, title_text: str, description: str):
            page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            page.set_margin_top(28)
            page.set_margin_bottom(28)
            page.set_margin_start(32)
            page.set_margin_end(32)
            page.set_valign(Gtk.Align.START)

            back = Gtk.Button(label="←  Home")
            back.set_halign(Gtk.Align.START)
            back.add_css_class("flat")
            back.connect("clicked", lambda _button: self.show_page("home"))
            page.append(back)

            heading = Gtk.Label(label=title_text)
            heading.add_css_class("title-1")
            heading.set_halign(Gtk.Align.START)
            page.append(heading)

            detail = Gtk.Label(label=description)
            detail.add_css_class("dim-label")
            detail.set_wrap(True)
            detail.set_xalign(0)
            page.append(detail)

            grid = Gtk.Grid(column_spacing=12, row_spacing=12)
            grid.set_hexpand(True)
            page.append(grid)

            self.entries[name] = {}
            self.status_labels[name] = Gtk.Label(label="")
            self.status_labels[name].set_wrap(True)
            self.status_labels[name].set_selectable(True)
            self.status_labels[name].set_xalign(0)
            self.status_labels[name].add_css_class("card")
            self.status_labels[name].set_margin_top(4)
            self.status_labels[name].set_margin_bottom(4)

            return page, grid

        def add_field(
            self,
            page_name: str,
            grid: Gtk.Grid,
            row: int,
            key: str,
            label_text: str,
            default: str = "",
            chooser: str | None = None,
            placeholder: str = "",
        ) -> Gtk.Entry:
            label = Gtk.Label(label=label_text)
            label.set_halign(Gtk.Align.START)
            label.set_valign(Gtk.Align.CENTER)
            label.set_wrap(True)
            grid.attach(label, 0, row, 1, 1)

            entry = Gtk.Entry()
            entry.set_hexpand(True)
            entry.set_text(str(default))
            if placeholder:
                entry.set_placeholder_text(placeholder)
            self.entries[page_name][key] = entry
            grid.attach(entry, 1, row, 1, 1)

            if chooser:
                browse = Gtk.Button(label="Browse…")
                browse.connect("clicked", self.choose_file, page_name, key, chooser)
                grid.attach(browse, 2, row, 1, 1)

            return entry

        def add_page_footer(self, page, page_name: str, action_text: str, callback) -> None:
            page.append(self.status_labels[page_name])
            action = Gtk.Button(label=action_text)
            action.add_css_class("suggested-action")
            action.set_halign(Gtk.Align.START)
            action.connect("clicked", callback)
            page.append(action)
            self.stack.add_named(page, page_name)

        def build_home(self) -> None:
            page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
            page.set_margin_top(34)
            page.set_margin_bottom(30)
            page.set_margin_start(34)
            page.set_margin_end(34)

            heading = Gtk.Label(label="What would you like to do?")
            heading.add_css_class("title-1")
            heading.set_halign(Gtk.Align.START)
            page.append(heading)

            intro = Gtk.Label(
                label="Choose a task. You’ll only see the information needed for that job."
            )
            intro.set_wrap(True)
            intro.set_xalign(0)
            intro.add_css_class("dim-label")
            page.append(intro)

            self.key_status = Gtk.Label(label="")
            self.key_status.set_xalign(0)
            self.key_status.set_wrap(True)
            self.key_status.add_css_class("card")
            page.append(self.key_status)

            tasks = [
                (
                    "Issue offline licence",
                    "Create a licence tied to one TomOS SIP device UUID.",
                    "offline",
                ),
                (
                    "Verify a licence",
                    "Check that a licence has a valid signature and contents.",
                    "verify",
                ),
                (
                    "Signing keys",
                    "Create or check the keys used to sign and verify licences.",
                    "keys",
                ),

            ]
            for title_text, description, destination in tasks:
                button = Gtk.Button()
                button.set_hexpand(True)
                button.set_halign(Gtk.Align.FILL)
                button_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
                button_box.set_margin_top(12)
                button_box.set_margin_bottom(12)
                button_box.set_margin_start(14)
                button_box.set_margin_end(14)
                title_label = Gtk.Label(label=title_text)
                title_label.add_css_class("heading")
                title_label.set_xalign(0)
                detail_label = Gtk.Label(label=description)
                detail_label.add_css_class("dim-label")
                detail_label.set_xalign(0)
                detail_label.set_wrap(True)
                button_box.append(title_label)
                button_box.append(detail_label)
                button.set_child(button_box)
                button.connect("clicked", lambda _button, target=destination: self.show_page(target))
                page.append(button)

            security = Gtk.Label(
                label="Security: the private signing key stays on this computer. "
                      "Send activation codes and QR images to customers privately."
            )
            security.set_wrap(True)
            security.set_xalign(0)
            security.add_css_class("dim-label")
            page.append(security)

            self.stack.add_named(page, "home")

        def build_keys_page(self) -> None:
            page, grid = self.make_page(
                "keys",
                "Signing keys",
                "Create the signing key pair once. Keep the private key secret and safe; "
                "the public key can be shared with TomOS SIP for licence verification.",
            )
            self.add_field(
                "keys", grid, 0, "private", "Private signing key",
                str(default_private), "save",
            )
            self.add_field(
                "keys", grid, 1, "public", "Public verification key",
                str(default_public), "save",
            )
            self.add_page_footer(page, "keys", "Create signing keys", self.on_keygen)

        def build_offline_page(self) -> None:
            page, grid = self.make_page(
                "offline",
                "Issue offline licence",
                "Create a signed licence for one device. "
                "Enter the device UUID displayed by TomOS SIP.",
            )
            self.add_field(
                "offline", grid, 0, "private", "Private signing key",
                str(default_private), "open",
            )
            self.add_field(
                "offline", grid, 1, "device", "TomOS SIP device UUID",
                placeholder="Paste the UUID from the customer's app",
            )
            self.add_field(
                "offline", grid, 2, "customer", "Customer reference (optional)",
                placeholder="For example, an order reference",
            )
            self.add_field(
                "offline", grid, 3, "output", "Save licence as",
                str(documents_dir / "offline-licence.json"), "save",
            )
            self.add_page_footer(page, "offline", "Create offline licence", self.on_offline)

        def build_verify_page(self) -> None:
            page, grid = self.make_page(
                "verify",
                "Verify a licence",
                "Choose the public verification key and the licence file. "
                "A valid result confirms the signature and supported licence contents.",
            )
            self.add_field(
                "verify", grid, 0, "public", "Public verification key",
                str(default_public), "open",
            )
            self.add_field(
                "verify", grid, 1, "licence", "Licence file",
                str(documents_dir / "online-licence.json"), "open",
            )
            self.add_page_footer(page, "verify", "Verify licence", self.on_verify)

        def show_page(self, name: str) -> None:
            self.stack.set_visible_child_name(name)
            if name == "home":
                self.update_key_status()

        def update_key_status(self) -> None:
            private_exists = default_private.is_file()
            public_exists = default_public.is_file()
            if private_exists and public_exists:
                status = "Signing keys found — ready to create licences."
            elif private_exists or public_exists:
                status = "Only one signing key was found. Check the key paths before creating licences."
            else:
                status = "Signing keys not set up yet. Start with “Signing keys”."
            self.key_status.set_text(status)

        def get_value(self, page_name: str, key: str) -> str:
            return self.entries[page_name][key].get_text().strip()

        def get_path(self, page_name: str, key: str) -> Path:
            return Path(self.get_value(page_name, key)).expanduser()

        def report(self, page_name: str, message: str, error: bool = False) -> None:
            label = self.status_labels[page_name]
            label.set_text(message)
            label.remove_css_class("error")
            if error:
                label.add_css_class("error")

        def choose_file(self, _button, page_name: str, key: str, action: str) -> None:
            entry = self.entries[page_name][key]
            current = Path(entry.get_text()).expanduser()
            save = action == "save"
            chooser = Gtk.FileChooserNative.new(
                "Choose file",
                self,
                Gtk.FileChooserAction.SAVE if save else Gtk.FileChooserAction.OPEN,
                "_Save" if save else "_Open",
                "_Cancel",
            )
            if current.parent.exists():
                chooser.set_current_folder(Gio.File.new_for_path(str(current.parent)))
            if save:
                chooser.set_current_name(current.name)

            def selected(dialog, response):
                if response == Gtk.ResponseType.ACCEPT:
                    chosen = dialog.get_file()
                    if chosen and chosen.get_path():
                        entry.set_text(chosen.get_path())
                dialog.destroy()

            chooser.connect("response", selected)
            chooser.show()

        def run_action(self, page_name: str, operation) -> None:
            try:
                self.report(page_name, operation())
            except (OSError, ValueError, RuntimeError) as error:
                self.report(page_name, f"Could not complete this task: {error}", error=True)

        def on_keygen(self, _button) -> None:
            def operation():
                private = self.get_path("keys", "private")
                public = self.get_path("keys", "public")
                generate_keypair(private, public)
                self.update_key_status()
                return (
                    "Signing keys created successfully.\n"
                    f"Private key: {private} (keep secret; permissions 0600).\n"
                    f"Public key: {public}"
                )
            self.run_action("keys", operation)

        def on_offline(self, _button) -> None:
            def operation():
                private = self.get_path("offline", "private")
                if not private.is_file():
                    raise FileNotFoundError(f"Private signing key not found: {private}")
                device_id = self.get_value("offline", "device")
                if not device_id:
                    raise ValueError("Enter the device UUID shown in TomOS SIP.")
                output = self.get_path("offline", "output")
                document = issue_offline_licence(
                    private, device_id, self.get_value("offline", "customer")
                )
                write_json(output, document)
                qr = output.with_suffix(".qr.png")
                from .licence import write_offline_licence_qr
                write_offline_licence_qr(document, qr)
                return (
                    "OFFLINE LICENCE CREATED\n"
                    f"Device: {document['payload']['device_id']}\n"
                    f"Signed licence: {output}\nQR image: {qr}\n\n"
                    "Transfer either file securely to the matching device."
                )
            self.run_action("offline", operation)

        def on_verify(self, _button) -> None:
            def operation():
                public = self.get_path("verify", "public")
                licence = self.get_path("verify", "licence")
                if not public.is_file():
                    raise FileNotFoundError(f"Public verification key not found: {public}")
                if not licence.is_file():
                    raise FileNotFoundError(f"Licence file not found: {licence}")
                if not verify_licence(public, read_json(licence)):
                    raise ValueError("INVALID — the signature or licence contents did not validate.")
                return "VALID — the signature and licence contents are correct."

            self.run_action("verify", operation)

    def on_activate(application: Gtk.Application) -> None:
        window = application.props.active_window
        if window is None:
            PremiumWindow(application).present()

    app.connect("activate", on_activate)
    app.run(None)
