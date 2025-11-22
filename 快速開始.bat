@echo off
chcp 65001 >nul
echo ========================================
echo 期權分析系統 - 快速開始
echo ========================================
echo.
echo 請選擇操作:
echo.
echo 1. 分析 AAPL (Apple)
echo 2. 分析 MSFT (Microsoft)
echo 3. 分析 TSLA (Tesla)
echo 4. 分析 NVDA (NVIDIA)
echo 5. 自定義股票代碼
echo 6. 查看幫助
echo 7. 退出
echo.
set /p choice="請輸入選項 (1-7): "

if "%choice%"=="1" (
    echo.
    echo 正在分析 AAPL...
    python main.py --ticker AAPL
    goto end
)

if "%choice%"=="2" (
    echo.
    echo 正在分析 MSFT...
    python main.py --ticker MSFT
    goto end
)

if "%choice%"=="3" (
    echo.
    echo 正在分析 TSLA...
    python main.py --ticker TSLA
    goto end
)

if "%choice%"=="4" (
    echo.
    echo 正在分析 NVDA...
    python main.py --ticker NVDA
    goto end
)

if "%choice%"=="5" (
    echo.
    set /p ticker="請輸入股票代碼 (例: AAPL): "
    echo.
    echo 正在分析 %ticker%...
    python main.py --ticker %ticker%
    goto end
)

if "%choice%"=="6" (
    echo.
    python main.py --help
    goto end
)

if "%choice%"=="7" (
    echo.
    echo 再見！
    exit /b 0
)

echo.
echo 無效的選項，請重新運行。

:end
echo.
echo ========================================
echo 分析完成！
echo ========================================
echo.
echo 報告文件位置: output/ 資料夾
echo 日誌文件位置: logs/ 資料夾
echo.
pause
