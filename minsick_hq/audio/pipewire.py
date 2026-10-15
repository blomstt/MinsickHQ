"""The audio outputs PipeWire knows about, read from `pw-dump`.

parse() turns pw-dump's JSON into plain dicts, so it can be tested with saved output. The
Maxwell shows up as a USB dongle ("Audeze Maxwell Dongle") or over Bluetooth; anything that
says it's a headset or headphones counts as headphones too.
No Qt here: everything in this file can be tested from a terminal.
"""
import json
import subprocess

# Everything the app itself adds (the equaliser output, the cleaned microphone) is named this way
OWN_PREFIX = "minsick_hq"

MAXWELL_WORDS = ("maxwell",)
HEADPHONE_FORM_FACTORS = ("headset", "headphone", "hands-free")


def dump(runner=subprocess):
    """pw-dump's objects, or [] when PipeWire isn't reachable."""
    try:
        output = runner.run(["pw-dump"], capture_output=True, text=True, timeout=5).stdout
        return json.loads(output or "[]")
    except (OSError, ValueError, subprocess.SubprocessError):
        return []


def _default_sink_name(objects, key="default.audio.sink"):
    for item in objects:
        if item.get("type") == "PipeWire:Interface:Metadata" and (item.get("props") or {}).get("metadata.name") == "default":
            for entry in item.get("metadata") or []:
                if entry.get("key") == key:
                    value = entry.get("value")
                    if isinstance(value, str):
                        try:
                            value = json.loads(value)
                        except ValueError:
                            return value
                    return (value or {}).get("name")
    return None


def parse(objects, media_class="Audio/Sink"):
    """Every real audio output (or, with media_class "Audio/Source", every microphone), as dicts
    with id, name, description, api, isHeadphones, isMaxwell and isDefault. What the app adds
    itself and the dummy output are left out."""
    devices = {item["id"]: (item.get("info") or {}).get("props") or {}
               for item in objects if item.get("type") == "PipeWire:Interface:Device"}
    default = _default_sink_name(objects, "default.audio.sink" if media_class == "Audio/Sink" else "default.audio.source")
    outputs = []
    for item in objects:
        if item.get("type") != "PipeWire:Interface:Node":
            continue
        props = (item.get("info") or {}).get("props") or {}
        name = props.get("node.name", "")
        if props.get("media.class") != media_class or name.startswith(OWN_PREFIX) or name in ("auto_null", "auto_null.monitor"):
            continue
        device = devices.get(props.get("device.id"), {})
        description = props.get("node.description") or device.get("device.description") or name
        words = " ".join(str(v) for v in (name, description, device.get("device.product.name", ""))).lower()
        form = str(device.get("device.form-factor") or props.get("device.form-factor") or "").lower()
        api = props.get("device.api") or device.get("device.api") or ""
        outputs.append({
            "id": item["id"],
            "name": name,
            "description": description,
            "api": "Bluetooth" if api == "bluez5" else "USB" if "usb" in name.lower() else api.upper() or "Audio",
            "isMaxwell": any(word in words for word in MAXWELL_WORDS),
            "isHeadphones": any(word in words for word in MAXWELL_WORDS) or form in HEADPHONE_FORM_FACTORS,
            "isDefault": name == default,
        })
    # The Maxwell first, then other headphones, then the rest, each by name
    outputs.sort(key=lambda o: (not o["isMaxwell"], not o["isHeadphones"], o["description"].lower()))
    return outputs


def default_sink_name(objects):
    return _default_sink_name(objects)


def microphones(objects):
    """Every real microphone, the Maxwell's first."""
    return parse(objects, "Audio/Source")


def default_source_name(objects):
    return _default_sink_name(objects, "default.audio.source")


def find_id(objects, node_name):
    """The id of the node with this name, or None."""
    for item in objects:
        props = (item.get("info") or {}).get("props") or {}
        if item.get("type") == "PipeWire:Interface:Node" and props.get("node.name") == node_name:
            return item.get("id")
    return None


def set_default(node_id, runner=subprocess):
    """Makes this output the system's default. True when wpctl accepted it."""
    try:
        return runner.run(["wpctl", "set-default", str(node_id)], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, timeout=5).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def volume(objects, node_id):
    """An output's volume as the slider shows it (0 to 1, PipeWire's cubic scale), or None.
    pw-dump reports linear channel volumes; the slider value is their cube root."""
    for item in objects:
        if item.get("id") != node_id or item.get("type") != "PipeWire:Interface:Node":
            continue
        for props in ((item.get("info") or {}).get("params") or {}).get("Props", []):
            channels = props.get("channelVolumes")
            if channels:
                return round(max(channels) ** (1.0 / 3.0), 4)
    return None


def set_volume(node_id, slider, runner=subprocess):
    """Sets an output's volume, 0 to 1 on the slider's scale. True when wpctl accepted it."""
    slider = max(0.0, min(1.0, float(slider)))
    try:
        return runner.run(["wpctl", "set-volume", str(node_id), f"{slider:.4f}"], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, timeout=5).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False

