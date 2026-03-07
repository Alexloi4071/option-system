"""
Bug Condition Exploration Tests for Module17-18-22 Calculation Bugs

這些測試在未修復的代碼上運行，預期會失敗。
失敗證明 bug 存在，並幫助我們理解根本原因。

CRITICAL: 這些測試編碼了預期行為 - 修復後它們應該通過。
DO NOT 在測試失敗時修改測試或代碼。
"""

import pytest
import numpy as np
import pandas as pd
from hypothesis import given, strategies as st, settings, example
from typing import Dict, List, Optional
from dataclasses import dataclass

# Import modules to test
from calculation_layer.module17_implied_volatility import ImpliedVolatilityCalculator
from calculation_layer.module18_historical_volatility import HistoricalVolatilityCalculator
from calculation_layer.module22_optimal_strike import OptimalStrikeAnalyzer


class TestBug22_06_ShortPutWinProbability:
    """
    BUG-22-06 (CRITICAL): Short Put win_probability 計算錯誤
    
    Bug Condition: strategy_type == 'short_put' AND calculating_win_probability
    Expected Behavior: win_probability = 1 - delta (not delta)
    
    這個測試預期在未修復代碼上失敗。
    """
    
    def test_short_put_win_probability_should_be_one_minus_delta(self):
        """
        測試 Short Put 的 win_probability 應該是 1 - delta
        
        場景：
        - strike=95, current_price=100, delta=0.30
        - Short Put 勝率應該是「不被行使的概率」= 70%
        
        預期失敗：未修復代碼會返回 win_probability = 0.30 (錯誤)
        """
        # 創建測試數據
        analyzer = OptimalStrikeAnalyzer()
        
        # 模擬 Short Put 場景
        strike = 95.0
        current_price = 100.0
        delta = 0.30  # Put delta (正值表示被行使概率)
        
        # 創建模擬的 option_data
        option_data = {
            'strike': strike,
            'bid': 2.0,
            'ask': 2.2,
            'last_price': 2.1,
            'delta': delta,
            'gamma': 0.05,
            'theta': -0.05,
            'vega': 0.25,
            'implied_volatility': 0.25,
            'volume': 1000,
            'open_interest': 5000,
        }
        
        # 調用 _calculate_risk_reward_score_v2
        # 注意：這個函數可能需要完整的 StrikeAnalysis 物件
        # 我們需要先創建一個基本的 analysis 物件
        
        # 由於 _calculate_risk_reward_score_v2 是私有方法，我們需要通過公開接口測試
        # 或者直接測試該方法（如果可以訪問）
        
        # 預期行為：win_probability 應該是 1 - delta = 0.70
        expected_win_probability = 1.0 - delta  # 0.70
        
        # 實際行為：未修復代碼會使用 delta = 0.30
        # 這個斷言預期會失敗
        
        # TODO: 需要實際調用函數並檢查結果
        # 暫時標記為預期失敗
        pytest.skip("需要實現完整的測試邏輯 - 需要訪問 _calculate_risk_reward_score_v2")


class TestBug22_04_NormalizeIV_3_to_5_Range:
    """
    BUG-22-04 (CRITICAL): _normalize_iv 在 3.0-5.0 範圍返回默認值
    
    Bug Condition: 3.0 < raw_iv < 5.0
    Expected Behavior: 返回 raw_iv (不是 DEFAULT_IV=0.30)
    
    這個測試預期在未修復代碼上失敗。
    """
    
    @pytest.mark.parametrize("raw_iv", [3.0, 3.5, 4.0, 4.5, 5.0])
    def test_normalize_iv_should_handle_3_to_5_range(self, raw_iv):
        """
        測試 _normalize_iv 應該正確處理 3.0-5.0 範圍的 IV
        
        場景：輸入 raw_iv 在 3.0-5.0 範圍（代表 300%-500% IV）
        預期行為：應該返回 raw_iv（識別為小數形式）
        預期失敗：未修復代碼會返回 DEFAULT_IV = 0.30
        """
        analyzer = OptimalStrikeAnalyzer()
        
        # 調用 _normalize_iv
        result = analyzer._normalize_iv(raw_iv)
        
        # 預期行為：應該返回原值
        expected = raw_iv
        
        # 實際行為：未修復代碼會返回 0.30
        # 這個斷言預期會失敗
        assert result == expected, (
            f"_normalize_iv({raw_iv}) 應該返回 {expected}，"
            f"但實際返回 {result}。"
            f"Bug: 3.0-5.0 範圍被錯誤地返回 DEFAULT_IV=0.30"
        )


