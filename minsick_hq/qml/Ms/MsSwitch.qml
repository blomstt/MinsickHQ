// An on/off switch with an optional label
import QtQuick
import QtQuick.Controls.Basic

Switch {
    id: control
    hoverEnabled: true
    font.pixelSize: Theme.body

    indicator: Rectangle {
        implicitWidth: 44
        implicitHeight: 24
        x: control.leftPadding
        y: (control.height - height) / 2
        radius: 12
        color: control.checked ? Theme.accent : Theme.cardRaised
        border.color: control.checked ? Theme.accent : Theme.border
        Behavior on color { ColorAnimation { duration: 120 } }

        Rectangle {
            width: 18; height: 18; radius: 9
            y: 3
            x: control.checked ? parent.width - width - 3 : 3
            color: control.checked ? Theme.background : Theme.muted
            Behavior on x { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
        }
    }

    contentItem: Text {
        text: control.text
        font: control.font
        color: Theme.text
        verticalAlignment: Text.AlignVCenter
        leftPadding: control.indicator.width + (control.text ? 10 : 0)
    }
}
