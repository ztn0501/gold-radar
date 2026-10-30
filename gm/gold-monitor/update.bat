@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   黄金盯盘台 - 一键更新数据
echo ============================================
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 update.py
) else (
    python update.py
)
if errorlevel 1 (
    echo.
    echo [失败] 请确认已安装 Python 3（python.org 下载，安装时勾选 Add to PATH）
    pause
    exit /b 1
)
start "" "index.html"
