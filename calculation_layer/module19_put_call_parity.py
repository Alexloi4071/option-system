# calculation_layer/module19_put_call_parity.py
"""
模塊19: Put-Call Parity 驗證器
書籍來源: 金融工程標準模型

功能:
- 驗證看漲-看跌平價關係
- 識別套利機會
- 計算理論利潤
- 提供套利策略建議

Put-Call Parity 說明:
─────────────────────────────────────
Put-Call Parity 是期權定價的基本關係，描述了 Call、Put、
股票和無風險債券之間的價格關係。

完整公式:
  C - P = S - K×e^(-r×T)
  
其中:
  C = Call 期權價格
  P = Put 期權價格
  S = 當前股價
  K = 行使價
  r = 無風險利率
  T = 到期時間（年）

套利策略:
  若 C - P > S - K×e^(-r×T) (Call 相對高估):
    → 沽出 Call, 買入 Put, 買入股票, 借入 K×e^(-r×T)
  
  若 C - P < S - K×e^(-r×T) (Put 相對高估):
    → 買入 Call, 沽出 Put, 沽出股票, 存入 K×e^(-r×T)

交易成本考慮:
  實際套利需要考慮交易成本（佣金、買賣價差等）
  只有當偏離超過交易成本時，套利才有利可圖
─────────────────────────────────────

參考文獻:
- Hull, J. C. (2018). Options, Futures, and Other Derivatives (10th ed.). Pearson.
- Stoll, H. R. (1969). The Relationship Between Put and Call Option Prices.
  The Journal of Finance, 24(5), 801-824.
"""

import logging
import math
from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime

# 導入 Black-Scholes 計算器用於理論價計算
from calculation_layer.module15_black_scholes import BlackScholesCalculator

logger = logging.getLogger(__name__)


@dataclass
class ParityResult:
    """Put-Call Parity 驗證結果"""
    call_price: float
    put_price: float
    stock_price: float
    strike_price: float
    risk_free_rate: float
    time_to_expiration: float
    theoretical_difference: float
    actual_difference: float
    deviation: float
    deviation_percentage: float
    arbitrage_opportunity: bool
    theoretical_profit: float
    strategy: str
    calculation_date: str
    dividend_yield: float = 0.0  # 股息率（年化，小數形式）
    dividend_adjusted: bool = False  # 是否進行了股息調整
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        return {
            'call_price': round(self.call_price, 4),
            'put_price': round(self.put_price, 4),
            'stock_price': round(self.stock_price, 2),
            'strike_price': round(self.strike_price, 2),
            'risk_free_rate': round(self.risk_free_rate, 6),
            'time_to_expiration': round(self.time_to_expiration, 4),
            'theoretical_difference': round(self.theoretical_difference, 4),
            'actual_difference': round(self.actual_difference, 4),
            'deviation': round(self.deviation, 4),
            'deviation_percentage': round(self.deviation_percentage, 4),
            'arbitrage_opportunity': self.arbitrage_opportunity,
            'theoretical_profit': round(self.theoretical_profit, 4),
            'strategy': self.strategy,
            'calculation_date': self.calculation_date,
            'dividend_yield': round(self.dividend_yield, 6),
            'dividend_adjusted': self.dividend_adjusted
        }


