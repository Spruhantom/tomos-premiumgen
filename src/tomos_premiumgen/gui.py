"""GTK 4 desktop interface for TomOS Premium licence administration.

The GTK bindings are provided by the host distribution (PyGObject); all
cryptographic and licence operations reuse the tested core modules.
"""
from __future__ import annotations

from pathlib import Path


def run_gui() -> None:
    """Launch the GTK 4 desktop application."""
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        from gi.repository import Gio, Gtk
    except (ImportError, ValueError) as error:
        raise RuntimeError(
            "GTK 4 Python bindings are missing. Re-run install.sh to install "
            "the distribution's python-gobject / python3-gi and GTK 4 packages."
        ) from error

    from .licence import generate_keypair, issue_licence, read_json, verify_licence, write_activation_qr, write_json
    from .offline import issue_offline_licence

    app = Gtk.Application(application_id="uk.co.tomos.premiumgen")

    class PremiumWindow(Gtk.ApplicationWindow):
        def __init__(self, application: Gtk.Application):
            super().__init__(application=application, title="TomOS Premium Code Generator")
            self.set_default_size(760, 650)
            self.set_resizable(True)

            root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
            root.set_margin_top(20)
            root.set_margin_bottom(20)
            root.set_margin_start(22)
            root.set_margin_end(22)
            self.set_child(root)

            heading = Gtk.Label(label="TomOS SIP Premium")
            heading.add_css_class("title-1")
            heading.set_halign(Gtk.Align.START)
            root.append(heading)
            subtitle = Gtk.Label(label="Lifetime licence administration · Ed25519 signing")
            subtitle.add_css_class("dim-label")
            subtitle.set_halign(Gtk.Align.START)
            root.append(subtitle)

            form = Gtk.Grid(column_spacing=10, row_spacing=10)
            form.set_hexpand(True)
            root.append(form)

            self.entries: dict[str, Gtk.Entry] = {}
            fields = [
                ("private", "Private signing key", str(Path.home() / ".config/tomos-premiumgen/private.pem")),
                ("public", "Public verification key", str(Path.home() / ".config/tomos-premiumgen/public.pem")),
                ("customer", "Customer reference (optional)", ""),
                ("device", "Device UUID (offline only)", ""),
                ("output", "Output licence file", str(Path.home() / "tomos-licence.json")),
                ("verify_licence", "Licence file to verify", ""),
            ]
            for row, (key, label_text, default) in enumerate(fields):
                label = Gtk.Label(label=label_text)
                label.set_halign(Gtk.Align.END)
                label.set_valign(Gtk.Align.CENTER)
                entry = Gtk.Entry()
                entry.set_hexpand(True)
                entry.set_text(default)
                if key == "private":
                    entry.set_visibility(True)
                self.entries[key] = entry
                form.attach(label, 0, row, 1, 1)
                form.attach(entry, 1, row, 1, 1)
                if key in {"private", "public", "output", "verify_licence"}:
                    browse = Gtk.Button(label="Browse…")
                    browse.connect("clicked", self.choose_file, key)
                    form.attach(browse, 2, row, 1, 1)

            actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            root.append(actions)
            for label, callback, suggested in [
                ("Generate signing keys", self.on_keygen, True),
                ("Online activation", self.on_online, True),
                ("Offline licence", self.on_offline, False),
                ("Verify licence", self.on_verify, False),
            ]:
                button = Gtk.Button(label=label)
                if suggested:
                    button.add_css_class("suggested-action")
                button.connect("clicked", callback)
                actions.append(button)

            warning = Gtk.Label(
                label="Security: the private signing key stays on this computer. "
                      "Treat activation codes, QR images and licence files as confidential."
            )
            warning.set_wrap(True)
            warning.set_halign(Gtk.Align.START)
            warning.add_css_class("warning")
            root.append(warning)

            self.status = Gtk.Label(label="Choose an action to get started.")
            self.status.set_wrap(True)
            self.status.set_selectable(True)
            self.status.set_halign(Gtk.Align.START)
            self.status.set_valign(Gtk.Align.START)
            self.status.add_css_class("card")
            self.status.set_margin_top(6)
            self.status.set_margin_bottom(6)
            root.append(self.status)

        def value(self, key: str) -> str:
            return self.entries[key].get_text().strip()

        def path(self, key: str) -> Path:
            return Path(self.value(key)).expanduser()

        def report(self, message: str, error: bool = False) -> None:
            self.status.set_text(message)
            self.status.remove_css_class("error")
            if error:
                self.status.add_css_class("error")

        def choose_file(self, _button, key: str) -> None:
            save = key in {"private", "public", "output"}
            chooser = Gtk.FileChooserNative.new(
                "Choose file", self,
                Gtk.FileChooserAction.SAVE if save else Gtk.FileChooserAction.OPEN,
                "_Select", "_Cancel",
            )
            current = self.value(key)
            if current:
                candidate = Path(current).expanduser()
                if candidate.parent.exists():
                    chooser.set_current_folder(Gio.File.new_for_path(str(candidate.parent)))
                if save:
                    chooser.set_current_name(candidate.name)
            def selected(dialog, response):
                if response == Gtk.ResponseType.ACCEPT:
                    file = dialog.get_file()
                    if file and file.get_path():
                        self.entries[key].set_text(file.get_path())
                dialog.destroy()
            chooser.connect("response", selected)
            chooser.show()

        def run_action(self, operation) -> None:
            try:
                self.report(operation())
            except (OSError, ValueError, RuntimeError) as error:
                self.report(f"Error: {error}", error=True)

        def on_keygen(self, _button) -> None:
            def operation():
                private, public = self.path("private"), self.path("public")
                generate_keypair(private, public)
                return (f"Signing keys created.\nPrivate key: {private} (keep secret; permissions 0600).\n"
                        f"Public key: {public}")
            self.run_action(operation)

        def on_online(self, _button) -> None:
            def operation():
                private = self.path("private")
                if not private.is_file():
                    raise FileNotFoundError(f"Private key not found: {private}")
                code, document = issue_licence(private, self.value("customer"))
                output = self.path("output")
                qr = output.with_suffix(".qr.png")
                write_json(output, document)
                write_activation_qr(code, qr)
                self.get_application().get_clipboard().set(code)
                return (f"ONLINE LIFETIME LICENCE CREATED\n\nActivation code (also copied to clipboard):\n{code}\n\n"
                        f"Signed licence: {output}\nPrivate QR image: {qr}\n\n"
                        "Deliver the code and QR image privately. The code is shown only now.")
            self.run_action(operation)

        def on_offline(self, _button) -> None:
            def operation():
                private = self.path("private")
                if not private.is_file():
                    raise FileNotFoundError(f"Private key not found: {private}")
                device_id = self.value("device")
                if not device_id:
                    raise ValueError("Enter the device UUID shown in TomOS SIP.")
                document = issue_offline_licence(private, device_id, self.value("customer"))
                output = self.path("output")
                write_json(output, document)
                return (f"OFFLINE LIFETIME LICENCE CREATED\nDevice: {document['payload']['device_id']}\n"
                        f"Signed licence: {output}\nTransfer this file securely to the matching device.")
            self.run_action(operation)

        def on_verify(self, _button) -> None:
            def operation():
                public = self.path("public")
                licence = self.path("verify_licence")
                if not public.is_file():
                    raise FileNotFoundError(f"Public key not found: {public}")
                if not licence.is_file():
                    raise FileNotFoundError(f"Licence file not found: {licence}")
                valid = verify_licence(public, read_json(licence))
                if not valid:
                    raise ValueError("INVALID: signature or licence contents did not validate.")
                return "VALID: signed TomOS SIP Premium lifetime licence."
            self.run_action(operation)

    def on_activate(application: Gtk.Application) -> None:
        window = application.props.active_window
        if window is None:
            PremiumWindow(application).present()

    app.connect("activate", on_activate)
    app.run(None)
