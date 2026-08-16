$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Spec = Join-Path $PSScriptRoot "ht_coach_portable.spec"
$DistRoot = Join-Path $RepoRoot "dist"
$BuildRoot = Join-Path $RepoRoot "build"
$PyInstallerOutput = Join-Path $DistRoot "HT Coach"
$PortableRoot = Join-Path $DistRoot "HT Coach Portable"
$ZipPath = Join-Path $DistRoot "HT_Coach_Alpha_0.6.9_Portable.zip"

if (-not (Test-Path $Python)) {
    throw "Virtual environment not found. Create .venv and install requirements first."
}

& $Python -c "import PyInstaller" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller is not installed in .venv. Install it before building."
}

Push-Location $RepoRoot
try {
    & $Python -m compileall ht_coach_app models engine tests
    if ($LASTEXITCODE -ne 0) {
        throw "compileall failed."
    }

    if (Test-Path $PyInstallerOutput) {
        Remove-Item -LiteralPath $PyInstallerOutput -Recurse -Force
    }
    if (Test-Path $PortableRoot) {
        Remove-Item -LiteralPath $PortableRoot -Recurse -Force
    }
    if (Test-Path $ZipPath) {
        Remove-Item -LiteralPath $ZipPath -Force
    }

    & $Python -m PyInstaller --noconfirm --clean $Spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed."
    }

    Move-Item -LiteralPath $PyInstallerOutput -Destination $PortableRoot

    New-Item -ItemType File -Path (Join-Path $PortableRoot "portable.flag") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $PortableRoot "data") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $PortableRoot "data\migrations") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $PortableRoot "data\rosters") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $PortableRoot "backups") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $PortableRoot "logs\crashes") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $PortableRoot "logs\recovery") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $PortableRoot "licenses") -Force | Out-Null

    "HT Coach Alpha 0.6.9 Portable" | Set-Content -Path (Join-Path $PortableRoot "version.txt") -Encoding UTF8
    Copy-Item -LiteralPath (Join-Path $RepoRoot "README_PORTABLE.txt") -Destination (Join-Path $PortableRoot "README_PORTABLE.txt") -Force

    $DebugCmd = @"
@echo off
set QT_QPA_PLATFORM=
echo Starting HT Coach with console diagnostics...
"%~dp0HT Coach.exe"
echo.
echo HT Coach closed. Press any key to exit.
pause > nul
"@
    $DebugCmd | Set-Content -Path (Join-Path $PortableRoot "HT Coach Debug.cmd") -Encoding ASCII

    Compress-Archive -Path $PortableRoot -DestinationPath $ZipPath -Force

    Write-Host "Portable build created:"
    Write-Host $PortableRoot
    Write-Host $ZipPath
}
finally {
    Pop-Location
}
