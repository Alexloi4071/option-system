#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module 25: 波動率微笑分析

功能:
1. 分析 Call/Put 隱含波動率曲線（波動率微笑）
2. 計算 IV Skew（波動率偏斜）和 IV Smile（波動率微笑）
3. 識別定價異常和套利機會
4. 為交易決策提供波動率環境洞察

IV Smile 模式:
- Smile: U 形曲線，ATM 較低，兩邊較高（股票期權典型）
- Skew: 向下傾斜，OTM Put IV 高於 OTM Call（股票期權典型）
- Smirk: 微笑 + 傾斜的組合

來源: Options Industry Council (OIC) + 芝加哥期權交易所 (CBOE)

作者: Kiro
日期: 2025-12-22
版本: 1.0.0
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class IVSmileShape(Enum):
    """IV 微笑形狀"""
    SMILE = "smile"        # U 形，ATM 較低
    SKEW = "skew"          # 向下傾斜，左邊較高
    REVERSE_SKEW = "reverse_skew"  # 向上傾斜，右邊較高
    FLAT = "flat"          # 平坦
    UNKNOWN = "unknown"    # 無法識別


class IVEnvironment(Enum):
    """IV 環境分類"""
    STEEP_SMILE = "steep_smile"        # 陡峭微笑
    GENTLE_SMILE = "gentle_smile"      # 溫和微笑
    CALL_SKEW = "call_skew"            # Call Skew（看漲傾斜）
    PUT_SKEW = "put_skew"              # Put Skew（看跌傾斜）
    FLAT_IV = "flat_iv"                # 平坦


@dataclass
class MoneynessBucket:
    """按 Moneyness 分類的期權組"""
    moneyness_pct: float  # Moneyness 百分比 (e.g., 0.90 = 90% of ATM)
    strikes: List[float]  # 該組的行使價列表
    call_iv: Optional[float] = None  # Call IV
    put_iv: Optional[float] = None   # Put IV
    avg_iv: Optional[float] = None   # 平均 IV
    call_bid_ask_spread: Optional[float] = None  # Call Bid-Ask Spread %
    put_bid_ask_spread: Optional[float] = None   # Put Bid-Ask Spread %
    call_volume: int = 0  # Call 成交量
    put_volume: int = 0   # Put 成交量
    
    def to_dict(self) -> Dict:
        return {
            'moneyness_pct': round(self.moneyness_pct * 100, 1),
            'strikes': [round(s, 2) for s in self.strikes],
            'call_iv': round(self.call_iv * 100, 2) if self.call_iv else None,
            'put_iv': round(self.put_iv * 100, 2) if self.put_iv else None,
            'avg_iv': round(self.avg_iv * 100, 2) if self.avg_iv else None,
            'call_bid_ask_spread': round(self.call_bid_ask_spread, 2) if self.call_bid_ask_spread else None,
            'put_bid_ask_spread': round(self.put_bid_ask_spread, 2) if self.put_bid_ask_spread else None,
            'call_volume': self.call_volume,
            'put_volume': self.put_volume
        }


