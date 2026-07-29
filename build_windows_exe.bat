@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%CD%\venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

echo Building MediStock AI Windows executable...
"%PYTHON_EXE%" -m PyInstaller --clean --distpath "%CD%\dist" --workpath "%CD%\build" "%CD%\MediStockAI.spec"
if errorlevel 1 exit /b %errorlevel%

echo Build complete.
echo Output: %CD%\dist\MediStockAI.exe
endlocal
