// Minsick HQ's colours and sizes in one place. Dark graphite with a mint accent
pragma Singleton
import QtQuick

QtObject {
    readonly property color background: "#0d0f12"
    readonly property color sidebar: "#121519"
    readonly property color card: "#181c22"
    readonly property color cardRaised: "#1f242b"
    readonly property color border: "#2a3038"
    readonly property color text: "#e9ecef"
    readonly property color muted: "#8b95a3"
    readonly property color faint: "#545d69"
    readonly property color accent: "#4fd1b0"
    readonly property color accentDim: "#2a6f60"
    readonly property color warning: "#f2b24c"
    readonly property color danger: "#e5645a"

    readonly property int radius: 10
    readonly property int gap: 16
    readonly property int small: 12
    readonly property int body: 14
    readonly property int title: 20
    readonly property int hero: 30
}
