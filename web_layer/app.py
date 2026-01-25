# web_layer/app.py
"""
期權分析系統 Web GUI 後端 (Flask)
"""

import os
import sys
import logging
import json
import time
import threading
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory, Response

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

# 進度追蹤存儲
progress_store = {}

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
        "selected_expirations": ["2025-06-20", "2025-07-18"], (可選，用於 Module 27)
        "confidence": 1.0, (可選)
        "strike": 150.0, (可選)
        "premium": 5.5, (可選)
        "type": "C", (可選)
        "use_ibkr": false (可選)
    }
    """
    try:
        data = request.json
        if not data or ((not data.get('ticker')) and (not data.get('target_date') and not data.get('expiration'))):
             # 兼容 target_date 或 expiration 字段
            return jsonify({'status': 'error', 'message': '缺少股票代碼或到期日'}), 400
        
        task_id = data.get('task_id')
        ticker = data.get('ticker').upper()
        # Frontend uses 'target_date', keeping 'expiration' for backward compat
        expiration = data.get('target_date') or data.get('expiration')
        selected_expirations = data.get('selected_expirations') 
        confidence = float(data.get('confidence_level', 0.68))
        use_ibkr = data.get('use_ibkr', False)
        
        # User Overrides
        user_strike = float(data.get('strike_price')) if data.get('strike_price') else None
        user_direction = data.get('direction') # 'CALL', 'PUT' or None
        user_rate = float(data.get('risk_free_rate')) if data.get('risk_free_rate') else None
        
        # New Overrides (Phase 8.1)
        user_iv = float(data.get('iv')) if data.get('iv') else None
        user_delta = float(data.get('delta')) if data.get('delta') else None
        user_gamma = float(data.get('gamma')) if data.get('gamma') else None
        user_theta = float(data.get('theta')) if data.get('theta') else None
        user_vega = float(data.get('vega')) if data.get('vega') else None
        user_rho = float(data.get('rho')) if data.get('rho') else None

        # Legacy fields mapping
        strike = user_strike 
        option_type = user_direction
        
        # 為了 run_complete_analysis 調用一致性，這裡直接定義變數
        premium = None
        

        
        logger.info(f"收到分析請求: {ticker}, 到期日: {expiration}, 多選到期日: {selected_expirations}, IBKR: {use_ibkr}")
        
        # 初始化進度追蹤
        if task_id:
            progress_store[task_id] = {
                'status': 'running',
                'progress': 0,
                'step': 0,
                'total_steps': 5,
                'message': '初始化分析...',
                'current_module': '準備中',
                'completed_modules': [],
                'start_time': time.time(),
                'estimated_remaining': None
            }
        
        # 創建進度回調函數
        def progress_callback(step, total, message, module_name=None):
            if task_id and task_id in progress_store:
                elapsed = time.time() - progress_store[task_id]['start_time']
                progress_pct = int((step / total) * 100)
                
                # 估算剩餘時間
                if step > 0:
                    estimated_total = elapsed * total / step
                    estimated_remaining = max(0, estimated_total - elapsed)
                else:
                    estimated_remaining = None
                
                progress_store[task_id].update({
                    'progress': progress_pct,
                    'step': step,
                    'total_steps': total,
                    'message': message,
                    'current_module': module_name or message,
                    'estimated_remaining': estimated_remaining
                })
                
                if module_name and module_name not in progress_store[task_id]['completed_modules']:
                    if step > 0:  # 不是第一步時，上一個模塊已完成
                        progress_store[task_id]['completed_modules'].append(module_name)
        
        # 執行分析 - 處理 None 值
        results = analysis_system.run_complete_analysis(
            ticker=ticker,
            expiration=expiration,
            confidence=confidence,
            use_ibkr=use_ibkr,
            strike=user_strike if user_strike is not None else None,          # 明確傳遞 None
            option_type=user_direction,  # User override or None
            risk_free_rate=user_rate if user_rate is not None else None,      # 明確傳遞 None
            iv=user_iv if user_iv is not None else None,
            delta=user_delta if user_delta is not None else None, 
            gamma=user_gamma if user_gamma is not None else None, 
            theta=user_theta if user_theta is not None else None, 
            vega=user_vega if user_vega is not None else None, 
            rho=user_rho if user_rho is not None else None,
            selected_expirations=selected_expirations,
            progress_callback=progress_callback
        )
        
        # 更新進度為完成
        if task_id and task_id in progress_store:
            progress_store[task_id].update({
                'status': 'completed',
                'progress': 100,
                'message': '分析完成！'
            })
        
        if results['status'] == 'success':
            # 使用更穩健的序列化方法
            try:
                # 1. 先嘗試標準轉換
                serializable_results = convert_to_serializable(results)
                
                # 2. 強制檢查 calculations 是否存在 (Debug)
                if 'calculations' not in serializable_results:
                    logger.error("CRITICAL: 'calculations' key missing after serialization!")
                    # 嘗試從原始結果恢復
                    if 'calculations' in results:
                         serializable_results['calculations'] = convert_to_serializable(results['calculations'])
                
                # 3. 確保 raw_data 存在
                if 'raw_data' not in serializable_results and 'raw_data' in results:
                     serializable_results['raw_data'] = convert_to_serializable(results['raw_data'])

                # 4. 生成策略推薦 (如果沒有的話)
                if 'recommendations' not in serializable_results:
                    serializable_results['recommendations'] = _generate_strategy_recommendations(serializable_results)

                # 5. 最終序列化檢查
                # 使用 json.dumps 測試是否真的可序列化，如果有 NaN/Infinity 會被處理
                json_str = json.dumps(serializable_results, allow_nan=False, default=str)
                final_obj = json.loads(json_str)
                
                logger.info(f"API Response prepared. Calculations keys: {list(final_obj.get('calculations', {}).keys())}")
                return jsonify(final_obj)
            except Exception as se:
                logger.error(f"Serialization Error: {se}")
                # Fallback: 只返回基本狀態，避免 500
                return jsonify({
                    'status': 'error', 
                    'message': f'Data Serialization Failed: {str(se)}'
                }), 500
        else:
            logger.error(f"Analysis Failed Logic: {results}")
            return jsonify(convert_to_serializable(results)), 500
            
    except Exception as e:
        logger.error(f"API 錯誤: {e}")
        if task_id and task_id in progress_store:
            progress_store[task_id].update({
                'status': 'error',
                'message': str(e)
            })
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/progress/<task_id>', methods=['GET'])
def get_progress(task_id):
    """獲取分析進度"""
    if task_id in progress_store:
        return jsonify(progress_store[task_id])
    else:
        return jsonify({'status': 'not_found', 'message': '任務不存在'}), 404


@app.route('/api/progress/stream/<task_id>')
def progress_stream(task_id):
    """SSE 進度流"""
    def generate():
        while True:
            if task_id in progress_store:
                data = progress_store[task_id]
                yield f"data: {json.dumps(data)}\n\n"
                
                if data.get('status') in ['completed', 'error']:
                    # 清理完成的任務
                    time.sleep(1)
                    if task_id in progress_store:
                        del progress_store[task_id]
                    break
            else:
                yield f"data: {json.dumps({'status': 'waiting'})}\n\n"
            
            time.sleep(0.5)  # 每 0.5 秒更新一次
    
    return Response(generate(), mimetype='text/event-stream')

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

def _generate_strategy_recommendations(data):
    """
    生成基本策略推薦
    """
    recommendations = []
    
    try:
        raw_data = data.get('raw_data', {})
        calculations = data.get('calculations', {})
        
        # 基本數據
        current_price = raw_data.get('current_price', 0)
        iv = raw_data.get('implied_volatility', 0)
        
        # Module 18 IV Rank
        module18 = calculations.get('module18_historical_volatility', {})
        iv_rank = module18.get('iv_rank', 50)
        
        # Module 1 支撐阻力
        module1 = calculations.get('module1_support_resistance_multi', {})
        conf90 = module1.get('results', {}).get('90%', {})
        
        # 生成推薦邏輯
        if iv_rank > 70:
            # 高IV環境 - 推薦賣出策略
            recommendations.append({
                'strategy': 'Short Put Credit Spread',
                'rationale': f'高IV環境 ({iv_rank:.0f}% Rank)，適合賣出波動率收取權利金',
                'confidence': 'HIGH'
            })
        elif iv_rank < 30:
            # 低IV環境 - 推薦買入策略  
            recommendations.append({
                'strategy': 'Long Call',
                'rationale': f'低IV環境 ({iv_rank:.0f}% Rank)，買入期權成本相對較低',
                'confidence': 'MEDIUM'
            })
        else:
            # 正常IV環境
            recommendations.append({
                'strategy': 'Iron Condor',
                'rationale': f'正常IV環境 ({iv_rank:.0f}% Rank)，可用中性策略收取時間價值',
                'confidence': 'MEDIUM'
            })
        
        # 第二推薦基於技術面
        if conf90 and current_price:
            support = conf90.get('support', 0)
            resistance = conf90.get('resistance', 0)
            
            if current_price > support * 1.05:  # 價格接近阻力位
                recommendations.append({
                    'strategy': 'Bear Call Spread',
                    'rationale': f'股價接近阻力位 (${resistance:.2f})，適合看漲價差',
                    'confidence': 'MEDIUM'
                })
            elif current_price < resistance * 0.95:  # 價格接近支持位
                recommendations.append({
                    'strategy': 'Bull Put Spread', 
                    'rationale': f'股價接近支持位 (${support:.2f})，適合牛市價差',
                    'confidence': 'MEDIUM'
                })
        
    except Exception as e:
        logger.error(f"策略推薦生成失敗: {e}")
        recommendations = [{
            'strategy': '觀望',
            'rationale': '數據不足，建議觀望',
            'confidence': 'LOW'
        }]
    
    return recommendations

@app.route('/api/system_status', methods=['GET'])
def system_status():
    """獲取系統狀態"""
    # 檢查 IBKR 連接狀態
    ibkr_status = False
    if hasattr(analysis_system, 'fetcher') and hasattr(analysis_system.fetcher, 'client'):
        try:
            # 檢查 client 是否已連接
            ibkr_status = analysis_system.fetcher.client.isConnected()
        except:
            ibkr_status = False

    status = {
        'version': settings.VERSION,
        'ibkr_connected': ibkr_status, # Changed key from ibkr_enabled to reflect real status
        'ibkr_enabled': settings.IBKR_ENABLED, # Keep config status
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