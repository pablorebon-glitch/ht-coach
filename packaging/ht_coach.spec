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
