$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Spec = Join-Path $RepoRoot "packaging\ht_coach.spec"
$DistRoot = Join-Path $RepoRoot "dist"
$BuildRoot = Join-Path $RepoRoot "build\ht_coach_windows"
$OutputRoot = Join-Path $DistRoot "HT Coach"
$ExePath = Join-Path $OutputRoot "HT Coach.exe"

if (-not (Test-Path $Python)) {
    throw "Virtual environment not found. Create .venv and install requirements first."
}

& $Python -c "import PyInstaller" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller is not installed in .venv. Install packaging requirements first: .\.venv\Scripts\python.exe -m pip install -r packaging\requirements-build.txt"
}

Push-Location $RepoRoot
try {
    & $Python -m compileall ht_coach_app models engine tests
    if ($LASTEXITCODE -ne 0) {
        throw "compileall failed."
    }

    if (Test-Path $OutputRoot) {
        Remove-Item -LiteralPath $OutputRoot -Recurse -Force
    }
    if (Test-Path $BuildRoot) {
        Remove-Item -LiteralPath $BuildRoot -Recurse -Force
    }

    & $Python -m PyInstaller --noconfirm --clean --distpath $DistRoot --workpath $BuildRoot $Spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed."
    }

    if (-not (Test-Path $ExePath)) {
        throw "Build completed but HT Coach.exe was not found at $ExePath"
    }

    Write-Host "Windows desktop build created:"
    Write-Host $ExePath
    Write-Host ""
    Write-Host "This is a normal desktop build. It does not create portable.flag and will use the canonical Windows user-data folder."
}
finally {
    Pop-Location
}
