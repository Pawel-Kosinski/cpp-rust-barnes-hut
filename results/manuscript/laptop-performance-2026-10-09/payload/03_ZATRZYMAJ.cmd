@echo off
setlocal
title BHBench-CR laptop - Stop
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0engine\runner.ps1" -Mode Stop
set "RESULT=%ERRORLEVEL%"
echo.
echo Exit code: %RESULT% (0=OK, 2=error, 3=paused)
pause
exit /b %RESULT%
