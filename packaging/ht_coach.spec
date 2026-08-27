# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


block_cipher = None
repo_root = Path.cwd()

datas = [
    (str(repo_root / "resources"), "resources"),
]

hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "pandas",
    "tzdata",
]


def _without_conflicting_icu_binaries(binaries):
    filtered = []
    for destination, source, kind in binaries:
        destination_name = Path(destination).name.lower()
        source_text = str(source).lower()
        if destination_name.startswith("icu") and "codex-primary-runtime" in source_text:
            continue
        filtered.append((destination, source, kind))
    return filtered


icon_candidates = [
    repo_root / "resources" / "assets" / "app_icon.ico",
    repo_root / "resources" / "assets" / "app_icon.png",
]
icon = next((str(path) for path in icon_candidates if path.exists()), None)

a = Analysis(
    [str(repo_root / "ht_coach_app" / "main.py")],
    pathex=[str(repo_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[
        str(repo_root / "packaging" / "runtime_hook_pyside6_paths.py"),
    ],
    excludes=["tests", ".venv"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
a.binaries = _without_conflicting_icu_binaries(a.binaries)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="HT Coach",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="HT Coach",
)
