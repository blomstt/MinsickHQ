"""Tests for everything that runs without a screen: the EQ maths, the PipeWire config,
reading devices from pw-dump, and profiles. Run with: python -m unittest"""
import json
import os
import subprocess
import tempfile
import unittest

from minsick_hq import autostart, mic
from minsick_hq.audio import pipewire
from minsick_hq.eq import autoeq, biquad, corrections, engine, presets
from minsick_hq.profiles import ProfileStore, search


class BiquadTests(unittest.TestCase):
    def test_flat_band_does_nothing(self):
        for kind in biquad.KINDS:
            coeffs = biquad.coefficients(kind, 1000, 1.0, 0.0)
            for freq in (50, 1000, 15000):
                self.assertAlmostEqual(biquad.magnitude_db(coeffs, freq), 0.0, places=6)

    def test_peak_reaches_its_gain_at_its_frequency(self):
        coeffs = biquad.coefficients(biquad.PEAKING, 1000, 1.41, 6.0)
        self.assertAlmostEqual(biquad.magnitude_db(coeffs, 1000), 6.0, places=3)
        self.assertLess(abs(biquad.magnitude_db(coeffs, 50)), 0.2)

    def test_shelves_lift_their_own_end(self):
        low = biquad.coefficients(biquad.LOWSHELF, 100, 0.71, 6.0)
        high = biquad.coefficients(biquad.HIGHSHELF, 8000, 0.71, 6.0)
        self.assertAlmostEqual(biquad.magnitude_db(low, 20), 6.0, delta=0.3)
        self.assertLess(abs(biquad.magnitude_db(low, 10000)), 0.1)
        self.assertAlmostEqual(biquad.magnitude_db(high, 20000), 6.0, delta=0.5)
        self.assertLess(abs(biquad.magnitude_db(high, 50)), 0.1)

    def test_response_adds_preamp(self):
        curve = biquad.response(presets.flat()["bands"], preamp_db=-3.0)
        self.assertTrue(all(abs(v + 3.0) < 1e-6 for v in curve))


class PresetTests(unittest.TestCase):
    def test_simple_presets_never_clip(self):
        for preset in presets.built_in():
            if preset["note"]:
                continue
            self.assertLessEqual(max(presets.curve(preset)), 0.01, preset["name"])

    def test_corrections_barely_clip(self):
        # AutoEQ's own preamps, kept as published; they leave at most a hair of overshoot here
        for preset in presets.built_in():
            if preset["note"]:
                self.assertLessEqual(max(presets.curve(preset)), 0.6, preset["name"])

    def test_clamp_fixes_bad_settings_and_reads_old_gains(self):
        setting = presets.clamp_setting({"preamp": 40, "gains": [99, -99]})
        self.assertEqual(len(setting["bands"]), 10)
        self.assertEqual([b["gain"] for b in setting["bands"][:3]], [20.0, -20.0, 0.0])
        self.assertEqual(setting["bands"][0]["kind"], biquad.LOWSHELF)
        self.assertEqual(setting["preamp"], presets.PREAMP_RANGE[1])
        band = presets.clamp_band({"kind": "notch", "freq": 5, "q": 50, "gain": 3}, 4)
        self.assertEqual((band["kind"], band["freq"], band["q"]), (biquad.PEAKING, 20.0, 10.0))

    def test_flat_preamp_has_no_minus_sign(self):
        self.assertEqual(str(presets.safe_preamp(presets.flat())), "0.0")


KUULOKE = """Preamp: -6.3 dB
Filter 1: ON LSC Fc 105 Hz Gain -2.2 dB Q 0.70
Filter 2: ON PK Fc 8114 Hz Gain 5.9 dB Q 2.31
Filter 3: OFF PK Fc 178 Hz Gain -1.9 dB Q 1.03
Filter 4: ON HSC Fc 10000 Hz Gain -5.5 dB Q 0.70
"""


