# tests/test_risk_reward_ratio.py
"""
測試策略推薦的風險回報比計算
"""

import pytest
from calculation_layer.strategy_recommendation import StrategyRecommender


class TestRiskRewardRatio:
    """測試 R/R 比率計算"""
    
    def setup_method(self):
        """設置測試環境"""
        self.recommender = StrategyRecommender()
        self.current_price = 100.0
        self.premium = 2.5  # 2.5% of stock price
    
    def test_long_call_rr_calculation(self):
        """測試 Long Call R/R 計算"""
        strike = 105.0
        target_price = 120.0
        
        result = self.recommender._calculate_risk_reward_ratio(
            strategy_name="Long Call",
            current_price=self.current_price,
            strike=strike,
            premium=self.premium,
            target_price=target_price
        )
        
        # Long Call: max_loss = premium, potential_profit = target - strike - premium
        expected_max_loss = self.premium
        expected_profit = target_price - strike - self.premium  # 120 - 105 - 2.5 = 12.5
        expected_rr = expected_profit / expected_max_loss  # 12.5 / 2.5 = 5.0
        
        assert result['max_loss'] == pytest.approx(expected_max_loss, rel=0.01)
        assert result['max_profit'] == pytest.approx(expected_profit, rel=0.01)
        assert result['risk_reward_ratio'] == pytest.approx(expected_rr, rel=0.01)
        assert result['break_even'] == pytest.approx(strike + self.premium, rel=0.01)
    
    def test_long_put_rr_calculation(self):
        """測試 Long Put R/R 計算"""
        strike = 95.0
        target_price = 80.0
        
        result = self.recommender._calculate_risk_reward_ratio(
            strategy_name="Long Put",
            current_price=self.current_price,
            strike=strike,
            premium=self.premium,
            target_price=target_price
        )
        
        # Long Put: max_loss = premium, potential_profit = strike - target - premium
        expected_max_loss = self.premium
        expected_profit = strike - target_price - self.premium  # 95 - 80 - 2.5 = 12.5
        expected_rr = expected_profit / expected_max_loss  # 12.5 / 2.5 = 5.0
        
        assert result['max_loss'] == pytest.approx(expected_max_loss, rel=0.01)
        assert result['max_profit'] == pytest.approx(expected_profit, rel=0.01)
        assert result['risk_reward_ratio'] == pytest.approx(expected_rr, rel=0.01)
        assert result['break_even'] == pytest.approx(strike - self.premium, rel=0.01)
    
    def test_short_put_rr_calculation(self):
        """測試 Short Put R/R 計算"""
        strike = 95.0
        
        result = self.recommender._calculate_risk_reward_ratio(
            strategy_name="Short Put",
            current_price=self.current_price,
            strike=strike,
            premium=self.premium
        )
        
        # Short Put: max_profit = premium, max_loss = strike - premium
        expected_max_loss = strike - self.premium  # 95 - 2.5 = 92.5
        expected_profit = self.premium  # 2.5
        expected_rr = expected_profit / expected_max_loss  # 2.5 / 92.5 ≈ 0.027
        
        assert result['max_loss'] == pytest.approx(expected_max_loss, rel=0.01)
        assert result['max_profit'] == pytest.approx(expected_profit, rel=0.01)
        assert result['risk_reward_ratio'] == pytest.approx(expected_rr, rel=0.01)
        assert result['break_even'] == pytest.approx(strike - self.premium, rel=0.01)
    
    def test_short_call_rr_calculation(self):
        """測試 Short Call R/R 計算"""
        strike = 105.0
        
        result = self.recommender._calculate_risk_reward_ratio(
            strategy_name="Short Call",
            current_price=self.current_price,
            strike=strike,
            premium=self.premium
        )
        
        # Short Call: max_profit = premium, max_loss = inf
        assert result['max_loss'] == float('inf')
        assert result['max_profit'] == pytest.approx(self.premium, rel=0.01)
        assert result['risk_reward_ratio'] is None  # Cannot calculate R/R with infinite loss
        assert result['break_even'] == pytest.approx(strike + self.premium, rel=0.01)
    
    def test_bull_call_spread_rr_calculation(self):
        """測試 Bull Call Spread R/R 計算"""
        strike = 100.0
        
        result = self.recommender._calculate_risk_reward_ratio(
            strategy_name="Bull Call Spread",
            current_price=self.current_price,
            strike=strike,
            premium=self.premium
        )
        
        # Spread: 使用簡化計算
        spread_width = self.current_price * 0.05  # 5.0
        expected_max_loss = spread_width - self.premium  # 5.0 - 2.5 = 2.5
        expected_profit = self.premium  # 2.5
        expected_rr = expected_profit / expected_max_loss  # 2.5 / 2.5 = 1.0
        
        assert result['max_loss'] == pytest.approx(expected_max_loss, rel=0.01)
        assert result['max_profit'] == pytest.approx(expected_profit, rel=0.01)
        assert result['risk_reward_ratio'] == pytest.approx(expected_rr, rel=0.01)
    
    def test_confidence_adjustment_high_rr(self):
        """測試高 R/R 比率時信心度提升"""
        recommendations = self.recommender.recommend(
            current_price=100.0,
            iv_rank=25.0,  # Low IV
            iv_percentile=20.0,
            iv_hv_ratio=0.75,
            support_level=95.0,
            resistance_level=110.0,
            trend='Up',
            valuation='Undervalued',
            days_to_expiry=45
        )
        
        # 應該有 Long Call 推薦
        long_call_recs = [r for r in recommendations if 'Long Call' in r.strategy_name]
        assert len(long_call_recs) > 0
        
        # 檢查是否有 R/R 比率
        for rec in long_call_recs:
            assert rec.risk_reward_ratio is not None
            assert rec.max_profit is not None
            assert rec.max_loss is not None
            
            # 如果 R/R > 2.0，應該提升信心度或在 reasoning 中提到
            if rec.risk_reward_ratio and rec.risk_reward_ratio > 2.0:
                assert rec.confidence in ['High', 'Medium']
                # 檢查 reasoning 中是否提到 R/R
                reasoning_text = ' '.join(rec.reasoning)
                assert '風險回報比' in reasoning_text or 'R/R' in reasoning_text.upper()
    
    def test_confidence_adjustment_low_rr(self):
        """測試低 R/R 比率時信心度降低"""
        recommendations = self.recommender.recommend(
            current_price=100.0,
            iv_rank=75.0,  # High IV
            iv_percentile=80.0,
            iv_hv_ratio=1.5,
            support_level=95.0,
            resistance_level=105.0,
            trend='Up',
            valuation='Fair',
            days_to_expiry=30
        )
        
        # 應該有 Short Put 推薦
        short_put_recs = [r for r in recommendations if 'Short Put' in r.strategy_name]
        assert len(short_put_recs) > 0
        
        # Short Put 通常 R/R < 1.0
        for rec in short_put_recs:
            if rec.risk_reward_ratio and rec.risk_reward_ratio < 1.0:
                # 信心度不應該是 High（如果原本是 High 應該降低）
                # 或者在 reasoning 中提到低 R/R
                reasoning_text = ' '.join(rec.reasoning)
                if rec.confidence == 'High':
                    # 如果仍然是 High，應該有其他強烈理由
                    assert len(rec.reasoning) >= 3
    
    def test_boundary_condition_zero_max_loss(self):
        """測試邊界條件：max_loss = 0"""
        # 這種情況理論上不應該發生，但測試健壯性
        result = self.recommender._calculate_risk_reward_ratio(
            strategy_name="Custom Strategy",
            current_price=self.current_price,
            strike=self.current_price,
            premium=0.0,  # 零期權金
            target_price=self.current_price * 1.1,
            stop_loss=self.current_price
        )
        
        # 當 max_loss = 0 時，R/R 應該無法計算
        # 但函數應該正常返回而不崩潰
        assert result is not None
        assert 'risk_reward_ratio' in result
        assert 'max_profit' in result
        assert 'max_loss' in result
    
    def test_boundary_condition_infinite_max_loss(self):
        """測試邊界條件：max_loss = inf"""
        result = self.recommender._calculate_risk_reward_ratio(
            strategy_name="Short Call",
            current_price=self.current_price,
            strike=105.0,
            premium=self.premium
        )
        
        # Short Call 的 max_loss 是無限的
        assert result['max_loss'] == float('inf')
        assert result['risk_reward_ratio'] is None
        assert result['max_profit'] > 0
    
    def test_rr_in_recommendation_output(self):
        """測試 R/R 比率是否正確輸出到推薦結果"""
        recommendations = self.recommender.recommend(
            current_price=100.0,
            iv_rank=30.0,
            iv_percentile=25.0,
            iv_hv_ratio=0.8,
            support_level=95.0,
            resistance_level=110.0,
            trend='Up',
            valuation='Undervalued',
            days_to_expiry=45
        )
        
        assert len(recommendations) > 0
        
        # 檢查每個推薦是否包含 R/R 信息
        for rec in recommendations:
            rec_dict = rec.to_dict()
            assert 'risk_reward_ratio' in rec_dict
            assert 'max_profit' in rec_dict
            assert 'max_loss' in rec_dict
            
            # 如果有 suggested_strike，應該有 R/R 計算
            if rec.suggested_strike:
                assert rec.risk_reward_ratio is not None or rec.max_loss == float('inf')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
