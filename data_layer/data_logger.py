# data_layer/data_logger.py
"""
數據日誌系統
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class DataLogger:
    """數據日誌記錄類"""
    
    def __init__(self, log_dir='logs/data/'):
        """
        初始化數據日誌系統
        
        參數:
            log_dir: 日誌目錄
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化數據庫管理器
        try:
            from data_layer.database_manager import DatabaseManager
            self.db = DatabaseManager()
        except ImportError:
            self.db = None
            logger.warning("DatabaseManager not found, falling back to local logging only")
            
        logger.info(f"數據日誌系統已初始化，目錄: {self.log_dir}")
    
    def log_data_fetch(self, ticker: str, data_type: str, 
                       status: str, details: Dict[str, Any] = None,
                       data_source: str = None, fallback_used: bool = False):
        """
        記錄數據獲取日誌
        
        參數:
            ticker: 股票代碼
            data_type: 數據類型
            status: 狀態 (success/failure)
            details: 詳細信息
            data_source: 使用的數據源 (ibkr, yfinance, yahoo_v2, etc.)
            fallback_used: 是否使用了降級方案
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'ticker': ticker,
            'data_type': data_type,
            'status': status,
            'data_source': data_source,
            'fallback_used': fallback_used,
            'details': details or {}
        }
        
        # 寫入日誌文件
        log_file = self.log_dir / f"data_fetch_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            
            source_info = f" ({data_source})" if data_source else ""
            fallback_info = " [降級]" if fallback_used else ""
            logger.info(f"數據獲取日誌已記錄: {ticker} - {data_type} - {status}{source_info}{fallback_info}")
            
        except Exception as e:
            logger.error(f"記錄數據獲取日誌失敗: {e}")
    
    def log_api_failure(self, api_name: str, error_message: str, 
                       context: Dict[str, Any] = None):
        """
        記錄 API 故障日誌
        
        參數:
            api_name: API 名稱 (ibkr, yfinance, yahoo_v2, etc.)
            error_message: 錯誤消息
            context: 上下文信息
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'api_name': api_name,
            'error_message': error_message,
            'context': context or {}
        }
        
        log_file = self.log_dir / f"api_failures_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            
            logger.warning(f"API 故障已記錄: {api_name} - {error_message}")
            
        except Exception as e:
            logger.error(f"記錄 API 故障日誌失敗: {e}")
    
    def log_calculation(self, ticker: str, module: str, 
                       status: str, result: Dict[str, Any] = None):
        """
        記錄計算日誌 (並寫入 Supabase module_run_log)
        
        參數:
            ticker: 股票代碼
            module: 計算模塊
            status: 狀態
            result: 計算結果
        """
        timestamp = datetime.now().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'ticker': ticker,
            'module': module,
            'status': status,
            'result': result or {}
        }
        
        log_file = self.log_dir / f"calculations_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False, default=str) + '\n')
            
            logger.info(f"計算日誌已記錄: {ticker} - {module} - {status}")
            
            # 同步寫入 Supabase
            if hasattr(self, 'db') and self.db and self.db.is_configured:
                # 簡單提取評分
                score = None
                signal = None
                if result:
                    score = result.get('score', result.get('confidence', None))
                    signal = result.get('signal', result.get('trend', None))
                
                # 計算時間轉為 short date
                an_date = datetime.now().strftime('%Y-%m-%d')
                self.db.insert_module_log(
                    run_id=f"run_{int(datetime.now().timestamp())}",
                    ticker=ticker,
                    analysis_date=an_date,
                    module_name=module,
                    score=float(score) if score is not None else None,
                    signal=str(signal) if signal is not None else None,
                    raw_data=result or {}
                )
                
        except Exception as e:
            logger.error(f"記錄計算日誌失敗: {e}")
            
    def log_iv_surface(self, ticker: str, expiration_date: str, 
                       strike_price: float, option_type: str, 
                       implied_volatility: float, delta: float = None):
        """將 IV 歷史資料寫入 Supabase (取代部分冗餘的 jsonl 紀錄)"""
        record_date = datetime.now().strftime('%Y-%m-%d')
        if hasattr(self, 'db') and self.db and self.db.is_configured:
            try:
                self.db.insert_iv_history(
                    ticker=ticker,
                    record_date=record_date,
                    expiration_date=expiration_date,
                    strike_price=strike_price,
                    option_type=option_type,
                    implied_volatility=implied_volatility,
                    delta=delta
                )
            except Exception as e:
                logger.error(f"寫入 IV 歷史資料庫失敗: {e}")

    def log_scanner_alert(self, ticker: str, alert_type: str, message: str, data: dict = None):
        """記錄 IBKR 掃描器觸發的 Alerts"""
        alert_time = datetime.now().isoformat()
        if hasattr(self, 'db') and self.db and self.db.is_configured:
            try:
                self.db.insert_scanner_alert(
                    ticker=ticker,
                    alert_time=alert_time,
                    alert_type=alert_type,
                    message=message,
                    data=data or {}
                )
            except Exception as e:
                logger.error(f"寫入掃描器 Alert 到資料庫失敗: {e}")

    def log_trade_decision(self, ticker: str, action: str, 
                           strategy_name: str = None, 
                           option_details: dict = None, 
                           ai_confidence_score: float = None, 
                           ai_reasoning: str = None):
        """記錄 AI 或策略模組產生的最終交易決策"""
        decision_time = datetime.now().isoformat()
        decision_id = f"dec_{int(datetime.now().timestamp())}"
        if hasattr(self, 'db') and self.db and self.db.is_configured:
            try:
                self.db.insert_trade_decision(
                    decision_id=decision_id,
                    ticker=ticker,
                    decision_time=decision_time,
                    action=action,
                    strategy_name=strategy_name,
                    option_details=option_details,
                    ai_confidence_score=ai_confidence_score,
                    ai_reasoning=ai_reasoning
                )
            except Exception as e:
                logger.error(f"寫入交易決策至資料庫失敗: {e}")
    
    def log_validation(self, ticker: str, validation_type: str, 
                      status: str, errors: list = None):
        """
        記錄驗證日誌
        
        參數:
            ticker: 股票代碼
            validation_type: 驗證類型
            status: 狀態
            errors: 錯誤信息列表
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'ticker': ticker,
            'validation_type': validation_type,
            'status': status,
            'errors': errors or []
        }
        
        log_file = self.log_dir / f"validations_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            
            logger.info(f"驗證日誌已記錄: {ticker} - {validation_type} - {status}")
            
        except Exception as e:
            logger.error(f"記錄驗證日誌失敗: {e}")
    
    def log_error(self, error_type: str, error_message: str, 
                  context: Dict[str, Any] = None):
        """
        記錄錯誤日誌
        
        參數:
            error_type: 錯誤類型
            error_message: 錯誤消息
            context: 上下文信息
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'error_type': error_type,
            'error_message': error_message,
            'context': context or {}
        }
        
        log_file = self.log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            
            logger.error(f"錯誤日誌已記錄: {error_type} - {error_message}")
            
        except Exception as e:
            logger.error(f"記錄錯誤日誌失敗: {e}")
    
    def get_daily_summary(self, date: str = None) -> Dict[str, Any]:
        """
        獲取每日摘要
        
        參數:
            date: 日期 (YYYYMMDD格式)，默認今天
        
        返回: dict
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        summary = {
            'date': date,
            'data_fetches': 0,
            'calculations': 0,
            'validations': 0,
            'errors': 0
        }
        
        # 統計各類型日誌數量
        for log_type in ['data_fetch', 'calculations', 'validations', 'errors']:
            log_file = self.log_dir / f"{log_type}_{date}.jsonl"
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    count = sum(1 for _ in f)
                    summary[f"{log_type}s"] = count
        
        return summary


# 使用示例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    data_logger = DataLogger()
    
    # 測試記錄數據獲取日誌
    data_logger.log_data_fetch(
        ticker='AAPL',
        data_type='stock_info',
        status='success',
        details={'price': 180.50, 'volume': 1000000}
    )
    
    # 測試記錄計算日誌
    data_logger.log_calculation(
        ticker='AAPL',
        module='module1_support_resistance',
        status='success',
        result={'support': 168.60, 'resistance': 192.40}
    )
    
    # 測試記錄驗證日誌
    data_logger.log_validation(
        ticker='AAPL',
        validation_type='stock_data',
        status='success'
    )
    
    # 測試記錄錯誤日誌
    data_logger.log_error(
        error_type='DataFetchError',
        error_message='無法獲取數據',
        context={'ticker': 'INVALID'}
    )
    
    # 獲取每日摘要
    summary = data_logger.get_daily_summary()
    print(f"每日摘要: {summary}")
