@echo off
chcp 65001 >nul

echo ========================================
echo Git Pull from Gitee
echo ========================================
echo.

echo Pulling from gitee master...
git pull gitee master

echo.
echo ========================================
echo Done!
echo ========================================
pause
