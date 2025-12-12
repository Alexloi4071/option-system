#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Property-based tests for Module Consistency Checker
使用 Hypothesis 進行屬性測試

**Feature: report-improvements, Property 6: 模塊一致性檢查**
**Validates: Requirements 8.1, 8.2, 8.3, 8.4**

測試 ModuleConsistencyChecker 的正確性：
- 當模塊建議存在矛盾時，報告應包含綜合分析區塊解釋差異
- 當多個模塊提供方向性建議時，應生成「綜合建議」區塊整合所有信號
- 當生成最終策略推薦時，應說明採納了哪些模塊的建議及原因
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import sys
import os

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from output_layer.module_consistency_checker import (
    ModuleConsistencyChecker, 
    ConsistencyResult, 
    ModuleSignal
)


# 策略生成器
direction_strategy = st.sampled_from(['Bullish', 'Bearish', 'Neutral'])
confidence_strategy = st.sampled_from(['High', 'Medium', 'Low'])
momentum_score_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)


def generate_module18_result(direction: str, confidence: str) -> dict:
    """生成 Module 18 結果"""
    action_map = {
        'Bullish': 'Long',
        'Bearish': 'Short',
        'Neutral': 'Neutral'
    }
    return {
        'iv_recommendation': {
            'action': action_map.get(direction, 'Neutral'),
            'confidence': confidence,
            'reason': f'IV Rank 建議 {action_map.get(direction, "Neutral")}'
        },
        'iv_rank': 50.0
    }


def generate_module21_result(momentum_score: float) -> dict:
    """生成 Module 21 結果"""
    if momentum_score > 0.7:
        recommendation = '強勢上漲，不建議逆勢Short'
    elif momentum_score > 0.4:
        recommendation = '中性，可謹慎操作'
    else:
        recommendation = '動量轉弱，可考慮Short'
    
    return {
        'status': 'success',
        'momentum_score': momentum_score,
        'recommendation': recommendation
    }


def generate_module24_result(direction: str, confidence: str) -> dict:
    """生成 Module 24 結果"""
    direction_map = {
        'Bullish': 'Call',
        'Bearish': 'Put',
        'Neutral': 'Neutral'
    }
    return {
        'status': 'success',
        'combined_direction': direction_map.get(direction, 'Neutral'),
        'confidence': confidence,
        'recommendation': f'技術分析建議 {direction_map.get(direction, "Neutral")}'
    }


