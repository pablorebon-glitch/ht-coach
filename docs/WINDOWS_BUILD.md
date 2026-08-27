# Windows Desktop Build

HT Coach supports two Windows launch modes:

- Development mode: run from the repository with Python.
- Normal desktop mode: run `dist\HT Coach\HT Coach.exe`.
- Portable mode: run a packaged folder that contains `portable.flag`.

Normal desktop mode and development mode use the same canonical Windows user-data
folder:

```text
%LOCALAPPDATA%\HT Coach\Alpha
```

Portable mode stores data beside the executable only when `portable.flag` exists in
the executable directory.

## Build

From the repository root:

```powershell
.\scripts\build_windows.ps1
```

The script uses `.venv\Scripts\python.exe`, verifies PyInstaller, compiles the
application, removes only packaging build output, and creates:

```text
dist\HT Coach\HT Coach.exe
```

Install build-only requirements when PyInstaller is missing:

```powershell
.\.venv\Scripts\python.exe -m pip install -r packaging\requirements-build.txt
```

## Desktop Shortcut

After building, create a Desktop shortcut with:

```powershell
.\scripts\create_desktop_shortcut.ps1
```

The shortcut target is:

```text
dist\HT Coach\HT Coach.exe
```

It does not target Python, PowerShell, or the development module command.

## Resources

The PyInstaller spec includes the full `resources` folder, including i18n JSON
catalogs. Runtime path resolution remains centralized in
`ht_coach_app.core.paths`; the application does not rely on the current working
directory being the repository root.

The build also installs `packaging/runtime_hook_pyside6_paths.py`. This hook runs
before the application imports PySide6 and registers the bundled `PySide6` and
`shiboken6` directories with the Windows DLL loader. That keeps QtGui startup
stable when `HT Coach.exe` is launched from Windows Explorer or a Desktop shortcut
without inheriting the development shell PATH.

## Diagnostics

The normal desktop executable is windowed and does not leave a console open.
Runtime logs and crash recovery continue to use the existing application log
location under the canonical user-data folder. Portable builds keep logs beside the
portable executable.
