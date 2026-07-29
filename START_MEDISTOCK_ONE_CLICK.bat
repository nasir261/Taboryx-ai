@echo off
setlocal
cd /d "%~dp0"

set "MODE=%~1"
set "PYTHON_EXE=%CD%\venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

if /I "%MODE%"=="--desktop-only" goto launch_desktop

set "HEALTH_URL=http://127.0.0.1:8000/health"
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $resp = Invoke-WebRequest -UseBasicParsing -Uri '%HEALTH_URL%' -TimeoutSec 2; if ($resp.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"
if errorlevel 1 (
    echo Starting MediStock mobile API server on port 8000...
    start "MediStock API" /MIN cmd /c "cd /d \"%CD%\" && \"%PYTHON_EXE%\" -m src.api.server --host 0.0.0.0 --port 8000"
    timeout /t 2 /nobreak >nul
) else (
    echo MediStock mobile API already running.
)

if /I "%MODE%"=="--api-only" goto done

:launch_desktop
echo Launching MediStock desktop app...
"%PYTHON_EXE%" -m src.app

:done
endlocal