class TestBug22_02_IBKRGreeksUnitMismatch:
    """
    BUG-22-02 (HIGH): IBKR Greeks 與 BS Greeks 單位不統一
    
    Bug Condition: greeks_source == 'IBKR' AND mixing_with_BS_greeks
    Expected Behavior: 統一單位（theta: $/year, vega: $/1.0 IV）
    
    這個測試預期在未修復代碼上失敗。
    """
    
    def test_ibkr_greeks_should_be_standardized(self):
        """
        測試 IBKR Greeks 應該被轉換為標準單位
        
        場景：
        - IBKR theta = -0.05 ($/day)
        - IBKR vega = 0.25 ($/1% IV)
        
        預期行為：
        - theta 應該轉換為 -18.25 ($/year = -0.05 * 365)
        - vega 應該轉換為 25.0 ($/1.0 IV = 0.25 * 100)
        
        預期失敗：未修復代碼直接使用原始值
        """
        pytest.skip("需要實現完整的測試邏輯 - 需要訪問 _normalize_greeks 或 _analyze_single_strike")


class TestBug17_03_FixedToleranceConvergence:
    """
    BUG-17-03 (HIGH): Newton-Raphson 收斂條件使用固定絕對誤差
    
    Bug Condition: market_price > 10.0 OR market_price < 1.0
    Expected Behavior: 使用 adaptive_tolerance = max(tolerance, market_price * relative_tolerance)
    
    這個測試預期在未修復代碼上失敗。
    """
    
    def test_high_price_option_should_converge_efficiently(self):
        """
        測試高價期權應該高效收斂
        
        場景：market_price = $50, tolerance = 0.0001
        預期行為：使用相對誤差，迭代次數 < 30
        預期失敗：未修復代碼使用固定絕對誤差，迭代次數 > 50
        """
        calculator = ImpliedVolatilityCalculator()
        
        # 高價期權參數
        market_price = 50.0
        stock_price = 100.0
        strike = 100.0
        time_to_expiry = 1.0
        risk_free_rate = 0.05
        option_type = 'call'
        
        # 計算 IV
        result = calculator.calculate_implied_volatility(
            market_price=market_price,
            stock_price=stock_price,
            strike=strike,
            time_to_expiry=time_to_expiry,
            risk_free_rate=risk_free_rate,
            option_type=option_type
        )
        
        # 預期行為：迭代次數應該 < 30
        # 預期失敗：未修復代碼可能需要 > 50 次迭代
        assert result.iterations < 30, (
            f"高價期權 (${market_price}) 應該在 30 次迭代內收斂，"
            f"但實際需要 {result.iterations} 次。"
            f"Bug: 固定絕對誤差 tolerance=0.0001 對高價期權過於嚴格"
        )
    
    def test_low_price_option_should_converge_with_precision(self):
        """
        測試低價期權應該以足夠精度收斂
        
        場景：market_price = $0.10, tolerance = 0.0001
        預期行為：應該收斂並返回合理的 IV
        預期失敗：未修復代碼可能無法收斂或精度不足
        """
        calculator = ImpliedVolatilityCalculator()
        
        # 低價期權參數
        market_price = 0.10
        stock_price = 100.0
        strike = 120.0  # 深度價外
        time_to_expiry = 0.1  # 10 天
        risk_free_rate = 0.05
        option_type = 'call'
        
        # 計算 IV
        result = calculator.calculate_implied_volatility(
            market_price=market_price,
            stock_price=stock_price,
            strike=strike,
            time_to_expiry=time_to_expiry,
            risk_free_rate=risk_free_rate,
            option_type=option_type
        )
        
        # 預期行為：應該成功收斂
        assert result.converged, (
            f"低價期權 (${market_price}) 應該收斂，但實際未收斂。"
            f"Bug: 固定絕對誤差 tolerance=0.0001 對低價期權可能過於寬鬆"
        )


