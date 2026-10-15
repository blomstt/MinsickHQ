"""Starting Minsick HQ when I log in, as a systemd user service that waits for the graphical
session and PipeWire. It starts with --background: no window, the equaliser and microphone as I
left them. Turning it off disables and removes the service file again.
No Qt here: everything in this file can be tested from a terminal.
"""
import os
import shutil
import subprocess

SERVICE = "minsick-hq.service"
CONFIG_HOME = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config"))
UNIT_PATH = os.path.join(CONFIG_HOME, "systemd", "user", SERVICE)
LAUNCHER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "minsick-hq")


def unit_text(launcher=LAUNCHER):
    return f"""# Written by Minsick HQ's "Start when I log in" setting. Turning that off removes this file
[Unit]
Description=Minsick HQ headset equaliser
PartOf=graphical-session.target
After=graphical-session.target pipewire.service wireplumber.service
Wants=pipewire.service

[Service]
ExecStart={launcher} --background
Restart=on-failure
RestartSec=3

[Install]
WantedBy=graphical-session.target
"""


def available():
    return shutil.which("systemctl") is not None


def _systemctl(*args):
    try:
        return subprocess.run(["systemctl", "--user", *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None


def enabled():
    result = _systemctl("is-enabled", SERVICE)
    return result is not None and result.stdout.strip() == "enabled"


def enable(launcher=LAUNCHER):
    """Writes and enables the service. Returns "" or what went wrong, for the person."""
    if not available():
        return "systemd isn't available, so Minsick HQ can't start itself at login."
    os.makedirs(os.path.dirname(UNIT_PATH), exist_ok=True)
    with open(UNIT_PATH, "w") as file:
        file.write(unit_text(launcher))
    _systemctl("daemon-reload")
    result = _systemctl("enable", SERVICE)
    if result is None or result.returncode != 0:
        return "systemd refused: " + (result.stderr.strip() if result else "systemctl didn't run")
    return ""


def disable():
    """Disables and removes the service. Returns "" or what went wrong."""
    if not available():
        return ""
    _systemctl("disable", SERVICE)
    if os.path.exists(UNIT_PATH):
        os.remove(UNIT_PATH)
    _systemctl("daemon-reload")
    return ""
