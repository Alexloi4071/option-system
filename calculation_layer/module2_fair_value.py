# calculation_layer/module2_fair_value.py
"""
模塊2: 公允值計算 (遠期理論價)
書籍來源: 《期權制勝》第一課

⚠️ 重要說明:
    本模塊計算的是「股票的遠期理論價格」，不是「期權的理論價值」。
    
    書中所稱「公允值」實際對應的是無套利遠期價格 (Forward Price)：
        Forward Price = Spot × e^(r×t) − Dividend
    
    本模塊保持原有命名以兼容既有程式，但文檔與輸出會明確標示為遠期理論價，
    以免與期權定價模型（如 Black-Scholes）混淆。
    
    若需計算期權理論價，請使用 Module 15 (Black-Scholes 期權定價模塊)。
    本模塊主要用於 Module 3 的套利分析基準。
"""

import logging
from dataclasses import dataclass, field
from typing import Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class FairValueResult:
    """遠期理論價計算結果 (Forward Price)
    
    ⚠️ 注意: 這是股票遠期價，不是期權價！
    """
    stock_price: float
    risk_free_rate: float
    days_to_expiration: int
    expected_dividend: float
    time_factor: float
    fair_value: float
    difference: float
    calculation_date: str
    calculation_method: str = field(
        default="Forward Price = Spot × e^(r×t) − Dividend (股票遠期價，非期權價)"
    )
    
    def to_dict(self) -> Dict:
        """轉換為字典
        
        返回包含以下字段:
        - fair_value: 遠期理論價（向後兼容字段名）
        - forward_price: 遠期理論價（明確字段名）
        - note: 說明這是股票遠期價，非期權價
        - calculation_method: 計算方法說明
        """
        return {
            'stock_price': round(self.stock_price, 2),
            'risk_free_rate': round(self.risk_free_rate, 4),
            'days_to_expiration': self.days_to_expiration,
            'expected_dividend': round(self.expected_dividend, 2),
            'time_factor': round(self.time_factor, 4),
            'fair_value': round(self.fair_value, 2),
            'forward_price': round(self.fair_value, 2),
            'difference': round(self.difference, 2),
            'calculation_method': self.calculation_method,
            'note': '此為股票遠期理論價，非期權理論價。期權定價請使用 Module 15 (Black-Scholes)',
            'calculation_date': self.calculation_date
        }


