# output_layer/history_manager.py
"""
History Manager Module - 管理歷史運行記錄
功能:
1. 維護每個股票的運行歷史索引
2. 檢索上一次的運行結果
3. 管理歷史數據的存儲和讀取

Requirements: New Requirement - History Tracking & Comparison
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from output_layer.output_manager import OutputPathManager

logger = logging.getLogger(__name__)

class HistoryManager:
    """歷史記錄管理器"""
    
    def __init__(self, output_manager: OutputPathManager):
        self.output_manager = output_manager
        self.history_filename = "history_index.json"
        
    def _get_history_path(self, ticker: str) -> str:
        """獲取歷史索引文件的路徑"""
        # 存儲在 output/{TICKER}/json/history_index.json
        return self.output_manager.get_output_path(ticker, 'json', self.history_filename)
        
    def load_history_index(self, ticker: str) -> List[Dict]:
        """讀取歷史索引列表"""
        path = self._get_history_path(ticker)
        if not os.path.exists(path):
            return []
            
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"讀取歷史索引失敗 {ticker}: {e}")
            return []
            
    def save_run_record(self, ticker: str, timestamp: str, 
                       json_path: str, result_summary: Dict) -> None:
        """
        保存本次運行記錄到索引
        
        參數:
            ticker: 股票代號
            timestamp: 運行時間戳
            json_path: 完整 JSON 報告路徑
            result_summary: 結果摘要（用於快速預覽）
        """
        index = self.load_history_index(ticker)
        
        # 構建新記錄
        new_record = {
            'timestamp': timestamp,
            'file_path': json_path,
            'summary': result_summary
        }
        
        # 添加到列表（按時間排序）
        index.append(new_record)
        # 按時間戳排序
        index.sort(key=lambda x: x['timestamp'])
        
        # 保存回文件
        path = self._get_history_path(ticker)
        try:
            self.output_manager.ensure_directory_exists(os.path.dirname(path))
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2, ensure_ascii=False)
            logger.info(f"已更新歷史索引: {ticker}")
        except Exception as e:
            logger.error(f"保存歷史索引失敗 {ticker}: {e}")
            
    def get_last_run(self, ticker: str) -> Optional[Dict]:
        """獲取上一次運行的完整數據"""
        index = self.load_history_index(ticker)
        if not index:
            return None
            
        # 獲取最後一個記錄
        last_record = index[-1]
        json_path = last_record['file_path']
        
        # 如果是相對路徑，嘗試修復
        if not os.path.exists(json_path):
             # 嘗試在當前目錄尋找
             if os.path.exists(os.path.basename(json_path)):
                 json_path = os.path.basename(json_path)
             else:
                 logger.warning(f"上次運行的文件不存在: {json_path}")
                 return None
                 
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"讀取上次運行數據失敗: {e}")
            return None

    def get_runs_by_date(self, ticker: str, date_str: str) -> List[Dict]:
        """獲取特定日期的所有運行記錄 (YYYY-MM-DD)"""
        index = self.load_history_index(ticker)
        return [r for r in index if r['timestamp'].startswith(date_str)]
