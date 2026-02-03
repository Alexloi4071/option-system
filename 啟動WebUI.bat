@echo off
chcp 65001 >nul
echo ========================================
echo 期權分析系統 - Web UI 啟動
echo ========================================
echo.
echo 正在啟動 Web 服務器...
echo.
echo 啟動後請在瀏覽器中訪問:
echo http://127.0.0.1:5000
echo.
echo 按 Ctrl+C 停止服務
echo ========================================
echo.

cd web_layer
python app.py

pause
