# calculation_layer/module33_wolfram_verification.py
"""
模塊33: Wolfram Alpha 數學驗證
功能: 定價核對、機率計算等，用作防呆與交叉驗證的模塊
"""

import logging
from typing import Dict, Any

try:
    from services.wolfram_service import WolframService
except ImportError:
    from option_trading_system.services.wolfram_service import WolframService

logger = logging.getLogger(__name__)

class WolframVerifier:
    def __init__(self):
        self.service = WolframService()
        if self.service.is_configured:
            logger.info("✓ 模塊33 (Wolfram 數學驗證) 已初始化")
        else:
            logger.warning("! 模塊33 (Wolfram 數學驗證) 停用: 缺乏 WOLFRAM_APP_ID")
        
    def verify(self, stock_price: float, strike_price: float, 
               option_type: str, time_to_expiration_years: float, 
               volatility: float, risk_free_rate: float = 0.045, 
               breakeven_price: float = None) -> Dict[str, Any]:
        """
        執行 Wolfram Alpha 驗證，返回核對結果字典
        """
        
        if not self.service.is_configured:
            return {
                "status": "disabled", 
                "message": "Wolfram Alpha API 未設置",
                "math_verification": "N/A",
                "probability_verification": "N/A"
            }
            
        try:
            is_call = option_type.lower() in ('c', 'call')
            
            # 核對定價公式
            math_verify = self.service.verify_black_scholes(
                S=stock_price, K=strike_price, T=time_to_expiration_years,
                r=risk_free_rate, v=volatility, is_call=is_call
            )
            
            # 計算達到損益平衡點的數學機率 (如果提供)
            prob_verify = "N/A"
            if breakeven_price and breakeven_price > 0 and time_to_expiration_years > 0:
                days = max(1, int(time_to_expiration_years * 365))
                prob_verify = self.service.calculate_probability_above(
                    current_price=stock_price, target_price=breakeven_price,
                    volatility=volatility, days_to_expiry=days
                )
                
            return {
                "status": "success",
                "math_verification": math_verify,
                "probability_verification": prob_verify
            }
        except Exception as e:
            logger.error(f"Wolfram 模塊執行錯誤: {e}")
            return {
                "status": "error", 
                "error": str(e),
                "math_verification": "Error",
                "probability_verification": "Error"
            }
