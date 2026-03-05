# services/wolfram_service.py
"""
Wolfram Alpha Service
提供高等數學運算與統計核對，用作 AI 決策的第二層驗證。
"""

import os
import requests
import urllib.parse
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class WolframService:
    def __init__(self):
        load_dotenv()
        self.app_id = os.environ.get("WOLFRAM_APP_ID")
        self.base_url = "http://api.wolframalpha.com/v1/result"
        self.is_configured = bool(self.app_id)
        
        if self.is_configured:
            logger.info("✓ Wolfram Alpha Service 已初始化")
        else:
            logger.warning("! 未找到 WOLFRAM_APP_ID，Wolfram 計算功能已停用")

    def ask(self, query: str) -> str:
        """
        向 Wolfram Alpha 提出簡短型查詢 (Short Answers API)
        常用於快速運算 (ex: 'derivative of x^2', 'Black Scholes call S=100 K=105 T=0.5 r=0.05 v=0.2')
        """
        if not self.is_configured:
            return "Error: Wolfram API not configured."
            
        params = {
            "appid": self.app_id,
            "i": query
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            if response.status_code == 200:
                answer = response.text.strip()
                logger.debug(f"Wolfram 查詢: '{query}' -> '{answer}'")
                return answer
            elif response.status_code == 501:
                return "Wolfram: 無法理解或計算此查詢"
            else:
                return f"Wolfram API Error: HTTP {response.status_code}"
        except Exception as e:
            logger.error(f"Wolfram 查詢失敗: {e}")
            return f"Error: Request failed - {str(e)}"

    def verify_black_scholes(self, S: float, K: float, T: float, r: float, v: float, is_call: bool = True) -> str:
        """
        透過 Wolfram 核對 Black Scholes 計算，用作系統準確度驗證
        """
        opt_type = "call" if is_call else "put"
        query = f"Black Scholes {opt_type} S={S} K={K} T={T} r={r} v={v}"
        return self.ask(query)

    def calculate_probability_above(self, current_price: float, target_price: float, volatility: float, days_to_expiry: int) -> str:
        """
        計算期權在到期日高於 target_price 的機率
        利用正態分佈概率查表
        """
        years = days_to_expiry / 365.0
        # 假設 S 遵循幾何布朗運動
        query = f"probability of standard normal variable > (ln({target_price}/{current_price}) - (0 - 0.5 * {volatility}^2)*{years}) / ({volatility} * sqrt({years}))"
        return self.ask(query)

if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.DEBUG)
    service = WolframService()
    print("Test derivative:", service.ask("derivative of S*N(d1) - K*exp(-rT)*N(d2)"))
