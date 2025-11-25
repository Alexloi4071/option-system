"""
Output Manager Module - 輸出檔案路徑管理器

按股票代號分類存儲所有輸出檔案（TXT、CSV、JSON、Test、Verify）

Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7, 15.8, 15.9
"""

import os
import re
import shutil
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MigrationResult:
    """遷移結果數據模型"""
    files_moved: int
    files_skipped: int
    errors: List[str]
    operations: List[Dict[str, str]]


class OutputPathManager:
    """
    管理輸出檔案路徑，按股票代號分類
    
    目錄結構:
        output/
        ├── AAPL/
        │   ├── csv/
        │   ├── json/
        │   ├── test/
        │   ├── verify/
        │   └── report_AAPL_*.txt
        ├── TSLA/
        │   └── ...
    """
    
    # 無效的檔案系統字符
    INVALID_CHARS = r'[/\\:*?"<>|]'
    
    # Windows 保留名稱（不能作為檔案或目錄名稱）
    WINDOWS_RESERVED_NAMES = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    # 檔案類型到子目錄的映射
    FILE_TYPE_SUBDIRS = {
        'txt': '',           # TXT 檔案放在 ticker 根目錄
        'csv': 'csv',        # CSV 檔案放在 csv 子目錄
        'json': 'json',      # JSON 檔案放在 json 子目錄
        'test': 'test',      # 測試輸出放在 test 子目錄
        'verify': 'verify',  # 驗證輸出放在 verify 子目錄
    }
    
    def __init__(self, base_output_dir: str = "output"):
        """
        初始化 OutputPathManager
        
        參數:
            base_output_dir: 基礎輸出目錄路徑
        """
        self.base_output_dir = base_output_dir
    
    def sanitize_ticker(self, ticker: str) -> str:
        """
        清理股票代號中的無效檔案系統字符
        
        規則:
            - 移除 / \\ : * ? " < > |
            - 轉換為大寫
            - 最大長度 10 字符
            - 如果清理後為空，返回 "UNKNOWN"
        
        參數:
            ticker: 原始股票代號
        
        返回:
            str: 清理後的股票代號
        
        Requirements: 15.9
        """
        if not ticker:
            return "UNKNOWN"
        
        # 移除無效字符
        sanitized = re.sub(self.INVALID_CHARS, '', ticker)
        
        # 轉換為大寫
        sanitized = sanitized.upper()
        
        # 限制長度
        sanitized = sanitized[:10]
        
        # 如果清理後為空，返回 UNKNOWN
        if not sanitized:
            return "UNKNOWN"
        
        # 檢查是否為 Windows 保留名稱
        if sanitized in self.WINDOWS_RESERVED_NAMES:
            sanitized = f"_{sanitized}"
        
        return sanitized

    
    def get_output_path(
        self,
        ticker: str,
        file_type: str,
        filename: str
    ) -> str:
        """
        獲取檔案的完整輸出路徑
        
        參數:
            ticker: 股票代號 (e.g., 'AAPL', 'TSLA')
            file_type: 檔案類型 ('txt', 'csv', 'json', 'test', 'verify')
            filename: 檔案名稱
        
        返回:
            str: 完整路徑 (e.g., 'output/AAPL/csv/report_AAPL_20251119.csv')
        
        Requirements: 15.3, 15.4, 15.5, 15.6, 15.7
        """
        # 清理 ticker
        safe_ticker = self.sanitize_ticker(ticker)
        
        # 獲取子目錄
        subdir = self.FILE_TYPE_SUBDIRS.get(file_type.lower(), '')
        
        # 構建路徑
        if subdir:
            path = os.path.join(self.base_output_dir, safe_ticker, subdir, filename)
        else:
            path = os.path.join(self.base_output_dir, safe_ticker, filename)
        
        return path
    
    def ensure_directory_exists(self, path: str) -> None:
        """
        確保目錄存在，如不存在則創建
        
        參數:
            path: 目錄路徑
        
        Requirements: 15.1, 15.2
        """
        try:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
                logger.info(f"Created directory: {path}")
        except PermissionError as e:
            logger.error(f"Permission denied creating directory {path}: {e}")
            raise
        except OSError as e:
            logger.error(f"Error creating directory {path}: {e}")
            raise
    
    def get_ticker_directory(self, ticker: str) -> str:
        """
        獲取股票代號的根目錄路徑
        
        參數:
            ticker: 股票代號
        
        返回:
            str: 目錄路徑 (e.g., 'output/AAPL')
        """
        safe_ticker = self.sanitize_ticker(ticker)
        return os.path.join(self.base_output_dir, safe_ticker)
    
    def save_file(
        self,
        ticker: str,
        file_type: str,
        filename: str,
        content: str,
        encoding: str = 'utf-8'
    ) -> str:
        """
        保存檔案到正確的位置
        
        參數:
            ticker: 股票代號
            file_type: 檔案類型
            filename: 檔案名稱
            content: 檔案內容
            encoding: 編碼格式
        
        返回:
            str: 保存的完整路徑
        """
        output_path = self.get_output_path(ticker, file_type, filename)
        
        # 確保目錄存在
        self.ensure_directory_exists(os.path.dirname(output_path))
        
        # 保存檔案
        with open(output_path, 'w', encoding=encoding) as f:
            f.write(content)
        
        logger.info(f"Saved file: {output_path}")
        return output_path


