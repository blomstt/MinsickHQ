// One equaliser band: its gain above, a vertical slider, its frequency below. Clicking it selects
// the band for the editor; double-click puts it back to 0 dB. Arrow keys move it a tenth of a dB
import QtQuick
import QtQuick.Controls.Basic

Item {
    id: band
    property real value: 0
    property real from: -20
    property real to: 20
    property string label: ""
    property bool selected: false
    signal moved(real value)
    signal picked()

    implicitWidth: 52
    implicitHeight: 260

    Text {
        id: valueText
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        text: (band.value > 0 ? "+" : "") + band.value.toFixed(1)
        color: band.value === 0 ? Theme.muted : Theme.text
        font.pixelSize: Theme.small
        font.weight: Font.DemiBold
        font.family: "monospace"
    }

    Slider {
        id: slider
        orientation: Qt.Vertical
        from: band.from
        to: band.to
        stepSize: 0.1
        value: band.value
        anchors { top: valueText.bottom; bottom: freqText.top; horizontalCenter: parent.horizontalCenter; topMargin: 8; bottomMargin: 8 }
        width: 36
        onMoved: band.moved(value)
        onPressedChanged: if (pressed) band.picked()

        background: Item {
            x: slider.leftPadding + slider.availableWidth / 2 - width / 2
            y: slider.topPadding
            width: 4
            height: slider.availableHeight
            Rectangle { anchors.fill: parent; radius: 2; color: Theme.cardRaised }
            // The 0 dB tick
            Rectangle {
                width: 16; height: 1; color: Theme.faint
                anchors.horizontalCenter: parent.horizontalCenter
                y: parent.height * (band.to / (band.to - band.from))
            }
            // Filled from 0 dB toward the handle
            Rectangle {
                width: parent.width
                radius: 2
                color: band.value >= 0 ? Theme.accent : Theme.accentDim
                property real zero: parent.height * (band.to / (band.to - band.from))
                property real here: slider.visualPosition * parent.height
                y: Math.min(zero, here)
                height: Math.abs(zero - here)
            }
        }

        handle: Rectangle {
            x: slider.leftPadding + slider.availableWidth / 2 - width / 2
            y: slider.topPadding + slider.visualPosition * (slider.availableHeight - height)
            width: 22; height: 22; radius: 11
            color: slider.pressed || band.selected ? Theme.accent : Theme.text
            border.color: slider.visualFocus ? Theme.text : Theme.background
            border.width: 3
        }

        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton
            propagateComposedEvents: true
            onPressed: function(mouse) { mouse.accepted = false }
            onDoubleClicked: band.moved(0)
        }
    }

    Text {
        id: freqText
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        text: band.label
        color: band.selected ? Theme.accent : Theme.muted
        font.weight: band.selected ? Font.DemiBold : Font.Normal
        font.pixelSize: Theme.small
    }
}
