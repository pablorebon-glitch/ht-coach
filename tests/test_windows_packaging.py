import importlib.util
import os
import sys
from pathlib import Path


def _load_runtime_hook():
    hook_path = Path("packaging/runtime_hook_pyside6_paths.py").resolve()
    spec = importlib.util.spec_from_file_location(
        "ht_coach_runtime_hook_pyside6_paths_test",
        hook_path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pyside6_runtime_hook_registers_packaged_dll_and_plugin_paths(tmp_path, monkeypatch):
    root = tmp_path / "_internal"
    pyside_dir = root / "PySide6"
    shiboken_dir = root / "shiboken6"
    platform_dir = pyside_dir / "plugins" / "platforms"
    platform_dir.mkdir(parents=True)
    shiboken_dir.mkdir()
    added = []

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(root), raising=False)
    monkeypatch.setenv("PATH", "C:/Windows/System32")
    monkeypatch.setenv("QT_PLUGIN_PATH", "C:/Qt/plugins")
    monkeypatch.setenv("QT_QPA_PLATFORM_PLUGIN_PATH", "C:/Qt/plugins/platforms")
    monkeypatch.setattr(
        os,
        "add_dll_directory",
        lambda value: added.append(value),
        raising=False,
    )

    hook = _load_runtime_hook()
    hook.configure_pyside6_runtime_paths()

    assert str(pyside_dir) in added
    assert str(shiboken_dir) in added
    assert str(root) in added
    assert os.environ["PATH"].startswith(
        str(pyside_dir) + os.pathsep + str(shiboken_dir) + os.pathsep + str(root)
    )
    assert os.environ["QT_PLUGIN_PATH"] == str(pyside_dir / "plugins")
    assert os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] == str(platform_dir)


def test_windows_specs_filter_conflicting_primary_runtime_icu_binaries():
    for spec_name in ("ht_coach.spec", "ht_coach_portable.spec"):
        spec_text = Path("packaging", spec_name).read_text(encoding="utf-8")

        assert "_without_conflicting_icu_binaries" in spec_text
        assert "destination_name.startswith(\"icu\")" in spec_text
        assert "codex-primary-runtime" in spec_text
