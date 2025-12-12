from dataclasses import dataclass
from typing import Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class LongPutResult:
    """Long Put損益計算結果"""
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

class LongPutCalculator:
    """Long Put損益計算器 (100%書籍實現)
    公式: 損益 = Max(行使價-股價,0) - 期權金
    書籍來源: 《期權制勝》第三課"""
    
    def __init__(self):
        logger.info("* Long Put計算器已初始化")
    
    def calculate(self, strike_price: float, option_premium: float,
                  stock_price_at_expiry: float, calculation_date: str = None) -> LongPutResult:
        try:
            logger.info(f"開始計算Long Put損益...")
            if not self._validate_inputs(strike_price, option_premium, stock_price_at_expiry):
                raise ValueError("輸入參數無效")
            
            if calculation_date is None:
                calculation_date = datetime.now().strftime('%Y-%m-%d')
            
            intrinsic_value = max(strike_price - stock_price_at_expiry, 0)
            profit_loss = intrinsic_value - option_premium
            breakeven_price = strike_price - option_premium
            max_profit = strike_price - option_premium
            max_loss = option_premium
            
            return_percentage = (profit_loss / option_premium) * 100 if option_premium > 0 else 0
            
            logger.info(f"* Long Put計算完成")
            
            return LongPutResult(
                strike_price=strike_price, option_premium=option_premium,
                stock_price_at_expiry=stock_price_at_expiry, intrinsic_value=intrinsic_value,
                profit_loss=profit_loss, breakeven_price=breakeven_price,
                max_profit=max_profit, max_loss=max_loss, return_percentage=return_percentage,
                calculation_date=calculation_date
            )
        except Exception as e:
            logger.error(f"x Long Put計算失敗: {e}")
            raise
    
    def calculate_with_contracts(
        self,
        strike_price: float,
        option_premium: float,
        stock_price_at_expiry: float,
        num_contracts: int = 1,
        calculation_date: str = None
    ) -> Dict:
        """
        計算多張合約的 Long Put 損益
        
        參數:
            strike_price: 行使價
            option_premium: 每股期權金
            stock_price_at_expiry: 到期股價
            num_contracts: 合約數量 (默認 1)
            calculation_date: 計算日期
        
        返回:
            包含單張和總損益的字典
        """
        result = self.calculate(strike_price, option_premium, stock_price_at_expiry, calculation_date)
        
        multiplier = 100
        total_cost = option_premium * num_contracts * multiplier
        total_pnl = result.profit_loss * num_contracts * multiplier
        
        return {
            **result.to_dict(),
            'num_contracts': num_contracts,
            'multiplier': multiplier,
            'total_cost': round(total_cost, 2),
            'total_profit_loss': round(total_pnl, 2),
            'total_return_percentage': round((total_pnl / total_cost) * 100, 2) if total_cost > 0 else 0
        }
    
    def calculate_current_pnl(
        self,
        strike_price: float,
        option_premium: float,
        current_stock_price: float,
        current_option_price: float,
        num_contracts: int = 1,
        calculation_date: str = None
    ) -> Dict:
        """
        計算當前持倉損益（提前平倉情境）
        
        參數:
            strike_price: 行使價
            option_premium: 買入時支付的期權金（每股成本）
            current_stock_price: 當前股價
            current_option_price: 當前期權市場價格
            num_contracts: 合約數量
            calculation_date: 計算日期
        
        返回:
            包含當前損益、未實現盈虧等信息的字典
        """
        try:
            logger.info(f"開始計算 Long Put 當前持倉損益...")
            
            if calculation_date is None:
                calculation_date = datetime.now().strftime('%Y-%m-%d')
            
            multiplier = 100
            
            # 當前內在價值 (Put: max(K-S, 0))
            intrinsic_value = max(strike_price - current_stock_price, 0)
            
            # 當前時間價值
            time_value = max(current_option_price - intrinsic_value, 0)
            
            # 單股未實現損益
            unrealized_pnl_per_share = current_option_price - option_premium
            
            # 總成本和總損益
            total_cost = option_premium * num_contracts * multiplier
            total_current_value = current_option_price * num_contracts * multiplier
            total_unrealized_pnl = unrealized_pnl_per_share * num_contracts * multiplier
            
            return_percentage = (unrealized_pnl_per_share / option_premium) * 100 if option_premium > 0 else 0
            
            logger.info(f"* Long Put 當前持倉損益計算完成")
            
            return {
                'position_type': 'Long Put',
                'strike_price': round(strike_price, 2),
                'entry_premium': round(option_premium, 2),
                'current_stock_price': round(current_stock_price, 2),
                'current_option_price': round(current_option_price, 2),
                'intrinsic_value': round(intrinsic_value, 2),
                'time_value': round(time_value, 2),
                'unrealized_pnl_per_share': round(unrealized_pnl_per_share, 2),
                'num_contracts': num_contracts,
                'total_cost': round(total_cost, 2),
                'total_current_value': round(total_current_value, 2),
                'total_unrealized_pnl': round(total_unrealized_pnl, 2),
                'return_percentage': round(return_percentage, 2),
                'calculation_date': calculation_date
            }
            
        except Exception as e:
            logger.error(f"x Long Put 當前持倉損益計算失敗: {e}")
            raise
    
    @staticmethod
    def _validate_inputs(strike_price: float, option_premium: float, stock_price_at_expiry: float) -> bool:
        logger.info("驗證輸入參數...")
        
        if not isinstance(strike_price, (int, float)):
            logger.error(f"x 行使價必須是數字: {strike_price}")
            return False
        if not isinstance(option_premium, (int, float)):
            logger.error(f"x 期權金必須是數字: {option_premium}")
            return False
        if not isinstance(stock_price_at_expiry, (int, float)):
            logger.error(f"x 到期股價必須是數字: {stock_price_at_expiry}")
            return False
        
        if strike_price <= 0:
            logger.error(f"x 行使價必須大於0: {strike_price}")
            return False
        if option_premium <= 0:
            logger.error(f"x 期權金必須大於0: {option_premium}")
            return False
        if stock_price_at_expiry < 0:
            logger.error(f"x 股價不能為負: {stock_price_at_expiry}")
            return False
        
        if stock_price_at_expiry == 0:
            logger.warning(f"⚠️ 股價為0，這通常表示公司破產")
        if option_premium > strike_price:
            logger.warning(f"⚠️ 期權金 ({option_premium}) 大於行使價 ({strike_price})，請確認輸入正確")
        
        logger.info("* 輸入參數驗證通過")
        return True