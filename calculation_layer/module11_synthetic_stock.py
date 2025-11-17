import logging
from dataclasses import dataclass
from typing import Dict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SyntheticStockResult:
    """合成正股計算結果"""
    strike_price: float
    call_premium: float
    put_premium: float
    synthetic_price: float
    current_stock_price: float
    difference: float
    arbitrage_opportunity: bool
    strategy: str
    calculation_date: str
    
    def to_dict(self) -> Dict:
        return {
            'strike_price': round(self.strike_price, 2),
            'call_premium': round(self.call_premium, 2),
            'put_premium': round(self.put_premium, 2),
            'synthetic_price': round(self.synthetic_price, 2),
            'current_stock_price': round(self.current_stock_price, 2),
            'difference': round(self.difference, 2),
            'arbitrage_opportunity': self.arbitrage_opportunity,
            'strategy': self.strategy,
            'calculation_date': self.calculation_date
        }


class SyntheticStockCalculator:
    """
    合成正股計算器
    
    書籍來源: 《期權制勝2》第二課
    
    公式 (100%書籍):
    ────────────────────────────────
    Long Call + Short Put = 合成Long Stock
    合成價格 = Call金 - Put金 + 行使價
    
    Short Call + Long Put = 合成Short Stock
    合成價格 = 行使價 - (Call金 - Put金)
    
    注意:
    - 本模塊採用書中到期日的簡化平價關係，忽略了利率折現因子 e^(-rT)。
    - 若需更嚴謹的理論價，可在外部加入利率與剩餘天數的折現調整。
    
    理論:
    期權組合可以複製正股的損益特徵
    當合成價格與實際股價有差異時
    存在套戥機會
    ────────────────────────────────
    """
    
    def __init__(self):
        logger.info("✓ 合成正股計算器已初始化")
    
    def calculate(self,
                  strike_price: float,
                  call_premium: float,
                  put_premium: float,
                  current_stock_price: float,
                  calculation_date: str = None) -> SyntheticStockResult:
        """
        計算合成正股價格
        
        參數:
            strike_price: 行使價
            call_premium: Call期權金
            put_premium: Put期權金
            current_stock_price: 當前股價
            calculation_date: 計算日期
        
        返回:
            SyntheticStockResult: 完整計算結果
        """
        try:
            logger.info(f"開始計算合成正股...")
            logger.info(f"  行使價: ${strike_price:.2f}")
            logger.info(f"  Call金: ${call_premium:.2f}")
            logger.info(f"  Put金: ${put_premium:.2f}")
            logger.info(f"  當前股價: ${current_stock_price:.2f}")
            
            if not self._validate_inputs(strike_price, call_premium, put_premium, current_stock_price):
                raise ValueError("輸入參數無效")
            
            if calculation_date is None:
                calculation_date = datetime.now().strftime('%Y-%m-%d')
            
            # 計算合成價格
            # 公式: 合成價 = Call金 - Put金 + 行使價
            synthetic_price = call_premium - put_premium + strike_price
            
            # 計算差異
            difference = current_stock_price - synthetic_price
            
            # 判斷套戥機會
            arbitrage_opportunity = abs(difference) > 0.10
            
            # 確定策略
            if arbitrage_opportunity:
                if difference > 0:
                    strategy = "沽出實股，買入合成空"
                else:
                    strategy = "買入實股，沽出合成多"
            else:
                strategy = "無明顯套戥機會"
            
            logger.info(f"  計算結果:")
            logger.info(f"    合成價格: ${synthetic_price:.2f}")
            logger.info(f"    差異: ${difference:.2f}")
            logger.info(f"    套戥機會: {arbitrage_opportunity}")
            logger.info(f"    策略: {strategy}")
            
            result = SyntheticStockResult(
                strike_price=strike_price,
                call_premium=call_premium,
                put_premium=put_premium,
                synthetic_price=synthetic_price,
                current_stock_price=current_stock_price,
                difference=difference,
                arbitrage_opportunity=arbitrage_opportunity,
                strategy=strategy,
                calculation_date=calculation_date
            )
            
            logger.info(f"✓ 合成正股計算完成")
            return result
            
        except Exception as e:
            logger.error(f"✗ 合成正股計算失敗: {e}")
            raise
    
    @staticmethod
    def _validate_inputs(strike_price: float, call_premium: float, 
                        put_premium: float, current_stock_price: float) -> bool:
        logger.info("驗證輸入參數...")
        
        if not all(isinstance(x, (int, float)) for x in [strike_price, call_premium, put_premium, current_stock_price]):
            logger.error("✗ 所有參數必須是數字")
            return False
        
        if strike_price <= 0 or current_stock_price <= 0:
            logger.error("✗ 股價和行使價必須大於0")
            return False
        
        if call_premium < 0 or put_premium < 0:
            logger.error("✗ 期權金不能為負")
            return False
        
        logger.info("✓ 輸入參數驗證通過")
        return True