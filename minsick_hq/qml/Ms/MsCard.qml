// A panel with an optional heading
import QtQuick

Rectangle {
    id: card
    property string heading: ""
    default property alias content: body.data
    property alias bodyItem: body

    radius: Theme.radius
    color: Theme.card
    border.color: Theme.border

    Text {
        id: title
        visible: card.heading !== ""
        text: card.heading.toUpperCase()
        color: Theme.muted
        font.pixelSize: Theme.small
        font.weight: Font.DemiBold
        font.letterSpacing: 1.2
        anchors { left: parent.left; top: parent.top; margins: Theme.gap }
    }

    Item {
        id: body
        anchors {
            fill: parent
            margins: Theme.gap
            topMargin: card.heading !== "" ? Theme.gap + title.height + 10 : Theme.gap
        }
    }
}
