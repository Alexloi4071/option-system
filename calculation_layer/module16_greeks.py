# calculation_layer/module16_greeks.py
"""
模塊16: Greeks 期權風險指標計算
書籍來源: 金融工程標準模型

功能:
- 計算期權的 Greeks 風險指標
- 支持 Delta, Gamma, Theta, Vega, Rho
- 支持 Call 和 Put 期權
- 提供完整的風險管理指標

理論基礎:
Greeks 是期權價格對各種市場參數的敏感度指標，用於風險管理和對沖策略。
每個 Greek 代表期權價格對特定參數變化的偏導數。

核心公式:
─────────────────────────────────────
Delta (Δ):
  Call: Δ = N(d1)
  Put:  Δ = N(d1) - 1
  含義: 期權價格對股價變化的敏感度

Gamma (Γ):
  Γ = N'(d1) / (S × σ × √T)
  含義: Delta 對股價變化的敏感度（Delta 的變化率）

Theta (Θ):
  Call: Θ = -[S×N'(d1)×σ / (2×√T)] - r×K×e^(-r×T)×N(d2)
  Put:  Θ = -[S×N'(d1)×σ / (2×√T)] + r×K×e^(-r×T)×N(-d2)
  含義: 期權價格對時間流逝的敏感度（時間衰減）

Vega (ν):
  ν = S × N'(d1) × √T
  含義: 期權價格對波動率變化的敏感度

Rho (ρ):
  Call: ρ = K×T×e^(-r×T)×N(d2)
  Put:  ρ = -K×T×e^(-r×T)×N(-d2)
  含義: 期權價格對利率變化的敏感度

其中:
N(x) = 標準正態累積分佈函數
N'(x) = 標準正態概率密度函數 = (1/√(2π)) × e^(-x²/2)
─────────────────────────────────────

參考文獻:
- Hull, J. C. (2018). Options, Futures, and Other Derivatives (10th ed.). Pearson.
- Natenberg, S. (1994). Option Volatility and Pricing. McGraw-Hill.
"""

import logging
import math
from dataclasses import dataclass
from typing import Dict
from datetime import datetime

# 導入 Module 15 的 Black-Scholes 計算器
try:
    from calculation_layer.module15_black_scholes import BlackScholesCalculator
except ImportError:
    from module15_black_scholes import BlackScholesCalculator

logger = logging.getLogger(__name__)


@dataclass
class GreeksResult:
    """Greeks 計算結果"""
    stock_price: float
    strike_price: float
    risk_free_rate: float
    time_to_expiration: float
    volatility: float
    option_type: str
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    calculation_date: str
    data_source: str = "Self-Calculated"
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        return {
            'stock_price': round(self.stock_price, 2),
            'strike_price': round(self.strike_price, 2),
            'risk_free_rate': round(self.risk_free_rate, 6),
            'time_to_expiration': round(self.time_to_expiration, 4),
            'volatility': round(self.volatility, 4),
            'option_type': self.option_type,
            'delta': round(self.delta, 6),
            'gamma': round(self.gamma, 6),
            'theta': round(self.theta, 6),
            'vega': round(self.vega, 6),
            'rho': round(self.rho, 6),
            'calculation_date': self.calculation_date,
            'data_source': self.data_source,
            'model': 'Black-Scholes Greeks'
        }


