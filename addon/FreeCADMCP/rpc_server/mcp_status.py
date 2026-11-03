"""Permanent, workbench-independent status for the FreeCAD-side RPC server."""

import FreeCADGui
from PySide import QtCore, QtWidgets

from rpc_server import rpc_server


class ServerStatusLabel(QtWidgets.QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("FreeCADMCPStatusLabel")
        self._state = None
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self.update_status)
        self._timer.start(500)
        self.update_status()

    def update_status(self):
        # stop_rpc_server clears the instance before the socket has closed.
        stop_thread = rpc_server._stop_thread
        if stop_thread is not None and stop_thread.is_alive():
            state = "Stopping..."
            color = "#d08000"
        elif rpc_server.rpc_server_instance is not None:
            state = "Running"
            color = "#00a000"
        else:
            state = "Stopped"
            color = "#c00000"

        if state == self._state:
            return
        self._state = state
        self.setText(f"\u25cf MCP Server: {state}")
        self.setStyleSheet(
            f"QLabel {{ color: {color}; font-weight: bold; padding: 0 8px; }}"
        )
        self.setToolTip(
            f"FreeCAD MCP RPC server: {state}.\n"
            "Shows the local server lifecycle, not MCP client connectivity."
        )


def install_status_indicator():
    """Install once on the GUI thread; the status bar owns the label and timer."""
    status_bar = FreeCADGui.getMainWindow().statusBar()
    label = status_bar.findChild(QtWidgets.QLabel, "FreeCADMCPStatusLabel")
    if label is None:
        label = ServerStatusLabel(status_bar)
        status_bar.addPermanentWidget(label)
    return label
