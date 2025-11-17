import logging
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)


class CSVExporter:
    """
    CSV導出器 - 完整實現
    
    功能:
    1. 導出單個模塊結果為CSV
    2. 導出批量結果為CSV
    3. 自動創建輸出目錄
    4. 支持自定義分隔符
    5. 完整的日誌和錯誤處理
    """
    
    def __init__(self, output_dir: str = 'output/csv'):
        """
        初始化CSV導出器
        
        參數:
            output_dir: 輸出目錄路徑
        """
        self.output_dir = Path(output_dir)
        self._ensure_output_dir()
        logger.info(f"✓ CSV導出器初始化完成，輸出目錄: {self.output_dir}")
    
    def _ensure_output_dir(self) -> None:
        """確保輸出目錄存在"""
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"✓ 輸出目錄已就緒: {self.output_dir}")
        except Exception as e:
            logger.error(f"✗ 創建輸出目錄失敗: {e}")
            raise
    
    def export_results(self, 
                      results: List[Dict[str, Any]], 
                      filename: Optional[str] = None,
                      delimiter: str = ',') -> bool:
        """
        導出結果列表為CSV
        
        參數:
            results: 包含多個結果的字典列表
            filename: 自定義檔案名稱
            delimiter: CSV分隔符
        
        返回:
            bool: 是否成功
        """
        try:
            if not results:
                logger.warning("✗ 結果列表為空，無法導出")
                return False
            
            if filename is None:
                filename = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            filepath = self.output_dir / filename
            
            logger.info(f"開始導出CSV文件...")
            logger.info(f"  檔案路徑: {filepath}")
            logger.info(f"  結果數量: {len(results)}")
            
            # 獲取表頭
            fieldnames = list(results[0].keys())
            logger.debug(f"  表頭字段: {fieldnames}")
            
            # 寫入CSV
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
                writer.writeheader()
                
                for i, row in enumerate(results, 1):
                    writer.writerow(row)
                    if i % 100 == 0:
                        logger.debug(f"  已寫入 {i} 行")
            
            logger.info(f"✓ CSV導出成功: {filepath}")
            logger.info(f"  總行數: {len(results)}")
            return True
            
        except Exception as e:
            logger.error(f"✗ CSV導出失敗: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def export_module_result(self, 
                            module_name: str, 
                            result: Dict[str, Any],
                            timestamp: bool = True) -> bool:
        """
        導出單個模塊結果
        
        參數:
            module_name: 模塊名稱
            result: 結果字典
            timestamp: 是否在檔名中添加時間戳
        
        返回:
            bool: 是否成功
        """
        try:
            if timestamp:
                filename = f"{module_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            else:
                filename = f"{module_name}.csv"
            
            return self.export_results([result], filename)
            
        except Exception as e:
            logger.error(f"✗ 模塊結果導出失敗: {e}")
            return False
    
    def export_batch_results(self,
                            batch_data: Dict[str, List[Dict]]) -> Dict[str, bool]:
        """
        批量導出多個結果集
        
        參數:
            batch_data: 格式為 {module_name: [結果列表]}
        
        返回:
            字典，記錄每個模塊的導出結果
        """
        results = {}
        
        logger.info(f"開始批量導出 {len(batch_data)} 個模塊...")
        
        for module_name, data_list in batch_data.items():
            filename = f"batch_{module_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            success = self.export_results(data_list, filename)
            results[module_name] = success
            
            if success:
                logger.info(f"  ✓ {module_name}: {len(data_list)} 條記錄")
            else:
                logger.warning(f"  ✗ {module_name}: 導出失敗")
        
        logger.info(f"✓ 批量導出完成，成功: {sum(results.values())}/{len(results)}")
        return results
    
    def get_last_file(self) -> Optional[Path]:
        """獲取最近導出的檔案"""
        try:
            files = list(self.output_dir.glob('*.csv'))
            if not files:
                return None
            return max(files, key=lambda f: f.stat().st_mtime)
        except Exception as e:
            logger.error(f"✗ 獲取檔案失敗: {e}")
            return None