class AutoEqTests(unittest.TestCase):
    def test_parse_reads_filters_and_skips_off_ones(self):
        setting = autoeq.parse(KUULOKE)
        self.assertEqual(setting["preamp"], -6.3)
        first, second, third = setting["bands"][:3]
        self.assertEqual((first["kind"], first["freq"], first["gain"], first["q"]), (biquad.LOWSHELF, 105.0, -2.2, 0.7))
        self.assertEqual((second["kind"], second["freq"]), (biquad.PEAKING, 8114.0))
        self.assertEqual(third["kind"], biquad.HIGHSHELF)
        # The rest are flat
        self.assertTrue(all(b["gain"] == 0.0 for b in setting["bands"][3:]))

    def test_round_trip(self):
        setting = autoeq.parse(KUULOKE)
        self.assertEqual(autoeq.parse(autoeq.to_text(setting, "x")), setting)

    def test_bad_files_say_why(self):
        with self.assertRaises(autoeq.FormatError):
            autoeq.parse("hello")
        with self.assertRaises(autoeq.FormatError):
            autoeq.parse("Filter 1: ON LP Fc 100 Hz Gain 0 dB Q 1")
        with self.assertRaises(autoeq.FormatError):
            autoeq.parse("\n".join(f"Filter {i}: ON PK Fc 100 Hz Gain 1 dB Q 1" for i in range(11)))

    def test_maxwell_corrections_match_autoeq(self):
        entries = {e["name"]: e for e in corrections.load()}
        kuuloke = entries["Maxwell correction (Kuulokenurkka)"]
        self.assertEqual(kuuloke["preamp"], -6.3)
        self.assertEqual(kuuloke["bands"][9], {"kind": biquad.PEAKING, "freq": 7619.0, "q": 5.68, "gain": 2.2})
        rtings = entries["Maxwell correction (Rtings)"]
        self.assertEqual(rtings["bands"][2]["gain"], -20.0)
        self.assertTrue(all(e["source"].startswith("AutoEQ") for e in entries.values()))


class EngineConfigTests(unittest.TestCase):
    def test_config_chains_preamp_and_ten_bands(self):
        text = engine.config_text(presets.flat(), "alsa_output.usb-Audeze_LLC_Audeze_Maxwell_Dongle")
        self.assertIn("libpipewire-module-filter-chain", text)
        self.assertEqual(text.count("label = bq_"), 10)
        self.assertIn('input = "band_1:In"', text)
        self.assertIn('output = "band_9:Out" input = "band_10:In"', text)
        self.assertIn('target.object = "alsa_output.usb-Audeze_LLC_Audeze_Maxwell_Dongle"', text)
        self.assertIn(f'node.name   = "{engine.SINK_NAME}"', text)

    def test_config_without_target_follows_the_default(self):
        self.assertNotIn("target.object", engine.config_text(presets.flat()))

    def test_config_parses_with_pipewire(self):
        # pipewire's own parser: --version doesn't load modules, so check with spa-json-dump if present
        dump = "/usr/bin/spa-json-dump"
        if not os.path.exists(dump):
            self.skipTest("spa-json-dump not installed")
        with tempfile.NamedTemporaryFile("w", suffix=".conf", delete=False) as file:
            file.write(engine.config_text(presets.flat(), "x"))
        result = subprocess.run([dump, file.name], capture_output=True, text=True)
        os.unlink(file.name)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("filter-chain", result.stdout)

    def test_param_json_sets_every_gain_and_the_preamp(self):
        text = engine.param_json({"preamp": -6.0, "gains": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]})
        self.assertIn('"preamp:Mult" 0.5012', text)
        self.assertIn('"band_10:Gain" 10.0000', text)
        self.assertIn('"band_10:Freq" 16000.0000', text)
        self.assertIn('"band_1:Q" 0.7100', text)

    def test_type_change_needs_a_restart(self):
        class FakeProcess:
            def poll(self):
                return None
        class FakeRunner:
            def Popen(self, *args, **kwargs):
                return FakeProcess()
        eq = engine.Engine(runner=FakeRunner())
        eq.process.process = FakeProcess()
        eq.kinds = presets.kinds(presets.flat())
        eq.target_sink = "x"
        changed = presets.flat()
        changed["bands"][3]["gain"] = 5.0
        self.assertFalse(eq.needs_restart(changed, "x"))
        changed["bands"][3]["kind"] = biquad.HIGHSHELF
        self.assertTrue(eq.needs_restart(changed, "x"))
        self.assertTrue(eq.needs_restart(presets.flat(), "y"))


