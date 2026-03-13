# calculation_layer/american_option_pricer.py
"""
美式期權定價模型 (American Option Pricing)

**BR-03 Fix**: Renamed from module32_american_pricing.py to semantic internal naming.
This is an internal pricing engine, not a user-facing numbered analysis module.
Module 32 now unambiguously refers to module32_complex_strategies.py (Complex Strategies Analysis).

功能:
- 計算美式 Call 和 Put 期權的理論價值
- 支持向量化的 Cox-Ross-Rubinstein (CRR) 二叉樹模型
- 直接從二叉樹節點提取美式期權 Greeks ($\Delta, \Gamma, \Theta$)
- 精確計算美式期權的提早履約溢價 (Early Exercise Premium)

理論基礎:
由於美股期權多為美式，可以隨時提早履約。傳統 Black-Scholes 假設只能在到期日履約，
這會導致在有股息或深度價內時低估選項價值。John Hull 推薦使用二叉樹直接定價並提取 Greeks。

核心算法:
1. Vectorized CRR Binomial Tree (二叉樹):
   將時間分為 N 步，建立股價二叉樹，由後向前推導期權價值，每個節點考慮是否提早履約。
   使用 Numpy 矩陣運算，將傳統 python loop O(n^2) 效能提升，允許步數 > 500。
2. Greeks 提取 (John Hull Ch. 21):
   直接利用樹的前兩步節點計算 $\Delta, \Gamma, \Theta$
"""

import logging
import math
import numpy as np
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

# 依賴 Black-Scholes 作為基準對比
try:
    from calculation_layer.module15_black_scholes import BlackScholesCalculator
except ImportError:
    from module15_black_scholes import BlackScholesCalculator

logger = logging.getLogger(__name__)

@dataclass
class AmericanPricingResult:
    """美式期權定價與 Greeks 結果"""
    stock_price: float
    strike_price: float
    risk_free_rate: float
    time_to_expiration: float
    volatility: float
    option_type: str
    dividend_yield: float
    european_price: float
    american_price: float
    early_exercise_premium: float
    model_used: str
    calculation_date: str
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0

    def to_dict(self) -> Dict:
        return {
            'stock_price': round(self.stock_price, 2),
            'strike_price': round(self.strike_price, 2),
            'risk_free_rate': round(self.risk_free_rate, 6),
            'time_to_expiration': round(self.time_to_expiration, 4),
            'volatility': round(self.volatility, 4),
            'option_type': self.option_type,
            'dividend_yield': round(self.dividend_yield, 6),
            'european_price': round(self.european_price, 4),
            'american_price': round(self.american_price, 4),
            'early_exercise_premium': round(self.early_exercise_premium, 4),
            'model_used': self.model_used,
            'calculation_date': self.calculation_date,
            'delta': round(self.delta, 6),
            'gamma': round(self.gamma, 6),
            'theta': round(self.theta, 6)
        }

