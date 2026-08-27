from __future__ import annotations

import os
import sys
from pathlib import Path


def _bundle_root():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(sys.executable).resolve().parent


def _prepend_path(paths):
    existing = os.environ.get("PATH", "")
    values = [str(path) for path in paths if path.exists()]
    if not values:
        return
    os.environ["PATH"] = os.pathsep.join(values + [existing])


def _add_dll_directories(paths):
    add_dll_directory = getattr(os, "add_dll_directory", None)
    if add_dll_directory is None:
        return
    for path in paths:
        if path.exists():
            add_dll_directory(str(path))


def configure_pyside6_runtime_paths():
    root = _bundle_root()
    pyside_dir = root / "PySide6"
    shiboken_dir = root / "shiboken6"
    plugin_dir = pyside_dir / "plugins"
    platform_dir = plugin_dir / "platforms"
    dll_dirs = [pyside_dir, shiboken_dir, root]

    _add_dll_directories(dll_dirs)
    _prepend_path(dll_dirs)

    if plugin_dir.exists():
        os.environ["QT_PLUGIN_PATH"] = str(plugin_dir)
    if platform_dir.exists():
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(platform_dir)


configure_pyside6_runtime_paths()
