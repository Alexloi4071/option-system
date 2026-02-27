import logging
import requests
import aiohttp
import json
from typing import Dict, Any, Optional
from config.settings import settings as SETTINGS

logger = logging.getLogger(__name__)

class AIAnalysisService:
    """
    Integration with NVIDIA API (Llama 3.1 405B) for advanced option analysis.
    Generates natural language reports in Traditional Chinese.
    """
    
    API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
    MODEL = "meta/llama-3.1-70b-instruct"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._cache = {} # Simple in-memory cache
        
    def generate_analysis(self, ticker: str, setup_data: Dict[str, Any]) -> str:
        """
        Generate a qualitative analysis report for a given trade setup (Synchronous).
        
        Args:
            ticker: Stock symbol
            setup_data: Dictionary containing setup parameters.
        """
        if ticker in self._cache:
            logger.info(f"使用緩存的 AI 分析結果: {ticker}")
            return self._cache[ticker]
            
        logger.info(f"正在請求 AI 分析 {ticker} (Sync)...")
        
        prompt = self._construct_prompt(ticker, setup_data)
        
        try:
            result = self._call_nvidia_api(prompt)
            self._cache[ticker] = result # Cache the result
            return result
        except Exception as e:
            logger.error(f"AI 分析生成失敗: {e}")
            return "無法生成 AI 分析報告 (API Error)"

    async def generate_analysis_async(self, ticker: str, setup_data: Dict[str, Any]) -> str:
        """
        Generate a qualitative analysis report for a given trade setup (Asynchronous).
        
        Args:
            ticker: Stock symbol
            setup_data: Dictionary containing setup parameters.
        """
        if ticker in self._cache:
            logger.info(f"使用緩存的 AI 分析結果: {ticker}")
            return self._cache[ticker]
            
        logger.info(f"正在請求 AI 分析 {ticker} (Async)...")
        
        prompt = self._construct_prompt(ticker, setup_data)
        
        try:
            result = await self._call_nvidia_api_async(prompt)
            self._cache[ticker] = result # Cache the result
            return result
        except Exception as e:
            logger.error(f"AI 分析生成失敗 (Async): {e}")
            return "無法生成 AI 分析報告 (API Error)"

    def _construct_prompt(self, ticker: str, data: Dict) -> str:
        """Construct the prompt for the Llama model."""
        
        # 1. Determine Data Source (Deep Analysis vs Basic Scanner)
        scanner_context = data.get('scanner_context', data) # Fallback to data if no context key
        
        # Basic Scanner Info
        direction = "看漲 (Long Call)" if "CALL" in scanner_context.get('strategy', '') else "看跌 (Long Put)"
        if "SHORT_CALL" in scanner_context.get('strategy', ''): direction = "看跌/中性 (Short Call)"
        if "SHORT_PUT" in scanner_context.get('strategy', ''): direction = "看漲/中性 (Short Put)"
        
        price = scanner_context.get('price', 0)
        gap = scanner_context.get('gap', 0) 
        score = scanner_context.get('score', 0)
        strike = scanner_context.get('strike')
        expiry = scanner_context.get('expiry')
        
        # Extract basic metrics
        analysis = scanner_context.get('analysis', {})
        input_data = analysis.get('input', {})
        
        gap = scanner_context.get('gap')
        if gap is None: gap = input_data.get('gap_percent', 0)
        gap_str = f"{gap:.2f}%" if gap is not None else "N/A"
        
        iv = input_data.get('iv')
        # If IV missing in scanner context, try deep analysis module 17 or 16
        if iv is None:
             # Try Module 16 (Greeks) or 17 (IV)
             mod17 = data.get('module17_implied_volatility', {})
             iv = mod17.get('average_iv')
        iv_str = f"{iv*100:.1f}%" if iv is not None else "N/A"
        
        breakeven_data = analysis.get('breakeven', {})
        breakeven = breakeven_data.get('price', 0)
        
        leverage_data = analysis.get('leverage', {})
        leverage = leverage_data.get('effective_leverage', 0)
        
        # 2. Extract Deep Analysis Metrics (If available)
        deep_metrics = ""
        
        # Module 4: PE Valuation
        mod4 = data.get('module4_pe_valuation', {})
        if mod4:
            pe = mod4.get('pe_ratio', 'N/A')
            fair_pe = mod4.get('fair_value_pe', 'N/A')
            valuation = mod4.get('valuation_status', 'Unknown')
            deep_metrics += f"- PE 估值: 當前 PE {pe}, 合理價 ${fair_pe} ({valuation})\n"
            
        # Module 2: Fair Value
        mod2 = data.get('module2_fair_value', {})
        if mod2:
            fv = mod2.get('fair_value', 0)
            margin = mod2.get('margin_of_safety', 0)
            deep_metrics += f"- 公允價值: ${fv:.2f} (安全邊際 {margin:.1f}%)\n"
            
        # Module 1: Support/Resistance
        mod1 = data.get('module1_support_resistance', {})
        if mod1:
            sup = mod1.get('support', 0)
            res = mod1.get('resistance', 0)
            deep_metrics += f"- 關鍵點位: 支撐 ${sup:.2f} / 阻力 ${res:.2f}\n"
            
        # Module 16: Greeks
        mod16 = data.get('module16_greeks', {})
        if mod16:
            delta = mod16.get('delta', 'N/A')
            gamma = mod16.get('gamma', 'N/A')
            theta = mod16.get('theta', 'N/A')
            deep_metrics += f"- Greeks: Delta {delta}, Gamma {gamma}, Theta {theta}\n"

        prompt = f"""
        你是一位華爾街資深期權交易員和風險分析師。請根據以下全面數據，為 {ticker} 的交易機會撰寫一份深度分析報告 (繁體中文)。
        
        **交易設置 (由掃描器發現):**
        - 標的: {ticker}
        - 策略方向: {direction}
        - 現價: ${price} (Gap: {gap_str})
        - 評分: {score}/100
        - 期權: 行權價 {strike}, 到期日 {expiry}
        - 隱含波動率 (IV): {iv_str}
        - 盈虧平衡點: ${breakeven:.2f}
        - 槓桿比率: {leverage:.2f}x
        
        **深度基本面與技術面數據 (32個模塊分析結果):**
        {deep_metrics or "無深度數據，僅基於掃描結果分析。"}
        
        **任務:**
        1. **基本面研判**: 基於 PE 和公允價值，判斷當前股價是否被低估或高估。
        2. **風險回報分析**: 結合 IV、Greeks 和槓桿，評估此期權策略的勝率與風險。
        3. **技術操作建議**: 參考支撐/阻力位，給出具體的入場、止損和獲利目標價位。
        4. **總結**: 給出 "強烈看漲 (Strong Bullish)", "看漲 (Bullish)", "中性 (Neutral)" 或 "看跌 (Bearish)" 的最終評級。
        
        請使用專業術語，語氣客觀，結構清晰，並用繁體中文輸出。
        """
        return prompt

    def _call_nvidia_api(self, prompt: str) -> str:
        """Make the HTTP request to NVIDIA API (Synchronous)."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.MODEL,
            "messages": [
                {"role": "system", "content": "You are an expert financial analyst. Output in Traditional Chinese (繁體中文)."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5,
            "max_tokens": 800 # Increased for deeper analysis
        }
        
        # Increased timeout to 60s to prevent ReadTimeoutError
        response = requests.post(self.API_URL, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            logger.error(f"NVIDIA API Error: Status {response.status_code}, Body: {response.text}")
            raise Exception(f"Status {response.status_code}: {response.text}")

    async def _call_nvidia_api_async(self, prompt: str) -> str:
        """Make the HTTP request to NVIDIA API (Asynchronous)."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.MODEL,
            "messages": [
                {"role": "system", "content": "You are an expert financial analyst. Output in Traditional Chinese (繁體中文)."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5,
            "max_tokens": 800
        }
        
        # Increased timeout to 60s
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(self.API_URL, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['choices'][0]['message']['content']
                else:
                    error_text = await response.text()
                    logger.error(f"NVIDIA API Error (Async): Status {response.status}, Body: {error_text}")
                    raise Exception(f"Status {response.status}: {error_text}")

# Helper to get instance
_instance = None
def get_ai_service(api_key: str = None) -> AIAnalysisService:
    global _instance
    if not _instance:
        # Use provided key or fetch from settings/env
        key = api_key or getattr(SETTINGS, 'NVIDIA_API_KEY', None)
        
        if not key:
             # Fallback to the one user provided in chat (NOT RECOMMENDED for prod, but for this task)
             # NOTE: This key is illustrative. Ideally user should set it in .env
             key = "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"
             logger.warning("Using fallback NVIDIA API Key. Please configure NVIDIA_API_KEY in .env")
             
        _instance = AIAnalysisService(key)
    return _instance
