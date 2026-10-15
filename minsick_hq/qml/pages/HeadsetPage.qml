// The headset page: is the Maxwell here, how it's connected, and every output to play into
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import Ms

Item {
    id: page
    signal openEqualizer()
    property var maxwell: hq.maxwell
    property bool connected: maxwell.name !== undefined

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.gap

        // The headset itself
        MsCard {
            Layout.fillWidth: true
            Layout.preferredHeight: 210

            RowLayout {
                anchors.fill: parent
                spacing: 28

                Rectangle {
                    Layout.preferredWidth: 150
                    Layout.preferredHeight: 150
                    radius: 75
                    color: page.connected ? Theme.cardRaised : Theme.background
                    border.color: page.connected ? Theme.accent : Theme.border
                    border.width: 2
                    Image {
                        anchors.centerIn: parent
                        source: "../images/icon.svg"
                        sourceSize: Qt.size(96, 96)
                        opacity: page.connected ? 1 : 0.3
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text {
                        text: page.connected ? page.maxwell.description : "Maxwell not connected"
                        color: Theme.text
                        font.pixelSize: Theme.hero
                        font.weight: Font.Bold
                    }
                    Text {
                        text: page.connected
                              ? (page.maxwell.api === "Bluetooth" ? "Connected over Bluetooth" : "Connected through the USB dongle")
                              : "Plug in the USB dongle or pair it over Bluetooth. It shows up here within a few seconds."
                        color: Theme.muted
                        font.pixelSize: Theme.body
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    Flow {
                        spacing: 8
                        Layout.topMargin: 4
                        Repeater {
                            model: page.connected ? [
                                page.maxwell.isDefault ? "Default output" : "",
                                hq.eqEnabled && hq.selected === page.maxwell.name ? "Equaliser on: " + hq.activeName : "",
                            ].filter(function(t) { return t !== "" }) : []
                            delegate: Rectangle {
                                radius: 12
                                height: 24
                                width: badgeText.implicitWidth + 20
                                color: Theme.accentDim
                                Text { id: badgeText; anchors.centerIn: parent; text: modelData; color: Theme.text; font.pixelSize: Theme.small }
                            }
                        }
                    }
                    RowLayout {
                        Layout.topMargin: 10
                        spacing: 10
                        visible: page.connected
                        MsButton {
                            text: "Use as output"
                            visible: !page.maxwell.isDefault && !hq.eqEnabled
                            primary: true
                            onClicked: hq.useAsOutput(page.maxwell.id)
                        }
                        MsButton { text: "Open equaliser"; onClicked: page.openEqualizer() }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.gap

            // Every output, the chosen one marked
            MsCard {
                heading: "Outputs"
                Layout.fillWidth: true
                Layout.fillHeight: true

                ListView {
                    id: outputs
                    anchors.fill: parent
                    clip: true
                    spacing: 6
                    model: hq.devices
                    delegate: Rectangle {
                        required property var modelData
                        width: outputs.width
                        height: 58
                        radius: 8
                        color: hq.selected === modelData.name ? Theme.cardRaised : rowMouse.containsMouse ? Theme.background : "transparent"
                        border.color: hq.selected === modelData.name ? Theme.accentDim : "transparent"

                        MouseArea { id: rowMouse; anchors.fill: parent; hoverEnabled: true; onClicked: hq.selectDevice(modelData.name) }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 10
                            spacing: 12
                            Rectangle {
                                width: 14; height: 14; radius: 7
                                color: "transparent"
                                border.color: hq.selected === modelData.name ? Theme.accent : Theme.faint
                                border.width: 2
                                Rectangle { anchors.centerIn: parent; width: 6; height: 6; radius: 3; color: Theme.accent; visible: hq.selected === modelData.name }
                            }
                            ColumnLayout {
                                spacing: 2
                                Layout.fillWidth: true
                                Text { text: modelData.description; color: Theme.text; font.pixelSize: Theme.body; elide: Text.ElideRight; Layout.fillWidth: true }
                                Text {
                                    text: modelData.api + (modelData.isMaxwell ? " · Maxwell" : modelData.isHeadphones ? " · Headphones" : "") + (modelData.isDefault ? " · Default" : "")
                                    color: Theme.muted; font.pixelSize: Theme.small
                                }
                            }
                            MsButton {
                                text: hq.eqEnabled ? "Play through EQ" : "Use"
                                flat: true
                                visible: hq.eqEnabled ? hq.selected !== modelData.name : !modelData.isDefault
                                onClicked: hq.useAsOutput(modelData.id)
                            }
                        }
                    }
                    Text {
                        anchors.centerIn: parent
                        visible: outputs.count === 0
                        text: "PipeWire reports no outputs right now."
                        color: Theme.muted
                        font.pixelSize: Theme.body
                    }
                }
            }

            // The equaliser in brief
            MsCard {
                heading: "Equaliser"
                Layout.preferredWidth: 320
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 12
                    MsSwitch {
                        text: hq.eqEnabled ? "On" : "Off"
                        checked: hq.eqEnabled
                        onToggled: hq.setEqEnabled(checked)
                    }
                    Text { text: hq.activeName + (hq.modified ? " (changed)" : ""); color: Theme.text; font.pixelSize: Theme.title; font.weight: Font.DemiBold }
                    ResponseGraph {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 90
                        curve: hq.curve
                    }
                    Text {
                        text: "Sound goes through a PipeWire equaliser into the output picked on the left. Switching it off hands your previous output back."
                        color: Theme.muted
                        font.pixelSize: Theme.small
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }
        }
    }
}