class TestModuleConsistencyChecker:
    """
    **Feature: report-improvements, Property 6: 模塊一致性檢查**
    **Validates: Requirements 8.1, 8.2, 8.3, 8.4**
    """
    
    def setup_method(self):
        """每個測試方法前初始化一致性檢查器"""
        self.checker = ModuleConsistencyChecker()
    
    @given(
        direction18=direction_strategy,
        confidence18=confidence_strategy,
        momentum_score=momentum_score_strategy,
        direction24=direction_strategy,
        confidence24=confidence_strategy
    )
    @settings(max_examples=100)
    def test_consistency_check_returns_valid_result(
        self, direction18, confidence18, momentum_score, direction24, confidence24
    ):
        """
        **Feature: report-improvements, Property 6: 模塊一致性檢查**
        **Validates: Requirements 8.2**
        
        Property: For any combination of module results, check_consistency
        should return a valid ConsistencyResult with all required fields.
        """
        calculation_results = {
            'module18_historical_volatility': generate_module18_result(direction18, confidence18),
            'module21_momentum_filter': generate_module21_result(momentum_score),
            'module24_technical_direction': generate_module24_result(direction24, confidence24)
        }
        
        result = self.checker.check_consistency(calculation_results)
        
        # 驗證返回類型
        assert isinstance(result, ConsistencyResult), \
            "Result should be a ConsistencyResult instance"
        
        # 驗證所有必要字段存在
        assert hasattr(result, 'is_consistent'), "Result should have 'is_consistent' field"
        assert hasattr(result, 'conflicts'), "Result should have 'conflicts' field"
        assert hasattr(result, 'consolidated_direction'), "Result should have 'consolidated_direction' field"
        assert hasattr(result, 'confidence'), "Result should have 'confidence' field"
        assert hasattr(result, 'explanation'), "Result should have 'explanation' field"
        assert hasattr(result, 'module_signals'), "Result should have 'module_signals' field"
        assert hasattr(result, 'adopted_modules'), "Result should have 'adopted_modules' field"
        assert hasattr(result, 'adoption_reason'), "Result should have 'adoption_reason' field"
        
        # 驗證方向是有效值
        assert result.consolidated_direction in ['Bullish', 'Bearish', 'Neutral'], \
            f"Consolidated direction should be valid, got {result.consolidated_direction}"
        
        # 驗證信心度是有效值
        assert result.confidence in ['High', 'Medium', 'Low'], \
            f"Confidence should be valid, got {result.confidence}"
    
    @given(
        confidence18=confidence_strategy,
        confidence24=confidence_strategy
    )
    @settings(max_examples=100)
    def test_conflicting_signals_detected(self, confidence18, confidence24):
        """
        **Feature: report-improvements, Property 6: 模塊一致性檢查**
        **Validates: Requirements 8.1, 8.3**
        
        Property: When Module 18 suggests Long (Bullish) and Module 24 suggests
        Put (Bearish), the checker should detect a conflict.
        """
        calculation_results = {
            'module18_historical_volatility': generate_module18_result('Bullish', confidence18),
            'module21_momentum_filter': generate_module21_result(0.5),  # 中性
            'module24_technical_direction': generate_module24_result('Bearish', confidence24)
        }
        
        result = self.checker.check_consistency(calculation_results)
        
        # 應該檢測到矛盾
        assert not result.is_consistent, \
            "Should detect inconsistency when Module 18 is Bullish and Module 24 is Bearish"
        
        # 應該有矛盾記錄
        assert len(result.conflicts) > 0, \
            "Should have at least one conflict recorded"
        
        # 矛盾應該包含解釋
        for conflict in result.conflicts:
            assert 'explanation' in conflict, \
                "Each conflict should have an explanation"
            assert conflict['explanation'], \
                "Conflict explanation should not be empty"
    
    @given(
        direction=st.sampled_from(['Bullish', 'Bearish']),
        confidence18=confidence_strategy,
        confidence24=confidence_strategy
    )
    @settings(max_examples=100)
    def test_consistent_signals_no_conflict(self, direction, confidence18, confidence24):
        """
        **Feature: report-improvements, Property 6: 模塊一致性檢查**
        **Validates: Requirements 8.2**
        
        Property: When all modules suggest the same direction, there should
        be no conflicts detected.
        """
        # 設置動量得分以匹配方向
        if direction == 'Bullish':
            momentum_score = 0.8  # 高動量 -> Bullish
        else:
            momentum_score = 0.2  # 低動量 -> Bearish
        
        calculation_results = {
            'module18_historical_volatility': generate_module18_result(direction, confidence18),
            'module21_momentum_filter': generate_module21_result(momentum_score),
            'module24_technical_direction': generate_module24_result(direction, confidence24)
        }
        
        result = self.checker.check_consistency(calculation_results)
        
        # 應該沒有矛盾
        assert result.is_consistent, \
            f"Should be consistent when all modules suggest {direction}"
        
        # 矛盾列表應該為空
        assert len(result.conflicts) == 0, \
            "Should have no conflicts when all modules agree"
        
        # 綜合方向應該與輸入一致
        assert result.consolidated_direction == direction, \
            f"Consolidated direction should be {direction}, got {result.consolidated_direction}"
    
    @given(
        direction18=direction_strategy,
        confidence18=confidence_strategy,
        momentum_score=momentum_score_strategy,
        direction24=direction_strategy,
        confidence24=confidence_strategy
    )
    @settings(max_examples=100)
    def test_explanation_contains_module_signals(
        self, direction18, confidence18, momentum_score, direction24, confidence24
    ):
        """
        **Feature: report-improvements, Property 6: 模塊一致性檢查**
        **Validates: Requirements 8.2, 8.4**
        
        Property: The explanation should contain information about each
        module's signal.
        """
        calculation_results = {
            'module18_historical_volatility': generate_module18_result(direction18, confidence18),
            'module21_momentum_filter': generate_module21_result(momentum_score),
            'module24_technical_direction': generate_module24_result(direction24, confidence24)
        }
        
        result = self.checker.check_consistency(calculation_results)
        
        # 解釋應該包含各模塊的信息
        assert result.explanation, "Explanation should not be empty"
        
        # 應該提到各模塊
        assert '模塊' in result.explanation or '分析' in result.explanation, \
            "Explanation should mention modules or analysis"
    
    @given(
        direction18=direction_strategy,
        confidence18=confidence_strategy,
        momentum_score=momentum_score_strategy,
        direction24=direction_strategy,
        confidence24=confidence_strategy
    )
    @settings(max_examples=100)
    def test_adoption_reason_provided(
        self, direction18, confidence18, momentum_score, direction24, confidence24
    ):
        """
        **Feature: report-improvements, Property 6: 模塊一致性檢查**
        **Validates: Requirements 8.4**
        
        Property: The result should always provide an adoption reason
        explaining which modules' recommendations were adopted and why.
        """
        calculation_results = {
            'module18_historical_volatility': generate_module18_result(direction18, confidence18),
            'module21_momentum_filter': generate_module21_result(momentum_score),
            'module24_technical_direction': generate_module24_result(direction24, confidence24)
        }
        
        result = self.checker.check_consistency(calculation_results)
        
        # 應該有採納原因
        assert result.adoption_reason, \
            "Adoption reason should not be empty"
        
        # 採納原因應該是有意義的文字
        assert len(result.adoption_reason) > 5, \
            "Adoption reason should be meaningful text"


