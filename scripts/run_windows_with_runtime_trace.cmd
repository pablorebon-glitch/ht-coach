@echo off
setlocal

set "HT_COACH_RUNTIME_TRACE=1"
set "HT_COACH_RUNTIME_TRACE_PLAYER=Michael Rushton"

set "REPO_ROOT=%~dp0.."
set "NORMAL_EXE=%REPO_ROOT%\dist\HT Coach\HT Coach.exe"
set "PORTABLE_EXE=%REPO_ROOT%\dist\HT Coach Portable\HT Coach.exe"

if exist "%NORMAL_EXE%" (
    start "HT Coach Runtime Trace" "%NORMAL_EXE%"
    goto :done
)

if exist "%PORTABLE_EXE%" (
    start "HT Coach Runtime Trace" "%PORTABLE_EXE%"
    goto :done
)

echo HT Coach.exe was not found.
echo Build first with: .\scripts\build_windows.ps1
echo.
pause

:done
endlocal