class GreeksCalculator:
    """
    期權 Greeks 計算器
    
    功能:
    - 計算 Delta, Gamma, Theta, Vega, Rho
    - 支持 Call 和 Put 期權
    - 提供完整的風險指標
    - 依賴 Module 15 的 Black-Scholes 計算器
    
    使用示例:
    >>> calculator = GreeksCalculator()
    >>> result = calculator.calculate_all_greeks(
    ...     stock_price=100,
    ...     strike_price=100,
    ...     risk_free_rate=0.05,
    ...     time_to_expiration=1.0,
    ...     volatility=0.2,
    ...     option_type='call'
    ... )
    >>> print(f"Delta: {result.delta:.4f}")
    >>> print(f"Gamma: {result.gamma:.4f}")
    """
    
    def __init__(self):
        """初始化 Greeks 計算器"""
        self.bs_calculator = BlackScholesCalculator()
        logger.info("* Greeks 計算器已初始化")
    
    def calculate_delta(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        time_to_expiration: float,
        volatility: float,
        option_type: str = 'call'
    ) -> float:
        """
        計算 Delta
        
        Delta 衡量期權價格對股價變化的敏感度。
        
        參數:
            stock_price: 當前股價
            strike_price: 行使價
            risk_free_rate: 無風險利率
            time_to_expiration: 到期時間（年）
            volatility: 波動率
            option_type: 期權類型 ('call' 或 'put')
        
        返回:
            float: Delta 值
                Call: 0 到 1 之間
                Put: -1 到 0 之間
        
        公式:
            Call Delta: Δ = N(d1)
            Put Delta:  Δ = N(d1) - 1
        
        解釋:
            - Delta = 0.5 表示股價上漲 $1，期權價格上漲 $0.50
            - Call Delta 為正，Put Delta 為負
            - ATM 期權的 Delta 約為 ±0.5
        """
        try:
            # 計算 d1
            d1, _ = self.bs_calculator.calculate_d1_d2(
                stock_price, strike_price, risk_free_rate,
                time_to_expiration, volatility
            )
            
            # 計算 Delta
            option_type_lower = option_type.lower()
            
            if option_type_lower == 'call':
                # Call Delta: N(d1)
                delta = self.bs_calculator.normal_cdf(d1)
            elif option_type_lower == 'put':
                # Put Delta: N(d1) - 1
                delta = self.bs_calculator.normal_cdf(d1) - 1
            else:
                raise ValueError(f"無效的期權類型: {option_type}")
            
            logger.debug(f"  Delta ({option_type}): {delta:.6f}")
            
            return delta
            
        except Exception as e:
            logger.error(f"✗ 計算 Delta 失敗: {e}")
            raise

    def calculate_gamma(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        time_to_expiration: float,
        volatility: float
    ) -> float:
        """
        計算 Gamma
        
        Gamma 衡量 Delta 對股價變化的敏感度（Delta 的變化率）。
        Gamma 對 Call 和 Put 期權都是相同的（總是正數）。
        
        參數:
            stock_price: 當前股價
            strike_price: 行使價
            risk_free_rate: 無風險利率
            time_to_expiration: 到期時間（年）
            volatility: 波動率
        
        返回:
            float: Gamma 值（總是正數）
        
        公式:
            Γ = N'(d1) / (S × σ × √T)
        
        解釋:
            - Gamma 總是正數
            - ATM 期權的 Gamma 最大
            - Gamma 衡量對沖組合的穩定性
            - 高 Gamma 意味著需要頻繁調整對沖
        """
        try:
            # 計算 d1
            d1, _ = self.bs_calculator.calculate_d1_d2(
                stock_price, strike_price, risk_free_rate,
                time_to_expiration, volatility
            )
            
            # 計算 Gamma
            # Γ = N'(d1) / (S × σ × √T)
            sqrt_t = math.sqrt(time_to_expiration)
            gamma = (self.bs_calculator.normal_pdf(d1) / 
                    (stock_price * volatility * sqrt_t))
            
            logger.debug(f"  Gamma: {gamma:.6f}")
            
            # 驗證 Gamma 為正數
            if gamma < 0:
                logger.warning(f"⚠ Gamma 應該為正數，但得到: {gamma}")
            
            return gamma
            
        except Exception as e:
            logger.error(f"✗ 計算 Gamma 失敗: {e}")
            raise
    
    def _calculate_theta_annual(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        time_to_expiration: float,
        volatility: float,
        option_type: str = 'call'
    ) -> float:
        """
        計算年化 Theta（內部方法）
        
        參數:
            stock_price: 當前股價
            strike_price: 行使價
            risk_free_rate: 無風險利率
            time_to_expiration: 到期時間（年）
            volatility: 波動率
            option_type: 期權類型 ('call' 或 'put')
        
        返回:
            float: 年化 Theta 值
        
        公式:
            Call: Θ = -[S×N'(d1)×σ / (2×√T)] - r×K×e^(-r×T)×N(d2)
            Put:  Θ = -[S×N'(d1)×σ / (2×√T)] + r×K×e^(-r×T)×N(-d2)
        """
        # 計算 d1 和 d2
        d1, d2 = self.bs_calculator.calculate_d1_d2(
            stock_price, strike_price, risk_free_rate,
            time_to_expiration, volatility
        )
        
        # 計算共同項
        sqrt_t = math.sqrt(time_to_expiration)
        discount_factor = math.exp(-risk_free_rate * time_to_expiration)
        
        # 第一項（對 Call 和 Put 都相同）
        term1 = -(stock_price * self.bs_calculator.normal_pdf(d1) * volatility) / (2 * sqrt_t)
        
        # 第二項（Call 和 Put 不同）
        option_type_lower = option_type.lower()
        
        if option_type_lower == 'call':
            # Call Theta
            term2 = -risk_free_rate * strike_price * discount_factor * self.bs_calculator.normal_cdf(d2)
            theta_annual = term1 + term2
        elif option_type_lower == 'put':
            # Put Theta
            term2 = risk_free_rate * strike_price * discount_factor * self.bs_calculator.normal_cdf(-d2)
            theta_annual = term1 + term2
        else:
            raise ValueError(f"無效的期權類型: {option_type}")
        
        return theta_annual

    def calculate_theta(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        time_to_expiration: float,
        volatility: float,
        option_type: str = 'call'
    ) -> float:
        """
        計算 Theta（每日時間衰減）
        
        Theta 衡量期權價格對時間流逝的敏感度（時間衰減）。
        通常為負數，表示隨著時間流逝，期權價值減少。
        
        參數:
            stock_price: 當前股價
            strike_price: 行使價
            risk_free_rate: 無風險利率
            time_to_expiration: 到期時間（年）
            volatility: 波動率
            option_type: 期權類型 ('call' 或 'put')
        
        返回:
            float: 每日 Theta 值（$/天）
        
        公式:
            Call: Θ = -[S×N'(d1)×σ / (2×√T)] - r×K×e^(-r×T)×N(d2)
            Put:  Θ = -[S×N'(d1)×σ / (2×√T)] + r×K×e^(-r×T)×N(-d2)
            每日 Theta = 年化 Theta / 365
        
        解釋:
            - Theta 通常為負（時間衰減）
            - ATM 期權的 Theta 最大（絕對值）
            - 接近到期時，Theta 加速
            - 返回值為每日衰減金額，例如 -0.05 表示每天損失 $0.05
        """
        try:
            # 計算年化 Theta
            theta_annual = self._calculate_theta_annual(
                stock_price, strike_price, risk_free_rate,
                time_to_expiration, volatility, option_type
            )
            
            # 轉換為每日 Theta
            theta_daily = theta_annual / 365.0
            
            # 記錄年化值和每日值以便驗證
            logger.debug(f"  Theta ({option_type}): 年化={theta_annual:.6f}, 每日={theta_daily:.6f} ($/天)")
            
            return theta_daily
            
        except Exception as e:
            logger.error(f"✗ 計算 Theta 失敗: {e}")
            raise
    
    def calculate_vega(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        time_to_expiration: float,
        volatility: float
    ) -> float:
        """
        計算 Vega
        
        Vega 衡量期權價格對波動率變化的敏感度。
        Vega 對 Call 和 Put 期權都是相同的（總是正數）。
        
        參數:
            stock_price: 當前股價
            strike_price: 行使價
            risk_free_rate: 無風險利率
            time_to_expiration: 到期時間（年）
            volatility: 波動率
        
        返回:
            float: Vega 值（對 1% 波動率變化的敏感度）
        
        公式:
            ν = S × N'(d1) × √T
        
        解釋:
            - Vega 總是正數
            - ATM 期權的 Vega 最大
            - 長期期權的 Vega 更大
            - Vega = 0.2 表示波動率上升 1%，期權價格上升 $0.20
        """
        try:
            # 計算 d1
            d1, _ = self.bs_calculator.calculate_d1_d2(
                stock_price, strike_price, risk_free_rate,
                time_to_expiration, volatility
            )
            
            # 計算 Vega
            # ν = S × N'(d1) × √T / 100
            # 除以 100 是因為 Vega 表示 IV 變化 1 個百分點（如 31% → 32%）的期權價格變化
            sqrt_t = math.sqrt(time_to_expiration)
            vega = stock_price * self.bs_calculator.normal_pdf(d1) * sqrt_t / 100
            
            # 標準 Vega 定義：IV 上升 1 個百分點，期權價格變化多少美元
            # 例如：Vega = 0.25 表示 IV 從 31% 升到 32%，期權價格上升 $0.25
            
            logger.debug(f"  Vega: {vega:.6f}")
            
            # 驗證 Vega 為正數
            if vega < 0:
                logger.warning(f"⚠ Vega 應該為正數，但得到: {vega}")
            
            return vega
            
        except Exception as e:
            logger.error(f"✗ 計算 Vega 失敗: {e}")
            raise
    
    def calculate_rho(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        time_to_expiration: float,
        volatility: float,
        option_type: str = 'call'
    ) -> float:
        """
        計算 Rho
        
        Rho 衡量期權價格對利率變化的敏感度。
        
        參數:
            stock_price: 當前股價
            strike_price: 行使價
            risk_free_rate: 無風險利率
            time_to_expiration: 到期時間（年）
            volatility: 波動率
            option_type: 期權類型 ('call' 或 'put')
        
        返回:
            float: Rho 值（對 1% 利率變化的敏感度）
        
        公式:
            Call: ρ = K×T×e^(-r×T)×N(d2)
            Put:  ρ = -K×T×e^(-r×T)×N(-d2)
        
        解釋:
            - Call Rho 為正，Put Rho 為負
            - 長期期權的 Rho 更大
            - 在低利率環境下，Rho 的影響較小
        """
        try:
            # 計算 d2
            _, d2 = self.bs_calculator.calculate_d1_d2(
                stock_price, strike_price, risk_free_rate,
                time_to_expiration, volatility
            )
            
            # 計算折現因子
            discount_factor = math.exp(-risk_free_rate * time_to_expiration)
            
            # 計算 Rho
            option_type_lower = option_type.lower()
            
            if option_type_lower == 'call':
                # Call Rho: K×T×e^(-r×T)×N(d2)
                rho = strike_price * time_to_expiration * discount_factor * self.bs_calculator.normal_cdf(d2)
            elif option_type_lower == 'put':
                # Put Rho: -K×T×e^(-r×T)×N(-d2)
                rho = -strike_price * time_to_expiration * discount_factor * self.bs_calculator.normal_cdf(-d2)
            else:
                raise ValueError(f"無效的期權類型: {option_type}")
            
            logger.debug(f"  Rho ({option_type}): {rho:.6f}")
            
            return rho
            
        except Exception as e:
            logger.error(f"✗ 計算 Rho 失敗: {e}")
            raise
    
    def calculate_all_greeks(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        time_to_expiration: float,
        volatility: float,
        option_type: str = 'call',
        calculation_date: str = None
    ) -> GreeksResult:
        """
        計算所有 Greeks
        
        一次性計算所有風險指標，提高效率。
        
        參數:
            stock_price: 當前股價
            strike_price: 行使價
            risk_free_rate: 無風險利率（年化，小數形式）
            time_to_expiration: 到期時間（年）
            volatility: 波動率（年化，小數形式）
            option_type: 期權類型 ('call' 或 'put')
            calculation_date: 計算日期（YYYY-MM-DD 格式）
        
        返回:
            GreeksResult: 包含所有 Greeks 的結果對象
        
        示例:
            >>> calc = GreeksCalculator()
            >>> result = calc.calculate_all_greeks(
            ...     stock_price=100,
            ...     strike_price=100,
            ...     risk_free_rate=0.05,
            ...     time_to_expiration=1.0,
            ...     volatility=0.2,
            ...     option_type='call'
            ... )
            >>> print(f"Delta: {result.delta:.4f}")
            >>> print(f"Gamma: {result.gamma:.4f}")
            >>> print(f"Theta: {result.theta:.4f}")
            >>> print(f"Vega: {result.vega:.4f}")
            >>> print(f"Rho: {result.rho:.4f}")
        
        異常:
            ValueError: 當輸入參數無效時
        """
        try:
            logger.info(f"開始計算 Greeks...")
            logger.info(f"  股價: ${stock_price:.2f}, 行使價: ${strike_price:.2f}")
            logger.info(f"  利率: {risk_free_rate*100:.2f}%, 時間: {time_to_expiration:.4f}年")
            logger.info(f"  波動率: {volatility*100:.2f}%, 類型: {option_type}")
            
            # 驗證輸入
            if not self.bs_calculator._validate_inputs(
                stock_price, strike_price, risk_free_rate,
                time_to_expiration, volatility, option_type
            ):
                raise ValueError("輸入參數無效")
            
            # 獲取計算日期
            if calculation_date is None:
                calculation_date = datetime.now().strftime('%Y-%m-%d')
            
            # 計算所有 Greeks
            delta = self.calculate_delta(
                stock_price, strike_price, risk_free_rate,
                time_to_expiration, volatility, option_type
            )
            
            gamma = self.calculate_gamma(
                stock_price, strike_price, risk_free_rate,
                time_to_expiration, volatility
            )
            
            theta = self.calculate_theta(
                stock_price, strike_price, risk_free_rate,
                time_to_expiration, volatility, option_type
            )
            
            vega = self.calculate_vega(
                stock_price, strike_price, risk_free_rate,
                time_to_expiration, volatility
            )
            
            rho = self.calculate_rho(
                stock_price, strike_price, risk_free_rate,
                time_to_expiration, volatility, option_type
            )
            
            logger.info(f"  計算結果:")
            logger.info(f"    Delta = {delta:.6f}")
            logger.info(f"    Gamma = {gamma:.6f}")
            logger.info(f"    Theta = {theta:.6f} ($/天)")
            logger.info(f"    Vega = {vega:.6f}")
            logger.info(f"    Rho = {rho:.6f}")
            
            # 驗證 Greeks 值是否在合理範圍
            try:
                from utils.validation import GreeksValidator
                greeks_to_validate = {
                    'delta': delta,
                    'gamma': gamma,
                    'theta': theta,
                    'vega': vega,
                    'rho': rho
                }
                validation_result = GreeksValidator.validate_greeks(greeks_to_validate)
                
                if not validation_result['is_valid']:
                    logger.warning(f"⚠ Greeks 驗證警告: {validation_result['invalid_greeks']}")
                    for greek_name in validation_result['invalid_greeks']:
                        detail = validation_result['details'].get(greek_name, {})
                        logger.warning(f"    {greek_name}: {detail.get('message', 'Unknown error')}")
            except ImportError:
                logger.debug("  Greeks 驗證模塊未安裝，跳過驗證")
            except Exception as e:
                logger.debug(f"  Greeks 驗證失敗: {e}")
            
            # 建立結果對象
            result = GreeksResult(
                stock_price=stock_price,
                strike_price=strike_price,
                risk_free_rate=risk_free_rate,
                time_to_expiration=time_to_expiration,
                volatility=volatility,
                option_type=option_type.lower(),
                delta=delta,
                gamma=gamma,
                theta=theta,
                vega=vega,
                rho=rho,
                calculation_date=calculation_date
            )
            
            logger.info(f"  Greeks 計算完成")
            
            return result
            
        except Exception as e:
            logger.error(f"✗ Greeks 計算失敗: {e}")
            raise