class TestConflictExplanationGeneration:
    """
    測試矛盾解釋生成
    
    **Feature: report-improvements, Property 6: 模塊一致性檢查**
    **Validates: Requirements 8.3**
    """
    
    def setup_method(self):
        """每個測試方法前初始化一致性檢查器"""
        self.checker = ModuleConsistencyChecker()
    
    def test_conflict_explanation_for_iv_vs_technical(self):
        """
        **Feature: report-improvements, Property 6: 模塊一致性檢查**
        **Validates: Requirements 8.1, 8.3**
        
        Test that when IV Rank suggests Long and Technical suggests Put,
        the conflict explanation mentions both IV and technical analysis.
        """
        calculation_results = {
            'module18_historical_volatility': generate_module18_result('Bullish', 'High'),
            'module24_technical_direction': generate_module24_result('Bearish', 'High')
        }
        
        result = self.checker.check_consistency(calculation_results)
        
        # 應該有矛盾
        assert len(result.conflicts) > 0, "Should detect conflict"
        
        # 矛盾解釋應該提到相關概念
        conflict = result.conflicts[0]
        explanation = conflict['explanation']
        
        # 解釋應該包含有意義的內容
        assert len(explanation) > 20, \
            "Conflict explanation should be detailed"
    
    def test_generate_conflict_explanation_method(self):
        """
        **Feature: report-improvements, Property 6: 模塊一致性檢查**
        **Validates: Requirements 8.3**
        
        Test the generate_conflict_explanation method directly.
        """
        # 創建一些矛盾
        conflicts = [
            {
                'module1': 'module18_historical_volatility',
                'module1_name': 'IV Rank 分析',
                'module1_direction': 'Bullish',
                'module1_reason': 'IV Rank 低，建議買入',
                'module2': 'module24_technical_direction',
                'module2_name': '技術方向分析',
                'module2_direction': 'Bearish',
                'module2_reason': '技術指標看跌',
                'conflict_type': 'direction_conflict',
                'explanation': '測試解釋'
            }
        ]
        
        report = self.checker.generate_conflict_explanation(conflicts)
        
        # 報告應該包含矛盾信息
        assert '矛盾' in report, "Report should mention conflicts"
        assert 'IV Rank' in report, "Report should mention IV Rank"
        assert '技術' in report, "Report should mention technical analysis"
    
    def test_no_conflict_explanation(self):
        """
        **Feature: report-improvements, Property 6: 模塊一致性檢查**
        **Validates: Requirements 8.2**
        
        Test that when there are no conflicts, the explanation indicates
        consistency.
        """
        conflicts = []
        
        report = self.checker.generate_conflict_explanation(conflicts)
        
        # 報告應該表示一致
        assert '一致' in report or '無矛盾' in report, \
            "Report should indicate consistency when no conflicts"


