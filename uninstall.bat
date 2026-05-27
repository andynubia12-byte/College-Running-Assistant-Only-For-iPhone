@echo off
cd /d "%~dp0"
taskkill /f /im GeoPilot.exe 2>nul
cd ..
rmdir /s /q "%~dp0"
echo GeoPilot uninstalled.
pause
