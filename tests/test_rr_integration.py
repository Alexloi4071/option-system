# tests/test_rr_integration.py
"""
集成測試：驗證 R/R 比率功能的完整流程
"""

import pytest
from calculation_layer.strategy_recommendation import StrategyRecommender
from output_layer.report_generator import ReportGenerator


class TestRRIntegration:
    """測試 R/R 比率的完整集成"""
    
    def test_end_to_end_rr_workflow(self):
        """測試從推薦生成到報告輸出的完整流程"""
        # 1. 生成策略推薦
        recommender = StrategyRecommender()
        recommendations = recommender.recommend(
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
        
        # 2. 驗證推薦包含 R/R 信息
        assert len(recommendations) > 0
        for rec in recommendations:
            if rec.suggested_strike:
                assert rec.risk_reward_ratio is not None or rec.max_loss == float('inf')
                assert rec.max_profit is not None
                assert rec.max_loss is not None
        
        # 3. 生成報告
        report_gen = ReportGenerator()
        report_text = report_gen._format_strategy_recommendations(recommendations)
        
        # 4. 驗證報告包含 R/R 信息
        assert '風險回報比' in report_text or 'R/R' in report_text.upper()
        assert '最大利潤' in report_text
        assert '最大損失' in report_text
        
        # 5. 驗證報告格式正確
        assert '策略推薦分析' in report_text
        assert '信心度' in report_text
        
        print("\n" + "="*70)
        print("集成測試報告輸出:")
        print("="*70)
        print(report_text)
    
    def test_rr_affects_confidence_in_report(self):
        """測試 R/R 比率影響信心度並反映在報告中"""
        recommender = StrategyRecommender()
        
        # 生成推薦（應該有高 R/R 的 Long Call）
        recommendations = recommender.recommend(
            current_price=100.0,
            iv_rank=20.0,  # Very low IV
            iv_percentile=15.0,
            iv_hv_ratio=0.7,
            support_level=95.0,
            resistance_level=120.0,  # 大幅上漲空間
            trend='Up',
            valuation='Undervalued',
            days_to_expiry=60
        )
        
        # 找到 Long Call 推薦
        long_call_recs = [r for r in recommendations if 'Long Call' in r.strategy_name]
        assert len(long_call_recs) > 0
        
        # 驗證高 R/R 導致高信心度
        for rec in long_call_recs:
            if rec.risk_reward_ratio and rec.risk_reward_ratio > 2.0:
                # 應該有高信心度或在 reasoning 中提到 R/R
                reasoning_text = ' '.join(rec.reasoning)
                assert rec.confidence in ['High', 'Medium'] or '風險回報比' in reasoning_text
        
        # 生成報告並驗證
        report_gen = ReportGenerator()
        report_text = report_gen._format_strategy_recommendations(recommendations)
        
        # 報告應該包含 R/R 信息
        assert '風險回報比' in report_text
        print("\n" + "="*70)
        print("高 R/R 比率報告:")
        print("="*70)
        print(report_text)
    
    def test_dict_and_object_compatibility(self):
        """測試報告生成器同時支持字典和對象格式"""
        recommender = StrategyRecommender()
        recommendations = recommender.recommend(
            current_price=100.0,
            iv_rank=50.0,
            iv_percentile=50.0,
            iv_hv_ratio=1.0,
            support_level=95.0,
            resistance_level=105.0,
            trend='Sideways',
            valuation='Fair',
            days_to_expiry=30
        )
        
        report_gen = ReportGenerator()
        
        # 測試對象格式
        report_obj = report_gen._format_strategy_recommendations(recommendations)
        assert '策略推薦分析' in report_obj
        
        # 測試字典格式
        recommendations_dict = [rec.to_dict() for rec in recommendations]
        report_dict = report_gen._format_strategy_recommendations(recommendations_dict)
        assert '策略推薦分析' in report_dict
        
        # 兩種格式應該產生相似的報告
        assert len(report_obj) > 0
        assert len(report_dict) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
