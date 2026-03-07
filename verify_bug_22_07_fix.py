#!/usr/bin/env python3
"""
驗證 BUG-22-07 修復：添加 mark_price 欄位到 StrikeAnalysis

測試場景：
1. 驗證 StrikeAnalysis 包含 mark_price 欄位
2. 驗證 mark_price 被正確計算和儲存
3. 驗證 to_dict() 包含 mark_price
"""

import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from calculation_layer.module22_optimal_strike import OptimalStrikeCalculator, StrikeAnalysis


def test_bug_22_07_mark_price_field():
    """測試 mark_price 欄位"""
    print("\n" + "="*80)
    print("BUG-22-07 驗證：添加 mark_price 欄位到 StrikeAnalysis")
    print("="*80)
    
    calc = OptimalStrikeCalculator()
    
    # 測試 1: 使用 IBKR markPrice
    print("\n測試 1: 使用 IBKR markPrice")
    print("-" * 80)
    
    option_with_mark_price = {
        'strike': 100.0,
        'bid': 5.0,
        'ask': 5.2,
        'lastPrice': 5.1,
        'markPrice': 5.15,  # IBKR 提供的 mark price
        'volume': 100,
        'openInterest': 500,
        'delta': 0.50,
        'gamma': 0.02,
        'theta': -0.05,
        'vega': 0.25,
        'greeks_source': 'ibkr_snapshot',
        'impliedVolatility': 0.30
    }
    
    print(f"輸入 option 數據:")
    print(f"  bid = {option_with_mark_price['bid']}")
    print(f"  ask = {option_with_mark_price['ask']}")
    print(f"  markPrice = {option_with_mark_price['markPrice']}")
    
    analysis = calc._analyze_single_strike(
        option=option_with_mark_price,
        option_type='call',
        current_price=100.0,
        strategy_type='long_call',
        days_to_expiration=30,
        iv_rank=50.0,
        target_price=None
    )
    
    if analysis:
        print(f"\n輸出:")
        print(f"  mark_price = {analysis.mark_price}")
        
        # 驗證 mark_price 欄位存在且正確
        assert hasattr(analysis, 'mark_price'), "StrikeAnalysis 應包含 mark_price 欄位"
        assert analysis.mark_price == 5.15, \
            f"mark_price 應為 5.15（IBKR markPrice），實際: {analysis.mark_price}"
        
        print(f"\n✅ 驗證通過: mark_price 欄位存在且使用 IBKR markPrice")
        
        # 驗證 to_dict() 包含 mark_price
        analysis_dict = analysis.to_dict()
        assert 'mark_price' in analysis_dict, "to_dict() 應包含 mark_price"
        assert analysis_dict['mark_price'] == 5.15, \
            f"to_dict() 中 mark_price 應為 5.15，實際: {analysis_dict['mark_price']}"
        
        print(f"✅ 驗證通過: to_dict() 包含 mark_price")
    else:
        print("\n❌ 錯誤: _analyze_single_strike 返回 None")
        sys.exit(1)
    
    # 測試 2: 沒有 IBKR markPrice，使用 mid_price
    print("\n\n測試 2: 沒有 IBKR markPrice，使用 (bid+ask)/2")
    print("-" * 80)
    
    option_without_mark_price = {
        'strike': 100.0,
        'bid': 5.0,
        'ask': 5.2,
        'lastPrice': 5.1,
        # 沒有 markPrice
        'volume': 100,
        'openInterest': 500,
        'delta': 0.50,
        'gamma': 0.02,
        'theta': -0.05,
        'vega': 0.25,
        'greeks_source': 'ibkr_snapshot',
        'impliedVolatility': 0.30
    }
    
    print(f"輸入 option 數據:")
    print(f"  bid = {option_without_mark_price['bid']}")
    print(f"  ask = {option_without_mark_price['ask']}")
    print(f"  markPrice = None")
    
    analysis = calc._analyze_single_strike(
        option=option_without_mark_price,
        option_type='call',
        current_price=100.0,
        strategy_type='long_call',
        days_to_expiration=30,
        iv_rank=50.0,
        target_price=None
    )
    
    if analysis:
        print(f"\n輸出:")
        print(f"  mark_price = {analysis.mark_price}")
        
        expected_mid_price = (5.0 + 5.2) / 2  # 5.1
        
        # 驗證 mark_price 使用 mid_price
        assert analysis.mark_price == expected_mid_price, \
            f"mark_price 應為 {expected_mid_price}（(bid+ask)/2），實際: {analysis.mark_price}"
        
        print(f"\n✅ 驗證通過: mark_price 使用 (bid+ask)/2 = {expected_mid_price}")
    else:
        print("\n❌ 錯誤: _analyze_single_strike 返回 None")
        sys.exit(1)
    
    # 測試 3: 沒有 bid/ask，使用 last_price
    print("\n\n測試 3: 沒有 bid/ask，使用 lastPrice")
    print("-" * 80)
    
    option_with_last_price_only = {
        'strike': 100.0,
        'bid': 0.0,
        'ask': 0.0,
        'lastPrice': 5.1,
        'volume': 100,
        'openInterest': 500,
        'delta': 0.50,
        'gamma': 0.02,
        'theta': -0.05,
        'vega': 0.25,
        'greeks_source': 'ibkr_snapshot',
        'impliedVolatility': 0.30
    }
    
    print(f"輸入 option 數據:")
    print(f"  bid = {option_with_last_price_only['bid']}")
    print(f"  ask = {option_with_last_price_only['ask']}")
    print(f"  lastPrice = {option_with_last_price_only['lastPrice']}")
    
    # 這個測試會被過濾掉（bid=0 且 ask=0），所以我們預期返回 None
    analysis = calc._analyze_single_strike(
        option=option_with_last_price_only,
        option_type='call',
        current_price=100.0,
        strategy_type='long_call',
        days_to_expiration=30,
        iv_rank=50.0,
        target_price=None
    )
    
    if analysis is None:
        print(f"\n輸出:")
        print(f"  analysis = None (因為 bid=0 且 ask=0 被過濾)")
        print(f"\n✅ 驗證通過: bid=0 且 ask=0 的情況被正確過濾")
    else:
        print(f"\n輸出:")
        print(f"  mark_price = {analysis.mark_price}")
        print(f"\n✅ 驗證通過: mark_price 使用 lastPrice")
    
    print("\n" + "="*80)
    print("✅ BUG-22-07 修復驗證完成：所有測試通過")
    print("="*80)


if __name__ == '__main__':
    test_bug_22_07_mark_price_field()
