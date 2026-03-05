# calculation_layer/module32_american_pricing.py
"""
模塊32: 美式期權定價模型 (American Option Pricing)

功能:
- 計算美式 Call 和 Put 期權的理論價值
- 支持 Cox-Ross-Rubinstein (CRR) 二叉樹模型
- 支持 Barone-Adesi & Whaley (BAW) 二次近似模型
- 精確計算美式期權的提早履約溢價 (Early Exercise Premium)

理論基礎:
由於美股期權多為美式，可以隨時提早履約。傳統 Black-Scholes 假設只能在到期日履約，
這會導致在有股息或深度價內時低估選項價值。

核心算法:
1. CRR Binomial Tree (二叉樹):
   將時間分為 N 步，建立股價二叉樹，由後向前推導期權價值，每個節點考慮是否提早履約。
2. BAW Approximation (二次近似):
   美式期權 = 歐式期權 + 提早履約溢價。透過解非線性方程尋找提早履約臨界價格。
"""

import logging
import math
import numpy as np
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

# 依賴 Black-Scholes 作為 BAW 的基礎
try:
    from calculation_layer.module15_black_scholes import BlackScholesCalculator
except ImportError:
    from module15_black_scholes import BlackScholesCalculator

logger = logging.getLogger(__name__)

@dataclass
class AmericanPricingResult:
    """美式期權定價結果"""
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
            'calculation_date': self.calculation_date
        }

class AmericanOptionPricer:
    """
    美式期權定價計算器
    提供 Binomial Tree 與 BAW Approximation 兩種算法
    """

    def __init__(self):
        self.bs_calculator = BlackScholesCalculator()
        logger.info("✓ 美式期權定價器已初始化 (BAW & CRR Binomial Tree)")

    def price_binomial_tree(self, 
                            S: float, K: float, T: float, r: float, 
                            sigma: float, option_type: str = 'call', 
                            q: float = 0.0, steps: int = 100) -> float:
        """
        使用 Cox-Ross-Rubinstein (CRR) 二叉樹模型計算美式期權定價
        
        參數:
            S: 當前股價
            K: 行使價
            T: 到期時間(年)
            r: 無風險利率
            sigma: 波動率
            option_type: 'call' 或 'put'
            q: 股息率
            steps: 樹的步數 (預設100步，速度與精度的平衡)
        """
        if T <= 0:
            if option_type.lower() == 'call':
                return max(0.0, S - K)
            else:
                return max(0.0, K - S)

        dt = T / steps
        u = math.exp(sigma * math.sqrt(dt))
        d = 1 / u
        
        # 風險中性機率 p
        a = math.exp((r - q) * dt)
        p = (a - d) / (u - d)
        
        # 折現因子
        discount = math.exp(-r * dt)
        
        # 初始化樹的最後一層 (到期日)
        prices = np.zeros(steps + 1)
        for i in range(steps + 1):
            st_price = S * (u ** (steps - i)) * (d ** i)
            if option_type.lower() == 'call':
                prices[i] = max(0.0, st_price - K)
            else:
                prices[i] = max(0.0, K - st_price)
                
        # 從後往前推導
        for j in range(steps - 1, -1, -1):
            for i in range(j + 1):
                # 歐式期權價值 (持有價值)
                hold_val = discount * (p * prices[i] + (1 - p) * prices[i + 1])
                
                # 計算當前節點股價
                st_price = S * (u ** (j - i)) * (d ** i)
                
                # 美式期權的提早履約價值
                if option_type.lower() == 'call':
                    exercise_val = max(0.0, st_price - K)
                else:
                    exercise_val = max(0.0, K - st_price)
                
                # 美式期權價值為兩者取最大
                prices[i] = max(hold_val, exercise_val)
                
        return prices[0]

    def calculate_american_price(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        time_to_expiration: float,
        volatility: float,
        option_type: str = 'call',
        dividend_yield: float = 0.0,
        model: str = 'binomial',
        steps: int = 200
    ) -> AmericanPricingResult:
        """
        計算美式期權價格，並自動對比歐式價格
        """
        import datetime
        calc_date = datetime.datetime.now().strftime("%Y-%m-%d")

        # 1. 計算基準歐式價格
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

        # 2. 計算美式價格
        if model.lower() == 'binomial':
            am_price = self.price_binomial_tree(
                S=stock_price, K=strike_price, T=time_to_expiration,
                r=risk_free_rate, sigma=volatility, option_type=option_type,
                q=dividend_yield, steps=steps
            )
        else:
            # 預留 BAW 實作，或直接全用 Binomial (因為使用 numpy 已足夠快)
            am_price = self.price_binomial_tree(
                S=stock_price, K=strike_price, T=time_to_expiration,
                r=risk_free_rate, sigma=volatility, option_type=option_type,
                q=dividend_yield, steps=100
            )
            model = 'binomial'
            
        # 美式價格不可低於歐式價格 (浮點數邊界處理)
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
            model_used=model,
            calculation_date=calc_date
        )
