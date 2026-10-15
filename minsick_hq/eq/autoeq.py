"""Reads and writes AutoEQ's "ParametricEQ.txt" format, which many EQ apps share:

    Preamp: -6.3 dB
    Filter 1: ON LSC Fc 105 Hz Gain -2.2 dB Q 0.70
    Filter 2: ON PK Fc 8114 Hz Gain 5.9 dB Q 2.31

LSC/LS is a low shelf, HSC/HS a high shelf, PK a peak. Filters marked OFF are skipped.
No Qt here: everything in this file can be tested from a terminal.
"""
import re

from . import presets
from .biquad import HIGHSHELF, LOWSHELF, PEAKING

_KINDS = {"LSC": LOWSHELF, "LS": LOWSHELF, "HSC": HIGHSHELF, "HS": HIGHSHELF, "PK": PEAKING, "PEQ": PEAKING}
_CODES = {LOWSHELF: "LSC", HIGHSHELF: "HSC", PEAKING: "PK"}
_FILTER = re.compile(
    r"Filter\s*\d*\s*:\s*(ON|OFF)\s+([A-Z]+)\s+Fc\s+([\d.]+)\s*Hz\s+Gain\s+(-?[\d.]+)\s*dB(?:\s+Q\s+([\d.]+))?",
    re.IGNORECASE)
_PREAMP = re.compile(r"Preamp\s*:\s*(-?[\d.]+)\s*dB", re.IGNORECASE)


class FormatError(ValueError):
    """The text isn't a parametric EQ this app can use; the message says why, for the person."""


def parse(text):
    """A setting from ParametricEQ.txt text. Fewer than ten filters are padded with flat bands."""
    preamp = 0.0
    bands = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = _PREAMP.match(line)
        if match:
            preamp = float(match.group(1))
            continue
        match = _FILTER.match(line)
        if not match:
            continue
        state, code, freq, gain, q = match.groups()
        if state.upper() == "OFF":
            continue
        kind = _KINDS.get(code.upper())
        if kind is None:
            raise FormatError(f"Filter type {code} isn't supported; Minsick HQ has low shelves, peaks and high shelves.")
        bands.append({"kind": kind, "freq": float(freq), "gain": float(gain),
                      "q": float(q) if q else (presets.SHELF_Q if kind != PEAKING else presets.PEAK_Q)})
    if not bands:
        raise FormatError("No filters found. Expected lines like “Filter 1: ON PK Fc 100 Hz Gain 2.0 dB Q 1.0”.")
    if len(bands) > presets.BAND_COUNT:
        raise FormatError(f"This EQ has {len(bands)} filters; Minsick HQ has {presets.BAND_COUNT} bands.")
    # Flat bands fill the rest; with no gain they change nothing
    bands += [dict(presets.default_band(i), gain=0.0) for i in range(len(bands), presets.BAND_COUNT)]
    return presets.clamp_setting({"preamp": preamp, "bands": bands})


def to_text(setting, title=""):
    """ParametricEQ.txt text for a setting. Flat bands are written too, so nothing is lost."""
    setting = presets.clamp_setting(setting)
    lines = [f"# {title}"] if title else []
    lines.append(f"Preamp: {setting['preamp']:.1f} dB")
    for i, band in enumerate(setting["bands"]):
        lines.append(f"Filter {i + 1}: ON {_CODES[band['kind']]} Fc {band['freq']:g} Hz "
                     f"Gain {band['gain']:.1f} dB Q {band['q']:.2f}")
    return "\n".join(lines) + "\n"
