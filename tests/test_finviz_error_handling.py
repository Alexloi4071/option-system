#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Finviz 錯誤處理測試

測試 Finviz 部分數據可用時的優雅處理和關鍵字段補充。

**Feature: data-sources-enhancement**
**Property 4: Finviz Partial Data Handling**
**Property 6: Critical Field Supplementation**
**Validates: Requirements 4.1, 4.2, 4.3**
"""

import pytest
import sys
import os
from unittest import mock
from hypothesis import given, strategies as st, settings, assume

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer.data_fetcher import DataFetcher


# ==================== 策略定義 ====================

# 所有預期的 Finviz 字段（與 data_fetcher.py 中的定義保持一致）
# 注意：這個列表必須與 _validate_and_supplement_finviz_data 中的 EXPECTED_FINVIZ_FIELDS 完全一致
EXPECTED_FINVIZ_FIELDS = [
    'price', 'eps_ttm', 'pe', 'forward_pe', 'peg', 'market_cap',
    'volume', 'dividend_yield', 'beta', 'atr', 'rsi', 'company_name',
    'sector', 'industry', 'target_price', 'profit_margin', 
    'operating_margin', 'roe', 'roa', 'debt_eq', 'insider_own',
    'inst_own', 'short_float', 'avg_volume', 'eps_next_y'
]  # 25 fields total

# 關鍵字段
CRITICAL_FIELDS = ['price', 'eps_ttm', 'pe']

# 非關鍵字段
NON_CRITICAL_FIELDS = [f for f in EXPECTED_FINVIZ_FIELDS if f not in CRITICAL_FIELDS]


def generate_finviz_field_value(field_name: str):
    """根據字段名生成合適的值策略"""
    if field_name in ['price', 'eps_ttm', 'pe', 'forward_pe', 'peg', 'beta', 
                      'atr', 'target_price', 'debt_eq']:
        return st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False)
    elif field_name in ['market_cap', 'volume', 'avg_volume']:
        return st.integers(min_value=1000, max_value=10**15)
    elif field_name in ['dividend_yield', 'rsi', 'profit_margin', 'operating_margin', 
                        'roe', 'roa', 'insider_own', 'inst_own', 'short_float']:
        return st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)
    elif field_name in ['company_name', 'sector', 'industry']:
        return st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z')))
    elif field_name == 'eps_next_y':
        return st.floats(min_value=-100.0, max_value=1000.0, allow_nan=False, allow_infinity=False)
    else:
        return st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False)


@st.composite
def finviz_data_with_all_critical_fields(draw):
    """生成包含所有關鍵字段的 Finviz 數據"""
    data = {}
    # 確保所有關鍵字段都有值
    for field in CRITICAL_FIELDS:
        data[field] = draw(generate_finviz_field_value(field))
    
    # 隨機添加一些非關鍵字段
    num_non_critical = draw(st.integers(min_value=0, max_value=len(NON_CRITICAL_FIELDS)))
    selected_fields = draw(st.sampled_from(
        [list(combo) for combo in [NON_CRITICAL_FIELDS[:i] for i in range(len(NON_CRITICAL_FIELDS) + 1)]]
    ))[:num_non_critical]
    
    for field in selected_fields:
        data[field] = draw(generate_finviz_field_value(field))
    
    return data


@st.composite
def finviz_data_missing_some_non_critical(draw):
    """生成缺少部分非關鍵字段的 Finviz 數據"""
    data = {}
    # 確保所有關鍵字段都有值
    for field in CRITICAL_FIELDS:
        data[field] = draw(generate_finviz_field_value(field))
    
    # 隨機選擇一些非關鍵字段（至少缺少一個）
    num_to_include = draw(st.integers(min_value=0, max_value=len(NON_CRITICAL_FIELDS) - 1))
    fields_to_include = draw(st.lists(
        st.sampled_from(NON_CRITICAL_FIELDS),
        min_size=num_to_include,
        max_size=num_to_include,
        unique=True
    ))
    
    for field in fields_to_include:
        data[field] = draw(generate_finviz_field_value(field))
    
    return data


@st.composite
def finviz_data_missing_critical_fields(draw):
    """生成缺少關鍵字段的 Finviz 數據"""
    data = {}
    
    # 隨機選擇要缺少的關鍵字段（至少缺少一個）
    num_missing = draw(st.integers(min_value=1, max_value=len(CRITICAL_FIELDS)))
    missing_critical = draw(st.lists(
        st.sampled_from(CRITICAL_FIELDS),
        min_size=num_missing,
        max_size=num_missing,
        unique=True
    ))
    
    # 添加未缺少的關鍵字段
    for field in CRITICAL_FIELDS:
        if field not in missing_critical:
            data[field] = draw(generate_finviz_field_value(field))
    
    # 添加一些非關鍵字段
    num_non_critical = draw(st.integers(min_value=1, max_value=5))
    fields_to_include = draw(st.lists(
        st.sampled_from(NON_CRITICAL_FIELDS),
        min_size=num_non_critical,
        max_size=num_non_critical,
        unique=True
    ))
    
    for field in fields_to_include:
        data[field] = draw(generate_finviz_field_value(field))
    
    return data, missing_critical


class TestFinvizErrorHandling:
    """測試 Finviz 錯誤處理"""
    
    @pytest.fixture
    def fetcher(self):
        """創建 DataFetcher 實例"""
        return DataFetcher(use_ibkr=False)
    
    def test_complete_finviz_data(self, fetcher):
        """測試完整的 Finviz 數據"""
        complete_data = {
            'price': 150.25,
            'eps_ttm': 6.15,
            'pe': 24.43,
            'forward_pe': 22.5,
            'peg': 2.1,
            'market_cap': 2500000000000,
            'volume': 50000000,
            'dividend_yield': 0.5,
            'beta': 1.2,
            'atr': 3.5,
            'rsi': 55.0,
            'company_name': 'Apple Inc.',
            'sector': 'Technology',
            'industry': 'Consumer Electronics',
            'target_price': 180.0,
            'profit_margin': 25.0,
            'operating_margin': 30.0,
            'roe': 150.0,
            'roa': 20.0,
            'debt_eq': 1.5,
            'insider_own': 0.1,
            'inst_own': 60.0,
            'short_float': 1.0,
            'avg_volume': 55000000,
            'eps_next_y': 7.0
        }
        
        result = fetcher._validate_and_supplement_finviz_data(complete_data, 'AAPL')
        
        assert result is not None
        assert result['data_quality'] == 'complete'
        assert len(result['supplemented_fields']) == 0

    def test_partial_finviz_data(self, fetcher):
        """
        測試部分數據可用時的優雅處理
        
        **Property 4: Finviz Partial Data Handling**
        """
        partial_data = {
            'price': 150.25,
            'eps_ttm': 6.15,
            'pe': 24.43,
            # 缺少很多非關鍵字段
            'company_name': 'Apple Inc.',
            'sector': 'Technology'
        }
        
        result = fetcher._validate_and_supplement_finviz_data(partial_data, 'AAPL')
        
        assert result is not None
        assert result['data_quality'] in ['partial', 'minimal']
        assert len(result['missing_fields']) > 0
        # 關鍵字段都存在，不需要補充
        assert len(result['supplemented_fields']) == 0
    
    def test_missing_critical_fields_supplementation(self, fetcher):
        """
        測試關鍵字段缺失時的補充邏輯
        
        **Property 6: Critical Field Supplementation**
        """
        # 缺少關鍵字段的數據
        incomplete_data = {
            # 缺少 price, eps_ttm, pe
            'company_name': 'Apple Inc.',
            'sector': 'Technology'
        }
        
        # 模擬 yfinance 補充數據
        mock_info = {
            'currentPrice': 150.25,
            'trailingEps': 6.15,
            'trailingPE': 24.43
        }
        
        with mock.patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.info = mock_info
            
            result = fetcher._validate_and_supplement_finviz_data(incomplete_data, 'AAPL')
        
        assert result is not None
        assert result['price'] == 150.25
        assert result['eps_ttm'] == 6.15
        assert result['pe'] == 24.43
        assert 'price' in result['supplemented_fields']
        assert 'eps_ttm' in result['supplemented_fields']
        assert 'pe' in result['supplemented_fields']
        assert result['data_source'] == 'Finviz+yfinance'
    
    def test_missing_critical_fields_no_supplement(self, fetcher):
        """測試關鍵字段缺失且無法補充時返回 None"""
        incomplete_data = {
            'company_name': 'Apple Inc.'
        }
        
        # 模擬 yfinance 也無法提供數據
        with mock.patch('yfinance.Ticker', side_effect=Exception("Network Error")):
            result = fetcher._validate_and_supplement_finviz_data(incomplete_data, 'AAPL')
        
        # 應該返回 None（驗證失敗）
        assert result is None
    
    def test_data_quality_assessment(self, fetcher):
        """測試數據質量評估"""
        # 測試 minimal 質量
        minimal_data = {
            'price': 150.25,
            'eps_ttm': 6.15,
            'pe': 24.43
        }
        result = fetcher._validate_and_supplement_finviz_data(minimal_data, 'AAPL')
        assert result is not None
        assert result['data_quality'] == 'minimal'
        
        # 測試 partial 質量（60-90% 字段）
        partial_data = {
            'price': 150.25,
            'eps_ttm': 6.15,
            'pe': 24.43,
            'forward_pe': 22.5,
            'peg': 2.1,
            'market_cap': 2500000000000,
            'volume': 50000000,
            'dividend_yield': 0.5,
            'beta': 1.2,
            'atr': 3.5,
            'rsi': 55.0,
            'company_name': 'Apple Inc.',
            'sector': 'Technology',
            'industry': 'Consumer Electronics',
            'target_price': 180.0,
            'profit_margin': 25.0,
            'operating_margin': 30.0,
            'roe': 150.0
            # 缺少一些字段
        }
        result = fetcher._validate_and_supplement_finviz_data(partial_data, 'AAPL')
        assert result is not None
        assert result['data_quality'] in ['partial', 'complete']


class TestFinvizPropertyBasedTests:
    """
    Finviz 錯誤處理的屬性測試
    
    使用 Hypothesis 進行屬性測試，驗證：
    - Property 4: Finviz Partial Data Handling
    - Property 6: Critical Field Supplementation
    """
    
    # 使用類級別的 fetcher 實例，避免 Hypothesis 健康檢查問題
    _fetcher = None
    
    @classmethod
    def get_fetcher(cls):
        """獲取或創建 DataFetcher 實例"""
        if cls._fetcher is None:
            cls._fetcher = DataFetcher(use_ibkr=False)
        return cls._fetcher
    
    @given(data=finviz_data_with_all_critical_fields())
    @settings(max_examples=100, deadline=None)
    def test_property4_partial_data_returns_valid_dict(self, data):
        """
        Property 4: Finviz Partial Data Handling
        
        *For any* Finviz response with all critical fields present (regardless of 
        non-critical fields), the system should return a valid dict with appropriate
        data_quality indicator (rather than failing completely).
        
        **Feature: data-sources-enhancement, Property 4: Finviz Partial Data Handling**
        **Validates: Requirements 4.1, 4.3**
        """
        fetcher = self.get_fetcher()
        result = fetcher._validate_and_supplement_finviz_data(data, 'TEST')
        
        # 結果不應為 None（因為關鍵字段都存在）
        assert result is not None, "Should return valid dict when critical fields present"
        
        # 必須包含數據質量指標
        assert 'data_quality' in result, "Result must include data_quality"
        assert result['data_quality'] in ['complete', 'partial', 'minimal'], \
            f"data_quality must be one of complete/partial/minimal, got {result['data_quality']}"
        
        # 必須包含缺失字段列表
        assert 'missing_fields' in result, "Result must include missing_fields"
        assert isinstance(result['missing_fields'], list), "missing_fields must be a list"
        
        # 必須包含補充字段列表
        assert 'supplemented_fields' in result, "Result must include supplemented_fields"
        assert isinstance(result['supplemented_fields'], list), "supplemented_fields must be a list"
        
        # 關鍵字段都存在時，不需要補充
        assert len(result['supplemented_fields']) == 0, \
            "No supplementation needed when all critical fields present"
        
        # 數據源應該是 Finviz
        assert result['data_source'] == 'Finviz', "Data source should be Finviz"
    
    @given(data=finviz_data_missing_some_non_critical())
    @settings(max_examples=100, deadline=None)
    def test_property4_missing_non_critical_continues_processing(self, data):
        """
        Property 4: Finviz Partial Data Handling (Non-Critical Fields)
        
        *For any* Finviz response with missing non-critical fields, the system should
        continue processing with available data and return a valid stock_info dict
        with None values for missing fields.
        
        **Feature: data-sources-enhancement, Property 4: Finviz Partial Data Handling**
        **Validates: Requirements 4.1, 4.3**
        """
        fetcher = self.get_fetcher()
        result = fetcher._validate_and_supplement_finviz_data(data, 'TEST')
        
        # 結果不應為 None
        assert result is not None, "Should return valid dict even with missing non-critical fields"
        
        # 缺失的字段應該在 missing_fields 中記錄
        # 注意：只檢查在 EXPECTED_FINVIZ_FIELDS 中定義的字段
        for field in EXPECTED_FINVIZ_FIELDS:
            if field not in data or data.get(field) is None:
                assert field in result['missing_fields'], \
                    f"Missing field {field} should be recorded in missing_fields"
        
        # 數據質量應該反映缺失情況
        if len(result['missing_fields']) > len(EXPECTED_FINVIZ_FIELDS) * 0.4:
            assert result['data_quality'] in ['partial', 'minimal'], \
                "Data quality should be partial or minimal when many fields missing"
    
    @given(data_and_missing=finviz_data_missing_critical_fields())
    @settings(max_examples=100, deadline=None)
    def test_property6_critical_field_supplementation(self, data_and_missing):
        """
        Property 6: Critical Field Supplementation
        
        *For any* Finviz response missing critical fields (price, eps, pe), the system
        should attempt to supplement these fields from yfinance before returning the data.
        
        **Feature: data-sources-enhancement, Property 6: Critical Field Supplementation**
        **Validates: Requirements 4.2**
        """
        fetcher = self.get_fetcher()
        data, missing_critical = data_and_missing
        
        # 模擬 yfinance 提供補充數據
        mock_info = {
            'currentPrice': 150.25,
            'trailingEps': 6.15,
            'trailingPE': 24.43
        }
        
        with mock.patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.info = mock_info
            
            result = fetcher._validate_and_supplement_finviz_data(data, 'TEST')
        
        # 結果不應為 None（因為 yfinance 可以補充）
        assert result is not None, "Should return valid dict when yfinance can supplement"
        
        # 所有缺失的關鍵字段都應該被補充
        for field in missing_critical:
            assert result.get(field) is not None, \
                f"Critical field {field} should be supplemented"
            assert field in result['supplemented_fields'], \
                f"Supplemented field {field} should be recorded"
        
        # 數據源應該標記為混合來源
        assert result['data_source'] == 'Finviz+yfinance', \
            "Data source should indicate mixed sources"
    
    @given(data_and_missing=finviz_data_missing_critical_fields())
    @settings(max_examples=100, deadline=None)
    def test_property6_supplementation_failure_returns_none(self, data_and_missing):
        """
        Property 6: Critical Field Supplementation (Failure Case)
        
        *For any* Finviz response missing critical fields, when yfinance also fails
        to provide the data, the system should return None.
        
        **Feature: data-sources-enhancement, Property 6: Critical Field Supplementation**
        **Validates: Requirements 4.2**
        """
        fetcher = self.get_fetcher()
        data, missing_critical = data_and_missing
        
        # 模擬 yfinance 失敗
        with mock.patch('yfinance.Ticker', side_effect=Exception("Network Error")):
            result = fetcher._validate_and_supplement_finviz_data(data, 'TEST')
        
        # 當無法補充關鍵字段時，應該返回 None
        assert result is None, \
            "Should return None when critical fields cannot be supplemented"
    
    @given(
        price=st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False),
        eps=st.floats(min_value=-100.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        pe=st.floats(min_value=0.01, max_value=1000.0, allow_nan=False, allow_infinity=False),
        num_extra_fields=st.integers(min_value=0, max_value=len(NON_CRITICAL_FIELDS))
    )
    @settings(max_examples=100, deadline=None)
    def test_property4_data_quality_calculation(self, price, eps, pe, num_extra_fields):
        """
        Property 4: Data Quality Calculation
        
        *For any* Finviz data with varying number of fields, the data_quality
        indicator should correctly reflect the completeness of the data.
        
        **Feature: data-sources-enhancement, Property 4: Finviz Partial Data Handling**
        **Validates: Requirements 4.1, 4.3**
        """
        fetcher = self.get_fetcher()
        
        # 構建測試數據
        data = {
            'price': price,
            'eps_ttm': eps,
            'pe': pe
        }
        
        # 添加額外的非關鍵字段
        for i, field in enumerate(NON_CRITICAL_FIELDS[:num_extra_fields]):
            if field in ['company_name', 'sector', 'industry']:
                data[field] = 'Test Value'
            elif field in ['market_cap', 'volume', 'avg_volume']:
                data[field] = 1000000
            else:
                data[field] = 50.0
        
        result = fetcher._validate_and_supplement_finviz_data(data, 'TEST')
        
        assert result is not None
        
        # 驗證數據質量指標存在且有效
        assert 'data_quality' in result, "Result must include data_quality"
        assert result['data_quality'] in ['complete', 'partial', 'minimal'], \
            f"data_quality must be one of complete/partial/minimal, got {result['data_quality']}"
        
        # 驗證數據質量與缺失字段數量的一致性
        # 如果缺失字段很多（>40%），質量不應該是 complete
        missing_ratio = len(result['missing_fields']) / len(EXPECTED_FINVIZ_FIELDS)
        if missing_ratio > 0.4:
            assert result['data_quality'] != 'complete', \
                f"Quality should not be complete when {missing_ratio*100:.1f}% fields are missing"
        
        # 如果缺失字段很少（<10%），質量應該是 complete
        if missing_ratio < 0.1:
            assert result['data_quality'] == 'complete', \
                f"Quality should be complete when only {missing_ratio*100:.1f}% fields are missing"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