class FileMigrationUtility:
    """
    遷移現有檔案到新的目錄結構
    
    Requirements: 15.8
    """
    
    def __init__(self, output_manager: OutputPathManager):
        """
        初始化 FileMigrationUtility
        
        參數:
            output_manager: OutputPathManager 實例
        """
        self.output_manager = output_manager
    
    def extract_ticker_from_filename(self, filename: str) -> Optional[str]:
        """
        從檔案名稱中提取股票代號
        
        支援格式:
            - report_AAPL_20251119_122525.txt
            - report_AAPL_20251119_122525.csv
            - report_AAPL_20251119_122525.json
        
        參數:
            filename: 檔案名稱
        
        返回:
            Optional[str]: 股票代號，如果無法提取則返回 None
        
        Requirements: 15.8
        """
        # 移除路徑，只保留檔案名
        basename = os.path.basename(filename)
        
        # 匹配格式: report_{TICKER}_{TIMESTAMP}.{ext}
        # TICKER 可以是 1-10 個大寫字母或數字
        pattern = r'^report_([A-Za-z0-9]+)_\d{8}_\d{6}\.\w+$'
        match = re.match(pattern, basename)
        
        if match:
            return match.group(1).upper()
        
        return None

    
    def migrate_existing_files(self, dry_run: bool = True) -> MigrationResult:
        """
        遷移現有檔案到新結構
        
        參數:
            dry_run: 如果為 True，只顯示將要執行的操作，不實際移動檔案
        
        返回:
            MigrationResult: 遷移結果
        
        Requirements: 15.8
        """
        files_moved = 0
        files_skipped = 0
        errors = []
        operations = []
        
        base_dir = self.output_manager.base_output_dir
        
        # 定義舊目錄結構和對應的檔案類型
        old_dirs = {
            base_dir: 'txt',           # 根目錄的 .txt 檔案
            os.path.join(base_dir, 'csv'): 'csv',
            os.path.join(base_dir, 'json'): 'json',
            os.path.join(base_dir, 'test'): 'test',
            os.path.join(base_dir, 'verify'): 'verify',
        }
        
        for old_dir, file_type in old_dirs.items():
            if not os.path.exists(old_dir):
                continue
            
            # 掃描目錄中的檔案
            try:
                for item in os.listdir(old_dir):
                    old_path = os.path.join(old_dir, item)
                    
                    # 只處理檔案，跳過目錄
                    if not os.path.isfile(old_path):
                        continue
                    
                    # 對於根目錄，只處理 .txt 檔案
                    if old_dir == base_dir and not item.endswith('.txt'):
                        continue
                    
                    # 提取 ticker
                    ticker = self.extract_ticker_from_filename(item)
                    
                    if not ticker:
                        files_skipped += 1
                        logger.warning(f"Could not extract ticker from: {item}")
                        continue
                    
                    # 計算新路徑
                    new_path = self.output_manager.get_output_path(
                        ticker=ticker,
                        file_type=file_type,
                        filename=item
                    )
                    
                    # 記錄操作
                    operation = {
                        'source': old_path,
                        'destination': new_path,
                        'ticker': ticker,
                        'file_type': file_type
                    }
                    operations.append(operation)
                    
                    if dry_run:
                        logger.info(f"[DRY RUN] Would move: {old_path} -> {new_path}")
                    else:
                        try:
                            # 確保目標目錄存在
                            self.output_manager.ensure_directory_exists(
                                os.path.dirname(new_path)
                            )
                            
                            # 移動檔案
                            shutil.move(old_path, new_path)
                            files_moved += 1
                            logger.info(f"Moved: {old_path} -> {new_path}")
                        except Exception as e:
                            errors.append(f"Error moving {old_path}: {str(e)}")
                            logger.error(f"Error moving {old_path}: {e}")
                            
            except Exception as e:
                errors.append(f"Error scanning {old_dir}: {str(e)}")
                logger.error(f"Error scanning {old_dir}: {e}")
        
        return MigrationResult(
            files_moved=files_moved,
            files_skipped=files_skipped,
            errors=errors,
            operations=operations
        )
    
    def cleanup_empty_directories(self) -> List[str]:
        """
        清理遷移後的空目錄
        
        返回:
            List[str]: 已刪除的目錄列表
        """
        removed = []
        base_dir = self.output_manager.base_output_dir
        
        # 舊的子目錄
        old_subdirs = ['csv', 'json', 'test', 'verify']
        
        for subdir in old_subdirs:
            dir_path = os.path.join(base_dir, subdir)
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                # 檢查是否為空
                if not os.listdir(dir_path):
                    try:
                        os.rmdir(dir_path)
                        removed.append(dir_path)
                        logger.info(f"Removed empty directory: {dir_path}")
                    except Exception as e:
                        logger.error(f"Error removing {dir_path}: {e}")
        
        return removed


