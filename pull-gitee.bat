@echo off
chcp 65001 >nul

echo ========================================
echo Git Pull from Gitee
echo ========================================
echo.

echo Pulling from gitee master...
git pull https://gitee.com/luopub/visualdna_to_listing.git master

echo.
echo ========================================
echo Done!
echo ========================================
pause