class PutCallParityValidator:
    """
    Put-Call Parity 驗證器
    
    功能:
    - 驗證看漲-看跌平價關係
    - 識別套利機會
    - 計算理論利潤
    - 提供套利策略建議
    
    使用示例:
    >>> validator = PutCallParityValidator()
    >>> result = validator.validate_parity(
    ...     call_price=10.45,
    ...     put_price=5.57,
    ...     stock_price=100.0,
    ...     strike_price=100.0,
    ...     risk_free_rate=0.05,
    ...     time_to_expiration=1.0
    ... )
    >>> print(f"套利機會: {result.arbitrage_opportunity}")
    >>> print(f"策略: {result.strategy}")
    """
    
    # 默認交易成本（0.5%）
    DEFAULT_TRANSACTION_COST = 0.005
    
    def __init__(self, transaction_cost: float = DEFAULT_TRANSACTION_COST):
        """
        初始化 Put-Call Parity 驗證器
        
        參數:
            transaction_cost: 交易成本（小數形式，默認 0.5%）
        """
        self.bs_calculator = BlackScholesCalculator()
        self.transaction_cost = transaction_cost
        
        logger.info("* Put-Call Parity 驗證器已初始化")
        logger.info(f"  交易成本閾值: {transaction_cost*100:.2f}%")
    
    def validate_parity(
        self,
        call_price: float,
        put_price: float,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        time_to_expiration: float,
        dividend_yield: float = 0.0,
        transaction_cost: Optional[float] = None,
        calculation_date: Optional[str] = None
    ) -> ParityResult:
        """
        驗證 Put-Call Parity 關係（支持股息調整）
        
        參數:
            call_price: Call 期權市場價格（美元）
            put_price: Put 期權市場價格（美元）
            stock_price: 當前股價（美元）
            strike_price: 行使價（美元）
            risk_free_rate: 無風險利率（年化，小數形式）
            time_to_expiration: 到期時間（年）
            dividend_yield: 年化股息率（小數形式，如 0.025 表示 2.5%，默認 0.0）
            transaction_cost: 交易成本（可選，默認使用初始化值）
            calculation_date: 計算日期（YYYY-MM-DD 格式）
        
        返回:
            ParityResult: 包含驗證結果和套利分析的對象
        
        公式（含股息調整）:
            理論差異: Theoretical_Diff = S×e^(-q×T) - K×e^(-r×T)
            實際差異: Actual_Diff = C - P
            偏離: Deviation = Actual_Diff - Theoretical_Diff
            
            套利條件: |Deviation| > Transaction_Cost
        
        向後兼容性:
            - dividend_yield 參數默認為 0.0
            - 當 dividend_yield = 0 時，行為與原來完全相同
            - 結果中包含 dividend_adjusted 標識
        
        股息調整說明:
            - 股息降低了股票的預期價格
            - 因此理論差異 (C - P) 應該更小
            - 對於高股息股票（如 KO, XOM），股息調整很重要
        
        示例:
            >>> validator = PutCallParityValidator()
            >>> # 無股息股票
            >>> result1 = validator.validate_parity(
            ...     call_price=10.45,
            ...     put_price=5.57,
            ...     stock_price=100.0,
            ...     strike_price=100.0,
            ...     risk_free_rate=0.05,
            ...     time_to_expiration=1.0
            ... )
            
            >>> # 高股息股票（如 KO, 股息率 3%）
            >>> result2 = validator.validate_parity(
            ...     call_price=10.45,
            ...     put_price=5.57,
            ...     stock_price=100.0,
            ...     strike_price=100.0,
            ...     risk_free_rate=0.05,
            ...     time_to_expiration=1.0,
            ...     dividend_yield=0.03
            ... )
            >>> print(f"股息調整: {result2.dividend_adjusted}")
        """
        try:
            logger.info(f"開始驗證 Put-Call Parity...")
            logger.info(f"  Call 價格: ${call_price:.4f}")
            logger.info(f"  Put 價格: ${put_price:.4f}")
            logger.info(f"  股價: ${stock_price:.2f}, 行使價: ${strike_price:.2f}")
            logger.info(f"  利率: {risk_free_rate*100:.2f}%, 時間: {time_to_expiration:.4f}年")
            
            if dividend_yield > 0:
                logger.info(f"  股息率: {dividend_yield*100:.2f}% (啟用股息調整)")
            
            # 第1步: 輸入驗證
            if not self._validate_inputs(
                call_price, put_price, stock_price, strike_price,
                risk_free_rate, time_to_expiration
            ):
                raise ValueError("輸入參數無效")
            
            # 驗證股息率
            if dividend_yield < 0 or dividend_yield > 0.2:
                logger.warning(f"⚠ 股息率超出常見範圍 [0%, 20%]: {dividend_yield*100:.2f}%")
            
            # 第2步: 獲取計算日期和交易成本
            if calculation_date is None:
                calculation_date = datetime.now().strftime('%Y-%m-%d')
            
            if transaction_cost is None:
                transaction_cost = self.transaction_cost
            
            # 第3步: 計算理論差異（含股息調整）
            # Theoretical_Diff = S×e^(-q×T) - K×e^(-r×T)
            adjusted_stock_price = stock_price * math.exp(-dividend_yield * time_to_expiration)
            discount_factor = math.exp(-risk_free_rate * time_to_expiration)
            theoretical_difference = adjusted_stock_price - strike_price * discount_factor
            
            dividend_adjusted = (dividend_yield > 0)
            
            logger.debug(f"  折現因子: {discount_factor:.6f}")
            if dividend_adjusted:
                logger.debug(f"  股息調整: S = ${stock_price:.2f} → S_adj = ${adjusted_stock_price:.2f}")
            logger.debug(f"  理論差異: ${theoretical_difference:.4f}")
            
            # 第4步: 計算實際差異
            # Actual_Diff = C - P
            actual_difference = call_price - put_price
            
            logger.debug(f"  實際差異: ${actual_difference:.4f}")
            
            # 第5步: 計算偏離
            # Deviation = Actual_Diff - Theoretical_Diff
            deviation = actual_difference - theoretical_difference
            
            # 計算偏離百分比
            # 修復 (2025-12-07): 使用相對於期權價格的百分比，而非相對於理論差異
            # 原因: 當理論差異很小時（ATM期權），原計算方式會放大百分比，造成誤解
            # 新方式: 偏離 / 期權平均價格 × 100，更直觀反映實際偏離程度
            avg_option_price = (call_price + put_price) / 2
            if avg_option_price > 0.01:
                deviation_percentage = (abs(deviation) / avg_option_price) * 100
            elif abs(theoretical_difference) > 0.01:
                # 降級: 如果期權價格太小，使用理論差異
                deviation_percentage = (abs(deviation) / abs(theoretical_difference)) * 100
            else:
                deviation_percentage = 0.0
            
            logger.info(f"  計算結果:")
            logger.info(f"    理論差異 (S×e^(-q×T) - K×e^(-r×T)): ${theoretical_difference:.4f}")
            logger.info(f"    實際差異 (C - P): ${actual_difference:.4f}")
            logger.info(f"    偏離: ${deviation:.4f} ({deviation_percentage:.2f}%)")
            
            # 第6步: 判斷套利機會
            # 套利條件: |Deviation| > Transaction_Cost
            abs_deviation = abs(deviation)
            cost_threshold = transaction_cost * stock_price  # 將百分比轉換為美元
            
            arbitrage_opportunity = abs_deviation > cost_threshold
            
            # 第7步: 計算理論利潤
            if arbitrage_opportunity:
                theoretical_profit = abs_deviation - cost_threshold
            else:
                theoretical_profit = 0.0
            
            # 第8步: 確定套利策略
            if arbitrage_opportunity:
                if deviation > 0:
                    # C - P > S×e^(-q×T) - K×e^(-r×T)
                    # Call 相對高估
                    strategy = (
                        "套利策略: 沽出 Call, 買入 Put, 買入股票, "
                        f"借入 ${strike_price * discount_factor:.2f}"
                    )
                    logger.info(f"  * 發現套利機會: Call 相對高估")
                else:
                    # C - P < S×e^(-q×T) - K×e^(-r×T)
                    # Put 相對高估
                    strategy = (
                        "套利策略: 買入 Call, 沽出 Put, 沽出股票, "
                        f"存入 ${strike_price * discount_factor:.2f}"
                    )
                    logger.info(f"  * 發現套利機會: Put 相對高估")
                
                logger.info(f"  理論利潤: ${theoretical_profit:.4f}")
            else:
                strategy = "無套利機會 - Put-Call Parity 成立"
                logger.info(f"  * Put-Call Parity 成立，無套利機會")
            
            # 第9步: 建立結果對象
            result = ParityResult(
                call_price=call_price,
                put_price=put_price,
                stock_price=stock_price,
                strike_price=strike_price,
                risk_free_rate=risk_free_rate,
                time_to_expiration=time_to_expiration,
                theoretical_difference=theoretical_difference,
                actual_difference=actual_difference,
                deviation=deviation,
                deviation_percentage=deviation_percentage,
                arbitrage_opportunity=arbitrage_opportunity,
                theoretical_profit=theoretical_profit,
                strategy=strategy,
                calculation_date=calculation_date,
                dividend_yield=dividend_yield,
                dividend_adjusted=dividend_adjusted
            )
            
            logger.info(f"* Put-Call Parity 驗證完成")
            
            return result
            
        except Exception as e:
            logger.error(f"x Put-Call Parity 驗證失敗: {e}")
            raise
    
    def validate_with_theoretical_prices(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        time_to_expiration: float,
        volatility: float,
        dividend_yield: float = 0.0,
        market_call_price: Optional[float] = None,
        market_put_price: Optional[float] = None,
        calculation_date: Optional[str] = None
    ) -> ParityResult:
        """
        使用 Black-Scholes 理論價格驗證 Parity（支持股息調整）
        
        當市場價格不完整時，使用 BS 模型計算理論價格進行驗證。
        
        參數:
            stock_price: 當前股價
            strike_price: 行使價
            risk_free_rate: 無風險利率
            time_to_expiration: 到期時間
            volatility: 波動率
            dividend_yield: 年化股息率（小數形式，默認 0.0）
            market_call_price: 市場 Call 價格（可選）
            market_put_price: 市場 Put 價格（可選）
            calculation_date: 計算日期
        
        返回:
            ParityResult: 驗證結果
        """
        try:
            logger.info(f"使用 BS 理論價格驗證 Put-Call Parity...")
            
            if dividend_yield > 0:
                logger.info(f"  股息率: {dividend_yield*100:.2f}%")
            
            # 計算理論價格（含股息調整）
            if market_call_price is None:
                call_result = self.bs_calculator.calculate_option_price(
                    stock_price=stock_price,
                    strike_price=strike_price,
                    risk_free_rate=risk_free_rate,
                    time_to_expiration=time_to_expiration,
                    volatility=volatility,
                    option_type='call',
                    dividend_yield=dividend_yield
                )
                call_price = call_result.option_price
                logger.info(f"  使用 BS 理論 Call 價格: ${call_price:.4f}")
            else:
                call_price = market_call_price
                logger.info(f"  使用市場 Call 價格: ${call_price:.4f}")
            
            if market_put_price is None:
                put_result = self.bs_calculator.calculate_option_price(
                    stock_price=stock_price,
                    strike_price=strike_price,
                    risk_free_rate=risk_free_rate,
                    time_to_expiration=time_to_expiration,
                    volatility=volatility,
                    option_type='put',
                    dividend_yield=dividend_yield
                )
                put_price = put_result.option_price
                logger.info(f"  使用 BS 理論 Put 價格: ${put_price:.4f}")
            else:
                put_price = market_put_price
                logger.info(f"  使用市場 Put 價格: ${put_price:.4f}")
            
            # 驗證 Parity（含股息調整）
            return self.validate_parity(
                call_price=call_price,
                put_price=put_price,
                stock_price=stock_price,
                strike_price=strike_price,
                risk_free_rate=risk_free_rate,
                time_to_expiration=time_to_expiration,
                dividend_yield=dividend_yield,
                calculation_date=calculation_date
            )
            
        except Exception as e:
            logger.error(f"x 理論價格驗證失敗: {e}")
            raise
    
    @staticmethod
    def _validate_inputs(
        call_price: float,
        put_price: float,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        time_to_expiration: float
    ) -> bool:
        """
        驗證輸入參數
        
        參數:
            call_price: Call 價格
            put_price: Put 價格
            stock_price: 股價
            strike_price: 行使價
            risk_free_rate: 利率
            time_to_expiration: 到期時間
        
        返回:
            bool: True 如果所有參數有效
        """
        logger.info("驗證輸入參數...")
        
        # 驗證數值類型
        if not all(isinstance(x, (int, float)) for x in [
            call_price, put_price, stock_price, strike_price,
            risk_free_rate, time_to_expiration
        ]):
            logger.error("x 所有參數必須是數字")
            return False
        
        # 驗證價格為正
        if call_price < 0 or put_price < 0:
            logger.error(f"x 期權價格不能為負: Call=${call_price}, Put=${put_price}")
            return False
        
        if stock_price <= 0 or strike_price <= 0:
            logger.error(f"x 股價和行使價必須大於0")
            return False
        
        # 驗證到期時間
        if time_to_expiration <= 0:
            logger.error(f"x 到期時間必須大於0: {time_to_expiration}")
            return False
        
        # 驗證利率範圍
        if risk_free_rate < -0.1 or risk_free_rate > 0.5:
            logger.error(f"x 利率超出合理範圍: {risk_free_rate*100:.2f}%")
            return False
        
        logger.info("* 輸入參數驗證通過")
        return True


