#!/usr/bin/env python3
"""
驗證 BUG-18-05 修復：get_iv_recommendation 一致性檢查

測試場景：
1. 矛盾信號（rank 高 percentile 低）
2. 矛盾信號（rank 低 percentile 高）
3. 一致信號（兩者都高）- Preservation
4. 一致信號（兩者都低）- Preservation
"""

import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from calculation_layer.module18_historical_volatility import HistoricalVolatilityCalculator


def test_bug_18_05_consistency_check():
    """測試 IV 信號一致性檢查"""
    print("\n" + "="*80)
    print("BUG-18-05 驗證：get_iv_recommendation 一致性檢查")
    print("="*80)
    
    calc = HistoricalVolatilityCalculator()
    
    # 測試 1: 矛盾信號（rank 高 percentile 低）
    print("\n測試 1: 矛盾信號（rank=85%, percentile=10%）")
    print("-" * 80)
    
    iv_rank = 85.0
    iv_percentile = 10.0
    
    print(f"輸入:")
    print(f"  iv_rank = {iv_rank}%")
    print(f"  iv_percentile = {iv_percentile}%")
    print(f"  差異 = {abs(iv_rank - iv_percentile):.1f} 個百分點")
    
    result = calc.get_iv_recommendation(iv_rank, iv_percentile)
    
    print(f"\n輸出:")
    print(f"  action = {result['action']}")
    print(f"  confidence = {result['confidence']}")
    print(f"  reason = {result['reason']}")
    
    # 驗證檢測到矛盾
    assert result['action'] == 'Neutral', f"應為 Neutral，實際: {result['action']}"
    assert result['confidence'] == 'Low', f"應為 Low，實際: {result['confidence']}"
    assert '矛盾' in result['reason'], f"原因應包含'矛盾'，實際: {result['reason']}"
    
    print(f"\n✅ 驗證通過: 檢測到矛盾信號，返回 Neutral/Low")
    
    # 測試 2: 矛盾信號（rank 低 percentile 高）
    print("\n\n測試 2: 矛盾信號（rank=15%, percentile=90%）")
    print("-" * 80)
    
    iv_rank = 15.0
    iv_percentile = 90.0
    
    print(f"輸入:")
    print(f"  iv_rank = {iv_rank}%")
    print(f"  iv_percentile = {iv_percentile}%")
    print(f"  差異 = {abs(iv_rank - iv_percentile):.1f} 個百分點")
    
    result = calc.get_iv_recommendation(iv_rank, iv_percentile)
    
    print(f"\n輸出:")
    print(f"  action = {result['action']}")
    print(f"  confidence = {result['confidence']}")
    print(f"  reason = {result['reason']}")
    
    # 驗證檢測到矛盾
    assert result['action'] == 'Neutral', f"應為 Neutral，實際: {result['action']}"
    assert result['confidence'] == 'Low', f"應為 Low，實際: {result['confidence']}"
    
    print(f"\n✅ 驗證通過: 檢測到矛盾信號，返回 Neutral/Low")
    
    # 測試 3: 一致信號（兩者都高）- Preservation
    print("\n\n測試 3: 一致信號（rank=85%, percentile=82%）- Preservation")
    print("-" * 80)
    
    iv_rank = 85.0
    iv_percentile = 82.0
    
    print(f"輸入:")
    print(f"  iv_rank = {iv_rank}%")
    print(f"  iv_percentile = {iv_percentile}%")
    
    result = calc.get_iv_recommendation(iv_rank, iv_percentile)
    
    print(f"\n輸出:")
    print(f"  action = {result['action']}")
    print(f"  confidence = {result['confidence']}")
    print(f"  reason = {result['reason']}")
    
    # 驗證一致信號給出正確建議
    assert result['action'] == 'Short', f"應為 Short，實際: {result['action']}"
    assert result['confidence'] == 'High', f"應為 High，實際: {result['confidence']}"
    
    print(f"\n✅ 驗證通過: 一致高信號，返回 Short/High")
    
    # 測試 4: 一致信號（兩者都低）- Preservation
    print("\n\n測試 4: 一致信號（rank=15%, percentile=25%）- Preservation")
    print("-" * 80)
    
    iv_rank = 15.0
    iv_percentile = 25.0
    
    print(f"輸入:")
    print(f"  iv_rank = {iv_rank}%")
    print(f"  iv_percentile = {iv_percentile}%")
    
    result = calc.get_iv_recommendation(iv_rank, iv_percentile)
    
    print(f"\n輸出:")
    print(f"  action = {result['action']}")
    print(f"  confidence = {result['confidence']}")
    print(f"  reason = {result['reason']}")
    
    # 驗證一致信號給出正確建議
    assert result['action'] == 'Long', f"應為 Long，實際: {result['action']}"
    assert result['confidence'] == 'Medium', f"應為 Medium，實際: {result['confidence']}"
    
    print(f"\n✅ 驗證通過: 一致低信號，返回 Long/Medium")
    
    # 測試 5: 中性區域 - Preservation
    print("\n\n測試 5: 中性區域（rank=50%, percentile=55%）- Preservation")
    print("-" * 80)
    
    iv_rank = 50.0
    iv_percentile = 55.0
    
    print(f"輸入:")
    print(f"  iv_rank = {iv_rank}%")
    print(f"  iv_percentile = {iv_percentile}%")
    
    result = calc.get_iv_recommendation(iv_rank, iv_percentile)
    
    print(f"\n輸出:")
    print(f"  action = {result['action']}")
    print(f"  confidence = {result['confidence']}")
    
    # 驗證中性區域
    assert result['action'] == 'Neutral', f"應為 Neutral，實際: {result['action']}"
    
    print(f"\n✅ 驗證通過: 中性區域，返回 Neutral")
    
    print("\n" + "="*80)
    print("✅ BUG-18-05 修復驗證完成：所有測試通過")
    print("="*80)


if __name__ == '__main__':
    test_bug_18_05_consistency_check()
