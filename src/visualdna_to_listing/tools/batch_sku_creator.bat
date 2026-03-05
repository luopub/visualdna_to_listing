@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================================
echo Batch SKU Image Creator
echo ============================================================
echo.

REM Get the script directory
set "SCRIPT_DIR=%~dp0"
set "PYTHON_SCRIPT=%SCRIPT_DIR%batch_sku_creator.py"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Run the batch creator
cd /d "%SCRIPT_DIR%"
python "%PYTHON_SCRIPT%" -p "phone bag for women" -b model_female_studio -f sku_list.txt

echo.
echo Done!
pause
