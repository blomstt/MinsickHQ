// A text button. `primary` fills it with the accent; `danger` tints it red; Button's own `flat` drops the frame
import QtQuick
import QtQuick.Controls.Basic

Button {
    id: control
    property bool primary: false
    property bool danger: false

    implicitHeight: 36
    leftPadding: 16
    rightPadding: 16
    font.pixelSize: Theme.body
    font.weight: Font.DemiBold
    hoverEnabled: true

    contentItem: Text {
        text: control.text
        font: control.font
        color: !control.enabled ? Theme.faint
             : control.primary ? Theme.background
             : control.danger ? Theme.danger
             : Theme.text
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: 8
        color: control.primary ? (control.down ? Qt.darker(Theme.accent, 1.2) : control.hovered ? Qt.lighter(Theme.accent, 1.1) : Theme.accent)
             : control.flat ? (control.hovered ? Theme.cardRaised : "transparent")
             : (control.down ? Theme.border : control.hovered ? Theme.cardRaised : Theme.card)
        border.color: control.primary || control.flat ? "transparent" : control.visualFocus ? Theme.accent : Theme.border
        opacity: control.enabled ? 1 : 0.5
        Behavior on color { ColorAnimation { duration: 90 } }
    }
}
