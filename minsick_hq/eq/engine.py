"""Runs the equaliser on real system audio with PipeWire's filter-chain.

Turning the EQ on starts a small PipeWire process of our own from a generated config. It adds
a virtual output, "Minsick HQ Equalizer", whose sound goes through the ten bands and on to
the chosen headphones. Gains, frequencies and widths change live with `pw-cli set-param`, so
moving a band never restarts the audio; only changing a band's type (shelf or peak) does. Turning the EQ off (or quitting) stops the process and the virtual output
disappears with it, so nothing is left behind in the system's PipeWire configuration.
No Qt here: everything in this file can be tested from a terminal.
"""
import json
import subprocess

from . import presets
from .. import pwproc

SINK_NAME = "minsick_hq_eq"
SINK_DESCRIPTION = "Minsick HQ Equalizer"
PREAMP_NODE = "preamp"


def band_node(i):
    return f"band_{i + 1}"


def _number(value):
    return f"{float(value):.4f}"


def preamp_factor(preamp_db):
    return 10.0 ** (preamp_db / 20.0)


def config_text(setting, target_sink=None):
    """A complete PipeWire config that runs the equaliser as its own filter-chain process.

    The graph is mono (preamp, then the ten bands in a row); filter-chain runs one copy per
    channel. target_sink is the node.name of the headphones to play into, or None for the
    system's default output.
    """
    setting = presets.clamp_setting(setting)
    nodes = [
        f'{{ type = builtin name = {PREAMP_NODE} label = linear '
        f'control = {{ "Mult" = {_number(preamp_factor(setting["preamp"]))} "Add" = 0.0 }} }}'
    ]
    links = []
    previous = PREAMP_NODE
    for i, band in enumerate(setting["bands"]):
        name = band_node(i)
        nodes.append(
            f'{{ type = builtin name = {name} label = bq_{band["kind"]} '
            f'control = {{ "Freq" = {_number(band["freq"])} "Q" = {_number(band["q"])} "Gain" = {_number(band["gain"])} }} }}'
        )
        links.append(f'{{ output = "{previous}:Out" input = "{name}:In" }}')
        previous = name
    target = f'\n                target.object = "{target_sink}"' if target_sink else ""
    module = f"""    {{ name = libpipewire-module-filter-chain
        args = {{
            node.description = "{SINK_DESCRIPTION}"
            media.name       = "{SINK_DESCRIPTION}"
            filter.graph = {{
                nodes = [
                    {chr(10).join("                    " + n for n in nodes).lstrip()}
                ]
                links = [
                    {chr(10).join("                    " + l for l in links).lstrip()}
                ]
            }}
            audio.channels = 2
            audio.position = [ FL FR ]
            capture.props = {{
                node.name   = "{SINK_NAME}"
                media.class = Audio/Sink
            }}
            playback.props = {{
                node.name    = "{SINK_NAME}.output"
                node.passive = true{target}
            }}
        }}
    }}
"""
    return pwproc.config(module, "equaliser")


def param_json(setting):
    """The filter-chain controls for a setting, as pw-cli set-param's Props JSON."""
    setting = presets.clamp_setting(setting)
    params = [f'"{PREAMP_NODE}:Mult"', _number(preamp_factor(setting["preamp"]))]
    for i, band in enumerate(setting["bands"]):
        node = band_node(i)
        params += [f'"{node}:Freq"', _number(band["freq"]), f'"{node}:Q"', _number(band["q"]),
                   f'"{node}:Gain"', _number(band["gain"])]
    return "{ params = [ " + " ".join(params) + " ] }"


class Engine:
    """One running equaliser. start(), update() and stop() are safe to call in any order."""

    def __init__(self, runner=subprocess):
        self.runner = runner
        self.process = pwproc.PipeWireProcess("equaliser", runner)
        self.target_sink = None
        # The band types the running process was built with
        self.kinds = None

    @staticmethod
    def available():
        return pwproc.available()

    def running(self):
        return self.process.running()

    def needs_restart(self, setting, target_sink=None):
        """True when the running process can't take this setting live: it's playing elsewhere,
        or a band changed type, which the filter graph fixes when it starts."""
        setting = presets.clamp_setting(setting)
        return not self.running() or target_sink != self.target_sink or presets.kinds(setting) != self.kinds

    def start(self, setting, target_sink=None):
        """Starts the equaliser into target_sink, restarting it if it was playing elsewhere or a
        band changed type; otherwise just updates it."""
        if not self.needs_restart(setting, target_sink):
            return self.update(setting)
        self.target_sink = target_sink
        self.kinds = presets.kinds(presets.clamp_setting(setting))
        self.process.start(config_text(setting, target_sink))
        return True

    def update(self, setting, node_id=None):
        """Sends new values to the running equaliser without restarting it.

        node_id is the PipeWire id of our sink; without one it's looked up by name.
        Returns False when the equaliser isn't running or the sink can't be found yet.
        """
        if not self.running():
            return False
        node_id = node_id if node_id is not None else find_node_id(SINK_NAME, self.runner)
        if node_id is None:
            return False
        result = self.runner.run(["pw-cli", "set-param", str(node_id), "Props", param_json(setting)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
        return result.returncode == 0

    def stop(self):
        self.process.stop()
        self.kinds = None


def find_node_id(node_name, runner=subprocess):
    """The id of the PipeWire node with this name, or None."""
    try:
        output = runner.run(["pw-dump"], capture_output=True, text=True, timeout=5).stdout
        objects = json.loads(output or "[]")
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    for item in objects:
        props = (item.get("info") or {}).get("props") or {}
        if item.get("type") == "PipeWire:Interface:Node" and props.get("node.name") == node_name:
            return item.get("id")
    return None
