// The equaliser's response curve, 20 Hz to 20 kHz across and -20 to +20 dB up. Anything above
// 0 dB after the preamp is tinted as a clipping warning.
// With `interactive`, each band has a numbered handle: drag it to move the band (sideways for
// frequency, up and down for gain), scroll over it to make it wider or narrower, double-click to
// flatten it. Clicking selects it
import QtQuick

Item {
    id: graph
    property var curve: []
    property var bands: []
    property int selectedBand: -1
    property bool interactive: false
    property real range: 20

    signal bandSelected(int index)
    signal bandMoved(int index, real freq, real gain)
    signal bandWidened(int index, real factor)
    signal bandFlattened(int index)

    function xFor(freq) { return width * Math.log(freq / 20) / Math.log(1000) }
    function freqFor(x) { return 20 * Math.pow(1000, Math.max(0, Math.min(1, x / width))) }
    function yFor(db) { return height / 2 - db / range * (height / 2) }
    function gainFor(y) { return Math.max(-range, Math.min(range, (height / 2 - y) / (height / 2) * range)) }

    onCurveChanged: canvas.requestPaint()
    onWidthChanged: canvas.requestPaint()
    onHeightChanged: canvas.requestPaint()

    Canvas {
        id: canvas
        anchors.fill: parent

        // The area between the curve and 0 dB, as the current path
        function traceArea(ctx) {
            var step = width / (graph.curve.length - 1)
            ctx.beginPath()
            ctx.moveTo(0, graph.yFor(0))
            for (var j = 0; j < graph.curve.length; j++)
                ctx.lineTo(j * step, graph.yFor(Math.max(-graph.range, Math.min(graph.range, graph.curve[j]))))
            ctx.lineTo(width, graph.yFor(0))
            ctx.closePath()
        }

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            ctx.font = "11px sans-serif"
            ctx.lineWidth = 1
            // Every 5 dB across, and the decades and their halves up
            for (var db = -graph.range + 5; db < graph.range; db += 5) {
                ctx.strokeStyle = db === 0 ? "#3a424d" : "#20262d"
                ctx.beginPath(); ctx.moveTo(0, graph.yFor(db)); ctx.lineTo(width, graph.yFor(db)); ctx.stroke()
                ctx.fillStyle = "#545d69"
                ctx.fillText((db > 0 ? "+" : "") + db, 4, graph.yFor(db) - 4)
            }
            var marks = [[50, "50"], [100, "100"], [200, "200"], [500, "500"], [1000, "1k"], [2000, "2k"], [5000, "5k"], [10000, "10k"]]
            for (var m = 0; m < marks.length; m++) {
                var x = graph.xFor(marks[m][0])
                ctx.strokeStyle = "#1c2128"
                ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke()
                ctx.fillStyle = "#454d58"
                ctx.fillText(marks[m][1], x + 4, height - 6)
            }
            if (graph.curve.length < 2)
                return
            traceArea(ctx)
            var fill = ctx.createLinearGradient(0, 0, 0, height)
            fill.addColorStop(0, "rgba(79, 209, 176, 0.28)")
            fill.addColorStop(0.5, "rgba(79, 209, 176, 0.06)")
            fill.addColorStop(1, "rgba(79, 209, 176, 0.28)")
            ctx.fillStyle = fill
            ctx.fill()
            // Clipping: the part of that area above 0 dB
            ctx.save()
            ctx.beginPath(); ctx.rect(0, 0, width, graph.yFor(0)); ctx.clip()
            traceArea(ctx)
            ctx.fillStyle = "rgba(242, 178, 76, 0.4)"
            ctx.fill()
            ctx.restore()
            var step = width / (graph.curve.length - 1)
            ctx.beginPath()
            for (var k = 0; k < graph.curve.length; k++) {
                var y = graph.yFor(Math.max(-graph.range, Math.min(graph.range, graph.curve[k])))
                if (k === 0) ctx.moveTo(0, y); else ctx.lineTo(k * step, y)
            }
            ctx.strokeStyle = "#4fd1b0"
            ctx.lineWidth = 2.5
            ctx.stroke()
        }
    }

    // One handle per band, at its frequency and gain
    Repeater {
        model: graph.interactive ? graph.bands : []
        delegate: Rectangle {
            id: handle
            required property var modelData
            required property int index
            property bool selected: index === graph.selectedBand
            width: selected ? 24 : 18
            height: width
            radius: width / 2
            x: graph.xFor(modelData.freq) - width / 2
            y: graph.yFor(modelData.gain) - height / 2
            color: selected ? Theme.accent : Theme.card
            border.color: selected ? Theme.text : modelData.gain === 0 ? Theme.faint : Theme.accent
            border.width: 2
            z: selected ? 2 : 1
            Text {
                anchors.centerIn: parent
                text: handle.index + 1
                color: handle.selected ? Theme.background : Theme.text
                font.pixelSize: 10
                font.weight: Font.Bold
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        enabled: graph.interactive
        hoverEnabled: true
        property int dragging: -1
        cursorShape: dragging >= 0 ? Qt.ClosedHandCursor : nearest(mouseX, mouseY) >= 0 ? Qt.OpenHandCursor : Qt.ArrowCursor

        // The band whose handle is under the pointer, or -1
        function nearest(mx, my) {
            var best = -1, bestDistance = 18 * 18
            for (var i = 0; i < graph.bands.length; i++) {
                var dx = graph.xFor(graph.bands[i].freq) - mx
                var dy = graph.yFor(graph.bands[i].gain) - my
                if (dx * dx + dy * dy < bestDistance) { bestDistance = dx * dx + dy * dy; best = i }
            }
            return best
        }

        onPressed: function(mouse) {
            dragging = nearest(mouse.x, mouse.y)
            if (dragging >= 0) graph.bandSelected(dragging)
        }
        onPositionChanged: function(mouse) {
            if (dragging >= 0)
                graph.bandMoved(dragging, graph.freqFor(mouse.x), graph.gainFor(mouse.y))
        }
        onReleased: dragging = -1
        onDoubleClicked: function(mouse) {
            var i = nearest(mouse.x, mouse.y)
            if (i >= 0) graph.bandFlattened(i)
        }
        onWheel: function(wheel) {
            var i = nearest(wheel.x, wheel.y)
            if (i < 0) i = graph.selectedBand
            if (i < 0) return
            graph.bandSelected(i)
            graph.bandWidened(i, wheel.angleDelta.y > 0 ? 1.12 : 1 / 1.12)
        }
    }
}
