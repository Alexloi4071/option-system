# calculation_layer/module3_arbitrage_spread.py
"""
模塊3: 套戥水位計算 (Arbitrage Spread)
書籍來源: 《期權制勝2》第一課
"""

import logging
from dataclasses import dataclass
from typing import Dict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ArbitrageSpreadResult:
    """套戥水位計算結果"""
    market_option_price: float
    fair_value: float
    arbitrage_spread: float
    spread_percentage: float
    recommendation: str
    calculation_date: str
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        return {
            'market_option_price': round(self.market_option_price, 2),
            'fair_value': round(self.fair_value, 2),
            'arbitrage_spread': round(self.arbitrage_spread, 2),
            'spread_percentage': round(self.spread_percentage, 4),
            'recommendation': self.recommendation,
            'calculation_date': self.calculation_date
        }


class ArbitrageSpreadCalculator:
    """
    套戥水位計算器 (使用相對閾值)
    
    書籍來源: 《期權制勝2》第一課
    
    公式 (100%書籍):
    ────────────────────────────────
    套戥水位 = 市場期權價格 - 公允值
    
    套戥百分比 = (套戥水位 / 公允值) × 100%
    
    判斷準則 (使用相對百分比閾值):
    - 套戥百分比 > +5%: 嚴重高估，建議沽出
    - 套戥百分比 +2~+5%: 略高估，觀望或輕倉沽出
    - 套戥百分比 ±2%: 合理定價，無套戥機會
    - 套戥百分比 -2~-5%: 略低估，考慮買入
    - 套戥百分比 < -5%: 嚴重低估，建議買入
    
    理論:
    當市場期權價格偏離理論公允值時，存在套戥機會
    可以通過買入低估期權、沽出高估期權來獲利
    
    為什麼使用相對閾值?
    - $0.50對於$10期權是5% (顯著)
    - $0.50對於$200期權只是0.25% (不顯著)
    - 相對閾值確保判斷標準的一致性
    ────────────────────────────────
    """
    
    # 相對百分比閾值
    THRESHOLDS = {
        'strong_overvalued': 5.0,    # 5%以上 - 嚴重高估
        'overvalued': 2.0,           # 2-5% - 略高估
        'fair': 2.0,                 # ±2% - 合理
        'undervalued': -2.0,         # -2~-5% - 略低估
        'strong_undervalued': -5.0   # -5%以下 - 嚴重低估
    }
    
    def __init__(self):
        """初始化計算器"""
        logger.info("✓ 套戥水位計算器已初始化")
    
    def calculate(self,
                  market_option_price: float,
                  fair_value: float,
                  calculation_date: str = None) -> ArbitrageSpreadResult:
        """
        計算套戥水位
        
        參數:
            market_option_price: 市場期權價格 (美元)
            fair_value: 公允值 (美元)
            calculation_date: 計算日期
        
        返回:
            ArbitrageSpreadResult: 完整計算結果
        """
        try:
            logger.info(f"開始計算套戥水位...")
            logger.info(f"  市場期權價格: ${market_option_price:.2f}")
            logger.info(f"  公允值: ${fair_value:.2f}")
            
            # 驗證輸入
            if not self._validate_inputs(market_option_price, fair_value):
                raise ValueError("輸入參數無效")
            
            # 獲取計算日期
            if calculation_date is None:
                calculation_date = datetime.now().strftime('%Y-%m-%d')
            
            # 計算套戥水位
            arbitrage_spread = market_option_price - fair_value
            
            # 計算套戥百分比 (相對閾值)
            spread_percentage = (arbitrage_spread / fair_value) * 100 if fair_value != 0 else 0
            
            # 基於相對閾值判斷
            if spread_percentage >= self.THRESHOLDS['strong_overvalued']:
                recommendation = "嚴重高估 - 強烈套戥機會 (建議沽出)"
            elif spread_percentage >= self.THRESHOLDS['overvalued']:
                recommendation = "略高估 - 輕微套戥機會 (觀望或輕倉沽出)"
            elif spread_percentage >= -self.THRESHOLDS['fair']:
                recommendation = "合理定價 - 無套戥機會 (公平價格,建議觀望)"
            elif spread_percentage >= self.THRESHOLDS['strong_undervalued']:
                recommendation = "略低估 - 輕微套戥機會 (考慮買入)"
            else:
                recommendation = "嚴重低估 - 強烈套戥機會 (建議買入)"
            
            logger.info(f"  計算結果:")
            logger.info(f"    套戥水位: ${arbitrage_spread:.2f}")
            logger.info(f"    套戥百分比: {spread_percentage:.4f}%")
            logger.info(f"    建議: {recommendation}")
            
            result = ArbitrageSpreadResult(
                market_option_price=market_option_price,
                fair_value=fair_value,
                arbitrage_spread=arbitrage_spread,
                spread_percentage=spread_percentage,
                recommendation=recommendation,
                calculation_date=calculation_date
            )
            
            logger.info(f"✓ 套戥水位計算完成")
            return result
            
        except Exception as e:
            logger.error(f"✗ 套戥水位計算失敗: {e}")
            raise
    
    @staticmethod
    def _validate_inputs(market_price: float, fair_value: float) -> bool:
        """驗證輸入參數"""
        logger.info("驗證輸入參數...")
        
        if not isinstance(market_price, (int, float)):
            logger.error(f"✗ 市場價格必須是數字")
            return False
        
        if market_price < 0:
            logger.error(f"✗ 市場價格不能為負")
            return False
        
        if not isinstance(fair_value, (int, float)):
            logger.error(f"✗ 公允值必須是數字")
            return False
        
        if fair_value <= 0:
            logger.error(f"✗ 公允值必須大於0")
            return False
        
        logger.info("✓ 輸入參數驗證通過")
        return True


