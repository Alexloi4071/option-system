# tests/test_finviz_scraper.py
"""
Finviz 抓取器屬性測試

測試優化功能:
- Property 4: 請求頭完整性
- Property 5: 隨機延遲範圍
- Property 6: 封鎖檢測
- Property 7: 多重選擇器容錯
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings, assume

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer.finviz_scraper import FinvizScraper, SafeFormatter
from data_layer.utils.user_agent_rotator import UserAgentRotator


class TestFinvizRandomDelay:
    """Property 5: 隨機延遲範圍測試"""
    
    @given(
        min_delay=st.floats(min_value=0.1, max_value=2.0),
        max_delay=st.floats(min_value=2.1, max_value=5.0)
    )
    @settings(max_examples=20)
    def test_random_delay_within_range(self, min_delay, max_delay):
        """測試隨機延遲在指定範圍內"""
        scraper = FinvizScraper(
            request_delay=0.0,  # 禁用基礎延遲
            random_delay_range=(min_delay, max_delay)
        )
        
        # 驗證配置正確
        assert scraper.random_delay_range == (min_delay, max_delay)
    
    def test_random_delay_default_range(self):
        """測試默認隨機延遲範圍為 1-3 秒"""
        scraper = FinvizScraper()
        assert scraper.random_delay_range == (1.0, 3.0)
    
    @settings(deadline=None)  # 禁用 deadline，因為測試涉及實際等待
    @given(st.just((0.01, 0.02)))  # 使用固定的非常短延遲
    def test_rate_limit_adds_random_delay(self, delay_range):
        """測試 _rate_limit 方法添加隨機延遲"""
        delay_min, delay_max = delay_range
        scraper = FinvizScraper(
            request_delay=0.0,
            random_delay_range=(delay_min, delay_max)
        )
        
        # 記錄開始時間
        start_time = time.time()
        scraper._rate_limit()
        elapsed = time.time() - start_time
        
        # 驗證延遲在範圍內（允許一些誤差）
        assert elapsed >= delay_min * 0.8  # 允許 20% 誤差
        assert elapsed <= delay_max * 2.0  # 允許 100% 上限誤差


class TestFinvizRequestHeaders:
    """Property 4: 請求頭完整性測試"""
    
    def test_headers_contain_required_fields(self):
        """測試請求頭包含所有必需字段"""
        scraper = FinvizScraper()
        
        required_headers = [
            'User-Agent',
            'Accept',
            'Accept-Language',
            'Accept-Encoding',
            'Connection',
        ]
        
        for header in required_headers:
            assert header in scraper.headers, f"缺少必需的請求頭: {header}"
    
    def test_user_agent_is_browser_like(self):
        """測試 User-Agent 看起來像瀏覽器"""
        scraper = FinvizScraper()
        ua = scraper.headers['User-Agent']
        
        # 應該包含瀏覽器標識
        browser_indicators = ['Mozilla', 'Chrome', 'Firefox', 'Safari', 'Edge']
        has_browser = any(indicator in ua for indicator in browser_indicators)
        assert has_browser, f"User-Agent 不像瀏覽器: {ua}"
    
    def test_headers_include_referer(self):
        """測試請求頭包含 Referer"""
        scraper = FinvizScraper()
        assert 'Referer' in scraper.headers
        assert 'finviz.com' in scraper.headers['Referer']
    
    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=10)
    def test_user_agent_rotation(self, num_rotations):
        """測試 User-Agent 輪換"""
        scraper = FinvizScraper()
        
        user_agents = set()
        for _ in range(num_rotations):
            ua = scraper._rotate_user_agent()
            user_agents.add(ua)
        
        # 如果輪換次數足夠多，應該有多個不同的 UA
        if num_rotations >= 3:
            assert len(user_agents) >= 2, "User-Agent 輪換不正常"


class TestFinvizBlockDetection:
    """Property 6: 封鎖檢測測試"""
    
    def test_detect_403_as_block(self):
        """測試檢測 403 為封鎖"""
        scraper = FinvizScraper()
        
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        
        assert scraper._detect_block(mock_response) is True
    
    def test_detect_429_as_block(self):
        """測試檢測 429 為封鎖"""
        scraper = FinvizScraper()
        
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Too Many Requests"
        
        assert scraper._detect_block(mock_response) is True
    
    @given(st.sampled_from(['captcha', 'robot', 'blocked', 'access denied', 'rate limit']))
    def test_detect_block_keywords(self, keyword):
        """測試檢測封鎖關鍵字"""
        scraper = FinvizScraper()
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = f"Please verify you are not a {keyword}"
        
        assert scraper._detect_block(mock_response) is True
    
    def test_normal_response_not_blocked(self):
        """測試正常響應不被識別為封鎖"""
        scraper = FinvizScraper()
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Stock data here</body></html>"
        
        assert scraper._detect_block(mock_response) is False


class TestFinvizMultipleSelectors:
    """Property 7: 多重選擇器容錯測試"""
    
    def test_table_selectors_defined(self):
        """測試定義了多個表格選擇器"""
        assert len(FinvizScraper.TABLE_SELECTORS) >= 2
    
    def test_find_table_with_primary_selector(self):
        """測試使用主選擇器找到表格"""
        from bs4 import BeautifulSoup
        
        scraper = FinvizScraper()
        html = '<html><body><table class="snapshot-table2"><tr><td>Data</td></tr></table></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        
        table = scraper._find_table(soup)
        assert table is not None
    
    def test_find_table_with_fallback_selector(self):
        """測試使用備用選擇器找到表格"""
        from bs4 import BeautifulSoup
        
        scraper = FinvizScraper()
        # 使用不同的類名
        html = '<html><body><table class="screener-body-table-nw"><tr><td>Data</td></tr></table></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        
        table = scraper._find_table(soup)
        assert table is not None
    
    def test_find_table_returns_none_when_not_found(self):
        """測試找不到表格時返回 None"""
        from bs4 import BeautifulSoup
        
        scraper = FinvizScraper()
        html = '<html><body><div>No table here</div></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        
        table = scraper._find_table(soup)
        assert table is None


class TestSafeFormatter:
    """SafeFormatter 測試"""
    
    @given(st.floats(min_value=-1e10, max_value=1e10, allow_nan=False, allow_infinity=False))
    @settings(max_examples=50)
    def test_format_number_with_valid_float(self, value):
        """測試格式化有效浮點數"""
        result = SafeFormatter.format_number(value)
        assert result != 'N/A'
        # 應該能轉換回數字
        float(result)
    
    def test_format_number_with_none(self):
        """測試格式化 None"""
        assert SafeFormatter.format_number(None) == 'N/A'
    
    def test_format_number_with_nan(self):
        """測試格式化 NaN"""
        import math
        assert SafeFormatter.format_number(float('nan')) == 'N/A'
    
    @given(st.floats(min_value=0, max_value=1e10, allow_nan=False, allow_infinity=False))
    @settings(max_examples=30)
    def test_format_currency(self, value):
        """測試格式化貨幣"""
        result = SafeFormatter.format_currency(value)
        assert result.startswith('$')
    
    @given(st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False))
    @settings(max_examples=30)
    def test_format_percent(self, value):
        """測試格式化百分比"""
        result = SafeFormatter.format_percent(value)
        assert result.endswith('%')


class TestFinvizStats:
    """統計功能測試"""
    
    def test_get_stats_initial(self):
        """測試初始統計"""
        scraper = FinvizScraper()
        stats = scraper.get_stats()
        
        assert stats['request_count'] == 0
        assert stats['block_count'] == 0
        assert stats['block_rate'] == 0
        assert 'ua_stats' in stats
        assert 'retry_stats' in stats
    
    def test_block_count_increments(self):
        """測試封鎖計數增加"""
        scraper = FinvizScraper()
        
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        
        initial_count = scraper._block_count
        scraper._detect_block(mock_response)
        
        assert scraper._block_count == initial_count + 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


class TestNumericParsing:
    """Property 7 & 8: 數值解析正確性和容錯解析測試"""
    
    def test_parse_simple_number(self):
        """測試解析簡單數字"""
        scraper = FinvizScraper()
        assert scraper._parse_value("123.45") == 123.45
        assert scraper._parse_value("0") == 0.0
        assert scraper._parse_value("1") == 1.0
    
    def test_parse_negative_number(self):
        """測試解析負數"""
        scraper = FinvizScraper()
        assert scraper._parse_value("-123.45") == -123.45
        assert scraper._parse_value("-5.67") == -5.67
    
    def test_parse_accounting_negative(self):
        """測試解析會計格式負數 (123.45)"""
        scraper = FinvizScraper()
        result = scraper._parse_value("(123.45)")
        assert result == -123.45
    
    def test_parse_thousand_suffix(self):
        """測試解析 K 後綴（千）"""
        scraper = FinvizScraper()
        assert scraper._parse_value("12.34K") == 12340.0
        assert scraper._parse_value("1k") == 1000.0
    
    def test_parse_million_suffix(self):
        """測試解析 M 後綴（百萬）"""
        scraper = FinvizScraper()
        assert scraper._parse_value("456.78M") == 456780000.0
        assert scraper._parse_value("1.5m") == 1500000.0
    
    def test_parse_billion_suffix(self):
        """測試解析 B 後綴（十億）"""
        scraper = FinvizScraper()
        assert scraper._parse_value("1.23B") == 1230000000.0
        assert scraper._parse_value("2.5b") == 2500000000.0
    
    def test_parse_trillion_suffix(self):
        """測試解析 T 後綴（萬億）"""
        scraper = FinvizScraper()
        assert scraper._parse_value("1.5T") == 1500000000000.0
        assert scraper._parse_value("2t") == 2000000000000.0
    
    def test_parse_percent(self):
        """測試解析百分比"""
        scraper = FinvizScraper()
        assert scraper._parse_value("12.34%") == 12.34
        assert scraper._parse_value("-5.67%") == -5.67
    
    def test_parse_with_comma_separator(self):
        """測試解析帶千位分隔符的數字"""
        scraper = FinvizScraper()
        assert scraper._parse_value("1,234.56") == 1234.56
        assert scraper._parse_value("1,234,567") == 1234567.0
    
    def test_parse_invalid_values(self):
        """測試解析無效值返回 None"""
        scraper = FinvizScraper()
        assert scraper._parse_value("-") is None
        assert scraper._parse_value("N/A") is None
        assert scraper._parse_value("n/a") is None
        assert scraper._parse_value("") is None
        assert scraper._parse_value(None) is None
    
    @given(st.floats(min_value=-1e12, max_value=1e12, allow_nan=False, allow_infinity=False))
    @settings(max_examples=30)
    def test_parse_roundtrip(self, value):
        """測試數值解析往返正確性"""
        scraper = FinvizScraper()
        
        # 格式化為字符串
        str_value = f"{value:.2f}"
        
        # 解析回數字
        parsed = scraper._parse_value(str_value)
        
        # 驗證結果接近原始值
        assert parsed is not None
        assert abs(parsed - value) < 0.01
    
    @given(st.sampled_from(['K', 'M', 'B', 'T', 'k', 'm', 'b', 't']))
    def test_parse_all_suffixes(self, suffix):
        """測試所有後綴都能正確解析"""
        scraper = FinvizScraper()
        result = scraper._parse_value(f"1.5{suffix}")
        assert result is not None
        assert result > 1.5  # 應該被乘以倍數
