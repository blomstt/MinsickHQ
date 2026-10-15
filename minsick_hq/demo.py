"""Sample PipeWire state for --demo: the Maxwell on its USB dongle with its microphone, a
Bluetooth pair and speakers. Lets the app be tried and screenshotted without the headset plugged in."""
DEMO_DUMP = [
    {"id": 40, "type": "PipeWire:Interface:Device",
     "info": {"props": {"device.description": "Audeze Maxwell Dongle", "device.api": "alsa"}}},
    {"id": 41, "type": "PipeWire:Interface:Device",
     "info": {"props": {"device.description": "WH-1000XM4", "device.api": "bluez5", "device.form-factor": "headphone"}}},
    {"id": 70, "type": "PipeWire:Interface:Node", "info": {"props": {
        "node.name": "alsa_output.usb-Audeze_LLC_Audeze_Maxwell_Dongle_0000000000000000-01.analog-stereo",
        "node.description": "Audeze Maxwell", "media.class": "Audio/Sink", "device.id": 40}}},
    {"id": 71, "type": "PipeWire:Interface:Node", "info": {"props": {
        "node.name": "bluez_output.AA_BB.1", "node.description": "WH-1000XM4",
        "media.class": "Audio/Sink", "device.id": 41, "device.api": "bluez5"}}},
    {"id": 72, "type": "PipeWire:Interface:Node", "info": {"props": {
        "node.name": "alsa_output.pci-0000_0c_00.4.analog-stereo", "node.description": "Desk speakers",
        "media.class": "Audio/Sink"}}},
    {"id": 73, "type": "PipeWire:Interface:Node", "info": {"props": {
        "node.name": "alsa_input.usb-Audeze_LLC_Audeze_Maxwell_Dongle_0000000000000000-01.mono-fallback",
        "node.description": "Audeze Maxwell microphone", "media.class": "Audio/Source", "device.id": 40}}},
    {"id": 0, "type": "PipeWire:Interface:Metadata", "props": {"metadata.name": "default"}, "metadata": [
        {"subject": 0, "key": "default.audio.sink", "type": "Spa:String:JSON",
         "value": {"name": "alsa_output.usb-Audeze_LLC_Audeze_Maxwell_Dongle_0000000000000000-01.analog-stereo"}}]},
]
