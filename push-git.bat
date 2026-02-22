@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo Git Push Script for visualdna_to_listing
echo ========================================
echo.

:: Get commit message from user or use default
set /p commit_msg="Enter commit message (press Enter for default): "
if "%commit_msg%"=="" (
    set commit_msg=Auto commit: %date% %time:~0,8%
)

echo.
echo [1/4] Adding files...
git add .

echo.
echo [2/4] Committing changes...
git commit -m "%commit_msg%"

echo.
echo [3/4] Pushing to Gitee...
git push https://gitee.com/luopub/visualdna_to_listing.git master

echo.
echo [4/4] Pushing to GitHub...
git push https://github.com/luopub/visualdna_to_listing.git master

echo.
echo ========================================
echo Done!
echo ========================================
pause
