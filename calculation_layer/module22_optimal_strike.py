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
            'safety_probability': round(self.safety_probability, 4)  # Requirements 2.5
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
                    'gamma': round(s.gamma, 4),
                    'theta': round(s.theta, 4),
                    'vega': round(s.vega, 4),
                    'volume': s.volume,
                    'open_interest': s.open_interest,
                    'iv': round(s.iv, 2),
                    'iv_skew': round(s.iv_skew, 2),
                    'bid_ask_spread_pct': round(s.bid_ask_spread_pct, 2),
                    'safety_probability': round(s.safety_probability, 4),  # Requirements 2.5
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
            
            # Bid/Ask 價格過濾邏輯
            # - Bid = 0 且 Ask = 0：跳過（無法交易）
            # - 只有 Bid（Ask = 0）：只能用於 Short 策略
            # - 只有 Ask（Bid = 0）：只能用於 Long 策略
            is_long_strategy = strategy_type in ['long_call', 'long_put']
            is_short_strategy = strategy_type in ['short_call', 'short_put']
            
            if bid == 0 and ask == 0:
                logger.debug(f"  跳過行使價 ${strike:.2f}: Bid 和 Ask 都為 0")
                return None
            
            if bid == 0 and is_short_strategy:
                logger.debug(f"  跳過行使價 ${strike:.2f}: Short 策略需要 Bid 價格，但 Bid = 0")
                return None
            
            if ask == 0 and is_long_strategy:
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
        """
        reasons = []
        
        # Short Put 安全概率顯示
        # Requirements: 2.5
        if strategy_type == 'short_put':
            safety_pct = analysis.safety_probability * 100
            reasons.append(f"安全概率 {safety_pct:.1f}%")
        
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
        
        return "、".join(reasons[:3])  # 最多顯示 3 個理由
    
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
