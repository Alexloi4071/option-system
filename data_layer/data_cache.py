# data_layer/data_cache.py
"""
數據緩存系統

增強功能:
- 支持不同數據類型的緩存時長
- 手動失效緩存功能
- 緩存有效性檢查
"""

import json
import pickle
import logging
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List

logger = logging.getLogger(__name__)

# 數據類型到緩存鍵前綴的映射
# 用於從緩存鍵推斷數據類型
DATA_TYPE_PATTERNS = {
    'stock_info': [r'^stock_info_', r'^finviz_', r'^quote_'],
    'option_chain': [r'^option_chain_', r'^options_'],
    'historical': [r'^historical_', r'^history_', r'^price_history_'],
    'earnings': [r'^earnings_', r'^earnings_calendar_'],
    'dividend': [r'^dividend_', r'^dividend_calendar_'],
    'vix': [r'^vix_', r'^vix$'],
    'risk_free_rate': [r'^risk_free_', r'^treasury_', r'^rate_'],
    'fundamentals': [r'^fundamentals_', r'^financial_'],
}


class DataCache:
    """
    數據緩存管理類
    
    增強功能:
    - 支持不同數據類型的緩存時長
    - 手動失效緩存功能
    - 緩存有效性檢查
    """
    
    def __init__(self, cache_dir='cache/', ttl=3600, type_specific_ttl: Optional[Dict[str, int]] = None):
        """
        初始化緩存系統
        
        參數:
            cache_dir: 緩存目錄
            ttl: 默認緩存有效期（秒），默認1小時
            type_specific_ttl: 數據類型特定的緩存時長字典
                例如: {'stock_info': 300, 'vix': 60, 'earnings': 3600}
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl = ttl
        
        # 數據類型特定的緩存時長
        self.type_specific_ttl = type_specific_ttl or {}
        
        # 手動失效的緩存鍵集合
        self._invalidated_keys: set = set()
        
        # 嘗試從 settings 加載數據類型特定的緩存時長
        self._load_type_specific_ttl_from_settings()
        
        logger.info(f"緩存系統已初始化，目錄: {self.cache_dir}, 默認TTL: {ttl}秒")
        if self.type_specific_ttl:
            logger.debug(f"數據類型特定TTL: {self.type_specific_ttl}")
    
    def _load_type_specific_ttl_from_settings(self):
        """從 settings 加載數據類型特定的緩存時長"""
        try:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from config.settings import settings
            
            # 映射 settings 中的緩存時長配置
            settings_mapping = {
                'stock_info': getattr(settings, 'CACHE_DURATION_STOCK_INFO', None),
                'option_chain': getattr(settings, 'CACHE_DURATION_OPTION_CHAIN', None),
                'historical': getattr(settings, 'CACHE_DURATION_HISTORICAL', None),
                'earnings': getattr(settings, 'CACHE_DURATION_EARNINGS', None),
                'dividend': getattr(settings, 'CACHE_DURATION_DIVIDEND', None),
                'vix': getattr(settings, 'CACHE_DURATION_VIX', None),
                'risk_free_rate': getattr(settings, 'CACHE_DURATION_RISK_FREE_RATE', None),
                'fundamentals': getattr(settings, 'CACHE_DURATION_FUNDAMENTALS', None),
            }
            
            # 只添加有值的配置（不覆蓋已有的 type_specific_ttl）
            for data_type, duration in settings_mapping.items():
                if duration is not None and data_type not in self.type_specific_ttl:
                    self.type_specific_ttl[data_type] = duration
            
            logger.debug(f"已從 settings 加載緩存時長配置: {len(self.type_specific_ttl)} 種數據類型")
            
        except ImportError as e:
            logger.debug(f"無法加載 settings，使用默認緩存時長: {e}")
    
    def _get_cache_file(self, key: str) -> Path:
        """獲取緩存文件路徑"""
        safe_key = key.replace('/', '_').replace('\\', '_')
        return self.cache_dir / f"{safe_key}.cache"
    
    def _get_meta_file(self, key: str) -> Path:
        """獲取元數據文件路徑"""
        safe_key = key.replace('/', '_').replace('\\', '_')
        return self.cache_dir / f"{safe_key}.meta"
    
    def _get_cache_duration_for_key(self, cache_key: str) -> int:
        """
        根據緩存鍵獲取對應的緩存時長
        
        此方法會根據緩存鍵的前綴或模式推斷數據類型，
        然後返回該數據類型對應的緩存時長。
        
        參數:
            cache_key: 緩存鍵
        
        返回:
            int: 緩存時長（秒）
        
        示例:
            >>> cache._get_cache_duration_for_key('stock_info_AAPL')
            300  # 股票信息緩存5分鐘
            >>> cache._get_cache_duration_for_key('vix')
            60   # VIX緩存1分鐘
        """
        # 嘗試根據緩存鍵模式匹配數據類型
        for data_type, patterns in DATA_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.match(pattern, cache_key, re.IGNORECASE):
                    duration = self.type_specific_ttl.get(data_type, self.ttl)
                    logger.debug(f"緩存鍵 '{cache_key}' 匹配數據類型 '{data_type}'，TTL: {duration}秒")
                    return duration
        
        # 如果沒有匹配到任何模式，返回默認 TTL
        logger.debug(f"緩存鍵 '{cache_key}' 未匹配任何數據類型，使用默認TTL: {self.ttl}秒")
        return self.ttl
    
    def _is_cache_valid(self, cache_key: str, duration: Optional[int] = None) -> bool:
        """
        檢查緩存是否有效（增強版）
        
        此方法支持:
        1. 不同數據類型的不同緩存時長
        2. 手動失效的緩存檢測
        3. 自定義緩存時長覆蓋
        
        參數:
            cache_key: 緩存鍵
            duration: 自定義緩存時長（秒），如果為 None 則根據數據類型自動確定
        
        返回:
            bool: 緩存是否有效
        
        示例:
            >>> cache._is_cache_valid('stock_info_AAPL')
            True  # 緩存存在且未過期
            >>> cache._is_cache_valid('vix', duration=30)
            False  # 使用自定義30秒時長，緩存已過期
        """
        # 檢查是否被手動失效
        if cache_key in self._invalidated_keys:
            logger.debug(f"緩存 '{cache_key}' 已被手動失效")
            return False
        
        # 檢查緩存文件是否存在
        cache_file = self._get_cache_file(cache_key)
        meta_file = self._get_meta_file(cache_key)
        
        if not cache_file.exists() or not meta_file.exists():
            logger.debug(f"緩存 '{cache_key}' 不存在")
            return False
        
        try:
            # 讀取元數據
            with open(meta_file, 'r') as f:
                meta = json.load(f)
            
            # 獲取緩存創建時間
            created_at = datetime.fromisoformat(meta['created_at'])
            
            # 確定緩存時長
            if duration is None:
                duration = self._get_cache_duration_for_key(cache_key)
            
            # 計算緩存年齡
            age = (datetime.now() - created_at).total_seconds()
            
            # 檢查是否過期
            is_valid = age < duration
            
            if is_valid:
                logger.debug(f"緩存 '{cache_key}' 有效，年齡: {age:.1f}秒，TTL: {duration}秒")
            else:
                logger.debug(f"緩存 '{cache_key}' 已過期，年齡: {age:.1f}秒，TTL: {duration}秒")
            
            return is_valid
            
        except Exception as e:
            logger.warning(f"檢查緩存有效性失敗 '{cache_key}': {e}")
            return False
    
    def invalidate(self, cache_key: str) -> bool:
        """
        手動失效指定的緩存
        
        此方法將緩存鍵添加到失效集合中，使其在下次訪問時被視為無效。
        實際的緩存文件不會被立即刪除，但會在下次 get() 時被忽略。
        
        參數:
            cache_key: 要失效的緩存鍵
        
        返回:
            bool: 操作是否成功
        
        示例:
            >>> cache.invalidate('stock_info_AAPL')
            True
            >>> cache._is_cache_valid('stock_info_AAPL')
            False
        """
        try:
            self._invalidated_keys.add(cache_key)
            logger.info(f"緩存已手動失效: {cache_key}")
            return True
        except Exception as e:
            logger.error(f"手動失效緩存失敗 '{cache_key}': {e}")
            return False
    
    def invalidate_by_pattern(self, pattern: str) -> int:
        """
        根據模式失效多個緩存
        
        此方法會匹配所有符合模式的緩存鍵並將其失效。
        
        參數:
            pattern: 正則表達式模式
        
        返回:
            int: 失效的緩存數量
        
        示例:
            >>> cache.invalidate_by_pattern(r'^stock_info_')
            5  # 失效了5個股票信息緩存
        """
        try:
            count = 0
            regex = re.compile(pattern, re.IGNORECASE)
            
            # 遍歷所有緩存文件
            for cache_file in self.cache_dir.glob('*.cache'):
                key = cache_file.stem
                if regex.match(key):
                    self._invalidated_keys.add(key)
                    count += 1
            
            logger.info(f"根據模式 '{pattern}' 失效了 {count} 個緩存")
            return count
            
        except Exception as e:
            logger.error(f"根據模式失效緩存失敗 '{pattern}': {e}")
            return 0
    
    def invalidate_by_type(self, data_type: str) -> int:
        """
        根據數據類型失效緩存
        
        此方法會失效指定數據類型的所有緩存。
        
        參數:
            data_type: 數據類型，如 'stock_info', 'option_chain', 'vix' 等
        
        返回:
            int: 失效的緩存數量
        
        示例:
            >>> cache.invalidate_by_type('stock_info')
            10  # 失效了10個股票信息緩存
        """
        if data_type not in DATA_TYPE_PATTERNS:
            logger.warning(f"未知的數據類型: {data_type}")
            return 0
        
        total_count = 0
        for pattern in DATA_TYPE_PATTERNS[data_type]:
            count = self.invalidate_by_pattern(pattern)
            total_count += count
        
        logger.info(f"根據數據類型 '{data_type}' 共失效了 {total_count} 個緩存")
        return total_count
    
    def clear_invalidated(self) -> int:
        """
        清除所有已失效的緩存（實際刪除文件）
        
        此方法會刪除所有被手動失效的緩存文件，並清空失效集合。
        
        返回:
            int: 刪除的緩存數量
        """
        count = 0
        for key in list(self._invalidated_keys):
            if self.delete(key):
                count += 1
        
        self._invalidated_keys.clear()
        logger.info(f"已清除 {count} 個失效緩存")
        return count
    
    def get_cache_info(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        獲取緩存的詳細信息
        
        參數:
            cache_key: 緩存鍵
        
        返回:
            dict: 緩存信息，包含創建時間、過期時間、數據類型等
        """
        meta_file = self._get_meta_file(cache_key)
        cache_file = self._get_cache_file(cache_key)
        
        if not meta_file.exists():
            return None
        
        try:
            with open(meta_file, 'r') as f:
                meta = json.load(f)
            
            created_at = datetime.fromisoformat(meta['created_at'])
            duration = self._get_cache_duration_for_key(cache_key)
            age = (datetime.now() - created_at).total_seconds()
            
            # 推斷數據類型
            data_type = 'unknown'
            for dt, patterns in DATA_TYPE_PATTERNS.items():
                for pattern in patterns:
                    if re.match(pattern, cache_key, re.IGNORECASE):
                        data_type = dt
                        break
                if data_type != 'unknown':
                    break
            
            return {
                'key': cache_key,
                'data_type': data_type,
                'created_at': meta['created_at'],
                'ttl': duration,
                'age_seconds': age,
                'is_valid': age < duration and cache_key not in self._invalidated_keys,
                'is_invalidated': cache_key in self._invalidated_keys,
                'file_size': cache_file.stat().st_size if cache_file.exists() else 0,
            }
            
        except Exception as e:
            logger.error(f"獲取緩存信息失敗 '{cache_key}': {e}")
            return None
    
    def get_all_cache_info(self) -> List[Dict[str, Any]]:
        """
        獲取所有緩存的信息
        
        返回:
            list: 所有緩存的信息列表
        """
        cache_info_list = []
        
        for cache_file in self.cache_dir.glob('*.cache'):
            key = cache_file.stem
            info = self.get_cache_info(key)
            if info:
                cache_info_list.append(info)
        
        return cache_info_list
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """
        設置緩存
        
        參數:
            key: 緩存鍵
            data: 要緩存的數據
            ttl: 自定義TTL（秒），如果為 None 則根據數據類型自動確定
        
        返回: bool
        """
        try:
            cache_file = self._get_cache_file(key)
            meta_file = self._get_meta_file(key)
            
            # 如果緩存鍵之前被手動失效，現在重新設置時移除失效標記
            if key in self._invalidated_keys:
                self._invalidated_keys.discard(key)
            
            # 保存數據
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            
            # 確定緩存時長
            if ttl is None:
                ttl = self._get_cache_duration_for_key(key)
            
            # 保存元數據
            meta = {
                'created_at': datetime.now().isoformat(),
                'ttl': ttl,
                'expires_at': (datetime.now() + timedelta(seconds=ttl)).isoformat()
            }
            
            with open(meta_file, 'w') as f:
                json.dump(meta, f)
            
            logger.info(f"緩存已設置: {key} (TTL: {ttl}秒)")
            return True
            
        except Exception as e:
            logger.error(f"設置緩存失敗 {key}: {e}")
            return False
    
    def get(self, key: str, duration: Optional[int] = None) -> Optional[Any]:
        """
        獲取緩存
        
        參數:
            key: 緩存鍵
            duration: 自定義緩存時長（秒），用於覆蓋默認的數據類型特定時長
        
        返回: 緩存的數據，如果不存在或過期則返回None
        """
        try:
            # 使用增強的緩存有效性檢查
            if not self._is_cache_valid(key, duration):
                # 如果緩存無效，嘗試刪除過期的緩存文件
                cache_file = self._get_cache_file(key)
                if cache_file.exists():
                    self.delete(key)
                return None
            
            cache_file = self._get_cache_file(key)
            
            # 讀取數據
            with open(cache_file, 'rb') as f:
                data = pickle.load(f)
            
            logger.info(f"緩存命中: {key}")
            return data
            
        except Exception as e:
            logger.error(f"獲取緩存失敗 {key}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """
        刪除緩存
        
        參數:
            key: 緩存鍵
        
        返回: bool
        """
        try:
            cache_file = self._get_cache_file(key)
            meta_file = self._get_meta_file(key)
            
            if cache_file.exists():
                cache_file.unlink()
            
            if meta_file.exists():
                meta_file.unlink()
            
            logger.info(f"緩存已刪除: {key}")
            return True
            
        except Exception as e:
            logger.error(f"刪除緩存失敗 {key}: {e}")
            return False
    
    def clear_all(self) -> int:
        """
        清除所有緩存
        
        返回: 清除的緩存數量
        """
        try:
            count = 0
            for file in self.cache_dir.glob('*.cache'):
                file.unlink()
                count += 1
            
            for file in self.cache_dir.glob('*.meta'):
                file.unlink()
            
            logger.info(f"已清除所有緩存，共 {count} 個")
            return count
            
        except Exception as e:
            logger.error(f"清除緩存失敗: {e}")
            return 0
    
    def clear_expired(self) -> int:
        """
        清除過期緩存
        
        返回: 清除的緩存數量
        """
        try:
            count = 0
            for meta_file in self.cache_dir.glob('*.meta'):
                try:
                    with open(meta_file, 'r') as f:
                        meta = json.load(f)
                    
                    expires_at = datetime.fromisoformat(meta['expires_at'])
                    if datetime.now() > expires_at:
                        # 提取key
                        key = meta_file.stem
                        self.delete(key)
                        count += 1
                        
                except Exception:
                    continue
            
            logger.info(f"已清除過期緩存，共 {count} 個")
            return count
            
        except Exception as e:
            logger.error(f"清除過期緩存失敗: {e}")
            return 0
    
    def exists(self, key: str, duration: Optional[int] = None) -> bool:
        """
        檢查緩存是否存在且未過期
        
        參數:
            key: 緩存鍵
            duration: 自定義緩存時長（秒），用於覆蓋默認的數據類型特定時長
        
        返回: bool
        """
        return self._is_cache_valid(key, duration)


# 使用示例
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    # 創建緩存實例，指定數據類型特定的緩存時長
    cache = DataCache(
        type_specific_ttl={
            'stock_info': 300,  # 5分鐘
            'vix': 60,          # 1分鐘
            'option_chain': 60, # 1分鐘
        }
    )
    
    print("=" * 50)
    print("測試 1: 基本緩存操作")
    print("=" * 50)
    
    # 測試設置緩存
    test_data = {
        'ticker': 'AAPL',
        'price': 180.50,
        'iv': 22.0
    }
    
    cache.set('test_key', test_data, ttl=10)
    
    # 測試獲取緩存
    result = cache.get('test_key')
    print(f"緩存數據: {result}")
    
    # 測試緩存是否存在
    print(f"緩存存在: {cache.exists('test_key')}")
    
    print("\n" + "=" * 50)
    print("測試 2: 數據類型特定的緩存時長")
    print("=" * 50)
    
    # 測試股票信息緩存（應該使用 300 秒 TTL）
    cache.set('stock_info_AAPL', {'price': 180.50})
    duration = cache._get_cache_duration_for_key('stock_info_AAPL')
    print(f"stock_info_AAPL 緩存時長: {duration}秒")
    
    # 測試 VIX 緩存（應該使用 60 秒 TTL）
    cache.set('vix', {'value': 15.5})
    duration = cache._get_cache_duration_for_key('vix')
    print(f"vix 緩存時長: {duration}秒")
    
    # 測試未知類型緩存（應該使用默認 TTL）
    cache.set('unknown_key', {'data': 'test'})
    duration = cache._get_cache_duration_for_key('unknown_key')
    print(f"unknown_key 緩存時長: {duration}秒 (默認)")
    
    print("\n" + "=" * 50)
    print("測試 3: 手動失效緩存")
    print("=" * 50)
    
    # 設置緩存
    cache.set('stock_info_MSFT', {'price': 350.00})
    print(f"設置後緩存有效: {cache._is_cache_valid('stock_info_MSFT')}")
    
    # 手動失效
    cache.invalidate('stock_info_MSFT')
    print(f"失效後緩存有效: {cache._is_cache_valid('stock_info_MSFT')}")
    
    # 重新設置應該清除失效標記
    cache.set('stock_info_MSFT', {'price': 351.00})
    print(f"重新設置後緩存有效: {cache._is_cache_valid('stock_info_MSFT')}")
    
    print("\n" + "=" * 50)
    print("測試 4: 根據模式失效緩存")
    print("=" * 50)
    
    # 設置多個股票信息緩存
    cache.set('stock_info_GOOGL', {'price': 140.00})
    cache.set('stock_info_AMZN', {'price': 180.00})
    cache.set('option_chain_AAPL', {'calls': [], 'puts': []})
    
    # 根據模式失效所有股票信息緩存
    count = cache.invalidate_by_pattern(r'^stock_info_')
    print(f"失效了 {count} 個股票信息緩存")
    
    # 檢查緩存狀態
    print(f"stock_info_GOOGL 有效: {cache._is_cache_valid('stock_info_GOOGL')}")
    print(f"option_chain_AAPL 有效: {cache._is_cache_valid('option_chain_AAPL')}")
    
    print("\n" + "=" * 50)
    print("測試 5: 獲取緩存信息")
    print("=" * 50)
    
    cache.set('stock_info_NVDA', {'price': 500.00})
    info = cache.get_cache_info('stock_info_NVDA')
    print(f"緩存信息: {info}")
    
    print("\n" + "=" * 50)
    print("測試 6: 清理")
    print("=" * 50)
    
    # 清理所有測試緩存
    cache.delete('test_key')
    cache.delete('stock_info_AAPL')
    cache.delete('stock_info_MSFT')
    cache.delete('stock_info_GOOGL')
    cache.delete('stock_info_AMZN')
    cache.delete('stock_info_NVDA')
    cache.delete('option_chain_AAPL')
    cache.delete('vix')
    cache.delete('unknown_key')
    
    print("測試完成！")
