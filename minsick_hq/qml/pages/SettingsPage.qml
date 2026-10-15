// Settings: what happens when the window closes, starting at login, how profile edits are saved,
// and about the app (licence, credits, the not-affiliated notice)
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import Ms

Item {
    signal quitRequested()

    component Choice: RowLayout {
        property string title
        property string detail
        property alias checked: toggle.checked
        signal toggled(bool on)
        Layout.fillWidth: true
        spacing: 16
        ColumnLayout {
            spacing: 2
            Layout.fillWidth: true
            Text { text: title; color: Theme.text; font.pixelSize: Theme.body; font.weight: Font.DemiBold }
            Text { text: detail; color: Theme.muted; font.pixelSize: Theme.small; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        }
        MsSwitch { id: toggle; onToggled: parent.toggled(checked) }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.gap

        Text { text: "Settings"; color: Theme.text; font.pixelSize: Theme.hero; font.weight: Font.Bold }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.gap

            MsCard {
                heading: "Running"
                Layout.fillWidth: true
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 20
                    Choice {
                        title: "Keep running when the window closes"
                        detail: "While the equaliser or the microphone cleanup is on, closing the window leaves them working. Open Minsick HQ again from the launcher to bring the window back."
                        checked: hq.prefs.keep_running
                        onToggled: function(on) { hq.setPref("keep_running", on) }
                    }
                    Choice {
                        title: "Start when I log in"
                        detail: "Starts in the background with the equaliser and microphone as you left them, through a systemd user service."
                        checked: hq.startOnLogin
                        onToggled: function(on) { hq.setStartOnLogin(on) }
                    }
                    Choice {
                        title: "Save edits to my profiles as I make them"
                        detail: "Off: changes to one of your profiles wait for the Save button, so you can try things and go back."
                        checked: hq.prefs.autosave_profiles
                        onToggled: function(on) { hq.setPref("autosave_profiles", on) }
                    }
                    Item { Layout.fillHeight: true }
                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "Quitting switches the equaliser and microphone cleanup off and gives your previous output and mic back."
                            color: Theme.muted; font.pixelSize: Theme.small; wrapMode: Text.WordWrap; Layout.fillWidth: true
                        }
                        MsButton { text: "Quit Minsick HQ"; danger: true; onClicked: quitRequested() }
                    }
                }
            }

            MsCard {
                heading: "About"
                Layout.preferredWidth: 420
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 12
                    RowLayout {
                        spacing: 12
                        Image { source: "../images/icon.svg"; sourceSize: Qt.size(44, 44) }
                        ColumnLayout {
                            spacing: 0
                            Text { text: "Minsick HQ"; color: Theme.text; font.pixelSize: Theme.title; font.weight: Font.Bold }
                            Text { text: "Version " + appVersion + " · MIT licence"; color: Theme.muted; font.pixelSize: Theme.small }
                        }
                    }
                    Text {
                        text: "An independent project, not affiliated with or endorsed by Audeze LLC. Audeze, Maxwell and Audeze HQ are trademarks of Audeze LLC."
                        color: Theme.muted; font.pixelSize: Theme.small; wrapMode: Text.WordWrap; Layout.fillWidth: true
                    }
                    Text {
                        text: "Headset corrections from the AutoEQ project (MIT), measured by Rtings and Kuulokenurkka. Filter formulas from Robert Bristow-Johnson's Audio EQ Cookbook. Audio by PipeWire; interface by Qt for Python (LGPL-3.0)."
                        color: Theme.muted; font.pixelSize: Theme.small; wrapMode: Text.WordWrap; Layout.fillWidth: true
                    }
                    Item { Layout.fillHeight: true }
                    Text { text: "Shortcuts"; color: Theme.text; font.pixelSize: Theme.body; font.weight: Font.DemiBold }
                    Text {
                        text: "Ctrl+1 to 4  pages\nCtrl+F  search presets\nCtrl+E  equaliser on or off\nCtrl+M  microphone cleanup on or off\nCtrl+Z, Ctrl+Shift+Z  undo, redo"
                        color: Theme.muted; font.pixelSize: Theme.small; font.family: "monospace"; lineHeight: 1.3
                    }
                }
            }
        }
    }
}
