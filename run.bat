@echo off
setlocal enabledelayedexpansion
title RazorUAP - Automated Setup and Launch
color 0A

echo ============================================================
echo   RazorUAP - Agent-to-Agent Commerce Gateway
echo   Automated Setup / Test / Launch Script
echo ============================================================
echo.

REM ----------------------------------------------------------
REM 0. Move to the script's own directory (so this works no
REM    matter where it's double-clicked from)
REM ----------------------------------------------------------
cd /d "%~dp0"
echo [0/5] Working directory: %cd%
echo.

REM ----------------------------------------------------------
REM 1. Detect a working Python launcher (py preferred on Windows)
REM ----------------------------------------------------------
echo [1/5] Detecting Python...
set PY_CMD=

py --version >nul 2>&1
if %errorlevel%==0 (
    set PY_CMD=py
    goto :python_found
)

python --version >nul 2>&1
if %errorlevel%==0 (
    set PY_CMD=python
    goto :python_found
)

echo.
echo ERROR: No working Python installation was found.
echo.
echo If Windows says "Python was not found; run without arguments
echo to install from the Microsoft Store", that means the Store
echo alias is intercepting the command. Fix it here:
echo   Settings -^> Apps -^> Advanced app settings -^>
echo   App execution aliases -^> turn OFF "App Installer python.exe"
echo   and "App Installer python3.exe"
echo.
echo Then install real Python from https://python.org and re-run this script.
pause
exit /b 1

:python_found
echo Found Python using command: %PY_CMD%
%PY_CMD% --version
echo.

REM ----------------------------------------------------------
REM 2. Verify requirements.txt exists
REM ----------------------------------------------------------
if not exist "requirements.txt" (
    echo ERROR: requirements.txt not found in %cd%
    echo Make sure this script sits in the razorpay-uap-agent folder.
    pause
    exit /b 1
)

REM ----------------------------------------------------------
REM 3. Create/reuse a virtual environment (keeps this project's
REM    deps isolated from your global Python)
REM ----------------------------------------------------------
echo [2/5] Setting up virtual environment...
if not exist "venv\" (
    %PY_CMD% -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo Created new venv.
) else (
    echo Reusing existing venv.
)

call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)
echo.

REM ----------------------------------------------------------
REM 4. Install dependencies
REM ----------------------------------------------------------
echo [3/5] Installing dependencies from requirements.txt...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Dependency installation failed. See output above.
    pause
    exit /b 1
)
echo Dependencies installed successfully.
echo.

REM ----------------------------------------------------------
REM 5. Run the automated test suite
REM ----------------------------------------------------------
echo [4/5] Running 9-point automated test suite...
echo ------------------------------------------------------------
python test_e2e.py
set TEST_RESULT=%errorlevel%
echo ------------------------------------------------------------

if not %TEST_RESULT%==0 (
    echo.
    echo WARNING: One or more tests FAILED (exit code %TEST_RESULT%).
    echo Review the output above before demoing or submitting.
    echo.
    choice /C YN /M "Continue and launch the server anyway"
    if errorlevel 2 (
        echo Aborting. Fix failing tests and re-run this script.
        pause
        exit /b 1
    )
) else (
    echo All tests passed.
)
echo.

REM ----------------------------------------------------------
REM 6. Launch the FastAPI server and open the dashboard
REM ----------------------------------------------------------
echo [5/5] Launching RazorUAP Gateway on http://127.0.0.1:8000 ...
echo (Press CTRL+C in this window to stop the server)
echo.

start "" "http://127.0.0.1:8000"
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

echo.
echo Server stopped.
pause
