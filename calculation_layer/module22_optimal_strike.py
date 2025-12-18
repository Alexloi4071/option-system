#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module 22: 最佳行使價分析

功能:
1. 分析 ATM ± 15% 範圍內所有行使價
2. 計算綜合評分：流動性(30%) + Greeks(30%) + IV(20%) + 風險回報(20%)
3. 為 Long Call/Put, Short Call/Put 推薦最佳行使價
4. 整合金曹三不買原則的流動性檢查

來源: 金曹《期權制勝》三不買原則 + 美股期權市場最佳實踐

作者: Kiro
日期: 2025-11-25
版本: 1.0.0
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

# 導入統一的數據標準化工具
try:
    from utils.data_normalization import normalize_numeric_value, is_valid_numeric
except ImportError:
    # 回退實現
    import math
    def normalize_numeric_value(value, default=None):
        if value is None:
            return default
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return default
        return value
    def is_valid_numeric(value):
        if value is None:
            return False
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return False
        return True

logger = logging.getLogger(__name__)


@dataclass
class StrikeAnalysis:
    """單個行使價的分析結果"""
    strike: float
    option_type: str  # 'call' or 'put'
    
    # 價格數據
    bid: float = 0.0
    ask: float = 0.0
    last_price: float = 0.0
    theoretical_price: float = 0.0
    
    # Greeks
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    
    # 流動性指標
    volume: int = 0
    open_interest: int = 0
    bid_ask_spread_pct: float = 0.0
    
    # IV 指標
    iv: float = 0.0
    iv_rank: float = 50.0
    iv_skew: float = 0.0  # 相對於ATM的IV差異
    iv_source: str = 'unknown'  # IV 來源: 'module17', 'yahoo', 'default'
    
    # 評分
    liquidity_score: float = 0.0
    greeks_score: float = 0.0
    iv_score: float = 0.0
    risk_reward_score: float = 0.0
    composite_score: float = 0.0
    
    # 策略適用性
    strategy_suitability: Dict[str, float] = field(default_factory=dict)
    
    # 風險回報指標
    max_loss: float = 0.0
    breakeven: float = 0.0
    potential_profit: float = 0.0
    
    # 增強風險回報指標 (Requirements 3.1)
    win_probability: float = 0.0  # 勝率估算（基於 Delta）
    expected_return: float = 0.0  # 預期收益
    theta_adjusted_return: float = 0.0  # Theta 調整後的預期收益
    
    # Put-Call Parity 驗證字段 (Requirements 4.4)
    parity_valid: Optional[bool] = None  # Parity 驗證是否通過
    parity_deviation_pct: Optional[float] = None  # Parity 偏離百分比
    
    # Short Put 安全概率 (Requirements 2.5)
    safety_probability: float = 0.0  # 安全概率 (1 - |Delta|)
    
    # ===== Long/Short 策略增強字段 (Task 1.1, 1.2) =====
    
    # Long 策略專用字段 (Task 1.1)
    multi_scenario_profit: Optional[Dict] = None  # 多場景收益分析
    optimal_exit_timing: Optional[Dict] = None    # 最佳退出時機
    max_profit_score: float = 0.0                 # 利益最大化評分 (Long) / 期權金安全性評分 (Short)
    
    # Short 策略專用字段 (Task 1.2)
    premium_analysis: Optional[Dict] = None       # 期權金收入和安全性分析
    hold_to_expiry_advantage: Optional[Dict] = None  # 持有到期優勢
    
    def to_dict(self) -> Dict:
        return {
            'strike': self.strike,
            'option_type': self.option_type,
            'bid': round(self.bid, 2),
            'ask': round(self.ask, 2),
            'last_price': round(self.last_price, 2),
            'theoretical_price': round(self.theoretical_price, 2),
            'delta': round(self.delta, 4),
            'gamma': round(self.gamma, 4),
            'theta': round(self.theta, 4),
            'vega': round(self.vega, 4),
            'volume': self.volume,
            'open_interest': self.open_interest,
            'bid_ask_spread_pct': round(self.bid_ask_spread_pct, 2),
            'iv': round(self.iv, 2),
            'iv_rank': round(self.iv_rank, 2),
            'iv_skew': round(self.iv_skew, 2),
            'iv_source': self.iv_source,
            'liquidity_score': round(self.liquidity_score, 2),
            'greeks_score': round(self.greeks_score, 2),
            'iv_score': round(self.iv_score, 2),
            'risk_reward_score': round(self.risk_reward_score, 2),
            'composite_score': round(self.composite_score, 2),
            'strategy_suitability': self.strategy_suitability,
            'max_loss': round(self.max_loss, 2),
            'breakeven': round(self.breakeven, 2),
            'potential_profit': round(self.potential_profit, 2),
            'win_probability': round(self.win_probability, 4),
            'expected_return': round(self.expected_return, 2),
            'theta_adjusted_return': round(self.theta_adjusted_return, 2),
            'parity_valid': self.parity_valid,
            'parity_deviation_pct': round(self.parity_deviation_pct, 2) if self.parity_deviation_pct is not None else None,
            'safety_probability': round(self.safety_probability, 4),  # Requirements 2.5
            # Long/Short 策略增強字段 (Task 1.1, 1.2)
            'multi_scenario_profit': self.multi_scenario_profit,
            'optimal_exit_timing': self.optimal_exit_timing,
            'max_profit_score': round(self.max_profit_score, 2),
            'premium_analysis': self.premium_analysis,
            'hold_to_expiry_advantage': self.hold_to_expiry_advantage
        }


