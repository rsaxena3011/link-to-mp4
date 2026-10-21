@echo off
setlocal
cd /d "%~dp0"
title Link to MP4
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "App\app.py" %*
    goto done
)
where python >nul 2>nul
if not errorlevel 1 (
    python "App\app.py" %*
    goto done
)
echo Python 3.10 or newer is needed for this app.
echo Install Python from https://www.python.org/downloads/windows/
echo Select "Add Python to PATH" if the installer offers it.
echo Then close this window and run Start-Windows.cmd again.
:done
echo.
pause
