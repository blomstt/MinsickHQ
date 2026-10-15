// A row of choices where one is picked, like the band type: Low shelf, Peak, High shelf
import QtQuick
import QtQuick.Controls.Basic

Row {
    id: control
    property var options: []      // [{ "value": ..., "label": ... }]
    property var current
    signal picked(var value)

    spacing: 4
    Repeater {
        model: control.options
        delegate: AbstractButton {
            required property var modelData
            required property int index
            property bool on: modelData.value === control.current
            implicitHeight: 34
            implicitWidth: label.implicitWidth + 24
            hoverEnabled: true
            onClicked: control.picked(modelData.value)
            background: Rectangle {
                color: parent.on ? Theme.accentDim : parent.hovered ? Theme.cardRaised : Theme.background
                border.color: parent.on ? Theme.accent : Theme.border
                radius: 6
            }
            contentItem: Text {
                id: label
                text: modelData.label
                color: parent.on ? Theme.text : Theme.muted
                font.pixelSize: Theme.small
                font.weight: parent.on ? Font.DemiBold : Font.Normal
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }
    }
}