class OptimalStrikeCalculator:
    """
    最佳行使價計算器
    
    基於金曹《期權制勝》三不買原則，整合美股期權市場最佳實踐，
    為 Long Call/Put, Short Call/Put 策略推薦最佳行使價。
    
    評分權重:
    - 流動性分數: 30% (Volume, OI, Bid-Ask Spread)
    - Greeks分數: 30% (Delta, Theta, Vega)
    - IV分數: 20% (IV Rank, IV Percentile, IV Skew)
    - 風險回報分數: 20% (Max Loss, Breakeven, Potential Profit)
    """
    
    # 評分權重
    WEIGHT_LIQUIDITY = 0.30
    WEIGHT_GREEKS = 0.30
    WEIGHT_IV = 0.20
    WEIGHT_RISK_REWARD = 0.20
    
    # 流動性閾值（金曹三不買原則）- 修改為 OR 邏輯
    MIN_VOLUME = 10
    MIN_OPEN_INTEREST = 100
    MAX_BID_ASK_SPREAD_PCT = 10.0
    
    # 推薦閾值
    RECOMMENDED_VOLUME = 100
    RECOMMENDED_OPEN_INTEREST = 500
    RECOMMENDED_BID_ASK_SPREAD_PCT = 5.0
    
    # IV 默認值
    DEFAULT_IV = 0.30
    
    # 行使價數量限制（ATM 上下各取最多 20 個）
    MAX_STRIKES_EACH_SIDE = 20
    
    def __init__(self):
        logger.info("* 最佳行使價計算器已初始化")
        self._iv_calculator = None
        self._bs_calculator = None
    
    def _get_bs_calculator(self):
        """延遲初始化 Black-Scholes 計算器"""
        if self._bs_calculator is None:
            from calculation_layer.module15_black_scholes import BlackScholesCalculator
            self._bs_calculator = BlackScholesCalculator()
        return self._bs_calculator
    
    # ===== Task 2.1, 2.3: 目標價和風險邊界確定方法 =====
    
    def _determine_target_price(
        self,
        current_price: float,
        strategy_type: str,
        support_resistance_data: Optional[Dict]
    ) -> float:
        """
        確定 Long 策略的目標價
        
        參數:
            current_price: 當前股價
            strategy_type: 策略類型 ('long_call' 或 'long_put')
            support_resistance_data: 支持阻力位數據
                {
                    'resistance_level': float,  # 阻力位
                    'support_level': float,     # 支持位
                    'resistance_levels': List[float],  # 多個阻力位
                    'support_levels': List[float]      # 多個支持位
                }
        
        返回:
            float: 目標價格
        
        Requirements: 8.1, 8.2, 8.5
        """
        try:
            if strategy_type == 'long_call':
                # Long Call: 使用阻力位作為目標價
                if support_resistance_data:
                    # 優先使用最近的阻力位
                    resistance = support_resistance_data.get('resistance_level')
                    if resistance and resistance > current_price:
                        logger.debug(f"  Long Call 目標價: ${resistance:.2f} (阻力位)")
                        return resistance
                    
                    # 嘗試從多個阻力位中找到最近的
                    resistance_levels = support_resistance_data.get('resistance_levels', [])
                    valid_resistances = [r for r in resistance_levels if r > current_price]
                    if valid_resistances:
                        target = min(valid_resistances)
                        logger.debug(f"  Long Call 目標價: ${target:.2f} (最近阻力位)")
                        return target
                
                # 默認值: 當前股價 +10%
                target = current_price * 1.10
                logger.debug(f"  Long Call 目標價: ${target:.2f} (默認 +10%)")
                return target
                
            elif strategy_type == 'long_put':
                # Long Put: 使用支持位作為目標價
                if support_resistance_data:
                    # 優先使用最近的支持位
                    support = support_resistance_data.get('support_level')
                    if support and support < current_price:
                        logger.debug(f"  Long Put 目標價: ${support:.2f} (支持位)")
                        return support
                    
                    # 嘗試從多個支持位中找到最近的
                    support_levels = support_resistance_data.get('support_levels', [])
                    valid_supports = [s for s in support_levels if s < current_price]
                    if valid_supports:
                        target = max(valid_supports)
                        logger.debug(f"  Long Put 目標價: ${target:.2f} (最近支持位)")
                        return target
                
                # 默認值: 當前股價 -10%
                target = current_price * 0.90
                logger.debug(f"  Long Put 目標價: ${target:.2f} (默認 -10%)")
                return target
            
            else:
                # 非 Long 策略，返回當前股價
                return current_price
                
        except Exception as e:
            logger.warning(f"確定目標價失敗: {e}，使用默認值")
            if strategy_type == 'long_call':
                return current_price * 1.10
            elif strategy_type == 'long_put':
                return current_price * 0.90
            return current_price
    
    def _determine_risk_boundary(
        self,
        current_price: float,
        strategy_type: str,
        support_resistance_data: Optional[Dict]
    ) -> float:
        """
        確定 Short 策略的風險邊界
        
        參數:
            current_price: 當前股價
            strategy_type: 策略類型 ('short_call' 或 'short_put')
            support_resistance_data: 支持阻力位數據
        
        返回:
            float: 風險邊界價格
        
        Requirements: 8.3, 8.4, 8.5
        """
        try:
            if strategy_type == 'short_call':
                # Short Call: 使用阻力位作為風險邊界（不希望股價突破）
                if support_resistance_data:
                    resistance = support_resistance_data.get('resistance_level')
                    if resistance and resistance > current_price:
                        logger.debug(f"  Short Call 風險邊界: ${resistance:.2f} (阻力位)")
                        return resistance
                    
                    resistance_levels = support_resistance_data.get('resistance_levels', [])
                    valid_resistances = [r for r in resistance_levels if r > current_price]
                    if valid_resistances:
                        boundary = min(valid_resistances)
                        logger.debug(f"  Short Call 風險邊界: ${boundary:.2f} (最近阻力位)")
                        return boundary
                
                # 默認值: 當前股價 +10%
                boundary = current_price * 1.10
                logger.debug(f"  Short Call 風險邊界: ${boundary:.2f} (默認 +10%)")
                return boundary
                
            elif strategy_type == 'short_put':
                # Short Put: 使用支持位作為風險邊界（不希望股價跌破）
                if support_resistance_data:
                    support = support_resistance_data.get('support_level')
                    if support and support < current_price:
                        logger.debug(f"  Short Put 風險邊界: ${support:.2f} (支持位)")
                        return support
                    
                    support_levels = support_resistance_data.get('support_levels', [])
                    valid_supports = [s for s in support_levels if s < current_price]
                    if valid_supports:
                        boundary = max(valid_supports)
                        logger.debug(f"  Short Put 風險邊界: ${boundary:.2f} (最近支持位)")
                        return boundary
                
                # 默認值: 當前股價 -10%
                boundary = current_price * 0.90
                logger.debug(f"  Short Put 風險邊界: ${boundary:.2f} (默認 -10%)")
                return boundary
            
            else:
                # 非 Short 策略，返回當前股價
                return current_price
                
        except Exception as e:
            logger.warning(f"確定風險邊界失敗: {e}，使用默認值")
            if strategy_type == 'short_call':
                return current_price * 1.10
            elif strategy_type == 'short_put':
                return current_price * 0.90
            return current_price
    
    # ===== Task 3.1: Long 策略多場景收益分析 =====
    
    def _calculate_multi_scenario_profit(
        self,
        analysis: StrikeAnalysis,
        current_price: float,
        target_price: float,
        strategy_type: str
    ) -> Dict:
        """
        計算 Long 策略的多場景收益
        
        參數:
            analysis: 行使價分析對象
            current_price: 當前股價
            target_price: 目標價格
            strategy_type: 策略類型 ('long_call' 或 'long_put')
        
        返回:
            Dict: {
                'scenarios': {
                    'conservative': {...},
                    'neutral': {...},
                    'optimistic': {...},
                    'extreme': {...}
                },
                'expected_profit': float,
                'expected_profit_pct': float,
                'best_case_profit_pct': float,
                'worst_case_profit_pct': float
            }
        
        Requirements: 1.1, 1.2, 1.3, 1.4
        """
        try:
            strike = analysis.strike
            premium = analysis.last_price if analysis.last_price > 0 else (analysis.bid + analysis.ask) / 2
            
            if premium <= 0:
                logger.warning(f"  期權金無效 ({premium})，無法計算多場景收益")
                return None
            
            # 定義四個場景的概率 (Property 1: 總和為 1.0)
            scenarios_config = {
                'conservative': {'probability': 0.30, 'label': '保守'},
                'neutral': {'probability': 0.40, 'label': '中性'},
                'optimistic': {'probability': 0.25, 'label': '樂觀'},
                'extreme': {'probability': 0.05, 'label': '極端'}
            }
            
            # 計算每個場景的目標股價
            if strategy_type == 'long_call':
                # Long Call: 期望股價上漲
                price_move = target_price - current_price
                scenario_prices = {
                    'conservative': current_price + price_move * 0.3,   # 達到 30% 目標
                    'neutral': current_price + price_move * 0.6,       # 達到 60% 目標
                    'optimistic': target_price,                         # 達到 100% 目標
                    'extreme': current_price + price_move * 1.5        # 超過目標 50%
                }
            else:  # long_put
                # Long Put: 期望股價下跌
                price_move = current_price - target_price
                scenario_prices = {
                    'conservative': current_price - price_move * 0.3,   # 達到 30% 目標
                    'neutral': current_price - price_move * 0.6,       # 達到 60% 目標
                    'optimistic': target_price,                         # 達到 100% 目標
                    'extreme': current_price - price_move * 1.5        # 超過目標 50%
                }
            
            scenarios = {}
            total_expected_profit = 0.0
            profits = []
            
            for scenario_name, config in scenarios_config.items():
                scenario_price = scenario_prices[scenario_name]
                probability = config['probability']
                label = config['label']
                
                # 計算內在價值 (Property 2)
                if strategy_type == 'long_call':
                    intrinsic_value = max(0, scenario_price - strike)
                else:  # long_put
                    intrinsic_value = max(0, strike - scenario_price)
                
                # 計算利潤
                profit = intrinsic_value - premium
                profit_pct = (profit / premium) * 100 if premium > 0 else 0
                
                scenarios[scenario_name] = {
                    'stock_price': round(scenario_price, 2),
                    'intrinsic_value': round(intrinsic_value, 2),
                    'profit': round(profit, 2),
                    'profit_pct': round(profit_pct, 2),
                    'probability': probability,
                    'label': f"{label}（{probability*100:.0f}%概率）"
                }
                
                # 累加期望收益 (Property 3)
                total_expected_profit += profit * probability
                profits.append(profit_pct)
            
            # 計算期望收益百分比
            expected_profit_pct = (total_expected_profit / premium) * 100 if premium > 0 else 0
            
            result = {
                'scenarios': scenarios,
                'expected_profit': round(total_expected_profit, 2),
                'expected_profit_pct': round(expected_profit_pct, 2),
                'best_case_profit_pct': round(max(profits), 2),
                'worst_case_profit_pct': round(min(profits), 2),
                'premium': round(premium, 2),
                'strike': strike,
                'current_price': current_price,
                'target_price': target_price
            }
            
            logger.debug(f"  多場景收益分析完成: 期望收益 {expected_profit_pct:.1f}%")
            return result
            
        except Exception as e:
            logger.error(f"多場景收益分析失敗: {e}")
            return None
    
    # ===== Task 4.1: Long 策略最佳退出時機計算 =====
    
    def _calculate_optimal_exit_timing(
        self,
        analysis: StrikeAnalysis,
        current_price: float,
        target_price: float,
        days_to_expiration: int,
        iv: float
    ) -> Dict:
        """
        計算 Long 策略的最佳退出時機
        
        參數:
            analysis: 行使價分析對象
            current_price: 當前股價
            target_price: 目標價格
            days_to_expiration: 到期天數
            iv: 隱含波動率（小數形式）
        
        返回:
            Dict: {
                'exit_scenarios': {...},
                'recommended_exit_day': int,
                'recommended_exit_profit': float,
                'recommended_exit_profit_pct': float,
                'annualized_return_pct': float
            }
        
        Requirements: 2.1, 2.2, 2.3, 2.4
        """
        try:
            strike = analysis.strike
            option_type = analysis.option_type
            premium = analysis.last_price if analysis.last_price > 0 else (analysis.bid + analysis.ask) / 2
            
            if premium <= 0:
                logger.warning(f"  期權金無效 ({premium})，無法計算最佳退出時機")
                return None
            
            # 定義退出時機場景
            exit_days = [5, 10, 15, 20]
            if days_to_expiration > 20:
                exit_days.append(days_to_expiration)
            
            exit_scenarios = {}
            best_annualized_return = float('-inf')
            recommended_exit = None
            
            # 獲取 Black-Scholes 計算器
            bs_calc = self._get_bs_calculator()
            risk_free_rate = 0.045
            
            for days_held in exit_days:
                if days_held > days_to_expiration:
                    continue
                
                remaining_days = days_to_expiration - days_held
                time_to_expiry = remaining_days / 365.0
                
                try:
                    if time_to_expiry > 0:
                        # 使用 Black-Scholes 計算期權價值
                        bs_result = bs_calc.calculate_option_price(
                            stock_price=target_price,
                            strike_price=strike,
                            time_to_expiration=time_to_expiry,
                            risk_free_rate=risk_free_rate,
                            volatility=iv,
                            option_type=option_type
                        )
                        option_value = bs_result.option_price
                    else:
                        # 到期日：使用內在價值
                        if option_type == 'call':
                            option_value = max(0, target_price - strike)
                        else:
                            option_value = max(0, strike - target_price)
                    
                except Exception as e:
                    logger.debug(f"  Black-Scholes 計算失敗: {e}，使用內在值")
                    if option_type == 'call':
                        option_value = max(0, target_price - strike)
                    else:
                        option_value = max(0, strike - target_price)
                
                # 計算利潤和年化收益率
                profit = option_value - premium
                profit_pct = (profit / premium) * 100 if premium > 0 else 0
                
                # 年化收益率 (Property 4)
                if days_held > 0:
                    annualized_return = (profit / premium) * (365 / days_held) * 100
                else:
                    annualized_return = 0
                
                scenario_key = f'day_{days_held}'
                exit_scenarios[scenario_key] = {
                    'days_held': days_held,
                    'remaining_days': remaining_days,
                    'option_value': round(option_value, 2),
                    'profit': round(profit, 2),
                    'profit_pct': round(profit_pct, 2),
                    'annualized_return_pct': round(annualized_return, 2)
                }
                
                # 找到最高年化收益率 (Property 5)
                if annualized_return > best_annualized_return:
                    best_annualized_return = annualized_return
                    recommended_exit = {
                        'day': days_held,
                        'profit': profit,
                        'profit_pct': profit_pct,
                        'annualized_return': annualized_return
                    }
            
            if recommended_exit is None:
                return None
            
            result = {
                'exit_scenarios': exit_scenarios,
                'recommended_exit_day': recommended_exit['day'],
                'recommended_exit_profit': round(recommended_exit['profit'], 2),
                'recommended_exit_profit_pct': round(recommended_exit['profit_pct'], 2),
                'annualized_return_pct': round(recommended_exit['annualized_return'], 2),
                'premium': round(premium, 2),
                'target_price': target_price
            }
            
            logger.debug(f"  最佳退出時機: 第 {recommended_exit['day']} 天，年化收益 {recommended_exit['annualized_return']:.1f}%")
            return result
            
        except Exception as e:
            logger.error(f"最佳退出時機計算失敗: {e}")
            return None
    
    # ===== Task 5.1: Long 策略評分計算 =====
    
    def _calculate_max_profit_score_long(self, analysis: StrikeAnalysis) -> float:
        """
        計算 Long 策略的利益最大化評分 (0-100)
        
        評分維度:
        - 期望收益評分 (50%): 50%收益→25分，100%→40分，200%→50分
        - 年化收益評分 (30%): 100%年化→20分，200%→30分
        - 風險控制評分 (20%): 不虧→20分，虧50%→10分，虧100%→0分
        
        Requirements: 3.1, 3.2, 3.3, 3.4
        Property 6: Long 策略評分權重正確性
        Property 15: 評分範圍有效性 (0-100)
        """
        try:
            # 檢查必要數據
            if analysis.multi_scenario_profit is None:
                return 0.0
            
            multi_scenario = analysis.multi_scenario_profit
            optimal_exit = analysis.optimal_exit_timing
            
            # 1. 期望收益評分 (50%)
            expected_profit_pct = multi_scenario.get('expected_profit_pct', 0)
            
            if expected_profit_pct >= 200:
                expected_score = 50.0
            elif expected_profit_pct >= 100:
                # 100% -> 40分, 200% -> 50分，線性插值
                expected_score = 40.0 + (expected_profit_pct - 100) / 100 * 10
            elif expected_profit_pct >= 50:
                # 50% -> 25分, 100% -> 40分，線性插值
                expected_score = 25.0 + (expected_profit_pct - 50) / 50 * 15
            elif expected_profit_pct >= 0:
                # 0% -> 10分, 50% -> 25分，線性插值
                expected_score = 10.0 + expected_profit_pct / 50 * 15
            else:
                # 負收益
                expected_score = max(0, 10.0 + expected_profit_pct / 50 * 10)
            
            # 2. 年化收益評分 (30%)
            annualized_return = 0
            if optimal_exit:
                annualized_return = optimal_exit.get('annualized_return_pct', 0)
            
            if annualized_return >= 200:
                annualized_score = 30.0
            elif annualized_return >= 100:
                # 100% -> 20分, 200% -> 30分，線性插值
                annualized_score = 20.0 + (annualized_return - 100) / 100 * 10
            elif annualized_return >= 0:
                # 0% -> 5分, 100% -> 20分，線性插值
                annualized_score = 5.0 + annualized_return / 100 * 15
            else:
                annualized_score = max(0, 5.0 + annualized_return / 100 * 5)
            
            # 3. 風險控制評分 (20%)
            worst_case_pct = multi_scenario.get('worst_case_profit_pct', -100)
            
            if worst_case_pct >= 0:
                # 不虧損 -> 20分
                risk_score = 20.0
            elif worst_case_pct >= -50:
                # 虧50% -> 10分，線性插值
                risk_score = 10.0 + (worst_case_pct + 50) / 50 * 10
            elif worst_case_pct >= -100:
                # 虧100% -> 0分，線性插值
                risk_score = (worst_case_pct + 100) / 50 * 10
            else:
                risk_score = 0.0
            
            # 計算總分 (Property 6)
            total_score = expected_score * 0.5 + annualized_score * 0.3 + risk_score * 0.2
            
            # 確保在 0-100 範圍內 (Property 15)
            total_score = max(0.0, min(100.0, total_score))
            
            logger.debug(f"  Long 評分: 期望{expected_score:.1f}×0.5 + 年化{annualized_score:.1f}×0.3 + 風險{risk_score:.1f}×0.2 = {total_score:.1f}")
            return total_score
            
        except Exception as e:
            logger.error(f"Long 策略評分計算失敗: {e}")
            return 0.0
    
    # ===== Task 7.1: Short 策略期權金收入分析 =====
    
    def _calculate_premium_safety_analysis(
        self,
        analysis: StrikeAnalysis,
        current_price: float,
        risk_boundary: float,
        days_to_expiration: int,
        strategy_type: str
    ) -> Dict:
        """
        計算 Short 策略的期權金收入和安全性分析
        
        參數:
            analysis: 行使價分析對象
            current_price: 當前股價
            risk_boundary: 風險邊界價格
            days_to_expiration: 到期天數
            strategy_type: 策略類型 ('short_call' 或 'short_put')
        
        返回:
            Dict: {
                'premium_amount': float,
                'premium_yield_pct': float,
                'annualized_yield_pct': float,
                'safety_distance_pct': float,
                'assignment_probability': float,
                'safe_probability': float,
                'premium_risk_ratio': float,
                'recommendation': str
            }
        
        Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
        """
        try:
            strike = analysis.strike
            premium = analysis.last_price if analysis.last_price > 0 else (analysis.bid + analysis.ask) / 2
            delta = abs(analysis.delta)
            
            if premium <= 0:
                logger.warning(f"  期權金無效 ({premium})，無法計算期權金分析")
                return None
            
            # 期權金收入（美元，假設 1 張合約 = 100 股）
            premium_amount = premium * 100
            
            # 收益率（佔股價比例）
            premium_yield_pct = (premium / current_price) * 100
            
            # 年化收益率
            if days_to_expiration > 0:
                annualized_yield_pct = premium_yield_pct * (365 / days_to_expiration)
            else:
                annualized_yield_pct = 0
            
            # 安全距離 (Property 8)
            if strategy_type == 'short_put':
                # Short Put: 安全距離 = (當前股價 - 行使價) / 當前股價 × 100
                safety_distance_pct = ((current_price - strike) / current_price) * 100
            else:  # short_call
                # Short Call: 安全距離 = (行使價 - 當前股價) / 當前股價 × 100
                safety_distance_pct = ((strike - current_price) / current_price) * 100
            
            # 被行使概率（基於 Delta）
            assignment_probability = delta
            
            # 安全概率 (Property 7)
            safe_probability = 1.0 - delta
            
            # 期權金/風險比
            if strategy_type == 'short_put':
                max_loss = strike * 100  # 最大損失是股票跌到 0
            else:  # short_call
                max_loss = current_price * 2 * 100  # 估計最大損失
            
            premium_risk_ratio = premium_amount / max_loss if max_loss > 0 else 0
            
            # 生成推薦
            if safe_probability >= 0.80 and annualized_yield_pct >= 30:
                recommendation = f"✅ 優秀：安全概率 {safe_probability*100:.1f}%，年化收益 {annualized_yield_pct:.1f}%"
            elif safe_probability >= 0.70 and annualized_yield_pct >= 20:
                recommendation = f"👍 良好：安全概率 {safe_probability*100:.1f}%，年化收益 {annualized_yield_pct:.1f}%"
            elif safe_probability >= 0.60:
                recommendation = f"⚠️ 一般：安全概率 {safe_probability*100:.1f}%，需謹慎"
            else:
                recommendation = f"❌ 風險高：安全概率僅 {safe_probability*100:.1f}%"
            
            result = {
                'premium_amount': round(premium_amount, 2),
                'premium_yield_pct': round(premium_yield_pct, 4),
                'annualized_yield_pct': round(annualized_yield_pct, 2),
                'safety_distance_pct': round(safety_distance_pct, 2),
                'assignment_probability': round(assignment_probability, 4),
                'safe_probability': round(safe_probability, 4),
                'premium_risk_ratio': round(premium_risk_ratio, 4),
                'recommendation': recommendation,
                'strike': strike,
                'current_price': current_price,
                'risk_boundary': risk_boundary
            }
            
            logger.debug(f"  期權金分析完成: 安全概率 {safe_probability*100:.1f}%，年化 {annualized_yield_pct:.1f}%")
            return result
            
        except Exception as e:
            logger.error(f"期權金安全性分析失敗: {e}")
            return None
    
    # ===== Task 8.1: Short 策略持有到期優勢計算 =====
    
    def _calculate_hold_to_expiry_advantage(
        self,
        analysis: StrikeAnalysis,
        days_to_expiration: int
    ) -> Dict:
        """
        計算 Short 策略持有到期的優勢
        
        參數:
            analysis: 行使價分析對象
            days_to_expiration: 到期天數
        
        返回:
            Dict: {
                'total_theta_gain': float,
                'daily_theta_gain': float,
                'theta_percentage': float,
                'hold_to_expiry_profit': float,
                'early_close_profit_estimate': float,
                'hold_advantage': float,
                'recommendation': str
            }
        
        Requirements: 5.1, 5.2, 5.3, 5.4
        """
        try:
            theta = analysis.theta
            premium = analysis.last_price if analysis.last_price > 0 else (analysis.bid + analysis.ask) / 2
            
            if premium <= 0:
                logger.warning(f"  期權金無效 ({premium})，無法計算持有優勢")
                return None
            
            # 每日 Theta 收益（Theta 是負數，對 Short 有利）
            daily_theta_gain = abs(theta)
            
            # 總 Theta 收益 (Property 9)
            total_theta_gain = daily_theta_gain * days_to_expiration
            
            # Theta 佔比
            theta_percentage = (total_theta_gain / premium) * 100 if premium > 0 else 0
            
            # 持有到期利潤（假設期權到期作廢）
            hold_to_expiry_profit = premium * 100  # 1 張合約
            
            # 提前平倉估計利潤（假設在 50% 時間點平倉，收回 30% 期權金）
            early_close_profit_estimate = premium * 100 * 0.70
            
            # 持有優勢
            hold_advantage = hold_to_expiry_profit - early_close_profit_estimate
            
            # 生成推薦
            if theta_percentage >= 80:
                recommendation = f"✅ 強烈建議持有到期：Theta 收益佔 {theta_percentage:.1f}%"
            elif theta_percentage >= 50:
                recommendation = f"👍 建議持有到期：Theta 收益佔 {theta_percentage:.1f}%"
            elif theta_percentage >= 30:
                recommendation = f"⚠️ 可考慮持有：Theta 收益佔 {theta_percentage:.1f}%"
            else:
                recommendation = f"💡 可提前平倉：Theta 收益僅佔 {theta_percentage:.1f}%"
            
            result = {
                'total_theta_gain': round(total_theta_gain, 4),
                'daily_theta_gain': round(daily_theta_gain, 4),
                'theta_percentage': round(theta_percentage, 2),
                'hold_to_expiry_profit': round(hold_to_expiry_profit, 2),
                'early_close_profit_estimate': round(early_close_profit_estimate, 2),
                'hold_advantage': round(hold_advantage, 2),
                'recommendation': recommendation,
                'days_to_expiration': days_to_expiration
            }
            
            logger.debug(f"  持有優勢分析完成: Theta 佔比 {theta_percentage:.1f}%")
            return result
            
        except Exception as e:
            logger.error(f"持有到期優勢計算失敗: {e}")
            return None
    
    # ===== Task 9.1: Short 策略評分計算 =====
    
    def _calculate_max_profit_score_short(self, analysis: StrikeAnalysis) -> float:
        """
        計算 Short 策略的期權金安全性評分 (0-100)
        
        評分維度:
        - 收益率評分 (40%): 50%年化→20分，100%→32分，200%→40分
        - 安全性評分 (40%): 90%安全概率→40分，80%→32分，70%→20分
        - Theta 優勢評分 (20%): Theta佔80%→20分，佔50%→12分
        
        Requirements: 6.1, 6.2, 6.3, 6.4
        Property 10: Short 策略評分權重正確性
        Property 15: 評分範圍有效性 (0-100)
        """
        try:
            # 檢查必要數據
            if analysis.premium_analysis is None:
                return 0.0
            
            premium_analysis = analysis.premium_analysis
            hold_advantage = analysis.hold_to_expiry_advantage
            
            # 1. 收益率評分 (40%)
            annualized_yield = premium_analysis.get('annualized_yield_pct', 0)
            
            if annualized_yield >= 200:
                yield_score = 40.0
            elif annualized_yield >= 100:
                # 100% -> 32分, 200% -> 40分，線性插值
                yield_score = 32.0 + (annualized_yield - 100) / 100 * 8
            elif annualized_yield >= 50:
                # 50% -> 20分, 100% -> 32分，線性插值
                yield_score = 20.0 + (annualized_yield - 50) / 50 * 12
            elif annualized_yield >= 0:
                # 0% -> 5分, 50% -> 20分，線性插值
                yield_score = 5.0 + annualized_yield / 50 * 15
            else:
                yield_score = 0.0
            
            # 2. 安全性評分 (40%)
            safe_probability = premium_analysis.get('safe_probability', 0)
            
            if safe_probability >= 0.90:
                safety_score = 40.0
            elif safe_probability >= 0.80:
                # 80% -> 32分, 90% -> 40分，線性插值
                safety_score = 32.0 + (safe_probability - 0.80) / 0.10 * 8
            elif safe_probability >= 0.70:
                # 70% -> 20分, 80% -> 32分，線性插值
                safety_score = 20.0 + (safe_probability - 0.70) / 0.10 * 12
            elif safe_probability >= 0.50:
                # 50% -> 5分, 70% -> 20分，線性插值
                safety_score = 5.0 + (safe_probability - 0.50) / 0.20 * 15
            else:
                safety_score = max(0, safe_probability / 0.50 * 5)
            
            # 3. Theta 優勢評分 (20%)
            theta_percentage = 0
            if hold_advantage:
                theta_percentage = hold_advantage.get('theta_percentage', 0)
            
            if theta_percentage >= 80:
                theta_score = 20.0
            elif theta_percentage >= 50:
                # 50% -> 12分, 80% -> 20分，線性插值
                theta_score = 12.0 + (theta_percentage - 50) / 30 * 8
            elif theta_percentage >= 20:
                # 20% -> 5分, 50% -> 12分，線性插值
                theta_score = 5.0 + (theta_percentage - 20) / 30 * 7
            else:
                theta_score = theta_percentage / 20 * 5
            
            # 計算總分 (Property 10)
            total_score = yield_score * 0.4 + safety_score * 0.4 + theta_score * 0.2
            
            # 確保在 0-100 範圍內 (Property 15)
            total_score = max(0.0, min(100.0, total_score))
            
            logger.debug(f"  Short 評分: 收益{yield_score:.1f}×0.4 + 安全{safety_score:.1f}×0.4 + Theta{theta_score:.1f}×0.2 = {total_score:.1f}")
            return total_score
            
        except Exception as e:
            logger.error(f"Short 策略評分計算失敗: {e}")
            return 0.0
    
    def _get_iv_calculator(self):
        """延遲初始化 IV 計算器"""
        if self._iv_calculator is None:
            from calculation_layer.module17_implied_volatility import ImpliedVolatilityCalculator
            self._iv_calculator = ImpliedVolatilityCalculator()
        return self._iv_calculator
    
    def _normalize_iv(self, raw_iv: float) -> float:
        """
        標準化 IV 為小數形式
        
        規則:
        - 0.05 <= raw_iv <= 3.0: 視為小數形式
        - 5 <= raw_iv <= 300: 視為百分比形式，除以 100
        - 其他: 使用默認值 0.30
        
        返回:
            float: 標準化後的 IV，範圍 [0.01, 5.0]
        
        Requirements: 1.4, 1.5, 2.1, 2.2, 2.3, 2.5
        """
        original_iv = raw_iv
        
        # 處理無效值
        if raw_iv is None or raw_iv <= 0:
            logger.debug(f"  IV 無效 ({raw_iv})，使用默認值 {self.DEFAULT_IV}")
            return self.DEFAULT_IV
        
        # 檢測格式並轉換
        if 5.0 <= raw_iv <= 300.0:
            # 百分比形式 (5-300) -> 轉換為小數
            normalized_iv = raw_iv / 100.0
            logger.debug(f"  IV 格式轉換: {original_iv}% -> {normalized_iv:.4f} (百分比->小數)")
        elif 0.05 <= raw_iv <= 3.0:
            # 已經是小數形式
            normalized_iv = raw_iv
            logger.debug(f"  IV 已是小數形式: {normalized_iv:.4f}")
        elif raw_iv > 300.0:
            # 異常高的百分比值
            normalized_iv = raw_iv / 100.0
            logger.warning(f"  IV 異常高 ({raw_iv})，轉換為 {normalized_iv:.4f}")
        elif raw_iv < 0.05 and raw_iv > 0:
            # 非常低的小數值
            normalized_iv = raw_iv
            logger.debug(f"  IV 非常低: {normalized_iv:.4f}")
        else:
            # 其他情況使用默認值
            logger.warning(f"  IV 格式無法識別 ({raw_iv})，使用默認值 {self.DEFAULT_IV}")
            return self.DEFAULT_IV
        
        # 限制在合理範圍內 [0.01, 5.0]
        clamped_iv = max(0.01, min(5.0, normalized_iv))
        
        if clamped_iv != normalized_iv:
            logger.debug(f"  IV 被限制: {normalized_iv:.4f} -> {clamped_iv:.4f}")
        
        return clamped_iv
    
    def _get_corrected_iv(
        self,
        option: Dict,
        current_price: float,
        strike: float,
        option_type: str,
        time_to_expiration: float,
        risk_free_rate: float = 0.045
    ) -> tuple:
        """
        獲取校正後的 IV
        
        策略優先級:
        1. Module 17 從市場價格反推（最準確）
        2. Yahoo Finance IV（需驗證）
        3. 默認值 0.30
        
        參數:
            option: 期權數據字典
            current_price: 當前股價
            strike: 行使價
            option_type: 期權類型 ('call' 或 'put')
            time_to_expiration: 到期時間（年）
            risk_free_rate: 無風險利率
        
        返回:
            tuple: (iv: float, source: str)
                - iv: 小數形式的 IV（如 0.35 表示 35%）
                - source: IV 來源 ('module17', 'yahoo', 'default')
        
        Requirements: 1.1, 1.2, 1.3, 1.6
        """
        # 獲取市場價格
        market_price = option.get('lastPrice', 0) or 0
        if market_price <= 0:
            bid = option.get('bid', 0) or 0
            ask = option.get('ask', 0) or 0
            market_price = (bid + ask) / 2 if (bid + ask) > 0 else 0
        
        # 策略 1: 使用 Module 17 從市場價格反推 IV
        if market_price > 0 and time_to_expiration > 0:
            try:
                iv_calculator = self._get_iv_calculator()
                iv_result = iv_calculator.calculate_implied_volatility(
                    market_price=market_price,
                    stock_price=current_price,
                    strike_price=strike,
                    risk_free_rate=risk_free_rate,
                    time_to_expiration=time_to_expiration,
                    option_type=option_type
                )
                
                if iv_result.converged:
                    # Module 17 返回的 IV 已經是小數形式
                    corrected_iv = self._normalize_iv(iv_result.implied_volatility)
                    logger.debug(f"  使用 Module 17 計算 IV: {corrected_iv:.4f} (收斂)")
                    return (corrected_iv, 'module17')
                else:
                    logger.debug(f"  Module 17 IV 計算未收斂，嘗試 Yahoo Finance IV")
            except Exception as e:
                logger.debug(f"  Module 17 IV 計算失敗: {e}，嘗試 Yahoo Finance IV")
        
        # 策略 2: 使用 Yahoo Finance IV（需驗證和標準化）
        raw_yahoo_iv = option.get('impliedVolatility', 0) or 0
        if raw_yahoo_iv > 0:
            corrected_iv = self._normalize_iv(raw_yahoo_iv)
            logger.debug(f"  使用 Yahoo Finance IV: {raw_yahoo_iv} -> {corrected_iv:.4f}")
            return (corrected_iv, 'yahoo')
        
        # 策略 3: 使用默認值
        logger.warning(f"  IV 數據無效或缺失，使用默認值 {self.DEFAULT_IV}")
        return (self.DEFAULT_IV, 'default')
    
    def analyze_strikes(
        self,
        current_price: float,
        option_chain: Dict[str, Any],
        strategy_type: str,
        days_to_expiration: int = 30,
        iv_rank: float = 50.0,
        target_price: Optional[float] = None,
        support_resistance_data: Optional[Dict] = None,  # Task 11.1: 新增支持阻力位數據
        enable_max_profit_analysis: bool = True  # Task 11.1: 控制新功能啟用
    ) -> Dict[str, Any]:
        """
        分析多個行使價並計算綜合評分
        
        參數:
            current_price: 當前股價
            option_chain: 期權鏈數據 {'calls': [...], 'puts': [...]}
            strategy_type: 策略類型 ('long_call', 'long_put', 'short_call', 'short_put')
            days_to_expiration: 到期天數
            iv_rank: IV Rank (0-100)
            target_price: 目標價格（用於計算風險回報）
            support_resistance_data: 支持阻力位數據（用於確定目標價/風險邊界）
            enable_max_profit_analysis: 是否啟用利益最大化分析（Long/Short 策略增強）
        
        返回:
            Dict: {
                'analyzed_strikes': List[StrikeAnalysis],
                'top_recommendations': List[Dict],
                'best_strike': float,
                'analysis_summary': str
            }
        """
        try:
            logger.info(f"開始最佳行使價分析...")
            logger.info(f"  當前股價: ${current_price:.2f}")
            logger.info(f"  策略類型: {strategy_type}")
            logger.info(f"  到期天數: {days_to_expiration}")
            
            # 確定分析的期權類型
            if strategy_type in ['long_call', 'short_call']:
                option_type = 'call'
                options_data = option_chain.get('calls', [])
            else:
                option_type = 'put'
                options_data = option_chain.get('puts', [])
            
            if not options_data:
                logger.warning("! 期權鏈數據為空")
                return self._create_empty_result("期權鏈數據為空")
            
            # 新邏輯：從 ATM 行使價向上和向下各取最多 20 個行使價
            # 1. 先按行使價排序所有期權
            sorted_options = sorted(options_data, key=lambda x: x.get('strike', 0))
            
            # 2. 找到最接近 ATM 的行使價索引
            atm_index = 0
            min_distance = float('inf')
            for i, opt in enumerate(sorted_options):
                strike = opt.get('strike', 0)
                distance = abs(strike - current_price)
                if distance < min_distance:
                    min_distance = distance
                    atm_index = i
            
            # 3. 從 ATM 向下取最多 20 個（價內 for call，價外 for put）
            lower_options = sorted_options[max(0, atm_index - self.MAX_STRIKES_EACH_SIDE):atm_index]
            
            # 4. 從 ATM 向上取最多 20 個（價外 for call，價內 for put）
            upper_options = sorted_options[atm_index:min(len(sorted_options), atm_index + self.MAX_STRIKES_EACH_SIDE + 1)]
            
            # 5. 合併選中的行使價
            selected_options = lower_options + upper_options
            
            # 計算實際選取的範圍
            if selected_options:
                min_strike = min(opt.get('strike', 0) for opt in selected_options)
                max_strike = max(opt.get('strike', 0) for opt in selected_options)
            else:
                min_strike = current_price * 0.8
                max_strike = current_price * 1.2
            
            logger.info(f"  行使價選取: ATM 上下各最多 {self.MAX_STRIKES_EACH_SIDE} 個")
            logger.info(f"  實際選取範圍: ${min_strike:.2f} - ${max_strike:.2f}")
            logger.info(f"  選取數量: {len(selected_options)} 個")
            
            # 第一輪：收集所有符合條件的行使價並計算 ATM IV
            analyzed_strikes = []
            atm_iv = None
            atm_strike = None
            min_atm_distance = float('inf')
            
            for option in selected_options:
                strike = option.get('strike', 0)
                
                # 過濾流動性不足的行使價（金曹三不買原則）- 改為 OR 邏輯
                volume = option.get('volume', 0) or 0
                oi = option.get('openInterest', 0) or 0
                
                # 修復：使用 OR 邏輯，只要 Volume 或 OI 其中一個達標即可
                if volume < self.MIN_VOLUME and oi < self.MIN_OPEN_INTEREST:
                    continue
                
                # 創建分析對象
                analysis = self._analyze_single_strike(
                    option, option_type, current_price, strategy_type,
                    days_to_expiration, iv_rank, target_price
                )
                
                if analysis:
                    analyzed_strikes.append(analysis)
                    
                    # 找到最接近 ATM 的行使價
                    distance = abs(strike - current_price)
                    if distance < min_atm_distance:
                        min_atm_distance = distance
                        atm_iv = analysis.iv
                        atm_strike = strike
            
            if not analyzed_strikes:
                logger.warning("! 沒有符合條件的行使價")
                return self._create_empty_result("沒有符合流動性條件的行使價")
            
            # 第二輪：計算 IV Skew（在評分之前）
            if atm_iv:
                logger.debug(f"  ATM IV: {atm_iv:.2f}% (行使價: ${atm_strike:.2f})")
                for analysis in analyzed_strikes:
                    analysis.iv_skew = analysis.iv - atm_iv
            
            # 第三輪：重新計算 IV 評分（現在 IV Skew 已經有值了）
            for analysis in analyzed_strikes:
                analysis.iv_score = self._calculate_iv_score(analysis, strategy_type)
            
            # ===== Task 11.2: Long/Short 策略增強分析 =====
            if enable_max_profit_analysis:
                is_long_strategy = strategy_type in ['long_call', 'long_put']
                is_short_strategy = strategy_type in ['short_call', 'short_put']
                
                # 確定目標價或風險邊界
                if is_long_strategy:
                    # Long 策略：確定目標價
                    if target_price is None:
                        target_price = self._determine_target_price(
                            current_price, strategy_type, support_resistance_data
                        )
                    logger.info(f"  Long 策略目標價: ${target_price:.2f}")
                elif is_short_strategy:
                    # Short 策略：確定風險邊界
                    risk_boundary = self._determine_risk_boundary(
                        current_price, strategy_type, support_resistance_data
                    )
                    logger.info(f"  Short 策略風險邊界: ${risk_boundary:.2f}")
                
                # 獲取 ATM IV 用於 Black-Scholes 計算
                iv_for_calc = (atm_iv / 100.0) if atm_iv else self.DEFAULT_IV
                
                # 為每個行使價計算增強分析
                for analysis in analyzed_strikes:
                    try:
                        if is_long_strategy:
                            # Task 11.2: Long 策略分析
                            # 計算多場景收益
                            analysis.multi_scenario_profit = self._calculate_multi_scenario_profit(
                                analysis, current_price, target_price, strategy_type
                            )
                            
                            # 計算最佳退出時機
                            analysis.optimal_exit_timing = self._calculate_optimal_exit_timing(
                                analysis, current_price, target_price,
                                days_to_expiration, iv_for_calc
                            )
                            
                            # 計算 Long 策略評分
                            analysis.max_profit_score = self._calculate_max_profit_score_long(analysis)
                            
                        elif is_short_strategy:
                            # Task 11.2: Short 策略分析
                            # 計算期權金安全性分析
                            analysis.premium_analysis = self._calculate_premium_safety_analysis(
                                analysis, current_price, risk_boundary,
                                days_to_expiration, strategy_type
                            )
                            
                            # 計算持有到期優勢
                            analysis.hold_to_expiry_advantage = self._calculate_hold_to_expiry_advantage(
                                analysis, days_to_expiration
                            )
                            
                            # 計算 Short 策略評分
                            analysis.max_profit_score = self._calculate_max_profit_score_short(analysis)
                            
                    except Exception as e:
                        # Task 12.2: 錯誤處理 - 回退到現有邏輯
                        logger.warning(f"  行使價 ${analysis.strike:.2f} 增強分析失敗: {e}")
                        analysis.max_profit_score = 0.0
            
            # ===== Task 11.3: 計算綜合評分（整合新評分） =====
            for analysis in analyzed_strikes:
                # 計算原始綜合評分
                original_score = self.calculate_composite_score(analysis, strategy_type)
                
                if enable_max_profit_analysis and analysis.max_profit_score > 0:
                    # 整合新評分
                    if strategy_type in ['long_call', 'long_put']:
                        # Long 策略: 綜合評分 = 原始評分 × 0.6 + 利益最大化評分 × 0.4
                        # Property 11
                        analysis.composite_score = original_score * 0.6 + analysis.max_profit_score * 0.4
                    else:
                        # Short 策略: 綜合評分 = 原始評分 × 0.5 + 期權金安全性評分 × 0.5
                        # Property 12
                        analysis.composite_score = original_score * 0.5 + analysis.max_profit_score * 0.5
                else:
                    # 未啟用新功能或計算失敗，使用原始評分
                    analysis.composite_score = original_score
            
            # 排序並獲取推薦
            analyzed_strikes.sort(key=lambda x: x.composite_score, reverse=True)
            
            top_recommendations = [
                {
                    'rank': i + 1,
                    'strike': s.strike,
                    'composite_score': round(s.composite_score, 2),
                    'liquidity_score': round(s.liquidity_score, 2),
                    'greeks_score': round(s.greeks_score, 2),
                    'iv_score': round(s.iv_score, 2),
                    'risk_reward_score': round(s.risk_reward_score, 2),
                    'max_profit_score': round(s.max_profit_score, 2),  # Task 13.3: 新增評分
                    'delta': round(s.delta, 4),
                    'gamma': round(s.gamma, 4),
                    'theta': round(s.theta, 4),
                    'vega': round(s.vega, 4),
                    'volume': s.volume,
                    'open_interest': s.open_interest,
                    'iv': round(s.iv, 2),
                    'iv_skew': round(s.iv_skew, 2),
                    'bid_ask_spread_pct': round(s.bid_ask_spread_pct, 2),
                    'safety_probability': round(s.safety_probability, 4),  # Requirements 2.5
                    # Task 13.3: Long/Short 策略專用數據
                    'multi_scenario_profit': s.multi_scenario_profit,
                    'optimal_exit_timing': s.optimal_exit_timing,
                    'premium_analysis': s.premium_analysis,
                    'hold_to_expiry_advantage': s.hold_to_expiry_advantage,
                    'reason': self._generate_recommendation_reason(s, strategy_type)
                }
                for i, s in enumerate(analyzed_strikes[:3])
            ]
            
            best_strike = analyzed_strikes[0].strike if analyzed_strikes else 0
            
            # 執行 Put-Call Parity 驗證
            # Requirements 4.1, 4.2, 4.3, 4.4
            time_to_expiry = days_to_expiration / 365.0
            parity_validation = self._validate_parity_for_atm(
                option_chain=option_chain,
                current_price=current_price,
                time_to_expiration=time_to_expiry,
                risk_free_rate=0.045
            )
            
            # 如果 Parity 驗證成功，將結果添加到每個分析的行使價
            # Requirements 4.4: 在報告中顯示 Parity 驗證狀態和偏離百分比
            if parity_validation is not None:
                for analysis in analyzed_strikes:
                    analysis.parity_valid = parity_validation['valid']
                    analysis.parity_deviation_pct = parity_validation['deviation_pct']
            
            # 執行波動率微笑分析
            # Requirements 5.6: 在分析流程中整合波動率微笑分析
            volatility_smile_result = self._analyze_volatility_smile(
                option_chain=option_chain,
                current_price=current_price,
                time_to_expiration=time_to_expiry,
                risk_free_rate=0.045
            )
            
            result = {
                'analyzed_strikes': [s.to_dict() for s in analyzed_strikes],
                'top_recommendations': top_recommendations,
                'best_strike': best_strike,
                'total_analyzed': len(analyzed_strikes),
                'strategy_type': strategy_type,
                'current_price': current_price,
                'strike_range': {
                    'min': round(min_strike, 2),
                    'max': round(max_strike, 2),
                    'max_strikes_each_side': self.MAX_STRIKES_EACH_SIDE,
                    'total_selected': len(selected_options)
                },
                'atm_info': {
                    'strike': atm_strike,
                    'iv': atm_iv
                },
                'analysis_summary': self._generate_summary(analyzed_strikes[0], strategy_type) if analyzed_strikes else "無推薦",
                'calculation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'parity_validation': parity_validation,
                'volatility_smile': volatility_smile_result
            }
            
            logger.info(f"* 最佳行使價分析完成")
            logger.info(f"  分析了 {len(analyzed_strikes)} 個行使價")
            logger.info(f"  最佳行使價: ${best_strike:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"x 最佳行使價分析失敗: {e}")
            return self._create_empty_result(str(e))

    
    def _filter_short_put(self, strike: float, current_price: float, delta: float) -> tuple:
        """
        Short Put 安全過濾
        
        過濾條件:
        1. ITM Put（行使價 >= 當前股價）
        2. 高 Delta Put（|Delta| > 0.35）
        3. 距離過近的 Put（距離 < 3%）
        
        參數:
            strike: 行使價
            current_price: 當前股價
            delta: Delta 值（Put 的 Delta 是負數）
        
        返回:
            tuple: (是否通過過濾, 跳過原因)
        
        Requirements: 2.1, 2.2, 2.3, 2.4
        """
        try:
            # 過濾 ITM Put（行使價 >= 當前股價）
            # Requirements 2.1
            if strike >= current_price:
                reason = f"ITM Put: ${strike:.2f} >= ${current_price:.2f}"
                logger.debug(f"  跳過 {reason}")
                return (False, reason)
            
            # 過濾高 Delta Put（|Delta| > 0.35）
            # Requirements 2.2
            abs_delta = abs(delta)
            if abs_delta > 0.35:
                reason = f"高 Delta: |Δ|={abs_delta:.2f} > 0.35"
                logger.debug(f"  跳過 {reason}")
                return (False, reason)
            
            # 確保距離 >= 3%
            # Requirements 2.3
            distance_pct = (current_price - strike) / current_price
            if distance_pct < 0.03:
                reason = f"距離過近: {distance_pct*100:.1f}% < 3%"
                logger.debug(f"  跳過 {reason}")
                return (False, reason)
            
            return (True, "")
        except Exception as e:
            logger.error(f"Short Put 過濾失敗: {e}")
            return (False, f"過濾錯誤: {e}")
    
    def _analyze_single_strike(
        self,
        option: Dict,
        option_type: str,
        current_price: float,
        strategy_type: str,
        days_to_expiration: int,
        iv_rank: float,
        target_price: Optional[float]
    ) -> Optional[StrikeAnalysis]:
        """分析單個行使價"""
        try:
            strike = option.get('strike', 0)
            bid = option.get('bid', 0) or 0
            ask = option.get('ask', 0) or 0
            last_price = option.get('lastPrice', 0) or 0
            volume = option.get('volume', 0) or 0
            oi = option.get('openInterest', 0) or 0
            
            # Bid/Ask 價格過濾邏輯（盤後時間容錯）
            # 如果 bid/ask 都為 0 但有 lastPrice，使用 lastPrice 估算 bid/ask
            # 這在盤後時間很常見，因為 Yahoo Finance 不返回盤後的 bid/ask
            is_long_strategy = strategy_type in ['long_call', 'long_put']
            is_short_strategy = strategy_type in ['short_call', 'short_put']
            
            if bid == 0 and ask == 0:
                if last_price > 0:
                    # 盤後容錯：使用 lastPrice 估算 bid/ask
                    # 假設 spread 為 lastPrice 的 5%（保守估計）
                    estimated_spread = last_price * 0.05
                    bid = last_price - estimated_spread / 2
                    ask = last_price + estimated_spread / 2
                    logger.debug(f"  行使價 ${strike:.2f}: 使用 lastPrice ${last_price:.2f} 估算 bid/ask (盤後模式)")
                else:
                    logger.debug(f"  跳過行使價 ${strike:.2f}: Bid、Ask 和 lastPrice 都為 0")
                    return None
            
            if bid == 0 and is_short_strategy:
                if last_price > 0:
                    # 使用 lastPrice 作為 bid 的估計
                    bid = last_price * 0.95  # 保守估計
                    logger.debug(f"  行使價 ${strike:.2f}: Short 策略使用 lastPrice 估算 bid")
                else:
                    logger.debug(f"  跳過行使價 ${strike:.2f}: Short 策略需要 Bid 價格，但 Bid = 0")
                    return None
            
            if ask == 0 and is_long_strategy:
                if last_price > 0:
                    # 使用 lastPrice 作為 ask 的估計
                    ask = last_price * 1.05  # 保守估計
                    logger.debug(f"  行使價 ${strike:.2f}: Long 策略使用 lastPrice 估算 ask")
                else:
                    logger.debug(f"  跳過行使價 ${strike:.2f}: Long 策略需要 Ask 價格，但 Ask = 0")
                    return None
            
            # 計算時間（年）
            time_to_expiry = days_to_expiration / 365.0
            if time_to_expiry <= 0:
                time_to_expiry = 1 / 365.0  # 至少 1 天
            
            # 獲取無風險利率（默認 4.5%）
            risk_free_rate = 0.045
            
            # 使用新的 IV 處理邏輯獲取校正後的 IV
            corrected_iv, iv_source = self._get_corrected_iv(
                option=option,
                current_price=current_price,
                strike=strike,
                option_type=option_type,
                time_to_expiration=time_to_expiry,
                risk_free_rate=risk_free_rate
            )
            
            # IV 已經是小數形式，轉換為百分比用於顯示
            iv_display = corrected_iv * 100
            
            # 嘗試從期權數據獲取 Greeks，如果沒有則自行計算
            delta = option.get('delta')
            gamma = option.get('gamma')
            theta = option.get('theta')
            vega = option.get('vega')
            
            # 如果沒有 Greeks 數據，使用 Black-Scholes 計算
            if delta is None or delta == 0:
                try:
                    from calculation_layer.module16_greeks import GreeksCalculator
                    greeks_calc = GreeksCalculator()
                    
                    # 使用校正後的 IV（已經是小數形式）計算 Greeks
                    volatility = corrected_iv
                    
                    # 計算 Greeks（使用正確的方法名）
                    greeks_result = greeks_calc.calculate_all_greeks(
                        stock_price=current_price,
                        strike_price=strike,
                        time_to_expiration=time_to_expiry,
                        risk_free_rate=risk_free_rate,
                        volatility=volatility,
                        option_type='call' if option_type == 'call' else 'put'
                    )
                    
                    if greeks_result:
                        delta = abs(greeks_result.delta)
                        gamma = greeks_result.gamma
                        theta = greeks_result.theta
                        vega = greeks_result.vega
                        logger.debug(f"  計算 Greeks: Δ={delta:.4f}, Γ={gamma:.4f}, Θ={theta:.4f}, ν={vega:.4f}")
                    else:
                        delta = 0.5
                        gamma = 0
                        theta = 0
                        vega = 0
                except Exception as e:
                    logger.debug(f"  計算 Greeks 失敗: {e}，使用默認值")
                    delta = 0.5
                    gamma = 0
                    theta = 0
                    vega = 0
            else:
                delta = abs(delta)
                gamma = gamma or 0
                theta = theta or 0
                vega = vega or 0
            
            # Short Put 安全過濾
            # Requirements: 2.1, 2.2, 2.3, 2.4
            if strategy_type == 'short_put':
                passed, skip_reason = self._filter_short_put(strike, current_price, delta)
                if not passed:
                    logger.debug(f"  Short Put 過濾: 跳過行使價 ${strike:.2f} - {skip_reason}")
                    return None
            
            # 計算 Bid-Ask Spread 百分比
            mid_price = (bid + ask) / 2 if (bid + ask) > 0 else last_price
            bid_ask_spread_pct = ((ask - bid) / mid_price * 100) if mid_price > 0 else 0
            
            # 創建分析對象
            analysis = StrikeAnalysis(
                strike=strike,
                option_type=option_type,
                bid=bid,
                ask=ask,
                last_price=last_price,
                delta=delta,
                gamma=gamma,
                theta=theta,
                vega=vega,
                volume=volume,
                open_interest=oi,
                bid_ask_spread_pct=bid_ask_spread_pct,
                iv=iv_display,  # 使用百分比形式顯示
                iv_rank=iv_rank,
                iv_source=iv_source  # 記錄 IV 來源
            )
            
            # 計算各項評分
            analysis.liquidity_score = self._calculate_liquidity_score(analysis)
            analysis.greeks_score = self._calculate_greeks_score(analysis, strategy_type)
            analysis.iv_score = self._calculate_iv_score(analysis, strategy_type)
            # 使用增強的風險回報評分 v2（包含勝率和 Theta 調整）
            # Requirements: 3.1
            analysis.risk_reward_score = self._calculate_risk_reward_score_v2(
                analysis, current_price, strategy_type, target_price, 
                holding_days=days_to_expiration
            )
            
            # 計算安全概率 (1 - |Delta|)
            # Requirements: 2.5
            analysis.safety_probability = 1.0 - abs(analysis.delta)
            
            return analysis
            
        except Exception as e:
            logger.debug(f"  分析行使價 {option.get('strike', 'N/A')} 失敗: {e}")
            return None
    
    def _calculate_liquidity_score(self, analysis: StrikeAnalysis) -> float:
        """
        計算流動性評分 (0-100)
        
        基於金曹三不買原則，增加更細緻的分數區間:
        - Volume: 推薦 ≥ 100, 優秀 ≥ 500, 最低 ≥ 10
        - Open Interest: 推薦 ≥ 500, 優秀 ≥ 2000, 最低 ≥ 100
        - Bid-Ask Spread: 推薦 < 5%, 優秀 < 2%, 最高 < 10%
        """
        score = 0.0
        
        # Volume 評分 (35%) - 增加更細緻的區間
        EXCELLENT_VOLUME = 500
        if analysis.volume >= EXCELLENT_VOLUME:
            volume_score = 35.0
        elif analysis.volume >= self.RECOMMENDED_VOLUME:
            # 100-500: 線性插值 25-35
            volume_score = 25.0 + (analysis.volume - self.RECOMMENDED_VOLUME) / (EXCELLENT_VOLUME - self.RECOMMENDED_VOLUME) * 10.0
        elif analysis.volume >= self.MIN_VOLUME:
            # 10-100: 線性插值 10-25
            volume_score = 10.0 + (analysis.volume - self.MIN_VOLUME) / (self.RECOMMENDED_VOLUME - self.MIN_VOLUME) * 15.0
        else:
            volume_score = 0.0
        score += volume_score
        
        # Open Interest 評分 (35%) - 增加更細緻的區間
        EXCELLENT_OI = 2000
        if analysis.open_interest >= EXCELLENT_OI:
            oi_score = 35.0
        elif analysis.open_interest >= self.RECOMMENDED_OPEN_INTEREST:
            # 500-2000: 線性插值 25-35
            oi_score = 25.0 + (analysis.open_interest - self.RECOMMENDED_OPEN_INTEREST) / (EXCELLENT_OI - self.RECOMMENDED_OPEN_INTEREST) * 10.0
        elif analysis.open_interest >= self.MIN_OPEN_INTEREST:
            # 100-500: 線性插值 10-25
            oi_score = 10.0 + (analysis.open_interest - self.MIN_OPEN_INTEREST) / (self.RECOMMENDED_OPEN_INTEREST - self.MIN_OPEN_INTEREST) * 15.0
        else:
            oi_score = 0.0
        score += oi_score
        
        # Bid-Ask Spread 評分 (30%) - 增加更細緻的區間
        EXCELLENT_SPREAD = 2.0
        if analysis.bid_ask_spread_pct <= EXCELLENT_SPREAD:
            spread_score = 30.0
        elif analysis.bid_ask_spread_pct <= self.RECOMMENDED_BID_ASK_SPREAD_PCT:
            # 2-5%: 線性插值 20-30
            spread_score = 20.0 + (self.RECOMMENDED_BID_ASK_SPREAD_PCT - analysis.bid_ask_spread_pct) / (self.RECOMMENDED_BID_ASK_SPREAD_PCT - EXCELLENT_SPREAD) * 10.0
        elif analysis.bid_ask_spread_pct <= self.MAX_BID_ASK_SPREAD_PCT:
            # 5-10%: 線性插值 5-20
            spread_score = 5.0 + (self.MAX_BID_ASK_SPREAD_PCT - analysis.bid_ask_spread_pct) / (self.MAX_BID_ASK_SPREAD_PCT - self.RECOMMENDED_BID_ASK_SPREAD_PCT) * 15.0
        else:
            spread_score = 0.0
        score += spread_score
        
        return min(100.0, max(0.0, score))
    
    def _calculate_greeks_score(self, analysis: StrikeAnalysis, strategy_type: str) -> float:
        """
        計算 Greeks 評分 (0-100)
        
        根據策略類型調整評分，使用連續函數而非離散區間:
        - Long Call/Put: 偏好較高 Delta (0.3-0.7), 較低 Theta 損失
        - Short Call/Put: 偏好較低 Delta (0.1-0.3), 較高 Theta 收益
        """
        delta = abs(analysis.delta)
        
        if strategy_type in ['long_call', 'long_put']:
            # Long 策略: 偏好 Delta 0.4-0.6 (ATM)
            # 使用高斯函數，中心在 0.5，標準差 0.15
            # 這樣 Delta=0.5 得分最高，越遠離 0.5 分數越低
            delta_center = 0.5
            delta_std = 0.15
            delta_score = 50.0 * (2.718 ** (-((delta - delta_center) ** 2) / (2 * delta_std ** 2)))
            
            # Theta 評分: Long 策略希望 Theta 損失小（Theta 是負數）
            # Theta 越接近 0 越好，使用線性函數
            # 假設 Theta 範圍 [-0.5, 0]，-0.5 得 0 分，0 得 30 分
            if analysis.theta < 0:
                theta_score = max(0, 30.0 + analysis.theta * 60)  # -0.5 -> 0, 0 -> 30
            else:
                theta_score = 30.0
            
            # Vega 評分: Long 策略希望 Vega 高（受益於 IV 上升）
            # 假設 Vega 範圍 [0, 50]，使用對數函數
            if analysis.vega > 0:
                import math
                vega_score = min(20.0, 5.0 * math.log(1 + analysis.vega))
            else:
                vega_score = 0
            
        else:  # short_call, short_put
            # Short 策略: 偏好 Delta 0.15-0.25
            # 使用高斯函數，中心在 0.2，標準差 0.08
            delta_center = 0.20
            delta_std = 0.08
            delta_score = 50.0 * (2.718 ** (-((delta - delta_center) ** 2) / (2 * delta_std ** 2)))
            
            # Theta 評分: Short 策略希望 Theta 收益高（Theta 是負數，對 Short 有利）
            # Theta 越負越好，使用線性函數
            if analysis.theta < 0:
                theta_score = min(30.0, abs(analysis.theta) * 40)  # -0.75 -> 30
            else:
                theta_score = 0
            
            # Vega 評分: Short 策略希望 Vega 低（不受 IV 上升影響）
            # Vega 越低越好
            if analysis.vega >= 0:
                vega_score = max(0, 20.0 - analysis.vega * 0.5)
            else:
                vega_score = 20.0
        
        score = delta_score + theta_score + vega_score
        return min(100.0, max(0.0, score))
    
    def _calculate_iv_score(self, analysis: StrikeAnalysis, strategy_type: str) -> float:
        """
        計算 IV 評分 (0-100)
        
        根據策略類型調整評分，使用連續函數:
        - Long 策略: 偏好低 IV Rank (買便宜的期權)
        - Short 策略: 偏好高 IV Rank (賣貴的期權)
        """
        iv_rank = analysis.iv_rank
        
        if strategy_type in ['long_call', 'long_put']:
            # Long 策略: IV Rank 越低越好
            # 使用線性函數: IV Rank 0 -> 60 分, IV Rank 100 -> 10 分
            iv_rank_score = 60.0 - (iv_rank / 100.0) * 50.0
        else:
            # Short 策略: IV Rank 越高越好
            # 使用線性函數: IV Rank 0 -> 10 分, IV Rank 100 -> 60 分
            iv_rank_score = 10.0 + (iv_rank / 100.0) * 50.0
        
        # IV Skew 評分 (40%)
        # 負 Skew 表示該行使價 IV 低於 ATM，正 Skew 表示高於 ATM
        skew = analysis.iv_skew
        
        if strategy_type in ['long_call', 'long_put']:
            # Long 策略: 偏好負 Skew (IV 低於 ATM)
            # 使用線性函數: Skew -10 -> 40 分, Skew 0 -> 25 分, Skew +10 -> 10 分
            if skew <= 0:
                skew_score = 25.0 + min(15.0, abs(skew) * 1.5)  # -10 -> 40
            else:
                skew_score = max(10.0, 25.0 - skew * 1.5)  # +10 -> 10
        else:
            # Short 策略: 偏好正 Skew (IV 高於 ATM)
            # 使用線性函數: Skew +10 -> 40 分, Skew 0 -> 25 分, Skew -10 -> 10 分
            if skew >= 0:
                skew_score = 25.0 + min(15.0, skew * 1.5)  # +10 -> 40
            else:
                skew_score = max(10.0, 25.0 + skew * 1.5)  # -10 -> 10
        
        score = iv_rank_score + skew_score
        return min(100.0, max(0.0, score))
    
    def _calculate_risk_reward_score(
        self,
        analysis: StrikeAnalysis,
        current_price: float,
        strategy_type: str,
        target_price: Optional[float]
    ) -> float:
        """
        計算風險回報評分 (0-100)
        
        計算:
        - 最大損失
        - 盈虧平衡點
        - 潛在收益
        """
        score = 0.0
        premium = analysis.last_price if analysis.last_price > 0 else (analysis.bid + analysis.ask) / 2
        strike = analysis.strike
        
        # 設定目標價格（如果未提供，使用 ±10% 作為目標）
        if target_price is None:
            if strategy_type in ['long_call', 'short_put']:
                target_price = current_price * 1.10  # 看漲目標
            else:
                target_price = current_price * 0.90  # 看跌目標
        
        if strategy_type == 'long_call':
            analysis.max_loss = premium
            analysis.breakeven = strike + premium
            analysis.potential_profit = max(0, target_price - strike - premium)
            
        elif strategy_type == 'long_put':
            analysis.max_loss = premium
            analysis.breakeven = strike - premium
            analysis.potential_profit = max(0, strike - target_price - premium)
            
        elif strategy_type == 'short_call':
            analysis.max_loss = float('inf')  # 理論上無限
            analysis.breakeven = strike + premium
            analysis.potential_profit = premium
            
        elif strategy_type == 'short_put':
            analysis.max_loss = strike - premium  # 最大損失是股票跌到0
            analysis.breakeven = strike - premium
            analysis.potential_profit = premium
        
        # 計算風險回報比
        if analysis.max_loss > 0 and analysis.max_loss != float('inf'):
            risk_reward_ratio = analysis.potential_profit / analysis.max_loss
            
            if risk_reward_ratio >= 3:
                score = 100.0
            elif risk_reward_ratio >= 2:
                score = 80.0
            elif risk_reward_ratio >= 1:
                score = 60.0
            elif risk_reward_ratio >= 0.5:
                score = 40.0
            else:
                score = 20.0
        elif strategy_type in ['short_call', 'short_put']:
            # Short 策略: 評估收益相對於風險
            if premium > 0:
                score = min(80.0, premium / current_price * 1000)  # 權金佔股價比例
            else:
                score = 20.0
        else:
            score = 20.0
        
        return min(100.0, max(0.0, score))
    
    def _calculate_risk_reward_score_v2(
        self,
        analysis: StrikeAnalysis,
        current_price: float,
        strategy_type: str,
        target_price: Optional[float],
        holding_days: int = 30
    ) -> float:
        """
        增強的風險回報評分 (0-100)
        
        新增考慮因素:
        - 勝率估算（基於 Delta）
        - 時間衰減影響（基於 Theta）
        - 預期收益計算
        
        公式:
        win_probability = Delta (for bullish) or |Delta| (for bearish)
        expected_return = potential_profit × win_probability - max_loss × (1 - win_probability)
        theta_loss = |Theta| × holding_days (only for Long strategies)
        adjusted_return = expected_return - theta_loss
        
        Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
        
        返回:
            float: 評分 0-100
        """
        # 首先調用原始方法計算基本的 max_loss, breakeven, potential_profit
        premium = analysis.last_price if analysis.last_price > 0 else (analysis.bid + analysis.ask) / 2
        strike = analysis.strike
        
        # 設定目標價格（如果未提供，使用 ±10% 作為目標）
        if target_price is None:
            if strategy_type in ['long_call', 'short_put']:
                target_price = current_price * 1.10  # 看漲目標
            else:
                target_price = current_price * 0.90  # 看跌目標
        
        # 計算基本風險回報指標
        if strategy_type == 'long_call':
            analysis.max_loss = premium
            analysis.breakeven = strike + premium
            analysis.potential_profit = max(0, target_price - strike - premium)
            
        elif strategy_type == 'long_put':
            analysis.max_loss = premium
            analysis.breakeven = strike - premium
            analysis.potential_profit = max(0, strike - target_price - premium)
            
        elif strategy_type == 'short_call':
            analysis.max_loss = float('inf')  # 理論上無限
            analysis.breakeven = strike + premium
            analysis.potential_profit = premium
            
        elif strategy_type == 'short_put':
            analysis.max_loss = strike - premium  # 最大損失是股票跌到0
            analysis.breakeven = strike - premium
            analysis.potential_profit = premium
        
        # 計算勝率（基於 Delta）
        # Requirements 3.1: 使用 Delta 估算勝率
        delta = abs(analysis.delta)
        
        # 對於 Long Call/Short Put（看漲策略），勝率 = Delta
        # 對於 Long Put/Short Call（看跌策略），勝率 = |Delta|
        # Delta 代表期權到期時處於價內的概率
        if strategy_type in ['long_call', 'short_put']:
            # 看漲策略: Delta 直接代表勝率
            analysis.win_probability = delta
        else:
            # 看跌策略: 1 - Delta 代表勝率（因為 Put 的 Delta 是負的，我們用絕對值）
            # 但對於 Put，Delta 的絕對值本身就代表價內概率
            analysis.win_probability = delta
        
        # 計算預期收益
        # Requirements 3.3: expected_return = potential_profit × win_probability - max_loss × (1 - win_probability)
        max_loss_for_calc = analysis.max_loss
        
        # 對於 Short Call，max_loss 是無限的，使用一個合理的估計值
        if max_loss_for_calc == float('inf'):
            # 使用 2 倍當前股價作為最大損失估計
            max_loss_for_calc = current_price * 2
        
        analysis.expected_return = (
            analysis.potential_profit * analysis.win_probability - 
            max_loss_for_calc * (1 - analysis.win_probability)
        )
        
        # 計算 Theta 調整
        # Requirements 3.2, 3.6: Long 策略需要扣除 Theta 損失，Short 策略不扣除
        theta_loss = 0.0
        if strategy_type in ['long_call', 'long_put']:
            # Long 策略: Theta 是負的，代表每天的時間價值損失
            # theta_loss = |Theta| × holding_days
            theta_loss = abs(analysis.theta) * holding_days
            analysis.theta_adjusted_return = analysis.expected_return - theta_loss
            logger.debug(f"  Long 策略 Theta 調整: 預期收益 {analysis.expected_return:.2f} - Theta損失 {theta_loss:.2f} = {analysis.theta_adjusted_return:.2f}")
        else:
            # Short 策略: Theta 收益（不扣除，因為 Theta 對 Short 有利）
            # Requirements 3.6: Short 策略不扣除 Theta 損失
            analysis.theta_adjusted_return = analysis.expected_return
            logger.debug(f"  Short 策略: 預期收益 {analysis.expected_return:.2f} (Theta 有利，不扣除)")
        
        # 計算評分
        # Requirements 3.4, 3.5: 根據調整後的預期收益計算評分
        adjusted_return = analysis.theta_adjusted_return
        
        if adjusted_return <= 0:
            # Requirements 3.5: 調整後預期收益為負，評分為 20.0
            score = 20.0
            logger.debug(f"  調整後預期收益為負 ({adjusted_return:.2f})，評分 20.0")
        else:
            # Requirements 3.4: 調整後預期收益為正，根據收益率評分
            # 收益率 = 調整後預期收益 / 最大損失
            if max_loss_for_calc > 0:
                return_rate = adjusted_return / max_loss_for_calc
                
                # 評分範圍 [40, 100]，基於收益率
                # 收益率 >= 100% -> 100 分
                # 收益率 0% -> 40 分
                # 線性插值
                score = min(100.0, 40.0 + return_rate * 60.0)
                logger.debug(f"  收益率 {return_rate:.2%}，評分 {score:.1f}")
            else:
                score = 40.0
        
        return min(100.0, max(0.0, score))
    
    def calculate_composite_score(self, analysis: StrikeAnalysis, strategy_type: str) -> float:
        """
        計算綜合評分 (0-100)
        
        權重:
        - 流動性分數: 30%
        - Greeks分數: 30%
        - IV分數: 20%
        - 風險回報分數: 20%
        """
        composite = (
            analysis.liquidity_score * self.WEIGHT_LIQUIDITY +
            analysis.greeks_score * self.WEIGHT_GREEKS +
            analysis.iv_score * self.WEIGHT_IV +
            analysis.risk_reward_score * self.WEIGHT_RISK_REWARD
        )
        return min(100.0, max(0.0, composite))
    
    def _generate_recommendation_reason(self, analysis: StrikeAnalysis, strategy_type: str) -> str:
        """
        生成推薦理由
        
        根據評分最高的維度生成推薦理由
        Requirements: 2.5 - 在推薦理由中顯示安全概率
        Task 13.1: 更新推薦理由，包含 Long/Short 策略專用信息
        """
        reasons = []
        
        # ===== Task 13.1: Long 策略專用推薦理由 =====
        if strategy_type in ['long_call', 'long_put']:
            # 顯示期望收益
            if analysis.multi_scenario_profit:
                expected_pct = analysis.multi_scenario_profit.get('expected_profit_pct', 0)
                if expected_pct >= 100:
                    reasons.append(f"期望收益 {expected_pct:.0f}%")
                elif expected_pct >= 50:
                    reasons.append(f"期望收益 {expected_pct:.0f}%")
            
            # 顯示建議持倉天數
            if analysis.optimal_exit_timing:
                exit_day = analysis.optimal_exit_timing.get('recommended_exit_day', 0)
                annualized = analysis.optimal_exit_timing.get('annualized_return_pct', 0)
                if exit_day > 0 and annualized > 0:
                    reasons.append(f"建議持倉 {exit_day} 天")
        
        # ===== Task 13.1: Short 策略專用推薦理由 =====
        elif strategy_type in ['short_call', 'short_put']:
            # 顯示安全概率
            if analysis.premium_analysis:
                safe_prob = analysis.premium_analysis.get('safe_probability', 0)
                annualized = analysis.premium_analysis.get('annualized_yield_pct', 0)
                if safe_prob > 0:
                    reasons.append(f"安全概率 {safe_prob*100:.0f}%")
                if annualized > 0:
                    reasons.append(f"年化 {annualized:.0f}%")
            elif strategy_type == 'short_put':
                # 回退到原有邏輯
                safety_pct = analysis.safety_probability * 100
                reasons.append(f"安全概率 {safety_pct:.1f}%")
            
            # 顯示 Theta 優勢
            if analysis.hold_to_expiry_advantage:
                theta_pct = analysis.hold_to_expiry_advantage.get('theta_percentage', 0)
                if theta_pct >= 50:
                    reasons.append(f"Theta佔{theta_pct:.0f}%")
        
        # 流動性評分
        if analysis.liquidity_score >= 80:
            reasons.append("流動性優秀")
        elif analysis.liquidity_score >= 60:
            reasons.append("流動性良好")
        
        # Delta 評分
        delta = abs(analysis.delta)
        if strategy_type in ['long_call', 'long_put']:
            if 0.4 <= delta <= 0.6:
                reasons.append("Delta 接近 ATM")
            elif 0.3 <= delta <= 0.7:
                reasons.append("Delta 適中")
        else:
            if 0.1 <= delta <= 0.3:
                reasons.append("Delta 適合 Short 策略")
        
        # IV Skew 評分
        if analysis.iv_skew < -3:
            reasons.append("IV 低於 ATM")
        elif analysis.iv_skew > 3:
            reasons.append("IV 高於 ATM")
        
        # Theta 評分
        if strategy_type in ['short_call', 'short_put'] and analysis.theta < -0.5:
            reasons.append("Theta 收益高")
        
        # 風險回報
        if analysis.risk_reward_score >= 70:
            reasons.append("風險回報比佳")
        
        if not reasons:
            reasons.append("綜合評分最高")
        
        return "、".join(reasons[:4])  # 最多顯示 4 個理由
    
    def _generate_summary(self, best: StrikeAnalysis, strategy_type: str) -> str:
        """
        生成分析摘要
        
        Task 13.2: 更新摘要，包含新的分析結果
        """
        strategy_names = {
            'long_call': '買入認購期權 (Long Call)',
            'long_put': '買入認沽期權 (Long Put)',
            'short_call': '賣出認購期權 (Short Call)',
            'short_put': '賣出認沽期權 (Short Put)'
        }
        
        base_summary = (
            f"推薦 {strategy_names.get(strategy_type, strategy_type)} 行使價 ${best.strike:.2f}, "
            f"綜合評分 {best.composite_score:.1f}/100, "
            f"Delta {best.delta:.2f}"
        )
        
        # Task 13.2: 添加 Long/Short 策略專用摘要
        if strategy_type in ['long_call', 'long_put']:
            # Long 策略摘要
            if best.multi_scenario_profit:
                expected_pct = best.multi_scenario_profit.get('expected_profit_pct', 0)
                base_summary += f", 期望收益 {expected_pct:.0f}%"
            if best.optimal_exit_timing:
                exit_day = best.optimal_exit_timing.get('recommended_exit_day', 0)
                annualized = best.optimal_exit_timing.get('annualized_return_pct', 0)
                if exit_day > 0:
                    base_summary += f", 建議持倉 {exit_day} 天 (年化 {annualized:.0f}%)"
        else:
            # Short 策略摘要
            if best.premium_analysis:
                safe_prob = best.premium_analysis.get('safe_probability', 0)
                annualized = best.premium_analysis.get('annualized_yield_pct', 0)
                base_summary += f", 安全概率 {safe_prob*100:.0f}%, 年化 {annualized:.0f}%"
            if best.hold_to_expiry_advantage:
                theta_pct = best.hold_to_expiry_advantage.get('theta_percentage', 0)
                if theta_pct > 0:
                    base_summary += f", Theta佔{theta_pct:.0f}%"
        
        return base_summary
    
    def _create_empty_result(self, reason: str) -> Dict[str, Any]:
        """創建空結果"""
        return {
            'analyzed_strikes': [],
            'top_recommendations': [],
            'best_strike': 0,
            'total_analyzed': 0,
            'strategy_type': '',
            'current_price': 0,
            'strike_range': {
                'min': 0,
                'max': 0,
                'max_strikes_each_side': self.MAX_STRIKES_EACH_SIDE,
                'total_selected': 0
            },
            'analysis_summary': f"分析失敗: {reason}",
            'calculation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'error': reason,
            'parity_validation': None,  # Put-Call Parity 驗證結果
            'volatility_smile': None  # 波動率微笑分析結果 (Requirements 5.6)
        }
    
    def _validate_parity_for_atm(
        self,
        option_chain: Dict[str, Any],
        current_price: float,
        time_to_expiration: float,
        risk_free_rate: float = 0.045
    ) -> Optional[Dict]:
        """
        驗證 ATM 期權的 Put-Call Parity
        
        參數:
            option_chain: 期權鏈數據 {'calls': [...], 'puts': [...]}
            current_price: 當前股價
            time_to_expiration: 到期時間（年）
            risk_free_rate: 無風險利率
        
        返回:
            Dict: {
                'valid': bool,
                'deviation_pct': float,
                'arbitrage_opportunity': bool,
                'strategy': str,
                'atm_strike': float,
                'call_price': float,
                'put_price': float
            }
            或 None（如果驗證失敗）
        
        Requirements: 4.1, 4.5
        """
        try:
            logger.info("開始驗證 ATM 期權的 Put-Call Parity...")
            
            calls = option_chain.get('calls', [])
            puts = option_chain.get('puts', [])
            
            if not calls or not puts:
                logger.warning("! 期權鏈數據不完整，跳過 Parity 驗證")
                return None
            
            # 找到最接近 ATM 的行使價
            atm_strike = None
            min_distance = float('inf')
            
            # 從 calls 中找到所有行使價
            call_strikes = {opt.get('strike', 0): opt for opt in calls if opt.get('strike', 0) > 0}
            put_strikes = {opt.get('strike', 0): opt for opt in puts if opt.get('strike', 0) > 0}
            
            # 找到同時存在於 calls 和 puts 的行使價中最接近 ATM 的
            common_strikes = set(call_strikes.keys()) & set(put_strikes.keys())
            
            if not common_strikes:
                logger.warning("! 沒有找到同時存在 Call 和 Put 的行使價")
                return None
            
            for strike in common_strikes:
                distance = abs(strike - current_price)
                if distance < min_distance:
                    min_distance = distance
                    atm_strike = strike
            
            if atm_strike is None:
                logger.warning("! 無法找到 ATM 行使價")
                return None
            
            logger.info(f"  ATM 行使價: ${atm_strike:.2f} (股價: ${current_price:.2f})")
            
            # 獲取 ATM Call 和 Put 的價格
            atm_call = call_strikes[atm_strike]
            atm_put = put_strikes[atm_strike]
            
            # 獲取價格（優先使用 lastPrice，否則使用 mid price）
            call_price = atm_call.get('lastPrice', 0) or 0
            if call_price <= 0:
                bid = atm_call.get('bid', 0) or 0
                ask = atm_call.get('ask', 0) or 0
                call_price = (bid + ask) / 2 if (bid + ask) > 0 else 0
            
            put_price = atm_put.get('lastPrice', 0) or 0
            if put_price <= 0:
                bid = atm_put.get('bid', 0) or 0
                ask = atm_put.get('ask', 0) or 0
                put_price = (bid + ask) / 2 if (bid + ask) > 0 else 0
            
            # 驗證價格有效性
            if call_price <= 0 or put_price <= 0:
                logger.warning(f"! ATM 期權價格無效: Call=${call_price}, Put=${put_price}")
                return None
            
            logger.info(f"  ATM Call 價格: ${call_price:.4f}")
            logger.info(f"  ATM Put 價格: ${put_price:.4f}")
            
            # 調用 Module 19 進行 Parity 驗證
            from calculation_layer.module19_put_call_parity import PutCallParityValidator
            
            parity_validator = PutCallParityValidator()
            parity_result = parity_validator.validate_parity(
                call_price=call_price,
                put_price=put_price,
                stock_price=current_price,
                strike_price=atm_strike,
                risk_free_rate=risk_free_rate,
                time_to_expiration=time_to_expiration
            )
            
            # 判斷是否超過 2% 偏離閾值
            # Requirements 4.2: 偏離超過 2% 時標記為可能定價錯誤
            deviation_pct = abs(parity_result.deviation_percentage)
            is_valid = deviation_pct <= 2.0
            
            result = {
                'valid': is_valid,
                'deviation_pct': parity_result.deviation_percentage,
                'arbitrage_opportunity': parity_result.arbitrage_opportunity,
                'strategy': parity_result.strategy,
                'atm_strike': atm_strike,
                'call_price': call_price,
                'put_price': put_price,
                'theoretical_difference': parity_result.theoretical_difference,
                'actual_difference': parity_result.actual_difference,
                'theoretical_profit': parity_result.theoretical_profit
            }
            
            if not is_valid:
                logger.warning(f"! Put-Call Parity 偏離超過 2%: {deviation_pct:.2f}%")
            else:
                logger.info(f"* Put-Call Parity 驗證通過，偏離: {deviation_pct:.2f}%")
            
            return result
            
        except Exception as e:
            logger.error(f"x Put-Call Parity 驗證失敗: {e}")
            return None
    
    def _analyze_volatility_smile(
        self,
        option_chain: Dict[str, Any],
        current_price: float,
        time_to_expiration: float,
        risk_free_rate: float = 0.045
    ) -> Optional[Dict]:
        """
        執行波動率微笑分析
        
        參數:
            option_chain: 期權鏈數據 {'calls': [...], 'puts': [...]}
            current_price: 當前股價
            time_to_expiration: 到期時間（年）
            risk_free_rate: 無風險利率
        
        返回:
            Dict: 波動率微笑分析結果（包含可視化數據）
            或 None（如果分析失敗）
        
        Requirements: 5.6
        """
        try:
            logger.info("開始波動率微笑分析...")
            
            # 創建 VolatilitySmileAnalyzer 實例
            from calculation_layer.module24_volatility_smile import VolatilitySmileAnalyzer
            
            smile_analyzer = VolatilitySmileAnalyzer()
            
            # 調用 analyze_smile 方法
            smile_result = smile_analyzer.analyze_smile(
                option_chain=option_chain,
                current_price=current_price,
                time_to_expiration=time_to_expiration,
                risk_free_rate=risk_free_rate
            )
            
            # 轉換為字典格式，包含可視化數據
            result_dict = smile_result.to_dict()
            
            # 添加可視化數據用於圖表繪製
            # Requirements 5.6: 包含可視化數據用於圖表
            result_dict['visualization'] = {
                'chart_type': 'volatility_smile',
                'x_axis': 'strike_price',
                'y_axis': 'implied_volatility',
                'call_data': [
                    {'strike': strike, 'iv': iv}
                    for strike, iv in result_dict['call_ivs']
                ],
                'put_data': [
                    {'strike': strike, 'iv': iv}
                    for strike, iv in result_dict['put_ivs']
                ],
                'atm_marker': {
                    'strike': result_dict['atm_strike'],
                    'iv': result_dict['atm_iv']
                },
                'annotations': {
                    'skew': result_dict['skew'],
                    'shape': result_dict['smile_shape'],
                    'skew_25delta': result_dict['skew_25delta']
                }
            }
            
            logger.info(f"* 波動率微笑分析完成")
            logger.info(f"  ATM IV: {result_dict['atm_iv']:.2f}%")
            logger.info(f"  Skew: {result_dict['skew']:.2f}%")
            logger.info(f"  形狀: {result_dict['smile_shape']}")
            
            return result_dict
            
        except Exception as e:
            logger.error(f"x 波動率微笑分析失敗: {e}")
            return None
