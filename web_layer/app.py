# web_layer/app.py
"""
期權分析系統 Web GUI 後端 (Flask)
"""

import os
import sys
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory

# 添加項目根目錄到 Python 路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.insert(0, root_dir)

from main import OptionsAnalysisSystem
from config.settings import settings
from utils.serialization import convert_to_serializable

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', template_folder='templates')

# 初始化分析系統
# 注意：這裡不強制使用 IBKR，讓 DataFetcher 根據配置決定
analysis_system = OptionsAnalysisSystem()

@app.route('/')
def index():
    """主頁面"""
    return render_template('index.html', version=settings.VERSION)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """
    執行期權分析 API
    
    請求體:
    {
        "ticker": "AAPL",
        "expiration": "2025-06-20", (可選)
        "confidence": 1.0, (可選)
        "strike": 150.0, (可選)
        "premium": 5.5, (可選)
        "type": "C", (可選)
        "use_ibkr": false (可選)
    }
    """
    try:
        data = request.json
        if not data or 'ticker' not in data:
            return jsonify({'status': 'error', 'message': '缺少股票代碼 (ticker)'}), 400
        
        ticker = data['ticker'].upper()
        expiration = data.get('expiration')
        confidence = float(data.get('confidence', 1.0))
        strike = float(data['strike']) if data.get('strike') else None
        premium = float(data['premium']) if data.get('premium') else None
        option_type = data.get('type')
        use_ibkr = data.get('use_ibkr')
        
        logger.info(f"收到分析請求: {ticker}, 到期日: {expiration}, IBKR: {use_ibkr}")
        
        # 執行分析
        results = analysis_system.run_complete_analysis(
            ticker=ticker,
            expiration=expiration,
            confidence=confidence,
            use_ibkr=use_ibkr,
            strike=strike,
            premium=premium,
            option_type=option_type
        )
        
        if results['status'] == 'success':
            # 處理結果中的特殊對象 (如 DataFrame, numpy types, datetime) 以便 JSON 序列化
            serializable_results = convert_to_serializable(results)
            return jsonify(serializable_results)
        else:
            serializable_results = convert_to_serializable(results)
            return jsonify(serializable_results), 500
            
    except Exception as e:
        logger.error(f"API 錯誤: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/expirations', methods=['GET'])
def get_expirations():
    """獲取期權到期日列表"""
    ticker = request.args.get('ticker')
    if not ticker:
        return jsonify({'status': 'error', 'message': '缺少股票代碼'}), 400
    
    try:
        # 使用 DataFetcher 獲取到期日
        fetcher = analysis_system.fetcher
        expirations = fetcher.get_option_expirations(ticker.upper())
        
        if expirations:
            return jsonify({'status': 'success', 'expirations': expirations})
        else:
            return jsonify({'status': 'error', 'message': '無法獲取到期日'}), 404
            
    except Exception as e:
        logger.error(f"獲取到期日失敗: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/system_status', methods=['GET'])
def system_status():
    """獲取系統狀態"""
    status = {
        'version': settings.VERSION,
        'ibkr_enabled': settings.IBKR_ENABLED,
        'timestamp': datetime.now().isoformat()
    }
    
    # 檢查 DataFetcher 狀態
    if hasattr(analysis_system, 'fetcher'):
        fetcher_status = analysis_system.fetcher.get_api_status_report()
        status['data_fetcher'] = fetcher_status
        
    return jsonify(status)

if __name__ == '__main__':
    # 開發模式運行
    print("\n" + "="*70)
    print("Web GUI 服務已啟動！")
    print("請在瀏覽器中訪問: http://127.0.0.1:5000")
    print("按 Ctrl+C 停止服務")
    print("="*70 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)