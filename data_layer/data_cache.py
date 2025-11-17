# data_layer/data_cache.py
"""
數據緩存系統
"""

import json
import pickle
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DataCache:
    """數據緩存管理類"""
    
    def __init__(self, cache_dir='cache/', ttl=3600):
        """
        初始化緩存系統
        
        參數:
            cache_dir: 緩存目錄
            ttl: 緩存有效期（秒），默認1小時
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl = ttl
        logger.info(f"緩存系統已初始化，目錄: {self.cache_dir}, TTL: {ttl}秒")
    
    def _get_cache_file(self, key: str) -> Path:
        """獲取緩存文件路徑"""
        safe_key = key.replace('/', '_').replace('\\', '_')
        return self.cache_dir / f"{safe_key}.cache"
    
    def _get_meta_file(self, key: str) -> Path:
        """獲取元數據文件路徑"""
        safe_key = key.replace('/', '_').replace('\\', '_')
        return self.cache_dir / f"{safe_key}.meta"
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """
        設置緩存
        
        參數:
            key: 緩存鍵
            data: 要緩存的數據
            ttl: 自定義TTL（秒）
        
        返回: bool
        """
        try:
            cache_file = self._get_cache_file(key)
            meta_file = self._get_meta_file(key)
            
            # 保存數據
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            
            # 保存元數據
            meta = {
                'created_at': datetime.now().isoformat(),
                'ttl': ttl if ttl is not None else self.ttl,
                'expires_at': (datetime.now() + timedelta(seconds=ttl if ttl else self.ttl)).isoformat()
            }
            
            with open(meta_file, 'w') as f:
                json.dump(meta, f)
            
            logger.info(f"緩存已設置: {key}")
            return True
            
        except Exception as e:
            logger.error(f"設置緩存失敗 {key}: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """
        獲取緩存
        
        參數:
            key: 緩存鍵
        
        返回: 緩存的數據，如果不存在或過期則返回None
        """
        try:
            cache_file = self._get_cache_file(key)
            meta_file = self._get_meta_file(key)
            
            # 檢查文件是否存在
            if not cache_file.exists() or not meta_file.exists():
                logger.debug(f"緩存不存在: {key}")
                return None
            
            # 讀取元數據
            with open(meta_file, 'r') as f:
                meta = json.load(f)
            
            # 檢查是否過期
            expires_at = datetime.fromisoformat(meta['expires_at'])
            if datetime.now() > expires_at:
                logger.debug(f"緩存已過期: {key}")
                self.delete(key)
                return None
            
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
    
    def exists(self, key: str) -> bool:
        """
        檢查緩存是否存在且未過期
        
        參數:
            key: 緩存鍵
        
        返回: bool
        """
        return self.get(key) is not None


# 使用示例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    cache = DataCache()
    
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
    
    # 測試刪除緩存
    cache.delete('test_key')
    print(f"刪除後緩存存在: {cache.exists('test_key')}")