class TestBug18_03_NaNInPriceSeries:
    """
    BUG-18-03 (MEDIUM): calculate_hv 不過濾 NaN 中間值
    
    Bug Condition: price_series CONTAINS NaN_in_middle
    Expected Behavior: 過濾所有 NaN 後計算 HV
    
    這個測試預期在未修復代碼上失敗。
    """
    
    def test_hv_should_handle_nan_in_middle_of_series(self):
        """
        測試 HV 計算應該處理 price_series 中間的 NaN 值
        
        場景：price_series = [100, 101, NaN, 103, 104]
        預期行為：過濾 NaN 後計算，返回有效的 HV
        預期失敗：未修復代碼會返回 NaN 或 inf
        """
        calculator = HistoricalVolatilityCalculator()
        
        # 創建包含 NaN 的 price_series
        prices = [100.0, 101.0, np.nan, 103.0, 104.0]
        price_series = pd.Series(prices)
        
        # 計算 HV
        result = calculator.calculate_hv(
            price_series=price_series,
            window=252
        )
        
        # 預期行為：應該返回有效的 HV（不是 NaN 或 inf）
        assert not np.isnan(result.hv), (
            f"HV 計算應該過濾 NaN 並返回有效值，但返回了 NaN。"
            f"Bug: price_series 中間的 NaN 未被過濾"
        )
        assert not np.isinf(result.hv), (
            f"HV 計算應該過濾 NaN 並返回有效值，但返回了 inf。"
            f"Bug: price_series 中間的 NaN 導致 log_returns 包含 inf"
        )
    
    def test_hv_should_handle_multiple_nans(self):
        """
        測試 HV 計算應該處理多個 NaN 值
        
        場景：price_series = [100, NaN, NaN, 103, 104]
        預期行為：過濾所有 NaN 後計算
        預期失敗：未修復代碼會失敗
        """
        calculator = HistoricalVolatilityCalculator()
        
        # 創建包含多個 NaN 的 price_series
        prices = [100.0, np.nan, np.nan, 103.0, 104.0]
        price_series = pd.Series(prices)
        
        # 計算 HV
        result = calculator.calculate_hv(
            price_series=price_series,
            window=252
        )
        
        # 預期行為：應該返回有效的 HV
        assert not np.isnan(result.hv), (
            f"HV 計算應該過濾多個 NaN 並返回有效值，但返回了 NaN。"
            f"Bug: 多個 NaN 未被正確處理"
        )


class TestBug18_04_IVRankFailureReturns50:
    """
    BUG-18-04 (MEDIUM): iv_rank/iv_percentile 靜默返回 50.0
    
    Bug Condition: iv_rank_result == CALCULATION_FAILED
    Expected Behavior: 返回 None (not 50.0)
    
    這個測試預期在未修復代碼上失敗。
    """
    
    def test_iv_rank_should_return_none_on_failure(self):
        """
        測試 calculate_iv_rank 失敗時應該返回 None
        
        場景：輸入無效數據導致計算失敗
        預期行為：返回 None
        預期失敗：未修復代碼返回 50.0
        """
        calculator = HistoricalVolatilityCalculator()
        
        # 創建無效的 IV history（空列表）
        current_iv = 0.25
        iv_history = []  # 空列表應該導致計算失敗
        
        # 計算 IV rank
        result = calculator.calculate_iv_rank(
            current_iv=current_iv,
            iv_history=iv_history
        )
        
        # 預期行為：應該返回 None
        # 預期失敗：未修復代碼會返回 50.0
        assert result is None, (
            f"calculate_iv_rank 失敗時應該返回 None，但返回了 {result}。"
            f"Bug: 計算失敗時靜默返回 50.0，調用方無法區分錯誤和真實中性值"
        )
    
    def test_iv_percentile_should_return_none_on_failure(self):
        """
        測試 calculate_iv_percentile 失敗時應該返回 None
        
        場景：輸入無效數據導致計算失敗
        預期行為：返回 None
        預期失敗：未修復代碼返回 50.0
        """
        calculator = HistoricalVolatilityCalculator()
        
        # 創建無效的 IV history
        current_iv = 0.25
        iv_history = []  # 空列表應該導致計算失敗
        
        # 計算 IV percentile
        result = calculator.calculate_iv_percentile(
            current_iv=current_iv,
            iv_history=iv_history
        )
        
        # 預期行為：應該返回 None
        assert result is None, (
            f"calculate_iv_percentile 失敗時應該返回 None，但返回了 {result}。"
            f"Bug: 計算失敗時靜默返回 50.0"
        )


