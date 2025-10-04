@echo off
setlocal

echo ========================================
echo   AI Agent - Dependency Installation
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

echo [OK] Python found
echo.

REM Check if pip is available
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip is not available
    echo Please ensure pip is installed with Python
    pause
    exit /b 1
)

echo [OK] pip found
echo.

set SCRIPT_DIR=%~dp0

echo Installing dependencies...
echo.

echo [1/3] Installing agent-main dependencies...
pip install -r "%SCRIPT_DIR%agent-main\requirements.txt"
if errorlevel 1 (
    echo [ERROR] Failed to install agent-main dependencies
    pause
    exit /b 1
)
echo [OK] agent-main dependencies installed
echo.

echo [2/3] Installing transcribe dependencies...
pip install -r "%SCRIPT_DIR%transcribe\requirements.txt"
if errorlevel 1 (
    echo [ERROR] Failed to install transcribe dependencies
    pause
    exit /b 1
)
echo [OK] transcribe dependencies installed
echo.

echo [3/3] Installing widget dependencies...
pip install -r "%SCRIPT_DIR%widget\requirements.txt"
if errorlevel 1 (
    echo [ERROR] Failed to install widget dependencies
    pause
    exit /b 1
)
echo [OK] widget dependencies installed
echo.

echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo Next steps:
echo   1. Set your OPENAI_API_KEY environment variable
echo   2. Double-click START.bat to launch
echo.
echo For help, see:
echo   - QUICKSTART.md
echo   - LAUNCH_GUIDE.md
echo.
pause
endlocal
