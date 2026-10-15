"""A cleaned-up microphone, "Minsick HQ Microphone", made by PipeWire's echo-cancel module with
the WebRTC engine. It listens to the headset's mic and takes out steady background noise (fans,
hum, keyboards to a degree), evens out the level, cuts low rumble, and removes sound from the
speakers that leaks back into the mic. Voice apps (Discord, games, calls) pick it like any other
microphone; the app can make it the default.

Like the equaliser it runs in a PipeWire process of the app's own (pwproc.py), so switching it off
removes the virtual microphone again.
No Qt here: everything in this file can be tested from a terminal.
"""
import subprocess

from . import pwproc

SOURCE_NAME = "minsick_hq_mic"
SOURCE_DESCRIPTION = "Minsick HQ Microphone"

# What each switch on the microphone page turns on, and its webrtc setting
OPTIONS = {
    "noise": "webrtc.noise_suppression",
    "level": "webrtc.gain_control",
    "rumble": "webrtc.high_pass_filter",
}
DEFAULT_OPTIONS = {"noise": True, "level": True, "rumble": True}


def config_text(source_name, options=None):
    """A complete PipeWire config for the cleaned microphone, listening to source_name.
    Echo removal uses whatever the system is playing as its reference, so no extra output appears."""
    options = {**DEFAULT_OPTIONS, **(options or {})}
    switches = "\n".join(f"                {OPTIONS[key]} = {'true' if on else 'false'}"
                         for key, on in options.items() if key in OPTIONS)
    target = f'\n                target.object = "{source_name}"' if source_name else ""
    module = f"""    {{ name = libpipewire-module-echo-cancel
        args = {{
            library.name = aec/libspa-aec-webrtc
            monitor.mode = true
            node.latency = 480/48000
            aec.args = {{
{switches}
                webrtc.extended_filter = true
                webrtc.delay_agnostic = true
            }}
            capture.props = {{
                node.name    = "{SOURCE_NAME}.capture"
                node.passive = true{target}
            }}
            source.props = {{
                node.name        = "{SOURCE_NAME}"
                node.description = "{SOURCE_DESCRIPTION}"
                media.class      = Audio/Source
            }}
        }}
    }}
"""
    return pwproc.config(module, "microphone")


class MicEngine:
    """The cleaned microphone. start() with the same source and options does nothing; anything
    else restarts it, since these settings are fixed when the module loads."""

    def __init__(self, runner=subprocess):
        self.process = pwproc.PipeWireProcess("microphone", runner)
        self.source = None
        self.options = None

    def running(self):
        return self.process.running()

    def start(self, source_name, options=None):
        options = {**DEFAULT_OPTIONS, **(options or {})}
        if self.running() and source_name == self.source and options == self.options:
            return
        self.source = source_name
        self.options = options
        self.process.start(config_text(source_name, options))

    def stop(self):
        self.process.stop()
        self.source = None
        self.options = None
