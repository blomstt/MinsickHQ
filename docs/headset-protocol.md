# The Maxwell dongle's control protocol

What Minsick HQ knows about talking to the headset itself (battery, sidetone, mic monitoring,
auto-off, the EQ stored on the headset), and how the rest gets worked out. Everything here is read
from the device itself.

## What the dongle says about itself

USB `3329:4b19` ("Audeze Maxwell Dongle"). Interface 0 is HID with one 64-byte interrupt IN
endpoint; interfaces 1 to 4 are ordinary USB audio (playback, the microphone). Its HID report
descriptor, read from `/sys/class/hidraw/hidraw*/device/report_descriptor`, declares:

| Report | Direction | Size | What the descriptor says |
|---|---|---|---|
| `0x0C` | in | 1 byte of bits | Consumer page: volume up/down, mute, play/pause, next, previous. The headset's own buttons. Linux already handles these. |
| `0x05` | in and out | bits | Telephony page: hook switch, phone mute, LEDs. Call controls for Teams/Discord-style apps. |
| `0x06` | out | 61 bytes | Vendor page `0xFF13`: commands from the computer to the headset |
| `0x07` | in | 61 bytes | Vendor page `0xFF13`: replies from the headset |
| `0x03` | in | 13 bytes | Vendor page `0xFF13`: a status message |
| `0x04` | in | 1 byte | Vendor page `0xFF13`: an event |

Battery, settings and the on-headset EQ almost certainly travel in reports 6 and 7, with 3 and 4
carrying things the headset reports by itself. The byte layout of those reports isn't in the
descriptor; that's the part still to learn.

## Rule: no guessed commands

Minsick HQ never sends report 6 until a command is understood from real traffic. A wrong command
could change a setting, or worse. Everything below starts read-only.

## Step 1: listen (works now, read-only)

```bash
python3 -m minsick_hq.hid.listen --log maxwell.log
```

It opens the dongle read-only and prints every report the headset sends by itself. While it runs,
do one thing at a time and note the time: power the headset off and on, turn the volume wheel, flip
the mic up and down, put it on the charger, wait for the battery to drop a step. Reports 3, 4 and 7
that line up with those moments tell us what the headset volunteers, which may already include the
battery level.

Access: on this system the dongle is already readable (systemd gives the logged-in user access to
it). Elsewhere, install `packaging/70-minsick-hq.rules` as its comments describe.

## Step 2: learn the commands

Settings and status queries need the byte layout of reports 6 and 7. That comes from recording the
dongle's USB traffic (usbmon on Linux) while a setting is changed, one at a time.

## Step 3: implement, read-only first

Battery and status queries first (asking, never setting), with each reply checked against the
headset's real state. Settings only after each command's effect is confirmed, one
at a time, with a way to put the old value back.
