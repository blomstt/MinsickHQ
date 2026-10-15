"""Tests for the objects behind the QML, in demo mode: no PipeWire, no window.
Profiles go to a temporary folder, never the real ~/.config."""
import os
import tempfile
import unittest

os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp()

from PySide6.QtCore import QCoreApplication  # noqa: E402

from minsick_hq import profiles  # noqa: E402
from minsick_hq.bridge import HQ, DialogQueue  # noqa: E402
from minsick_hq.demo import DEMO_DUMP  # noqa: E402

APP = QCoreApplication.instance() or QCoreApplication([])


class BridgeTests(unittest.TestCase):
    def setUp(self):
        profiles.DEFAULT_PATH = os.path.join(tempfile.mkdtemp(), "profiles.json")
        profiles.ProfileStore.__init__.__defaults__ = (profiles.DEFAULT_PATH,)
        self.dialogs = DialogQueue()
        self.hq = HQ(self.dialogs, demo_dump=DEMO_DUMP)

    def test_picks_the_maxwell(self):
        self.assertEqual(self.hq.maxwell["description"], "Audeze Maxwell")
        self.assertEqual(self.hq.selected, self.hq.maxwell["name"])
        self.assertIn("Audeze Maxwell", self.hq.status)

    def test_presets_load_and_report_changes(self):
        self.hq.applyEntry("Bass Boost")
        self.assertEqual(self.hq.activeName, "Bass Boost")
        self.assertFalse(self.hq.modified)
        self.assertLessEqual(self.hq.peak, 0.01)
        self.hq.setGain(9, 6.0)
        self.assertTrue(self.hq.modified)
        self.hq.reset()
        self.assertFalse(self.hq.modified)

    def test_auto_preamp_stops_clipping(self):
        self.hq.applyEntry("Flat")
        self.hq.setGain(3, 9.0)
        self.assertGreater(self.hq.peak, 1.0)
        self.hq.autoPreamp()
        self.assertLessEqual(self.hq.peak, 0.05)

    def test_save_rename_delete_profile(self):
        self.hq.setGain(0, 4.0)
        self.assertNotEqual(self.hq.saveProfile("Flat"), "")
        self.assertEqual(self.hq.saveProfile("Night raid"), "")
        self.assertEqual(self.hq.activeName, "Night raid")
        # Editing my own profile saves it straight away
        self.hq.setGain(1, 2.0)
        self.assertFalse(self.hq.modified)
        self.assertEqual(self.hq.store.find("Night raid")["bands"][1]["gain"], 2.0)
        self.assertEqual(self.hq.renameProfile("Night raid", "Raids"), "")
        self.assertEqual(self.hq.activeName, "Raids")
        self.hq.askDelete("Raids")
        self.assertTrue(self.dialogs.open)
        self.assertEqual(self.hq.confirm("delete", "Raids", ""), "")
        self.dialogs.done()
        self.assertEqual(self.hq.activeName, "Flat")
        self.assertNotIn("Raids", [e["name"] for e in self.hq.entries])

    def test_search_filters_presets_and_profiles(self):
        self.hq.saveProfile("My bass")
        self.hq.setSearch("bass")
        self.assertEqual([e["name"] for e in self.hq.entries], ["Bass Boost", "Bass Reducer", "My bass"])
        self.hq.setSearch("")
        self.assertGreater(len(self.hq.entries), 9)

    def test_dialogs_wait_their_turn(self):
        self.dialogs.push("message", "First")
        self.dialogs.push("message", "Second")
        self.assertEqual(self.dialogs.current["title"], "First")
        self.dialogs.done()
        self.assertEqual(self.dialogs.current["title"], "Second")
        self.dialogs.done()
        self.assertFalse(self.dialogs.open)

    def test_eq_needs_an_output(self):
        empty = HQ(self.dialogs, demo_dump=[])
        empty.setEqEnabled(True)
        self.assertFalse(empty.eqEnabled)
        self.assertEqual(self.dialogs.current["title"], "No headphones to play into")


    def test_undo_and_redo(self):
        self.hq.applyEntry("Flat")
        self.hq.setGain(2, 5.0)
        self.hq.setGain(2, 6.0)   # straight after: same undo step
        self.assertTrue(self.hq.canUndo)
        self.hq.undo()
        self.assertEqual(self.hq.bands[2]["gain"], 0.0)
        self.hq.redo()
        self.assertEqual(self.hq.bands[2]["gain"], 6.0)
        self.hq.applyEntry("Bass Boost")
        self.hq.undo()
        self.assertEqual(self.hq.activeName, "Flat")
        self.assertEqual(self.hq.bands[2]["gain"], 6.0)

    def test_bands_move_and_change_type(self):
        self.hq.applyEntry("Flat")
        self.hq.setBand(4, "freq", 777.0)
        self.hq.setBand(4, "q", 3.0)
        self.hq.setBand(4, "kind", "highshelf")
        band = self.hq.bands[4]
        self.assertEqual((band["freq"], band["q"], band["kind"]), (777.0, 3.0, "highshelf"))
        self.assertEqual(self.hq.selectedBand, 4)
        self.assertTrue(self.hq.modified)

    def test_maxwell_corrections_are_offered_with_a_note(self):
        names = [e["name"] for e in self.hq.entries]
        self.assertIn("Maxwell correction (Kuulokenurkka)", names)
        self.hq.applyEntry("Maxwell correction (Kuulokenurkka)")
        self.assertIn("Audeze preset", self.hq.activeNote)

    def test_import_and_export(self):
        folder = tempfile.mkdtemp()
        source = os.path.join(folder, "Desk Fix ParametricEQ.txt")
        with open(source, "w") as file:
            file.write("Preamp: -2 dB\nFilter 1: ON PK Fc 3000 Hz Gain 2 dB Q 2\n")
        self.hq.importFile(source)
        self.assertEqual(self.hq.activeName, "Desk Fix")
        self.assertEqual(self.hq.bands[0]["freq"], 3000.0)
        self.hq.importFile(source)
        self.assertEqual(self.hq.activeName, "Desk Fix (2)")
        target = os.path.join(folder, "out")
        self.hq.exportFile(target)
        with open(target + ".txt") as file:
            self.assertIn("Filter 1: ON PK Fc 3000 Hz Gain 2.0 dB Q 2.00", file.read())
        self.hq.importFile(os.path.join(folder, "missing.txt"))
        self.assertTrue(self.dialogs.open)

    def test_background_only_when_something_is_on(self):
        self.assertFalse(self.hq.keepRunningWhenClosed())
        self.hq.setEqEnabled(True)
        self.assertTrue(self.hq.keepRunningWhenClosed())
        self.hq.setPref("keep_running", False)
        self.assertFalse(self.hq.keepRunningWhenClosed())

    def test_microphone_in_demo(self):
        self.assertEqual(self.hq.micSelected, self.hq.microphones[0]["name"])
        self.hq.setMicEnabled(True)
        self.assertTrue(self.hq.micEnabled)
        self.assertIn("Microphone cleaned up", self.hq.status)


