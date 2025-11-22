# calculation_layer/module4_pe_valuation.py
"""
模塊4: 市盈率法估算股價 (PE Valuation)
書籍來源: 《期權制勝》第十課
"""

import logging
from dataclasses import dataclass
from typing import Dict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PEValuationResult:
    """PE估值計算結果"""
    eps: float
    pe_multiple: float
    estimated_price: float
    current_price: float
    difference: float
    difference_percentage: float
    valuation: str
    calculation_date: str
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        return {
            'eps': round(self.eps, 2),
            'pe_multiple': round(self.pe_multiple, 2),
            'estimated_price': round(self.estimated_price, 2),
            'current_price': round(self.current_price, 2),
            'difference': round(self.difference, 2),
            'difference_percentage': round(self.difference_percentage, 2),
            'valuation': self.valuation,
            'calculation_date': self.calculation_date
        }


class PEValuationCalculator:
    """
    市盈率法估算股價計算器
    
    書籍來源: 《期權制勝》第十課
    
    公式 (100%書籍):
    ────────────────────────────────
    合理股價 = EPS × PE倍數
    
    PE倍數參考 (來自書籍):
    - 熊市: 8.5倍
    - 正常市場: 15倍
    - 牛市: 25倍
    
    估值判斷:
    - 當前股價 > 合理股價: 高估
    - 當前股價 ≈ 合理股價: 合理
    - 當前股價 < 合理股價: 低估
    
    理論:
    PE倍數反映市場對公司未來盈利的預期
    不同市場環境下PE倍數有差異
    ────────────────────────────────
    """
    
    def __init__(self):
        """初始化計算器"""
        logger.info("* PE估值計算器已初始化")
    
    def calculate(self,
                  eps: float,
                  pe_multiple: float,
                  current_price: float,
                  calculation_date: str = None) -> PEValuationResult:
        """
        計算PE估值
        
        參數:
            eps: 每股收益 (美元)
            pe_multiple: PE倍數 (倍)
            current_price: 當前股價 (美元)
            calculation_date: 計算日期
        
        返回:
            PEValuationResult: 完整計算結果
        """
        try:
            logger.info(f"開始計算PE估值...")
            logger.info(f"  EPS: ${eps:.2f}")
            logger.info(f"  PE倍數: {pe_multiple:.2f}倍")
            logger.info(f"  當前股價: ${current_price:.2f}")
            
            # 驗證輸入
            if not self._validate_inputs(eps, pe_multiple, current_price):
                raise ValueError("輸入參數無效")
            
            if calculation_date is None:
                calculation_date = datetime.now().strftime('%Y-%m-%d')
            
            # 計算合理股價
            # 公式: 合理股價 = EPS × PE倍數
            estimated_price = eps * pe_multiple
            
            # 計算差異
            difference = estimated_price - current_price
            difference_percentage = (difference / current_price) * 100 if current_price != 0 else 0
            
            # 確定估值評級
            if difference_percentage > 10:
                valuation = "低估 (>10%)"
            elif difference_percentage > 5:
                valuation = "略低估 (5-10%)"
            elif difference_percentage > -5:
                valuation = "合理 (±5%)"
            elif difference_percentage > -10:
                valuation = "略高估 (-10至-5%)"
            else:
                valuation = "高估 (<-10%)"
            
            logger.info(f"  計算結果:")
            logger.info(f"    合理股價: ${estimated_price:.2f}")
            logger.info(f"    差異: ${difference:.2f} ({difference_percentage:.2f}%)")
            logger.info(f"    估值評級: {valuation}")
            
            result = PEValuationResult(
                eps=eps,
                pe_multiple=pe_multiple,
                estimated_price=estimated_price,
                current_price=current_price,
                difference=difference,
                difference_percentage=difference_percentage,
                valuation=valuation,
                calculation_date=calculation_date
            )
            
            logger.info(f"* PE估值計算完成")
            return result
            
        except Exception as e:
            logger.error(f"x PE估值計算失敗: {e}")
            raise
    
    @staticmethod
    def _validate_inputs(eps: float, pe_multiple: float, current_price: float) -> bool:
        """驗證輸入參數"""
        logger.info("驗證輸入參數...")
        
        if not isinstance(eps, (int, float)):
            logger.error(f"x EPS必須是數字")
            return False
        
        if eps <= 0:
            logger.error(f"x EPS必須大於0")
            return False
        
        if not isinstance(pe_multiple, (int, float)):
            logger.error(f"x PE倍數必須是數字")
            return False
        
        if pe_multiple <= 0:
            logger.error(f"x PE倍數必須大於0")
            return False
        
        if not isinstance(current_price, (int, float)):
            logger.error(f"x 當前股價必須是數字")
            return False
        
        if current_price <= 0:
            logger.error(f"x 當前股價必須大於0")
            return False
        
        logger.info("* 輸入參數驗證通過")
        return True


# 使用示例和測試
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    calculator = PEValuationCalculator()
    
    print("\n" + "=" * 70)
    print("模塊4: 市盈率法估算股價")
    print("=" * 70)
    
    # 例子1: 牛市估值
    print("\n【例子1】牛市估值 (PE=25倍)")
    print("-" * 70)
    
    result1 = calculator.calculate(
        eps=6.05,
        pe_multiple=25.0,
        current_price=150.0
    )
    
    print(f"\n計算結果:")
    print(f"  EPS: ${result1.eps:.2f}")
    print(f"  PE倍數: {result1.pe_multiple:.2f}倍")
    print(f"  合理股價: ${result1.estimated_price:.2f}")
    print(f"  當前股價: ${result1.current_price:.2f}")
    print(f"  差異: ${result1.difference:.2f} ({result1.difference_percentage:.2f}%)")
    print(f"  估值: {result1.valuation}")
    
    # 例子2: 熊市估值
    print("\n【例子2】熊市估值 (PE=8.5倍)")
    print("-" * 70)
    
    result2 = calculator.calculate(
        eps=6.05,
        pe_multiple=8.5,
        current_price=60.0
    )
    
    print(f"\n計算結果:")
    print(f"  EPS: ${result2.eps:.2f}")
    print(f"  合理股價: ${result2.estimated_price:.2f}")
    print(f"  當前股價: ${result2.current_price:.2f}")
    print(f"  估值: {result2.valuation}")
    
    # 例子3: 正常市場估值
    print("\n【例子3】正常市場 (PE=15倍)")
    print("-" * 70)
    
    result3 = calculator.calculate(
        eps=6.05,
        pe_multiple=15.0,
        current_price=90.0
    )
    
    print(f"\n計算結果:")
    print(f"  合理股價: ${result3.estimated_price:.2f}")
    print(f"  當前股價: ${result3.current_price:.2f}")
    print(f"  估值: {result3.valuation}")
    
    print("\n" + "=" * 70)
