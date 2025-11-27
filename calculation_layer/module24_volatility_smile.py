#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module 24: 波動率微笑分析器 (Volatility Smile Analyzer)

功能:
1. 計算不同行使價的 IV 分佈
2. 識別 ATM IV 作為基準
3. 計算 Skew（偏斜度）
4. 分類微笑形狀（symmetric, put_skew, call_skew）

來源: 金曹《期權制勝》+ 期權市場微觀結構分析

作者: Kiro
日期: 2025-11-27
版本: 1.0.0
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SmileAnalysisResult:
    """
    波動率微笑分析結果
    
    Requirements: 5.5
    """
    atm_iv: float  # ATM 隱含波動率（小數形式）
    atm_strike: float  # ATM 行使價
    call_ivs: List[Tuple[float, float]] = field(default_factory=list)  # [(strike, iv), ...]
    put_ivs: List[Tuple[float, float]] = field(default_factory=list)  # [(strike, iv), ...]
    skew: float = 0.0  # OTM Put IV - OTM Call IV
    smile_shape: str = 'unknown'  # 'symmetric', 'put_skew', 'call_skew'
    skew_25delta: float = 0.0  # 25-delta skew
    current_price: float = 0.0
    calculation_date: str = ''
    
    def to_dict(self) -> Dict:
        """
        轉換為字典格式
        
        Requirements: 5.5
        """
        return {
            'atm_iv': round(self.atm_iv * 100, 2),  # 轉換為百分比顯示
            'atm_strike': self.atm_strike,
            'call_ivs': [(s, round(iv * 100, 2)) for s, iv in self.call_ivs],
            'put_ivs': [(s, round(iv * 100, 2)) for s, iv in self.put_ivs],
            'skew': round(self.skew * 100, 2),  # 轉換為百分比顯示
            'smile_shape': self.smile_shape,
            'skew_25delta': round(self.skew_25delta * 100, 2),
            'current_price': self.current_price,
            'calculation_date': self.calculation_date
        }


