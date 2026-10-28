@echo off
rem Chromium 90 (dvizhok Chrome 90 / Edge 90 / Yandex 21). Otdelnyj profil, avtoobnovlenij net.
start "" "%~dp0chromium90\chrome-win\chrome.exe" --user-data-dir="%~dp0profiles\chromium90" --no-first-run --no-default-browser-check http://localhost:8080
