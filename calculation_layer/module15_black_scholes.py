# calculation_layer/module15_black_scholes.py
"""
模塊15: Black-Scholes 期權定價模型
書籍來源: 金融工程標準模型

功能:
- 計算 Call 和 Put 期權的理論價值
- 提供標準正態分佈函數
- 計算 d1 和 d2 參數
- 支持完整的 Black-Scholes 定價公式

理論基礎:
Black-Scholes 模型是期權定價的基礎，由 Fischer Black, Myron Scholes 和 Robert Merton 
在1973年提出。該模型假設股價遵循幾何布朗運動，無套利機會存在。

核心公式:
─────────────────────────────────────
Call Price: C = S×N(d1) - K×e^(-r×T)×N(d2)
Put Price:  P = K×e^(-r×T)×N(-d2) - S×N(-d1)

d1 = [ln(S/K) + (r + σ²/2)×T] / (σ×√T)
d2 = d1 - σ×√T

其中:
S = 當前股價
K = 行使價
r = 無風險利率（年化，小數形式）
T = 到期時間（年）
σ = 波動率（年化，小數形式）
N(x) = 標準正態累積分佈函數
─────────────────────────────────────

參考文獻:
- Black, F., & Scholes, M. (1973). The Pricing of Options and Corporate Liabilities.
  Journal of Political Economy, 81(3), 637-654.
- Hull, J. C. (2018). Options, Futures, and Other Derivatives (10th ed.). Pearson.
"""

import logging
import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from datetime import datetime
from scipy.stats import norm

logger = logging.getLogger(__name__)


@dataclass
class BSPricingResult:
    """Black-Scholes 定價結果"""
    stock_price: float
    strike_price: float
    risk_free_rate: float
    time_to_expiration: float
    volatility: float
    option_type: str
    d1: float
    d2: float
    option_price: float
    calculation_date: str
    iv_source: str = 'unknown'  # IV 來源標識（Requirements 3.3）
    dividend_yield: float = 0.0  # 股息率（年化，小數形式）
    dividend_adjusted: bool = False  # 是否進行了股息調整
    adjusted_stock_price: float = None  # 調整後的股價（如果使用股息調整）
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        result = {
            'stock_price': round(self.stock_price, 2),
            'strike_price': round(self.strike_price, 2),
            'risk_free_rate': round(self.risk_free_rate, 6),
            'time_to_expiration': round(self.time_to_expiration, 4),
            'volatility': round(self.volatility, 4),
            'option_type': self.option_type,
            'd1': round(self.d1, 6),
            'd2': round(self.d2, 6),
            'option_price': round(self.option_price, 4),
            'calculation_date': self.calculation_date,
            'model': 'Black-Scholes',
            'iv_source': self.iv_source,
            'dividend_yield': round(self.dividend_yield, 6),
            'dividend_adjusted': self.dividend_adjusted
        }
        
        # 只在使用股息調整時包含調整後的股價
        if self.adjusted_stock_price is not None:
            result['adjusted_stock_price'] = round(self.adjusted_stock_price, 2)
        
        return result


