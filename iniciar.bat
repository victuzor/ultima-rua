@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 goto erro
)
".venv\Scripts\python.exe" -c "import pygame" >nul 2>&1
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto erro
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 goto erro
exit /b 0
:erro
echo Nao foi possivel iniciar. Confira a mensagem acima e a instalacao do Python.
pause
exit /b 1
