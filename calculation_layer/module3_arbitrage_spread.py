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
        logger.info("* 套戥水位計算器已初始化")
    
    def calculate(self,
                  market_option_price: float,
                  fair_value: float,
                  bid_price: float = None,
                  ask_price: float = None,
                  calculation_date: str = None) -> ArbitrageSpreadResult:
        """
        計算套戥水位
        
        參數:
            market_option_price: 市場期權價格 (美元)
            fair_value: 公允值 (美元)
            bid_price: 買入價 (可選)
            ask_price: 賣出價 (可選)
            calculation_date: 計算日期
        
        返回:
            ArbitrageSpreadResult: 完整計算結果
        """
        try:
            logger.info(f"開始計算套戥水位...")
            logger.info(f"  市場期權價格: ${market_option_price:.2f}")
            logger.info(f"  公允值: ${fair_value:.2f}")
            if bid_price is not None and ask_price is not None:
                logger.info(f"  Bid/Ask: ${bid_price:.2f} / ${ask_price:.2f}")
            
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
            recommendation = ""
            
            # 如果有 Bid/Ask 數據，進行更精確的判斷
            if bid_price is not None and ask_price is not None and bid_price > 0 and ask_price > 0:
                # 判斷是否真的有套利空間 (考慮買賣價差)
                if fair_value < bid_price:
                    # 理論價 < Bid，說明市場價(Bid)過高，可以 Sell at Bid
                    real_profit_pct = ((bid_price - fair_value) / fair_value) * 100
                    if real_profit_pct > self.THRESHOLDS['overvalued']:
                        recommendation = f"高估 (Bid > 理論價) - 可直接沽出獲利 (潛在利潤 {real_profit_pct:.1f}%)"
                    else:
                        recommendation = "略高估 - 但利潤空間有限 (考慮交易成本)"
                elif fair_value > ask_price:
                    # 理論價 > Ask，說明市場價(Ask)過低，可以 Buy at Ask
                    real_profit_pct = ((fair_value - ask_price) / ask_price) * 100
                    if real_profit_pct > abs(self.THRESHOLDS['undervalued']):
                        recommendation = f"低估 (Ask < 理論價) - 可直接買入獲利 (潛在利潤 {real_profit_pct:.1f}%)"
                    else:
                        recommendation = "略低估 - 但利潤空間有限 (考慮交易成本)"
                else:
                    # 理論價在 Bid/Ask 之間，無套利機會
                    recommendation = "合理定價 - 理論價在買賣價差內 (無套利空間)"
            
            # 如果沒有 Bid/Ask 或上面的判斷未觸發 (fallback 到中間價判斷)
            if not recommendation:
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
            
            logger.info(f"* 套戥水位計算完成")
            return result
            
        except Exception as e:
            logger.error(f"x 套戥水位計算失敗: {e}")
            raise
    
    def calculate_with_momentum(
        self,
        market_option_price: float,
        fair_value: float,
        momentum_score: float,
        ticker: str = "",
        bid_price: float = None,
        ask_price: float = None,
        calculation_date: str = None
    ) -> ArbitrageSpreadResult:
        """
        計算套戥水位（整合動量過濾器）
        
        這是增強版的calculate方法，會考慮動量因素來調整建議。
        
        參數:
            market_option_price: 市場期權價格
            fair_value: 公允值（期權理論價）
            momentum_score: 動量得分（0-1，來自Module 21）
            ticker: 股票代碼（用於日誌）
            bid_price: 買入價（可選）
            ask_price: 賣出價（可選）
            calculation_date: 計算日期
        
        返回:
            ArbitrageSpreadResult: 包含動量調整後的建議
        
        邏輯:
            1. 先計算基本的套戥水位
            2. 如果期權被高估（建議Short）：
               - 動量強（>0.7）：改為"觀望"（避免逆勢虧損）
               - 動量中（0.4-0.7）：改為"謹慎Short"
               - 動量弱（<0.4）：保持"Short"建議
            3. 如果期權被低估（建議Long）：
               - 動量強：加強"Long"建議
               - 動量弱：保持"Long"建議
        """
        try:
            logger.info(f"開始計算套戥水位（含動量過濾）...")
            if ticker:
                logger.info(f"  股票: {ticker}")
            logger.info(f"  動量得分: {momentum_score:.4f}")
            
            # 第1步：計算基本套戥水位
            basic_result = self.calculate(
                market_option_price=market_option_price,
                fair_value=fair_value,
                bid_price=bid_price,
                ask_price=ask_price,
                calculation_date=calculation_date
            )
            
            # 第2步：根據動量調整建議
            spread_pct = basic_result.spread_percentage
            original_recommendation = basic_result.recommendation
            adjusted_recommendation = original_recommendation
            momentum_note = ""
            
            # 情況1：期權被高估（spread_pct > 2%）
            if spread_pct >= self.THRESHOLDS['overvalued']:
                if momentum_score >= 0.7:
                    # 強動量：不要逆勢做空
                    adjusted_recommendation = f"⚠️ 觀望 - 雖然高估{spread_pct:.1f}%，但動量強勁（{momentum_score:.2f}），不建議逆勢做空"
                    momentum_note = "強動量警告：避免在上漲趨勢中做空（參考NVDA 2023案例）"
                    logger.warning(f"! 動量過濾: 高估但動量強，建議觀望")
                
                elif momentum_score >= 0.4:
                    # 中等動量：謹慎做空
                    adjusted_recommendation = f"⚠️ 謹慎Short - 高估{spread_pct:.1f}%，但動量中等（{momentum_score:.2f}），建議輕倉或觀望"
                    momentum_note = "中等動量：建議等待動量轉弱或使用小倉位"
                    logger.info(f"  動量過濾: 高估+中等動量，謹慎操作")
                
                else:
                    # 弱動量：可以做空
                    adjusted_recommendation = f"✓ Short - 高估{spread_pct:.1f}%且動量轉弱（{momentum_score:.2f}），適合做空"
                    momentum_note = "弱動量確認：估值高+動量弱，做空時機成熟"
                    logger.info(f"  動量過濾: 高估+弱動量，確認Short")
            
            # 情況2：期權被低估（spread_pct < -2%）
            elif spread_pct <= self.THRESHOLDS['undervalued']:
                if momentum_score >= 0.7:
                    # 強動量+低估：強烈買入信號
                    adjusted_recommendation = f"✓✓ 強烈Long - 低估{abs(spread_pct):.1f}%且動量強勁（{momentum_score:.2f}），雙重買入信號"
                    momentum_note = "強動量+低估：最佳買入機會"
                    logger.info(f"  動量過濾: 低估+強動量，強烈Long")
                
                else:
                    # 弱動量+低估：普通買入信號
                    adjusted_recommendation = f"✓ Long - 低估{abs(spread_pct):.1f}%，動量{momentum_score:.2f}"
                    momentum_note = "低估確認：適合買入"
                    logger.info(f"  動量過濾: 低估，確認Long")
            
            # 情況3：合理定價（-2% ~ +2%）
            else:
                momentum_note = f"估值合理，動量{momentum_score:.2f}"
            
            # 第3步：更新結果
            result = ArbitrageSpreadResult(
                market_option_price=basic_result.market_option_price,
                fair_value=basic_result.fair_value,
                arbitrage_spread=basic_result.arbitrage_spread,
                spread_percentage=basic_result.spread_percentage,
                recommendation=adjusted_recommendation,
                calculation_date=basic_result.calculation_date
            )
            
            # 添加額外信息到結果字典
            result_dict = result.to_dict()
            result_dict['momentum_score'] = round(momentum_score, 4)
            result_dict['momentum_note'] = momentum_note
            result_dict['original_recommendation'] = original_recommendation
            result_dict['momentum_adjusted'] = (adjusted_recommendation != original_recommendation)
            
            logger.info(f"  最終建議: {adjusted_recommendation}")
            logger.info(f"* 套戥水位計算完成（含動量過濾）")
            
            return result
            
        except Exception as e:
            logger.error(f"x 套戥水位計算失敗（含動量）: {e}")
            # 降級到基本計算
            return self.calculate(
                market_option_price=market_option_price,
                fair_value=fair_value,
                bid_price=bid_price,
                ask_price=ask_price,
                calculation_date=calculation_date
            )
    
    @staticmethod
    def _validate_inputs(market_price: float, fair_value: float) -> bool:
        """驗證輸入參數"""
        logger.info("驗證輸入參數...")
        
        if not isinstance(market_price, (int, float)):
            logger.error(f"x 市場價格必須是數字")
            return False
        
        if market_price < 0:
            logger.error(f"x 市場價格不能為負")
            return False
        
        if not isinstance(fair_value, (int, float)):
            logger.error(f"x 公允值必須是數字")
            return False
        
        if fair_value <= 0:
            logger.error(f"x 公允值必須大於0")
            return False
        
        logger.info("* 輸入參數驗證通過")
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
