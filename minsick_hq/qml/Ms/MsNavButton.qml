// A page button in the sidebar: a glyph, a label, and an accent bar when it's the current page
import QtQuick
import QtQuick.Controls.Basic

AbstractButton {
    id: control
    property string glyph: ""
    property bool current: false

    implicitHeight: 44
    hoverEnabled: true

    background: Rectangle {
        radius: 8
        color: control.current ? Theme.cardRaised : control.hovered ? Theme.card : "transparent"
        Rectangle {
            visible: control.current
            width: 3; radius: 2
            height: parent.height - 18
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            color: Theme.accent
        }
    }

    contentItem: Row {
        leftPadding: 16
        spacing: 12
        Text {
            text: control.glyph
            font.pixelSize: 17
            color: control.current ? Theme.accent : Theme.muted
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            text: control.text
            font.pixelSize: Theme.body
            font.weight: control.current ? Font.DemiBold : Font.Normal
            color: control.current ? Theme.text : Theme.muted
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}
