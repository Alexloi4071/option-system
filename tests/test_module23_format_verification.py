#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Module 23 format verification for Requirements 11.1-11.4
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from output_layer.report_generator import ReportGenerator


class TestModule23FormatRequirements:
    """Test Module 23 format requirements 11.1-11.4"""
    
    @pytest.fixture
    def report_generator(self):
        return ReportGenerator()
    
    @pytest.fixture
    def normal_iv_result(self):
        """Normal IV result with sufficient data"""
        return {
            'current_iv': 25.0,
            'high_threshold': 40.0,
            'low_threshold': 20.0,
            'status': '正常範圍',
            'data_quality': 'sufficient',
            'historical_days': 252,
            'percentile_75': 40.0,
            'percentile_25': 20.0,
            'median_iv': 30.0,
            'reliability': 'reliable'
        }
    
    @pytest.fixture
    def iv_rank_data(self):
        """Module 18 IV Rank data"""
        return {'iv_rank': 35.0}
    
    def test_requirement_11_1_dynamic_iv_vs_module17_explanation(
        self, report_generator, normal_iv_result, iv_rank_data
    ):
        """
        Requirement 11.1: 解釋動態 IV 與 Module 17 隱含波動率的區別
        """
        output = report_generator._format_module23_dynamic_iv_threshold(
            normal_iv_result, iv_rank_data
        )
        
        # Check for the explanation section
        assert "動態 IV 閾值 vs Module 17 隱含波動率" in output
        assert "Module 17 (隱含波動率)" in output
        assert "Module 23 (動態 IV 閾值)" in output
        assert "從期權市場價格反推" in output
        assert "基於歷史 IV 數據計算" in output
    
    def test_requirement_11_2_threshold_calculation_method(
        self, report_generator, normal_iv_result, iv_rank_data
    ):
        """
        Requirement 11.2: 說明閾值計算方法（基於歷史百分位）
        """
        output = report_generator._format_module23_dynamic_iv_threshold(
            normal_iv_result, iv_rank_data
        )
        
        # Check for threshold calculation method section
        assert "閾值計算方法" in output
        assert "252 天歷史 IV 數據" in output
        assert "75th 百分位" in output
        assert "25th 百分位" in output
        assert "中位數" in output
    
    def test_requirement_11_2_static_threshold_explanation(self, report_generator):
        """
        Requirement 11.2: 說明靜態閾值計算方法（數據不足時）
        """
        insufficient_data_result = {
            'current_iv': 25.0,
            'high_threshold': 31.25,
            'low_threshold': 18.75,
            'status': 'NORMAL (VIX基準範圍內)',
            'data_quality': 'insufficient',
            'historical_days': 0,
            'reliability': 'unreliable'
        }
        
        output = report_generator._format_module23_dynamic_iv_threshold(
            insufficient_data_result, None
        )
        
        # Check for static threshold explanation
        assert "閾值計算方法" in output
        assert "VIX 靜態閾值" in output or "歷史數據不足" in output
    
    def test_requirement_11_3_boundary_warning_near_high(self, report_generator, iv_rank_data):
        """
        Requirement 11.3: 添加邊界預警（接近高閾值）
        """
        near_high_result = {
            'current_iv': 38.0,  # Close to high threshold of 40
            'high_threshold': 40.0,
            'low_threshold': 20.0,
            'status': '正常範圍',
            'data_quality': 'sufficient',
            'historical_days': 252,
            'percentile_75': 40.0,
            'percentile_25': 20.0,
            'median_iv': 30.0,
            'reliability': 'reliable'
        }
        
        output = report_generator._format_module23_dynamic_iv_threshold(
            near_high_result, iv_rank_data
        )
        
        # Check for boundary warning
        assert "邊界預警" in output
        assert "接近高閾值" in output
    
    def test_requirement_11_3_boundary_warning_near_low(self, report_generator, iv_rank_data):
        """
        Requirement 11.3: 添加邊界預警（接近低閾值）
        """
        near_low_result = {
            'current_iv': 22.0,  # Close to low threshold of 20
            'high_threshold': 40.0,
            'low_threshold': 20.0,
            'status': '正常範圍',
            'data_quality': 'sufficient',
            'historical_days': 252,
            'percentile_75': 40.0,
            'percentile_25': 20.0,
            'median_iv': 30.0,
            'reliability': 'reliable'
        }
        
        output = report_generator._format_module23_dynamic_iv_threshold(
            near_low_result, iv_rank_data
        )
        
        # Check for boundary warning
        assert "邊界預警" in output
        assert "接近低閾值" in output
    
    def test_requirement_11_3_no_boundary_warning_when_not_near(
        self, report_generator, normal_iv_result, iv_rank_data
    ):
        """
        Requirement 11.3: 不在邊界時不顯示預警
        """
        output = report_generator._format_module23_dynamic_iv_threshold(
            normal_iv_result, iv_rank_data
        )
        
        # Should not have boundary warning when IV is in the middle
        assert "邊界預警" not in output
    
    def test_requirement_11_4_cross_validation_with_module18(
        self, report_generator, normal_iv_result, iv_rank_data
    ):
        """
        Requirement 11.4: 與 Module 18 IV Rank 交叉驗證
        """
        output = report_generator._format_module23_dynamic_iv_threshold(
            normal_iv_result, iv_rank_data
        )
        
        # Check for cross-validation section
        assert "Module 18 IV Rank 交叉驗證" in output
        assert "Module 18 IV Rank: 35.00%" in output
        assert "一致性" in output
    
    def test_requirement_11_4_cross_validation_consistency_check(self, report_generator):
        """
        Requirement 11.4: 交叉驗證一致性檢查
        """
        # High IV result
        high_iv_result = {
            'current_iv': 45.0,
            'high_threshold': 40.0,
            'low_threshold': 20.0,
            'status': '高於歷史水平',
            'data_quality': 'sufficient',
            'historical_days': 252,
            'percentile_75': 40.0,
            'percentile_25': 20.0,
            'median_iv': 30.0,
            'reliability': 'reliable'
        }
        
        # High IV Rank (consistent)
        high_iv_rank = {'iv_rank': 75.0}
        
        output = report_generator._format_module23_dynamic_iv_threshold(
            high_iv_result, high_iv_rank
        )
        
        # Should show consistency
        assert "一致" in output
        assert "賣出期權" in output or "Short" in output
    
    def test_requirement_11_4_cross_validation_inconsistency(self, report_generator):
        """
        Requirement 11.4: 交叉驗證不一致時的解釋
        """
        # Low IV result
        low_iv_result = {
            'current_iv': 15.0,
            'high_threshold': 40.0,
            'low_threshold': 20.0,
            'status': '低於歷史水平',
            'data_quality': 'sufficient',
            'historical_days': 252,
            'percentile_75': 40.0,
            'percentile_25': 20.0,
            'median_iv': 30.0,
            'reliability': 'reliable'
        }
        
        # Normal IV Rank (inconsistent with low IV)
        normal_iv_rank = {'iv_rank': 50.0}
        
        output = report_generator._format_module23_dynamic_iv_threshold(
            low_iv_result, normal_iv_rank
        )
        
        # Should show inconsistency and explanation
        assert "不一致" in output
        assert "說明" in output
    
    def test_no_cross_validation_when_no_iv_rank_data(
        self, report_generator, normal_iv_result
    ):
        """
        When no IV Rank data is provided, cross-validation section should not appear
        """
        output = report_generator._format_module23_dynamic_iv_threshold(
            normal_iv_result, None
        )
        
        # Should not have cross-validation section
        assert "Module 18 IV Rank 交叉驗證" not in output


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
