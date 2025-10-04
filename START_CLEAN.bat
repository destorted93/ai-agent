@echo off
REM Clean launcher - runs all services in background, no visible windows
REM Closes everything when you close the widget
REM Note: Make sure OPENAI_API_KEY is set in your environment variables

start /B wscript.exe start_hidden.vbs
exit
