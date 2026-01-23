"""
測試數據驗證功能 (US-2: 空數據保護)
"""

import pytest
import sys
import os

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import OptionsAnalysisSystem


class TestDataValidation:
    """測試數據完整性驗證"""
    
    def setup_method(self):
        """設置測試環境"""
        self.system = OptionsAnalysisSystem(use_ibkr=False)
    
    def test_validate_data_completeness_all_fields_present(self):
        """測試所有必需字段都存在的情況"""
        data = {
            'current_price': 150.0,
            'implied_volatility': 0.25,
            'expiration_date': '2026-03-20'
        }
        required_fields = ['current_price', 'implied_volatility', 'expiration_date']
        
        result = self.system.validate_data_completeness(data, required_fields)
        
        assert result['is_valid'] is True
        assert len(result['missing_fields']) == 0
        assert result['error_message'] is None
    
    def test_validate_data_completeness_missing_fields(self):
        """測試缺少必需字段的情況"""
        data = {
            'current_price': 150.0
        }
        required_fields = ['current_price', 'implied_volatility', 'expiration_date']
        
        result = self.system.validate_data_completeness(data, required_fields)
        
        assert result['is_valid'] is False
        assert 'implied_volatility' in result['missing_fields']
        assert 'expiration_date' in result['missing_fields']
        assert result['error_message'] is not None
        assert '缺少必需字段' in result['error_message']
    
    def test_validate_data_completeness_none_values(self):
        """測試字段值為 None 的情況"""
        data = {
            'current_price': 150.0,
            'implied_volatility': None,
            'expiration_date': '2026-03-20'
        }
        required_fields = ['current_price', 'implied_volatility', 'expiration_date']
        
        result = self.system.validate_data_completeness(data, required_fields)
        
        assert result['is_valid'] is False
        assert 'implied_volatility' in result['missing_fields']
    
    def test_validate_data_completeness_empty_required_fields(self):
        """測試空的必需字段列表"""
        data = {
            'current_price': 150.0,
            'implied_volatility': 0.25
        }
        required_fields = []
        
        result = self.system.validate_data_completeness(data, required_fields)
        
        assert result['is_valid'] is True
        assert len(result['missing_fields']) == 0


class TestEmptyDataProtection:
    """測試空數據保護功能（集成測試）"""
    
    def setup_method(self):
        """設置測試環境"""
        self.system = OptionsAnalysisSystem(use_ibkr=False)
    
    @pytest.mark.skip(reason="需要實際 API 調用，僅用於手動測試")
    def test_invalid_ticker(self):
        """測試無效股票代碼"""
        result = self.system.run_complete_analysis('INVALID_TICKER_12345')
        
        assert result['success'] is False
        assert 'error' in result
        assert 'error_type' in result
        assert result['ticker'] == 'INVALID_TICKER_12345'
    
    @pytest.mark.skip(reason="需要實際 API 調用，僅用於手動測試")
    def test_empty_option_chain(self):
        """測試空期權鏈（使用沒有期權的股票）"""
        # 注意：需要找一個實際沒有期權的股票代碼
        result = self.system.run_complete_analysis('SOME_STOCK_WITHOUT_OPTIONS')
        
        assert result['success'] is False
        assert 'error_type' in result
        assert result['error_type'] in ['no_option_chain', 'empty_options']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
