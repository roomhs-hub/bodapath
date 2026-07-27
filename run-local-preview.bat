@echo off
setlocal
cd /d "%~dp0"

set APP_PASSWORD=local1234
set SECRET_KEY=local-preview-secret-key
set FLASK_DEBUG=1
set PORT=5050

REM SQLite does not work reliably on network/virtual drives (locking issues),
REM so the local preview DB file is stored on the real local disk instead,
REM even though the source code stays on the network drive.
set LOCALDB_DIR=%LOCALAPPDATA%\handover-local-preview
if not exist "%LOCALDB_DIR%" mkdir "%LOCALDB_DIR%"
set "LOCALDB_DIR_FWD=%LOCALDB_DIR:\=/%"
set DATABASE_URL=sqlite:///%LOCALDB_DIR_FWD%/dev_local.db

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python is not installed, or not added to PATH.
    echo Install Python from https://www.python.org/downloads/
    echo During install, check the box "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo Creating virtual environment ...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment. See message above.
        pause
        exit /b 1
    )
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)

set REQ_FILE=requirements.txt
if exist "requirements-local.txt" set REQ_FILE=requirements-local.txt

echo Installing required packages from %REQ_FILE% ...
pip install -q -r %REQ_FILE%
if errorlevel 1 (
    echo [ERROR] Package install failed. See message above.
    pause
    exit /b 1
)

echo.
echo ===============================================
echo  Starting local preview server
echo  URL:      http://127.0.0.1:5050
echo  Password: local1234
echo  DB file:  %LOCALDB_DIR%\dev_local.db
echo  Press Ctrl+C in this window to stop the server.
echo ===============================================
echo.

start "" http://127.0.0.1:5050

python wsgi.py

echo.
echo [INFO] Server stopped. Check messages above for errors.
pause
endlocal