class BlackScholesCalculator:
    """
    Black-Scholes 期權定價計算器
    
    功能:
    - 計算 Call 和 Put 期權理論價值
    - 提供標準正態分佈函數 N(x) 和 N'(x)
    - 計算 d1 和 d2 參數
    - 完整的輸入驗證和錯誤處理
    
    使用示例:
    >>> calculator = BlackScholesCalculator()
    >>> result = calculator.calculate_option_price(
    ...     stock_price=100,
    ...     strike_price=100,
    ...     risk_free_rate=0.05,
    ...     time_to_expiration=1.0,
    ...     volatility=0.2,
    ...     option_type='call'
    ... )
    >>> print(f"Call 期權價格: ${result.option_price:.2f}")
    """
    
    def __init__(self):
        """初始化 Black-Scholes 計算器"""
        logger.info("✓ Black-Scholes 計算器已初始化")
    
    @staticmethod
    def normal_cdf(x: float) -> float:
        """
        標準正態累積分佈函數 N(x)
        
        計算標準正態分佈在 x 點的累積概率。
        使用 scipy.stats.norm.cdf 提供高精度計算。
        
        參數:
            x: 標準正態分佈的值
        
        返回:
            float: 累積概率 P(X ≤ x)，範圍 [0, 1]
        
        數學定義:
            N(x) = ∫[-∞, x] (1/√(2π)) × e^(-t²/2) dt
        
        示例:
            >>> BlackScholesCalculator.normal_cdf(0)
            0.5
            >>> BlackScholesCalculator.normal_cdf(1.96)
            0.975  # 約等於 97.5%
        """
        return norm.cdf(x)
    
    @staticmethod
    def normal_pdf(x: float) -> float:
        """
        標準正態概率密度函數 N'(x)
        
        計算標準正態分佈在 x 點的概率密度。
        用於計算 Gamma 和 Vega 等 Greeks。
        
        參數:
            x: 標準正態分佈的值
        
        返回:
            float: 概率密度值
        
        數學定義:
            N'(x) = (1/√(2π)) × e^(-x²/2)
        
        示例:
            >>> BlackScholesCalculator.normal_pdf(0)
            0.3989...  # 1/√(2π)
        """
        return norm.pdf(x)
    
    def calculate_d1_d2(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        time_to_expiration: float,
        volatility: float,
        dividend_yield: float = 0.0
    ) -> Tuple[float, float]:
        """
        計算 Black-Scholes 模型的 d1 和 d2 參數
        
        這兩個參數是 BS 模型的核心，用於計算期權價格和 Greeks。
        支持股息調整，使用調整後的股價進行計算。
        
        參數:
            stock_price: 當前股價 S
            strike_price: 行使價 K
            risk_free_rate: 無風險利率 r（年化，小數形式，如 0.05 表示 5%）
            time_to_expiration: 到期時間 T（年）
            volatility: 波動率 σ（年化，小數形式，如 0.2 表示 20%）
            dividend_yield: 年化股息率 q（小數形式，如 0.025 表示 2.5%，默認 0.0）
        
        返回:
            Tuple[float, float]: (d1, d2)
        
        公式（含股息調整）:
            S_adjusted = S × e^(-q×T)
            d1 = [ln(S_adjusted/K) + (r + σ²/2)×T] / (σ×√T)
            d2 = d1 - σ×√T
        
        注意:
            - 當 dividend_yield = 0 時，行為與原來完全相同（向後兼容）
            - 股息調整降低了有效股價，因此 Call 價格降低，Put 價格升高
        
        特殊情況處理:
            - 當 T → 0 時，使用極限值
            - 當 σ → 0 時，使用極限值
        
        異常:
            ValueError: 當參數無效時
        """
        try:
            # 處理特殊情況: 到期時間接近0
            if time_to_expiration < 1e-10:
                logger.warning("⚠ 到期時間接近0，使用極限值")
                # 當 T → 0 時，期權價值趨向於內在價值
                if stock_price > strike_price:
                    return (float('inf'), float('inf'))  # ITM Call
                else:
                    return (float('-inf'), float('-inf'))  # OTM Call
            
            # 處理特殊情況: 波動率接近0
            if volatility < 1e-10:
                logger.warning("⚠ 波動率接近0，使用極限值")
                # 當 σ → 0 時，期權價值確定
                adjusted_stock_price = stock_price * math.exp(-dividend_yield * time_to_expiration)
                if adjusted_stock_price > strike_price * math.exp(-risk_free_rate * time_to_expiration):
                    return (float('inf'), float('inf'))
                else:
                    return (float('-inf'), float('-inf'))
            
            # 股息調整: S_adjusted = S × e^(-q×T)
            adjusted_stock_price = stock_price * math.exp(-dividend_yield * time_to_expiration)
            
            if dividend_yield > 0:
                logger.debug(f"  股息調整: S = ${stock_price:.2f} → S_adj = ${adjusted_stock_price:.2f} (q = {dividend_yield*100:.2f}%)")
            
            # 標準計算
            sqrt_t = math.sqrt(time_to_expiration)
            vol_sqrt_t = volatility * sqrt_t
            
            # d1 = [ln(S_adjusted/K) + (r + σ²/2)×T] / (σ×√T)
            d1 = (math.log(adjusted_stock_price / strike_price) + 
                  (risk_free_rate + 0.5 * volatility ** 2) * time_to_expiration) / vol_sqrt_t
            
            # d2 = d1 - σ×√T
            d2 = d1 - vol_sqrt_t
            
            logger.debug(f"  d1 = {d1:.6f}, d2 = {d2:.6f}")
            
            return (d1, d2)
            
        except Exception as e:
            logger.error(f"✗ 計算 d1, d2 失敗: {e}")
            raise ValueError(f"無法計算 d1, d2: {e}")
    
    def calculate_option_price(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        time_to_expiration: float,
        volatility: float,
        option_type: str = 'call',
        dividend_yield: float = 0.0,
        calculation_date: str = None
    ) -> BSPricingResult:
        """
        計算期權的 Black-Scholes 理論價格（支持股息調整）
        
        參數:
            stock_price: 當前股價（美元）
            strike_price: 行使價（美元）
            risk_free_rate: 無風險利率（年化，小數形式，如 0.05 表示 5%）
            time_to_expiration: 到期時間（年，如 0.5 表示半年）
            volatility: 波動率（年化，小數形式，如 0.2 表示 20%）
            option_type: 期權類型 ('call' 或 'put')
            dividend_yield: 年化股息率（小數形式，如 0.025 表示 2.5%，默認 0.0）
            calculation_date: 計算日期（YYYY-MM-DD 格式）
        
        返回:
            BSPricingResult: 包含完整計算結果的對象
        
        公式（含股息調整）:
            S_adjusted = S × e^(-q×T)
            Call: C = S_adjusted×N(d1) - K×e^(-r×T)×N(d2)
            Put:  P = K×e^(-r×T)×N(-d2) - S_adjusted×N(-d1)
        
        向後兼容性:
            - dividend_yield 參數默認為 0.0
            - 當 dividend_yield = 0 時，行為與原來完全相同
            - 結果中包含 dividend_adjusted 標識
        
        股息調整說明:
            - 股息會降低股票的預期價格（因為股息支付後股價下跌）
            - 因此 Call 期權價格降低，Put 期權價格升高
            - 對於高股息股票（如 KO, XOM），股息調整很重要
        
        示例:
            >>> calc = BlackScholesCalculator()
            >>> # 無股息股票（如 TSLA）
            >>> result1 = calc.calculate_option_price(
            ...     stock_price=100,
            ...     strike_price=100,
            ...     risk_free_rate=0.05,
            ...     time_to_expiration=1.0,
            ...     volatility=0.2,
            ...     option_type='call'
            ... )
            >>> print(f"Call 價格（無股息）: ${result1.option_price:.2f}")
            
            >>> # 高股息股票（如 KO, 股息率 3%）
            >>> result2 = calc.calculate_option_price(
            ...     stock_price=100,
            ...     strike_price=100,
            ...     risk_free_rate=0.05,
            ...     time_to_expiration=1.0,
            ...     volatility=0.2,
            ...     option_type='call',
            ...     dividend_yield=0.03
            ... )
            >>> print(f"Call 價格（3% 股息）: ${result2.option_price:.2f}")
            >>> print(f"股息調整: {result2.dividend_adjusted}")
        
        異常:
            ValueError: 當輸入參數無效時
        """
        try:
            logger.info(f"開始 Black-Scholes 定價計算...")
            logger.info(f"  股價: ${stock_price:.2f}, 行使價: ${strike_price:.2f}")
            logger.info(f"  利率: {risk_free_rate*100:.2f}%, 時間: {time_to_expiration:.4f}年")
            logger.info(f"  波動率: {volatility*100:.2f}%, 類型: {option_type}")
            
            if dividend_yield > 0:
                logger.info(f"  股息率: {dividend_yield*100:.2f}% (啟用股息調整)")
            
            # 第1步: 輸入驗證
            if not self._validate_inputs(
                stock_price, strike_price, risk_free_rate, 
                time_to_expiration, volatility, option_type
            ):
                raise ValueError("輸入參數無效")
            
            # 驗證股息率
            if dividend_yield < 0 or dividend_yield > 0.2:
                logger.warning(f"⚠ 股息率超出常見範圍 [0%, 20%]: {dividend_yield*100:.2f}%")
            
            # 第2步: 獲取計算日期
            if calculation_date is None:
                calculation_date = datetime.now().strftime('%Y-%m-%d')
            
            # 第3步: 計算調整後的股價（如果有股息）
            adjusted_stock_price = stock_price * math.exp(-dividend_yield * time_to_expiration)
            dividend_adjusted = (dividend_yield > 0)
            
            # 第4步: 計算 d1 和 d2（使用調整後的股價）
            d1, d2 = self.calculate_d1_d2(
                stock_price, strike_price, risk_free_rate,
                time_to_expiration, volatility, dividend_yield
            )
            
            # 第5步: 計算折現因子
            discount_factor = math.exp(-risk_free_rate * time_to_expiration)
            
            # 第6步: 計算期權價格（使用調整後的股價）
            option_type_lower = option_type.lower()
            
            if option_type_lower == 'call':
                # Call: C = S_adjusted×N(d1) - K×e^(-r×T)×N(d2)
                option_price = (
                    adjusted_stock_price * self.normal_cdf(d1) - 
                    strike_price * discount_factor * self.normal_cdf(d2)
                )
            elif option_type_lower == 'put':
                # Put: P = K×e^(-r×T)×N(-d2) - S_adjusted×N(-d1)
                option_price = (
                    strike_price * discount_factor * self.normal_cdf(-d2) - 
                    adjusted_stock_price * self.normal_cdf(-d1)
                )
            else:
                raise ValueError(f"無效的期權類型: {option_type}")
            
            logger.info(f"  計算結果:")
            logger.info(f"    d1 = {d1:.6f}, d2 = {d2:.6f}")
            if dividend_adjusted:
                logger.info(f"    調整後股價 = ${adjusted_stock_price:.2f}")
            logger.info(f"    期權價格 = ${option_price:.4f}")
            
            # 第7步: 建立結果對象
            result = BSPricingResult(
                stock_price=stock_price,
                strike_price=strike_price,
                risk_free_rate=risk_free_rate,
                time_to_expiration=time_to_expiration,
                volatility=volatility,
                option_type=option_type_lower,
                d1=d1,
                d2=d2,
                option_price=option_price,
                calculation_date=calculation_date,
                dividend_yield=dividend_yield,
                dividend_adjusted=dividend_adjusted,
                adjusted_stock_price=adjusted_stock_price if dividend_adjusted else None
            )
            
            logger.info(f"✓ Black-Scholes 定價計算完成")
            
            return result
            
        except Exception as e:
            logger.error(f"✗ Black-Scholes 定價計算失敗: {e}")
            raise
    
    def calculate_option_price_with_atm_iv(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        time_to_expiration: float,
        market_iv: float,
        atm_iv: float = None,
        option_type: str = 'call',
        dividend_yield: float = 0.0,
        calculation_date: str = None
    ) -> BSPricingResult:
        """
        計算期權理論價格，優先使用 ATM IV，支持股息調整
        
        此方法擴展了標準 Black-Scholes 定價，支持優先使用 ATM IV（來自 Module 17）
        進行計算，並支持股息調整，以獲得更接近市場實際定價的理論價格。
        
        參數:
            stock_price: 當前股價（美元）
            strike_price: 行使價（美元）
            risk_free_rate: 無風險利率（年化，小數形式，如 0.05 表示 5%）
            time_to_expiration: 到期時間（年，如 0.5 表示半年）
            market_iv: 整體市場 IV（回退選項，小數形式）
            atm_iv: ATM 隱含波動率（來自 Module 17，可選，小數形式）
            option_type: 期權類型 ('call' 或 'put')
            dividend_yield: 年化股息率（小數形式，如 0.025 表示 2.5%，默認 0.0）
            calculation_date: 計算日期（YYYY-MM-DD 格式）
        
        返回:
            BSPricingResult: 包含完整計算結果的對象，包括 iv_source 和 dividend_adjusted 標識
        
        IV 選擇邏輯:
            1. 如果 atm_iv 有效（非 None 且 > 0），使用 ATM IV
            2. 否則回退使用 market_iv
            3. 結果中的 iv_source 字段標識使用的 IV 來源
        
        向後兼容性:
            - atm_iv 和 dividend_yield 參數可選（默認 None 和 0.0），確保現有代碼無需修改
            - 如果不提供 atm_iv，自動回退到 market_iv
            - 如果不提供 dividend_yield，行為與原來相同
        
        示例:
            >>> calc = BlackScholesCalculator()
            >>> # 使用 ATM IV 和股息調整
            >>> result = calc.calculate_option_price_with_atm_iv(
            ...     stock_price=200,
            ...     strike_price=200,
            ...     risk_free_rate=0.05,
            ...     time_to_expiration=0.077,
            ...     market_iv=0.30,
            ...     atm_iv=0.25,
            ...     option_type='call',
            ...     dividend_yield=0.03
            ... )
            >>> print(f"期權價格: ${result.option_price:.2f}")
            >>> print(f"IV 來源: {result.iv_source}")
            >>> print(f"股息調整: {result.dividend_adjusted}")
        
        Requirements: 3.1, 3.2, 3.3
        """
        try:
            logger.info(f"開始 Black-Scholes 定價計算（支持 ATM IV 和股息調整）...")
            logger.info(f"  股價: ${stock_price:.2f}, 行使價: ${strike_price:.2f}")
            logger.info(f"  利率: {risk_free_rate*100:.2f}%, 時間: {time_to_expiration:.4f}年")
            logger.info(f"  Market IV: {market_iv*100:.2f}%")
            
            if atm_iv is not None:
                logger.info(f"  ATM IV: {atm_iv*100:.2f}%")
            else:
                logger.info(f"  ATM IV: 未提供")
            
            if dividend_yield > 0:
                logger.info(f"  股息率: {dividend_yield*100:.2f}%")
            
            # 選擇 IV 來源（Requirements 3.1, 3.2）
            if atm_iv is not None and atm_iv > 0:
                volatility = atm_iv
                iv_source = 'ATM IV (Module 17)'
                logger.info(f"  → 使用 ATM IV: {volatility*100:.2f}%")
            else:
                volatility = market_iv
                iv_source = 'Market IV (fallback)'
                logger.info(f"  → 回退使用 Market IV: {volatility*100:.2f}%")
            
            # 調用標準 calculate_option_price 方法（含股息調整）
            result = self.calculate_option_price(
                stock_price=stock_price,
                strike_price=strike_price,
                risk_free_rate=risk_free_rate,
                time_to_expiration=time_to_expiration,
                volatility=volatility,
                option_type=option_type,
                dividend_yield=dividend_yield,
                calculation_date=calculation_date
            )
            
            # 設置 IV 來源標識（Requirements 3.3）
            result.iv_source = iv_source
            
            logger.info(f"  IV 來源: {iv_source}")
            logger.info(f"✓ Black-Scholes 定價計算完成（ATM IV 和股息調整支持）")
            
            return result
            
        except Exception as e:
            logger.error(f"✗ Black-Scholes 定價計算失敗（ATM IV 和股息調整支持）: {e}")
            raise
    
    @staticmethod
    def _validate_inputs(
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        time_to_expiration: float,
        volatility: float,
        option_type: str
    ) -> bool:
        """
        驗證輸入參數的有效性
        
        參數:
            stock_price: 股價
            strike_price: 行使價
            risk_free_rate: 利率
            time_to_expiration: 到期時間
            volatility: 波動率
            option_type: 期權類型
        
        返回:
            bool: True 如果所有參數有效
        
        驗證規則:
            - 股價和行使價必須 > 0
            - 利率範圍: -0.1 到 0.5 (-10% 到 50%)
            - 到期時間必須 ≥ 0
            - 波動率範圍: 0 到 5 (0% 到 500%)
            - 期權類型必須是 'call' 或 'put'
        """
        logger.info("驗證輸入參數...")
        
        # 驗證數值類型
        if not all(isinstance(x, (int, float)) for x in [
            stock_price, strike_price, risk_free_rate, 
            time_to_expiration, volatility
        ]):
            logger.error("✗ 所有數值參數必須是數字")
            return False
        
        # 驗證股價和行使價
        if stock_price <= 0:
            logger.error(f"✗ 股價必須大於0: {stock_price}")
            return False
        
        if strike_price <= 0:
            logger.error(f"✗ 行使價必須大於0: {strike_price}")
            return False
        
        # 驗證利率範圍
        if risk_free_rate < -0.1 or risk_free_rate > 0.5:
            logger.error(f"✗ 利率超出合理範圍 [-10%, 50%]: {risk_free_rate*100:.2f}%")
            return False
        
        # 驗證到期時間
        if time_to_expiration < 0:
            logger.error(f"✗ 到期時間不能為負: {time_to_expiration}")
            return False
        
        if time_to_expiration > 10:
            logger.warning(f"⚠ 到期時間超過10年: {time_to_expiration:.2f}年")
        
        # 驗證波動率
        if volatility < 0:
            logger.error(f"✗ 波動率不能為負: {volatility}")
            return False
        
        if volatility > 5:
            logger.error(f"✗ 波動率超出合理範圍 [0%, 500%]: {volatility*100:.2f}%")
            return False
        
        if volatility > 2:
            logger.warning(f"⚠ 波動率異常高: {volatility*100:.2f}%")
        
        # 驗證期權類型
        if option_type.lower() not in ['call', 'put']:
            logger.error(f"✗ 無效的期權類型: {option_type}")
            return False
        
        logger.info("✓ 輸入參數驗證通過")
        return True


