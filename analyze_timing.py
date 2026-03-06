#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析日誌時間消耗"""

import re
from datetime import datetime

log_file = "logs/main_20260306_211932.log"

# 關鍵時間點
timestamps = []

with open(log_file, 'r', encoding='utf-8') as f:
    for line in f:
        # 提取時間戳和關鍵事件
        match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}).*?- (.*)', line)
        if match:
            ts_str, msg = match.groups()
            ts = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S,%f')
            
            # 記錄關鍵事件
            if any(keyword in msg for keyword in [
                '系統啟動', 'IBKR 連接成功', 'Crumb 獲取成功', 
                '開始獲取', '成功獲取', '完成', 
                'Greeks 收斂超時', 'Disconnecting'
            ]):
                timestamps.append((ts, msg[:100]))

# 計算時間差
print("=" * 80)
print("時間消耗分析")
print("=" * 80)

if timestamps:
    start_time = timestamps[0][0]
    prev_time = start_time
    
    for i, (ts, msg) in enumerate(timestamps):
        elapsed = (ts - start_time).total_seconds()
        delta = (ts - prev_time).total_seconds()
        
        if delta > 1.0:  # 只顯示超過1秒的步驟
            print(f"\n[+{elapsed:6.1f}s] (+{delta:5.1f}s) {msg}")
        
        prev_time = ts
    
    total_time = (timestamps[-1][0] - timestamps[0][0]).total_seconds()
    print("\n" + "=" * 80)
    print(f"總耗時: {total_time:.1f}秒")
    print("=" * 80)
