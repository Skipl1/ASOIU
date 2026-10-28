@echo off
rem Skachat i podgotovit Chromium 90 i Firefox 88 (sm. README.md)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_browsers.ps1" %*
pause
