// Minsick HQ's window: a sidebar with the pages, the page itself, and the dialog queue on top.
// Closing it while the equaliser or microphone cleanup is on only hides it (see Settings)
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import Ms
import "pages"

ApplicationWindow {
    id: window
    width: 1240
    height: 800
    minimumWidth: 1000
    minimumHeight: 660
    visible: !startHidden
    title: "Minsick HQ"
    color: Theme.background

    property int page: startPage

    // Close: hide while something is running in the background, otherwise quit
    onClosing: function(close) {
        if (!hq.keepRunningWhenClosed())
            Qt.quit()
    }

    // Opening Minsick HQ again while it runs brings this window back
    Connections {
        target: instance
        function onShowRequested() {
            window.show()
            window.raise()
            window.requestActivate()
        }
    }

    Shortcut { sequence: "Ctrl+F"; onActivated: { window.page = 1; equalizer.searchField.forceActiveFocus(); equalizer.searchField.selectAll() } }
    Shortcut { sequence: "Ctrl+1"; onActivated: window.page = 0 }
    Shortcut { sequence: "Ctrl+2"; onActivated: window.page = 1 }
    Shortcut { sequence: "Ctrl+3"; onActivated: window.page = 2 }
    Shortcut { sequence: "Ctrl+4"; onActivated: window.page = 3 }
    Shortcut { sequence: "Ctrl+E"; onActivated: hq.setEqEnabled(!hq.eqEnabled) }
    Shortcut { sequence: "Ctrl+M"; onActivated: hq.setMicEnabled(!hq.micEnabled) }
    Shortcut { sequences: [StandardKey.Undo]; onActivated: hq.undo() }
    Shortcut { sequences: [StandardKey.Redo, "Ctrl+Shift+Z"]; onActivated: hq.redo() }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: 230
            Layout.fillHeight: true
            color: Theme.sidebar

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 6

                RowLayout {
                    Layout.topMargin: 8
                    Layout.bottomMargin: 22
                    spacing: 10
                    Image { source: "images/icon.svg"; sourceSize: Qt.size(34, 34) }
                    ColumnLayout {
                        spacing: 0
                        Text { text: "MINSICK"; color: Theme.text; font.pixelSize: 15; font.weight: Font.Bold; font.letterSpacing: 1.5 }
                        Text { text: "HQ"; color: Theme.accent; font.pixelSize: 12; font.weight: Font.Bold; font.letterSpacing: 3 }
                    }
                }

                MsNavButton { text: "Headset"; glyph: "◎"; current: window.page === 0; Layout.fillWidth: true; onClicked: window.page = 0 }
                MsNavButton { text: "Equaliser"; glyph: "≈"; current: window.page === 1; Layout.fillWidth: true; onClicked: window.page = 1 }
                MsNavButton { text: "Microphone"; glyph: "◉"; current: window.page === 2; Layout.fillWidth: true; onClicked: window.page = 2 }
                MsNavButton { text: "Settings"; glyph: "⚙"; current: window.page === 3; Layout.fillWidth: true; onClicked: window.page = 3 }

                Item { Layout.fillHeight: true }

                Rectangle {
                    visible: demoMode
                    Layout.fillWidth: true
                    height: 26
                    radius: 6
                    color: "#33f2b24c"
                    Text { anchors.centerIn: parent; text: "Demo devices, no real audio"; color: Theme.warning; font.pixelSize: 11 }
                }
                Text {
                    text: hq.status
                    color: Theme.muted
                    font.pixelSize: Theme.small
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    Layout.bottomMargin: 8
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 24
            currentIndex: window.page

            HeadsetPage { onOpenEqualizer: window.page = 1 }
            EqualizerPage { id: equalizer }
            MicrophonePage {}
            SettingsPage { onQuitRequested: Qt.quit() }
        }
    }

    MsDialog {}
}
