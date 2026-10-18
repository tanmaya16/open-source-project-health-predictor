@echo off
setlocal
cd /d "%~dp0"
title Open-Source Project Health Predictor

echo ===============================================
echo   Open-Source Project Health Predictor
echo ===============================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python launcher 'py' was not found.
    echo Install Python 3.11 or newer from https://www.python.org/downloads/
    echo Make sure the Python launcher is selected during installation.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    py -m venv .venv
    if errorlevel 1 goto :error
)

echo Installing or checking required packages...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error

if not exist ".env" copy ".env.example" ".env" >nul

echo.
echo Starting Streamlit...
".venv\Scripts\python.exe" -m streamlit run app.py
if errorlevel 1 goto :error
goto :end

:error
echo.
echo ERROR: Setup or app launch failed. Read the message above.
pause
exit /b 1

:end
echo.
echo App stopped.
pause
endlocal
