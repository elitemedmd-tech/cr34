@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
  echo Python 3.11 or 3.12 must be installed from python.org with Add Python to PATH enabled.
  pause
  exit /b 1
)
py -3 -m venv .venv
if errorlevel 1 goto error
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto error
python -m pip install -r requirements.txt
if errorlevel 1 goto error
python -m PyInstaller --noconfirm --clean --onefile --windowed --name CR3_to_JPEG --collect-all rawpy cr3_to_jpeg.py
if errorlevel 1 goto error
echo.
echo READY: %CD%\dist\CR3_to_JPEG.exe
echo.
pause
exit /b 0
:error
echo Build failed. Check error message above.
pause
exit /b 1