# 使用示例和測試
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    calculator = GreeksCalculator()
    
    print("\n" + "=" * 70)
    print("模塊16: Greeks 期權風險指標計算")
    print("=" * 70)
    
    # 例子1: ATM Call 期權的 Greeks
    print("\n【例子1】ATM Call 期權的 Greeks")
    print("-" * 70)
    
    result1 = calculator.calculate_all_greeks(
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
    print(f"  期權類型: {result1.option_type.upper()}")
    print(f"\nGreeks:")
    print(f"  Delta:  {result1.delta:>10.6f}  (股價變化 $1 → 期權價格變化 ${result1.delta:.2f})")
    print(f"  Gamma:  {result1.gamma:>10.6f}  (股價變化 $1 → Delta 變化 {result1.gamma:.6f})")
    print(f"  Theta:  {result1.theta:>10.6f}  (每日時間衰減 $/天)")
    print(f"  Vega:   {result1.vega:>10.6f}  (波動率變化 1% → 期權價格變化 ${result1.vega/100:.2f})")
    print(f"  Rho:    {result1.rho:>10.6f}  (利率變化 1% → 期權價格變化 ${result1.rho/100:.2f})")
    
    # 例子2: ATM Put 期權的 Greeks
    print("\n【例子2】ATM Put 期權的 Greeks")
    print("-" * 70)
    
    result2 = calculator.calculate_all_greeks(
        stock_price=100.0,
        strike_price=100.0,
        risk_free_rate=0.05,
        time_to_expiration=1.0,
        volatility=0.2,
        option_type='put'
    )
    
    print(f"\n計算結果:")
    print(f"  期權類型: {result2.option_type.upper()}")
    print(f"\nGreeks:")
    print(f"  Delta:  {result2.delta:>10.6f}  (注: Put Delta 為負)")
    print(f"  Gamma:  {result2.gamma:>10.6f}  (與 Call 相同)")
    print(f"  Theta:  {result2.theta:>10.6f}")
    print(f"  Vega:   {result2.vega:>10.6f}  (與 Call 相同)")
    print(f"  Rho:    {result2.rho:>10.6f}  (注: Put Rho 為負)")
    
    # 例子3: ITM Call 期權的 Greeks
    print("\n【例子3】ITM Call 期權的 Greeks (股價 > 行使價)")
    print("-" * 70)
    
    result3 = calculator.calculate_all_greeks(
        stock_price=110.0,
        strike_price=100.0,
        risk_free_rate=0.05,
        time_to_expiration=0.5,
        volatility=0.25,
        option_type='call'
    )
    
    print(f"\n計算結果:")
    print(f"  股價: ${result3.stock_price:.2f}")
    print(f"  行使價: ${result3.strike_price:.2f}")
    print(f"  Delta:  {result3.delta:>10.6f}  (ITM Call Delta 接近 1)")
    print(f"  Gamma:  {result3.gamma:>10.6f}")
    
    # 例子4: OTM Call 期權的 Greeks
    print("\n【例子4】OTM Call 期權的 Greeks (股價 < 行使價)")
    print("-" * 70)
    
    result4 = calculator.calculate_all_greeks(
        stock_price=90.0,
        strike_price=100.0,
        risk_free_rate=0.05,
        time_to_expiration=0.5,
        volatility=0.25,
        option_type='call'
    )
    
    print(f"\n計算結果:")
    print(f"  股價: ${result4.stock_price:.2f}")
    print(f"  行使價: ${result4.strike_price:.2f}")
    print(f"  Delta:  {result4.delta:>10.6f}  (OTM Call Delta 接近 0)")
    print(f"  Gamma:  {result4.gamma:>10.6f}")
    
    # 例子5: Greeks 的對稱性驗證
    print("\n【例子5】Greeks 的對稱性驗證")
    print("-" * 70)
    
    print(f"\nCall vs Put (相同參數):")
    print(f"  Gamma (Call): {result1.gamma:.6f}")
    print(f"  Gamma (Put):  {result2.gamma:.6f}")
    print(f"  差異: {abs(result1.gamma - result2.gamma):.8f}")
    
    print(f"\n  Vega (Call): {result1.vega:.6f}")
    print(f"  Vega (Put):  {result2.vega:.6f}")
    print(f"  差異: {abs(result1.vega - result2.vega):.8f}")
    
    print(f"\n  Delta (Call): {result1.delta:.6f}")
    print(f"  Delta (Put):  {result2.delta:.6f}")
    print(f"  Delta 差異: {result1.delta - result2.delta:.6f}  (應該接近 1)")
    
    print("\n" + "=" * 70)
    print("注: Greeks 用於風險管理和對沖策略")
    print("=" * 70)
