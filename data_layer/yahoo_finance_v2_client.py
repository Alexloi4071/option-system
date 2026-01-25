#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Yahoo Finance API 客户端（優化版，支持 Crumb 驗證）
使用公开的 Yahoo Finance API

優化功能:
- CrumbManager: 多種 Crumb 獲取方法，自動過期檢測和刷新
- UserAgentRotator: 每次請求使用不同的 User-Agent
- RetryHandler: 智能重試邏輯（429/401/5xx 錯誤處理）
"""

import time
import logging
import re
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter

# 導入優化工具
from .utils.user_agent_rotator import UserAgentRotator
from .utils.retry_handler import RetryHandler, RetryConfig
from .utils import ConnectionConfig, YAHOO_CONNECTION_CONFIG

# 配置日志
logger = logging.getLogger(__name__)


class CrumbManager:
    """
    Yahoo Finance Crumb 管理器
    
    提供多種 Crumb 獲取方法，支持自動過期檢測和刷新。
    
    Crumb 獲取方法:
    1. 直接 API 獲取 (/v1/test/getcrumb)
    2. 從頁面提取 (finance.yahoo.com/quote/AAPL)
    3. 從 consent 頁面獲取
    
    Requirements: 2.1, 2.2, 2.3
    """
    
    # Crumb 有效期（默認 5 分鐘 - 避免 429 錯誤）
    CRUMB_TTL_MINUTES = 5
    
    def __init__(self, session: requests.Session, ua_rotator: UserAgentRotator):
        """
        初始化 Crumb 管理器
        
        參數:
            session: requests.Session 實例（用於保持 cookies）
            ua_rotator: UserAgentRotator 實例
        """
        self.session = session
        self.ua_rotator = ua_rotator
        self._crumb: Optional[str] = None
        self._crumb_timestamp: Optional[datetime] = None
        self._consecutive_failures = 0
        
        logger.debug("CrumbManager 初始化完成")
    
    @property
    def crumb(self) -> Optional[str]:
        """獲取當前 Crumb（如果過期則返回 None）"""
        if self._is_crumb_expired():
            return None
        return self._crumb
    
    def _is_crumb_expired(self) -> bool:
        """檢查 Crumb 是否過期"""
        if self._crumb is None or self._crumb_timestamp is None:
            return True
        
        elapsed = datetime.now() - self._crumb_timestamp
        return elapsed > timedelta(minutes=self.CRUMB_TTL_MINUTES)
    
    def get_crumb(self, force_refresh: bool = False) -> Optional[str]:
        """
        獲取有效的 Crumb
        
        參數:
            force_refresh: 是否強制刷新（忽略緩存）
        
        返回:
            str: 有效的 Crumb，或 None（如果所有方法都失敗）
        """
        # 如果有有效的緩存 Crumb，直接返回
        if not force_refresh and not self._is_crumb_expired():
            logger.debug(f"使用緩存的 Crumb")
            return self._crumb
        
        logger.info("正在獲取新的 Crumb...")
        
        # 依次嘗試三種方法
        methods = [
            ("API 直接獲取", self._get_crumb_from_api),
            ("頁面提取", self._get_crumb_from_page),
            ("Consent 頁面", self._get_crumb_from_consent),
        ]
        
        for method_name, method_func in methods:
            try:
                crumb = method_func()
                if crumb and self._validate_crumb(crumb):
                    self._crumb = crumb
                    self._crumb_timestamp = datetime.now()
                    self._consecutive_failures = 0
                    logger.info(f"* Crumb 獲取成功（方法: {method_name}）")
                    return crumb
                else:
                    logger.debug(f"  {method_name}: 無效或空")
            except Exception as e:
                logger.debug(f"  {method_name} 失敗: {e}")
        
        # 所有方法都失敗
        self._consecutive_failures += 1
        logger.warning(f"! 所有 Crumb 獲取方法都失敗（連續失敗: {self._consecutive_failures}）")
        return None
    
    def _get_browser_headers(self) -> Dict[str, str]:
        """
        獲取模擬瀏覽器的完整 headers
        
        根據 Stack Overflow 討論，完整的瀏覽器 headers 是避免 429 的關鍵
        """
        return {
            'User-Agent': self.ua_rotator.get_next(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://finance.yahoo.com/',
            'Origin': 'https://finance.yahoo.com',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def _get_crumb_from_api(self) -> Optional[str]:
        """方法 1: 從 API 直接獲取 Crumb"""
        # 使用完整的瀏覽器 headers
        headers = self._get_browser_headers()
        
        # 先訪問主頁獲取 cookies
        self.session.get(
            'https://finance.yahoo.com',
            headers=headers,
            timeout=15
        )
        
        # 短暫延遲，模擬真實用戶行為
        time.sleep(1)
        
        # 獲取 crumb（使用 API headers）
        api_headers = headers.copy()
        api_headers['Sec-Fetch-Dest'] = 'empty'
        api_headers['Sec-Fetch-Mode'] = 'cors'
        api_headers['Sec-Fetch-Site'] = 'same-site'
        
        crumb_url = 'https://query1.finance.yahoo.com/v1/test/getcrumb'
        # 備用 crumb URL（如果第一個失效）
        backup_crumb_url = 'https://query2.finance.yahoo.com/v1/test/getcrumb'
        
        # 先嘗試第一個 URL
        response = self.session.get(crumb_url, headers=api_headers, timeout=15)
        
        if response.status_code == 200:
            crumb = response.text.strip()
            if crumb and len(crumb) > 5:  # 確保 crumb 不為空且有足夠長度
                logger.info(f"✓ Crumb 獲取成功（主URL）: {crumb[:10]}...")
                return crumb
            else:
                logger.warning("  主URL 返回空 crumb，嘗試備用URL")
        
        # 嘗試備用 URL
        logger.info("  嘗試備用 crumb URL...")
        response = self.session.get(backup_crumb_url, headers=api_headers, timeout=15)
        
        if response.status_code == 200:
            crumb = response.text.strip()
            if crumb and len(crumb) > 5:
                logger.info(f"✓ Crumb 獲取成功（備用URL）: {crumb[:10]}...")
                return crumb
            else:
                logger.warning("  備用URL 也返回空 crumb")
        
        logger.error("  無法獲取有效 crumb")
        return None
    
    def _get_crumb_from_page(self) -> Optional[str]:
        """方法 2: 從股票頁面提取 Crumb"""
        headers = self._get_browser_headers()
        
        quote_url = 'https://finance.yahoo.com/quote/AAPL'
        response = self.session.get(quote_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            # 嘗試多種正則模式
            patterns = [
                r'"crumb":"([^"]+)"',
                r'"CrumbStore":\{"crumb":"([^"]+)"\}',
                r'crumb=([a-zA-Z0-9]+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response.text)
                if match:
                    return match.group(1)
        
        return None
    
    def _get_crumb_from_consent(self) -> Optional[str]:
        """方法 3: 從 consent 頁面獲取 Crumb"""
        headers = self._get_browser_headers()
        
        # 訪問 consent 頁面
        consent_url = 'https://consent.yahoo.com/v2/collectConsent'
        
        try:
            response = self.session.get(
                'https://finance.yahoo.com',
                headers=headers,
                timeout=10,
                allow_redirects=True
            )
            
            # 如果被重定向到 consent 頁面，嘗試處理
            if 'consent.yahoo.com' in response.url:
                # 提交 consent 表單
                form_data = {
                    'agree': 'agree',
                    'consentCollectionStep': 'ACCEPT_ALL'
                }
                self.session.post(consent_url, data=form_data, headers=headers, timeout=10)
            
            # 再次嘗試從 API 獲取
            return self._get_crumb_from_api()
            
        except Exception as e:
            logger.debug(f"Consent 處理失敗: {e}")
            return None
    
    def _validate_crumb(self, crumb: str) -> bool:
        """驗證 Crumb 是否有效"""
        if not crumb:
            return False
        
        # Crumb 不應該是錯誤信息
        invalid_patterns = ['{', 'error', 'Error', '<', '>']
        for pattern in invalid_patterns:
            if pattern in crumb:
                return False
        
        # Crumb 長度通常在 10-50 字符之間
        if len(crumb) < 5 or len(crumb) > 100:
            return False
        
        return True
    
    def invalidate(self) -> None:
        """使當前 Crumb 失效（強制下次重新獲取）"""
        self._crumb = None
        self._crumb_timestamp = None
        logger.debug("Crumb 已失效")
    
    def get_stats(self) -> dict:
        """獲取 Crumb 管理器統計"""
        return {
            'has_crumb': self._crumb is not None,
            'is_expired': self._is_crumb_expired(),
            'consecutive_failures': self._consecutive_failures,
            'crumb_age_minutes': (
                (datetime.now() - self._crumb_timestamp).total_seconds() / 60
                if self._crumb_timestamp else None
            )
        }


class YahooFinanceV2Client:
    """
    Yahoo Finance API 客户端（優化版，支持 Crumb 驗證）
    
    優化功能:
    - CrumbManager: 多種 Crumb 獲取方法，自動過期檢測和刷新
    - UserAgentRotator: 每次請求使用不同的 User-Agent
    - RetryHandler: 智能重試邏輯（429/401/5xx 錯誤處理）
    
    Requirements: 2.1-2.4, 3.1-3.4
    """
    
    # Yahoo Finance API 端点
    API_BASE_URL = 'https://query1.finance.yahoo.com'
    API_BASE_URL_V2 = 'https://query2.finance.yahoo.com'
    CHART_ENDPOINT = '/v8/finance/chart'
    OPTIONS_ENDPOINT = '/v7/finance/options'
    CRUMB_URL = 'https://fc.yahoo.com'
    
    def __init__(
        self, 
        request_delay: float = 5.0,  # 增加默認延遲到 5 秒，Yahoo Finance 對連續請求非常敏感
        max_retries: int = 3,
        user_agent: Optional[str] = None,
        ua_rotator: Optional[UserAgentRotator] = None,
        retry_handler: Optional[RetryHandler] = None,
        connection_config: Optional[ConnectionConfig] = None
    ):
        """
        初始化客户端
        
        Args:
            request_delay: 请求间隔（秒），默认 2.0（增加以避免 429 錯誤）
            max_retries: 最大重试次数，默认 3
            user_agent: 自定义 User-Agent（已棄用，使用 ua_rotator）
            ua_rotator: User-Agent 輪換器（可選，默認創建新實例）
            retry_handler: 重試處理器（可選，默認創建新實例）
            connection_config: 連接配置（可選，默認使用 YAHOO_CONNECTION_CONFIG）
        """
        self.request_delay = request_delay
        self.max_retries = max_retries
        self.last_request_time = 0
        
        # 連接配置
        self.connection_config = connection_config or YAHOO_CONNECTION_CONFIG
        
        # 创建 Session 以保持 cookies（配置連接池）
        self.session = requests.Session()
        
        # 配置連接適配器（連接池復用）
        adapter = HTTPAdapter(
            pool_connections=self.connection_config.pool_connections,
            pool_maxsize=self.connection_config.pool_maxsize,
            max_retries=0  # 我們使用自己的重試邏輯
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # 會話創建時間（用於過期檢測）
        self._session_created_at = datetime.now()
        
        # 初始化 User-Agent 輪換器
        self.ua_rotator = ua_rotator or UserAgentRotator()
        
        # 初始化重試處理器（針對 Yahoo Finance 優化）
        if retry_handler:
            self.retry_handler = retry_handler
        else:
            retry_config = RetryConfig(
                max_retries=max_retries,
                initial_delay=2.0,
                max_delay=120.0,
                exponential_base=2.0,
                jitter=True,
                retryable_status_codes=[429, 500, 502, 503, 504]
            )
            self.retry_handler = RetryHandler(retry_config)
        
        # 设置初始 User-Agent 和關鍵 Headers
        # 根據 Stack Overflow 討論，Referer 和 Origin 是避免 429 的關鍵
        # https://stackoverflow.com/questions/78111453/yahoo-finance-api-file-get-contents-429-too-many-requests
        current_ua = user_agent or self.ua_rotator.get_next()
        self.headers = {
            'User-Agent': current_ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            # 關鍵 Headers - 避免 429 錯誤
            'Referer': 'https://finance.yahoo.com/',
            'Origin': 'https://finance.yahoo.com',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
        }
        self.session.headers.update(self.headers)
        
        # 初始化 Crumb 管理器
        self.crumb_manager = CrumbManager(self.session, self.ua_rotator)
        
        # 兼容舊代碼的 crumb 屬性
        self.cookies = None
        
        # 初始化時獲取 crumb
        self._init_crumb()
        
        logger.info(f"Yahoo Finance 客户端已初始化（優化版）")
        logger.debug(f"  User-Agent 輪換器: {len(self.ua_rotator)} 個 UA")
        logger.debug(f"  重試配置: max_retries={max_retries}")
    
    @property
    def crumb(self) -> Optional[str]:
        """獲取當前 Crumb（兼容舊代碼）"""
        return self.crumb_manager.crumb
    
    def _init_crumb(self):
        """初始化 Crumb 驗證（使用 CrumbManager）"""
        crumb = self.crumb_manager.get_crumb()
        if crumb:
            logger.info(f"* 成功獲取 Yahoo Finance Crumb")
        else:
            logger.warning("! 無法獲取 Crumb，將使用無 Crumb 模式")
    
    def _rotate_user_agent(self) -> str:
        """輪換 User-Agent 並更新 headers"""
        new_ua = self.ua_rotator.get_next()
        self.headers['User-Agent'] = new_ua
        self.session.headers['User-Agent'] = new_ua
        return new_ua
    
    def _get_default_user_agent(self) -> str:
        """获取默认 User-Agent (2024年12月最新版本)"""
        return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    
    def _rate_limit_delay(self) -> None:
        """
        请求速率限制（帶隨機抖動）
        
        添加隨機延遲可以避免被識別為爬蟲，因為真實用戶的請求間隔是不規則的。
        這是避免 Yahoo Finance 429 錯誤的關鍵策略之一。
        """
        import random
        
        elapsed = time.time() - self.last_request_time
        
        # 基礎延遲 + 隨機抖動 (0-50% 的額外延遲)
        jitter = random.uniform(0, self.request_delay * 0.5)
        total_delay = self.request_delay + jitter
        
        if elapsed < total_delay:
            sleep_time = total_delay - elapsed
            logger.debug(f"速率限制: 等待 {sleep_time:.2f}s (基礎={self.request_delay}s, 抖動={jitter:.2f}s)")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _refresh_session(self) -> None:
        """
        刷新 Session（清除 cookies 並重新建立連接）
        
        Requirements: 2.1
        """
        logger.info("刷新 Session...")
        
        try:
            # 關閉舊的 session
            self.session.close()
            
            # 創建全新的 session（徹底清除所有 cookies）
            self.session = requests.Session()
            
            # 清除所有可能的 cookies
            self.session.cookies.clear()
            
            # 重新配置連接池
            adapter = HTTPAdapter(
                pool_connections=self.connection_config.pool_connections,
                pool_maxsize=self.connection_config.pool_maxsize,
                max_retries=self.connection_config.max_retries
            )
            self.session.mount('http://', adapter)
            self.session.mount('https://', adapter)
            
            # 重新設置 headers（使用默認 User-Agent）
            self.session.headers.update(self.headers)
            
            # 設置額外的反追蹤 headers
            self.session.headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0'
            })
            
            # 更新 CrumbManager 的 session 引用
            self.crumb_manager.session = self.session
            
            # 重置時間戳
            self._session_created_at = datetime.now()
            
            # 等待一小段時間避免立即請求
            time.sleep(2)
            
            # 立即獲取新的 Crumb
            # self.crumb_manager.get_crumb()  # 暫時禁用
            
            logger.info("* Session 已刷新（清除所有 cookies 和追蹤信息）")
            
        except Exception as e:
            logger.error(f"Session 刷新失敗: {e}")
            raise
        
    def _handle_429_error(self, url: str) -> None:
        """處理 429 錯誤的專用方法"""
        logger.error("x HTTP Error 429 - Too Many Requests")
        logger.error("  立即刷新 session 以清除追蹤信息")
        
        # 強制刷新 session
        self._refresh_session()
        
        # 等待更長時間
        time.sleep(15)
        
        logger.info("  Session 已刷新，可以重試請求")
    
    def _make_request(self, endpoint: str, params: dict = None, retry_count: int = 0, use_v2: bool = True) -> dict:
        """
        發送 HTTP 請求並處理錯誤
        
        Args:
            endpoint: API 端點
            params: 請求參數
            retry_count: 重試次數
            use_v2: 是否使用 V2 API
        
        Returns:
            dict: 響應數據
        """
        start_time = time.time()
        
        try:
            # 設置請求間隔以避免 429
            elapsed = time.time() - getattr(self, '_last_request_time', 0)
            if elapsed < 8.0:  # 8秒間隔
                wait_time = 8.0 - elapsed
                logger.info(f"  等待 {wait_time:.1f} 秒避免 429 錯誤...")
                time.sleep(wait_time)
            
            self._last_request_time = time.time()
            
            # 添加 crumb 到參數（所有 V1/V2 API 都需要）
            if hasattr(self, 'crumb_manager'):
                crumb = self.crumb_manager.get_crumb()
                if crumb:
                    if not params:
                        params = {}
                    params['crumb'] = crumb
                    logger.info(f"  使用 crumb: {crumb[:10]}...")
                else:
                    logger.warning("  Crumb 為空，可能導致 401 錯誤")
            
            # 確保 params 不為 None
            if params is None:
                params = {}
            
            logger.info(f"Requesting {endpoint} (attempt {retry_count + 1})")
            
            response = self.session.get(
                endpoint,
                params=params,
                timeout=self.connection_config.timeout
            )
            
            # 處理 429 錯誤
            if response.status_code == 429:
                logger.error(f"x HTTP 429 - Too Many Requests: {endpoint}")
                if retry_count < 2:  # 最多重試 2 次
                    self._handle_429_error(endpoint)
                    return self._make_request(endpoint, params, retry_count + 1, use_v2)
                else:
                    logger.error("x 已達到最大重試次數，放棄請求")
                    raise Exception("429 錯誤重試失敗")
            
            # 處理其他 HTTP 錯誤
            response.raise_for_status()
            
            # 解析 JSON 響應
            data = response.json()
            
            logger.info(f"✓ 請求成功: {endpoint}")
            return data
            
        except requests.exceptions.Timeout as e:
            elapsed = time.time() - start_time
            logger.error(f"x Request timeout after {elapsed:.2f}s - URL: {endpoint}")
            if retry_count < 2:
                time.sleep(5)
                return self._make_request(endpoint, params, retry_count + 1, use_v2)
            raise
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"x Connection error - URL: {endpoint}")
            if retry_count < 2:
                time.sleep(5)
                return self._make_request(endpoint, params, retry_count + 1, use_v2)
            raise
            
        except requests.exceptions.RequestException as e:
            logger.error(f"x Network error - URL: {endpoint}")
            raise
            
        except Exception as e:
            logger.error(f"x Unexpected error - URL: {endpoint}: {e}")
            raise
    
    # ==================== 股票数据 API ====================
    
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        获取股票报价
        
        Args:
            symbol: 股票代码
        
        Returns:
            dict: 报价数据
        """
        # 使用 chart API 获取报价数据
        endpoint = f"{self.API_BASE_URL_V2}{self.CHART_ENDPOINT}/{symbol}"
        params = {
            'interval': '1d',
            'range': '1d'
        }
        
        return self._make_request(endpoint, params)
    
    def get_historical_data(
        self, 
        symbol: str, 
        interval: str = '1d',
        period: str = '1mo'
    ) -> Dict[str, Any]:
        """
        获取历史数据
        
        Args:
            symbol: 股票代码
            interval: 时间间隔（1m, 5m, 1d, 1wk, 1mo）
            period: 时间范围（1d, 5d, 1mo, 3mo, 1y）
        
        Returns:
            dict: 历史数据
        """
        endpoint = f"{self.API_BASE_URL_V2}{self.CHART_ENDPOINT}/{symbol}"
        params = {
            'interval': interval,
            'range': period
        }
        
        return self._make_request(endpoint, params)
    
    def get_option_chain(
        self, 
        symbol: str, 
        expiration: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取期权链
        
        Args:
            symbol: 股票代码
            expiration: 到期日（可选，格式 YYYY-MM-DD 或 Unix timestamp）
        
        Returns:
            dict: 期权链数据
        """
        endpoint = f"{self.API_BASE_URL}{self.OPTIONS_ENDPOINT}/{symbol}"
        params = {}
        
        # 將日期轉換為 Unix 時間戳
        if expiration:
            # 如果已經是數字（timestamp），直接使用
            if isinstance(expiration, (int, float)):
                params['date'] = int(expiration)
            elif expiration.isdigit():
                params['date'] = int(expiration)
            else:
                try:
                    from datetime import datetime
                    import calendar
                    # 解析日期
                    exp_date = datetime.strptime(expiration, '%Y-%m-%d')
                    # 使用 UTC 時間戳（避免時區問題）
                    timestamp = calendar.timegm(exp_date.timetuple())
                    params['date'] = timestamp
                    logger.debug(f"期權到期日: {expiration} -> Unix timestamp: {timestamp}")
                except ValueError:
                    # 如果解析失敗，直接使用原始值
                    params['date'] = expiration
        
        return self._make_request(endpoint, params)
    
    def get_available_expirations(self, symbol: str) -> list:
        """
        獲取可用的期權到期日列表
        
        Args:
            symbol: 股票代碼
        
        Returns:
            list: 可用的到期日列表（Unix timestamp）
        """
        try:
            endpoint = f"{self.API_BASE_URL}{self.OPTIONS_ENDPOINT}/{symbol}"
            response = self._make_request(endpoint, {})
            
            if not response:
                return []
            
            option_chain = response.get('optionChain', {})
            result = option_chain.get('result', [])
            
            if not result:
                return []
            
            expirations = result[0].get('expirationDates', [])
            logger.info(f"* 獲取 {symbol} 可用到期日: {len(expirations)} 個")
            
            return expirations
            
        except Exception as e:
            logger.error(f"x 獲取 {symbol} 到期日列表失敗: {e}")
            return []



class YahooDataParser:
    """
    Yahoo Finance 数据解析器
    
    提供統一的接口解析 Yahoo Finance API 的各種響應格式。
    所有解析方法都返回標準化的數據結構，便於系統其他部分使用。
    """
    
    @staticmethod
    def parse_quote(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        解析股票报价响应
        
        Args:
            response: Yahoo Finance Chart API 原始響應
        
        Returns:
            標準化的股票數據字典，包含以下字段：
            - symbol: 股票代碼
            - current_price: 當前價格
            - open: 開盤價
            - high: 最高價
            - low: 最低價
            - volume: 成交量
            - previous_close: 前收盤價
            - market_cap: 市值（Chart API 不提供，返回 0）
            - pe_ratio: 市盈率（Chart API 不提供，返回 0）
            - dividend_rate: 股息率（Chart API 不提供，返回 0）
            - eps: 每股收益（Chart API 不提供，返回 0）
            - fifty_two_week_high: 52週最高價（Chart API 不提供，返回 0）
            - fifty_two_week_low: 52週最低價（Chart API 不提供，返回 0）
            - beta: Beta 係數（Chart API 不提供，返回 0）
            - company_name: 公司名稱（Chart API 不提供，返回空字符串）
            - sector: 行業（Chart API 不提供，返回空字符串）
            - industry: 子行業（Chart API 不提供，返回空字符串）
            - data_source: 數據來源標記 ('yahoo_finance')
            
            解析失敗返回 None
            
        Note:
            Chart API 主要提供價格數據，不包含基本面數據。
            如需完整的基本面數據，應使用 quoteSummary API 或降級到其他數據源。
        """
        try:
            # 驗證響應結構
            if not response or not isinstance(response, dict):
                logger.error("x Invalid response: not a dict")
                return None
            
            chart = response.get('chart', {})
            if not chart:
                logger.error("x Missing 'chart' key in response")
                return None
            
            result = chart.get('result', [])
            if not result or len(result) == 0:
                logger.error("x Empty result in quote response")
                return None
            
            data = result[0]
            meta = data.get('meta', {})
            
            if not meta:
                logger.warning("! Missing 'meta' in response, using empty dict")
            
            # 提取價格數據
            parsed_data = {
                'symbol': meta.get('symbol', ''),
                'current_price': meta.get('regularMarketPrice', 0),
                'open': meta.get('regularMarketOpen', 0),
                'high': meta.get('regularMarketDayHigh', 0),
                'low': meta.get('regularMarketDayLow', 0),
                'volume': meta.get('regularMarketVolume', 0),
                'previous_close': meta.get('previousClose', 0),
                # Chart API 不提供的字段（使用默認值）
                'market_cap': 0,
                'pe_ratio': 0,
                'dividend_rate': 0,
                'eps': 0,
                'fifty_two_week_high': 0,
                'fifty_two_week_low': 0,
                'beta': 0,
                'company_name': '',
                'sector': '',
                'industry': '',
                'data_source': 'yahoo_finance'
            }
            
            # 驗證關鍵字段
            if not parsed_data['symbol']:
                logger.warning("! Missing symbol in parsed data")
            
            if parsed_data['current_price'] == 0:
                logger.warning("! Current price is 0, data may be incomplete")
            
            logger.debug(f"* Successfully parsed quote for {parsed_data['symbol']}")
            return parsed_data
            
        except KeyError as e:
            logger.error(f"x Missing required key in response: {e}")
            return None
        except TypeError as e:
            logger.error(f"x Type error while parsing quote: {e}")
            return None
        except Exception as e:
            logger.error(f"x Unexpected error parsing quote response: {e}")
            logger.debug(f"Response structure: {response}")
            return None
    
    @staticmethod
    def parse_option_chain(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        解析期权链响应
        
        Args:
            response: Yahoo Finance Options API 原始響應
        
        Returns:
            標準化的期權數據字典，包含以下字段：
            - calls: Call 期權列表（list of dict）
            - puts: Put 期權列表（list of dict）
            - expiration: 到期日期（Unix timestamp 或日期字符串）
            - data_source: 數據來源標記 ('yahoo_finance')
            
            每個期權包含：
            - contractSymbol: 合約代碼
            - strike: 行使價
            - lastPrice: 最新價格
            - bid: 買價
            - ask: 賣價
            - volume: 成交量
            - openInterest: 未平倉量
            - impliedVolatility: 隱含波動率
            
            解析失敗返回 None
        """
        try:
            # 驗證響應結構
            if not response or not isinstance(response, dict):
                logger.error("x Invalid response: not a dict")
                return None
            
            option_chain = response.get('optionChain', {})
            if not option_chain:
                logger.error("x Missing 'optionChain' key in response")
                return None
            
            result = option_chain.get('result', [])
            if not result or len(result) == 0:
                logger.error("x Empty result in option chain response")
                return None
            
            data = result[0]
            
            # 調試：顯示數據結構
            logger.debug(f"  期權數據鍵: {list(data.keys())}")
            
            options = data.get('options', [])
            
            if not options or len(options) == 0:
                # 嘗試直接從 data 獲取 calls 和 puts
                calls = data.get('calls', [])
                puts = data.get('puts', [])
                
                if calls or puts:
                    logger.debug(f"  從 data 直接獲取: {len(calls)} calls, {len(puts)} puts")
                    return {
                        'calls': calls,
                        'puts': puts,
                        'expiration': data.get('expirationDate', ''),
                        'data_source': 'yahoo_finance'
                    }
                
                logger.error("x No options data in response")
                logger.debug(f"  data 結構: {list(data.keys())}")
                return None
            
            option_data = options[0]
            
            # 提取 calls 和 puts
            calls = option_data.get('calls', [])
            puts = option_data.get('puts', [])
            
            if not calls and not puts:
                logger.warning("! Both calls and puts are empty")
            
            parsed_data = {
                'calls': calls,
                'puts': puts,
                'expiration': option_data.get('expirationDate', ''),
                'data_source': 'yahoo_finance'
            }
            
            logger.debug(
                f"* Successfully parsed option chain: "
                f"{len(calls)} calls, {len(puts)} puts"
            )
            return parsed_data
            
        except KeyError as e:
            logger.error(f"x Missing required key in response: {e}")
            return None
        except TypeError as e:
            logger.error(f"x Type error while parsing option chain: {e}")
            return None
        except Exception as e:
            logger.error(f"x Unexpected error parsing option chain response: {e}")
            logger.debug(f"Response structure: {response}")
            return None
    
    @staticmethod
    def parse_historical_data(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        解析历史数据响应
        
        Args:
            response: Yahoo Finance Chart API 原始響應
        
        Returns:
            歷史數據字典，包含以下字段：
            - timestamps: Unix 時間戳列表
            - open: 開盤價列表
            - high: 最高價列表
            - low: 最低價列表
            - close: 收盤價列表
            - volume: 成交量列表
            - data_source: 數據來源標記 ('yahoo_finance')
            
            所有列表長度相同，對應同一時間序列。
            解析失敗返回 None
            
        Note:
            可以使用 pandas.DataFrame 將數據轉換為表格格式：
            ```python
            import pandas as pd
            df = pd.DataFrame(parsed_data)
            df['date'] = pd.to_datetime(df['timestamps'], unit='s')
            ```
        """
        try:
            # 驗證響應結構
            if not response or not isinstance(response, dict):
                logger.error("x Invalid response: not a dict")
                return None
            
            chart = response.get('chart', {})
            if not chart:
                logger.error("x Missing 'chart' key in response")
                return None
            
            result = chart.get('result', [])
            if not result or len(result) == 0:
                logger.error("x Empty result in historical data response")
                return None
            
            data = result[0]
            timestamps = data.get('timestamp', [])
            
            if not timestamps:
                logger.error("x No timestamps in historical data")
                return None
            
            indicators = data.get('indicators', {})
            if not indicators:
                logger.error("x Missing 'indicators' in response")
                return None
            
            quote_list = indicators.get('quote', [])
            if not quote_list or len(quote_list) == 0:
                logger.error("x No quote data in indicators")
                return None
            
            quote = quote_list[0]
            
            # 提取 OHLCV 數據
            parsed_data = {
                'timestamps': timestamps,
                'open': quote.get('open', []),
                'high': quote.get('high', []),
                'low': quote.get('low', []),
                'close': quote.get('close', []),
                'volume': quote.get('volume', []),
                'data_source': 'yahoo_finance'
            }
            
            # 驗證數據長度一致性
            data_length = len(timestamps)
            for key in ['open', 'high', 'low', 'close', 'volume']:
                if len(parsed_data[key]) != data_length:
                    logger.warning(
                        f"! Length mismatch: {key} has {len(parsed_data[key])} "
                        f"items but timestamps has {data_length}"
                    )
            
            logger.debug(f"* Successfully parsed {data_length} historical data points")
            return parsed_data
            
        except KeyError as e:
            logger.error(f"x Missing required key in response: {e}")
            return None
        except TypeError as e:
            logger.error(f"x Type error while parsing historical data: {e}")
            return None
        except IndexError as e:
            logger.error(f"x Index error while parsing historical data: {e}")
            return None
        except Exception as e:
            logger.error(f"x Unexpected error parsing historical data response: {e}")
            logger.debug(f"Response structure: {response}")
            return None


# 使用示例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "=" * 70)
    print("Yahoo Finance 客户端示例（優化版）")
    print("=" * 70)
    
    # 初始化客户端（使用優化功能）
    client = YahooFinanceV2Client()
    
    # 顯示優化功能狀態
    print(f"\n優化功能:")
    print(f"  - User-Agent 輪換器: {len(client.ua_rotator)} 個 UA")
    print(f"  - Crumb 管理器: {client.crumb_manager.get_stats()}")
    print(f"  - 重試處理器: max_retries={client.max_retries}")
    
    # 测试获取股票数据
    print("\n测试获取 AAPL 股票数据...")
    try:
        response = client.get_quote('AAPL')
        stock_info = YahooDataParser.parse_quote(response)
        
        if stock_info:
            print(f"\n股票代码: {stock_info['symbol']}")
            print(f"当前股价: ${stock_info['current_price']:.2f}")
            print(f"开盘价: ${stock_info['open']:.2f}")
            print(f"成交量: {stock_info['volume']:,}")
            print("\n* Yahoo Finance API 运行正常")
        else:
            print("\n x 数据解析失败")
    except Exception as e:
        print(f"\n x API 调用失败: {e}")
    
    # 顯示重試統計
    print(f"\n重試統計: {client.retry_handler.get_stats()}")