# 使用示例和測試
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    calculator = BlackScholesCalculator()
    
    print("\n" + "=" * 70)
    print("模塊15: Black-Scholes 期權定價模型")
    print("=" * 70)
    
    # 例子1: ATM Call 期權
    print("\n【例子1】ATM Call 期權")
    print("-" * 70)
    
    result1 = calculator.calculate_option_price(
        stock_price=100.0,
        strike_price=100.0,
        risk_free_rate=0.05,
        time_to_expiration=1.0,
        volatility=0.2,
        option_type='call'
    )
    
    print(f"\n計算結果:")
    print(f"  股價: ${result1.stock_price:.2f}")
    print(f"  行使價: ${result1.strike_price:.2f}")
    print(f"  利率: {result1.risk_free_rate*100:.2f}%")
    print(f"  到期時間: {result1.time_to_expiration:.2f}年")
    print(f"  波動率: {result1.volatility*100:.2f}%")
    print(f"  d1: {result1.d1:.6f}")
    print(f"  d2: {result1.d2:.6f}")
    print(f"  Call 期權價格: ${result1.option_price:.4f}")
    
    # 例子2: ATM Put 期權
    print("\n【例子2】ATM Put 期權")
    print("-" * 70)
    
    result2 = calculator.calculate_option_price(
        stock_price=100.0,
        strike_price=100.0,
        risk_free_rate=0.05,
        time_to_expiration=1.0,
        volatility=0.2,
        option_type='put'
    )
    
    print(f"\n計算結果:")
    print(f"  Put 期權價格: ${result2.option_price:.4f}")
    
    # 例子3: 驗證 Put-Call Parity
    print("\n【例子3】驗證 Put-Call Parity")
    print("-" * 70)
    
    # Put-Call Parity: C - P = S - K×e^(-r×T)
    parity_left = result1.option_price - result2.option_price
    parity_right = result1.stock_price - result1.strike_price * math.exp(
        -result1.risk_free_rate * result1.time_to_expiration
    )
    
    print(f"\nPut-Call Parity 驗證:")
    print(f"  C - P = ${parity_left:.4f}")
    print(f"  S - K×e^(-r×T) = ${parity_right:.4f}")
    print(f"  差異: ${abs(parity_left - parity_right):.6f}")
    
    if abs(parity_left - parity_right) < 0.01:
        print(f"  * Put-Call Parity 驗證通過")
    else:
        print(f"  x Put-Call Parity 驗證失敗")
    
    # 例子4: ITM Call 期權
    print("\n【例子4】ITM Call 期權 (股價 > 行使價)")
    print("-" * 70)
    
    result4 = calculator.calculate_option_price(
        stock_price=110.0,
        strike_price=100.0,
        risk_free_rate=0.05,
        time_to_expiration=0.5,
        volatility=0.25,
        option_type='call'
    )
    
    print(f"\n計算結果:")
    print(f"  股價: ${result4.stock_price:.2f}")
    print(f"  行使價: ${result4.strike_price:.2f}")
    print(f"  內在價值: ${max(result4.stock_price - result4.strike_price, 0):.2f}")
    print(f"  Call 期權價格: ${result4.option_price:.4f}")
    print(f"  時間價值: ${result4.option_price - max(result4.stock_price - result4.strike_price, 0):.4f}")
    
    # 例子5: OTM Put 期權
    print("\n【例子5】OTM Put 期權 (股價 > 行使價)")
    print("-" * 70)
    
    result5 = calculator.calculate_option_price(
        stock_price=110.0,
        strike_price=100.0,
        risk_free_rate=0.05,
        time_to_expiration=0.5,
        volatility=0.25,
        option_type='put'
    )
    
    print(f"\n計算結果:")
    print(f"  股價: ${result5.stock_price:.2f}")
    print(f"  行使價: ${result5.strike_price:.2f}")
    print(f"  內在價值: ${max(result5.strike_price - result5.stock_price, 0):.2f}")
    print(f"  Put 期權價格: ${result5.option_price:.4f}")
    
    print("\n" + "=" * 70)
    print("注: Black-Scholes 模型假設無套利、連續交易、無交易成本")
    print("=" * 70)
