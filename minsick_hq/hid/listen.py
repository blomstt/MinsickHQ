"""Logs every report the Maxwell dongle sends by itself, without sending anything to it.

    python -m minsick_hq.hid.listen            print reports as they arrive
    python -m minsick_hq.hid.listen --log F    also append them to F

Leave it running, then do one thing at a time: power the headset off and on, turn the volume
wheel, mute the mic, let the battery change, put it on the charger. Note the time of each.
Whatever the headset reports by itself (battery, power, mute) shows up here, and lining the
times up tells us which bytes mean what. Reading is all this ever does: it opens the device
read-only and never writes, so it can't change any setting on the headset.
"""
import argparse
import os
import select
import sys
import time

from . import REPORTS, find_hidraw


def describe(data):
    report = data[0] if data else None
    name = REPORTS.get(report, "unknown")
    return f"report 0x{report:02x} ({name}): {data[1:].hex(' ')}"


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m minsick_hq.hid.listen")
    parser.add_argument("--log", help="also append every report to this file")
    args = parser.parse_args(argv)
    path = find_hidraw()
    if path is None:
        print("The Maxwell dongle isn't plugged in (no hidraw device for 3329:4b19).")
        return 1
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    except PermissionError:
        print(f"No permission to read {path}. Install the udev rule in packaging/70-minsick-hq.rules\n"
              "(see the comments at its top), then unplug and replug the dongle.")
        return 1
    print(f"Listening to {path}, read-only. Ctrl+C to stop.")
    log = open(args.log, "a") if args.log else None
    last = None
    try:
        while True:
            ready, _, _ = select.select([fd], [], [], 1.0)
            if not ready:
                continue
            data = os.read(fd, 64)
            # Media-key reports repeat a lot; only print when something changed
            if data == last:
                continue
            last = data
            line = f"{time.strftime('%H:%M:%S')}  {describe(data)}"
            print(line, flush=True)
            if log:
                log.write(line + "\n")
                log.flush()
    except KeyboardInterrupt:
        return 0
    finally:
        os.close(fd)
        if log:
            log.close()


if __name__ == "__main__":
    sys.exit(main())