SAMPLE_DUMP = [
    {"id": 40, "type": "PipeWire:Interface:Device",
     "info": {"props": {"device.description": "Audeze Maxwell Dongle", "device.api": "alsa"}}},
    {"id": 41, "type": "PipeWire:Interface:Device",
     "info": {"props": {"device.description": "Sony WH-1000XM4", "device.api": "bluez5", "device.form-factor": "headphone"}}},
    {"id": 70, "type": "PipeWire:Interface:Node", "info": {"props": {
        "node.name": "alsa_output.usb-Audeze_LLC_Audeze_Maxwell_Dongle_0000000000000000-01.analog-stereo",
        "node.description": "Audeze Maxwell Dongle Analog Stereo", "media.class": "Audio/Sink", "device.id": 40}}},
    {"id": 71, "type": "PipeWire:Interface:Node", "info": {"props": {
        "node.name": "bluez_output.AA_BB.1", "node.description": "Sony WH-1000XM4",
        "media.class": "Audio/Sink", "device.id": 41, "device.api": "bluez5"}}},
    {"id": 72, "type": "PipeWire:Interface:Node", "info": {"props": {
        "node.name": "alsa_output.pci-0000_0c_00.4.analog-stereo", "node.description": "Speakers",
        "media.class": "Audio/Sink"}}},
    {"id": 73, "type": "PipeWire:Interface:Node", "info": {"props": {
        "node.name": "minsick_hq_eq", "node.description": "Minsick HQ Equalizer", "media.class": "Audio/Sink"}}},
    {"id": 74, "type": "PipeWire:Interface:Node", "info": {"props": {
        "node.name": "auto_null", "node.description": "Dummy Output", "media.class": "Audio/Sink"}}},
    {"id": 0, "type": "PipeWire:Interface:Metadata", "props": {"metadata.name": "default"}, "metadata": [
        {"subject": 0, "key": "default.audio.sink", "type": "Spa:String:JSON",
         "value": {"name": "bluez_output.AA_BB.1"}}]},
]


class PipewireTests(unittest.TestCase):
    def test_parse_finds_outputs_and_the_maxwell(self):
        outputs = pipewire.parse(SAMPLE_DUMP)
        self.assertEqual([o["id"] for o in outputs], [70, 71, 72])
        maxwell, sony, speakers = outputs
        self.assertTrue(maxwell["isMaxwell"] and maxwell["isHeadphones"])
        self.assertEqual(maxwell["api"], "USB")
        self.assertTrue(sony["isHeadphones"] and not sony["isMaxwell"])
        self.assertEqual(sony["api"], "Bluetooth")
        self.assertTrue(sony["isDefault"])
        self.assertFalse(speakers["isHeadphones"])

    def test_parse_survives_nothing(self):
        self.assertEqual(pipewire.parse([]), [])

    def test_default_as_json_string(self):
        dump = [dict(SAMPLE_DUMP[-1], metadata=[{"key": "default.audio.sink", "value": json.dumps({"name": "x"})}])]
        self.assertEqual(pipewire.default_sink_name(dump), "x")


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "profiles.json")

    def test_save_load_rename_remove(self):
        store = ProfileStore(self.path)
        store.add("  Gaming  ", {"preamp": -4, "gains": [4] * 10})
        store.set_pref("keep_running", False)
        store.set_pref("keep_running", "nonsense")
        store.last_used = "Gaming"
        store.save()
        again = ProfileStore(self.path)
        self.assertEqual(again.names(), ["Gaming"])
        self.assertEqual([b["gain"] for b in again.find("gaming")["bands"]], [4.0] * 10)
        self.assertFalse(again.prefs["keep_running"])
        again.rename("Gaming", "Shooters")
        self.assertEqual(again.last_used, "Shooters")
        again.remove("Shooters")
        self.assertEqual(ProfileStore(self.path).names(), [])

    def test_names_are_checked(self):
        self.assertTrue(ProfileStore.check_name("   ", []))
        self.assertTrue(ProfileStore.check_name("flat", ["Flat"]))
        self.assertTrue(ProfileStore.check_name("x" * 60, []))
        self.assertEqual(ProfileStore.check_name("Mine", ["Flat"]), "")

    def test_broken_file_starts_empty(self):
        with open(self.path, "w") as file:
            file.write("{ not json")
        self.assertEqual(ProfileStore(self.path).names(), [])


