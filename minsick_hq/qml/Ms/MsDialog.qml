// Shows whatever the dialog queue has at the front: a message, a yes/no question, or a name
// prompt. Closing it lets the next one in the queue through
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Popup {
    id: popup
    property var entry: dialogs.current
    property string problem: ""

    anchors.centerIn: Overlay.overlay
    width: 420
    modal: true
    focus: true
    visible: dialogs.open
    closePolicy: Popup.CloseOnEscape
    padding: 24

    onOpened: {
        problem = ""
        // Renaming starts from the current name
        nameField.text = entry.action === "rename" ? entry.value : ""
        if (entry.kind === "name") { nameField.forceActiveFocus(); nameField.selectAll() }
    }
    onClosed: if (dialogs.open) dialogs.done()

    function accept() {
        if (entry.kind === "message") { dialogs.done(); return }
        var result = hq.confirm(entry.action, entry.value || "", entry.kind === "name" ? nameField.text : "")
        if (result !== "") { problem = result; return }
        dialogs.done()
    }

    Overlay.modal: Rectangle { color: "#b0000000" }
    background: Rectangle { radius: 14; color: Theme.card; border.color: Theme.border }

    contentItem: ColumnLayout {
        spacing: 14
        Text {
            text: popup.entry.title || ""
            color: Theme.text
            font.pixelSize: Theme.title
            font.weight: Font.DemiBold
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }
        Text {
            visible: text !== ""
            text: popup.entry.text || ""
            color: Theme.muted
            font.pixelSize: Theme.body
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }
        MsTextField {
            id: nameField
            visible: popup.entry.kind === "name"
            placeholderText: "Profile name"
            Layout.fillWidth: true
            onAccepted: popup.accept()
            onTextChanged: popup.problem = ""
        }
        Text {
            visible: popup.problem !== ""
            text: popup.problem
            color: Theme.danger
            font.pixelSize: Theme.small
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 6
            spacing: 10
            Item { Layout.fillWidth: true }
            MsButton {
                visible: popup.entry.kind !== "message"
                text: "Cancel"
                flat: true
                onClicked: dialogs.done()
            }
            MsButton {
                text: popup.entry.kind === "message" ? "OK" : popup.entry.action === "delete" ? "Delete"
                    : popup.entry.action === "rename" ? "Rename" : "Save"
                primary: popup.entry.action !== "delete"
                danger: popup.entry.action === "delete"
                onClicked: popup.accept()
            }
        }
    }
}
