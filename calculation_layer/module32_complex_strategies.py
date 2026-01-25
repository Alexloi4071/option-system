#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module 32: 高級組合策略分析 (Complex Strategies)

功能:
1. 支援多腿策略 (Multi-Leg Strategies) 的數據結構
2. 計算組合策略的 Greeks 與 P&L
3. 實現 Vertical Spreads, Iron Condor 等高級策略邏輯

作者: Antigravity
日期: 2026-01-24
版本: 1.0.0
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import pandas as pd

logger = logging.getLogger(__name__)

@dataclass
class OptionLeg:
    """單個期權腿"""
    strike: float
    option_type: str  # 'call' or 'put'
    action: str       # 'buy' or 'sell'
    quantity: int = 1
    
    # 市場數據
    premium: float = 0.0  # 單價
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    iv: float = 0.0
    
    def __post_init__(self):
        # 統一 action 格式
        self.action = self.action.lower()
        if self.action not in ['buy', 'sell']:
            raise ValueError(f"無效的 action: {self.action}")

@dataclass
class StrategyResult:
    """策略分析結果"""
    name: str
    legs: List[OptionLeg]
    net_premium: float      # 淨權利金 (+收入, -支出)
    max_profit: float
    max_loss: float
    breakevens: List[float]
    priority_score: float = 0.0  # 推薦分數
    risk_reward_ratio: float = 0.0
    win_probability: float = 0.0
    
    # 組合 Greeks
    net_delta: float = 0.0
    net_gamma: float = 0.0
    net_theta: float = 0.0
    net_vega: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'description': self._get_description(),
            'net_premium': float(round(self.net_premium, 2)),
            'max_profit': float(round(self.max_profit, 2)) if self.max_profit != float('inf') else 'Unlimited',
            'max_loss': float(round(self.max_loss, 2)) if self.max_loss != float('inf') else 'Unlimited',
            'breakevens': [float(round(b, 2)) for b in self.breakevens],
            'risk_reward': float(round(self.risk_reward_ratio, 2)),
            'win_prob': float(round(self.win_probability * 100, 1)),
            'greeks': {
                'delta': float(round(self.net_delta, 4)),
                'gamma': float(round(self.net_gamma, 4)),
                'theta': float(round(self.net_theta, 4)),
                'vega': float(round(self.net_vega, 4))
            },
            'score': float(round(self.priority_score, 1))
        }
    
    def _get_description(self) -> str:
        legs_desc = []
        for leg in self.legs:
            action_symbol = "+" if leg.action == 'buy' else "-"
            type_symbol = "C" if leg.option_type == 'call' else "P"
            legs_desc.append(f"{action_symbol}{leg.quantity}{type_symbol}{leg.strike:.0f}")
        return f"{self.name} ({', '.join(legs_desc)})"

