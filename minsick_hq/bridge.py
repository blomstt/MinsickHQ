"""The objects the QML interface talks to. Everything that touches PipeWire runs asynchronously
through QProcess, so dragging a band or plugging in the headset never freezes the window.

HQ          the app's state: outputs and microphones, the equaliser and its bands, presets and
            profiles, undo, the cleaned microphone, and the settings
DialogQueue one dialog at a time: errors, confirmations and the profile-name prompt queue up
            behind whatever is showing instead of stacking on top of it
"""
import json
import os
import subprocess
import time

from PySide6.QtCore import Property, QObject, QProcess, QTimer, QUrl, Signal, Slot

from . import autostart, mic, pwproc
from .audio import pipewire
from .eq import autoeq, engine, presets
from .profiles import ProfileStore, search

REFRESH_MS = 2500
UPDATE_DEBOUNCE_MS = 40
# Changes closer together than this are one step for undo, so a drag undoes in one go
UNDO_COALESCE_S = 0.7
UNDO_LIMIT = 100


class DialogQueue(QObject):
    """Dialogs wait their turn. QML shows `current` and calls done() when it closes."""
    changed = Signal()

    def __init__(self):
        super().__init__()
        self._queue = []
        self._current = None

    def _get_current(self):
        return self._current or {}

    def _get_open(self):
        return self._current is not None

    current = Property("QVariantMap", _get_current, notify=changed)
    open = Property(bool, _get_open, notify=changed)

    def push(self, kind, title, text="", action="", value=""):
        """kind: "message", "confirm" or "name". action names what confirming does."""
        self._queue.append({"kind": kind, "title": title, "text": text, "action": action, "value": value})
        if self._current is None:
            self._next()

    @Slot()
    def done(self):
        self._current = None
        self._next()

    def _next(self):
        self._current = self._queue.pop(0) if self._queue else None
        self.changed.emit()