# 使用示例和測試
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    calculator = ArbitrageSpreadCalculator()
    
    print("\n" + "=" * 70)
    print("模塊3: 套戥水位計算")
    print("=" * 70)
    
    # 例子1: 期權高估
    print("\n【例子1】期權高估情況")
    print("-" * 70)
    
    result1 = calculator.calculate(
        market_option_price=3.50,
        fair_value=2.80
    )
    
    print(f"\n計算結果:")
    print(f"  市場期權價格: ${result1.market_option_price:.2f}")
    print(f"  公允值: ${result1.fair_value:.2f}")
    print(f"  套戥水位: ${result1.arbitrage_spread:.2f}")
    print(f"  套戥百分比: {result1.spread_percentage:.4f}%")
    print(f"  建議: {result1.recommendation}")
    
    # 例子2: 期權低估
    print("\n【例子2】期權低估情況")
    print("-" * 70)
    
    result2 = calculator.calculate(
        market_option_price=1.50,
        fair_value=2.80
    )
    
    print(f"\n計算結果:")
    print(f"  市場期權價格: ${result2.market_option_price:.2f}")
    print(f"  公允值: ${result2.fair_value:.2f}")
    print(f"  套戥水位: ${result2.arbitrage_spread:.2f}")
    print(f"  套戥百分比: {result2.spread_percentage:.4f}%")
    print(f"  建議: {result2.recommendation}")
    
    # 例子3: 價格合理
    print("\n【例子3】價格合理情況")
    print("-" * 70)
    
    result3 = calculator.calculate(
        market_option_price=2.80,
        fair_value=2.80
    )
    
    print(f"\n計算結果:")
    print(f"  市場期權價格: ${result3.market_option_price:.2f}")
    print(f"  公允值: ${result3.fair_value:.2f}")
    print(f"  套戥水位: ${result3.arbitrage_spread:.2f}")
    print(f"  套戥百分比: {result3.spread_percentage:.4f}%")
    print(f"  建議: {result3.recommendation}")
    
    print("\n" + "=" * 70)
    print("注: 套戥水位反映市場定價是否合理 (書籍理論)")
    print("=" * 70)
