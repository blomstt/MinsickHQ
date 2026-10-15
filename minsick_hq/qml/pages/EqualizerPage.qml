// The equaliser: the curve with a handle per band, ten sliders and a preamp, an editor for the
// selected band (type, frequency, width, gain), and a searchable list of presets, the headset
// corrections and my own profiles. AutoEQ ParametricEQ.txt files can be imported and exported
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts
import Ms

Item {
    id: page
    property alias searchField: search
    property var band: hq.bands[hq.selectedBand] || ({ kind: "peaking", freq: 1000, q: 1, gain: 0 })

    function freqLabel(f) {
        if (f >= 1000) return (f / 1000).toFixed(f >= 10000 || f % 1000 < 50 ? 0 : 1) + "k"
        return Math.round(f).toString()
    }

    FileDialog {
        id: importDialog
        title: "Import an AutoEQ ParametricEQ.txt"
        nameFilters: ["EQ files (*.txt)", "All files (*)"]
        onAccepted: hq.importFile(selectedFile.toString())
    }
    FileDialog {
        id: exportDialog
        title: "Export as ParametricEQ.txt"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "txt"
        nameFilters: ["EQ files (*.txt)"]
        currentFile: "file:///" + hq.activeName + " ParametricEQ.txt"
        onAccepted: hq.exportFile(selectedFile.toString())
    }

    RowLayout {
        anchors.fill: parent
        spacing: Theme.gap

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            // Which curve, what it is, undo, on or off
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                ColumnLayout {
                    spacing: 2
                    Layout.fillWidth: true
                    Text {
                        text: hq.activeName; color: Theme.text; font.pixelSize: Theme.hero; font.weight: Font.Bold
                        // Long names shrink to fit before they're cut off
                        fontSizeMode: Text.HorizontalFit; minimumPixelSize: 18; elide: Text.ElideRight
                        Layout.fillWidth: true; Layout.preferredHeight: 38
                    }
                    Text {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        maximumLineCount: 3
                        elide: Text.ElideRight
                        text: hq.modified
                              ? (hq.activeIsMine ? "Changed. Press Save to keep it." : "Changed from the preset. Save it as a profile to keep it.")
                              : hq.activeNote !== "" ? hq.activeNote
                              : "Drag the numbered points on the graph, or pick a preset on the right."
                        color: hq.modified ? Theme.warning : Theme.muted
                        font.pixelSize: Theme.small
                    }
                }
                MsButton { text: "↶"; flat: true; enabled: hq.canUndo; implicitWidth: 38; onClicked: hq.undo(); ToolTip.visible: hovered; ToolTip.text: "Undo (Ctrl+Z)" }
                MsButton { text: "↷"; flat: true; enabled: hq.canRedo; implicitWidth: 38; onClicked: hq.redo(); ToolTip.visible: hovered; ToolTip.text: "Redo (Ctrl+Shift+Z)" }
                MsSwitch {
                    text: hq.eqEnabled ? "Equaliser on" : "Equaliser off"
                    checked: hq.eqEnabled
                    onToggled: hq.setEqEnabled(checked)
                }
            }

            MsCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 200
                ResponseGraph {
                    anchors.fill: parent
                    interactive: true
                    curve: hq.curve
                    bands: hq.bands
                    selectedBand: hq.selectedBand
                    range: 20
                    onBandSelected: function(i) { hq.selectBand(i) }
                    onBandMoved: function(i, freq, gain) {
                        hq.setBand(i, "freq", Math.round(freq))
                        hq.setBand(i, "gain", gain)
                    }
                    onBandWidened: function(i, factor) { hq.setBand(i, "q", hq.bands[i].q * factor) }
                    onBandFlattened: function(i) { hq.setBand(i, "gain", 0) }
                }
                Text {
                    visible: hq.peak > 0.05
                    anchors { right: parent.right; top: parent.top }
                    text: "Peaks at +" + hq.peak.toFixed(1) + " dB and may clip. Lower the preamp or press Auto preamp."
                    color: Theme.warning
                    font.pixelSize: Theme.small
                }
            }

            // Ten sliders and the preamp, then the selected band's details
            MsCard {
                Layout.fillWidth: true
                Layout.preferredHeight: 300

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 0
                        MsBandSlider {
                            Layout.fillHeight: true
                            Layout.preferredWidth: 60
                            label: "PRE"
                            from: hq.ranges.preamp[0]; to: hq.ranges.preamp[1]
                            value: hq.preamp
                            onMoved: function(v) { hq.setPreamp(v) }
                        }
                        Rectangle { Layout.fillHeight: true; Layout.preferredWidth: 1; Layout.margins: 6; color: Theme.border }
                        Repeater {
                            model: hq.bands
                            delegate: MsBandSlider {
                                required property int index
                                required property var modelData
                                Layout.fillHeight: true
                                Layout.fillWidth: true
                                label: page.freqLabel(modelData.freq) + (modelData.kind === "lowshelf" ? " ┐" : modelData.kind === "highshelf" ? " ┌" : "")
                                value: modelData.gain
                                selected: index === hq.selectedBand
                                onMoved: function(v) { hq.setGain(index, v) }
                                onPicked: hq.selectBand(index)
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.border }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        Text { text: "Band " + (hq.selectedBand + 1); color: Theme.text; font.pixelSize: Theme.body; font.weight: Font.DemiBold; Layout.preferredWidth: 58 }
                        MsSegmented {
                            options: [{ value: "lowshelf", label: "Low shelf" }, { value: "peaking", label: "Peak" }, { value: "highshelf", label: "High shelf" }]
                            current: page.band.kind
                            onPicked: function(value) { hq.setBand(hq.selectedBand, "kind", value) }
                        }
                        Item { Layout.fillWidth: true }
                        MsNumberField {
                            value: page.band.freq; unit: "Hz"; decimals: 0; logStep: true
                            from: hq.ranges.freq[0]; to: hq.ranges.freq[1]
                            onCommitted: function(v) { hq.setBand(hq.selectedBand, "freq", v) }
                        }
                        MsNumberField {
                            implicitWidth: 86
                            value: page.band.q; unit: "Q"; decimals: 2; step: 0.05
                            from: hq.ranges.q[0]; to: hq.ranges.q[1]
                            onCommitted: function(v) { hq.setBand(hq.selectedBand, "q", v) }
                        }
                        MsNumberField {
                            implicitWidth: 96
                            value: page.band.gain; unit: "dB"; decimals: 1
                            from: hq.ranges.gain[0]; to: hq.ranges.gain[1]
                            onCommitted: function(v) { hq.setBand(hq.selectedBand, "gain", v) }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                MsButton { text: "Reset"; enabled: hq.modified; onClicked: hq.reset() }
                MsButton { text: "Auto preamp"; onClicked: hq.autoPreamp() }
                Item { Layout.fillWidth: true }
                MsButton { text: "Import…"; flat: true; onClicked: importDialog.open() }
                MsButton { text: "Export…"; flat: true; onClicked: exportDialog.open() }
                MsButton { text: "Save"; visible: hq.activeIsMine && !hq.prefs.autosave_profiles; enabled: hq.modified; primary: true; onClicked: hq.saveChanges() }
                MsButton { text: "Save as profile"; primary: !(hq.activeIsMine && !hq.prefs.autosave_profiles); onClicked: hq.askSave() }
            }
        }

        // Presets, corrections and my profiles, searchable
        MsCard {
            heading: "Presets and profiles"
            Layout.preferredWidth: 300
            Layout.fillHeight: true

            ColumnLayout {
                anchors.fill: parent
                spacing: 10

                MsTextField {
                    id: search
                    Layout.fillWidth: true
                    icon: "⌕"
                    placeholderText: "Search  (Ctrl+F)"
                    onTextChanged: hq.setSearch(text)
                    Keys.onEscapePressed: text = ""
                    // Enter loads the best match
                    onAccepted: if (hq.entries.length > 0) hq.applyEntry(hq.entries[0].name)
                }

                ListView {
                    id: list
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 4
                    model: hq.entries
                    section.property: "builtIn"
                    section.delegate: Text {
                        required property string section
                        text: section === "true" ? "PRESETS" : "MY PROFILES"
                        color: Theme.faint
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                        font.letterSpacing: 1.2
                        topPadding: 10
                        bottomPadding: 6
                    }
                    delegate: Rectangle {
                        required property var modelData
                        property bool active: hq.activeName === modelData.name
                        property bool correction: modelData.note !== ""
                        width: list.width
                        height: correction ? 54 : 42
                        radius: 8
                        color: active ? Theme.cardRaised : entryMouse.containsMouse ? Theme.background : "transparent"
                        border.color: active ? Theme.accentDim : "transparent"

                        MouseArea { id: entryMouse; anchors.fill: parent; hoverEnabled: true; onClicked: hq.applyEntry(modelData.name) }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 6
                            spacing: 6
                            ColumnLayout {
                                spacing: 1
                                Layout.fillWidth: true
                                Text {
                                    text: modelData.name
                                    color: active ? Theme.accent : Theme.text
                                    font.pixelSize: Theme.body
                                    font.weight: active ? Font.DemiBold : Font.Normal
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                                Text {
                                    visible: correction
                                    text: "Measured correction · AutoEQ"
                                    color: Theme.muted
                                    font.pixelSize: 11
                                }
                            }
                            MsButton {
                                visible: !modelData.builtIn && entryMouse.containsMouse
                                text: "✎"; flat: true
                                implicitWidth: 30; leftPadding: 0; rightPadding: 0
                                onClicked: hq.askRename(modelData.name)
                            }
                            MsButton {
                                visible: !modelData.builtIn && entryMouse.containsMouse
                                text: "✕"; flat: true; danger: true
                                implicitWidth: 30; leftPadding: 0; rightPadding: 0
                                onClicked: hq.askDelete(modelData.name)
                            }
                        }
                    }
                    Text {
                        anchors.centerIn: parent
                        visible: list.count === 0
                        text: "Nothing matches “" + search.text + "”"
                        color: Theme.muted
                        font.pixelSize: Theme.body
                    }
                }
            }
        }
    }
}
