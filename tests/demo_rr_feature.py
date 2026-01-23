# tests/demo_rr_feature.py
"""
演示 Risk/Reward Ratio 功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculation_layer.strategy_recommendation import StrategyRecommender
from output_layer.report_generator import ReportGenerator


def demo_rr_feature():
    """演示 R/R 比率功能"""
    
    print("\n" + "="*80)
    print("策略推薦 Risk/Reward Ratio 功能演示")
    print("="*80)
    
    recommender = StrategyRecommender()
    report_gen = ReportGenerator()
    
    # 場景 1: 看漲趨勢 + 低 IV（適合買入期權）
    print("\n場景 1: 看漲趨勢 + 低 IV")
    print("-" * 80)
    recommendations_1 = recommender.recommend(
        current_price=100.0,
        iv_rank=20.0,
        iv_percentile=15.0,
        iv_hv_ratio=0.7,
        support_level=95.0,
        resistance_level=120.0,
        trend='Up',
        valuation='Undervalued',
        days_to_expiry=60
    )
    
    print(report_gen._format_strategy_recommendations(recommendations_1))
    
    # 場景 2: 看跌趨勢 + 高 IV（適合賣出期權）
    print("\n場景 2: 看跌趨勢 + 高 IV")
    print("-" * 80)
    recommendations_2 = recommender.recommend(
        current_price=100.0,
        iv_rank=75.0,
        iv_percentile=80.0,
        iv_hv_ratio=1.5,
        support_level=85.0,
        resistance_level=105.0,
        trend='Down',
        valuation='Overvalued',
        days_to_expiry=30
    )
    
    print(report_gen._format_strategy_recommendations(recommendations_2))
    
    # 場景 3: 盤整 + 高 IV（適合區間策略）
    print("\n場景 3: 盤整 + 高 IV")
    print("-" * 80)
    recommendations_3 = recommender.recommend(
        current_price=100.0,
        iv_rank=70.0,
        iv_percentile=75.0,
        iv_hv_ratio=1.4,
        support_level=95.0,
        resistance_level=105.0,
        trend='Sideways',
        valuation='Fair',
        days_to_expiry=45
    )
    
    print(report_gen._format_strategy_recommendations(recommendations_3))
    
    # 總結
    print("\n" + "="*80)
    print("功能亮點:")
    print("="*80)
    print("✅ 每個策略都包含風險回報比（R/R Ratio）")
    print("✅ 顯示最大利潤和最大損失")
    print("✅ 根據 R/R 比率自動調整信心度")
    print("✅ 在推薦理由中說明 R/R 情況")
    print("✅ 支持多種策略類型（Long/Short Call/Put, Spreads, Straddles 等）")
    print("✅ 特殊處理無限損失情況（Short Call, Short Straddle）")
    print("\n" + "="*80)


if __name__ == '__main__':
    demo_rr_feature()
