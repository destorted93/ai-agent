@echo off
setlocal

REM Run the main AI agent

set SCRIPT_DIR=%~dp0
set AGENT_MAIN_DIR=%SCRIPT_DIR%agent-main

echo Starting AI Agent (Interactive Mode)...
python "%AGENT_MAIN_DIR%\app.py" --mode interactive

endlocal