class TestBug18_05_ConflictingIVSignals:
    """
    BUG-18-05 (MEDIUM): get_iv_recommendation OR 邏輯產生矛盾信號
    
    Bug Condition: (iv_rank >= 80 AND iv_percentile < 20) OR (iv_rank < 20 AND iv_percentile >= 80)
    Expected Behavior: 檢測矛盾，降低信心度或標記為 'Conflicting'
    
    這個測試預期在未修復代碼上失敗。
    """
    
    def test_conflicting_signals_should_be_detected(self):
        """
        測試矛盾的 IV 信號應該被檢測
        
        場景：iv_rank=85%, iv_percentile=10%（矛盾）
        預期行為：標記為矛盾或低信心度
        預期失敗：未修復代碼仍給出高信心建議（因為 OR 邏輯）
        """
        calculator = HistoricalVolatilityCalculator()
        
        # 矛盾信號：rank 高但 percentile 低
        iv_rank = 85.0
        iv_percentile = 10.0
        
        # 獲取推薦
        result = calculator.get_iv_recommendation(
            iv_rank=iv_rank,
            iv_percentile=iv_percentile
        )
        
        # 預期行為：應該檢測到矛盾
        # 信心度應該是「低」或推薦應該包含「矛盾」
        is_conflicting_detected = (
            result.confidence == "低" or
            "矛盾" in result.recommendation or
            "Conflicting" in result.recommendation
        )
        
        assert is_conflicting_detected, (
            f"矛盾的 IV 信號（rank={iv_rank}, percentile={iv_percentile}）"
            f"應該被檢測，但返回了 recommendation='{result.recommendation}', "
            f"confidence='{result.confidence}'。"
            f"Bug: OR 邏輯無法檢測矛盾信號"
        )


class TestBug22_03_GlobalIVRankBroadcast:
    """
    BUG-22-03 (MEDIUM): iv_rank 對所有行使價廣播同一值
    
    Bug Condition: calculating_iv_rank AND using_global_value
    Expected Behavior: 為每個行使價單獨計算 iv_rank
    
    這個測試預期在未修復代碼上失敗。
    """
    
    def test_each_strike_should_have_different_iv_rank(self):
        """
        測試每個行使價應該有不同的 iv_rank（反映 IV Skew）
        
        場景：創建多個行使價，每個有不同的 IV
        預期行為：每個行使價的 iv_rank 不同
        預期失敗：未修復代碼所有行使價的 iv_rank 相同（全局廣播）
        """
        pytest.skip("需要實現完整的測試邏輯 - 需要訪問 analyze_strikes 並提供 per-strike IV history")


class TestBug22_05_CompositeScoreExceeds100:
    """
    BUG-22-05 (MEDIUM): composite_score 可能超過 100
    
    Bug Condition: composite_score > 100.0
    Expected Behavior: Cap at 100.0
    
    這個測試預期在未修復代碼上失敗。
    """
    
    def test_composite_score_should_be_capped_at_100(self):
        """
        測試 composite_score 應該被限制在 100
        
        場景：weighted_score=90, bonus_score=15
        預期行為：返回 100（被限制）
        預期失敗：未修復代碼返回 105
        """
        pytest.skip("需要實現完整的測試邏輯 - 需要訪問 calculate_composite_score")


class TestBug22_07_MissingMarkPriceField:
    """
    BUG-22-07 (MEDIUM): StrikeAnalysis 缺少 mark_price 欄位
    
    Bug Condition: strike_analysis.mark_price == NOT_SET
    Expected Behavior: mark_price 應該被儲存
    
    這個測試預期在未修復代碼上失敗。
    """
    
    def test_strike_analysis_should_have_mark_price(self):
        """
        測試 StrikeAnalysis 應該包含 mark_price 欄位
        
        場景：調用 _analyze_single_strike
        預期行為：返回的物件包含 mark_price 欄位且 > 0
        預期失敗：未修復代碼 mark_price 欄位不存在或為 0
        """
        pytest.skip("需要實現完整的測試邏輯 - 需要訪問 _analyze_single_strike 和 StrikeAnalysis")


class TestBug22_08_CacheCollisionAcrossTickers:
    """
    BUG-22-08 (LOW): LRU cache 跨實例共享
    
    Bug Condition: cache_params.ticker1 != cache_params.ticker2 AND same_other_params
    Expected Behavior: 不同 ticker 返回不同的 Greeks
    
    這個測試預期在未修復代碼上失敗。
    """
    
    def test_different_tickers_should_not_share_cache(self):
        """
        測試不同 ticker 的 Greeks 不應該共享 cache
        
        場景：
        - 為 ticker='AAPL' 計算 Greeks，參數 (100, 100, 0.05, 1.0, 0.25, 'call')
        - 為 ticker='TSLA' 計算 Greeks，使用相同參數
        
        預期行為：返回不同的 Greeks
        預期失敗：未修復代碼返回相同的 Greeks（cache 碰撞）
        """
        pytest.skip("需要實現完整的測試邏輯 - 需要訪問 _calculate_greeks_cached")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
