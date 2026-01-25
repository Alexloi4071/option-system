echo ===================================================
echo 正在執行「強制環境清洗」... (解決 DLL 報錯)
echo Deep Cleaning Python Environment...
echo ===================================================

echo [1/4] 正在移除舊的、衝突的庫...
echo Removing conflicting packages...
pip uninstall -y numpy pandas scipy yfinance Flask flask-cors simplejson

echo.
echo [2/4] 正在重新安裝乾淨的穩定版本...
echo Installing clean versions...
pip install --no-cache-dir "numpy==1.23.5" "pandas==2.0.3" "scipy==1.10.1" "yfinance==0.2.40" "simplejson==3.20.2" "Flask==3.0.0" "flask-cors==4.0.0"

echo.
echo [3/4] 驗證安裝與數據連通性...
python -c "import numpy; import pandas; import scipy; import yfinance; from data_layer.data_fetcher import DataFetcher; df=DataFetcher(); dates=df.get_option_expirations('AAPL'); print('環境驗證成功！'); print('期權數據測試: ' + ('成功' if len(dates)>0 else '失敗'))"

echo.
echo [4/4] 正在啟動 Web GUI...
echo ===================================================
python -m web_layer.app

echo.
echo 如果仍然報錯，請嘗試：
echo 1. 關閉所有 Python 相關的程式 (包括 VS Code, Spyder, Jupyter)
echo 2. 重新運行此腳本。
pause
