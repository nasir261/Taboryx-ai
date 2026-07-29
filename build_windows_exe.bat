@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%CD%\venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

echo Building Taboryx AI Windows executable...
"%PYTHON_EXE%" -m PyInstaller --clean --distpath "%CD%\dist" --workpath "%CD%\build" "%CD%\TaboryxAI.spec"
if errorlevel 1 exit /b %errorlevel%

echo Build complete.
echo Output: %CD%\dist\TaboryxAI.exe
endlocal
