#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Yahoo Finance 2.0 API OAuth 客户端
使用官方 Yahoo Finance API with OAuth 2.0 认证
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient
import requests

# 配置日志
logger = logging.getLogger(__name__)


class YahooFinanceV2Client:
    """Yahoo Finance 2.0 官方API客户端（OAuth 2.0）"""
    
    # Yahoo Finance API 端点
    AUTHORIZATION_BASE_URL = 'https://api.login.yahoo.com/oauth2/request_auth'
    TOKEN_URL = 'https://api.login.yahoo.com/oauth2/get_token'
    API_BASE_URL = 'https://query2.finance.yahoo.com/v10/finance'
    
    def __init__(self, client_id, client_secret, redirect_uri, token_file='yahoo_token.json'):
        """
        初始化 Yahoo Finance 2.0 客户端
        
        参数:
            client_id: Yahoo App Client ID
            client_secret: Yahoo App Client Secret
            redirect_uri: OAuth 回调 URI
            token_file: Token 存储文件路径
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.token_file = token_file
        self.token = None
        self.oauth = None
        self.request_delay = 0.5  # 请求间隔（秒）
        self.last_request_time = 0
        
        # 尝试加载已保存的 token
        self._load_token()
        
        logger.info("Yahoo Finance 2.0 OAuth 客户端已初始化")
    
    def _load_token(self):
        """从文件加载 token"""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r') as f:
                    self.token = json.load(f)
                
                # 检查 token 是否过期
                if self._is_token_expired():
                    logger.warning("Token 已过期，需要重新授权")
                    self.token = None
                else:
                    logger.info("✓ 成功加载已保存的 token")
                    self._initialize_oauth_session()
            except Exception as e:
                logger.error(f"加载 token 失败: {e}")
                self.token = None
    
    def _save_token(self):
        """保存 token 到文件"""
        try:
            with open(self.token_file, 'w') as f:
                json.dump(self.token, f, indent=2)
            logger.info("✓ Token 已保存")
        except Exception as e:
            logger.error(f"保存 token 失败: {e}")
    
    def _is_token_expired(self):
        """检查 token 是否过期"""
        if not self.token or 'expires_at' not in self.token:
            return True
        
        # 提前5分钟刷新
        expires_at = self.token['expires_at'] - 300
        return time.time() >= expires_at
    
    def _initialize_oauth_session(self):
        """初始化 OAuth session"""
        if self.token:
            self.oauth = OAuth2Session(
                self.client_id,
                token=self.token,
                auto_refresh_url=self.TOKEN_URL,
                auto_refresh_kwargs={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                },
                token_updater=self._token_updater
            )
        else:
            self.oauth = OAuth2Session(
                self.client_id,
                redirect_uri=self.redirect_uri
            )
    
    def _token_updater(self, token):
        """Token 自动刷新回调"""
        self.token = token
        self._save_token()
        logger.info("✓ Token 已自动刷新")
    
    def get_authorization_url(self):
        """
        获取授权 URL（步骤1：用户需要访问此URL进行授权）
        
        返回:
            tuple: (authorization_url, state)
        """
        self._initialize_oauth_session()
        authorization_url, state = self.oauth.authorization_url(
            self.AUTHORIZATION_BASE_URL
        )
        logger.info(f"授权 URL: {authorization_url}")
        return authorization_url, state
    
    def fetch_token(self, authorization_response_url):
        """
        使用授权响应获取 token（步骤2：用户授权后调用）
        
        参数:
            authorization_response_url: 授权后的完整回调 URL（包含 code）
        
        返回:
            dict: Token 信息
        """
        try:
            token = self.oauth.fetch_token(
                self.TOKEN_URL,
                authorization_response=authorization_response_url,
                client_secret=self.client_secret
            )
            
            self.token = token
            self._save_token()
            self._initialize_oauth_session()
            
            logger.info("✓ 成功获取 access token")
            return token
            
        except Exception as e:
            logger.error(f"获取 token 失败: {e}")
            raise
    
    def is_authenticated(self):
        """检查是否已认证"""
        return self.token is not None and not self._is_token_expired()
    
    def _rate_limit_delay(self):
        """请求速率限制"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint, params=None):
        """
        发送 API 请求
        
        参数:
            endpoint: API 端点
            params: 查询参数
        
        返回:
            dict: API 响应
        """
        if not self.is_authenticated():
            raise Exception("未认证，请先完成 OAuth 授权")
        
        self._rate_limit_delay()
        
        url = f"{self.API_BASE_URL}/{endpoint}"
        
        try:
            response = self.oauth.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.warning("API 速率限制，等待30秒...")
                time.sleep(30)
                return self._make_request(endpoint, params)
            else:
                logger.error(f"API 请求失败: {e}")
                raise
    
    # ==================== 股票数据 API ====================
    
    def get_quote(self, symbols):
        """
        获取股票报价
        
        参数:
            symbols: 股票代码或列表
        
        返回:
            dict: 报价数据
        """
        if isinstance(symbols, list):
            symbols = ','.join(symbols)
        
        params = {
            'symbols': symbols,
            'fields': 'regularMarketPrice,regularMarketOpen,regularMarketDayHigh,'
                     'regularMarketDayLow,regularMarketVolume,marketCap,trailingPE,'
                     'dividendRate,epsTrailingTwelveMonths'
        }
        
        return self._make_request('quoteSummary', params)
    
    def get_historical_data(self, symbol, interval='1d', period1=None, period2=None):
        """
        获取历史数据
        
        参数:
            symbol: 股票代码
            interval: 时间间隔 (1m, 5m, 15m, 30m, 60m, 1d, 1wk, 1mo)
            period1: 开始时间戳
            period2: 结束时间戳
        
        返回:
            dict: 历史数据
        """
        if period1 is None:
            period1 = int((datetime.now() - timedelta(days=30)).timestamp())
        if period2 is None:
            period2 = int(datetime.now().timestamp())
        
        params = {
            'symbol': symbol,
            'interval': interval,
            'period1': period1,
            'period2': period2
        }
        
        return self._make_request('chart', params)
    
    def get_options_chain(self, symbol, expiration_date=None):
        """
        获取期权链
        
        参数:
            symbol: 股票代码
            expiration_date: 到期日期（Unix 时间戳）
        
        返回:
            dict: 期权链数据
        """
        params = {'symbol': symbol}
        if expiration_date:
            params['date'] = expiration_date
        
        return self._make_request('options', params)
    
    def get_fundamentals(self, symbol):
        """
        获取基本面数据
        
        参数:
            symbol: 股票代码
        
        返回:
            dict: 基本面数据
        """
        params = {
            'symbol': symbol,
            'modules': 'financialData,defaultKeyStatistics,calendarEvents'
        }
        
        return self._make_request('quoteSummary', params)


