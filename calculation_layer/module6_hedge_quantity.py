# calculation_layer/module6_hedge_quantity.py
"""
模塊6: 對沖量計算 (Hedge Quantity)
書籍來源: 《期權制勝》第七課
"""

import logging
from dataclasses import dataclass
from typing import Dict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class HedgeQuantityResult:
    """對沖量計算結果"""
    stock_quantity: int
    stock_price: float
    portfolio_value: float
    option_multiplier: int
    hedge_contracts: int
    coverage_percentage: float
    calculation_date: str
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        return {
            'stock_quantity': self.stock_quantity,
            'stock_price': round(self.stock_price, 2),
            'portfolio_value': round(self.portfolio_value, 2),
            'option_multiplier': self.option_multiplier,
            'hedge_contracts': self.hedge_contracts,
            'coverage_percentage': round(self.coverage_percentage, 2),
            'calculation_date': self.calculation_date
        }


class HedgeQuantityCalculator:
    """
    對沖量計算器
    
    書籍來源: 《期權制勝》第七課
    
    公式 (100%書籍):
    ────────────────────────────────
    對沖份數 = 正股持倉市值 / (股價 × 期權合約乘數)
    
    其中:
    - 正股持倉市值 = 正股數量 × 股價
    - 期權合約乘數 = 100 (美股標準)
    
    原理:
    一張期權合約代表100股股票
    對沖就是用期權來抵消正股的風險
    1張Put期權可以對沖100股正股
    
    例子:
    - 持有1000股，股價100：市值10萬
    - 1張期權對應100股
    - 需要 10萬 / (100×100) = 10張期權
    ────────────────────────────────
    """
    
    OPTION_MULTIPLIER = 100  # 美股期權標準乘數
    
    def __init__(self):
        """初始化計算器"""
        logger.info("✓ 對沖量計算器已初始化")
    
    def calculate(self,
                  stock_quantity: int,
                  stock_price: float,
                  calculation_date: str = None) -> HedgeQuantityResult:
        """
        計算對沖量
        
        參數:
            stock_quantity: 正股數量 (股)
            stock_price: 股價 (美元)
            calculation_date: 計算日期
        
        返回:
            HedgeQuantityResult: 完整計算結果
        """
        try:
            logger.info(f"開始計算對沖量...")
            logger.info(f"  正股數量: {stock_quantity}股")
            logger.info(f"  股價: ${stock_price:.2f}")
            
            # 驗證輸入
            if not self._validate_inputs(stock_quantity, stock_price):
                raise ValueError("輸入參數無效")
            
            if calculation_date is None:
                calculation_date = datetime.now().strftime('%Y-%m-%d')
            
            # 計算持倉市值
            portfolio_value = stock_quantity * stock_price
            
            logger.info(f"  持倉市值: ${portfolio_value:.2f}")
            
            # 計算對沖份數
            # 公式: 對沖份數 = 市值 / (股價 × 100)
            hedge_contracts = int(portfolio_value / (stock_price * self.OPTION_MULTIPLIER))
            
            # 計算覆蓋率
            coverage_percentage = (hedge_contracts * self.OPTION_MULTIPLIER * 100) / (stock_quantity * 100)
            
            logger.info(f"  計算結果:")
            logger.info(f"    對沖合約數: {hedge_contracts}張")
            logger.info(f"    覆蓋率: {coverage_percentage:.2f}%")
            
            result = HedgeQuantityResult(
                stock_quantity=stock_quantity,
                stock_price=stock_price,
                portfolio_value=portfolio_value,
                option_multiplier=self.OPTION_MULTIPLIER,
                hedge_contracts=hedge_contracts,
                coverage_percentage=coverage_percentage,
                calculation_date=calculation_date
            )
            
            logger.info(f"✓ 對沖量計算完成")
            return result
            
        except Exception as e:
            logger.error(f"✗ 對沖量計算失敗: {e}")
            raise
    
    @staticmethod
    def _validate_inputs(stock_quantity: int, stock_price: float) -> bool:
        """驗證輸入參數"""
        logger.info("驗證輸入參數...")
        
        if not isinstance(stock_quantity, int):
            logger.error(f"✗ 正股數量必須是整數")
            return False
        
        if stock_quantity <= 0:
            logger.error(f"✗ 正股數量必須大於0")
            return False
        
        if not isinstance(stock_price, (int, float)):
            logger.error(f"✗ 股價必須是數字")
            return False
        
        if stock_price <= 0:
            logger.error(f"✗ 股價必須大於0")
            return False
        
        logger.info("✓ 輸入參數驗證通過")
        return True


# 使用示例
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    calculator = HedgeQuantityCalculator()
    
    print("\n" + "=" * 70)
    print("模塊6: 對沖量計算")
    print("=" * 70)
    
    # 例子1: 1000股，股價$100
    print("\n【例子1】1000股，股價$100")
    print("-" * 70)
    
    result1 = calculator.calculate(
        stock_quantity=1000,
        stock_price=100.0
    )
    
    print(f"\n計算結果:")
    print(f"  正股數量: {result1.stock_quantity}股")
    print(f"  股價: ${result1.stock_price:.2f}")
    print(f"  持倉市值: ${result1.portfolio_value:.2f}")
    print(f"  對沖合約數: {result1.hedge_contracts}張")
    print(f"  覆蓋率: {result1.coverage_percentage:.2f}%")
    
    # 例子2: 5000股，股價$50
    print("\n【例子2】5000股，股價$50")
    print("-" * 70)
    
    result2 = calculator.calculate(
        stock_quantity=5000,
        stock_price=50.0
    )
    
    print(f"\n計算結果:")
    print(f"  正股數量: {result2.stock_quantity}股")
    print(f"  對沖合約數: {result2.hedge_contracts}張")
    print(f"  覆蓋率: {result2.coverage_percentage:.2f}%")
    
    print("\n" + "=" * 70)
    print("注: 對沖是用期權來保護正股的風險 (書籍理論)")
    print("=" * 70)
