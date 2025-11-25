"""
Property-Based Tests for Output Manager Module

Tests for OutputPathManager and FileMigrationUtility

Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7, 15.8, 15.9
"""

import os
import re
import sys
import tempfile
import shutil
from typing import Optional

import pytest
from hypothesis import given, strategies as st, settings, assume

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from output_layer.output_manager import (
    OutputPathManager,
    FileMigrationUtility,
    MigrationResult
)


class TestFileTypeRouting:
    """
    **Feature: jin-cao-option-enhancements, Property 11: File Type Routing**
    
    For any ticker symbol and file type (txt, csv, json, test, verify), 
    the generated output path should follow the correct pattern.
    
    **Validates: Requirements 15.3, 15.4, 15.5, 15.6, 15.7**
    """
    
    @given(
        ticker=st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ', min_size=1, max_size=5),
        file_type=st.sampled_from(['txt', 'csv', 'json', 'test', 'verify'])
    )
    @settings(max_examples=100)
    def test_file_type_routing(self, ticker: str, file_type: str):
        """Each file type should route to correct subdirectory"""
        manager = OutputPathManager(base_output_dir="output")
        filename = f"report_{ticker}_20251119_122525.{file_type if file_type in ['txt', 'csv', 'json'] else 'txt'}"
        path = manager.get_output_path(ticker, file_type, filename)
        
        # Normalize path separators for cross-platform compatibility
        path = path.replace('\\', '/')
        
        # Get sanitized ticker (may have _ prefix for Windows reserved names)
        sanitized_ticker = manager.sanitize_ticker(ticker)
        
        if file_type == 'txt':
            # TXT files should be in ticker root directory
            assert f"output/{sanitized_ticker}/report_" in path
            assert '/csv/' not in path
            assert '/json/' not in path
            assert '/test/' not in path
            assert '/verify/' not in path
        elif file_type == 'csv':
            assert f"output/{sanitized_ticker}/csv/" in path
        elif file_type == 'json':
            assert f"output/{sanitized_ticker}/json/" in path
        elif file_type == 'test':
            assert f"output/{sanitized_ticker}/test/" in path
        elif file_type == 'verify':
            assert f"output/{sanitized_ticker}/verify/" in path



class TestDirectoryAutoCreation:
    """
    **Feature: jin-cao-option-enhancements, Property 12: Directory Auto-Creation**
    
    For any ticker symbol and file save operation, if the target directory 
    does not exist, it should be automatically created before the file is saved.
    
    **Validates: Requirements 15.1, 15.2**
    """
    
    @given(
        ticker=st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ', min_size=1, max_size=5),
        file_type=st.sampled_from(['txt', 'csv', 'json', 'test', 'verify'])
    )
    @settings(max_examples=100)
    def test_directory_auto_creation(self, ticker: str, file_type: str):
        """Directories should be automatically created when saving files"""
        # Skip Windows reserved names that would cause issues
        windows_reserved = {'CON', 'PRN', 'AUX', 'NUL', 
                          'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
                          'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'}
        assume(ticker.upper() not in windows_reserved)
        
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = OutputPathManager(base_output_dir=temp_dir)
            
            filename = f"report_{ticker}_20251119_122525.txt"
            output_path = manager.get_output_path(ticker, file_type, filename)
            
            # Directory should not exist yet
            dir_path = os.path.dirname(output_path)
            
            # Ensure directory exists
            manager.ensure_directory_exists(dir_path)
            
            # Directory should now exist
            assert os.path.exists(dir_path)
            assert os.path.isdir(dir_path)


