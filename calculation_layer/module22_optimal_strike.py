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
            'liquidity_score': round(self.liquidity_score, 2),
            'greeks_score': round(self.greeks_score, 2),
            'iv_score': round(self.iv_score, 2),
            'risk_reward_score': round(self.risk_reward_score, 2),
            'composite_score': round(self.composite_score, 2),
            'strategy_suitability': self.strategy_suitability,
            'max_loss': round(self.max_loss, 2),
            'breakeven': round(self.breakeven, 2),
            'potential_profit': round(self.potential_profit, 2)
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
    
    # 流動性閾值（金曹三不買原則）
    MIN_VOLUME = 10
    MIN_OPEN_INTEREST = 100
    MAX_BID_ASK_SPREAD_PCT = 10.0
    
    # 推薦閾值
    RECOMMENDED_VOLUME = 100
    RECOMMENDED_OPEN_INTEREST = 500
    RECOMMENDED_BID_ASK_SPREAD_PCT = 5.0
    
    def __init__(self):
        logger.info("* 最佳行使價計算器已初始化")
    
    def analyze_strikes(
        self,
        current_price: float,
        option_chain: Dict[str, Any],
        strategy_type: str,
        days_to_expiration: int = 30,
        iv_rank: float = 50.0,
        target_price: Optional[float] = None
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
            
            # 過濾行使價範圍 (ATM ± 15%)
            min_strike = current_price * 0.85
            max_strike = current_price * 1.15
            
            # 分析每個行使價
            analyzed_strikes = []
            atm_iv = None  # 用於計算 IV Skew
            
            for option in options_data:
                strike = option.get('strike', 0)
                
                # 過濾範圍外的行使價
                if strike < min_strike or strike > max_strike:
                    continue
                
                # 過濾流動性不足的行使價（金曹三不買原則）
                volume = option.get('volume', 0) or 0
                oi = option.get('openInterest', 0) or 0
                
                if volume < self.MIN_VOLUME or oi < self.MIN_OPEN_INTEREST:
                    continue
                
                # 創建分析對象
                analysis = self._analyze_single_strike(
                    option, option_type, current_price, strategy_type,
                    days_to_expiration, iv_rank, target_price
                )
                
                if analysis:
                    analyzed_strikes.append(analysis)
                    
                    # 記錄 ATM IV 用於計算 IV Skew
                    if abs(strike - current_price) < current_price * 0.02:
                        atm_iv = analysis.iv
            
            if not analyzed_strikes:
                logger.warning("! 沒有符合條件的行使價")
                return self._create_empty_result("沒有符合流動性條件的行使價")
            
            # 計算 IV Skew
            if atm_iv:
                for analysis in analyzed_strikes:
                    analysis.iv_skew = analysis.iv - atm_iv
            
            # 計算綜合評分
            for analysis in analyzed_strikes:
                analysis.composite_score = self.calculate_composite_score(analysis, strategy_type)
            
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
                    'delta': round(s.delta, 4),
                    'volume': s.volume,
                    'open_interest': s.open_interest
                }
                for i, s in enumerate(analyzed_strikes[:3])
            ]
            
            best_strike = analyzed_strikes[0].strike if analyzed_strikes else 0
            
            result = {
                'analyzed_strikes': [s.to_dict() for s in analyzed_strikes],
                'top_recommendations': top_recommendations,
                'best_strike': best_strike,
                'total_analyzed': len(analyzed_strikes),
                'strategy_type': strategy_type,
                'current_price': current_price,
                'analysis_summary': self._generate_summary(analyzed_strikes[0], strategy_type) if analyzed_strikes else "無推薦",
                'calculation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logger.info(f"* 最佳行使價分析完成")
            logger.info(f"  分析了 {len(analyzed_strikes)} 個行使價")
            logger.info(f"  最佳行使價: ${best_strike:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"x 最佳行使價分析失敗: {e}")
            return self._create_empty_result(str(e))

    
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
            # 獲取 IV（Yahoo Finance 返回的已經是小數形式，如 0.25 表示 25%）
            raw_iv = option.get('impliedVolatility', 0) or 0
            # 如果 IV > 5，說明已經是百分比形式；否則轉換為百分比
            iv = raw_iv if raw_iv > 5 else raw_iv * 100
            
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
                    
                    # 計算時間（年）
                    time_to_expiry = days_to_expiration / 365.0
                    
                    # 確保時間不為零
                    if time_to_expiry <= 0:
                        time_to_expiry = 1 / 365.0  # 至少 1 天
                    
                    # 使用 IV 或默認值（確保波動率在合理範圍內）
                    if iv > 0:
                        # IV 已經是百分比形式，轉換為小數
                        volatility = iv / 100 if iv > 1 else iv
                        # 限制在合理範圍內 (1% - 500%)
                        volatility = max(0.01, min(5.0, volatility))
                    else:
                        volatility = 0.30
                    
                    # 獲取無風險利率（默認 4.5%）
                    risk_free_rate = 0.045
                    
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
                iv=iv,
                iv_rank=iv_rank
            )
            
            # 計算各項評分
            analysis.liquidity_score = self._calculate_liquidity_score(analysis)
            analysis.greeks_score = self._calculate_greeks_score(analysis, strategy_type)
            analysis.iv_score = self._calculate_iv_score(analysis, strategy_type)
            analysis.risk_reward_score = self._calculate_risk_reward_score(
                analysis, current_price, strategy_type, target_price
            )
            
            return analysis
            
        except Exception as e:
            logger.debug(f"  分析行使價 {option.get('strike', 'N/A')} 失敗: {e}")
            return None
    
    def _calculate_liquidity_score(self, analysis: StrikeAnalysis) -> float:
        """
        計算流動性評分 (0-100)
        
        基於金曹三不買原則:
        - Volume: 推薦 ≥ 100, 最低 ≥ 10
        - Open Interest: 推薦 ≥ 500, 最低 ≥ 100
        - Bid-Ask Spread: 推薦 < 5%, 最高 < 10%
        """
        score = 0.0
        
        # Volume 評分 (40%)
        if analysis.volume >= self.RECOMMENDED_VOLUME:
            volume_score = 40.0
        elif analysis.volume >= self.MIN_VOLUME:
            volume_score = 20.0 + (analysis.volume - self.MIN_VOLUME) / (self.RECOMMENDED_VOLUME - self.MIN_VOLUME) * 20.0
        else:
            volume_score = 0.0
        score += volume_score
        
        # Open Interest 評分 (40%)
        if analysis.open_interest >= self.RECOMMENDED_OPEN_INTEREST:
            oi_score = 40.0
        elif analysis.open_interest >= self.MIN_OPEN_INTEREST:
            oi_score = 20.0 + (analysis.open_interest - self.MIN_OPEN_INTEREST) / (self.RECOMMENDED_OPEN_INTEREST - self.MIN_OPEN_INTEREST) * 20.0
        else:
            oi_score = 0.0
        score += oi_score
        
        # Bid-Ask Spread 評分 (20%)
        if analysis.bid_ask_spread_pct <= self.RECOMMENDED_BID_ASK_SPREAD_PCT:
            spread_score = 20.0
        elif analysis.bid_ask_spread_pct <= self.MAX_BID_ASK_SPREAD_PCT:
            spread_score = 10.0 + (self.MAX_BID_ASK_SPREAD_PCT - analysis.bid_ask_spread_pct) / (self.MAX_BID_ASK_SPREAD_PCT - self.RECOMMENDED_BID_ASK_SPREAD_PCT) * 10.0
        else:
            spread_score = 0.0
        score += spread_score
        
        return min(100.0, max(0.0, score))
    
    def _calculate_greeks_score(self, analysis: StrikeAnalysis, strategy_type: str) -> float:
        """
        計算 Greeks 評分 (0-100)
        
        根據策略類型調整評分:
        - Long Call/Put: 偏好較高 Delta (0.3-0.7), 較低 Theta 損失
        - Short Call/Put: 偏好較低 Delta (0.1-0.3), 較高 Theta 收益
        """
        score = 0.0
        delta = abs(analysis.delta)
        
        if strategy_type in ['long_call', 'long_put']:
            # Long 策略: 偏好 Delta 0.3-0.7
            if 0.4 <= delta <= 0.6:
                delta_score = 50.0  # ATM 最佳
            elif 0.3 <= delta <= 0.7:
                delta_score = 40.0
            elif 0.2 <= delta <= 0.8:
                delta_score = 25.0
            else:
                delta_score = 10.0
            
            # Theta 評分: Long 策略希望 Theta 損失小
            theta_score = max(0, 30.0 + analysis.theta * 10) if analysis.theta < 0 else 30.0
            
            # Vega 評分: Long 策略希望 Vega 高（受益於 IV 上升）
            vega_score = min(20.0, analysis.vega * 2) if analysis.vega > 0 else 0
            
        else:  # short_call, short_put
            # Short 策略: 偏好 Delta 0.1-0.3
            if 0.1 <= delta <= 0.2:
                delta_score = 50.0  # 最佳
            elif 0.2 < delta <= 0.3:
                delta_score = 40.0
            elif delta < 0.1 or 0.3 < delta <= 0.4:
                delta_score = 25.0
            else:
                delta_score = 10.0
            
            # Theta 評分: Short 策略希望 Theta 收益高
            theta_score = min(30.0, abs(analysis.theta) * 10) if analysis.theta < 0 else 0
            
            # Vega 評分: Short 策略希望 Vega 低（不受 IV 上升影響）
            vega_score = max(0, 20.0 - analysis.vega * 2)
        
        score = delta_score + theta_score + vega_score
        return min(100.0, max(0.0, score))
    
    def _calculate_iv_score(self, analysis: StrikeAnalysis, strategy_type: str) -> float:
        """
        計算 IV 評分 (0-100)
        
        根據策略類型調整評分:
        - Long 策略: 偏好低 IV Rank (買便宜的期權)
        - Short 策略: 偏好高 IV Rank (賣貴的期權)
        """
        score = 0.0
        iv_rank = analysis.iv_rank
        
        if strategy_type in ['long_call', 'long_put']:
            # Long 策略: IV Rank 越低越好
            if iv_rank <= 20:
                iv_rank_score = 60.0
            elif iv_rank <= 30:
                iv_rank_score = 50.0
            elif iv_rank <= 50:
                iv_rank_score = 35.0
            elif iv_rank <= 70:
                iv_rank_score = 20.0
            else:
                iv_rank_score = 10.0
        else:
            # Short 策略: IV Rank 越高越好
            if iv_rank >= 80:
                iv_rank_score = 60.0
            elif iv_rank >= 70:
                iv_rank_score = 50.0
            elif iv_rank >= 50:
                iv_rank_score = 35.0
            elif iv_rank >= 30:
                iv_rank_score = 20.0
            else:
                iv_rank_score = 10.0
        
        score += iv_rank_score
        
        # IV Skew 評分 (40%)
        # 負 Skew 表示該行使價 IV 低於 ATM，正 Skew 表示高於 ATM
        skew = analysis.iv_skew
        if strategy_type in ['long_call', 'long_put']:
            # Long 策略: 偏好負 Skew (IV 低於 ATM)
            if skew <= -5:
                skew_score = 40.0
            elif skew <= 0:
                skew_score = 30.0
            elif skew <= 5:
                skew_score = 20.0
            else:
                skew_score = 10.0
        else:
            # Short 策略: 偏好正 Skew (IV 高於 ATM)
            if skew >= 5:
                skew_score = 40.0
            elif skew >= 0:
                skew_score = 30.0
            elif skew >= -5:
                skew_score = 20.0
            else:
                skew_score = 10.0
        
        score += skew_score
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
    
    def _generate_summary(self, best: StrikeAnalysis, strategy_type: str) -> str:
        """生成分析摘要"""
        strategy_names = {
            'long_call': '買入認購期權 (Long Call)',
            'long_put': '買入認沽期權 (Long Put)',
            'short_call': '賣出認購期權 (Short Call)',
            'short_put': '賣出認沽期權 (Short Put)'
        }
        
        return (
            f"推薦 {strategy_names.get(strategy_type, strategy_type)} 行使價 ${best.strike:.2f}, "
            f"綜合評分 {best.composite_score:.1f}/100, "
            f"Delta {best.delta:.2f}, "
            f"流動性評分 {best.liquidity_score:.1f}"
        )
    
    def _create_empty_result(self, reason: str) -> Dict[str, Any]:
        """創建空結果"""
        return {
            'analyzed_strikes': [],
            'top_recommendations': [],
            'best_strike': 0,
            'total_analyzed': 0,
            'strategy_type': '',
            'current_price': 0,
            'analysis_summary': f"分析失敗: {reason}",
            'calculation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'error': reason
        }