@dataclass
class VolatilitySmileResult:
    """波動率微笑分析結果"""
    # ATM 信息
    atm_strike: float
    atm_iv: float
    current_price: float
    
    # IV Skew 指標
    skew: float = 0.0
    skew_type: str = "neutral"  # "put_skew", "call_skew", "neutral"
    skew_25delta: float = 0.0  # 25 Delta Skew（更精確的衡量）
    
    # IV Smile 指標
    smile_curve: float = 0.0
    smile_shape: str = "neutral"  # "smile", "smirk", "skew", "flat"
    smile_steepness: float = 0.0  # 微笑陡峭度 (0-1)
    
    # 分層 IV 數據（用於可視化）
    call_ivs: List[Tuple[float, float]] = field(default_factory=list)  # [(strike, iv), ...]
    put_ivs: List[Tuple[float, float]] = field(default_factory=list)   # [(strike, iv), ...]
    
    # 按 Moneyness 分類
    moneyness_buckets: List[MoneynessBucket] = field(default_factory=list)
    
    # IV 分布統計
    call_iv_mean: float = 0.0
    call_iv_std: float = 0.0
    put_iv_mean: float = 0.0
    put_iv_std: float = 0.0
    
    # 環境評估
    iv_environment: str = "neutral"  # "steep_smile", "gentle_smile", "call_skew", "put_skew", "flat"
    mean_reversion_signal: str = "neutral"  # "revert_to_mean", "widen", "hold"
    
    # 定價異常檢測
    pricing_anomalies: List[Dict] = field(default_factory=list)  # 異常行使價
    anomaly_count: int = 0
    
    # 交易建議
    trading_recommendations: List[str] = field(default_factory=list)
    recommendation_confidence: float = 0.0  # 0-1
    
    # 計算時間戳
    calculation_date: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'atm_strike': round(self.atm_strike, 2),
            'atm_iv': round(self.atm_iv * 100, 2),
            'current_price': round(self.current_price, 2),
            'skew': round(self.skew * 100, 2),
            'skew_type': self.skew_type,
            'skew_25delta': round(self.skew_25delta * 100, 2),
            'smile_curve': round(self.smile_curve * 100, 2),
            'smile_shape': self.smile_shape,
            'smile_steepness': round(self.smile_steepness, 3),
            'call_ivs': [(round(s, 2), round(iv * 100, 2)) for s, iv in self.call_ivs],
            'put_ivs': [(round(s, 2), round(iv * 100, 2)) for s, iv in self.put_ivs],
            'moneyness_buckets': [b.to_dict() for b in self.moneyness_buckets],
            'call_iv_mean': round(self.call_iv_mean * 100, 2),
            'call_iv_std': round(self.call_iv_std * 100, 2),
            'put_iv_mean': round(self.put_iv_mean * 100, 2),
            'put_iv_std': round(self.put_iv_std * 100, 2),
            'iv_environment': self.iv_environment,
            'mean_reversion_signal': self.mean_reversion_signal,
            'pricing_anomalies': self.pricing_anomalies,
            'anomaly_count': self.anomaly_count,
            'trading_recommendations': self.trading_recommendations,
            'recommendation_confidence': round(self.recommendation_confidence, 2),
            'calculation_date': self.calculation_date
        }