class ComplexStrategyAnalyzer:
    """
    高級組合策略分析器
    """
    
    def __init__(self):
        logger.info("* 高級組合策略分析器 (Complex Strategy) 已初始化")
        
    def analyze_vertical_spreads(self, 
                               calls_df: pd.DataFrame, 
                               puts_df: pd.DataFrame, 
                               current_price: float) -> Dict[str, List[StrategyResult]]:
        """
        分析垂直價差策略 (Credit Spreads)
        
        策略:
        1. Bull Put Spread (賣出 OTM Put Credit Spread) - 看漲/中性
        2. Bear Call Spread (賣出 OTM Call Credit Spread) - 看跌/中性
        """
        results = {'bull_put': [], 'bear_call': []}
        
        # 簡單篩選邏輯 (示例)
        # 尋找 Delta ~0.20 (Short) 和 Delta ~0.10 (Long) 的組合
        try:
            # 1. Bull Put Spread Logic
            # Short Put (Strike A, 高 Delta) + Long Put (Strike B, 低 Delta), A > B
            results['bull_put'] = self._find_spreads(
                puts_df, 'put', 'bull_put', current_price, 
                short_delta_target=0.20, width_pct=0.05
            )
            
            # 2. Bear Call Spread Logic
            # Short Call (Strike A, 高 Delta) + Long Call (Strike B, 低 Delta), A < B
            results['bear_call'] = self._find_spreads(
                calls_df, 'call', 'bear_call', current_price,
                short_delta_target=0.20, width_pct=0.05
            )
            
            return results
            
        except Exception as e:
            logger.error(f"垂直價差分析失敗: {e}")
            return results

    def _find_spreads(self, df: pd.DataFrame, option_type: str, strategy_name: str, 
                     current_price: float, short_delta_target: float, width_pct: float) -> List[StrategyResult]:
        """通用價差搜尋邏輯"""
        strategies = []
        
        if df.empty:
            return strategies
            
        # 確保有 delta
        if 'delta' not in df.columns:
            return strategies
            
        # 1. 尋找 Short Leg 候選者 (Delta 接近 target)
        # 對於 Put, delta 是負數，取絕對值比較
        df['abs_delta'] = df['delta'].abs()
        short_candidates = df[
            (df['abs_delta'] >= short_delta_target - 0.05) & 
            (df['abs_delta'] <= short_delta_target + 0.05)
        ]
        
        for _, short_leg in short_candidates.iterrows():
            short_strike = short_leg['strike']
            short_price = short_leg['lastPrice'] or (short_leg['bid'] + short_leg['ask']) / 2
            
            # 2. 尋找 Long Leg (Strike 距離約 5%)
            # Bull Put: Long Strike < Short Strike
            # Bear Call: Long Strike > Short Strike
            
            target_long_strike = short_strike * (1 - width_pct) if option_type == 'put' else short_strike * (1 + width_pct)
            
            # 在 DataFrame 中找最接近的 strike
            # 簡單起見，這裡只找一個
            long_candidates = df.iloc[(df['strike'] - target_long_strike).abs().argsort()[:1]]
            
            if not long_candidates.empty:
                long_leg = long_candidates.iloc[0]
                long_strike = long_leg['strike']
                long_price = long_leg['lastPrice'] or (long_leg['bid'] + long_leg['ask']) / 2
                
                # 構建策略對象
                leg1 = OptionLeg(short_strike, option_type, 'sell', 1, 
                               premium=short_price, delta=short_leg.get('delta', 0), 
                               gamma=short_leg.get('gamma', 0), theta=short_leg.get('theta', 0), 
                               vega=short_leg.get('vega', 0))
                               
                leg2 = OptionLeg(long_strike, option_type, 'buy', 1,
                               premium=long_price, delta=long_leg.get('delta', 0),
                               gamma=long_leg.get('gamma', 0), theta=long_leg.get('theta', 0),
                               vega=long_leg.get('vega', 0))
                
                # 計算策略指標
                net_premium = (short_price - long_price) * 100
                width = abs(short_strike - long_strike)
                max_loss = (width * 100) - net_premium
                
                # 簡單評分: 權利金 / 最大損失 (回報率)
                roi = net_premium / max_loss if max_loss > 0 else 0
                
                strat = StrategyResult(
                    name=strategy_name,
                    legs=[leg1, leg2],
                    net_premium=net_premium,
                    max_profit=net_premium,
                    max_loss=max_loss,
                    breakevens=[short_strike - (net_premium/100)] if option_type == 'put' else [short_strike + (net_premium/100)],
                    risk_reward_ratio=roi,
                    win_probability=1 - short_leg['abs_delta'], # 粗略估算
                    priority_score=roi * 100,
                    net_delta=leg1.delta - (leg2.delta if option_type == 'call' else -leg2.delta), # 簡化計算
                    net_gamma=leg1.gamma - leg2.gamma, # Sell position is short gamma? No, leg1 is sell, leg delta/gamma are per unit.
                    # 修正: Sell leg contributes negative Greeks (for Long Gamma/Vega assets)
                    # Sell delta = -1 * leg.delta
                    # Sell gamma = -1 * leg.gamma
                    net_theta= (-1 * leg1.theta * 1) + (leg2.theta * 1) 
                )
                
                # 重新精確計算 Greeks
                # Sell action: quantity = -1
                strat.net_delta = (-1 * leg1.delta) + (1 * leg2.delta)
                strat.net_gamma = (-1 * leg1.gamma) + (1 * leg2.gamma)
                strat.net_theta = (-1 * leg1.theta) + (1 * leg2.theta)
                strat.net_vega  = (-1 * leg1.vega)  + (1 * leg2.vega)
                
                strategies.append(strat)
                
        # 按分數排序
        strategies.sort(key=lambda x: x.priority_score, reverse=True)
        return strategies[:3] # 返回前3名

    def analyze_iron_condor(self, 
                          calls_df: pd.DataFrame, 
                          puts_df: pd.DataFrame, 
                          current_price: float) -> List[StrategyResult]:
        """
        分析鐵兀鷹策略 (Iron Condor)
        
        結構:
        - Bull Put Spread (賣 OTM Put Spread)
        - Bear Call Spread (賣 OTM Call Spread)
        
        適用:
        - 高 IV 環境
        - 預期橫盤震盪 (Range Bound)
        """
        strategies = []
        
        # 1. 獲取單邊 Spread 候選
        # 寬一點的 Condor: Short Delta ~0.15 - 0.20
        put_spreads = self._find_spreads(puts_df, 'put', 'bull_put', current_price, 
                                       short_delta_target=0.15, width_pct=0.05)
        call_spreads = self._find_spreads(calls_df, 'call', 'bear_call', current_price,
                                        short_delta_target=0.15, width_pct=0.05)
        
        if not put_spreads or not call_spreads:
            return strategies
            
        # 2. 組合 Condor (取最佳 Put Spread 和最佳 Call Spread)
        best_put_spread = put_spreads[0]
        best_call_spread = call_spreads[0]
        
        # 檢查 Strike 是否衝突 (Short Call Stirke 必須 > Short Put Strike)
        # Put Spread Legs: [Short Put, Long Put] -> Short Put Strike is Leg1
        short_put_strike = best_put_spread.legs[0].strike
        short_call_strike = best_call_spread.legs[0].strike
        
        if short_call_strike > short_put_strike:
            # 合併數據
            net_premium = best_put_spread.net_premium + best_call_spread.net_premium
            
            # Iron Condor 最大損失 = 較寬一邊的 Spread Width * 100 - Net Premium
            put_width = best_put_spread.max_loss + best_put_spread.net_premium
            call_width = best_call_spread.max_loss + best_call_spread.net_premium
            max_risk_width = max(put_width, call_width)
            
            max_loss = max_risk_width - net_premium
            
            condor = StrategyResult(
                name='iron_condor',
                legs=best_put_spread.legs + best_call_spread.legs,
                net_premium=net_premium,
                max_profit=net_premium,
                max_loss=max_loss,
                breakevens=[
                    short_put_strike - (net_premium / 100), 
                    short_call_strike + (net_premium / 100)
                ],
                risk_reward_ratio=net_premium / max_loss if max_loss > 0 else 0,
                # 簡單勝率估計: 1 - (Call Delta + Put Delta)
                win_probability=1 - (abs(best_call_spread.legs[0].delta) + abs(best_put_spread.legs[0].delta)),
                priority_score=(net_premium / max_loss * 100) if max_loss > 0 else 0,
                net_delta=best_put_spread.net_delta + best_call_spread.net_delta,
                net_gamma=best_put_spread.net_gamma + best_call_spread.net_gamma,
                net_theta=best_put_spread.net_theta + best_call_spread.net_theta,
                net_vega=best_put_spread.net_vega + best_call_spread.net_vega
            )
            strategies.append(condor)
            
        return strategies

    def analyze_straddle_strangle(self,
                                calls_df: pd.DataFrame,
                                puts_df: pd.DataFrame, 
                                current_price: float) -> Dict[str, List[StrategyResult]]:
        """
        分析跨式 (Straddle) 與寬跨式 (Strangle) 策略
        
        策略:
        1. Long Straddle: 買入 ATM Call + Put (波動率爆發)
        2. Long Strangle: 買入 OTM Call + Put (波動率爆發，成本較低)
        3. Short Straddle/Strangle: 賣出 (高 IV 收斂)
        """
        results = {'straddle': [], 'strangle': []}
        
        try:
            # 1. Long Straddle (尋找 ATM)
            # 找最接近 ATM 的 Call 和 Put
            atm_call = calls_df.iloc[(calls_df['strike'] - current_price).abs().argsort()[:1]]
            atm_put = puts_df.iloc[(puts_df['strike'] - current_price).abs().argsort()[:1]]
            
            if not atm_call.empty and not atm_put.empty:
                call_leg = atm_call.iloc[0]
                put_leg = atm_put.iloc[0]
                
                # 行使價必須相同
                if call_leg['strike'] == put_leg['strike']:
                    call_price = call_leg['lastPrice'] or (call_leg['bid'] + call_leg['ask']) / 2
                    put_price = put_leg['lastPrice'] or (put_leg['bid'] + put_leg['ask']) / 2
                    total_premium = (call_price + put_price) * 100
                    
                    leg1 = OptionLeg(call_leg['strike'], 'call', 'buy', 1, premium=call_price, 
                                   delta=call_leg.get('delta', 0), gamma=call_leg.get('gamma', 0),
                                   theta=call_leg.get('theta', 0), vega=call_leg.get('vega', 0))
                    leg2 = OptionLeg(put_leg['strike'], 'put', 'buy', 1, premium=put_price,
                                   delta=put_leg.get('delta', 0), gamma=put_leg.get('gamma', 0),
                                   theta=put_leg.get('theta', 0), vega=put_leg.get('vega', 0))
                                   
                    straddle = StrategyResult(
                        name='long_straddle',
                        legs=[leg1, leg2],
                        net_premium=-total_premium, # 支出
                        max_profit=float('inf'),
                        max_loss=total_premium,
                        breakevens=[
                            call_leg['strike'] - (total_premium / 100),
                            call_leg['strike'] + (total_premium / 100)
                        ],
                        risk_reward_ratio=0, # 無限
                        win_probability=0.35, # 粗略估計
                        priority_score=50, # 基礎分
                        net_delta=leg1.delta + leg2.delta,
                        net_gamma=leg1.gamma + leg2.gamma,
                        net_theta=leg1.theta + leg2.theta,
                        net_vega=leg1.vega + leg2.vega
                    )
                    results['straddle'].append(straddle)
            
            # 2. Long Strangle (尋找 OTM, Delta ~0.25)
            # Call Strike > Price, Put Strike < Price
            # 檢查 delta 列是否存在
            if 'delta' in calls_df.columns and 'delta' in puts_df.columns:
                otm_calls = calls_df[
                    (calls_df['strike'] > current_price) & 
                    (calls_df['delta'] >= 0.20) & (calls_df['delta'] <= 0.30)
                ].sort_values('delta', key=lambda x: (x - 0.25).abs())
                
                otm_puts = puts_df[
                    (puts_df['strike'] < current_price) & 
                    (puts_df['delta'].abs() >= 0.20) & (puts_df['delta'].abs() <= 0.30)
                ].sort_values('delta', key=lambda x: (x.abs() - 0.25).abs())
            else:
                # 如果沒有 delta 列，使用價外程度作為替代篩選
                otm_calls = calls_df[
                    (calls_df['strike'] > current_price) & 
                    (calls_df['strike'] <= current_price * 1.1)  # OTM 10% 以內
                ].head(3)
                otm_puts = puts_df[
                    (puts_df['strike'] < current_price) & 
                    (puts_df['strike'] >= current_price * 0.9)  # OTM 10% 以內
                ].head(3)
            
            if not otm_calls.empty and not otm_puts.empty:
                call_leg = otm_calls.iloc[0]
                put_leg = otm_puts.iloc[0]
                
                call_price = call_leg['lastPrice'] or (call_leg['bid'] + call_leg['ask']) / 2
                put_price = put_leg['lastPrice'] or (put_leg['bid'] + put_leg['ask']) / 2
                total_premium = (call_price + put_price) * 100
                
                leg1 = OptionLeg(call_leg['strike'], 'call', 'buy', 1, premium=call_price,
                               delta=call_leg.get('delta', 0), gamma=call_leg.get('gamma', 0),
                               theta=call_leg.get('theta', 0), vega=call_leg.get('vega', 0))
                leg2 = OptionLeg(put_leg['strike'], 'put', 'buy', 1, premium=put_price,
                               delta=put_leg.get('delta', 0), gamma=put_leg.get('gamma', 0),
                               theta=put_leg.get('theta', 0), vega=put_leg.get('vega', 0))
                               
                strangle = StrategyResult(
                    name='long_strangle',
                    legs=[leg1, leg2],
                    net_premium=-total_premium,
                    max_profit=float('inf'),
                    max_loss=total_premium,
                    breakevens=[
                        put_leg['strike'] - (total_premium / 100),
                        call_leg['strike'] + (total_premium / 100)
                    ],
                    risk_reward_ratio=0,
                    win_probability=0.30,
                    priority_score=50,
                    net_delta=leg1.delta + leg2.delta,
                    net_gamma=leg1.gamma + leg2.gamma,
                    net_theta=leg1.theta + leg2.theta,
                    net_vega=leg1.vega + leg2.vega
                )
                results['strangle'].append(strangle)
                
            return results
            
        except Exception as e:
            logger.error(f"Straddle/Strangle 分析失敗: {e}")
            return results
