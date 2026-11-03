"""InitGui.py startup callbacks, run the way FreeCAD runs the file.

FreeCADGuiInit's RunInitGuiPy calls exec(compile(...)) inside a function with no
explicit namespaces, so top-level names of InitGui.py land in that call's locals
and are invisible from function bodies defined in the file.
"""

import sys
import types
from pathlib import Path
from unittest import mock

INIT_GUI = Path(__file__).parent.parent / "addon" / "FreeCADMCP" / "InitGui.py"


def _run_startup(auto_start):
    rpc_server = mock.Mock()
    rpc_server.load_settings.return_value = {"auto_start_rpc": auto_start}
    rpc_server.start_rpc_server.return_value = "started"
    mcp_status = mock.Mock()
    scheduled = []
    qtcore = mock.Mock()
    qtcore.QTimer.singleShot.side_effect = lambda _ms, callback: scheduled.append(callback)

    pyside = types.ModuleType("PySide")
    pyside.QtCore = qtcore
    package = types.ModuleType("rpc_server")
    package.rpc_server = rpc_server
    package.mcp_status = mcp_status
    modules = {
        "PySide": pyside,
        "PySide.QtCore": qtcore,
        "rpc_server": package,
        "rpc_server.rpc_server": rpc_server,
        "rpc_server.mcp_status": mcp_status,
    }

    # Mirrors RunInitGuiPy: the names FreeCADGuiInit provides are its globals.
    run_globals = {"FreeCAD": mock.Mock(), "Gui": mock.Mock(), "Workbench": object}
    runner = eval(
        "lambda source: exec(compile(source, 'InitGui.py', 'exec'))", run_globals
    )

    path_before = list(sys.path)
    try:
        with mock.patch.dict(sys.modules, modules):
            runner(INIT_GUI.read_text(encoding="utf-8"))
            for callback in scheduled:
                callback()
    finally:
        sys.path[:] = path_before
    return rpc_server, mcp_status


def test_auto_start_on_starts_server_and_installs_status():
    rpc_server, mcp_status = _run_startup(auto_start=True)

    rpc_server.start_rpc_server.assert_called_once_with()
    mcp_status.install_status_indicator.assert_called_once_with()


def test_auto_start_off_installs_status_only():
    rpc_server, mcp_status = _run_startup(auto_start=False)

    rpc_server.start_rpc_server.assert_not_called()
    mcp_status.install_status_indicator.assert_called_once_with()
