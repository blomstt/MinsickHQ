// A number with a unit, typed in. Enter or leaving the field commits it; Escape puts it back.
// Up and down arrows step it (by `step`, or 10% for a log value like frequency)
import QtQuick
import QtQuick.Controls.Basic

MsTextField {
    id: field
    property real value: 0
    property int decimals: 1
    property string unit: ""
    property real from: -1e9
    property real to: 1e9
    property real step: 0.1
    property bool logStep: false
    signal committed(real value)

    implicitWidth: 110
    horizontalAlignment: TextInput.AlignRight
    rightPadding: unitText.implicitWidth + 16
    validator: DoubleValidator { notation: DoubleValidator.StandardNotation }
    text: value.toFixed(decimals)

    // Show the current value whenever it changes from outside and I'm not typing
    onValueChanged: if (!activeFocus) text = value.toFixed(decimals)
    onEditingFinished: commit(parseFloat(text))
    Keys.onEscapePressed: { text = value.toFixed(decimals); focus = false }
    Keys.onUpPressed: commit(logStep ? value * 1.1 : value + step)
    Keys.onDownPressed: commit(logStep ? value / 1.1 : value - step)

    function commit(number) {
        if (isNaN(number)) { text = value.toFixed(decimals); return }
        number = Math.max(from, Math.min(to, number))
        committed(number)
        text = number.toFixed(decimals)
    }

    Text {
        id: unitText
        text: field.unit
        color: Theme.muted
        font.pixelSize: Theme.small
        anchors.right: parent.right
        anchors.rightMargin: 10
        anchors.verticalCenter: parent.verticalCenter
    }
}
