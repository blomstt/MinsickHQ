"""EQ settings and the presets that come with the app.

A setting is a plain dict: {"preamp": dB, "bands": [ten bands]}, and a band is
{"kind": "lowshelf" | "peaking" | "highshelf", "freq": Hz, "q": width, "gain": dB}.
Every band can sit anywhere, so AutoEQ corrections (which put their filters wherever the headset
needs them) fit as they are. Settings saved before bands were movable only stored ten "gains";
those load onto the original layout below.
"""
from .biquad import HIGHSHELF, KINDS, LOWSHELF, PEAKING, response

BAND_COUNT = 10
# The layout new settings and the simple presets start from: one octave apart
FREQUENCIES = [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
PEAK_Q = 1.41
SHELF_Q = 0.71
GAIN_RANGE = (-20.0, 20.0)
PREAMP_RANGE = (-24.0, 6.0)
FREQ_RANGE = (20.0, 20000.0)
Q_RANGE = (0.1, 10.0)


def default_band(i, gain=0.0):
    kind = LOWSHELF if i == 0 else HIGHSHELF if i == BAND_COUNT - 1 else PEAKING
    return {"kind": kind, "freq": float(FREQUENCIES[i]), "q": SHELF_Q if kind != PEAKING else PEAK_Q,
            "gain": float(gain)}


def from_gains(gains, preamp=0.0):
    """A setting on the default layout with these ten gains."""
    return {"preamp": float(preamp), "bands": [default_band(i, gains[i]) for i in range(BAND_COUNT)]}


def flat():
    return from_gains([0.0] * BAND_COUNT)


def _clamp(value, limits):
    return max(limits[0], min(limits[1], float(value)))


def clamp_band(band, i=0):
    kind = band.get("kind") if band.get("kind") in KINDS else default_band(i)["kind"]
    return {
        "kind": kind,
        "freq": round(_clamp(band.get("freq", FREQUENCIES[i]), FREQ_RANGE), 1),
        "q": round(_clamp(band.get("q", PEAK_Q), Q_RANGE), 3),
        "gain": round(_clamp(band.get("gain", 0.0), GAIN_RANGE), 2),
    }


def clamp_setting(setting):
    """A copy with every value inside its range and exactly ten bands. Accepts old "gains" settings."""
    if "bands" not in setting and "gains" in setting:
        setting = from_gains((list(setting["gains"]) + [0.0] * BAND_COUNT)[:BAND_COUNT], setting.get("preamp", 0.0))
    bands = list(setting.get("bands", []))[:BAND_COUNT]
    bands += [default_band(i) for i in range(len(bands), BAND_COUNT)]
    return {"preamp": round(_clamp(setting.get("preamp", 0.0), PREAMP_RANGE), 2),
            "bands": [clamp_band(b, i) for i, b in enumerate(bands)]}


def kinds(setting):
    """The band types in order. The running equaliser has to restart when these change."""
    return tuple(b["kind"] for b in setting["bands"])


def curve(setting):
    return response(setting["bands"], setting["preamp"])


def safe_preamp(setting):
    """Enough preamp cut that the loudest point of the curve can't clip. Neighbouring bands
    overlap, so the curve can peak higher than any single band; this uses the real curve"""
    # Adding 0.0 turns -0.0 into 0.0, so a flat curve doesn't show a minus sign
    return round(-max(0.0, max(response(setting["bands"]))), 2) + 0.0


# Built-in presets: name -> gains on the default layout, each given a preamp with headroom
_SIMPLE = {
    "Flat": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "Bass Boost": [6, 5, 3.5, 1.5, 0, 0, 0, 0, 0, 0],
    "Bass Reducer": [-5, -4, -2.5, -1, 0, 0, 0, 0, 0, 0],
    "Treble Boost": [0, 0, 0, 0, 0, 0.5, 1.5, 3, 4.5, 5],
    "Vocal Clarity": [-2, -1.5, -1, 0, 1.5, 3, 3.5, 2, 0.5, 0],
    "Footsteps": [-4, -3, -2, -1, 0, 1, 3, 4.5, 3, 1],
    "Cinema": [4, 3, 1.5, 0, -1, -0.5, 0.5, 1.5, 2.5, 3],
    "Podcast": [-6, -4, -1, 0.5, 1.5, 2.5, 2, 1, 0, -1],
    "Late Night": [-3, -2, -0.5, 0.5, 1, 1, 0.5, -0.5, -2, -3],
}


def built_in():
    """The presets in display order: the headset corrections first, then the simple curves.
    Each is {"name", "preamp", "bands", "builtIn", "note"}."""
    from . import corrections
    result = []
    for entry in corrections.load():
        result.append({**entry, "builtIn": True})
    for name, gains in _SIMPLE.items():
        setting = from_gains(gains)
        setting["preamp"] = safe_preamp(setting)
        result.append({"name": name, **setting, "builtIn": True, "note": ""})
    return result
