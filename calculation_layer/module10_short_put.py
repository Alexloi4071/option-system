from dataclasses import dataclass
from typing import Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class ShortPutResult:
    strike_price: float
    option_premium: float
    stock_price_at_expiry: float
    intrinsic_value: float
    profit_loss: float
    breakeven_price: float
    max_profit: float
    max_loss: float
    return_percentage: float
    calculation_date: str
    
    def to_dict(self) -> Dict:
        return {
            'strike_price': round(self.strike_price, 2),
            'option_premium': round(self.option_premium, 2),
            'stock_price_at_expiry': round(self.stock_price_at_expiry, 2),
            'intrinsic_value': round(self.intrinsic_value, 2),
            'profit_loss': round(self.profit_loss, 2),
            'breakeven_price': round(self.breakeven_price, 2),
            'max_profit': round(self.max_profit, 2),
            'max_loss': round(self.max_loss, 2),
            'return_percentage': round(self.return_percentage, 2),
            'calculation_date': self.calculation_date
        }

class ShortPutCalculator:
    """Short Put損益計算器 (100%書籍實現)
    公式: 損益 = 期權金 - Max(行使價-股價,0)
    書籍來源: 《期權制勝》第五課"""
    
    def __init__(self):
        logger.info("* Short Put計算器已初始化")
    
    def calculate(self, strike_price: float, option_premium: float,
                  stock_price_at_expiry: float, calculation_date: str = None) -> ShortPutResult:
        try:
            logger.info(f"開始計算Short Put損益...")
            if not self._validate_inputs(strike_price, option_premium, stock_price_at_expiry):
                raise ValueError("輸入參數無效")
            
            if calculation_date is None:
                calculation_date = datetime.now().strftime('%Y-%m-%d')
            
            intrinsic_value = max(strike_price - stock_price_at_expiry, 0)
            profit_loss = option_premium - intrinsic_value
            breakeven_price = strike_price - option_premium
            max_profit = option_premium
            max_loss = strike_price - option_premium
            
            return_percentage = (profit_loss / option_premium) * 100 if option_premium > 0 else 0
            
            logger.info(f"  Short Put計算完成")
            
            return ShortPutResult(
                strike_price=strike_price, option_premium=option_premium,
                stock_price_at_expiry=stock_price_at_expiry, intrinsic_value=intrinsic_value,
                profit_loss=profit_loss, breakeven_price=breakeven_price,
                max_profit=max_profit, max_loss=max_loss, return_percentage=return_percentage,
                calculation_date=calculation_date
            )
        except Exception as e:
            logger.error(f"x Short Put計算失敗: {e}")
            raise
    
    @staticmethod
    def _validate_inputs(strike_price: float, option_premium: float, stock_price_at_expiry: float) -> bool:
        logger.info("驗證輸入參數...")
        if not all(isinstance(x, (int, float)) for x in [strike_price, option_premium, stock_price_at_expiry]):
            return False
        if strike_price <= 0 or option_premium <= 0 or stock_price_at_expiry < 0:
            return False
        logger.info("  輸入參數驗證通過")
        return True

# print("✓ Module 2,7,8,9,10 完整代碼已生成")