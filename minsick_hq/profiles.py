"""My own EQ profiles and the app's settings, saved as JSON in ~/.config/minsick-hq/profiles.json.

A profile is a named EQ setting: {"name", "preamp", "bands"} (see eq/presets.py; older files
with "gains" still load). The file also remembers which profile or preset was last used, whether
the equaliser was on, and the preferences in PREFERENCES.
No Qt here: everything in this file can be tested from a terminal.
"""
import json
import os

from .eq import presets

CONFIG_HOME = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config"))
DEFAULT_PATH = os.path.join(CONFIG_HOME, "minsick-hq", "profiles.json")
MAX_NAME = 40
# The settings page's choices, with their defaults
PREFERENCES = {
    # Closing the window while the equaliser or microphone is on keeps them running
    "keep_running": True,
    # Edits to one of my profiles are saved as I make them; off means "Save" saves them
    "autosave_profiles": True,
    "mic_enabled": False,
    "mic_source": "",
    "mic_make_default": True,
    "mic_noise": True,
    "mic_level": True,
    "mic_rumble": True,
}


class ProfileStore:
    def __init__(self, path=DEFAULT_PATH):
        self.path = path
        self.profiles = []
        self.last_used = "Flat"
        self.eq_enabled = False
        self.prefs = dict(PREFERENCES)
        # While the equaliser runs it owns the volume and the headset sits at 100%. This records
        # which output that is and the level to give it back: {"device": node name, "volume": 0-1}.
        # Kept on disk so a crash can't leave the headset at full volume (see HQ._settle_handoff)
        self.handoff = None
        self.load()

    def load(self):
        try:
            with open(self.path) as file:
                data = json.load(file)
        except (OSError, ValueError):
            return
        self.profiles = [{"name": str(p["name"])[:MAX_NAME], **presets.clamp_setting(p)}
                         for p in data.get("profiles", []) if p.get("name")]
        self.last_used = data.get("last_used", self.last_used)
        self.eq_enabled = bool(data.get("eq_enabled", False))
        handoff = data.get("volume_handoff")
        if isinstance(handoff, dict) and isinstance(handoff.get("device"), str) and isinstance(handoff.get("volume"), (int, float)):
            self.handoff = {"device": handoff["device"], "volume": max(0.0, min(1.0, float(handoff["volume"])))}
        for key, default in PREFERENCES.items():
            value = data.get("prefs", {}).get(key, default)
            self.prefs[key] = value if isinstance(value, type(default)) else default

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        temporary = self.path + ".tmp"
        with open(temporary, "w") as file:
            json.dump({"profiles": self.profiles, "last_used": self.last_used,
                       "eq_enabled": self.eq_enabled, "prefs": self.prefs,
                       "volume_handoff": self.handoff}, file, indent=2)
        os.replace(temporary, self.path)

    def names(self):
        return [p["name"] for p in self.profiles]

    def find(self, name):
        for profile in self.profiles:
            if profile["name"].lower() == name.strip().lower():
                return profile
        return None

    @staticmethod
    def check_name(name, taken):
        """Why a name can't be used, or "" when it's fine. taken is every name already in use."""
        name = name.strip()
        if not name:
            return "Enter a name for the profile."
        if len(name) > MAX_NAME:
            return f"Keep the name under {MAX_NAME} characters."
        if name.lower() in (t.lower() for t in taken):
            return f"“{name}” already exists."
        return ""

    def add(self, name, setting):
        self.profiles.append({"name": name.strip(), **presets.clamp_setting(setting)})
        self.save()

    def update(self, name, setting):
        profile = self.find(name)
        if profile:
            index = self.profiles.index(profile)
            self.profiles[index] = {"name": profile["name"], **presets.clamp_setting(setting)}
            self.save()

    def set_pref(self, key, value):
        if key in PREFERENCES and isinstance(value, type(PREFERENCES[key])):
            self.prefs[key] = value
            self.save()

    def rename(self, old, new):
        profile = self.find(old)
        if profile:
            profile["name"] = new.strip()
            if self.last_used == old:
                self.last_used = profile["name"]
            self.save()

    def remove(self, name):
        self.profiles = [p for p in self.profiles if p["name"].lower() != name.lower()]
        if self.last_used == name:
            self.last_used = "Flat"
        self.save()


def search(entries, query):
    """Entries whose name matches every word of the query, best matches first.

    Matching ignores case. A name that starts with the query ranks above one that only
    contains it, so typing "ba" puts Bass Boost above Late Night Bass.
    """
    words = query.lower().split()
    if not words:
        return list(entries)
    scored = []
    for index, entry in enumerate(entries):
        name = entry["name"].lower()
        if all(word in name for word in words):
            starts = name.startswith(words[0])
            word_start = any(part.startswith(words[0]) for part in name.split())
            scored.append((0 if starts else 1 if word_start else 2, index, entry))
    return [entry for _, _, entry in sorted(scored, key=lambda s: (s[0], s[1]))]