MAXWELL = "alsa_output.usb-Audeze_LLC_Audeze_Maxwell_Dongle_0000000000000000-01.analog-stereo"


def fake_pipewire(maxwell_level, eq_level=None):
    """pw-dump objects: the Maxwell at a slider level, and the equaliser's output if eq_level is set."""
    objects = [{"id": 70, "type": "PipeWire:Interface:Node", "info": {
        "props": {"node.name": MAXWELL, "node.description": "Audeze Maxwell", "media.class": "Audio/Sink"},
        "params": {"Props": [{"channelVolumes": [maxwell_level ** 3] * 2}]}}}]
    if eq_level is not None:
        objects.append({"id": 80, "type": "PipeWire:Interface:Node", "info": {
            "props": {"node.name": "minsick_hq_eq", "node.description": "Minsick HQ Equalizer", "media.class": "Audio/Sink"},
            "params": {"Props": [{"channelVolumes": [eq_level ** 3] * 2}]}}})
    return objects


class FakeEngine:
    def start(self, *args):
        pass

    def stop(self):
        pass

    def needs_restart(self, *args):
        return False

    def running(self):
        return True


class VolumeHandoffTests(unittest.TestCase):
    """While the equaliser runs there's one volume: the EQ output takes the headset's level and the
    headset goes to 100%. Switching off, and recovering from a crash, give the level back."""

    def setUp(self):
        from minsick_hq import bridge
        self.bridge = bridge
        profiles.DEFAULT_PATH = os.path.join(tempfile.mkdtemp(), "profiles.json")
        profiles.ProfileStore.__init__.__defaults__ = (profiles.DEFAULT_PATH,)
        self.calls = []
        self.objects = fake_pipewire(0.5)
        self.saved = (bridge.pipewire.set_volume, bridge.pipewire.set_default, bridge.pipewire.dump, bridge.subprocess.run)
        bridge.pipewire.set_volume = lambda node, level: self.calls.append((node, round(level, 3))) or True
        bridge.pipewire.set_default = lambda node: True
        bridge.pipewire.dump = lambda: self.objects
        bridge.subprocess.run = lambda *a, **k: None
        self.dialogs = DialogQueue()

    def tearDown(self):
        b = self.bridge
        b.pipewire.set_volume, b.pipewire.set_default, b.pipewire.dump, b.subprocess.run = self.saved

    def make(self, recover=False):
        hq = HQ(self.dialogs, demo_dump=None, recover=recover)
        hq._refresh_timer.stop()
        hq.engine = FakeEngine()
        hq._apply_dump(self.objects)
        return hq

    def test_switching_on_hands_the_level_to_the_equaliser(self):
        hq = self.make()
        hq.setEqEnabled(True)
        self.objects = fake_pipewire(0.5, eq_level=1.0)
        hq._apply_dump(self.objects)
        self.assertIn((80, 0.5), self.calls)   # the EQ output takes the headset's 50%
        self.assertIn((70, 1.0), self.calls)   # the headset goes to full
        self.assertEqual(hq.store.handoff, {"device": MAXWELL, "volume": 0.5})

    def test_my_latest_level_goes_back_when_switching_off(self):
        hq = self.make()
        hq.setEqEnabled(True)
        hq._apply_dump(fake_pipewire(0.5, eq_level=1.0))
        # I turn the volume down to 30% while the equaliser runs
        self.objects = fake_pipewire(1.0, eq_level=0.3)
        hq._apply_dump(self.objects)
        self.assertEqual(hq.store.handoff["volume"], 0.3)
        self.calls.clear()
        hq.setEqEnabled(False)
        self.assertEqual(self.calls[0], (70, 0.3))  # before the EQ stops, never after
        self.assertIsNone(hq.store.handoff)

    def test_a_crash_never_leaves_the_headset_at_full_volume(self):
        hq = self.make()
        hq.store.handoff = {"device": MAXWELL, "volume": 0.4}
        hq.store.save()
        # The app died; the headset was left at 100% and the equaliser's output is gone
        self.objects = fake_pipewire(1.0)
        self.calls.clear()
        self.make(recover=True)
        self.assertIn((70, 0.4), self.calls)
        self.assertIsNone(profiles.ProfileStore().handoff)


if __name__ == "__main__":
    unittest.main()
