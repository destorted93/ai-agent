@echo off
setlocal

REM Run the AI agent in service mode
REM Usage: run_agent_service.bat [PORT]

set PORT=%~1
if "%PORT%"=="" set PORT=6002

set SCRIPT_DIR=%~dp0
set AGENT_DIR=%SCRIPT_DIR%agent-main

echo Starting AI Agent Service on port %PORT%...
python "%AGENT_DIR%\app.py" --mode service --port %PORT%

endlocal
