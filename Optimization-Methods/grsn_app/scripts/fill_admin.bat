@echo off
rem Zapusk dvojnym shchelchkom: zapolnyaet uchetnuyu zapis administratora istoriej za mesyac.
rem Sistema dolzhna byt uzhe zapushchena (scripts\setup.ps1). Dopolnitelno: fill_admin.bat -Demo
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0fill_admin.ps1" %*
echo.
pause
