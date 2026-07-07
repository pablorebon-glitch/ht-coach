@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "LOG=%~dp0ht_coach_error.log"
del /q "%LOG%" >nul 2>&1

echo ==============================================
echo HT COACH - INICIO
echo ==============================================
echo.

set "PY_CMD="
where py >nul 2>&1 && set "PY_CMD=py"
if not defined PY_CMD (
    where python >nul 2>&1 && set "PY_CMD=python"
)
if not defined PY_CMD (
    echo ERROR: No se encontro Python instalado.
    echo Instala Python desde python.org y marca "Add Python to PATH".
    echo ERROR: Python no encontrado. > "%LOG%"
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual...
    %PY_CMD% -m venv .venv >> "%LOG%" 2>&1
    if errorlevel 1 goto :error
)

echo Instalando/verificando dependencias...
".venv\Scripts\python.exe" -m pip install --upgrade pip >> "%LOG%" 2>&1
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m pip install -r requirements.txt >> "%LOG%" 2>&1
if errorlevel 1 goto :error

echo Verificando aplicacion...
".venv\Scripts\python.exe" -c "import tkinter; import pandas; import app; print('OK')" >> "%LOG%" 2>&1
if errorlevel 1 goto :error

echo Iniciando HT COACH...
".venv\Scripts\python.exe" app.py >> "%LOG%" 2>&1
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo ==============================================
echo HT COACH NO PUDO INICIARSE
 echo ==============================================
echo.
echo El detalle del error fue guardado en:
echo %LOG%
echo.
echo Copiame el contenido de ht_coach_error.log si necesitas ayuda.
echo.
pause
exit /b 1
