@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Link to MP4

rem ============================================================
rem  Link to MP4 launcher (Windows)
rem  Finds a real Python 3.10+ (ignoring the Microsoft Store
rem  placeholder), installs Python automatically if it is
rem  missing, then starts the app. No administrator needed.
rem ============================================================

call :find_python
if defined PYEXE goto :run

echo.
echo Python 3.10 or newer was not found on this computer.
echo Installing Python now - one-time setup, needs internet.
echo.

where winget >nul 2>nul
if not errorlevel 1 (
    echo Installing Python with winget, the Windows package manager...
    winget install --id Python.Python.3.12 --exact --scope user --silent --accept-package-agreements --accept-source-agreements
    call :refresh_path
    call :find_python
    if defined PYEXE goto :run
)

call :download_python
call :refresh_path
call :find_python
if defined PYEXE goto :run

echo.
echo Python could not be installed automatically.
echo Please install Python 3.10 or newer from https://www.python.org/downloads/
echo Tick "Add Python to PATH" during setup, then run Start-Windows.cmd again.
echo.
pause
exit /b 1

:run
echo Starting Link to MP4...
"%PYEXE%" "App\app.py" %*
echo.
pause
exit /b 0

rem ------------------------------------------------------------
rem  :find_python sets PYEXE to a verified Python 3.10+ path.
rem  A candidate only counts if it actually runs and reports
rem  version 3.10 or newer, so Store placeholders never pass.
rem ------------------------------------------------------------
:find_python
set "PYEXE="
call :probe py -3
if defined PYEXE exit /b 0
for /f "delims=" %%P in ('where python 2^>nul') do (
    echo %%P | findstr /i /c:"WindowsApps" >nul
    if errorlevel 1 if not defined PYEXE call :probe "%%P"
)
if defined PYEXE exit /b 0
for %%D in ("%LocalAppData%\Programs\Python\Python313" "%LocalAppData%\Programs\Python\Python312" "%LocalAppData%\Programs\Python\Python311" "%LocalAppData%\Programs\Python\Python310" "C:\Program Files\Python313" "C:\Program Files\Python312" "C:\Program Files\Python311" "C:\Program Files\Python310") do (
    if not defined PYEXE if exist "%%~D\python.exe" call :probe "%%~D\python.exe"
)
exit /b 0

rem ------------------------------------------------------------
rem  :probe runs the candidate with a version check and, on
rem  success, stores its real executable path in PYEXE.
rem  Usage: call :probe py -3   or   call :probe "C:\path\python.exe"
rem ------------------------------------------------------------
:probe
set "PROBE_OUT="
for /f "tokens=2 delims=|" %%O in ('%* -c "import sys; assert sys.version_info >= (3, 10); print('LINKTOMP4_PY_OK^|' + sys.executable)" 2^>nul') do set "PROBE_OUT=%%O"
if defined PROBE_OUT set "PYEXE=%PROBE_OUT%"
exit /b 0

rem ------------------------------------------------------------
rem  :download_python fetches the official python.org installer
rem  and installs per-user (no administrator needed).
rem ------------------------------------------------------------
:download_python
set "PYSETUP=%TEMP%\linktomp4-python-3.12.10-setup.exe"
echo Downloading Python 3.12 from python.org...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile '%PYSETUP%'"
if not exist "%PYSETUP%" exit /b 0
echo Installing Python (per-user)...
"%PYSETUP%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0
exit /b 0

rem ------------------------------------------------------------
rem  :refresh_path reloads PATH from the registry so a Python
rem  installed a moment ago becomes visible in this window.
rem ------------------------------------------------------------
:refresh_path
for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "MACHINE_PATH=%%B"
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USER_PATH=%%B"
if defined MACHINE_PATH set "PATH=%MACHINE_PATH%"
if defined USER_PATH set "PATH=%PATH%;%USER_PATH%"
exit /b 0
