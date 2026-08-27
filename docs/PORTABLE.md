# Portable Mode

HT Coach portable mode is enabled only when `portable.flag` exists beside
`HT Coach.exe`.

In portable mode, user data is stored beside the executable:

```text
HT Coach Portable\
  HT Coach.exe
  portable.flag
  data\
  logs\
  backups\
```

Without `portable.flag`, a packaged executable is a normal desktop build and uses:

```text
%LOCALAPPDATA%\HT Coach\Alpha
```

Build portable packages with the existing script:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build_portable.ps1
```

Build normal desktop packages with:

```powershell
.\scripts\build_windows.ps1
```

Do not copy only the executable for portable use. The full portable folder must
travel together so resources, logs, backups and data stay in the expected places.