class VolatilitySmileAnalyzer:
    """
    波動率微笑分析器
    
    分析期權鏈中的隱含波動率分布，識別定價模式和異常
    """
    
    # 定價異常閾值
    ANOMALY_THRESHOLD = 0.05  # 偏離標準差超過 5%
    
    # Moneyness 分組
    MONEYNESS_GROUPS = [
        (0.80, "Deep OTM"),      # 深度 OTM
        (0.90, "OTM"),           # OTM
        (0.95, "Near ATM"),      # 接近 ATM
        (1.00, "ATM"),           # ATM
        (1.05, "Near ATM"),      # 接近 ATM
        (1.10, "OTM"),           # OTM（Call）
        (1.20, "Deep OTM")       # 深度 OTM（Call）
    ]
    
    # IV 環境閾值
    STEEP_SMILE_THRESHOLD = 0.10  # 超過 10% 的微笑為陡峭
    FLAT_IV_THRESHOLD = 0.02      # 低於 2% 的傾斜為平坦
    
    def __init__(self):
        logger.info("* 波動率微笑分析器已初始化")
    
    def analyze_smile(
        self,
        option_chain: Dict[str, Any],
        current_price: float,
        time_to_expiration: float,
        risk_free_rate: float = 0.045
    ) -> VolatilitySmileResult:
        """
        分析期權鏈的波動率微笑
        
        參數:
            option_chain: 期權鏈數據 {'calls': [...], 'puts': [...]}
            current_price: 當前股價
            time_to_expiration: 到期時間（年）
            risk_free_rate: 無風險利率
        
        返回:
            VolatilitySmileResult: 分析結果
        """
        try:
            logger.info(f"開始波動率微笑分析...")
            logger.info(f"  當前股價: ${current_price:.2f}")
            logger.info(f"  到期時間: {time_to_expiration*252:.0f} 天")
            
            # 1. 提取 IV 數據
            calls_data = option_chain.get('calls', [])
            puts_data = option_chain.get('puts', [])
            
            if not calls_data or not puts_data:
                logger.warning("! 期權鏈數據不完整")
                return self._create_empty_result(current_price)
            
            # 2. 找到 ATM 行使價
            atm_strike = self._find_atm_strike(calls_data, current_price)
            if atm_strike is None:
                logger.warning("! 無法找到 ATM 行使價")
                return self._create_empty_result(current_price)
            
            # 3. 提取並標準化 IV
            call_ivs = self._extract_iv_data(calls_data, 'call')
            put_ivs = self._extract_iv_data(puts_data, 'put')
            
            atm_iv = self._get_atm_iv(call_ivs, atm_strike)
            
            if atm_iv is None:
                logger.warning("! 無法獲取 ATM IV")
                return self._create_empty_result(current_price)
            
            logger.info(f"  ATM 行使價: ${atm_strike:.2f}")
            logger.info(f"  ATM IV: {atm_iv*100:.2f}%")
            
            # 4. 創建結果對象
            result = VolatilitySmileResult(
                atm_strike=atm_strike,
                atm_iv=atm_iv,
                current_price=current_price,
                calculation_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            
            # 5. 計算 IV Skew
            logger.info("  計算 IV Skew...")
            result.skew = self._calculate_skew(call_ivs, put_ivs, atm_strike, current_price)
            result.skew_type = self._classify_skew(result.skew)
            result.skew_25delta = self._calculate_25delta_skew(call_ivs, put_ivs, current_price)
            
            logger.info(f"    Skew: {result.skew*100:.2f}% ({result.skew_type})")
            logger.info(f"    25 Delta Skew: {result.skew_25delta*100:.2f}%")
            
            # 6. 計算 IV Smile
            logger.info("  計算 IV Smile...")
            result.smile_curve = self._calculate_smile(call_ivs, put_ivs, atm_strike, current_price)
            result.smile_shape = self._classify_smile_shape(result.skew, result.smile_curve)
            result.smile_steepness = self._calculate_smile_steepness(call_ivs, put_ivs, atm_iv)
            
            logger.info(f"    Smile 曲線: {result.smile_curve*100:.2f}%")
            logger.info(f"    形狀: {result.smile_shape}")
            logger.info(f"    陡峭度: {result.smile_steepness:.3f}")
            
            # 7. 分層 IV 數據
            logger.info("  分層 IV 數據...")
            result.call_ivs = sorted(call_ivs.items())
            result.put_ivs = sorted(put_ivs.items())
            result.moneyness_buckets = self._create_moneyness_buckets(
                calls_data, puts_data, current_price, atm_strike
            )
            
            # 8. 計算 IV 統計
            logger.info("  計算 IV 統計...")
            call_iv_values = list(call_ivs.values())
            put_iv_values = list(put_ivs.values())
            
            result.call_iv_mean = sum(call_iv_values) / len(call_iv_values) if call_iv_values else 0
            result.call_iv_std = self._calculate_std(call_iv_values, result.call_iv_mean)
            result.put_iv_mean = sum(put_iv_values) / len(put_iv_values) if put_iv_values else 0
            result.put_iv_std = self._calculate_std(put_iv_values, result.put_iv_mean)
            
            logger.info(f"    Call IV: {result.call_iv_mean*100:.2f}% ± {result.call_iv_std*100:.2f}%")
            logger.info(f"    Put IV: {result.put_iv_mean*100:.2f}% ± {result.put_iv_std*100:.2f}%")
            
            # 9. 評估 IV 環境
            logger.info("  評估 IV 環境...")
            result.iv_environment = self._assess_iv_environment(
                result.smile_steepness, result.skew, result.smile_shape
            )
            logger.info(f"    環境: {result.iv_environment}")
            
            # 10. 檢測定價異常
            logger.info("  檢測定價異常...")
            result.pricing_anomalies = self._detect_pricing_anomalies(
                call_ivs, put_ivs, atm_iv, result.call_iv_std, result.put_iv_std
            )
            result.anomaly_count = len(result.pricing_anomalies)
            
            if result.anomaly_count > 0:
                logger.warning(f"    發現 {result.anomaly_count} 個定價異常")
            
            # 11. 生成交易建議
            logger.info("  生成交易建議...")
            result.trading_recommendations, result.recommendation_confidence = \
                self._generate_recommendations(result)
            
            logger.info(f"* 波動率微笑分析完成")
            return result
            
        except Exception as e:
            logger.error(f"x 波動率微笑分析失敗: {e}")
            import traceback
            traceback.print_exc()
            return self._create_empty_result(current_price)
    
    def _find_atm_strike(self, options: List[Dict], current_price: float) -> Optional[float]:
        """
        找到最接近當前股價的 ATM 行使價
        """
        try:
            min_distance = float('inf')
            atm_strike = None
            
            for opt in options:
                strike = opt.get('strike', 0)
                distance = abs(strike - current_price)
                
                if distance < min_distance:
                    min_distance = distance
                    atm_strike = strike
            
            return atm_strike if atm_strike is not None else None
        except Exception as e:
            logger.error(f"找到 ATM 行使價失敗: {e}")
            return None
    
    def _extract_iv_data(self, options: List[Dict], option_type: str) -> Dict[float, float]:
        """
        提取期權鏈的 IV 數據
        
        返回: {strike: iv, ...}
        """
        iv_data = {}
        
        for opt in options:
            strike = opt.get('strike', 0)
            
            # 獲取 IV（優先 impliedVolatility，否則嘗試計算）
            iv_raw = opt.get('impliedVolatility', 0)
            
            if iv_raw is None or iv_raw == 0:
                # 嘗試從 bid/ask/lastPrice 反推 IV（簡化版）
                bid = opt.get('bid', 0) or 0
                ask = opt.get('ask', 0) or 0
                
                if bid > 0 and ask > 0:
                    # 使用 mid price 作為 IV 估計的輸入
                    mid_price = (bid + ask) / 2
                    # 簡化：IV = (mid_price / strike) × volatility_factor
                    # 實際應使用完整的 IV 計算
                    iv_raw = mid_price / strike * 0.3 if strike > 0 else 0.3
                else:
                    continue  # 跳過無效期權
            
            # 標準化 IV 為小數形式
            if iv_raw > 1.0:  # 百分比形式
                iv_normalized = iv_raw / 100.0
            else:
                iv_normalized = iv_raw
            
            # 過濾異常 IV
            if 0.01 <= iv_normalized <= 5.0:
                iv_data[strike] = iv_normalized
        
        return iv_data
    
    def _get_atm_iv(self, call_ivs: Dict[float, float], atm_strike: float) -> Optional[float]:
        """
        獲取 ATM IV（如果精確 ATM 不存在，則使用接近的行使價）
        """
        # 首先嘗試找到精確的 ATM IV
        if atm_strike in call_ivs:
            return call_ivs[atm_strike]
        
        # 否則找最接近的
        min_distance = float('inf')
        closest_iv = None
        
        for strike, iv in call_ivs.items():
            distance = abs(strike - atm_strike)
            if distance < min_distance:
                min_distance = distance
                closest_iv = iv
        
        return closest_iv
    
    def _calculate_skew(
        self,
        call_ivs: Dict[float, float],
        put_ivs: Dict[float, float],
        atm_strike: float,
        current_price: float
    ) -> float:
        """
        計算 IV Skew
        
        Skew = IV(OTM Put) - IV(OTM Call)
        正值: Put IV > Call IV（看跌傾斜，股票典型）
        負值: Call IV > Put IV（看漲傾斜）
        """
        try:
            # 找到 10% OTM Put 和 Call 的行使價
            otm_put_strike = current_price * 0.90
            otm_call_strike = current_price * 1.10
            
            # 找最接近的行使價
            closest_put_iv = self._find_closest_iv(put_ivs, otm_put_strike)
            closest_call_iv = self._find_closest_iv(call_ivs, otm_call_strike)
            
            if closest_put_iv is not None and closest_call_iv is not None:
                skew = closest_put_iv - closest_call_iv
                return skew
            
            return 0.0
        except Exception as e:
            logger.debug(f"計算 Skew 失敗: {e}")
            return 0.0
    
    def _calculate_25delta_skew(
        self,
        call_ivs: Dict[float, float],
        put_ivs: Dict[float, float],
        current_price: float
    ) -> float:
        """
        計算 25 Delta Skew（更精確的衡量）
        
        使用 25% OTM Put 和 75% OTM Call 的 IV 差異
        """
        try:
            # 找 25% OTM 的行使價（Delta 約 0.25）
            otm25_put_strike = current_price * 0.88  # 約 12% OTM
            otm25_call_strike = current_price * 1.12  # 約 12% OTM
            
            put_iv = self._find_closest_iv(put_ivs, otm25_put_strike)
            call_iv = self._find_closest_iv(call_ivs, otm25_call_strike)
            
            if put_iv is not None and call_iv is not None:
                return put_iv - call_iv
            
            return 0.0
        except Exception as e:
            logger.debug(f"計算 25 Delta Skew 失敗: {e}")
            return 0.0
    
    def _calculate_smile(
        self,
        call_ivs: Dict[float, float],
        put_ivs: Dict[float, float],
        atm_strike: float,
        current_price: float
    ) -> float:
        """
        計算 IV Smile
        
        Smile = (IV(OTM Put) + IV(OTM Call)) / 2 - IV(ATM)
        正值: 兩邊 IV > ATM IV（微笑形狀）
        負值: 兩邊 IV < ATM IV（反向微笑，罕見）
        """
        try:
            atm_iv = self._get_atm_iv(call_ivs, atm_strike)
            if atm_iv is None:
                return 0.0
            
            # 找 10% OTM 的 IV
            otm_put_iv = self._find_closest_iv(put_ivs, current_price * 0.90)
            otm_call_iv = self._find_closest_iv(call_ivs, current_price * 1.10)
            
            if otm_put_iv is not None and otm_call_iv is not None:
                smile = (otm_put_iv + otm_call_iv) / 2 - atm_iv
                return smile
            
            return 0.0
        except Exception as e:
            logger.debug(f"計算 Smile 失敗: {e}")
            return 0.0
    
    def _classify_skew(self, skew: float) -> str:
        """
        分類 IV Skew
        """
        if skew > 0.03:  # 超過 3%
            return "put_skew"
        elif skew < -0.03:
            return "call_skew"
        else:
            return "neutral"
    
    def _classify_smile_shape(self, skew: float, smile_curve: float) -> str:
        """
        分類微笑形狀
        """
        # 如果 Smile > 0 且 |Skew| 較小 -> Smile
        # 如果 Smile > 0 且 |Skew| 較大 -> Smirk (Smile + Skew)
        # 如果 Smile ≈ 0 -> Skew
        # 如果都接近 0 -> Flat
        
        if abs(smile_curve) < 0.01 and abs(skew) < 0.02:
            return "flat"
        elif abs(skew) > 0.05:
            return "skew"
        elif smile_curve > 0.05:
            if abs(skew) > 0.02:
                return "smirk"
            else:
                return "smile"
        else:
            return "neutral"
    
    def _calculate_smile_steepness(self, call_ivs: Dict, put_ivs: Dict, atm_iv: float) -> float:
        """
        計算微笑陡峭度 (0-1)
        
        陡峭度 = max(|IV - ATM_IV| / ATM_IV)
        """
        try:
            if atm_iv == 0:
                return 0.0
            
            all_ivs = list(call_ivs.values()) + list(put_ivs.values())
            
            # 計算最大偏離
            max_dev = max(abs(iv - atm_iv) / atm_iv for iv in all_ivs) if all_ivs else 0
            
            # 標準化到 0-1
            steepness = min(1.0, max_dev)
            return steepness
        except Exception as e:
            logger.debug(f"計算陡峭度失敗: {e}")
            return 0.0
    
    def _create_moneyness_buckets(
        self,
        calls_data: List[Dict],
        puts_data: List[Dict],
        current_price: float,
        atm_strike: float
    ) -> List[MoneynessBucket]:
        """
        按 Moneyness 分組期權數據
        """
        buckets = []
        
        try:
            # 構建 strike -> option 的映射
            call_map = {opt.get('strike'): opt for opt in calls_data}
            put_map = {opt.get('strike'): opt for opt in puts_data}
            
            # 為每個 Moneyness 層級創建 bucket
            for moneyness_pct, label in self.MONEYNESS_GROUPS:
                target_strike = current_price * moneyness_pct
                
                # 找最接近的 Call 和 Put
                closest_call = self._find_closest_option(call_map, target_strike)
                closest_put = self._find_closest_option(put_map, target_strike)
                
                if closest_call is not None or closest_put is not None:
                    strikes = []
                    call_iv = None
                    put_iv = None
                    call_volume = 0
                    put_volume = 0
                    
                    if closest_call:
                        call_iv = self._normalize_iv(closest_call.get('impliedVolatility', 0))
                        call_volume = closest_call.get('volume', 0) or 0
                        strikes.append(closest_call.get('strike'))
                    
                    if closest_put:
                        put_iv = self._normalize_iv(closest_put.get('impliedVolatility', 0))
                        put_volume = closest_put.get('volume', 0) or 0
                        strikes.append(closest_put.get('strike'))
                    
                    # 計算平均 IV
                    iv_values = [iv for iv in [call_iv, put_iv] if iv is not None]
                    avg_iv = sum(iv_values) / len(iv_values) if iv_values else None
                    
                    bucket = MoneynessBucket(
                        moneyness_pct=moneyness_pct,
                        strikes=strikes,
                        call_iv=call_iv,
                        put_iv=put_iv,
                        avg_iv=avg_iv,
                        call_volume=call_volume,
                        put_volume=put_volume
                    )
                    buckets.append(bucket)
            
            return buckets
        except Exception as e:
            logger.debug(f"創建 Moneyness Buckets 失敗: {e}")
            return []
    
    def _find_closest_iv(self, iv_data: Dict[float, float], target_strike: float) -> Optional[float]:
        """
        找到最接近目標行使價的 IV
        """
        if not iv_data:
            return None
        
        min_distance = float('inf')
        closest_iv = None
        
        for strike, iv in iv_data.items():
            distance = abs(strike - target_strike)
            if distance < min_distance:
                min_distance = distance
                closest_iv = iv
        
        return closest_iv
    
    def _find_closest_option(self, option_map: Dict, target_strike: float) -> Optional[Dict]:
        """
        找到最接近目標行使價的期權
        """
        if not option_map:
            return None
        
        min_distance = float('inf')
        closest_option = None
        
        for strike, opt in option_map.items():
            distance = abs(strike - target_strike)
            if distance < min_distance:
                min_distance = distance
                closest_option = opt
        
        return closest_option
    
    def _normalize_iv(self, iv_raw: float) -> Optional[float]:
        """
        標準化 IV 為小數形式
        """
        if iv_raw is None or iv_raw == 0:
            return None
        
        if iv_raw > 1.0:  # 百分比形式
            return iv_raw / 100.0
        else:
            return iv_raw
    
    def _calculate_std(self, values: List[float], mean: float) -> float:
        """
        計算標準差
        """
        if len(values) <= 1:
            return 0.0
        
        variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
        return math.sqrt(variance)
    
    def _assess_iv_environment(self, steepness: float, skew: float, smile_shape: str) -> str:
        """
        評估 IV 環境類型
        """
        if steepness > self.STEEP_SMILE_THRESHOLD:
            if smile_shape == "smile":
                return "steep_smile"
            else:
                return "steep_smile"  # 簡化版
        elif abs(skew) < self.FLAT_IV_THRESHOLD:
            return "flat_iv"
        elif skew > 0:
            return "put_skew"
        else:
            return "call_skew"
    
    def _detect_pricing_anomalies(
        self,
        call_ivs: Dict[float, float],
        put_ivs: Dict[float, float],
        atm_iv: float,
        call_std: float,
        put_std: float
    ) -> List[Dict]:
        """
        檢測定價異常
        
        標準: 偏離平均值超過 1.5 倍標準差
        """
        anomalies = []
        threshold = 1.5
        
        try:
            # 檢查 Call IV 異常
            for strike, iv in call_ivs.items():
                if call_std > 0 and abs(iv - atm_iv) > threshold * call_std:
                    anomalies.append({
                        'strike': round(strike, 2),
                        'type': 'call',
                        'iv': round(iv * 100, 2),
                        'deviation_std': round(abs(iv - atm_iv) / call_std, 2) if call_std > 0 else 0,
                        'severity': 'high' if abs(iv - atm_iv) > 2 * call_std else 'medium'
                    })
            
            # 檢查 Put IV 異常
            for strike, iv in put_ivs.items():
                if put_std > 0 and abs(iv - atm_iv) > threshold * put_std:
                    anomalies.append({
                        'strike': round(strike, 2),
                        'type': 'put',
                        'iv': round(iv * 100, 2),
                        'deviation_std': round(abs(iv - atm_iv) / put_std, 2) if put_std > 0 else 0,
                        'severity': 'high' if abs(iv - atm_iv) > 2 * put_std else 'medium'
                    })
            
            return anomalies
        except Exception as e:
            logger.debug(f"檢測定價異常失敗: {e}")
            return []
    
    def _generate_recommendations(self, result: VolatilitySmileResult) -> Tuple[List[str], float]:
        """
        生成交易建議
        
        返回: (建議列表, 信心度 0-1)
        """
        recommendations = []
        confidence = 0.5
        
        try:
            # 基於 IV 環境的建議
            if result.iv_environment == "steep_smile":
                recommendations.append("IV 微笑陡峭 - 考慮 Strangle/Straddle 策略")
                confidence = 0.7
            elif result.iv_environment == "put_skew":
                recommendations.append("看跌傾斜（股票典型）- Put 定價相對較高")
                recommendations.append("考慮 Call Spread 或 Call Ratio Spread")
                confidence = 0.75
            elif result.iv_environment == "call_skew":
                recommendations.append("看漲傾斜（指數典型）- Call 定價相對較高")
                recommendations.append("考慮 Put Spread 或 Put Ratio Spread")
                confidence = 0.75
            elif result.iv_environment == "flat_iv":
                recommendations.append("IV 環境平坦 - 方向性策略可行")
                confidence = 0.65
            
            # 基於定價異常的建議
            if result.anomaly_count > 0:
                high_severity = sum(1 for a in result.pricing_anomalies if a.get('severity') == 'high')
                if high_severity > 0:
                    recommendations.append(f"檢測到 {high_severity} 個定價異常 - 尋找套利機會")
                    confidence = min(0.9, confidence + 0.15)
            
            # 基於 Skew 的建議
            if abs(result.skew) > 0.10:
                if result.skew > 0:
                    recommendations.append("Put IV 遠高於 Call IV - 考慮買入 Call / 賣出 Put")
                else:
                    recommendations.append("Call IV 遠高於 Put IV - 考慮買入 Put / 賣出 Call")
                confidence = min(0.9, confidence + 0.1)
            
            # 基於 Smile 的建議
            if result.smile_curve > 0.08:
                recommendations.append("IV 微笑明顯 - 雙邊期權溢價較高，適合 Iron Butterfly")
                confidence = 0.75
            
            if not recommendations:
                recommendations.append("IV 環境普通 - 根據技術分析進行交易")
                confidence = 0.5
            
            return recommendations, min(1.0, confidence)
        except Exception as e:
            logger.debug(f"生成建議失敗: {e}")
            return ["無法生成建議"], 0.3
    
    def _create_empty_result(self, current_price: float) -> VolatilitySmileResult:
        """
        創建空結果
        """
        return VolatilitySmileResult(
            atm_strike=current_price,
            atm_iv=0.30,
            current_price=current_price,
            calculation_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
