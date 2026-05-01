@echo off
:: Survey High-Frequency Data Quality Checks — Windows Launcher
:: Double-click this file to start the app.

cd /d "%~dp0"

echo ================================================
echo   Survey HFC — Data Quality Checks
echo ================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3 is not installed or not on your PATH.
    echo Please install Python 3 from https://www.python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

:: Create virtual environment on first run
if not exist "venv\" (
    echo First run — setting up virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: Activate
call venv\Scripts\activate.bat

:: Install / update dependencies
echo Checking dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    echo Check your internet connection and try again.
    pause
    exit /b 1
)

echo.
echo Starting the app...
echo It will open in your browser at http://localhost:8501
echo To stop the app, close this window or press Ctrl+C.
echo.

streamlit run app.py --server.headless false
pause