class SearchTests(unittest.TestCase):
    ENTRIES = [{"name": n} for n in ["Flat", "Late Night", "Bass Boost", "Bass Reducer", "Vocal Clarity", "My bass"]]

    def names(self, query):
        return [e["name"] for e in search(self.ENTRIES, query)]

    def test_empty_query_keeps_everything_in_order(self):
        self.assertEqual(self.names("  "), [e["name"] for e in self.ENTRIES])

    def test_starts_with_ranks_first(self):
        self.assertEqual(self.names("bass"), ["Bass Boost", "Bass Reducer", "My bass"])

    def test_every_word_must_match(self):
        self.assertEqual(self.names("bass red"), ["Bass Reducer"])
        self.assertEqual(self.names("zzz"), [])


class MicTests(unittest.TestCase):
    def test_config_listens_to_the_headset_and_names_the_clean_mic(self):
        text = mic.config_text("alsa_input.usb-Audeze_LLC_Audeze_Maxwell_Dongle-01.mono-fallback", {"level": False})
        self.assertIn("libpipewire-module-echo-cancel", text)
        self.assertIn("aec/libspa-aec-webrtc", text)
        self.assertIn('target.object = "alsa_input.usb-Audeze_LLC_Audeze_Maxwell_Dongle-01.mono-fallback"', text)
        self.assertIn("webrtc.noise_suppression = true", text)
        self.assertIn("webrtc.gain_control = false", text)
        self.assertIn(f'node.name        = "{mic.SOURCE_NAME}"', text)

    def test_config_parses_with_pipewire(self):
        dump = "/usr/bin/spa-json-dump"
        if not os.path.exists(dump):
            self.skipTest("spa-json-dump not installed")
        with tempfile.NamedTemporaryFile("w", suffix=".conf", delete=False) as file:
            file.write(mic.config_text("x"))
        result = subprocess.run([dump, file.name], capture_output=True, text=True)
        os.unlink(file.name)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_microphones_skip_our_own(self):
        dump = [
            {"id": 1, "type": "PipeWire:Interface:Node", "info": {"props": {
                "node.name": "alsa_input.usb-Audeze_LLC_Audeze_Maxwell_Dongle-01.mono-fallback",
                "node.description": "Audeze Maxwell Dongle Mono", "media.class": "Audio/Source"}}},
            {"id": 2, "type": "PipeWire:Interface:Node", "info": {"props": {
                "node.name": "minsick_hq_mic", "node.description": "Minsick HQ Microphone", "media.class": "Audio/Source"}}},
        ]
        found = pipewire.microphones(dump)
        self.assertEqual([m["id"] for m in found], [1])
        self.assertTrue(found[0]["isMaxwell"])
        self.assertEqual(pipewire.find_id(dump, "minsick_hq_mic"), 2)


class AutostartTests(unittest.TestCase):
    def test_unit_starts_in_the_background_after_the_session(self):
        text = autostart.unit_text("/opt/minsick-hq")
        self.assertIn("ExecStart=/opt/minsick-hq --background", text)
        self.assertIn("WantedBy=graphical-session.target", text)


if __name__ == "__main__":
    unittest.main()
