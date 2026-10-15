// A single-line text field. `icon` puts a glyph in front, for the search box
import QtQuick
import QtQuick.Controls.Basic

TextField {
    id: control
    property string icon: ""

    implicitHeight: 38
    leftPadding: icon ? 34 : 12
    rightPadding: 12
    font.pixelSize: Theme.body
    color: Theme.text
    placeholderTextColor: Theme.faint
    selectionColor: Theme.accentDim
    selectedTextColor: Theme.text

    background: Rectangle {
        radius: 8
        color: Theme.background
        border.color: control.activeFocus ? Theme.accent : Theme.border
        Behavior on border.color { ColorAnimation { duration: 90 } }

        Text {
            visible: control.icon !== ""
            text: control.icon
            color: Theme.muted
            font.pixelSize: 15
            anchors.left: parent.left
            anchors.leftMargin: 11
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}