class AmericanOptionPricer:
    """
    美式期權定價與 Greeks 計算器
    使用 Vectorized Binomial Tree 方法 (基於 John Hull)
    """

    def __init__(self):
        self.bs_calculator = BlackScholesCalculator()
        logger.info("✓ 美式期權定價器已初始化 (Vectorized CRR Binomial Tree)")

    def price_binomial_tree(self, 
                            S: float, K: float, T: float, r: float, 
                            sigma: float, option_type: str = 'call', 
                            q: float = 0.0, discrete_dividends: Optional[list] = None, 
                            steps: int = 500) -> Tuple[float, float, float, float]:
        """
        使用 Numpy 向量化的 Cox-Ross-Rubinstein (CRR) 二叉樹模型計算美式期權定價與 Greeks
        
        參數:
            S: 當前股價
            K: 行使價
            T: 到期時間(年)
            r: 無風險利率
            sigma: 波動率
            option_type: 'call' 或 'put'
            q: 股息率 (如提供 discrete_dividends，將覆寫此連續股息率)
            discrete_dividends: 離散股息列表，格式為 [(time_to_ex_date_years, amount), ...]
            steps: 樹的步數 (向量化後建議可設500步獲得高精度)
            
        返回:
            Tuple[float, float, float, float]: (期權價格, Delta, Gamma, 每日 Theta)
        """
        is_call = option_type.lower() == 'call'
        if T <= 0:
            intrinsic = max(0.0, S - K) if is_call else max(0.0, K - S)
            return intrinsic, 0.0, 0.0, 0.0
            
        if steps < 3:
            steps = 3  # 需要至少 3 步來提取 Gamma

        # 離散股息處理 (John Hull Ch. 21.3)
        if discrete_dividends is None:
            discrete_dividends = []
            
        # 過濾出到期日之前的股息
        valid_divs = [(t_div, amt) for t_div, amt in discrete_dividends if 0 < t_div <= T]
        
        S_star = S
        if valid_divs:
            # 扣除所有期間股息的現值得到無股息資產價格 S*
            pv_divs = sum(amt * math.exp(-r * t_div) for t_div, amt in valid_divs)
            S_star = S - pv_divs
            q = 0.0  # 覆寫連續股息率為 0，因已提取離散股息

        dt = T / steps
        u = math.exp(sigma * math.sqrt(dt))
        d = 1 / u
        
        # 風險中性機率 p (對 S* 來說 q=0，但如果使用連續股息則 q 存在)
        a = math.exp((r - q) * dt)
        p = (a - d) / (u - d)
        
        # 折現因子
        discount = math.exp(-r * dt)
        
        # 初始化樹的最後一層 (到期日), 共 steps + 1 個節點
        j_nodes = np.arange(steps, -1, -1)
        i_nodes = np.arange(0, steps + 1)
        
        # 到期日時，S* = S_T (因為到達到期的剩餘股息現值為 0)
        ST = S_star * (u ** j_nodes) * (d ** i_nodes)
        
        if is_call:
            prices = np.maximum(0.0, ST - K)
        else:
            prices = np.maximum(0.0, K - ST)
            
        prices_step2 = None
        prices_step1 = None

        # 從後往前推導
        for step in range(steps - 1, -1, -1):
            t_k = step * dt
            
            # 預期持有價值向量
            hold_val = discount * (p * prices[:-1] + (1 - p) * prices[1:])
            
            # 當前節點底層資產 S* 價格向量
            j_curr = np.arange(step, -1, -1)
            i_curr = np.arange(0, step + 1)
            st_price_star = S_star * (u ** j_curr) * (d ** i_curr)
            
            # 計算當前節點真實股票價格 = S* + 此刻後續剩餘股息之現值
            pv_rem_divs = 0.0
            if valid_divs:
                pv_rem_divs = sum(amt * math.exp(-r * (t_div - t_k)) for t_div, amt in valid_divs if t_div > t_k)
            st_price = st_price_star + pv_rem_divs
            
            # 提早履約價值
            if is_call:
                exercise_val = np.maximum(0.0, st_price - K)
            else:
                exercise_val = np.maximum(0.0, K - st_price)
                
            # 美式期權: 取兩者最大
            prices = np.maximum(hold_val, exercise_val)

            # 保存特定步數的定價矩陣以計算 Greeks
            if step == 2:
                prices_step2 = prices.copy()
            elif step == 1:
                prices_step1 = prices.copy()

        f0 = float(prices[0])

        # 計算 Greeks (John Hull Ch.21)
        delta = 0.0
        gamma = 0.0
        theta_daily = 0.0
        
        try:
            # Greeks calculation helper for actual S
            def get_actual_s(step_num):
                t_k = step_num * dt
                rem_divs = sum(amt * math.exp(-r * (t_div - t_k)) for t_div, amt in valid_divs if t_div > t_k) if valid_divs else 0.0
                return rem_divs
                
            # 1. Delta: 取 t=1
            f1_1 = float(prices_step1[0]) # Up
            f1_0 = float(prices_step1[1]) # Down
            pv_d_1 = get_actual_s(1)
            S1_1 = S_star * u + pv_d_1
            S1_0 = S_star * d + pv_d_1
            delta = (f1_1 - f1_0) / (S1_1 - S1_0) if (S1_1 - S1_0) != 0 else 0
            
            # 2. Gamma: 取 t=2
            f2_2 = float(prices_step2[0]) # Up-Up
            f2_1 = float(prices_step2[1]) # Up-Down (or Down-Up)
            f2_0 = float(prices_step2[2]) # Down-Down
            pv_d_2 = get_actual_s(2)
            S2_2 = S_star * u * u + pv_d_2
            S2_1 = S_star + pv_d_2
            S2_0 = S_star * d * d + pv_d_2
            
            # Gamma = [ (f2_2 - f2_1) / (S2_2 - S2_1) - (f2_1 - f2_0) / (S2_1 - S2_0) ] / [ 0.5 * (S2_2 - S2_0) ]
            delta_up = (f2_2 - f2_1) / (S2_2 - S2_1) if (S2_2 - S2_1) != 0 else 0
            delta_down = (f2_1 - f2_0) / (S2_1 - S2_0) if (S2_1 - S2_0) != 0 else 0
            gamma_h = 0.5 * (S2_2 - S2_0)
            gamma = (delta_up - delta_down) / gamma_h if gamma_h != 0 else 0
            
            # 3. Theta: 取 t=2 推至 t=0
            # Theta per year = (f2_1 - f0) / (2 * dt)
            theta_annual = (f2_1 - f0) / (2 * dt) if dt != 0 else 0
            theta_daily = theta_annual / 252.0  # 轉換為每日衰減 ($/天)
            
        except Exception as e:
            logger.warning(f"⚠ Extracting Greeks from Binomial Tree failed. Using 0s. Error: {e}")

        return f0, delta, gamma, theta_daily

    def calculate_american_price(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        time_to_expiration: float,
        volatility: float,
        option_type: str = 'call',
        dividend_yield: float = 0.0,
        discrete_dividends: Optional[list] = None,
        model: str = 'binomial',
        steps: int = 500
    ) -> AmericanPricingResult:
        """
        計算美式期權價格與 Greeks，並對比歐式價格
        
        提供向下兼容的 API，內部使用向量化二叉樹計算
        """
        import datetime
        calc_date = datetime.datetime.now().strftime("%Y-%m-%d")

        # 1. 基準歐式價格
        # 2. 準備歐式黑休斯模型需要的股息調整
        bs_dividend_yield = dividend_yield
        if discrete_dividends and time_to_expiration > 0:
            # 轉換離散股息為近似的連續股息率（或調整 S），此處簡單將 S 調整
            valid_divs = [(t_div, amt) for t_div, amt in discrete_dividends if 0 < t_div <= time_to_expiration]
            pv_divs = sum(amt * math.exp(-risk_free_rate * t_div) for t_div, amt in valid_divs)
            
            # 調用 BS 時使用調整後的 S，且不使用連續股息率
            bs_result = self.bs_calculator.calculate_option_price(
                stock_price=max(0.01, stock_price - pv_divs),
                strike_price=strike_price,
                risk_free_rate=risk_free_rate,
                time_to_expiration=time_to_expiration,
                volatility=volatility,
                option_type=option_type,
                dividend_yield=0.0
            )
        else:
            bs_result = self.bs_calculator.calculate_option_price(
                stock_price=stock_price,
                strike_price=strike_price,
                risk_free_rate=risk_free_rate,
                time_to_expiration=time_to_expiration,
                volatility=volatility,
                option_type=option_type,
                dividend_yield=dividend_yield
            )
            
        euro_price = bs_result.option_price

        # 3. 美式價格與 Greeks
        am_price, delta, gamma, theta = self.price_binomial_tree(
            S=stock_price, K=strike_price, T=time_to_expiration,
            r=risk_free_rate, sigma=volatility, option_type=option_type,
            q=dividend_yield, discrete_dividends=discrete_dividends, steps=steps
        )
            
        # 價格合理性保護 (美式 >= 歐式)
        am_price = max(am_price, euro_price)
        premium = am_price - euro_price

        return AmericanPricingResult(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            volatility=volatility,
            option_type=option_type,
            dividend_yield=dividend_yield,
            european_price=euro_price,
            american_price=am_price,
            early_exercise_premium=premium,
            model_used='binomial',
            calculation_date=calc_date,
            delta=delta,
            gamma=gamma,
            theta=theta
        )
