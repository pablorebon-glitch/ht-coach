$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ExePath = Join-Path $RepoRoot "dist\HT Coach\HT Coach.exe"

if (-not (Test-Path $ExePath)) {
    throw "HT Coach.exe was not found. Build first with: .\scripts\build_windows.ps1"
}

$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "HT Coach.lnk"
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $ExePath
$Shortcut.WorkingDirectory = Split-Path $ExePath -Parent
$Shortcut.WindowStyle = 1
$Shortcut.Description = "HT Coach"
$Shortcut.Save()

Write-Host "Desktop shortcut created:"
Write-Host $ShortcutPath