class TestFormattedRecommendation:
    """
    測試格式化綜合建議
    
    **Feature: report-improvements, Property 6: 模塊一致性檢查**
    **Validates: Requirements 8.2, 8.4**
    """
    
    def setup_method(self):
        """每個測試方法前初始化一致性檢查器"""
        self.checker = ModuleConsistencyChecker()
    
    @given(
        direction18=direction_strategy,
        confidence18=confidence_strategy,
        momentum_score=momentum_score_strategy,
        direction24=direction_strategy,
        confidence24=confidence_strategy
    )
    @settings(max_examples=100)
    def test_formatted_recommendation_contains_required_sections(
        self, direction18, confidence18, momentum_score, direction24, confidence24
    ):
        """
        **Feature: report-improvements, Property 6: 模塊一致性檢查**
        **Validates: Requirements 8.2, 8.4**
        
        Property: The formatted recommendation should contain all required
        sections: module signals, conflicts (if any), conclusion, and
        trading suggestions.
        """
        calculation_results = {
            'module18_historical_volatility': generate_module18_result(direction18, confidence18),
            'module21_momentum_filter': generate_module21_result(momentum_score),
            'module24_technical_direction': generate_module24_result(direction24, confidence24)
        }
        
        result = self.checker.check_consistency(calculation_results)
        report = self.checker.format_consolidated_recommendation(result)
        
        # 報告應該包含標題
        assert '綜合建議' in report, "Report should contain title '綜合建議'"
        
        # 報告應該包含模塊信號區塊
        assert '方向性信號' in report or '模塊' in report, \
            "Report should contain module signals section"
        
        # 報告應該包含結論
        assert '結論' in report, "Report should contain conclusion section"
        
        # 報告應該包含交易建議
        assert '建議' in report, "Report should contain trading suggestions"
    
    @given(
        confidence18=confidence_strategy,
        confidence24=confidence_strategy
    )
    @settings(max_examples=100)
    def test_formatted_recommendation_shows_conflicts(self, confidence18, confidence24):
        """
        **Feature: report-improvements, Property 6: 模塊一致性檢查**
        **Validates: Requirements 8.1, 8.3**
        
        Property: When there are conflicts, the formatted recommendation
        should clearly show the conflict warning.
        """
        # 創建矛盾的結果
        calculation_results = {
            'module18_historical_volatility': generate_module18_result('Bullish', confidence18),
            'module24_technical_direction': generate_module24_result('Bearish', confidence24)
        }
        
        result = self.checker.check_consistency(calculation_results)
        report = self.checker.format_consolidated_recommendation(result)
        
        # 報告應該包含矛盾警告
        assert '矛盾' in report or '⚠️' in report, \
            "Report should show conflict warning when conflicts exist"


class TestEmptyAndPartialResults:
    """
    測試空結果和部分結果的處理
    """
    
    def setup_method(self):
        """每個測試方法前初始化一致性檢查器"""
        self.checker = ModuleConsistencyChecker()
    
    def test_empty_calculation_results(self):
        """
        Test handling of empty calculation results.
        """
        calculation_results = {}
        
        result = self.checker.check_consistency(calculation_results)
        
        # 應該返回有效結果
        assert isinstance(result, ConsistencyResult)
        assert result.consolidated_direction in ['Bullish', 'Bearish', 'Neutral']
    
    def test_partial_module_results(self):
        """
        Test handling when only some modules have results.
        """
        calculation_results = {
            'module18_historical_volatility': generate_module18_result('Bullish', 'High')
            # 其他模塊缺失
        }
        
        result = self.checker.check_consistency(calculation_results)
        
        # 應該返回有效結果
        assert isinstance(result, ConsistencyResult)
        assert len(result.module_signals) == 1
    
    def test_module_with_error_status(self):
        """
        Test handling when a module has error status.
        """
        calculation_results = {
            'module18_historical_volatility': generate_module18_result('Bullish', 'High'),
            'module21_momentum_filter': {'status': 'error', 'reason': 'Test error'},
            'module24_technical_direction': generate_module24_result('Bullish', 'High')
        }
        
        result = self.checker.check_consistency(calculation_results)
        
        # 應該返回有效結果，忽略錯誤的模塊
        assert isinstance(result, ConsistencyResult)
        # Module 21 應該被忽略
        assert 'module21_momentum_filter' not in result.module_signals


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
