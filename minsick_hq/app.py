"""Starts Minsick HQ: the Qt application, the QML window and the objects behind it.

    python -m minsick_hq                 the app (or brings back the window of the one already running)
    python -m minsick_hq --background    start without a window, the equaliser and microphone as
                                         I left them; quits straight away if neither is on
    python -m minsick_hq --demo          sample devices instead of PipeWire, nothing touches real
                                         audio (for screenshots and trying it out)
    python -m minsick_hq --screenshot F  save the window to F after it loads, then quit
    python -m minsick_hq --page N        open on page N (0 headset, 1 equaliser, 2 microphone, 3 settings)
"""
import argparse
import os
import signal
import sys

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow  # noqa: F401  so the root object comes back as a QQuickWindow
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from . import __version__
from .bridge import HQ, DialogQueue
from .demo import DEMO_DUMP

HERE = os.path.dirname(os.path.abspath(__file__))
ICON = os.path.join(HERE, "qml", "images", "icon.svg")
# The local socket the running copy listens on; tests set their own so they never reach a real one
INSTANCE_NAME = os.environ.get("MINSICK_HQ_INSTANCE", f"minsick-hq-{os.getuid()}")


class Instance(QObject):
    """Keeps Minsick HQ to one copy. The first one listens; starting it again tells the first to
    show its window, and the second one quits."""
    showRequested = Signal()

    def __init__(self):
        super().__init__()
        self.server = None

    def already_running(self):
        socket = QLocalSocket()
        socket.connectToServer(INSTANCE_NAME)
        if socket.waitForConnected(300):
            socket.write(b"show\n")
            socket.flush()
            socket.waitForBytesWritten(300)
            socket.disconnectFromServer()
            return True
        return False

    def listen(self):
        # A copy that crashed can leave its socket behind
        QLocalServer.removeServer(INSTANCE_NAME)
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._connection)
        self.server.listen(INSTANCE_NAME)

    def _connection(self):
        socket = self.server.nextPendingConnection()
        socket.readyRead.connect(lambda: (socket.readAll(), self.showRequested.emit()))
        socket.disconnected.connect(socket.deleteLater)


def _desktop_entry_installed(name):
    """True when a launcher entry with this file name is in one of the XDG applications folders."""
    home = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    folders = [home] + os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":")
    return any(os.path.exists(os.path.join(folder, "applications", name)) for folder in folders if folder)


def _tray(app, hq, instance):
    """A tray icon with the main switches, where the desktop has a tray to show it in."""
    if not QSystemTrayIcon.isSystemTrayAvailable():
        return None
    tray = QSystemTrayIcon(QIcon(ICON), app)
    tray.setToolTip("Minsick HQ")
    menu = QMenu()
    show = QAction("Open Minsick HQ", menu)
    show.triggered.connect(instance.showRequested.emit)
    eq = QAction("Equaliser", menu, checkable=True)
    eq.toggled.connect(lambda on: hq.setEqEnabled(on))
    mic = QAction("Microphone cleanup", menu, checkable=True)
    mic.toggled.connect(lambda on: hq.setMicEnabled(on))
    quit_action = QAction("Quit", menu)
    quit_action.triggered.connect(app.quit)
    for action in (show, None, eq, mic, None, quit_action):
        menu.addSeparator() if action is None else menu.addAction(action)

    def sync():
        eq.blockSignals(True)
        eq.setChecked(hq.eqEnabled)
        eq.blockSignals(False)
        mic.blockSignals(True)
        mic.setChecked(hq.micEnabled)
        mic.blockSignals(False)
        tray.setToolTip("Minsick HQ\n" + hq.status)
    hq.eqChanged.connect(sync)
    hq.micChanged.connect(sync)
    hq.statusChanged.connect(sync)
    sync()
    tray.setContextMenu(menu)
    tray.activated.connect(lambda reason: instance.showRequested.emit()
                           if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
    tray.show()
    # Keep the menu alive as long as the tray
    tray._menu = menu
    return tray


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="minsick-hq",
        description="Headset status, a PipeWire equaliser and microphone cleanup. MIT licensed.",
        epilog="Not affiliated with or endorsed by Audeze LLC. Audeze and Maxwell are trademarks of Audeze LLC.")
    parser.add_argument("--background", action="store_true", help="start without a window")
    parser.add_argument("--demo", action="store_true", help="sample devices, no real audio")
    parser.add_argument("--screenshot", help="save the window to this file, then quit")
    parser.add_argument("--page", type=int, default=0, help="open on this page")
    args, qt_args = parser.parse_known_args(argv)

    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    # Qt on Wayland warns every time a text field loses focus ("Trying to disable ... but 0x0 is
    # focused"). It's harmless; hide just that one, unless you've set your own logging rules
    os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.wayland.textinput=false")
    app = QApplication([sys.argv[0], *qt_args])
    app.setApplicationName("Minsick HQ")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("Minsick")
    # The window can close while the equaliser keeps running; quitting is decided explicitly
    app.setQuitOnLastWindowClosed(False)
    # Only claim the launcher entry once it's installed; otherwise the desktop portal complains
    if _desktop_entry_installed("minsick-hq.desktop"):
        app.setDesktopFileName("minsick-hq")
    app.setWindowIcon(QIcon(ICON))

    # Demo and screenshot runs are throwaway copies; everything else is the one and only
    single = not args.demo and not args.screenshot
    instance = Instance()
    if single:
        if instance.already_running():
            return 0
        instance.listen()

    # Ctrl+C or a stop from systemd quits cleanly, so the equaliser and mic are switched off
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    signal.signal(signal.SIGTERM, lambda *_: app.quit())
    pulse = QTimer(interval=250, timeout=lambda: None)
    pulse.start()

    dialogs = DialogQueue()
    # Only the one running copy cleans up after a crash; a demo or screenshot copy never does
    hq = HQ(dialogs, demo_dump=DEMO_DUMP if args.demo else None, recover=single)
    app.aboutToQuit.connect(hq.shutdown)

    engine = QQmlApplicationEngine()
    # QML errors always reach the terminal, even where Qt's own logging is turned off
    engine.warnings.connect(lambda warnings: [print(w.toString(), file=sys.stderr) for w in warnings])
    engine.addImportPath(os.path.join(HERE, "qml"))
    context = engine.rootContext()
    context.setContextProperty("hq", hq)
    context.setContextProperty("dialogs", dialogs)
    context.setContextProperty("instance", instance)
    context.setContextProperty("startPage", args.page)
    context.setContextProperty("startHidden", args.background)
    context.setContextProperty("demoMode", args.demo)
    context.setContextProperty("appVersion", __version__)
    engine.load(QUrl.fromLocalFile(os.path.join(HERE, "qml", "Main.qml")))
    if not engine.rootObjects():
        return 1
    tray = _tray(app, hq, instance) if single else None  # noqa: F841  kept alive with the app

    if args.background:
        # Started at login with nothing switched on: nothing to do in the background
        QTimer.singleShot(2500, lambda: None if hq.busy() else app.quit())

    if args.screenshot:
        window = engine.rootObjects()[0]

        def grab():
            try:
                window.grabWindow().save(args.screenshot)
            finally:
                app.quit()
        QTimer.singleShot(1500, grab)
    result = app.exec()
    # The interface goes first, while the objects it reads still exist
    del tray
    del engine
    return result
