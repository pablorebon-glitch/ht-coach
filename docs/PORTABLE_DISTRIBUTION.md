# Portable Windows Distribution

Alpha 0.6.9 adds a portable Windows target for copying HT Coach to a USB drive,
another Windows PC or a local folder without installing Python.

## Detection

Portable mode is enabled by a `portable.flag` file beside `HT Coach.exe`.

When the flag exists:

- writable data goes under `<portable root>/data`;
- logs go under `<portable root>/logs`;
- backups go under `<portable root>/backups`;
- resources are read from the bundled `resources` directory;
- AppData is not used for user data.

When the flag does not exist, development/installed behavior keeps using the normal
local user data directory.

## Paths

`ht_coach_app.core.paths.ApplicationPaths.detect()` is the application-level path
boundary. Repositories should use `user_data_dir()` or the specific helpers instead of
hardcoding AppData, `logs/` or current-working-directory paths.

For PyInstaller, the executable directory is resolved from `sys.executable`. Bundled
resources are resolved from `_MEIPASS` when needed.

## CSV Portability

In portable mode, roster CSV imports are copied into `data/rosters/` and settings store
a path relative to the portable root. Saved matches and recent CSVs can therefore be
opened after the folder moves to a different drive letter.

## Data Import

On first portable launch, if portable data is empty and existing AppData data exists,
the app offers to copy it. Manual import is available from Settings. Import creates a
backup of current portable data before replacement.

## Safe Writes

Application JSON writes use a temporary file, flush to disk and atomically replace the
final file. Existing domain repositories that own JSON persistence use the same pattern
without importing desktop UI code.

## Build

Use:

```powershell
powershell -ExecutionPolicy Bypass -File packaging/build_portable.ps1
```

Output:

- `dist/HT Coach Portable/`
- `dist/HT_Coach_Alpha_0.6.9_Portable.zip`

## Security

The portable build does not require administrator privileges. The executable is
unsigned, so Windows SmartScreen or corporate application-control policies may block it.
HT Coach does not implement security bypasses.