class TestTickerSanitization:
    """
    **Feature: jin-cao-option-enhancements, Property 13: Ticker Sanitization**
    
    For any ticker string containing invalid filesystem characters (/ \\ : * ? " < > |), 
    the sanitized ticker should:
    - Not contain any of these characters
    - Be uppercase
    - Be non-empty (at least 1 character) or "UNKNOWN"
    - Be at most 10 characters long
    
    **Validates: Requirements 15.9**
    """
    
    @given(ticker=st.text(min_size=0, max_size=20))
    @settings(max_examples=100)
    def test_sanitized_ticker_valid(self, ticker: str):
        """Sanitized ticker should not contain invalid characters"""
        manager = OutputPathManager()
        sanitized = manager.sanitize_ticker(ticker)
        
        # Should not contain invalid characters
        invalid_chars = r'[/\\:*?"<>|]'
        assert not re.search(invalid_chars, sanitized)
        
        # Should be uppercase
        assert sanitized == sanitized.upper()
        
        # Should be at most 10 characters
        assert len(sanitized) <= 10
        
        # Should be non-empty (UNKNOWN is returned for empty input)
        assert len(sanitized) >= 1
    
    @given(ticker=st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', min_size=1, max_size=10))
    @settings(max_examples=100)
    def test_valid_ticker_unchanged(self, ticker: str):
        """Valid tickers should remain unchanged (except for case and Windows reserved names)"""
        manager = OutputPathManager()
        sanitized = manager.sanitize_ticker(ticker)
        
        # Windows reserved names get _ prefix
        windows_reserved = {'CON', 'PRN', 'AUX', 'NUL', 
                          'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
                          'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'}
        
        if ticker.upper() in windows_reserved:
            assert sanitized == f"_{ticker.upper()}"
        else:
            # Valid ticker should be preserved (uppercase)
            assert sanitized == ticker.upper()
    
    def test_empty_ticker_returns_unknown(self):
        """Empty ticker should return UNKNOWN"""
        manager = OutputPathManager()
        assert manager.sanitize_ticker("") == "UNKNOWN"
        assert manager.sanitize_ticker(None) == "UNKNOWN"
    
    def test_invalid_chars_removed(self):
        """Invalid characters should be removed"""
        manager = OutputPathManager()
        
        # Test various invalid characters
        assert manager.sanitize_ticker("AA/PL") == "AAPL"
        assert manager.sanitize_ticker("TS:LA") == "TSLA"
        assert manager.sanitize_ticker("GO*OG") == "GOOG"
        assert manager.sanitize_ticker("ME?TA") == "META"
        assert manager.sanitize_ticker('MS"FT') == "MSFT"



class TestMigrationPreservesContent:
    """
    **Feature: jin-cao-option-enhancements, Property 14: Migration Preserves Content**
    
    For any file in the old output structure, after migration:
    - The file content should be identical to the original
    - The file should exist in the new location based on its ticker and type
    - The original file should no longer exist (unless dry_run=True)
    
    **Validates: Requirements 15.8**
    """
    
    @given(
        ticker=st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ', min_size=2, max_size=5),
        content=st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ', min_size=1, max_size=100)
    )
    @settings(max_examples=50)
    def test_migration_preserves_content(self, ticker: str, content: str):
        """File content should be preserved after migration"""
        # Skip Windows reserved names
        windows_reserved = {'CON', 'PRN', 'AUX', 'NUL', 
                          'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
                          'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'}
        assume(ticker.upper() not in windows_reserved)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create old structure
            old_csv_dir = os.path.join(temp_dir, 'csv')
            os.makedirs(old_csv_dir, exist_ok=True)
            
            # Create a test file in old structure
            filename = f"report_{ticker}_20251119_122525.csv"
            old_path = os.path.join(old_csv_dir, filename)
            
            with open(old_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Run migration
            manager = OutputPathManager(base_output_dir=temp_dir)
            migration = FileMigrationUtility(manager)
            result = migration.migrate_existing_files(dry_run=False)
            
            # Check new file exists
            new_path = manager.get_output_path(ticker, 'csv', filename)
            assert os.path.exists(new_path), f"New file should exist at {new_path}"
            
            # Check content is preserved
            with open(new_path, 'r', encoding='utf-8') as f:
                new_content = f.read()
            assert new_content == content, "Content should be preserved"
            
            # Check old file no longer exists
            assert not os.path.exists(old_path), "Old file should be removed"
    
    def test_dry_run_does_not_move_files(self):
        """Dry run should not actually move files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create old structure
            old_csv_dir = os.path.join(temp_dir, 'csv')
            os.makedirs(old_csv_dir, exist_ok=True)
            
            # Create a test file
            filename = "report_AAPL_20251119_122525.csv"
            old_path = os.path.join(old_csv_dir, filename)
            content = "test content"
            
            with open(old_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Run dry run migration
            manager = OutputPathManager(base_output_dir=temp_dir)
            migration = FileMigrationUtility(manager)
            result = migration.migrate_existing_files(dry_run=True)
            
            # Old file should still exist
            assert os.path.exists(old_path), "Old file should still exist in dry run"
            
            # New file should not exist
            new_path = manager.get_output_path('AAPL', 'csv', filename)
            assert not os.path.exists(new_path), "New file should not exist in dry run"
            
            # Operations should be recorded
            assert len(result.operations) > 0, "Operations should be recorded"


class TestTickerExtractionFromFilename:
    """
    **Feature: jin-cao-option-enhancements, Property 15: Ticker Extraction from Filename**
    
    For any filename in the format `report_{TICKER}_{TIMESTAMP}.{ext}`, 
    the extracted ticker should match the original ticker used to generate the filename.
    
    **Validates: Requirements 15.8**
    """
    
    @given(
        ticker=st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', min_size=1, max_size=10),
        ext=st.sampled_from(['txt', 'csv', 'json'])
    )
    @settings(max_examples=100)
    def test_ticker_extraction_round_trip(self, ticker: str, ext: str):
        """Extracted ticker should match original ticker"""
        manager = OutputPathManager()
        migration = FileMigrationUtility(manager)
        
        # Generate filename
        filename = f"report_{ticker}_20251119_122525.{ext}"
        
        # Extract ticker
        extracted = migration.extract_ticker_from_filename(filename)
        
        # Should match (uppercase)
        assert extracted == ticker.upper()
    
    def test_invalid_filename_returns_none(self):
        """Invalid filenames should return None"""
        manager = OutputPathManager()
        migration = FileMigrationUtility(manager)
        
        # Test various invalid formats
        assert migration.extract_ticker_from_filename("invalid.txt") is None
        assert migration.extract_ticker_from_filename("report.txt") is None
        assert migration.extract_ticker_from_filename("report_AAPL.txt") is None
        assert migration.extract_ticker_from_filename("AAPL_20251119_122525.txt") is None
    
    def test_valid_filenames(self):
        """Valid filenames should extract ticker correctly"""
        manager = OutputPathManager()
        migration = FileMigrationUtility(manager)
        
        # Test various valid formats
        assert migration.extract_ticker_from_filename("report_AAPL_20251119_122525.txt") == "AAPL"
        assert migration.extract_ticker_from_filename("report_TSLA_20251122_224740.csv") == "TSLA"
        assert migration.extract_ticker_from_filename("report_GOOG_20251125_234744.json") == "GOOG"
        assert migration.extract_ticker_from_filename("report_META_20251119_013147.csv") == "META"
        assert migration.extract_ticker_from_filename("report_ZIM_20251125_195227.txt") == "ZIM"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
