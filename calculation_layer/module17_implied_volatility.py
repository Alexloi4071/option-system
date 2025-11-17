# calculation_layer/module17_implied_volatility.py
"""
模塊17: 隱含波動率計算器 (Implied Volatility Calculator)
書籍來源: 金融工程標準模型

功能:
- 從市場期權價格反推隱含波動率 (IV)
- 使用 Newton-Raphson 迭代法
- 提供收斂性驗證
- 異常值檢測
- 作為 API 數據驗證工具

隱含波動率 (IV) 說明:
─────────────────────────────────────
隱含波動率是使 Black-Scholes 期權定價公式計算出的理論價格
等於市場觀察到的期權價格的波動率值。

數學定義:
  Market_Price = BS_Price(S, K, r, T, IV)
  
求解 IV 使得上式成立。

Newton-Raphson 迭代法:
  IV(n+1) = IV(n) - [BS_Price(IV(n)) - Market_Price] / Vega(IV(n))
  
其中 Vega = ∂BS_Price/∂σ

收斂條件:
  |BS_Price(IV(n)) - Market_Price| < tolerance
─────────────────────────────────────

參考文獻:
- Hull, J. C. (2018). Options, Futures, and Other Derivatives (10th ed.). Pearson.
- Brenner, M., & Subrahmanyam, M. G. (1988). A Simple Formula to Compute 
  the Implied Standard Deviation. Financial Analysts Journal, 44(5), 80-83.
"""

import logging
import math
from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime

# 導入依賴模塊
from calculation_layer.module15_black_scholes import BlackScholesCalculator
from calculation_layer.module16_greeks import GreeksCalculator

logger = logging.getLogger(__name__)


@dataclass
class IVResult:
    """隱含波動率計算結果"""
    market_price: float
    implied_volatility: float
    iterations: int
    converged: bool
    bs_price: float
    price_difference: float
    initial_guess: float
    calculation_date: str
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        return {
            'market_price': round(self.market_price, 4),
            'implied_volatility': round(self.implied_volatility, 6),
            'implied_volatility_percent': round(self.implied_volatility * 100, 2),
            'iterations': self.iterations,
            'converged': self.converged,
            'bs_price': round(self.bs_price, 4),
            'price_difference': round(self.price_difference, 6),
            'initial_guess': round(self.initial_guess, 4),
            'calculation_date': self.calculation_date
        }


