@echo off
rem Firefox 88. Otdelnyj profil, avtoobnovlenie otklyucheno (firefox88\core\distribution\policies.json).
start "" "%~dp0firefox88\core\firefox.exe" -no-remote -profile "%~dp0profiles\firefox88" http://localhost:8080
