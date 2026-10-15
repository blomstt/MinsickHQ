"""Biquad filter maths for drawing the equaliser's response curve.

Uses the same filter shapes PipeWire's filter-chain runs (bq_lowshelf, bq_peaking,
bq_highshelf), with coefficients from Robert Bristow-Johnson's Audio EQ Cookbook.
No Qt here: everything in this file can be tested from a terminal.
"""
import cmath
import math

SAMPLE_RATE = 48000.0

LOWSHELF = "lowshelf"
PEAKING = "peaking"
HIGHSHELF = "highshelf"
KINDS = (LOWSHELF, PEAKING, HIGHSHELF)


def coefficients(kind, freq, q, gain_db, rate=SAMPLE_RATE):
    """Normalised (b0, b1, b2, a1, a2) for one band."""
    a = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * min(freq, rate * 0.49) / rate
    cos_w0 = math.cos(w0)
    alpha = math.sin(w0) / (2.0 * max(q, 0.01))
    if kind == PEAKING:
        b0, b1, b2 = 1 + alpha * a, -2 * cos_w0, 1 - alpha * a
        a0, a1, a2 = 1 + alpha / a, -2 * cos_w0, 1 - alpha / a
    elif kind in (LOWSHELF, HIGHSHELF):
        root = 2.0 * math.sqrt(a) * alpha
        sign = 1.0 if kind == LOWSHELF else -1.0
        b0 = a * ((a + 1) - sign * (a - 1) * cos_w0 + root)
        b1 = sign * 2 * a * ((a - 1) - sign * (a + 1) * cos_w0)
        b2 = a * ((a + 1) - sign * (a - 1) * cos_w0 - root)
        a0 = (a + 1) + sign * (a - 1) * cos_w0 + root
        a1 = -sign * 2 * ((a - 1) + sign * (a + 1) * cos_w0)
        a2 = (a + 1) + sign * (a - 1) * cos_w0 - root
    else:
        raise ValueError(f"unknown band kind {kind!r}")
    return b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0


def magnitude_db(coeffs, freq, rate=SAMPLE_RATE):
    """How much one band lifts or cuts a frequency, in dB."""
    b0, b1, b2, a1, a2 = coeffs
    z = cmath.exp(-1j * 2.0 * math.pi * freq / rate)
    h = (b0 + b1 * z + b2 * z * z) / (1 + a1 * z + a2 * z * z)
    return 20.0 * math.log10(max(abs(h), 1e-9))


def log_frequencies(count=160, low=20.0, high=20000.0):
    """Frequencies spread evenly on a log scale, the way the graph draws them."""
    step = math.log(high / low) / (count - 1)
    return [low * math.exp(step * i) for i in range(count)]


def response(bands, preamp_db=0.0, freqs=None, rate=SAMPLE_RATE):
    """The whole equaliser's curve in dB at each frequency: preamp plus every band."""
    freqs = freqs or log_frequencies()
    coeffs = [coefficients(b["kind"], b["freq"], b["q"], b["gain"], rate) for b in bands]
    return [preamp_db + sum(magnitude_db(c, f, rate) for c in coeffs) for f in freqs]