class HQ(QObject):
    devicesChanged = Signal()
    micChanged = Signal()
    eqChanged = Signal()
    historyChanged = Signal()
    entriesChanged = Signal()
    statusChanged = Signal()
    prefsChanged = Signal()

    def __init__(self, dialogs, demo_dump=None, recover=False):
        """recover: this is the one running copy, so it may clean up after one that crashed."""
        super().__init__()
        self.dialogs = dialogs
        self.store = ProfileStore()
        self.engine = engine.Engine()
        self.mic_engine = mic.MicEngine()
        self._demo_dump = demo_dump
        # Outputs
        self._devices = []
        self._selected = ""
        self._default_name = None
        self._eq_node_id = None
        self._restore_default = None
        # One volume control while the equaliser runs (see _handoff_volume)
        self._handoff_pending = False
        self._eq_volume = None
        self._eq_volume_node = None
        # Microphones
        self._mics = []
        self._mic_selected = self.store.prefs["mic_source"]
        self._default_source = None
        self._mic_node_id = None
        self._restore_source = None
        self._mic_enabled = False
        # Equaliser
        self._eq_enabled = False
        self._search = ""
        self._dirty = False
        self._selected_band = 0
        self._history = []
        self._future = []
        self._last_change = 0.0
        entry = self._entry(self.store.last_used) or self._entry("Flat")
        self._active = entry["name"]
        self._setting = presets.clamp_setting(entry)
        self._curve = presets.curve(self._setting)
        self._login = autostart.enabled() if demo_dump is None else False
        self._dump_process = None
        if recover and demo_dump is None:
            self._recover()
        self._refresh_timer = QTimer(self, interval=REFRESH_MS, timeout=self.refresh)
        self._update_timer = QTimer(self, interval=UPDATE_DEBOUNCE_MS, singleShot=True, timeout=self._push_update)
        self._refresh_timer.start()
        self.refresh()
        # Switch back on whatever was on when the app last closed
        if self.store.eq_enabled:
            QTimer.singleShot(800, lambda: self.setEqEnabled(True))
        if self.store.prefs["mic_enabled"]:
            QTimer.singleShot(900, lambda: self.setMicEnabled(True))

    # ---------- reading PipeWire ----------

    @Slot()
    def refresh(self):
        """Reads PipeWire's state again in the background."""
        if self._demo_dump is not None:
            self._apply_dump(self._demo_dump)
            return
        if self._dump_process is not None:
            return
        process = QProcess(self)
        process.finished.connect(lambda *_: self._dump_finished(process))
        # Only a pw-dump that couldn't start at all; other errors also end in finished. Quitting
        # mid-read reports an error after the process is gone, which must be ignored
        process.errorOccurred.connect(
            lambda error: self._dump_finished(process) if error == QProcess.ProcessError.FailedToStart else None)
        self._dump_process = process
        process.start("pw-dump", [])

    def _dump_finished(self, process):
        if self._dump_process is not process:
            return
        self._dump_process = None
        try:
            objects = json.loads(bytes(process.readAllStandardOutput()).decode() or "[]")
        except (ValueError, RuntimeError):
            # RuntimeError: the process was already deleted while the app was closing
            return
        process.deleteLater()
        self._apply_dump(objects)

    def _apply_dump(self, objects):
        self._apply_outputs(objects)
        self._apply_microphones(objects)

    def _recover(self):
        """After a crash: stop equaliser and mic processes the last copy left running, and give
        the headset back the volume it had, before anything else happens. Without this a crash
        could leave the headset at 100% once the equaliser's output disappears."""
        subprocess.run(["pkill", "-f", "^pipewire -c .*/minsick-hq-"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        handoff = self.store.handoff
        if not handoff:
            return
        objects = pipewire.dump()
        device = next((d for d in pipewire.parse(objects) if d["name"] == handoff["device"]), None)
        if device:
            pipewire.set_volume(device["id"], handoff["volume"])
        self.store.handoff = None
        self.store.save()

    def _apply_outputs(self, objects):
        devices = pipewire.parse(objects)
        self._default_name = pipewire.default_sink_name(objects)
        self._eq_node_id = pipewire.find_id(objects, engine.SINK_NAME)
        # Keep my choice while it's plugged in; otherwise the Maxwell, the default, or the first
        names = [d["name"] for d in devices]
        selected = self._selected if self._selected in names else ""
        if not selected and devices:
            maxwell = next((d for d in devices if d["isMaxwell"]), None)
            default = next((d for d in devices if d["isDefault"]), None)
            selected = (maxwell or default or devices[0])["name"]
        changed = devices != self._devices or selected != self._selected
        lost = self._selected and self._selected not in names
        self._devices = devices
        self._selected = selected
        if changed:
            self.devicesChanged.emit()
            self.statusChanged.emit()
        if lost and self._eq_enabled:
            self.dialogs.push("message", "Headset disconnected",
                              "The equaliser now plays into " + (self._get_selected_device().get("description") or "nothing") + ".")
        if self._eq_enabled and changed:
            self._start_engine()
        if self._eq_enabled and self._eq_node_id is not None:
            self._handoff_volume(objects)
            if self._default_name != engine.SINK_NAME:
                pipewire.set_default(self._eq_node_id)

    def _handoff_volume(self, objects):
        """While the equaliser runs there must be one volume, not two in a row: my volume control
        works on the equaliser's output, and the headset under it sits at 100%. Without this the
        headset's old level stacks on top: 30% on the EQ plus 50% on the headset is about -50 dB,
        silence. The level carries over both ways, so switching on or off doesn't jump."""
        device = self._get_selected_device()
        if not device or self._demo_dump is not None:
            return
        handoff = self.store.handoff
        if self._handoff_pending:
            level = pipewire.volume(objects, device["id"])
            if level is None:
                return
            # The equaliser takes over the headset's level, then the headset goes to full
            pipewire.set_volume(self._eq_node_id, level)
            pipewire.set_volume(device["id"], 1.0)
            self.store.handoff = {"device": device["name"], "volume": level}
            self.store.save()
            self._eq_volume, self._eq_volume_node = level, self._eq_node_id
            self._handoff_pending = False
            return
        if not handoff:
            return
        if self._eq_node_id != self._eq_volume_node and self._eq_volume is not None:
            # The equaliser restarted (a band changed type): its new output starts at 100%
            pipewire.set_volume(self._eq_node_id, self._eq_volume)
            self._eq_volume_node = self._eq_node_id
            return
        if handoff["device"] != device["name"]:
            # Playing into other headphones now: the old ones get the level back, the new go to full
            old = next((d for d in self._devices if d["name"] == handoff["device"]), None)
            if old:
                pipewire.set_volume(old["id"], self._eq_volume or handoff["volume"])
            pipewire.set_volume(device["id"], 1.0)
            handoff["device"] = device["name"]
            self.store.save()
            return
        level = pipewire.volume(objects, self._eq_node_id)
        if level is not None and level != handoff["volume"]:
            # Remember my latest level, so it's what the headset gets back
            self._eq_volume = handoff["volume"] = level
            self.store.save()

    def _give_volume_back(self):
        """The headset gets my latest level back, before the equaliser's output goes away, so the
        sound only ever gets quieter for a moment, never louder."""
        handoff = self.store.handoff
        if not handoff:
            return
        objects = pipewire.dump()
        level = pipewire.volume(objects, pipewire.find_id(objects, engine.SINK_NAME)) if objects else None
        level = level if level is not None else handoff["volume"]
        device = next((d for d in pipewire.parse(objects) if d["name"] == handoff["device"]), None)
        if device:
            pipewire.set_volume(device["id"], level)
        self.store.handoff = None
        self.store.save()

    def _apply_microphones(self, objects):
        mics = pipewire.microphones(objects)
        self._default_source = pipewire.default_source_name(objects)
        self._mic_node_id = pipewire.find_id(objects, mic.SOURCE_NAME)
        names = [m["name"] for m in mics]
        selected = self._mic_selected if self._mic_selected in names else ""
        if not selected and mics:
            maxwell = next((m for m in mics if m["isMaxwell"]), None)
            default = next((m for m in mics if m["isDefault"]), None)
            selected = (maxwell or default or mics[0])["name"]
        changed = mics != self._mics or selected != self._mic_selected
        self._mics = mics
        self._mic_selected = selected
        if changed:
            self.micChanged.emit()
            if self._mic_enabled:
                self._start_mic()
        if (self._mic_enabled and self.store.prefs["mic_make_default"] and self._mic_node_id is not None
                and self._default_source != mic.SOURCE_NAME):
            pipewire.set_default(self._mic_node_id)

    # ---------- outputs ----------

    def _get_devices(self):
        return self._devices

    def _get_selected(self):
        return self._selected

    def _get_selected_device(self):
        return next((d for d in self._devices if d["name"] == self._selected), {})

    def _get_maxwell(self):
        return next((d for d in self._devices if d["isMaxwell"]), {})

    devices = Property("QVariantList", _get_devices, notify=devicesChanged)
    selected = Property(str, _get_selected, notify=devicesChanged)
    selectedDevice = Property("QVariantMap", _get_selected_device, notify=devicesChanged)
    maxwell = Property("QVariantMap", _get_maxwell, notify=devicesChanged)

    @Slot(str)
    def selectDevice(self, name):
        if name != self._selected:
            self._selected = name
            self.devicesChanged.emit()
            self.statusChanged.emit()
            if self._eq_enabled:
                self._start_engine()

    @Slot(int)
    def useAsOutput(self, node_id):
        if self._eq_enabled:
            # Playing through the EQ: change what the EQ plays into instead of bypassing it
            device = next((d for d in self._devices if d["id"] == node_id), None)
            if device:
                self.selectDevice(device["name"])
            return
        if not pipewire.set_default(node_id):
            self.dialogs.push("message", "Couldn't switch output", "PipeWire didn't accept the change. Is wpctl installed?")
        self.refresh()

    # ---------- equaliser on and off ----------

    def _get_eq_enabled(self):
        return self._eq_enabled

    eqEnabled = Property(bool, _get_eq_enabled, notify=eqChanged)

    @Slot(bool)
    def setEqEnabled(self, enabled):
        if enabled == self._eq_enabled:
            return
        if enabled:
            if self._demo_dump is None and not pwproc.available():
                self.dialogs.push("message", "PipeWire not found", "The equaliser needs the pipewire and pw-cli commands.")
                return
            if not self._devices:
                self.dialogs.push("message", "No headphones to play into",
                                  "Connect your Maxwell (or pick another output) first.")
                return
            self._eq_enabled = True
            self._restore_default = self._default_name if self._default_name != engine.SINK_NAME else None
            self._handoff_pending = True
            self._start_engine()
        else:
            self._eq_enabled = False
            self._stop_engine()
        self.store.eq_enabled = self._eq_enabled
        self.store.save()
        self.eqChanged.emit()
        self.statusChanged.emit()

    def _start_engine(self):
        if self._demo_dump is not None:
            return
        self.engine.start(self._setting, self._selected or None)
        QTimer.singleShot(600, self.refresh)

    def _stop_engine(self):
        if self._demo_dump is not None:
            return
        self._give_volume_back()
        self._handoff_pending = False
        self._eq_volume = self._eq_volume_node = None
        self.engine.stop()
        # Hand the system back the output it had before the equaliser took over
        device = next((d for d in self._devices if d["name"] == self._restore_default), None)
        if device:
            pipewire.set_default(device["id"])
        self._eq_node_id = None
        QTimer.singleShot(300, self.refresh)

    def _push_update(self):
        if not self._eq_enabled or self._demo_dump is not None:
            return
        if self.engine.needs_restart(self._setting, self._selected or None):
            # A band changed type: the filter graph has to be built again
            self._start_engine()
        elif self._eq_node_id is not None:
            # pw-cli echoes every parameter it sets; keep that out of the terminal
            process = QProcess()
            process.setProgram("pw-cli")
            process.setArguments(["set-param", str(self._eq_node_id), "Props", engine.param_json(self._setting)])
            process.setStandardOutputFile(QProcess.nullDevice())
            process.setStandardErrorFile(QProcess.nullDevice())
            process.startDetached()

    # ---------- the curve and its bands ----------

    def _get_bands(self):
        return self._setting["bands"]

    def _get_preamp(self):
        return self._setting["preamp"]

    def _get_curve(self):
        return self._curve

    def _get_peak(self):
        return max(self._curve) if self._curve else 0.0

    def _get_selected_band(self):
        return self._selected_band

    def _get_active(self):
        return self._active

    def _get_active_note(self):
        entry = self._entry(self._active)
        return entry.get("note", "") if entry else ""

    def _get_active_is_mine(self):
        entry = self._entry(self._active)
        return bool(entry) and not entry.get("builtIn")

    def _get_dirty(self):
        return self._dirty

    def _get_ranges(self):
        return {"gain": list(presets.GAIN_RANGE), "preamp": list(presets.PREAMP_RANGE),
                "freq": list(presets.FREQ_RANGE), "q": list(presets.Q_RANGE)}

    bands = Property("QVariantList", _get_bands, notify=eqChanged)
    preamp = Property(float, _get_preamp, notify=eqChanged)
    curve = Property("QVariantList", _get_curve, notify=eqChanged)
    peak = Property(float, _get_peak, notify=eqChanged)
    selectedBand = Property(int, _get_selected_band, notify=eqChanged)
    activeName = Property(str, _get_active, notify=eqChanged)
    activeNote = Property(str, _get_active_note, notify=eqChanged)
    activeIsMine = Property(bool, _get_active_is_mine, notify=eqChanged)
    modified = Property(bool, _get_dirty, notify=eqChanged)
    ranges = Property("QVariantMap", _get_ranges, constant=True)

    @Slot(int)
    def selectBand(self, index):
        if 0 <= index < presets.BAND_COUNT and index != self._selected_band:
            self._selected_band = index
            self.eqChanged.emit()

    @Slot(int, str, "QVariant")
    def setBand(self, index, key, value):
        """Changes one thing about a band: "gain", "freq", "q" or "kind"."""
        if not 0 <= index < presets.BAND_COUNT or key not in ("gain", "freq", "q", "kind"):
            return
        bands = [dict(b) for b in self._setting["bands"]]
        if key == "gain":
            value = round(float(value) * 10) / 10
        bands[index][key] = value
        self._selected_band = index
        self._change({"preamp": self._setting["preamp"], "bands": bands})

    @Slot(int, float)
    def setGain(self, index, gain):
        self.setBand(index, "gain", gain)

    @Slot(float)
    def setPreamp(self, preamp):
        self._change({"preamp": round(preamp * 10) / 10, "bands": self._setting["bands"]})

    @Slot()
    def autoPreamp(self):
        self._change({"preamp": presets.safe_preamp(self._setting), "bands": self._setting["bands"]}, force_step=True)

    @Slot()
    def reset(self):
        """Back to the saved preset or profile."""
        entry = self._entry(self._active)
        if entry:
            self._change(presets.clamp_setting(entry), force_step=True)

    def _change(self, setting, force_step=False):
        setting = presets.clamp_setting(setting)
        if setting == self._setting:
            return
        self._remember(force_step)
        self._setting = setting
        self._after_change()

    def _after_change(self):
        entry = self._entry(self._active)
        self._dirty = entry is None or presets.clamp_setting(entry) != self._setting
        # Edits to one of my profiles save as I go, unless I've asked for a Save button instead
        if self._dirty and entry and not entry.get("builtIn") and self.store.prefs["autosave_profiles"]:
            self.store.update(self._active, self._setting)
            self._dirty = False
        self._curve = presets.curve(self._setting)
        self.eqChanged.emit()
        self._update_timer.start()

    @Slot()
    def saveChanges(self):
        """Saves the curve into the profile it came from (when profile edits don't save as I go)."""
        if self._get_active_is_mine():
            self.store.update(self._active, self._setting)
            self._dirty = False
            self.eqChanged.emit()

    # ---------- undo ----------

    def _remember(self, force=False):
        """Keeps the state before a change for undo. Quick successive changes share one step."""
        now = time.monotonic()
        if force or not self._history or now - self._last_change > UNDO_COALESCE_S:
            self._history.append((self._active, self._setting))
            del self._history[:-UNDO_LIMIT]
        self._last_change = now
        self._future.clear()
        self.historyChanged.emit()

    def _restore(self, state):
        self._active, self._setting = state
        self._last_change = 0.0
        self._after_change()
        self.historyChanged.emit()

    def _get_can_undo(self):
        return bool(self._history)

    def _get_can_redo(self):
        return bool(self._future)

    canUndo = Property(bool, _get_can_undo, notify=historyChanged)
    canRedo = Property(bool, _get_can_redo, notify=historyChanged)

    @Slot()
    def undo(self):
        if self._history:
            self._future.append((self._active, self._setting))
            self._restore(self._history.pop())

    @Slot()
    def redo(self):
        if self._future:
            self._history.append((self._active, self._setting))
            self._restore(self._future.pop())

    # ---------- presets, profiles and search ----------

    def _all_entries(self):
        mine = [{"name": p["name"], "preamp": p["preamp"], "bands": p["bands"], "builtIn": False, "note": ""}
                for p in self.store.profiles]
        return mine + presets.built_in()

    def _entry(self, name):
        name = (name or "").lower()
        return next((e for e in self._all_entries() if e["name"].lower() == name), None)

    def _get_entries(self):
        return search(self._all_entries(), self._search)

    def _get_search(self):
        return self._search

    entries = Property("QVariantList", _get_entries, notify=entriesChanged)
    searchText = Property(str, _get_search, notify=entriesChanged)

    @Slot(str)
    def setSearch(self, text):
        if text != self._search:
            self._search = text
            self.entriesChanged.emit()

    @Slot(str)
    def applyEntry(self, name):
        entry = self._entry(name)
        if entry is None:
            return
        self._remember(force=True)
        self._active = entry["name"]
        self._setting = presets.clamp_setting(entry)
        self.store.last_used = self._active
        self.store.save()
        self._after_change()

    @Slot(str, result=str)
    def checkName(self, name):
        return ProfileStore.check_name(name, [e["name"] for e in self._all_entries()])

    @Slot(str, result=str)
    def saveProfile(self, name):
        """Saves the current curve as a new profile. Returns why not, or "" when saved."""
        problem = self.checkName(name)
        if problem:
            return problem
        self.store.add(name, self._setting)
        self.entriesChanged.emit()
        self._active = name.strip()
        self.store.last_used = self._active
        self.store.save()
        self._after_change()
        return ""

    @Slot(str, str, result=str)
    def renameProfile(self, old, new):
        taken = [e["name"] for e in self._all_entries() if e["name"].lower() != old.lower()]
        problem = ProfileStore.check_name(new, taken)
        if problem:
            return problem
        self.store.rename(old, new)
        if self._active == old:
            self._active = new.strip()
            self.eqChanged.emit()
        self.entriesChanged.emit()
        return ""

    @Slot(str)
    def askDelete(self, name):
        self.dialogs.push("confirm", "Delete profile?", f"“{name}” will be gone for good.", "delete", name)

    @Slot(str)
    def askRename(self, name):
        self.dialogs.push("name", "Rename profile", f"A new name for “{name}”.", "rename", name)

    @Slot()
    def askSave(self):
        self.dialogs.push("name", "Save as profile", "Name the current curve.", "save", "")

    @Slot(str, str, str, result=str)
    def confirm(self, action, value, text=""):
        """The dialog's confirm button. value is what the dialog was about, text what was typed.
        Returns a problem to show in the dialog, or ""."""
        if action == "delete":
            self.store.remove(value)
            if self._active == value:
                self.applyEntry("Flat")
            self.entriesChanged.emit()
        elif action == "save":
            return self.saveProfile(text)
        elif action == "rename":
            return self.renameProfile(value, text)
        return ""

    # ---------- AutoEQ files ----------

    @staticmethod
    def _path(url_or_path):
        url = QUrl(url_or_path)
        return url.toLocalFile() if url.isLocalFile() else url_or_path

    @Slot(str)
    def importFile(self, url_or_path):
        """Loads a ParametricEQ.txt file as a new profile named after the file."""
        path = self._path(url_or_path)
        try:
            with open(path) as file:
                setting = autoeq.parse(file.read())
        except (OSError, UnicodeDecodeError) as error:
            self.dialogs.push("message", "Couldn't read the file", str(error))
            return
        except autoeq.FormatError as error:
            self.dialogs.push("message", "Not an EQ file Minsick HQ can use", str(error))
            return
        base = os.path.splitext(os.path.basename(path))[0].replace(" ParametricEQ", "").strip() or "Imported"
        name, n = base[:36], 2
        while self.checkName(name):
            name = f"{base[:32]} ({n})"
            n += 1
        self._remember(force=True)
        self.store.add(name, setting)
        self.entriesChanged.emit()
        self._active = name
        self._setting = presets.clamp_setting(setting)
        self.store.last_used = name
        self.store.save()
        self._after_change()

    @Slot(str)
    def exportFile(self, url_or_path):
        path = self._path(url_or_path)
        if not path.endswith(".txt"):
            path += ".txt"
        try:
            with open(path, "w") as file:
                file.write(autoeq.to_text(self._setting, f"{self._active}, exported from Minsick HQ"))
        except OSError as error:
            self.dialogs.push("message", "Couldn't save the file", str(error))
            return
        self.dialogs.push("message", "Exported", f"Saved as {path}. Other EQ apps that read AutoEQ's ParametricEQ.txt can load it.")

    # ---------- the cleaned microphone ----------

    def _get_mics(self):
        return self._mics

    def _get_mic_selected(self):
        return self._mic_selected

    def _get_mic_enabled(self):
        return self._mic_enabled

    microphones = Property("QVariantList", _get_mics, notify=micChanged)
    micSelected = Property(str, _get_mic_selected, notify=micChanged)
    micEnabled = Property(bool, _get_mic_enabled, notify=micChanged)

    def _mic_options(self):
        prefs = self.store.prefs
        return {"noise": prefs["mic_noise"], "level": prefs["mic_level"], "rumble": prefs["mic_rumble"]}

    @Slot(bool)
    def setMicEnabled(self, enabled):
        if enabled == self._mic_enabled:
            return
        if enabled:
            if self._demo_dump is None and not pwproc.available():
                self.dialogs.push("message", "PipeWire not found", "The microphone cleanup needs the pipewire command.")
                return
            if not self._mics:
                self.dialogs.push("message", "No microphone", "Connect your Maxwell first; its mic shows up here.")
                return
            self._mic_enabled = True
            self._restore_source = self._default_source if self._default_source != mic.SOURCE_NAME else None
            self._start_mic()
        else:
            self._mic_enabled = False
            self._stop_mic()
        self.store.set_pref("mic_enabled", self._mic_enabled)
        self.micChanged.emit()
        self.statusChanged.emit()

    @Slot(str)
    def selectMic(self, name):
        if name != self._mic_selected:
            self._mic_selected = name
            self.store.set_pref("mic_source", name)
            self.micChanged.emit()
            if self._mic_enabled:
                self._start_mic()

    def _start_mic(self):
        if self._demo_dump is not None:
            return
        self.mic_engine.start(self._mic_selected or None, self._mic_options())
        QTimer.singleShot(600, self.refresh)

    def _stop_mic(self):
        if self._demo_dump is not None:
            return
        self.mic_engine.stop()
        source = next((m for m in self._mics if m["name"] == self._restore_source), None)
        if source:
            pipewire.set_default(source["id"])
        self._mic_node_id = None
        QTimer.singleShot(300, self.refresh)

    # ---------- settings ----------

    def _get_prefs(self):
        return self.store.prefs

    def _get_login(self):
        return self._login

    prefs = Property("QVariantMap", _get_prefs, notify=prefsChanged)
    startOnLogin = Property(bool, _get_login, notify=prefsChanged)

    @Slot(str, "QVariant")
    def setPref(self, key, value):
        self.store.set_pref(key, value)
        self.prefsChanged.emit()
        if key.startswith("mic_") and key != "mic_make_default" and self._mic_enabled:
            self._start_mic()
        if key == "mic_make_default" and self._mic_enabled:
            if value:
                self.refresh()
            else:
                source = next((m for m in self._mics if m["name"] == self._restore_source), None)
                if source:
                    pipewire.set_default(source["id"])
        if key == "autosave_profiles":
            self.eqChanged.emit()

    @Slot(bool)
    def setStartOnLogin(self, enabled):
        if self._demo_dump is not None:
            self._login = enabled
        else:
            problem = autostart.enable() if enabled else autostart.disable()
            if problem:
                self.dialogs.push("message", "Couldn't change start at login", problem)
            self._login = autostart.enabled()
        self.prefsChanged.emit()

    @Slot(result=bool)
    def keepRunningWhenClosed(self):
        """Whether closing the window should leave the app running in the background."""
        return self.store.prefs["keep_running"] and (self._eq_enabled or self._mic_enabled)

    @Slot(result=bool)
    def busy(self):
        return self._eq_enabled or self._mic_enabled

    @Slot()
    def shutdown(self):
        if self._eq_enabled:
            self._stop_engine()
        if self._mic_enabled:
            self._stop_mic()

    # ---------- the status line ----------

    def _get_status(self):
        device = self._get_selected_device()
        if not device:
            return "No headphones connected"
        route = "through the equaliser" if self._eq_enabled else "directly"
        text = f"Playing {route} into {device['description']}"
        if self._mic_enabled:
            text += ". Microphone cleaned up"
        return text

    status = Property(str, _get_status, notify=statusChanged)
