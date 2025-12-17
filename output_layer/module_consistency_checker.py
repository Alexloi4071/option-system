#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模塊一致性檢查器

Requirements: 8.1, 8.2, 8.3, 8.4
- 檢查各模塊建議的一致性
- 生成綜合分析解釋差異
- 標示矛盾並提供解釋
- 說明採納的建議及原因
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class ModuleSignal:
    """模塊信號數據"""
    module_name: str
    direction: str  # 'Bullish', 'Bearish', 'Neutral'
    confidence: str  # 'High', 'Medium', 'Low'
    reason: str
    weight: float  # 權重 (0-1)


@dataclass
class ConsistencyResult:
    """一致性檢查結果"""
    is_consistent: bool
    conflicts: List[Dict]
    consolidated_direction: str  # 'Bullish', 'Bearish', 'Neutral'
    confidence: str  # 'High', 'Medium', 'Low'
    explanation: str
    module_signals: Dict[str, ModuleSignal]
    adopted_modules: List[str]  # 採納的模塊列表
    adoption_reason: str  # 採納原因


class ModuleConsistencyChecker:
    """
    模塊一致性檢查器
    
    負責檢查各模塊建議的一致性並生成綜合分析。
    
    Requirements: 8.1, 8.2, 8.3, 8.4
    """
    
    # 提供方向性建議的模塊及其權重
    DIRECTIONAL_MODULES = {
        'module18_historical_volatility': {
            'name': 'IV Rank 分析',
            'weight': 0.3,
            'description': '基於隱含波動率的相對位置'
        },
        'module21_momentum_filter': {
            'name': '動量過濾器',
            'weight': 0.35,
            'description': '基於價格和成交量動量'
        },
        'module24_technical_direction': {
            'name': '技術方向分析',
            'weight': 0.35,
            'description': '基於技術指標的綜合分析'
        }
    }
    
    # 方向映射
    DIRECTION_MAPPING = {
        # Module 18 IV Rank 建議映射
        'Long': 'Bullish',
        'Short': 'Bearish',
        'Neutral': 'Neutral',
        'Hold': 'Neutral',
        # Module 21 動量建議映射
        '強勢': 'Bullish',
        '中性': 'Neutral',
        '轉弱': 'Bearish',
        # Module 24 技術方向映射
        'Call': 'Bullish',
        'Put': 'Bearish',
        'Bullish': 'Bullish',
        'Bearish': 'Bearish'
    }
    
    def __init__(self):
        """初始化一致性檢查器"""
        pass
    
    def check_consistency(self, calculation_results: Dict) -> ConsistencyResult:
        """
        檢查模塊間的一致性
        
        Requirements: 8.1, 8.2, 8.3
        
        參數:
            calculation_results: 所有模塊的計算結果
            
        返回:
            ConsistencyResult: 一致性檢查結果
        """
        # 提取各模塊的方向性信號
        module_signals = self._extract_module_signals(calculation_results)
        
        # 檢測矛盾
        conflicts = self._detect_conflicts(module_signals)
        
        # 計算綜合方向
        consolidated = self._calculate_consolidated_direction(module_signals)
        
        # 生成解釋
        explanation = self._generate_explanation(module_signals, conflicts, consolidated)
        
        # 確定採納的模塊和原因
        adopted_modules, adoption_reason = self._determine_adoption(
            module_signals, conflicts, consolidated
        )
        
        return ConsistencyResult(
            is_consistent=len(conflicts) == 0,
            conflicts=conflicts,
            consolidated_direction=consolidated['direction'],
            confidence=consolidated['confidence'],
            explanation=explanation,
            module_signals=module_signals,
            adopted_modules=adopted_modules,
            adoption_reason=adoption_reason
        )
    
    def _extract_module_signals(self, calculation_results: Dict) -> Dict[str, ModuleSignal]:
        """
        從計算結果中提取各模塊的方向性信號
        
        參數:
            calculation_results: 所有模塊的計算結果
            
        返回:
            Dict[str, ModuleSignal]: 各模塊的信號
        """
        signals = {}
        
        # Module 18: IV Rank 分析
        module18 = calculation_results.get('module18_historical_volatility', {})
        if module18 and not module18.get('error'):
            iv_recommendation = module18.get('iv_recommendation', {})
            action = iv_recommendation.get('action', 'Neutral')
            confidence = iv_recommendation.get('confidence', 'Medium')
            reason = iv_recommendation.get('reason', 'N/A')
            
            direction = self.DIRECTION_MAPPING.get(action, 'Neutral')
            
            signals['module18_historical_volatility'] = ModuleSignal(
                module_name='IV Rank 分析',
                direction=direction,
                confidence=confidence,
                reason=reason,
                weight=self.DIRECTIONAL_MODULES['module18_historical_volatility']['weight']
            )
        
        # Module 21: 動量過濾器
        module21 = calculation_results.get('module21_momentum_filter', {})
        if module21 and module21.get('status') not in ['error', 'skipped']:
            momentum_score = module21.get('momentum_score', 0.5)
            recommendation = module21.get('recommendation', 'N/A')
            
            # 根據動量得分判斷方向
            if momentum_score > 0.7:
                direction = 'Bullish'
                confidence = 'High'
            elif momentum_score > 0.4:
                direction = 'Neutral'
                confidence = 'Medium'
            else:
                direction = 'Bearish'
                confidence = 'High'
            
            signals['module21_momentum_filter'] = ModuleSignal(
                module_name='動量過濾器',
                direction=direction,
                confidence=confidence,
                reason=f"動量得分: {momentum_score:.2f}",
                weight=self.DIRECTIONAL_MODULES['module21_momentum_filter']['weight']
            )
        
        # Module 24: 技術方向分析
        module24 = calculation_results.get('module24_technical_direction', {})
        if module24 and module24.get('status') not in ['error', 'skipped']:
            combined_direction = module24.get('combined_direction', 'Neutral')
            confidence = module24.get('confidence', 'Medium')
            recommendation = module24.get('recommendation', 'N/A')
            
            direction = self.DIRECTION_MAPPING.get(combined_direction, 'Neutral')
            
            signals['module24_technical_direction'] = ModuleSignal(
                module_name='技術方向分析',
                direction=direction,
                confidence=confidence,
                reason=recommendation,
                weight=self.DIRECTIONAL_MODULES['module24_technical_direction']['weight']
            )
        
        return signals
    
    def _detect_conflicts(self, module_signals: Dict[str, ModuleSignal]) -> List[Dict]:
        """
        檢測模塊間的矛盾
        
        Requirements: 8.1, 8.3
        
        參數:
            module_signals: 各模塊的信號
            
        返回:
            List[Dict]: 矛盾列表
        """
        conflicts = []
        
        # 獲取所有非中性的信號
        directional_signals = {
            k: v for k, v in module_signals.items() 
            if v.direction != 'Neutral'
        }
        
        # 檢查是否有相反的方向
        bullish_modules = [k for k, v in directional_signals.items() if v.direction == 'Bullish']
        bearish_modules = [k for k, v in directional_signals.items() if v.direction == 'Bearish']
        
        # 如果同時存在看漲和看跌信號，則存在矛盾
        if bullish_modules and bearish_modules:
            for bull_mod in bullish_modules:
                for bear_mod in bearish_modules:
                    bull_signal = module_signals[bull_mod]
                    bear_signal = module_signals[bear_mod]
                    
                    conflict = {
                        'module1': bull_mod,
                        'module1_name': bull_signal.module_name,
                        'module1_direction': 'Bullish',
                        'module1_reason': bull_signal.reason,
                        'module2': bear_mod,
                        'module2_name': bear_signal.module_name,
                        'module2_direction': 'Bearish',
                        'module2_reason': bear_signal.reason,
                        'conflict_type': 'direction_conflict',
                        'explanation': self._generate_conflict_explanation(
                            bull_signal, bear_signal
                        )
                    }
                    conflicts.append(conflict)
        
        return conflicts
    
    def _generate_conflict_explanation(
        self, 
        signal1: ModuleSignal, 
        signal2: ModuleSignal
    ) -> str:
        """
        生成矛盾解釋
        
        Requirements: 8.3
        
        參數:
            signal1: 第一個信號
            signal2: 第二個信號
            
        返回:
            str: 矛盾解釋
        """
        explanations = []
        
        # 根據模塊類型生成解釋
        if 'IV Rank' in signal1.module_name or 'IV Rank' in signal2.module_name:
            explanations.append(
                "IV Rank 基於波動率的相對位置，反映期權定價的高低；"
            )
        
        if '動量' in signal1.module_name or '動量' in signal2.module_name:
            explanations.append(
                "動量指標反映價格趨勢的強度，可能與波動率信號不同步；"
            )
        
        if '技術' in signal1.module_name or '技術' in signal2.module_name:
            explanations.append(
                "技術分析基於價格形態和指標，可能與基本面信號存在時間差；"
            )
        
        # 添加通用解釋
        explanations.append(
            f"{signal1.module_name}建議{signal1.direction}（{signal1.reason}），"
            f"而{signal2.module_name}建議{signal2.direction}（{signal2.reason}）。"
        )
        
        return "".join(explanations)
    
    def _calculate_consolidated_direction(
        self, 
        module_signals: Dict[str, ModuleSignal]
    ) -> Dict[str, str]:
        """
        計算綜合方向
        
        Requirements: 8.2
        
        參數:
            module_signals: 各模塊的信號
            
        返回:
            Dict: 包含 direction 和 confidence
        """
        if not module_signals:
            return {'direction': 'Neutral', 'confidence': 'Low'}
        
        # 計算加權得分
        bullish_score = 0.0
        bearish_score = 0.0
        total_weight = 0.0
        
        for module_key, signal in module_signals.items():
            weight = signal.weight
            
            # 根據信心度調整權重
            confidence_multiplier = {
                'High': 1.0,
                'Medium': 0.7,
                'Low': 0.4
            }.get(signal.confidence, 0.5)
            
            adjusted_weight = weight * confidence_multiplier
            
            if signal.direction == 'Bullish':
                bullish_score += adjusted_weight
            elif signal.direction == 'Bearish':
                bearish_score += adjusted_weight
            
            total_weight += adjusted_weight
        
        # 計算淨得分
        if total_weight == 0:
            return {'direction': 'Neutral', 'confidence': 'Low'}
        
        net_score = (bullish_score - bearish_score) / total_weight
        
        # 確定方向
        if net_score > 0.2:
            direction = 'Bullish'
        elif net_score < -0.2:
            direction = 'Bearish'
        else:
            direction = 'Neutral'
        
        # 確定信心度
        score_magnitude = abs(net_score)
        if score_magnitude > 0.6:
            confidence = 'High'
        elif score_magnitude > 0.3:
            confidence = 'Medium'
        else:
            confidence = 'Low'
        
        return {'direction': direction, 'confidence': confidence}
    
    def _generate_explanation(
        self,
        module_signals: Dict[str, ModuleSignal],
        conflicts: List[Dict],
        consolidated: Dict[str, str]
    ) -> str:
        """
        生成綜合解釋
        
        Requirements: 8.2, 8.3
        
        參數:
            module_signals: 各模塊的信號
            conflicts: 矛盾列表
            consolidated: 綜合方向
            
        返回:
            str: 綜合解釋
        """
        explanation_parts = []
        
        # 列出各模塊的信號
        if module_signals:
            explanation_parts.append("各模塊分析結果：")
            for module_key, signal in module_signals.items():
                direction_cn = {
                    'Bullish': '看漲',
                    'Bearish': '看跌',
                    'Neutral': '中性'
                }.get(signal.direction, signal.direction)
                
                explanation_parts.append(
                    f"  • {signal.module_name}: {direction_cn} "
                    f"(信心度: {signal.confidence})"
                )
        
        # 說明矛盾
        if conflicts:
            explanation_parts.append("")
            explanation_parts.append(f"⚠️ 發現 {len(conflicts)} 個信號矛盾：")
            for i, conflict in enumerate(conflicts, 1):
                explanation_parts.append(
                    f"  {i}. {conflict['module1_name']} vs {conflict['module2_name']}"
                )
        
        # 說明綜合結論
        direction_cn = {
            'Bullish': '看漲',
            'Bearish': '看跌',
            'Neutral': '中性'
        }.get(consolidated['direction'], consolidated['direction'])
        
        explanation_parts.append("")
        explanation_parts.append(
            f"綜合結論: {direction_cn} (信心度: {consolidated['confidence']})"
        )
        
        return "\n".join(explanation_parts)
    
    def _determine_adoption(
        self,
        module_signals: Dict[str, ModuleSignal],
        conflicts: List[Dict],
        consolidated: Dict[str, str]
    ) -> tuple:
        """
        確定採納的模塊和原因
        
        Requirements: 8.4
        
        改進邏輯：
        1. 當有矛盾時，優先採納信心度最高的模塊
        2. 如果信心度相同，採納權重最高的模塊
        3. 清楚說明採納原因和被否決的模塊
        
        參數:
            module_signals: 各模塊的信號
            conflicts: 矛盾列表
            consolidated: 綜合方向
            
        返回:
            tuple: (adopted_modules, adoption_reason)
        """
        adopted_modules = []
        reasons = []
        
        consolidated_direction = consolidated['direction']
        
        # 信心度權重映射
        confidence_weight = {'High': 3, 'Medium': 2, 'Low': 1}
        
        # 找出與綜合方向一致的模塊，並按信心度排序
        matching_signals = []
        opposing_signals = []
        neutral_signals = []
        
        for module_key, signal in module_signals.items():
            if signal.direction == consolidated_direction:
                matching_signals.append(signal)
                adopted_modules.append(signal.module_name)
            elif signal.direction == 'Neutral':
                neutral_signals.append(signal)
            else:
                opposing_signals.append(signal)
        
        # 生成採納原因
        if not conflicts:
            reasons.append("所有模塊信號一致")
        else:
            # 有矛盾時，詳細說明採納原因
            if matching_signals:
                # 找出信心度最高的採納模塊
                best_match = max(matching_signals, 
                               key=lambda s: (confidence_weight.get(s.confidence, 0), s.weight))
                
                # 找出被否決的模塊
                rejected_names = [s.module_name for s in opposing_signals]
                
                # 說明採納原因
                if best_match.confidence == 'High':
                    reasons.append(f"採納 {best_match.module_name}（信心度: High）")
                    if rejected_names:
                        reasons.append(f"否決 {', '.join(rejected_names)}（信心度較低或方向相反）")
                elif len(matching_signals) > len(opposing_signals):
                    reasons.append(f"多數模塊（{len(matching_signals)}/{len(module_signals)}）支持此方向")
                else:
                    # 基於加權得分
                    matching_score = sum(
                        s.weight * confidence_weight.get(s.confidence, 1) 
                        for s in matching_signals
                    )
                    opposing_score = sum(
                        s.weight * confidence_weight.get(s.confidence, 1) 
                        for s in opposing_signals
                    )
                    reasons.append(
                        f"加權得分: 採納方 {matching_score:.2f} vs 否決方 {opposing_score:.2f}"
                    )
            else:
                # 沒有匹配的模塊，可能是中性結論
                if neutral_signals:
                    reasons.append("多數模塊為中性信號")
                else:
                    reasons.append("信號相互抵消，建議觀望")
        
        adoption_reason = "；".join(reasons) if reasons else "無明確採納原因"
        
        return adopted_modules, adoption_reason
    
    def generate_conflict_explanation(self, conflicts: List[Dict]) -> str:
        """
        生成矛盾解釋報告
        
        Requirements: 8.3
        
        參數:
            conflicts: 矛盾列表
            
        返回:
            str: 矛盾解釋報告
        """
        if not conflicts:
            return "各模塊建議一致，無矛盾。"
        
        report_parts = []
        report_parts.append(f"發現 {len(conflicts)} 個模塊間的建議矛盾：")
        report_parts.append("")
        
        for i, conflict in enumerate(conflicts, 1):
            report_parts.append(f"矛盾 {i}:")
            report_parts.append(
                f"  • {conflict['module1_name']}: {conflict['module1_direction']}"
            )
            report_parts.append(f"    原因: {conflict['module1_reason']}")
            report_parts.append(
                f"  • {conflict['module2_name']}: {conflict['module2_direction']}"
            )
            report_parts.append(f"    原因: {conflict['module2_reason']}")
            report_parts.append("")
            report_parts.append(f"  解釋: {conflict['explanation']}")
            report_parts.append("")
        
        return "\n".join(report_parts)
    
    def format_consolidated_recommendation(
        self, 
        consistency_result: ConsistencyResult
    ) -> str:
        """
        格式化綜合建議報告
        
        Requirements: 8.2, 8.4
        
        參數:
            consistency_result: 一致性檢查結果
            
        返回:
            str: 格式化的綜合建議報告
        """
        report = "\n" + "=" * 70 + "\n"
        report += "綜合建議\n"
        report += "=" * 70 + "\n\n"
        
        # 各模塊信號摘要
        report += "📊 各模塊方向性信號:\n"
        report += "─" * 70 + "\n"
        
        direction_emoji = {
            'Bullish': '📈',
            'Bearish': '📉',
            'Neutral': '➖'
        }
        
        direction_cn = {
            'Bullish': '看漲',
            'Bearish': '看跌',
            'Neutral': '中性'
        }
        
        for module_key, signal in consistency_result.module_signals.items():
            emoji = direction_emoji.get(signal.direction, '❓')
            dir_cn = direction_cn.get(signal.direction, signal.direction)
            report += f"  {emoji} {signal.module_name}: {dir_cn} "
            report += f"(信心度: {signal.confidence})\n"
            report += f"     └─ {signal.reason}\n"
        
        report += "\n"
        
        # 矛盾警告
        if consistency_result.conflicts:
            report += "⚠️ 信號矛盾警告:\n"
            report += "─" * 70 + "\n"
            
            for conflict in consistency_result.conflicts:
                report += f"  • {conflict['module1_name']} ({conflict['module1_direction']}) "
                report += f"vs {conflict['module2_name']} ({conflict['module2_direction']})\n"
                report += f"    解釋: {conflict['explanation']}\n"
            
            report += "\n"
        
        # 綜合結論
        report += "🎯 綜合結論:\n"
        report += "─" * 70 + "\n"
        
        consolidated_emoji = direction_emoji.get(
            consistency_result.consolidated_direction, '❓'
        )
        consolidated_cn = direction_cn.get(
            consistency_result.consolidated_direction, 
            consistency_result.consolidated_direction
        )
        
        report += f"  方向: {consolidated_emoji} {consolidated_cn}\n"
        report += f"  信心度: {consistency_result.confidence}\n"
        
        if consistency_result.adopted_modules:
            report += f"  採納模塊: {', '.join(consistency_result.adopted_modules)}\n"
        
        report += f"  採納原因: {consistency_result.adoption_reason}\n"
        
        report += "\n"
        
        # 交易建議
        report += "💡 交易建議:\n"
        report += "─" * 70 + "\n"
        
        # 根據矛盾情況調整建議
        has_conflicts = len(consistency_result.conflicts) > 0
        conflict_warning = "（存在信號矛盾，建議謹慎）" if has_conflicts else ""
        
        if consistency_result.consolidated_direction == 'Bullish':
            if consistency_result.confidence == 'High' and not has_conflicts:
                report += "  建議考慮 Long Call 或 Short Put 策略\n"
                report += "  信號強度較高，可適當增加倉位\n"
            elif consistency_result.confidence == 'High' and has_conflicts:
                report += "  可考慮 Long Call 策略，但存在矛盾信號\n"
                report += "  建議控制倉位，設置嚴格止損\n"
            elif consistency_result.confidence == 'Medium':
                report += f"  可考慮 Long Call 策略，但建議控制倉位{conflict_warning}\n"
                report += "  等待更多確認信號\n"
            else:
                report += "  信號較弱，建議觀望或小倉位試探\n"
                report += "  不建議重倉操作\n"
        elif consistency_result.consolidated_direction == 'Bearish':
            if consistency_result.confidence == 'High' and not has_conflicts:
                report += "  建議考慮 Long Put 或 Short Call 策略\n"
                report += "  信號強度較高，可適當增加倉位\n"
            elif consistency_result.confidence == 'High' and has_conflicts:
                report += "  可考慮 Long Put 策略，但存在矛盾信號\n"
                report += "  建議控制倉位，設置嚴格止損\n"
            elif consistency_result.confidence == 'Medium':
                report += f"  可考慮 Long Put 策略，但建議控制倉位{conflict_warning}\n"
                report += "  等待更多確認信號\n"
            else:
                report += "  信號較弱，建議觀望或小倉位試探\n"
                report += "  不建議重倉操作\n"
        else:
            report += "  市場方向不明確，建議觀望\n"
            if has_conflicts:
                report += "  多個模塊信號矛盾，等待方向明確\n"
            else:
                report += "  可考慮中性策略如 Iron Condor 或 Straddle\n"
        
        # 矛盾詳情
        if has_conflicts:
            report += "\n"
            report += "  ⚠️ 矛盾詳情:\n"
            for conflict in consistency_result.conflicts:
                report += f"    • {conflict['module1_name']} 建議 {conflict['module1_direction']}\n"
                report += f"      vs {conflict['module2_name']} 建議 {conflict['module2_direction']}\n"
        
        report += "\n"
        
        return report