# 使用示例和測試
if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    import logging
    logging.basicConfig(level=logging.INFO)
    
    validator = PutCallParityValidator()
    
    print("\n" + "=" * 70)
    print("模塊19: Put-Call Parity 驗證器")
    print("=" * 70)
    
    # 例子1: 驗證理論價格的 Parity（應該完美成立）
    print("\n【例子1】驗證 BS 理論價格的 Put-Call Parity")
    print("-" * 70)
    
    result1 = validator.validate_with_theoretical_prices(
        stock_price=100.0,
        strike_price=100.0,
        risk_free_rate=0.05,
        time_to_expiration=1.0,
        volatility=0.2
    )
    
    print(f"\n驗證結果:")
    print(f"  Call 價格: ${result1.call_price:.4f}")
    print(f"  Put 價格: ${result1.put_price:.4f}")
    print(f"  理論差異: ${result1.theoretical_difference:.4f}")
    print(f"  實際差異: ${result1.actual_difference:.4f}")
    print(f"  偏離: ${result1.deviation:.6f}")
    print(f"  套利機會: {result1.arbitrage_opportunity}")
    
    # 例子2: 模擬 Call 高估情況
    print("\n【例子2】模擬 Call 高估情況")
    print("-" * 70)
    
    result2 = validator.validate_parity(
        call_price=11.00,  # 高估 Call
        put_price=5.57,
        stock_price=100.0,
        strike_price=100.0,
        risk_free_rate=0.05,
        time_to_expiration=1.0
    )
    
    print(f"\n驗證結果:")
    print(f"  偏離: ${result2.deviation:.4f} ({result2.deviation_percentage:.2f}%)")
    print(f"  套利機會: {result2.arbitrage_opportunity}")
    print(f"  理論利潤: ${result2.theoretical_profit:.4f}")
    print(f"  策略: {result2.strategy}")
    
    # 例子3: 模擬 Put 高估情況
    print("\n【例子3】模擬 Put 高估情況")
    print("-" * 70)
    
    result3 = validator.validate_parity(
        call_price=10.45,
        put_price=6.50,  # 高估 Put
        stock_price=100.0,
        strike_price=100.0,
        risk_free_rate=0.05,
        time_to_expiration=1.0
    )
    
    print(f"\n驗證結果:")
    print(f"  偏離: ${result3.deviation:.4f} ({result3.deviation_percentage:.2f}%)")
    print(f"  套利機會: {result3.arbitrage_opportunity}")
    print(f"  理論利潤: ${result3.theoretical_profit:.4f}")
    print(f"  策略: {result3.strategy}")
    
    print("\n" + "=" * 70)
    print("注: Put-Call Parity 用於發現期權定價異常和套利機會")
    print("=" * 70)
