import logging
import requests
import aiohttp
import json
import time
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
    
    CACHE_TTL_SECONDS = 300  # Fix 3: 5分鐘 TTL，日內分析避免返回舊結果
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._cache = {}  # Fix 3: {ticker: (result, timestamp)} 帶時間戳的緩存

    def _is_cache_valid(self, ticker: str) -> bool:
        """Fix 3: 檢查緩存是否在 TTL 內有效"""
        if ticker not in self._cache:
            return False
        _, ts = self._cache[ticker]
        age = time.time() - ts
        if age > self.CACHE_TTL_SECONDS:
            logger.info(f"AI 緩存已過期 ({age:.0f}秒 > {self.CACHE_TTL_SECONDS}秒): {ticker}")
            return False
        return True
        
    def generate_analysis(self, ticker: str, setup_data: Dict[str, Any]) -> str:
        """
        Generate a qualitative analysis report for a given trade setup (Synchronous).
        Fix 3: Uses TTL-aware cache (5 minutes) to avoid stale intraday data.
        """
        if self._is_cache_valid(ticker):
            result, _ = self._cache[ticker]
            logger.info(f"使用緩存的 AI 分析結果: {ticker} (TTL内有效)")
            return result
            
        logger.info(f"正在請求 AI 分析 {ticker} (Sync)...")
        prompt = self._construct_prompt(ticker, setup_data)
        
        try:
            result = self._call_nvidia_api(prompt)
            self._cache[ticker] = (result, time.time())  # Fix 3: 存储结果和时间戳
            return result
        except Exception as e:
            logger.error(f"AI 分析生成失敗: {e}")
            return "無法生成 AI 分析報告 (API Error)"

    async def generate_analysis_async(self, ticker: str, setup_data: Dict[str, Any]) -> str:
        """
        Generate a qualitative analysis report for a given trade setup (Asynchronous).
        Fix 3: Uses TTL-aware cache (5 minutes) to avoid stale intraday data.
        """
        if self._is_cache_valid(ticker):
            result, _ = self._cache[ticker]
            logger.info(f"使用緩存的 AI 分析結果: {ticker} (TTL内有效)")
            return result
            
        logger.info(f"正在請求 AI 分析 {ticker} (Async)...")
        prompt = self._construct_prompt(ticker, setup_data)
        
        try:
            result = await self._call_nvidia_api_async(prompt)
            self._cache[ticker] = (result, time.time())  # Fix 3: 存储结果和时间戳
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
        
        # Fix 9: 日內交易核心數據（優先）
        iv_rank = data.get('module18_historical_volatility', {}).get('iv_rank', None)
        iv_hv_ratio_data = data.get('module18_historical_volatility', {}).get('iv_hv_ratio', None)
        iv_rank_str = f"{iv_rank:.0f}%" if iv_rank is not None else "N/A"
        iv_hv_str = f"{iv_hv_ratio_data:.2f}" if iv_hv_ratio_data is not None else "N/A"

        # Fix 9: 從 module16/20 提取完整 Greeks
        mod16 = data.get('module16_greeks', {})
        delta_v = mod16.get('delta', 'N/A')
        gamma_v = mod16.get('gamma', 'N/A')
        theta_v = mod16.get('theta', 'N/A')
        vega_v  = mod16.get('vega', 'N/A')

        # Fix 9: 基本面僅作次要參考
        fundamental_note = ""
        mod4 = data.get('module4_pe_valuation', {})
        mod2 = data.get('module2_fair_value', {})
        mod1 = data.get('module1_support_resistance', {})
        if mod4: fundamental_note += f"PE {mod4.get('pe_ratio','?')} / 估值 {mod4.get('valuation_status','?')} | "
        if mod2: fundamental_note += f"公允價 ${mod2.get('fair_value',0):.2f} (安全邊際 {mod2.get('margin_of_safety',0):.1f}%) | "
        if mod1: fundamental_note += f"支撐 ${mod1.get('support',0):.2f} / 阻力 ${mod1.get('resistance',0):.2f}"

        prompt = f"""
        你是一位專注於日內期權交易的華爾街資深交易員。請根據以下數據為 {ticker} 提供日內操作建議 (繁體中文)。

        **【日內核心交易參數】**
        - 標的: {ticker} | 策略: {direction}
        - 現價: ${price} | 今日 Gap: {gap_str}
        - 期權: 行權價 {strike}, 到期日 {expiry}
        - 隱含波動率 (IV): {iv_str} | IV Rank: {iv_rank_str} | IV/HV: {iv_hv_str}
        - Greeks: Delta {delta_v}, Gamma {gamma_v}, Theta {theta_v}/日, Vega {vega_v}
        - 盈虧平衡: ${breakeven:.2f} | 槓桿: {leverage:.2f}x | 評分: {score}/100

        **【次要基本面參考（非日內決策依據）】**
        {fundamental_note or '無基本面數據'}

        **【日內分析任務（請依序回答）】**
        1. **今日方向研判**: 根據 Gap、IV Rank、Delta，判斷今日 Bull/Bear/Neutral 並給出置信度 (High/Medium/Low)。
        2. **最佳到期日選擇**: 根據 Theta 衰減和流動性，建議 0DTE / 1DTE / 本週到期 / {expiry}，並解釋原因。
        3. **日內入場條件**: 列出 2-3 個具體的觸發條件（例如：突破某價位、成交量確認、VWAP 關係）。
        4. **止損與目標**: 給出期權多頭的合理止損設定（建議期權損失 ≤ 50%）和獲利目標（至少 2R）。
        5. **風險提示**: 針對此期權的主要風險（Theta 衰減速度、Gap 風險、IV 壓縮可能性）。
        6. **最終評級**: 「強烈做多 (Strong Bull)」/ 「做多 (Bull)」/ 「中性觀望 (Neutral)」/ 「做空 (Bear)」。

        請使用專業術語，語氣客觀，結構清晰。
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
