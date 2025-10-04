@echo off
setlocal ENABLEDELAYEDEXPANSION

REM Usage: run_services.bat [OPENAI_API_KEY] [PORT]
REM Defaults: uses existing OPENAI_API_KEY and 6001

set KEY=%~1
if "%KEY%"=="" set KEY=%OPENAI_API_KEY%
if "%KEY%"=="" (
  echo Enter OpenAI API Key:
  set /p KEY="> "
)
set OPENAI_API_KEY=%KEY%

set PORT=%~2
if "%PORT%"=="" set PORT=6001

set SCRIPT_DIR=%~dp0
set TRANSCRIBE_DIR=%SCRIPT_DIR%transcribe
set WIDGET_DIR=%SCRIPT_DIR%widget

start powershell -NoExit -Command "Set-Location '%TRANSCRIBE_DIR%'; $env:OPENAI_API_KEY=$env:OPENAI_API_KEY; $env:PORT='%PORT%'; uvicorn app:app --host 0.0.0.0 --port %PORT%"
start powershell -NoExit -Command "Set-Location '%WIDGET_DIR%'; $env:TRANSCRIBE_URL='http://127.0.0.1:%PORT%/upload'; python .\widget.py"

echo Launched transcribe (FastAPI) on port %PORT% and widget.
endlocal