class VolatilitySmileAnalyzer:
    """
    波動率微笑分析器
    
    功能:
    - 計算不同行使價的 IV 分佈
    - 識別 ATM IV 作為基準
    - 計算 Skew（偏斜度）
    - 分類微笑形狀
    
    Requirements: 5.1
    """
    
    def __init__(self):
        """
        初始化波動率微笑分析器
        
        Requirements: 5.1
        """
        self._iv_calculator = None
        logger.info("* 波動率微笑分析器已初始化")
    
    def _get_iv_calculator(self):
        """延遲初始化 IV 計算器"""
        if self._iv_calculator is None:
            from calculation_layer.module17_implied_volatility import ImpliedVolatilityCalculator
            self._iv_calculator = ImpliedVolatilityCalculator()
        return self._iv_calculator
    
    def analyze_smile(
        self,
        option_chain: Dict[str, Any],
        current_price: float,
        time_to_expiration: float,
        risk_free_rate: float = 0.045
    ) -> SmileAnalysisResult:
        """
        分析波動率微笑
        
        參數:
            option_chain: 期權鏈數據 {'calls': [...], 'puts': [...]}
            current_price: 當前股價
            time_to_expiration: 到期時間（年）
            risk_free_rate: 無風險利率
        
        返回:
            SmileAnalysisResult: 分析結果
        
        Requirements: 5.1, 5.2
        """
        try:
            logger.info(f"開始波動率微笑分析...")
            logger.info(f"  當前股價: ${current_price:.2f}")
            logger.info(f"  到期時間: {time_to_expiration:.4f}年")
            
            calls = option_chain.get('calls', [])
            puts = option_chain.get('puts', [])
            
            if not calls and not puts:
                logger.warning("! 期權鏈數據為空")
                return self._create_empty_result(current_price)
            
            # 計算每個行使價的 IV
            call_ivs = self._calculate_ivs_for_options(
                options=calls,
                option_type='call',
                current_price=current_price,
                time_to_expiration=time_to_expiration,
                risk_free_rate=risk_free_rate
            )
            
            put_ivs = self._calculate_ivs_for_options(
                options=puts,
                option_type='put',
                current_price=current_price,
                time_to_expiration=time_to_expiration,
                risk_free_rate=risk_free_rate
            )
            
            # 識別 ATM 行使價和 IV
            atm_strike, atm_iv = self._find_atm_iv(
                call_ivs=call_ivs,
                put_ivs=put_ivs,
                current_price=current_price
            )
            
            # 計算 Skew
            skew, skew_25delta = self._calculate_skew(
                call_ivs=call_ivs,
                put_ivs=put_ivs,
                atm_strike=atm_strike,
                current_price=current_price
            )
            
            # 分類微笑形狀
            smile_shape = self._classify_smile_shape(
                call_ivs=call_ivs,
                put_ivs=put_ivs,
                atm_strike=atm_strike
            )
            
            result = SmileAnalysisResult(
                atm_iv=atm_iv,
                atm_strike=atm_strike,
                call_ivs=call_ivs,
                put_ivs=put_ivs,
                skew=skew,
                smile_shape=smile_shape,
                skew_25delta=skew_25delta,
                current_price=current_price,
                calculation_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            
            logger.info(f"* 波動率微笑分析完成")
            logger.info(f"  ATM IV: {atm_iv*100:.2f}%")
            logger.info(f"  Skew: {skew*100:.2f}%")
            logger.info(f"  形狀: {smile_shape}")
            
            return result
            
        except Exception as e:
            logger.error(f"x 波動率微笑分析失敗: {e}")
            return self._create_empty_result(current_price)
    
    def _calculate_ivs_for_options(
        self,
        options: List[Dict],
        option_type: str,
        current_price: float,
        time_to_expiration: float,
        risk_free_rate: float
    ) -> List[Tuple[float, float]]:
        """
        計算期權列表的 IV
        
        Requirements: 5.1
        """
        ivs = []
        iv_calculator = self._get_iv_calculator()
        
        for option in options:
            strike = option.get('strike', 0)
            if strike <= 0:
                continue
            
            # 獲取市場價格
            market_price = option.get('lastPrice', 0) or 0
            if market_price <= 0:
                bid = option.get('bid', 0) or 0
                ask = option.get('ask', 0) or 0
                market_price = (bid + ask) / 2 if (bid + ask) > 0 else 0
            
            if market_price <= 0:
                # 嘗試使用 Yahoo Finance 提供的 IV
                yahoo_iv = option.get('impliedVolatility', 0) or 0
                if yahoo_iv > 0:
                    # 標準化 Yahoo IV
                    if yahoo_iv > 5:
                        yahoo_iv = yahoo_iv / 100.0
                    ivs.append((strike, yahoo_iv))
                continue
            
            try:
                # 使用 Module 17 計算 IV
                iv_result = iv_calculator.calculate_implied_volatility(
                    market_price=market_price,
                    stock_price=current_price,
                    strike_price=strike,
                    risk_free_rate=risk_free_rate,
                    time_to_expiration=time_to_expiration,
                    option_type=option_type
                )
                
                if iv_result.converged:
                    ivs.append((strike, iv_result.implied_volatility))
                else:
                    # 回退到 Yahoo IV
                    yahoo_iv = option.get('impliedVolatility', 0) or 0
                    if yahoo_iv > 0:
                        if yahoo_iv > 5:
                            yahoo_iv = yahoo_iv / 100.0
                        ivs.append((strike, yahoo_iv))
                        
            except Exception as e:
                logger.debug(f"  計算行使價 {strike} 的 IV 失敗: {e}")
                # 回退到 Yahoo IV
                yahoo_iv = option.get('impliedVolatility', 0) or 0
                if yahoo_iv > 0:
                    if yahoo_iv > 5:
                        yahoo_iv = yahoo_iv / 100.0
                    ivs.append((strike, yahoo_iv))
        
        # 按行使價排序
        ivs.sort(key=lambda x: x[0])
        return ivs
    
    def _find_atm_iv(
        self,
        call_ivs: List[Tuple[float, float]],
        put_ivs: List[Tuple[float, float]],
        current_price: float
    ) -> Tuple[float, float]:
        """
        找到 ATM 行使價和 IV
        
        Requirements: 5.2
        """
        # 合併所有行使價
        all_ivs = call_ivs + put_ivs
        
        if not all_ivs:
            logger.warning("! 沒有可用的 IV 數據")
            return (current_price, 0.30)  # 默認值
        
        # 找到最接近當前價格的行使價
        min_distance = float('inf')
        atm_strike = current_price
        atm_iv = 0.30
        
        for strike, iv in all_ivs:
            distance = abs(strike - current_price)
            if distance < min_distance:
                min_distance = distance
                atm_strike = strike
                atm_iv = iv
        
        # 如果 Call 和 Put 都有該行使價的 IV，取平均值
        call_iv_at_atm = None
        put_iv_at_atm = None
        
        for strike, iv in call_ivs:
            if strike == atm_strike:
                call_iv_at_atm = iv
                break
        
        for strike, iv in put_ivs:
            if strike == atm_strike:
                put_iv_at_atm = iv
                break
        
        if call_iv_at_atm is not None and put_iv_at_atm is not None:
            atm_iv = (call_iv_at_atm + put_iv_at_atm) / 2
        elif call_iv_at_atm is not None:
            atm_iv = call_iv_at_atm
        elif put_iv_at_atm is not None:
            atm_iv = put_iv_at_atm
        
        logger.debug(f"  ATM 行使價: ${atm_strike:.2f}, ATM IV: {atm_iv*100:.2f}%")
        return (atm_strike, atm_iv)

    
    def _calculate_skew(
        self,
        call_ivs: List[Tuple[float, float]],
        put_ivs: List[Tuple[float, float]],
        atm_strike: float,
        current_price: float
    ) -> Tuple[float, float]:
        """
        計算 Skew（偏斜度）
        
        Skew = OTM Put IV - OTM Call IV
        
        參數:
            call_ivs: Call 期權的 IV 列表 [(strike, iv), ...]
            put_ivs: Put 期權的 IV 列表 [(strike, iv), ...]
            atm_strike: ATM 行使價
            current_price: 當前股價
        
        返回:
            Tuple[float, float]: (skew, skew_25delta)
        
        Requirements: 5.4
        """
        skew = 0.0
        skew_25delta = 0.0
        
        if not call_ivs or not put_ivs:
            logger.debug("  無法計算 Skew: 缺少 Call 或 Put IV 數據")
            return (skew, skew_25delta)
        
        # 找到等距離的 OTM Put 和 OTM Call
        # OTM Put: strike < current_price
        # OTM Call: strike > current_price
        
        # 計算目標距離（約 5% OTM）
        target_distance = current_price * 0.05
        
        # 找到最接近目標距離的 OTM Put
        otm_put_iv = None
        min_put_distance = float('inf')
        
        for strike, iv in put_ivs:
            if strike < atm_strike:  # OTM Put
                distance = atm_strike - strike
                distance_diff = abs(distance - target_distance)
                if distance_diff < min_put_distance:
                    min_put_distance = distance_diff
                    otm_put_iv = iv
        
        # 找到最接近目標距離的 OTM Call
        otm_call_iv = None
        min_call_distance = float('inf')
        
        for strike, iv in call_ivs:
            if strike > atm_strike:  # OTM Call
                distance = strike - atm_strike
                distance_diff = abs(distance - target_distance)
                if distance_diff < min_call_distance:
                    min_call_distance = distance_diff
                    otm_call_iv = iv
        
        # 計算 Skew
        if otm_put_iv is not None and otm_call_iv is not None:
            skew = otm_put_iv - otm_call_iv
            logger.debug(f"  Skew: OTM Put IV ({otm_put_iv*100:.2f}%) - OTM Call IV ({otm_call_iv*100:.2f}%) = {skew*100:.2f}%")
        else:
            logger.debug("  無法計算 Skew: 找不到合適的 OTM 期權")
        
        # 計算 25-delta Skew（如果可能）
        # 25-delta 期權通常在 ATM ± 10-15% 範圍內
        target_25delta_distance = current_price * 0.10
        
        put_25delta_iv = None
        min_put_25delta_distance = float('inf')
        
        for strike, iv in put_ivs:
            if strike < atm_strike:
                distance = atm_strike - strike
                distance_diff = abs(distance - target_25delta_distance)
                if distance_diff < min_put_25delta_distance:
                    min_put_25delta_distance = distance_diff
                    put_25delta_iv = iv
        
        call_25delta_iv = None
        min_call_25delta_distance = float('inf')
        
        for strike, iv in call_ivs:
            if strike > atm_strike:
                distance = strike - atm_strike
                distance_diff = abs(distance - target_25delta_distance)
                if distance_diff < min_call_25delta_distance:
                    min_call_25delta_distance = distance_diff
                    call_25delta_iv = iv
        
        if put_25delta_iv is not None and call_25delta_iv is not None:
            skew_25delta = put_25delta_iv - call_25delta_iv
            logger.debug(f"  25-delta Skew: {skew_25delta*100:.2f}%")
        
        return (skew, skew_25delta)

    
    def _classify_smile_shape(
        self,
        call_ivs: List[Tuple[float, float]],
        put_ivs: List[Tuple[float, float]],
        atm_strike: float
    ) -> str:
        """
        分類微笑形狀
        
        規則:
        - symmetric: OTM Put IV ≈ OTM Call IV（差異 < 2%）
        - put_skew: OTM Put IV > OTM Call IV（常見於股票期權）
        - call_skew: OTM Call IV > OTM Put IV（常見於商品期權）
        
        參數:
            call_ivs: Call 期權的 IV 列表 [(strike, iv), ...]
            put_ivs: Put 期權的 IV 列表 [(strike, iv), ...]
            atm_strike: ATM 行使價
        
        返回:
            str: 'symmetric', 'put_skew', 或 'call_skew'
        
        Requirements: 5.3
        """
        if not call_ivs or not put_ivs:
            logger.debug("  無法分類微笑形狀: 缺少 Call 或 Put IV 數據")
            return 'unknown'
        
        # 計算 OTM Put 的平均 IV
        otm_put_ivs = [iv for strike, iv in put_ivs if strike < atm_strike]
        avg_otm_put_iv = sum(otm_put_ivs) / len(otm_put_ivs) if otm_put_ivs else 0
        
        # 計算 OTM Call 的平均 IV
        otm_call_ivs = [iv for strike, iv in call_ivs if strike > atm_strike]
        avg_otm_call_iv = sum(otm_call_ivs) / len(otm_call_ivs) if otm_call_ivs else 0
        
        if avg_otm_put_iv == 0 or avg_otm_call_iv == 0:
            logger.debug("  無法分類微笑形狀: OTM IV 數據不足")
            return 'unknown'
        
        # 計算差異
        iv_diff = avg_otm_put_iv - avg_otm_call_iv
        iv_diff_pct = iv_diff * 100  # 轉換為百分點
        
        # 分類閾值: 2% 差異
        threshold = 0.02
        
        if abs(iv_diff) < threshold:
            shape = 'symmetric'
            logger.debug(f"  微笑形狀: symmetric (差異 {iv_diff_pct:.2f}%)")
        elif iv_diff > 0:
            shape = 'put_skew'
            logger.debug(f"  微笑形狀: put_skew (OTM Put IV 高於 OTM Call IV {iv_diff_pct:.2f}%)")
        else:
            shape = 'call_skew'
            logger.debug(f"  微笑形狀: call_skew (OTM Call IV 高於 OTM Put IV {abs(iv_diff_pct):.2f}%)")
        
        return shape
    
    def _create_empty_result(self, current_price: float) -> SmileAnalysisResult:
        """創建空結果"""
        return SmileAnalysisResult(
            atm_iv=0.30,  # 默認 IV
            atm_strike=current_price,
            call_ivs=[],
            put_ivs=[],
            skew=0.0,
            smile_shape='unknown',
            skew_25delta=0.0,
            current_price=current_price,
            calculation_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
