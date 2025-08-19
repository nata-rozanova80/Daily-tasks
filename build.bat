@echo off
setlocal
cd /d %~dp0

if not exist .venv (
  py -m venv .venv
)
call .venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

pyinstaller --noconfirm --windowed --name "ChecklistNotes" main.py

echo.
echo Build complete. Executable is in .\dist\ChecklistNotes\ChecklistNotes.exe
echo To create a desktop shortcut, double-click create_shortcut.vbs
pause
