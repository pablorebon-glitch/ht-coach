# HT Coach Packaging

Build target: Windows 10/11 x64, PyInstaller one-folder.

## Prerequisites

- Existing `.venv`
- Runtime requirements installed
- `pyinstaller` installed in `.venv`

## Normal Desktop Build

```powershell
.\scripts\build_windows.ps1
```

Output:

- `dist/HT Coach/HT Coach.exe`

This build does not create `portable.flag`, so it uses the canonical Windows
user-data folder rather than a portable data folder.

## Runtime Integrity Trace

Normal launches keep tracing disabled. To reproduce a runtime state issue with
the packaged app, run:

```powershell
.\scripts\run_windows_with_runtime_trace.cmd
```

The app prints the active JSONL trace location once at startup:

```text
Runtime integrity trace enabled: <absolute path>
```

For the normal desktop build, the trace is written under the canonical Windows
app logs folder.

## Portable Build

```powershell
powershell -ExecutionPolicy Bypass -File packaging/build_portable.ps1
```

The script:

1. validates `.venv`;
2. runs `compileall`;
3. cleans previous portable output;
4. runs PyInstaller with `packaging/ht_coach_portable.spec`;
5. creates `portable.flag`;
6. creates empty writable folders;
7. writes `version.txt`;
8. copies `README_PORTABLE.txt`;
9. creates `HT Coach Debug.cmd`;
10. creates a portable zip.

## Output

- `dist/HT Coach Portable/HT Coach.exe`
- `dist/HT Coach Portable/portable.flag`
- `dist/HT Coach Portable/data/`
- `dist/HT Coach Portable/logs/`
- `dist/HT Coach Portable/backups/`
- `dist/HT_Coach_Alpha_0.6.9_Portable.zip`

Do not include `.git`, `.venv`, tests or production user data in the portable folder.