def run_migration(base_output_dir: str = "output", dry_run: bool = True) -> MigrationResult:
    """
    執行檔案遷移的便捷函數
    
    參數:
        base_output_dir: 基礎輸出目錄
        dry_run: 是否為試運行模式
    
    返回:
        MigrationResult: 遷移結果
    """
    manager = OutputPathManager(base_output_dir)
    migration = FileMigrationUtility(manager)
    
    print(f"\n{'='*60}")
    print(f"Output File Migration Utility")
    print(f"{'='*60}")
    print(f"Base directory: {base_output_dir}")
    print(f"Mode: {'DRY RUN (no files will be moved)' if dry_run else 'ACTUAL MIGRATION'}")
    print(f"{'='*60}\n")
    
    result = migration.migrate_existing_files(dry_run=dry_run)
    
    print(f"\n{'='*60}")
    print(f"Migration Summary")
    print(f"{'='*60}")
    print(f"Files to move: {len(result.operations)}")
    print(f"Files moved: {result.files_moved}")
    print(f"Files skipped: {result.files_skipped}")
    print(f"Errors: {len(result.errors)}")
    
    if result.operations:
        print(f"\nOperations:")
        for op in result.operations:
            print(f"  {op['ticker']}: {op['source']} -> {op['destination']}")
    
    if result.errors:
        print(f"\nErrors:")
        for error in result.errors:
            print(f"  - {error}")
    
    print(f"{'='*60}\n")
    
    return result


if __name__ == "__main__":
    # 命令行執行遷移
    import sys
    
    dry_run = "--execute" not in sys.argv
    base_dir = "output"
    
    # 檢查是否有自定義目錄
    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            base_dir = arg
            break
    
    result = run_migration(base_dir, dry_run=dry_run)
    
    if dry_run:
        print("This was a dry run. To actually migrate files, run with --execute flag.")
