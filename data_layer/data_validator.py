# data_layer/data_validator.py
"""
數據驗證類 (第1階段完整實現)
"""

import pandas as pd
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DataValidator:
    """數據驗證類"""
    
    @staticmethod
    def validate_stock_data(data):
        """
        驗證股票數據完整性
        
        參數:
            data: 股票數據字典
        
        返回: bool
        """
        logger.info("開始驗證股票數據...")
        
        required_fields = [
            'ticker',
            'current_price',
            'implied_volatility',
            'eps',
            'risk_free_rate'
        ]
        
        # 檢查必需字段
        missing_fields = [f for f in required_fields 
                         if f not in data or data[f] is None]
        
        if missing_fields:
            logger.error(f"x 缺少必需字段: {missing_fields}")
            return False
        
        # 檢查數據類型和範圍
        try:
            # 股價驗證
            if not isinstance(data['current_price'], (int, float)):
                logger.error(f"x 股價類型無效: {type(data['current_price'])}")
                return False
            
            if data['current_price'] <= 0:
                logger.error(f"x 股價必須大於0: {data['current_price']}")
                return False
            
            # IV驗證
            if not isinstance(data['implied_volatility'], (int, float)):
                logger.error(f"x IV類型無效: {type(data['implied_volatility'])}")
                return False
            
            if data['implied_volatility'] <= 0:
                logger.error(f"x IV必須大於0: {data['implied_volatility']}")
                return False
            
            if 0 < data['implied_volatility'] < 1:
                # 自動轉換小數格式為百分比格式
                original_iv = data['implied_volatility']
                data['implied_volatility'] = original_iv * 100
                logger.warning(f"! IV 自動轉換: {original_iv:.4f} → {data['implied_volatility']:.2f}%")
            
            # 利率驗證
            if data['risk_free_rate'] is not None:
                if not isinstance(data['risk_free_rate'], (int, float)):
                    logger.error(f"x 利率類型無效")
                    return False
                
                if data['risk_free_rate'] < 0 or data['risk_free_rate'] > 50:
                    logger.warning(f"! 利率異常: {data['risk_free_rate']}%")
            
            logger.info("* 股票數據驗證通過")
            return True
            
        except Exception as e:
            logger.error(f"x 數據驗證過程出錯: {e}")
            return False
    
    @staticmethod
    def validate_option_chain(option_chain):
        """
        驗證期權鏈數據
        
        參數:
            option_chain: 期權鏈字典
        
        返回: bool
        """
        logger.info("開始驗證期權鏈數據...")
        
        if option_chain is None:
            logger.error("x 期權鏈為None")
            return False
        
        required_keys = ['calls', 'puts', 'expiration']
        if not all(k in option_chain for k in required_keys):
            logger.error("x 期權鏈缺少必需字段")
            return False
        
        calls = option_chain['calls']
        puts = option_chain['puts']
        
        if calls.empty:
            logger.error("x Call期權鏈為空")
            return False
        
        if puts.empty:
            logger.error("x Put期權鏈為空")
            return False
        
        # 檢查必需列
        required_columns = ['strike', 'lastPrice', 'impliedVolatility']
        
        for col in required_columns:
            if col not in calls.columns or col not in puts.columns:
                logger.error(f"x 期權鏈缺少列: {col}")
                return False
        
        logger.info(f"* 期權鏈數據驗證通過")
        logger.info(f"  Calls: {len(calls)} 個")
        logger.info(f"  Puts: {len(puts)} 個")
        
        return True
    
    @staticmethod
    def validate_expiration_date(expiration_date_str):
        """
        驗證期權到期日期
        
        參數:
            expiration_date_str: 日期字符串 (YYYY-MM-DD)
        
        返回: bool
        """
        try:
            exp_date = pd.to_datetime(expiration_date_str)
            today = pd.to_datetime(datetime.now().date())
            
            if exp_date <= today:
                logger.error(f"x 到期日期已過期: {expiration_date_str}")
                return False
            
            logger.info(f"* 到期日期驗證通過: {expiration_date_str}")
            return True
            
        except Exception as e:
            logger.error(f"x 日期格式無效: {e}")
            return False


# 使用示例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    validator = DataValidator()
    
    # 測試1: 有效的股票數據
    print("=" * 70)
    print("測試1: 驗證有效的股票數據")
    print("=" * 70)
    
    test_data_valid = {
        'ticker': 'AAPL',
        'current_price': 180.50,
        'implied_volatility': 22.0,
        'eps': 6.05,
        'risk_free_rate': 4.50
    }
    
    is_valid = validator.validate_stock_data(test_data_valid)
    print(f"結果: {'* 通過' if is_valid else 'x 失敗'}\n")
    
    # 測試2: 無效的股票數據 (股價為0)
    print("=" * 70)
    print("測試2: 驗證無效的股票數據 (股價為0)")
    print("=" * 70)
    
    test_data_invalid = {
        'ticker': 'TEST',
        'current_price': 0,  # 無效
        'implied_volatility': 22.0,
        'eps': 6.05,
        'risk_free_rate': 4.50
    }
    
    is_valid = validator.validate_stock_data(test_data_invalid)
    print(f"結果: {'* 通過' if is_valid else 'x 失敗'}\n")
