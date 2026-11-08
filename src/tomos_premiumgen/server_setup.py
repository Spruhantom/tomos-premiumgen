"""Safe generation of a per-user systemd unit for the redemption API."""
from __future__ import annotations

import os
from pathlib import Path


def _systemd_quote(value: str) -> str:
    """Quote one systemd unit-file value, including literal percent signs."""
    return '"' + value.replace("%", "%%").replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_user_service(
    database_path: Path | str,
    port: int,
    python_executable: str | Path,
) -> str:
    """Build a loopback-only user service without enabling or starting it."""
    try:
        port = int(port)
    except (TypeError, ValueError) as error:
        raise ValueError("Port must be a number between 1 and 65535.") from error
    if not 1 <= port <= 65535:
        raise ValueError("Port must be between 1 and 65535.")

    database = Path(database_path).expanduser()
    if not database.is_absolute():
        raise ValueError("Choose an absolute path for the licence database.")
    executable = str(Path(python_executable).expanduser().absolute())

    return (
        "[Unit]\n"
        "Description=TomOS Premium redemption API\n"
        "After=network.target\n"
        "\n"
        "[Service]\n"
        "Type=simple\n"
        f"Environment={_systemd_quote('TOMOS_LICENCE_DB=' + str(database))}\n"
        f"ExecStart={_systemd_quote(executable)} -m uvicorn "
        "tomos_premiumgen.server:app --host 127.0.0.1 "
        f"--port {port} --log-level info\n"
        "Restart=on-failure\n"
        "RestartSec=5\n"
        "\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )


def install_user_service(
    database_path: Path | str,
    port: int,
    *,
    home: Path | str | None = None,
    python_executable: str | Path,
) -> Path:
    """Create a private user service file; never overwrite an existing unit."""
    home_path = Path(home).expanduser() if home is not None else Path.home()
    database = Path(database_path).expanduser()
    if not database.is_absolute():
        raise ValueError("Choose an absolute path for the licence database.")
    database.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(database.parent, 0o700)
    except OSError:
        pass

    service_dir = home_path / ".config" / "systemd" / "user"
    service_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(service_dir, 0o700)
    except OSError:
        pass
    service_path = service_dir / "tomos-premiumgen.service"
    content = build_user_service(database, port, python_executable)

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(service_path, flags, 0o600)
    except FileExistsError as error:
        raise FileExistsError(
            f"{service_path} already exists; it was left unchanged."
        ) from error
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as service_file:
            service_file.write(content)
    except Exception:
        service_path.unlink(missing_ok=True)
        raise
    os.chmod(service_path, 0o600)
    return service_path
