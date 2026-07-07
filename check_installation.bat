@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Primero ejecuta run_ht_coach.bat para crear el entorno.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -c "import sys, tkinter, pandas, app; print('Python:', sys.version); print('Tkinter: OK'); print('Pandas:', pandas.__version__); print('HT COACH imports: OK')"
pause
