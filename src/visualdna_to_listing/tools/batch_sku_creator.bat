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

REM Prompt user for product name
set /p PRODUCT_NAME="Enter product name (-p): "
if "!PRODUCT_NAME!"=="" (
    echo Error: Product name cannot be empty
    pause
    exit /b 1
)

REM Prompt user for background style
set /p BG_STYLE="Enter background style (-b): "
if "!BG_STYLE!"=="" (
    echo Error: Background style cannot be empty
    pause
    exit /b 1
)

REM Prompt user for count
set /p COUNT="Enter count (-c) [default: 1]: "
if "!COUNT!"=="" set "COUNT=1"

REM Check SKU file parameter
set "SKU_FILE=sku_list.txt"
if not exist "%SCRIPT_DIR%!SKU_FILE!" (
    echo Error: SKU file not found: %SCRIPT_DIR%!SKU_FILE!
    echo Please ensure sku_list.txt exists in the script directory
    pause
    exit /b 1
)

echo.
echo Product name: !PRODUCT_NAME!
echo Background style: !BG_STYLE!
echo Count: !COUNT!
echo SKU file: !SKU_FILE!
echo.

REM Run the batch creator
cd /d "%SCRIPT_DIR%"
python "%PYTHON_SCRIPT%" -p "!PRODUCT_NAME!" -b "!BG_STYLE!" -c !COUNT! -f "!SKU_FILE!"

echo.
echo Done!
pause
