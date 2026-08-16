# HT Coach Portable Packaging

Build target: Windows 10/11 x64, PyInstaller one-folder.

## Prerequisites

- Existing `.venv`
- Runtime requirements installed
- `pyinstaller` installed in `.venv`

## Build

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