class FairValueCalculator:
    """
    遠期理論價 (Forward Price) 計算器
    
    ⚠️ 重要: 本模塊計算股票遠期價，不是期權價！
    
    公式 (書籍簡化版本):
    ────────────────────────────────
    Forward Price = Spot × e^(r×t) − Dividend
    
    其中:
    - Spot = 當前股價
    - r = 無風險利率 (年化百分比)
    - t = 到期時間 (年)
    - Dividend = 預期派息總額
    
    與 Module 15 (Black-Scholes) 的區別:
    ────────────────────────────────
    - Module 2: 計算股票的遠期理論價格（用於套利分析基準）
    - Module 15: 計算期權的理論價值（Call/Put 期權定價）
    
    使用場景:
    ────────────────────────────────
    - Module 3 套利分析的基準價格
    - 驗證股票現貨與期貨的價格關係
    - 不適用於期權定價！
    
    注意:
    - 本模塊不計算期權定價，只提供書中所述的遠期理論價。
    - 「fair_value」欄位僅為向後兼容的命名，輸出將同時提供 forward_price。
    ────────────────────────────────
    """
    
    def __init__(self):
        logger.info("* 公允值計算器已初始化")
    
    def calculate(self,
                  stock_price: float,
                  risk_free_rate: float,
                  expiration_date: str = None,
                  expected_dividend: float = 0.0,
                  calculation_date: str = None,
                  days_to_expiration: int = None) -> FairValueResult:
        """
        計算股票遠期理論價 (Forward Price)
        
        ⚠️ 注意: 這不是期權定價！這是股票的遠期價格。
        
        參數:
            stock_price: 股價 (美元)
            risk_free_rate: 無風險利率 (%)
            expiration_date: 到期日 (YYYY-MM-DD) - 如果提供 days_to_expiration 則可選
            expected_dividend: 預期派息 (美元)
            calculation_date: 計算日期
            days_to_expiration: 到期天數（交易日，優先使用）
        
        返回:
            FairValueResult: 完整計算結果（包含 forward_price 和 fair_value 字段）
        
        示例:
            >>> calc = FairValueCalculator()
            >>> result = calc.calculate(
            ...     stock_price=100.0,
            ...     risk_free_rate=4.0,
            ...     days_to_expiration=30,
            ...     expected_dividend=0.0
            ... )
            >>> print(f"遠期價: ${result.forward_price:.2f}")
        """
        try:
            import math
            
            logger.info(f"開始計算公允值...")
            logger.info(f"  股價: ${stock_price:.2f}")
            logger.info(f"  無風險利率: {risk_free_rate:.2f}%")
            
            if not self._validate_inputs(stock_price, risk_free_rate, expiration_date, days_to_expiration):
                raise ValueError("輸入參數無效")
            
            if calculation_date is None:
                calculation_date = datetime.now().strftime('%Y-%m-%d')
            
            # 優先使用提供的交易日數，否則從日期計算
            if days_to_expiration is None:
                if expiration_date is None:
                    raise ValueError("必須提供 expiration_date 或 days_to_expiration")
                today = datetime.strptime(calculation_date, '%Y-%m-%d')
                exp_date = datetime.strptime(expiration_date, '%Y-%m-%d')
                days_to_expiration = (exp_date - today).days
                logger.info(f"  到期日: {expiration_date} (使用日曆日: {days_to_expiration} 天)")
            else:
                logger.info(f"  到期交易日數: {days_to_expiration} 天")
            
            # 計算時間因子 (年) - 使用交易日
            time_factor = days_to_expiration / 365.0
            
            # 轉換利率為小數
            r = risk_free_rate / 100.0
            
            # 計算公允值
            # 公式: 公允值 = 股價 × e^(r×t) - 派息
            fair_value = stock_price * math.exp(r * time_factor) - expected_dividend
            
            # 計算差異
            difference = fair_value - stock_price
            
            logger.info(f"  計算結果:")
            logger.info(f"    到期天數: {days_to_expiration}")
            logger.info(f"    時間因子: {time_factor:.4f}")
            logger.info(f"    公允值: ${fair_value:.2f}")
            logger.info(f"    差異: ${difference:.2f}")
            
            result = FairValueResult(
                stock_price=stock_price,
                risk_free_rate=risk_free_rate,
                days_to_expiration=days_to_expiration,
                expected_dividend=expected_dividend,
                time_factor=time_factor,
                fair_value=fair_value,
                difference=difference,
                calculation_date=calculation_date
            )
            
            logger.info(f"* 公允值計算完成")
            return result
            
        except Exception as e:
            logger.error(f"x 公允值計算失敗: {e}")
            raise
    
    @staticmethod
    def _validate_inputs(stock_price: float, risk_free_rate: float, 
                        expiration_date: str = None, days_to_expiration: int = None) -> bool:
        """驗證輸入參數"""
        logger.info("驗證輸入參數...")
        
        if not isinstance(stock_price, (int, float)):
            logger.error(f"x 股價必須是數字")
            return False
        
        if stock_price <= 0:
            logger.error(f"x 股價必須大於0")
            return False
        
        if not isinstance(risk_free_rate, (int, float)):
            logger.error(f"x 利率必須是數字")
            return False
        
        if risk_free_rate < 0 or risk_free_rate > 50:
            logger.error(f"x 利率範圍無效")
            return False
        
        # 必須提供 expiration_date 或 days_to_expiration 之一
        if days_to_expiration is None:
            if expiration_date is None:
                logger.error(f"x 必須提供 expiration_date 或 days_to_expiration")
                return False
            try:
                datetime.strptime(expiration_date, '%Y-%m-%d')
            except (ValueError, TypeError):
                logger.error(f"x 到期日期格式無效")
                return False
        else:
            if not isinstance(days_to_expiration, int) or days_to_expiration < 0:
                logger.error(f"x 到期天數必須是非負整數")
                return False
        
        logger.info("* 輸入參數驗證通過")
        return True


# 使用示例
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    calculator = FairValueCalculator()
    
    print("\n" + "=" * 70)
    print("模塊2: 公允值計算")
    print("=" * 70)
    
    # 例子1: 基本計算
    print("\n【例子1】基本公允值計算")
    print("-" * 70)
    
    exp_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    result1 = calculator.calculate(
        stock_price=100.0,
        risk_free_rate=4.0,
        expiration_date=exp_date,
        expected_dividend=0.0
    )
    
    print(f"\n計算結果:")
    print(f"  股價: ${result1.stock_price:.2f}")
    print(f"  利率: {result1.risk_free_rate:.2f}%")
    print(f"  到期天數: {result1.days_to_expiration}")
    print(f"  公允值: ${result1.fair_value:.2f}")
    print(f"  差異: ${result1.difference:.2f}")
    
    # 例子2: 考慮派息
    print("\n【例子2】考慮派息的公允值")
    print("-" * 70)
    
    result2 = calculator.calculate(
        stock_price=100.0,
        risk_free_rate=4.0,
        expiration_date=exp_date,
        expected_dividend=2.0
    )
    
    print(f"\n計算結果:")
    print(f"  派息: ${result2.expected_dividend:.2f}")
    print(f"  公允值: ${result2.fair_value:.2f}")
    
    print("\n" + "=" * 70)
