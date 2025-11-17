# tests/test_data_fetcher_integration.py
"""
DataFetcher 集成測試
測試降級策略、自主計算和 API 狀態報告

測試範圍:
- 降級策略的完整流程
- 模擬 API 失敗場景
- 驗證自主計算被正確調用
- 驗證 API 狀態報告準確性
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import logging
import sys
import os

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer.data_fetcher import DataFetcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestDataFetcherFallbackStrategy(unittest.TestCase):
    """測試 DataFetcher 降級策略"""
    
    def setUp(self):
        """測試初始化"""
        logger.info("=" * 70)
        logger.info("TestDataFetcherFallbackStrategy 測試開始")
        
        # 創建 DataFetcher 實例（不使用 IBKR）
        with patch('data_layer.data_fetcher.IBKR_AVAILABLE', False):
            self.fetcher = DataFetcher(use_ibkr=False)
    
    def test_greeks_fallback_to_self_calculated(self):
        """
        測試 Greeks 降級到自主計算
        
        場景: IBKR 和 Yahoo V2 都失敗，應該使用自主計算
        """
        logger.info("✓ 測試: Greeks 降級到自主計算")
        
        # 模擬 IBKR 不可用
        self.fetcher.ibkr_client = None
        
        # 模擬 Yahoo V2 不可用
        self.fetcher.yahoo_v2_client = None
        
        # 確保自主計算模塊可用
        if not self.fetcher.greeks_calculator:
            logger.warning("  ⚠ 自主計算模塊不可用，跳過測試")
            self.skipTest("自主計算模塊不可用")
        
        # 調用 get_option_greeks（應該降級到自主計算）
        greeks = self.fetcher.get_option_greeks(
            ticker='AAPL',
            strike=150.0,
            expiration='2025-12-19',
            option_type='C',
            stock_price=150.0,
            iv=0.25,
            risk_free_rate=0.05
        )
        
        # 驗證結果
        self.assertIsNotNone(greeks, "Greeks 不應該為 None")
        self.assertIn('delta', greeks, "應該包含 delta")
        self.assertIn('gamma', greeks, "應該包含 gamma")
        self.assertIn('theta', greeks, "應該包含 theta")
        self.assertIn('vega', greeks, "應該包含 vega")
        self.assertIn('rho', greeks, "應該包含 rho")
        self.assertIn('source', greeks, "應該包含 source")
        
        # 驗證來源是自主計算
        self.assertIn('Self-Calculated', greeks['source'], 
                     f"來源應該是自主計算，實際: {greeks['source']}")
        
        # 驗證 Delta 範圍（Call 期權應該在 0-1 之間）
        self.assertGreaterEqual(greeks['delta'], 0, "Call Delta 應該 >= 0")
        self.assertLessEqual(greeks['delta'], 1, "Call Delta 應該 <= 1")
        
        # 驗證 Gamma 為正數
        self.assertGreater(greeks['gamma'], 0, "Gamma 應該 > 0")
        
        logger.info(f"  ✓ Greeks 計算成功: Delta={greeks['delta']:.4f}")
        logger.info(f"  ✓ 數據來源: {greeks['source']}")
    
    def test_greeks_fallback_to_default(self):
        """
        測試 Greeks 降級到默認值
        
        場景: 所有方案都失敗，應該返回默認值
        """
        logger.info("✓ 測試: Greeks 降級到默認值")
        
        # 模擬所有數據源不可用
        self.fetcher.ibkr_client = None
        self.fetcher.yahoo_v2_client = None
        self.fetcher.greeks_calculator = None
        
        # 調用 get_option_greeks（應該返回默認值）
        greeks = self.fetcher.get_option_greeks(
            ticker='AAPL',
            strike=150.0,
            expiration='2025-12-19',
            option_type='C'
        )
        
        # 驗證結果
        self.assertIsNotNone(greeks, "應該返回默認值而不是 None")
        self.assertIn('Default', greeks['source'], 
                     f"來源應該是默認值，實際: {greeks['source']}")
        
        # 驗證默認值
        self.assertEqual(greeks['delta'], 0.5, "Call 默認 Delta 應該是 0.5")
        
        logger.info(f"  ✓ 返回默認值: {greeks['source']}")


class TestImpliedVolatilityValidation(unittest.TestCase):
    """測試隱含波動率驗證功能"""
    
    def setUp(self):
        """測試初始化"""
        logger.info("=" * 70)
        logger.info("TestImpliedVolatilityValidation 測試開始")
        
        with patch('data_layer.data_fetcher.IBKR_AVAILABLE', False):
            self.fetcher = DataFetcher(use_ibkr=False)
    
    @patch('data_layer.data_fetcher.DataFetcher.get_option_chain')
    @patch('data_layer.data_fetcher.DataFetcher.get_stock_info')
    @patch('data_layer.data_fetcher.DataFetcher.get_risk_free_rate')
    def test_iv_validation_with_api_data(self, mock_rate, mock_stock, mock_chain):
        """
        測試 IV 驗證（有 API 數據）
        
        場景: API 提供 IV，反推計算也成功，對比兩者
        """
        logger.info("✓ 測試: IV 驗證（有 API 數據）")
        
        # 確保 IV 計算器可用
        if not self.fetcher.iv_calculator:
            logger.warning("  ⚠ IV 計算器不可用，跳過測試")
            self.skipTest("IV 計算器不可用")
        
        # 模擬股價數據
        mock_stock.return_value = {'current_price': 150.0}
        
        # 模擬無風險利率
        mock_rate.return_value = 5.0
        
        # 模擬期權鏈數據
        import pandas as pd
        mock_chain_data = {
            'calls': pd.DataFrame({
                'strike': [150.0],
                'lastPrice': [10.0],
                'impliedVolatility': [25.0]  # 25%
            }),
            'puts': pd.DataFrame(),
            'expiration': '2025-12-19',
            'data_source': 'mock'
        }
        mock_chain.return_value = mock_chain_data
        
        # 調用 IV 驗證
        result = self.fetcher.get_implied_volatility_with_validation(
            ticker='AAPL',
            strike=150.0,
            expiration='2025-12-19',
            option_type='C',
            market_price=10.0
        )
        
        # 驗證結果
        self.assertIsNotNone(result, "IV 驗證結果不應該為 None")
        self.assertIn('api_iv', result)
        self.assertIn('calculated_iv', result)
        self.assertIn('iv_difference', result)
        self.assertIn('validation_passed', result)
        self.assertIn('recommended_iv', result)
        self.assertIn('converged', result)
        
        logger.info(f"  ✓ API IV: {result['api_iv']:.2f}%")
        logger.info(f"  ✓ 計算 IV: {result['calculated_iv']:.2f}%")
        logger.info(f"  ✓ 差異: {result['iv_difference']:.2f}%")
        logger.info(f"  ✓ 驗證通過: {result['validation_passed']}")
        logger.info(f"  ✓ 推薦 IV: {result['recommended_iv']:.2f}%")


class TestOptionTheoreticalPrice(unittest.TestCase):
    """測試期權理論價計算功能"""
    
    def setUp(self):
        """測試初始化"""
        logger.info("=" * 70)
        logger.info("TestOptionTheoreticalPrice 測試開始")
        
        with patch('data_layer.data_fetcher.IBKR_AVAILABLE', False):
            self.fetcher = DataFetcher(use_ibkr=False)
    
    @patch('data_layer.data_fetcher.DataFetcher.get_stock_info')
    @patch('data_layer.data_fetcher.DataFetcher.extract_implied_volatility')
    @patch('data_layer.data_fetcher.DataFetcher.get_risk_free_rate')
    def test_theoretical_price_calculation(self, mock_rate, mock_iv, mock_stock):
        """
        測試期權理論價計算
        
        場景: 使用 BS 模型計算期權理論價
        """
        logger.info("✓ 測試: 期權理論價計算")
        
        # 確保 BS 計算器可用
        if not self.fetcher.bs_calculator:
            logger.warning("  ⚠ BS 計算器不可用，跳過測試")
            self.skipTest("BS 計算器不可用")
        
        # 模擬數據
        mock_stock.return_value = {'current_price': 150.0}
        mock_iv.return_value = 25.0  # 25%
        mock_rate.return_value = 5.0  # 5%
        
        # 調用理論價計算
        result = self.fetcher.get_option_theoretical_price(
            ticker='AAPL',
            strike=150.0,
            expiration='2025-12-19',
            option_type='C'
        )
        
        # 驗證結果
        self.assertIsNotNone(result, "理論價結果不應該為 None")
        self.assertIn('theoretical_price', result)
        self.assertIn('stock_price', result)
        self.assertIn('strike_price', result)
        self.assertIn('volatility', result)
        self.assertIn('risk_free_rate', result)
        self.assertIn('time_to_expiration', result)
        self.assertIn('option_type', result)
        self.assertIn('d1', result)
        self.assertIn('d2', result)
        self.assertIn('data_source', result)
        
        # 驗證理論價在合理範圍內
        self.assertGreater(result['theoretical_price'], 0, "理論價應該 > 0")
        self.assertLess(result['theoretical_price'], result['stock_price'], 
                       "Call 理論價應該 < 股價（對於 ATM 期權）")
        
        # 驗證數據來源
        self.assertIn('Black-Scholes', result['data_source'])
        
        logger.info(f"  ✓ 理論價: ${result['theoretical_price']:.2f}")
        logger.info(f"  ✓ 股價: ${result['stock_price']:.2f}")
        logger.info(f"  ✓ 波動率: {result['volatility_percent']:.2f}%")
        logger.info(f"  ✓ 數據來源: {result['data_source']}")
    
    def test_theoretical_price_with_provided_params(self):
        """
        測試使用提供的參數計算理論價
        
        場景: 直接提供所有參數，不需要從 API 獲取
        """
        logger.info("✓ 測試: 使用提供參數計算理論價")
        
        if not self.fetcher.bs_calculator:
            logger.warning("  ⚠ BS 計算器不可用，跳過測試")
            self.skipTest("BS 計算器不可用")
        
        # 直接提供所有參數
        result = self.fetcher.get_option_theoretical_price(
            ticker='AAPL',
            strike=150.0,
            expiration='2025-12-19',
            option_type='C',
            stock_price=150.0,
            volatility=0.25,  # 25%
            risk_free_rate=0.05  # 5%
        )
        
        # 驗證結果
        self.assertIsNotNone(result)
        self.assertGreater(result['theoretical_price'], 0)
        
        logger.info(f"  ✓ 理論價: ${result['theoretical_price']:.2f}")


class TestAPIStatusReport(unittest.TestCase):
    """測試 API 狀態報告功能"""
    
    def setUp(self):
        """測試初始化"""
        logger.info("=" * 70)
        logger.info("TestAPIStatusReport 測試開始")
        
        with patch('data_layer.data_fetcher.IBKR_AVAILABLE', False):
            self.fetcher = DataFetcher(use_ibkr=False)
    
    def test_api_status_report_structure(self):
        """
        測試 API 狀態報告結構
        
        驗證報告包含所有必要字段
        """
        logger.info("✓ 測試: API 狀態報告結構")
        
        report = self.fetcher.get_api_status_report()
        
        # 驗證原有字段
        self.assertIn('api_failures', report)
        self.assertIn('fallback_used', report)
        self.assertIn('ibkr_enabled', report)
        self.assertIn('ibkr_connected', report)
        
        # 驗證新增字段
        self.assertIn('statistics', report)
        self.assertIn('self_calculation_available', report)
        
        # 驗證統計字段
        stats = report['statistics']
        self.assertIn('total_fallback_calls', stats)
        self.assertIn('total_api_failures', stats)
        self.assertIn('self_calculated_count', stats)
        self.assertIn('self_calculated_percentage', stats)
        self.assertIn('self_calculated_types', stats)
        self.assertIn('api_failure_counts', stats)
        self.assertIn('fallback_by_type', stats)
        
        # 驗證自主計算可用性
        self_calc = report['self_calculation_available']
        self.assertIn('bs_calculator', self_calc)
        self.assertIn('greeks_calculator', self_calc)
        self.assertIn('iv_calculator', self_calc)
        
        logger.info("  ✓ 報告結構完整")
        logger.info(f"  ✓ 總降級調用: {stats['total_fallback_calls']}")
        logger.info(f"  ✓ 自主計算次數: {stats['self_calculated_count']}")
        logger.info(f"  ✓ 自主計算百分比: {stats['self_calculated_percentage']:.2f}%")
    
    def test_api_status_report_with_fallbacks(self):
        """
        測試有降級記錄的 API 狀態報告
        
        模擬一些降級調用，驗證統計準確性
        """
        logger.info("✓ 測試: 有降級記錄的 API 狀態報告")
        
        # 模擬一些降級調用
        # 注意: _record_fallback 不會添加重複的 source，所以每個 data_type 只記錄一次
        self.fetcher._record_fallback('option_greeks', 'self_calculated')
        self.fetcher._record_fallback('option_greeks', 'self_calculated')  # 重複，不會被添加
        self.fetcher._record_fallback('option_chain', 'yfinance')
        self.fetcher._record_fallback('option_theoretical_price', 'bs_calculated')
        
        # 模擬一些 API 失敗
        self.fetcher._record_api_failure('ibkr', 'Connection failed')
        self.fetcher._record_api_failure('yahoo_v2', 'Authentication failed')
        
        report = self.fetcher.get_api_status_report()
        stats = report['statistics']
        
        # 驗證統計（實際只有 3 次不同的降級調用，因為重複的不會被添加）
        self.assertEqual(stats['total_fallback_calls'], 3, "應該有 3 次降級調用")
        self.assertEqual(stats['self_calculated_count'], 2, "應該有 2 次自主計算")
        self.assertEqual(stats['total_api_failures'], 2, "應該有 2 次 API 失敗")
        
        # 驗證自主計算百分比
        expected_percentage = round((2 / 3) * 100, 2)
        self.assertEqual(stats['self_calculated_percentage'], expected_percentage)
        
        # 驗證自主計算類型
        self.assertIn('option_greeks', stats['self_calculated_types'])
        self.assertIn('option_theoretical_price', stats['self_calculated_types'])
        
        logger.info(f"  ✓ 總降級調用: {stats['total_fallback_calls']}")
        logger.info(f"  ✓ 自主計算次數: {stats['self_calculated_count']}")
        logger.info(f"  ✓ 自主計算百分比: {stats['self_calculated_percentage']:.2f}%")
        logger.info(f"  ✓ API 失敗次數: {stats['total_api_failures']}")


class TestIntegrationWorkflow(unittest.TestCase):
    """測試完整的集成工作流程"""
    
    def setUp(self):
        """測試初始化"""
        logger.info("=" * 70)
        logger.info("TestIntegrationWorkflow 測試開始")
        
        with patch('data_layer.data_fetcher.IBKR_AVAILABLE', False):
            self.fetcher = DataFetcher(use_ibkr=False)
    
    def test_complete_fallback_workflow(self):
        """
        測試完整的降級工作流程
        
        場景: 
        1. 嘗試獲取 Greeks（API 失敗）
        2. 降級到自主計算
        3. 驗證結果
        4. 檢查狀態報告
        """
        logger.info("✓ 測試: 完整降級工作流程")
        
        # 確保自主計算可用
        if not self.fetcher.greeks_calculator:
            logger.warning("  ⚠ 自主計算模塊不可用，跳過測試")
            self.skipTest("自主計算模塊不可用")
        
        # 步驟1: 模擬 API 不可用
        self.fetcher.ibkr_client = None
        self.fetcher.yahoo_v2_client = None
        
        # 步驟2: 調用 get_option_greeks（應該降級到自主計算）
        greeks = self.fetcher.get_option_greeks(
            ticker='AAPL',
            strike=150.0,
            expiration='2025-12-19',
            option_type='C',
            stock_price=150.0,
            iv=0.25,
            risk_free_rate=0.05
        )
        
        # 步驟3: 驗證結果
        self.assertIsNotNone(greeks)
        self.assertIn('Self-Calculated', greeks['source'])
        
        # 步驟4: 檢查狀態報告
        report = self.fetcher.get_api_status_report()
        stats = report['statistics']
        
        # 驗證自主計算被記錄
        self.assertGreater(stats['self_calculated_count'], 0, "應該有自主計算記錄")
        self.assertIn('option_greeks', stats['self_calculated_types'])
        
        logger.info("  ✓ 完整工作流程測試通過")
        logger.info(f"  ✓ Greeks 來源: {greeks['source']}")
        logger.info(f"  ✓ 自主計算次數: {stats['self_calculated_count']}")


if __name__ == '__main__':
    # 運行測試
    unittest.main(verbosity=2)