class ImpliedVolatilityCalculator:
    """
    隱含波動率計算器
    
    功能:
    - 從市場期權價格反推 IV
    - 使用 Newton-Raphson 迭代法
    - 自動收斂性檢查
    - 異常值檢測
    
    使用示例:
    >>> calculator = ImpliedVolatilityCalculator()
    >>> result = calculator.calculate_implied_volatility(
    ...     market_price=10.45,
    ...     stock_price=100,
    ...     strike_price=100,
    ...     risk_free_rate=0.05,
    ...     time_to_expiration=1.0,
    ...     option_type='call'
    ... )
    >>> print(f"隱含波動率: {result.implied_volatility*100:.2f}%")
    """
    
    def __init__(
        self,
        max_iterations: int = 100,
        tolerance: float = 0.0001,
        min_volatility: float = 0.001,
        max_volatility: float = 5.0
    ):
        """
        初始化隱含波動率計算器
        
        參數:
            max_iterations: 最大迭代次數（默認 100）
            tolerance: 收斂容差（默認 0.0001）
            min_volatility: 最小波動率（默認 0.1%）
            max_volatility: 最大波動率（默認 500%）
        """
        self.bs_calculator = BlackScholesCalculator()
        self.greeks_calculator = GreeksCalculator()
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        self.min_volatility = min_volatility
        self.max_volatility = max_volatility
        
        logger.info("✓ 隱含波動率計算器已初始化")
        logger.info(f"  最大迭代次數: {max_iterations}")
        logger.info(f"  收斂容差: {tolerance}")
        logger.info(f"  波動率範圍: {min_volatility*100:.1f}% - {max_volatility*100:.1f}%")
    
    def _get_initial_guess(
        self,
        market_price: float,
        stock_price: float,
        strike_price: float,
        time_to_expiration: float
    ) -> float:
        """
        獲取初始猜測值
        
        使用 Brenner-Subrahmanyam 近似公式提供更好的初始猜測。
        
        參數:
            market_price: 市場期權價格
            stock_price: 股價
            strike_price: 行使價
            time_to_expiration: 到期時間（年）
        
        返回:
            float: 初始波動率猜測值
        
        公式 (Brenner-Subrahmanyam):
            σ ≈ √(2π/T) × (C/S)
        
        其中 C 是期權價格，S 是股價，T 是到期時間
        """
        try:
            # 使用 Brenner-Subrahmanyam 近似
            if time_to_expiration > 0 and stock_price > 0:
                initial_guess = math.sqrt(2 * math.pi / time_to_expiration) * (market_price / stock_price)
                
                # 確保在合理範圍內
                initial_guess = max(self.min_volatility, min(initial_guess, self.max_volatility))
                
                logger.debug(f"  初始猜測值 (Brenner-Subrahmanyam): {initial_guess*100:.2f}%")
                return initial_guess
            else:
                # 降級到固定初始值
                return 0.3
                
        except Exception as e:
            logger.warning(f"⚠ 初始猜測計算失敗，使用默認值 30%: {e}")
            return 0.3
    
    def calculate_implied_volatility(
        self,
        market_price: float,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        time_to_expiration: float,
        option_type: str = 'call',
        initial_guess: Optional[float] = None,
        calculation_date: Optional[str] = None
    ) -> IVResult:
        """
        計算隱含波動率
        
        使用 Newton-Raphson 迭代法從市場期權價格反推隱含波動率。
        
        參數:
            market_price: 市場期權價格（美元）
            stock_price: 當前股價（美元）
            strike_price: 行使價（美元）
            risk_free_rate: 無風險利率（年化，小數形式）
            time_to_expiration: 到期時間（年）
            option_type: 期權類型 ('call' 或 'put')
            initial_guess: 初始波動率猜測值（可選，默認使用 Brenner-Subrahmanyam）
            calculation_date: 計算日期（YYYY-MM-DD 格式）
        
        返回:
            IVResult: 包含隱含波動率和收斂信息的結果對象
        
        算法:
            Newton-Raphson 迭代:
            σ(n+1) = σ(n) - [BS_Price(σ(n)) - Market_Price] / Vega(σ(n))
            
            收斂條件:
            |BS_Price(σ(n)) - Market_Price| < tolerance
        
        異常:
            ValueError: 當輸入參數無效時
            RuntimeError: 當迭代未收斂時（返回最後一次迭代結果）
        
        示例:
            >>> calc = ImpliedVolatilityCalculator()
            >>> result = calc.calculate_implied_volatility(
            ...     market_price=10.45,
            ...     stock_price=100,
            ...     strike_price=100,
            ...     risk_free_rate=0.05,
            ...     time_to_expiration=1.0,
            ...     option_type='call'
            ... )
            >>> print(f"IV: {result.implied_volatility*100:.2f}%")
            >>> print(f"收斂: {result.converged}, 迭代次數: {result.iterations}")
        """
        try:
            logger.info(f"開始計算隱含波動率...")
            logger.info(f"  市場價格: ${market_price:.4f}")
            logger.info(f"  股價: ${stock_price:.2f}, 行使價: ${strike_price:.2f}")
            logger.info(f"  利率: {risk_free_rate*100:.2f}%, 時間: {time_to_expiration:.4f}年")
            logger.info(f"  期權類型: {option_type}")
            
            # 第1步: 輸入驗證
            if not self._validate_inputs(market_price, stock_price, strike_price, 
                                        risk_free_rate, time_to_expiration):
                raise ValueError("輸入參數無效")
            
            # 第2步: 獲取計算日期
            if calculation_date is None:
                calculation_date = datetime.now().strftime('%Y-%m-%d')
            
            # 第3步: 獲取初始猜測值
            if initial_guess is None:
                initial_guess = self._get_initial_guess(
                    market_price, stock_price, strike_price, time_to_expiration
                )
            else:
                # 確保初始猜測在合理範圍內
                initial_guess = max(self.min_volatility, min(initial_guess, self.max_volatility))
            
            logger.info(f"  初始猜測: {initial_guess*100:.2f}%")
            
            # 第4步: Newton-Raphson 迭代
            volatility = initial_guess
            converged = False
            
            for iteration in range(self.max_iterations):
                # 計算當前波動率下的 BS 價格
                bs_result = self.bs_calculator.calculate_option_price(
                    stock_price=stock_price,
                    strike_price=strike_price,
                    risk_free_rate=risk_free_rate,
                    time_to_expiration=time_to_expiration,
                    volatility=volatility,
                    option_type=option_type
                )
                
                bs_price = bs_result.option_price
                price_diff = bs_price - market_price
                
                # 檢查收斂
                if abs(price_diff) < self.tolerance:
                    converged = True
                    logger.info(f"  ✓ 收斂於第 {iteration + 1} 次迭代")
                    logger.info(f"    隱含波動率: {volatility*100:.2f}%")
                    logger.info(f"    價格差異: ${abs(price_diff):.6f}")
                    break
                
                # 計算 Vega
                vega = self.greeks_calculator.calculate_vega(
                    stock_price=stock_price,
                    strike_price=strike_price,
                    risk_free_rate=risk_free_rate,
                    time_to_expiration=time_to_expiration,
                    volatility=volatility
                )
                
                # 檢查 Vega 是否太小（避免除以零）
                if abs(vega) < 1e-10:
                    logger.warning(f"⚠ Vega 太小 ({vega:.10f})，停止迭代")
                    break
                
                # Newton-Raphson 更新
                # Vega = S × N'(d1) × √T 是 dC/dσ（對絕對波動率的導數）
                # Newton-Raphson: σ_new = σ_old - f(σ) / f'(σ)
                # 其中 f(σ) = BS_price(σ) - market_price
                # f'(σ) = dBS/dσ = Vega
                volatility_change = price_diff / vega
                volatility = volatility - volatility_change
                
                # 確保波動率在合理範圍內
                volatility = max(self.min_volatility, min(volatility, self.max_volatility))
                
                logger.debug(f"  迭代 {iteration + 1}: σ={volatility*100:.4f}%, "
                           f"BS價格=${bs_price:.4f}, 差異=${price_diff:.6f}")
            
            # 第5步: 最終計算
            final_bs_result = self.bs_calculator.calculate_option_price(
                stock_price=stock_price,
                strike_price=strike_price,
                risk_free_rate=risk_free_rate,
                time_to_expiration=time_to_expiration,
                volatility=volatility,
                option_type=option_type
            )
            
            final_price_diff = final_bs_result.option_price - market_price
            
            # 第6步: 異常值檢測
            if volatility > 2.0:  # 200%
                logger.warning(f"⚠ 隱含波動率異常高: {volatility*100:.2f}%")
            
            if not converged:
                logger.warning(f"⚠ 未在 {self.max_iterations} 次迭代內收斂")
                logger.warning(f"  最終波動率: {volatility*100:.2f}%")
                logger.warning(f"  最終價格差異: ${abs(final_price_diff):.6f}")
            
            # 第7步: 建立結果對象
            result = IVResult(
                market_price=market_price,
                implied_volatility=volatility,
                iterations=iteration + 1 if converged else self.max_iterations,
                converged=converged,
                bs_price=final_bs_result.option_price,
                price_difference=final_price_diff,
                initial_guess=initial_guess,
                calculation_date=calculation_date
            )
            
            if converged:
                logger.info(f"✓ 隱含波動率計算完成")
            else:
                logger.warning(f"⚠ 隱含波動率計算未完全收斂")
            
            return result
            
        except Exception as e:
            logger.error(f"✗ 隱含波動率計算失敗: {e}")
            raise
    
    @staticmethod
    def _validate_inputs(
        market_price: float,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        time_to_expiration: float
    ) -> bool:
        """
        驗證輸入參數
        
        參數:
            market_price: 市場期權價格
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
            market_price, stock_price, strike_price, 
            risk_free_rate, time_to_expiration
        ]):
            logger.error("✗ 所有參數必須是數字")
            return False
        
        # 驗證市場價格
        if market_price <= 0:
            logger.error(f"✗ 市場價格必須大於0: {market_price}")
            return False
        
        # 驗證股價和行使價
        if stock_price <= 0:
            logger.error(f"✗ 股價必須大於0: {stock_price}")
            return False
        
        if strike_price <= 0:
            logger.error(f"✗ 行使價必須大於0: {strike_price}")
            return False
        
        # 驗證到期時間
        if time_to_expiration <= 0:
            logger.error(f"✗ 到期時間必須大於0: {time_to_expiration}")
            return False
        
        # 驗證利率範圍
        if risk_free_rate < -0.1 or risk_free_rate > 0.5:
            logger.error(f"✗ 利率超出合理範圍: {risk_free_rate*100:.2f}%")
            return False
        
        logger.info("✓ 輸入參數驗證通過")
        return True


# 使用示例和測試
if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    import logging
    logging.basicConfig(level=logging.INFO)
    
    calculator = ImpliedVolatilityCalculator()
    
    print("\n" + "=" * 70)
    print("模塊17: 隱含波動率計算器")
    print("=" * 70)
    
    # 例子1: 從已知 IV 的期權價格反推 IV
    print("\n【例子1】驗證 IV 反推準確性")
    print("-" * 70)
    
    # 先用 BS 模型計算一個期權價格（已知 IV = 20%）
    bs_calc = BlackScholesCalculator()
    known_iv = 0.2
    bs_result = bs_calc.calculate_option_price(
        stock_price=100.0,
        strike_price=100.0,
        risk_free_rate=0.05,
        time_to_expiration=1.0,
        volatility=known_iv,
        option_type='call'
    )
    
    print(f"已知 IV: {known_iv*100:.2f}%")
    print(f"BS 計算的期權價格: ${bs_result.option_price:.4f}")
    
    # 從這個價格反推 IV
    iv_result = calculator.calculate_implied_volatility(
        market_price=bs_result.option_price,
        stock_price=100.0,
        strike_price=100.0,
        risk_free_rate=0.05,
        time_to_expiration=1.0,
        option_type='call'
    )
    
    print(f"\n反推結果:")
    print(f"  隱含波動率: {iv_result.implied_volatility*100:.2f}%")
    print(f"  迭代次數: {iv_result.iterations}")
    print(f"  收斂: {iv_result.converged}")
    print(f"  價格差異: ${abs(iv_result.price_difference):.6f}")
    print(f"  誤差: {abs(iv_result.implied_volatility - known_iv)*100:.4f}%")
    
    # 例子2: 高波動率情況
    print("\n【例子2】高波動率情況 (IV = 40%)")
    print("-" * 70)
    
    known_iv_high = 0.4
    bs_result_high = bs_calc.calculate_option_price(
        stock_price=100.0,
        strike_price=100.0,
        risk_free_rate=0.05,
        time_to_expiration=0.5,
        volatility=known_iv_high,
        option_type='call'
    )
    
    iv_result_high = calculator.calculate_implied_volatility(
        market_price=bs_result_high.option_price,
        stock_price=100.0,
        strike_price=100.0,
        risk_free_rate=0.05,
        time_to_expiration=0.5,
        option_type='call'
    )
    
    print(f"已知 IV: {known_iv_high*100:.2f}%")
    print(f"反推 IV: {iv_result_high.implied_volatility*100:.2f}%")
    print(f"迭代次數: {iv_result_high.iterations}")
    print(f"收斂: {iv_result_high.converged}")
    
    # 例子3: Put 期權
    print("\n【例子3】Put 期權 IV 反推")
    print("-" * 70)
    
    bs_result_put = bs_calc.calculate_option_price(
        stock_price=100.0,
        strike_price=100.0,
        risk_free_rate=0.05,
        time_to_expiration=1.0,
        volatility=0.25,
        option_type='put'
    )
    
    iv_result_put = calculator.calculate_implied_volatility(
        market_price=bs_result_put.option_price,
        stock_price=100.0,
        strike_price=100.0,
        risk_free_rate=0.05,
        time_to_expiration=1.0,
        option_type='put'
    )
    
    print(f"已知 IV: 25.00%")
    print(f"反推 IV: {iv_result_put.implied_volatility*100:.2f}%")
    print(f"迭代次數: {iv_result_put.iterations}")
    print(f"收斂: {iv_result_put.converged}")
    
    print("\n" + "=" * 70)
    print("注: IV 反推用於驗證市場數據和發現定價異常")
    print("=" * 70)
