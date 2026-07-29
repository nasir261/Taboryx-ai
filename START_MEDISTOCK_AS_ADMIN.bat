@echo off
:: Launches MediStock AI with Windows Administrator privileges (required for Wi-Fi management)
:: A UAC prompt will appear — click Yes to continue

setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%CD%\venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

:: Start API server if not already running
set "HEALTH_URL=http://127.0.0.1:8000/health"
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $resp = Invoke-WebRequest -UseBasicParsing -Uri '%HEALTH_URL%' -TimeoutSec 2; if ($resp.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"
if errorlevel 1 (
    echo Starting MediStock mobile API server...
    start "MediStock API" /MIN cmd /c "cd /d \"%CD%\" && \"%PYTHON_EXE%\" -m src.api.server --host 0.0.0.0 --port 8000"
    timeout /t 2 /nobreak >nul
)

:: Re-launch this script elevated via PowerShell if not already admin
net session >nul 2>&1
if errorlevel 1 (
    echo Requesting Administrator privileges...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd -ArgumentList '/c cd /d ""%~dp0"" && ""%PYTHON_EXE%"" -m src.app' -Verb RunAs"
    exit /b
)

:: Already elevated — launch directly
echo Running as Administrator. Launching MediStock AI...
"%PYTHON_EXE%" -m src.app

endlocal
