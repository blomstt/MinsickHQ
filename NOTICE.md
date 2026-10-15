# Notices

## Not affiliated with Audeze

Minsick HQ is an independent project. It is not affiliated with, endorsed by, sponsored by or
connected to Audeze LLC. Audeze, Maxwell and Audeze HQ are trademarks of Audeze LLC; they are used
here only to say which headset this app works with. Minsick HQ contains no code, interface files,
images or other material from Audeze HQ or any other Audeze product.

## Third-party software

Minsick HQ's own code is under the MIT licence (see `LICENSE`). It doesn't bundle any other
software; it uses these, installed separately on your system:

| Software | Licence | How Minsick HQ uses it |
|---|---|---|
| [PySide6 / Qt for Python](https://doc.qt.io/qtforpython-6/) and [Qt 6](https://www.qt.io/) | LGPL-3.0 (or commercial) | Imported as an installed library for the window and interface. You can replace it with any compatible build. |
| [PipeWire](https://pipewire.org/) | MIT | Runs the equaliser (filter-chain module) and the microphone cleanup (echo-cancel module with its WebRTC engine) in `pipewire -c` processes, and reports devices (`pw-dump`, `pw-cli`) |
| [WirePlumber](https://pipewire.pages.freedesktop.org/wireplumber/) | MIT | Switches the default output (`wpctl`) |
| [Python](https://www.python.org/) | PSF License | Runs the app |
| [systemd](https://systemd.io/) | LGPL-2.1+ | Starts the app at login, when that setting is on (`systemctl --user`) |

If you distribute Minsick HQ together with PySide6 or Qt (for example in a packaged build), include
their licence texts and keep them replaceable, as the LGPL-3.0 requires.

## Headset corrections

The two "Maxwell correction" presets (`minsick_hq/eq/corrections/`) are EQ settings published by
the [AutoEQ](https://github.com/jaakkopasanen/AutoEq) project under the MIT licence, copied
unchanged with a header saying where each came from; AutoEQ's licence is next to them in
`LICENSE-AutoEQ`. AutoEQ computed them from measurements by
[Rtings](https://www.rtings.com/) and [Kuulokenurkka](https://kuulokenurkka.fi/); only the
resulting filter settings are included, not the measurements.

MIT License, Copyright (c) 2018-2022 Jaakko Pasanen (AutoEQ). The full licence text is at
https://github.com/jaakkopasanen/AutoEq/blob/master/LICENSE.

## Credits

The equaliser's filter formulas follow Robert Bristow-Johnson's *Audio EQ Cookbook*; the code
implementing them is this project's own.
