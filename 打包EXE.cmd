@echo off
cd /d "%~dp0"
python -m PyInstaller --noconfirm --clean --onefile --windowed --name Netease-W10M-Login-Generator --add-data "blank.dat;." gui.py
pause
