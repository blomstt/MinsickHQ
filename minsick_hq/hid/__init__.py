"""The Maxwell dongle's HID interface: finding it, and (for now) only listening to it.
See docs/headset-protocol.md for what's known and how the rest is being worked out."""
import glob
import os

VENDOR = 0x3329
PRODUCT = 0x4b19
# From the dongle's own report descriptor (docs/headset-protocol.md)
REPORTS = {
    0x03: "vendor status (13 bytes)",
    0x04: "vendor event (1 byte)",
    0x05: "telephony: call buttons and mute",
    0x06: "vendor command (61 bytes, host to headset)",
    0x07: "vendor reply (61 bytes, headset to host)",
    0x0C: "media keys: volume, mute, play/pause, next, previous",
}


def find_hidraw():
    """/dev/hidrawN of the Maxwell dongle, or None when it isn't plugged in."""
    for node in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        try:
            with open(os.path.join(node, "device", "uevent")) as file:
                uevent = file.read()
        except OSError:
            continue
        # HID_ID=0003:00003329:00004B19
        for line in uevent.splitlines():
            if line.startswith("HID_ID="):
                _, vendor, product = line[7:].split(":")
                if int(vendor, 16) == VENDOR and int(product, 16) == PRODUCT:
                    return "/dev/" + os.path.basename(node)
    return None