class YahooFinanceV2Helper:
    """Yahoo Finance 2.0 辅助工具类（用于简化数据提取）"""
    
    @staticmethod
    def extract_stock_info(api_response):
        """
        从 API 响应提取股票信息
        
        参数:
            api_response: API 返回的原始数据
        
        返回:
            dict: 标准化的股票信息
        """
        try:
            result = api_response.get('quoteSummary', {}).get('result', [{}])[0]
            price = result.get('price', {})
            financial = result.get('financialData', {})
            stats = result.get('defaultKeyStatistics', {})
            
            return {
                'ticker': price.get('symbol', ''),
                'current_price': price.get('regularMarketPrice', {}).get('raw', 0),
                'open': price.get('regularMarketOpen', {}).get('raw', 0),
                'high': price.get('regularMarketDayHigh', {}).get('raw', 0),
                'low': price.get('regularMarketDayLow', {}).get('raw', 0),
                'volume': price.get('regularMarketVolume', {}).get('raw', 0),
                'market_cap': price.get('marketCap', {}).get('raw', 0),
                'pe_ratio': stats.get('trailingPE', {}).get('raw', 0),
                'dividend_rate': stats.get('dividendRate', {}).get('raw', 0),
                'eps': stats.get('trailingEps', {}).get('raw', 0),
                'company_name': price.get('longName', ''),
            }
        except Exception as e:
            logger.error(f"提取股票信息失败: {e}")
            return None
    
    @staticmethod
    def extract_options_data(api_response):
        """
        从 API 响应提取期权数据
        
        参数:
            api_response: API 返回的原始数据
        
        返回:
            dict: 标准化的期权数据
        """
        try:
            result = api_response.get('optionChain', {}).get('result', [{}])[0]
            options = result.get('options', [{}])[0]
            
            return {
                'calls': options.get('calls', []),
                'puts': options.get('puts', []),
                'expiration': options.get('expirationDate', '')
            }
        except Exception as e:
            logger.error(f"提取期权数据失败: {e}")
            return None


# 使用示例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "=" * 70)
    print("Yahoo Finance 2.0 OAuth 客户端示例")
    print("=" * 70)
    
    # 从环境变量加载配置
    from config.settings import settings
    
    client = YahooFinanceV2Client(
        client_id=settings.YAHOO_CLIENT_ID,
        client_secret=settings.YAHOO_CLIENT_SECRET,
        redirect_uri=settings.YAHOO_REDIRECT_URI
    )
    
    if not client.is_authenticated():
        print("\n需要进行 OAuth 授权...")
        auth_url, state = client.get_authorization_url()
        print(f"\n请访问以下 URL 进行授权:\n{auth_url}")
        print("\n授权后，将浏览器地址栏中的完整 URL 复制回来")
        callback_url = input("\n请输入回调 URL: ")
        client.fetch_token(callback_url)
    else:
        print("\n✓ 已认证")
    
    # 测试获取股票数据
    print("\n测试获取 AAPL 股票数据...")
    response = client.get_quote('AAPL')
    stock_info = YahooFinanceV2Helper.extract_stock_info(response)
    
    if stock_info:
        print(f"\n股票代码: {stock_info['ticker']}")
        print(f"当前股价: ${stock_info['current_price']:.2f}")
        print(f"市盈率: {stock_info['pe_ratio']:.2f}")
        print(f"EPS: ${stock_info['eps']:.2f}")
        print("\n✅ Yahoo Finance 2.0 API 运行正常")

