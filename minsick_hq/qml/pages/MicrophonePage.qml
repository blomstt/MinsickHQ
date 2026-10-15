// The microphone: which mic to clean up, what to take out, and whether the clean one becomes the
// default. Voice apps pick "Minsick HQ Microphone" like any other mic
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import Ms

Item {
    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.gap

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                spacing: 2
                Layout.fillWidth: true
                Text { text: "Microphone"; color: Theme.text; font.pixelSize: Theme.hero; font.weight: Font.Bold }
                Text {
                    text: hq.micEnabled ? "Apps can pick “Minsick HQ Microphone” for the cleaned-up sound."
                                        : "Clean up the headset's mic for calls, Discord and games."
                    color: Theme.muted
                    font.pixelSize: Theme.small
                }
            }
            Item { Layout.fillWidth: true }
            MsSwitch {
                text: hq.micEnabled ? "Cleanup on" : "Cleanup off"
                checked: hq.micEnabled
                onToggled: hq.setMicEnabled(checked)
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.gap

            MsCard {
                heading: "Clean up this microphone"
                Layout.fillWidth: true
                Layout.fillHeight: true

                ListView {
                    id: mics
                    anchors.fill: parent
                    clip: true
                    spacing: 6
                    model: hq.microphones
                    delegate: Rectangle {
                        required property var modelData
                        width: mics.width
                        height: 58
                        radius: 8
                        color: hq.micSelected === modelData.name ? Theme.cardRaised : micMouse.containsMouse ? Theme.background : "transparent"
                        border.color: hq.micSelected === modelData.name ? Theme.accentDim : "transparent"
                        MouseArea { id: micMouse; anchors.fill: parent; hoverEnabled: true; onClicked: hq.selectMic(modelData.name) }
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            spacing: 12
                            Rectangle {
                                width: 14; height: 14; radius: 7; color: "transparent"
                                border.color: hq.micSelected === modelData.name ? Theme.accent : Theme.faint
                                border.width: 2
                                Rectangle { anchors.centerIn: parent; width: 6; height: 6; radius: 3; color: Theme.accent; visible: hq.micSelected === modelData.name }
                            }
                            ColumnLayout {
                                spacing: 2
                                Layout.fillWidth: true
                                Text { text: modelData.description; color: Theme.text; font.pixelSize: Theme.body; elide: Text.ElideRight; Layout.fillWidth: true }
                                Text {
                                    text: modelData.api + (modelData.isMaxwell ? " · Maxwell" : "") + (modelData.isDefault ? " · Default" : "")
                                    color: Theme.muted; font.pixelSize: Theme.small
                                }
                            }
                        }
                    }
                    Text {
                        anchors.centerIn: parent
                        visible: mics.count === 0
                        text: "No microphones right now. Connect your Maxwell."
                        color: Theme.muted
                        font.pixelSize: Theme.body
                    }
                }
            }

            MsCard {
                heading: "What to take out"
                Layout.preferredWidth: 380
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 14
                    Repeater {
                        model: [
                            { key: "mic_noise", title: "Background noise", text: "Fans, hum, a busy room. Steady sounds fade out while you talk." },
                            { key: "mic_level", title: "Uneven level", text: "Quiet and loud moments come out at a steady volume." },
                            { key: "mic_rumble", title: "Low rumble", text: "Desk bumps, breath and handling noise below the voice." },
                        ]
                        delegate: RowLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: 12
                            ColumnLayout {
                                spacing: 2
                                Layout.fillWidth: true
                                Text { text: modelData.title; color: Theme.text; font.pixelSize: Theme.body; font.weight: Font.DemiBold }
                                Text { text: modelData.text; color: Theme.muted; font.pixelSize: Theme.small; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            }
                            MsSwitch { checked: hq.prefs[modelData.key]; onToggled: hq.setPref(modelData.key, checked) }
                        }
                    }
                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.border }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        ColumnLayout {
                            spacing: 2
                            Layout.fillWidth: true
                            Text { text: "Make it the default microphone"; color: Theme.text; font.pixelSize: Theme.body; font.weight: Font.DemiBold }
                            Text { text: "Apps that use the default get the clean sound without changing their settings. Switching cleanup off gives the old default back."; color: Theme.muted; font.pixelSize: Theme.small; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        }
                        MsSwitch { checked: hq.prefs.mic_make_default; onToggled: hq.setPref("mic_make_default", checked) }
                    }
                    Item { Layout.fillHeight: true }
                    Text {
                        text: "Echo from speakers is removed too. With headphones there's little to remove."
                        color: Theme.faint
                        font.pixelSize: Theme.small
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }
        }
    }
}
