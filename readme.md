## HT Coach Windows Launcher

Development mode:

```powershell
.\.venv\Scripts\python.exe -m ht_coach_app.main
```

Normal Windows desktop build:

```powershell
.\scripts\build_windows.ps1
```

The generated executable is:

```text
dist\HT Coach\HT Coach.exe
```

Optional Desktop shortcut:

```powershell
.\scripts\create_desktop_shortcut.ps1
```

See `docs/WINDOWS_BUILD.md` and `docs/PORTABLE.md` for normal desktop versus
portable data behavior.
