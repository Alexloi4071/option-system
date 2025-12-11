# calculation_layer/module24_technical_direction.py
"""
模塊24: 技術方向分析 (Technical Direction Analysis)

功能:
- 日線趨勢分析（30-90天期權方向）
- 15分鐘入場信號（日內交易時機）
- 綜合方向判斷（Call/Put決策）

數據來源: Finnhub API (優先) → Yahoo Finance (降級)

Requirements: 1.1-1.4, 2.1-2.4, 3.1-3.4
"""

import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


# ==================== 指標配置 ====================

DAILY_CONFIG = {
    'resolution': 'D',
    'rsi_period': 14,
    'macd': {'fast': 12, 'slow': 26, 'signal': 9},
    'sma_periods': [20, 50, 200],
    'adx_period': 14,
    'lookback_days': 200
}

INTRADAY_CONFIG = {
    'resolution': '15',
    'rsi_period': 9,
    'macd': {'fast': 5, 'slow': 13, 'signal': 3},
    'ema_periods': [9, 21],
    'stochastic': {'k': 5, 'd': 3, 'smooth': 3},
    'bollinger': {'period': 20, 'std': 2},
    'lookback_days': 5
}


# ==================== 數據結構 ====================

@dataclass
class DailyTrendResult:
    """日線趨勢結果"""
    trend: str  # 'Bullish' | 'Bearish' | 'Neutral'
    rsi: Optional[float] = None
    macd: Dict[str, float] = field(default_factory=dict)
    sma: Dict[str, float] = field(default_factory=dict)
    adx: Optional[float] = None
    price: Optional[float] = None
    price_vs_sma: Dict[str, bool] = field(default_factory=dict)
    signals: List[str] = field(default_factory=list)
    score: float = 0.0  # -100 到 +100
    
    def to_dict(self) -> Dict:
        return {
            'trend': self.trend,
            'rsi': round(self.rsi, 2) if self.rsi else None,
            'macd': {k: round(v, 4) if v else None for k, v in self.macd.items()},
            'sma': {k: round(v, 2) if v else None for k, v in self.sma.items()},
            'adx': round(self.adx, 2) if self.adx else None,
            'price': round(self.price, 2) if self.price else None,
            'price_vs_sma': self.price_vs_sma,
            'signals': self.signals,
            'score': round(self.score, 2)
        }


@dataclass
class IntradaySignalResult:
    """15分鐘入場信號結果"""
    signal: str  # 'Enter' | 'Wait_Pullback' | 'Wait_Breakout' | 'Hold'
    rsi: Optional[float] = None
    macd: Dict[str, float] = field(default_factory=dict)
    stochastic: Dict[str, float] = field(default_factory=dict)
    ema: Dict[str, float] = field(default_factory=dict)
    bollinger: Dict[str, float] = field(default_factory=dict)
    price: Optional[float] = None
    signals: List[str] = field(default_factory=list)
    available: bool = True
    
    def to_dict(self) -> Dict:
        return {
            'signal': self.signal,
            'rsi': round(self.rsi, 2) if self.rsi else None,
            'macd': {k: round(v, 4) if v else None for k, v in self.macd.items()},
            'stochastic': {k: round(v, 2) if v else None for k, v in self.stochastic.items()},
            'ema': {k: round(v, 2) if v else None for k, v in self.ema.items()},
            'bollinger': {k: round(v, 2) if v else None for k, v in self.bollinger.items()},
            'price': round(self.price, 2) if self.price else None,
            'signals': self.signals,
            'available': self.available
        }


@dataclass
class TechnicalDirectionResult:
    """技術方向分析結果"""
    ticker: str
    daily_trend: DailyTrendResult
    intraday_signal: IntradaySignalResult
    combined_direction: str  # 'Call' | 'Put' | 'Neutral'
    confidence: str  # 'High' | 'Medium' | 'Low'
    recommendation: str
    entry_timing: str  # 入場時機建議
    calculation_date: str
    data_source: str = 'Finnhub'
    
    def to_dict(self) -> Dict:
        return {
            'ticker': self.ticker,
            'daily_trend': self.daily_trend.to_dict(),
            'intraday_signal': self.intraday_signal.to_dict(),
            'combined_direction': self.combined_direction,
            'confidence': self.confidence,
            'recommendation': self.recommendation,
            'entry_timing': self.entry_timing,
            'calculation_date': self.calculation_date,
            'data_source': self.data_source
        }


# ==================== 技術指標計算 ====================

class TechnicalIndicators:
    """技術指標計算工具類"""
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> Optional[float]:
        """
        計算 RSI (Relative Strength Index) - 使用 Wilder's Smoothing Method
        
        參數:
            prices: 收盤價序列
            period: RSI 週期
        
        返回:
            RSI 值 (0-100)
        
        注意: 使用 Wilder's Smoothing (EMA with alpha=1/period) 以匹配
              TradingView、Yahoo Finance 等主流平台的計算方式
        """
        try:
            if len(prices) < period + 1:
                return None
            
            delta = prices.diff()
            gain = delta.where(delta > 0, 0.0)
            loss = (-delta).where(delta < 0, 0.0)
            
            # 使用 Wilder's Smoothing Method (EMA with alpha = 1/period)
            # 這是標準 RSI 計算方式，與 TradingView 等平台一致
            alpha = 1.0 / period
            avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
            avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()
            
            # 避免除以零
            rs = avg_gain / avg_loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))
            
            return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None
        except Exception as e:
            logger.warning(f"RSI 計算失敗: {e}")
            return None
    
    @staticmethod
    def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, 
                       signal: int = 9) -> Dict[str, Optional[float]]:
        """
        計算 MACD
        
        返回:
            {'macd': float, 'signal': float, 'histogram': float}
        """
        try:
            if len(prices) < slow + signal:
                return {'macd': None, 'signal': None, 'histogram': None}
            
            ema_fast = prices.ewm(span=fast, adjust=False).mean()
            ema_slow = prices.ewm(span=slow, adjust=False).mean()
            
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal, adjust=False).mean()
            histogram = macd_line - signal_line
            
            return {
                'macd': float(macd_line.iloc[-1]) if not pd.isna(macd_line.iloc[-1]) else None,
                'signal': float(signal_line.iloc[-1]) if not pd.isna(signal_line.iloc[-1]) else None,
                'histogram': float(histogram.iloc[-1]) if not pd.isna(histogram.iloc[-1]) else None
            }
        except Exception as e:
            logger.warning(f"MACD 計算失敗: {e}")
            return {'macd': None, 'signal': None, 'histogram': None}
    
    @staticmethod
    def calculate_sma(prices: pd.Series, period: int) -> Optional[float]:
        """計算 SMA"""
        try:
            if len(prices) < period:
                return None
            sma = prices.rolling(window=period).mean()
            return float(sma.iloc[-1]) if not pd.isna(sma.iloc[-1]) else None
        except Exception as e:
            logger.warning(f"SMA({period}) 計算失敗: {e}")
            return None
    
    @staticmethod
    def calculate_ema(prices: pd.Series, period: int) -> Optional[float]:
        """計算 EMA"""
        try:
            if len(prices) < period:
                return None
            ema = prices.ewm(span=period, adjust=False).mean()
            return float(ema.iloc[-1]) if not pd.isna(ema.iloc[-1]) else None
        except Exception as e:
            logger.warning(f"EMA({period}) 計算失敗: {e}")
            return None
    
    @staticmethod
    def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
                            k_period: int = 5, d_period: int = 3, 
                            smooth: int = 3) -> Dict[str, Optional[float]]:
        """
        計算 Stochastic 隨機指標
        
        返回:
            {'k': float, 'd': float}
        """
        try:
            if len(close) < k_period + d_period:
                return {'k': None, 'd': None}
            
            lowest_low = low.rolling(window=k_period).min()
            highest_high = high.rolling(window=k_period).max()
            
            stoch_k = 100 * (close - lowest_low) / (highest_high - lowest_low)
            stoch_k = stoch_k.rolling(window=smooth).mean()  # Smooth %K
            stoch_d = stoch_k.rolling(window=d_period).mean()
            
            return {
                'k': float(stoch_k.iloc[-1]) if not pd.isna(stoch_k.iloc[-1]) else None,
                'd': float(stoch_d.iloc[-1]) if not pd.isna(stoch_d.iloc[-1]) else None
            }
        except Exception as e:
            logger.warning(f"Stochastic 計算失敗: {e}")
            return {'k': None, 'd': None}
    
    @staticmethod
    def calculate_bollinger_bands(prices: pd.Series, period: int = 20, 
                                  std_dev: float = 2.0) -> Dict[str, Optional[float]]:
        """
        計算 Bollinger Bands
        
        返回:
            {'upper': float, 'middle': float, 'lower': float}
        """
        try:
            if len(prices) < period:
                return {'upper': None, 'middle': None, 'lower': None}
            
            middle = prices.rolling(window=period).mean()
            std = prices.rolling(window=period).std()
            
            upper = middle + (std * std_dev)
            lower = middle - (std * std_dev)
            
            return {
                'upper': float(upper.iloc[-1]) if not pd.isna(upper.iloc[-1]) else None,
                'middle': float(middle.iloc[-1]) if not pd.isna(middle.iloc[-1]) else None,
                'lower': float(lower.iloc[-1]) if not pd.isna(lower.iloc[-1]) else None
            }
        except Exception as e:
            logger.warning(f"Bollinger Bands 計算失敗: {e}")
            return {'upper': None, 'middle': None, 'lower': None}
    
    @staticmethod
    def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series,
                     period: int = 14) -> Optional[float]:
        """
        計算 ADX (Average Directional Index)
        
        返回:
            ADX 值
        """
        try:
            if len(close) < period * 2:
                return None
            
            # True Range
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # Directional Movement
            up_move = high - high.shift(1)
            down_move = low.shift(1) - low
            
            plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
            minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
            
            # Smoothed averages
            atr = tr.rolling(window=period).mean()
            plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
            minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
            
            # ADX
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            adx = dx.rolling(window=period).mean()
            
            return float(adx.iloc[-1]) if not pd.isna(adx.iloc[-1]) else None
        except Exception as e:
            logger.warning(f"ADX 計算失敗: {e}")
            return None


# ==================== 技術方向分析器 ====================

class TechnicalDirectionAnalyzer:
    """
    Module 24: 技術方向分析器
    
    功能:
    - 日線趨勢分析（30-90天期權方向）
    - 15分鐘入場信號（日內交易時機）
    - 綜合方向判斷（Call/Put決策）
    """
    
    def __init__(self):
        """初始化技術方向分析器"""
        self.indicators = TechnicalIndicators()
        logger.info("* Module 24 技術方向分析器已初始化")
    
    def analyze(self, ticker: str, daily_data: pd.DataFrame,
                intraday_data: pd.DataFrame = None,
                current_price: float = None) -> TechnicalDirectionResult:
        """
        主分析方法
        
        參數:
            ticker: 股票代碼
            daily_data: 日線數據 (需包含 Open, High, Low, Close, Volume)
            intraday_data: 15分鐘數據 (可選)
            current_price: 當前價格 (可選，用於補充)
        
        返回:
            TechnicalDirectionResult
        """
        logger.info(f"開始 {ticker} 技術方向分析...")
        
        calculation_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 1. 日線趨勢分析
        daily_trend = self.analyze_daily_trend(daily_data, current_price)
        logger.info(f"  日線趨勢: {daily_trend.trend} (得分: {daily_trend.score})")
        
        # 2. 15分鐘入場信號分析
        if intraday_data is not None and len(intraday_data) >= 20:
            intraday_signal = self.analyze_intraday_signal(intraday_data, daily_trend.trend)
            logger.info(f"  15分鐘信號: {intraday_signal.signal}")
        else:
            intraday_signal = IntradaySignalResult(
                signal='N/A',
                signals=['15分鐘數據不可用'],
                available=False
            )
            logger.info("  15分鐘數據不可用，僅使用日線分析")
        
        # 3. 綜合方向判斷
        combined_direction, confidence, recommendation, entry_timing = \
            self.get_combined_direction(daily_trend, intraday_signal)
        
        logger.info(f"  綜合方向: {combined_direction} ({confidence})")
        logger.info(f"* Module 24 分析完成")
        
        return TechnicalDirectionResult(
            ticker=ticker,
            daily_trend=daily_trend,
            intraday_signal=intraday_signal,
            combined_direction=combined_direction,
            confidence=confidence,
            recommendation=recommendation,
            entry_timing=entry_timing,
            calculation_date=calculation_date
        )
    
    def analyze_daily_trend(self, data: pd.DataFrame, 
                           current_price: float = None) -> DailyTrendResult:
        """
        日線趨勢分析
        
        判斷邏輯:
        - 價格 vs SMA 50/200 位置
        - MACD 方向和金叉/死叉
        - RSI 超買超賣
        - ADX 趨勢強度
        """
        signals = []
        score = 0.0  # -100 到 +100
        
        if data is None or len(data) < 50:
            return DailyTrendResult(
                trend='Neutral',
                signals=['數據不足，無法分析'],
                score=0
            )
        
        close = data['Close']
        high = data['High']
        low = data['Low']
        price = current_price or float(close.iloc[-1])
        
        # 計算指標
        rsi = self.indicators.calculate_rsi(close, DAILY_CONFIG['rsi_period'])
        macd = self.indicators.calculate_macd(
            close, 
            DAILY_CONFIG['macd']['fast'],
            DAILY_CONFIG['macd']['slow'],
            DAILY_CONFIG['macd']['signal']
        )
        
        sma = {}
        price_vs_sma = {}
        for period in DAILY_CONFIG['sma_periods']:
            sma[f'sma{period}'] = self.indicators.calculate_sma(close, period)
            if sma[f'sma{period}']:
                price_vs_sma[f'above_sma{period}'] = price > sma[f'sma{period}']
        
        adx = self.indicators.calculate_adx(high, low, close, DAILY_CONFIG['adx_period'])
        
        # === 評分邏輯 ===
        
        # 1. RSI 評分 (權重 20%)
        if rsi:
            if rsi < 30:
                score += 15  # 超賣，看漲
                signals.append(f"RSI {rsi:.1f} 超賣，可能反彈")
            elif rsi > 70:
                score -= 15  # 超買，看跌
                signals.append(f"RSI {rsi:.1f} 超買，可能回調")
            elif rsi > 50:
                score += 5
                signals.append(f"RSI {rsi:.1f} 偏強")
            else:
                score -= 5
                signals.append(f"RSI {rsi:.1f} 偏弱")
        
        # 2. MACD 評分 (權重 30%)
        if macd['histogram'] is not None:
            if macd['histogram'] > 0:
                score += 20
                if macd['macd'] > macd['signal']:
                    signals.append("MACD 金叉，動量向上")
                else:
                    signals.append("MACD 柱狀圖為正")
            else:
                score -= 20
                if macd['macd'] < macd['signal']:
                    signals.append("MACD 死叉，動量向下")
                else:
                    signals.append("MACD 柱狀圖為負")
        
        # 3. 均線系統評分 (權重 35%)
        if price_vs_sma.get('above_sma200'):
            score += 15
            signals.append(f"價格在 SMA 200 之上（長期上升趨勢）")
        else:
            score -= 15
            signals.append(f"價格在 SMA 200 之下（長期下降趨勢）")
        
        if price_vs_sma.get('above_sma50'):
            score += 10
            signals.append(f"價格在 SMA 50 之上（中期上升）")
        else:
            score -= 10
            signals.append(f"價格在 SMA 50 之下（中期下降）")
        
        if price_vs_sma.get('above_sma20'):
            score += 5
            signals.append(f"價格在 SMA 20 之上（短期上升）")
        else:
            score -= 5
            signals.append(f"價格在 SMA 20 之下（短期下降）")
        
        # 4. ADX 趨勢強度 (權重 15%)
        if adx:
            if adx > 25:
                signals.append(f"ADX {adx:.1f} 趨勢明確")
                # ADX 只影響信心度，不影響方向
            else:
                signals.append(f"ADX {adx:.1f} 趨勢不明確")
        
        # 確定趨勢方向
        if score >= 25:
            trend = 'Bullish'
        elif score <= -25:
            trend = 'Bearish'
        else:
            trend = 'Neutral'
        
        return DailyTrendResult(
            trend=trend,
            rsi=rsi,
            macd=macd,
            sma=sma,
            adx=adx,
            price=price,
            price_vs_sma=price_vs_sma,
            signals=signals,
            score=score
        )
    
    def analyze_intraday_signal(self, data: pd.DataFrame,
                                daily_trend: str) -> IntradaySignalResult:
        """
        15分鐘入場信號分析
        
        判斷邏輯:
        - RSI 超買超賣
        - MACD 金叉/死叉
        - Stochastic 超買超賣
        - Bollinger Bands 位置
        """
        signals = []
        
        if data is None or len(data) < 20:
            return IntradaySignalResult(
                signal='N/A',
                signals=['數據不足'],
                available=False
            )
        
        close = data['Close']
        high = data['High']
        low = data['Low']
        price = float(close.iloc[-1])
        
        # 計算指標
        rsi = self.indicators.calculate_rsi(close, INTRADAY_CONFIG['rsi_period'])
        macd = self.indicators.calculate_macd(
            close,
            INTRADAY_CONFIG['macd']['fast'],
            INTRADAY_CONFIG['macd']['slow'],
            INTRADAY_CONFIG['macd']['signal']
        )
        stochastic = self.indicators.calculate_stochastic(
            high, low, close,
            INTRADAY_CONFIG['stochastic']['k'],
            INTRADAY_CONFIG['stochastic']['d'],
            INTRADAY_CONFIG['stochastic']['smooth']
        )
        
        ema = {}
        for period in INTRADAY_CONFIG['ema_periods']:
            ema[f'ema{period}'] = self.indicators.calculate_ema(close, period)
        
        bollinger = self.indicators.calculate_bollinger_bands(
            close,
            INTRADAY_CONFIG['bollinger']['period'],
            INTRADAY_CONFIG['bollinger']['std']
        )
        
        # === 入場信號判斷 ===
        overbought = False
        oversold = False
        
        # RSI 判斷
        if rsi:
            if rsi > 70:
                overbought = True
                signals.append(f"RSI {rsi:.1f} 短線超買")
            elif rsi < 30:
                oversold = True
                signals.append(f"RSI {rsi:.1f} 短線超賣")
            else:
                signals.append(f"RSI {rsi:.1f} 中性區間")
        
        # Stochastic 判斷
        if stochastic['k'] and stochastic['d']:
            if stochastic['k'] > 80:
                overbought = True
                signals.append(f"Stochastic K={stochastic['k']:.1f} 超買")
            elif stochastic['k'] < 20:
                oversold = True
                signals.append(f"Stochastic K={stochastic['k']:.1f} 超賣")
        
        # MACD 判斷
        macd_bullish = False
        macd_bearish = False
        if macd['histogram'] is not None:
            if macd['histogram'] > 0 and macd['macd'] > macd['signal']:
                macd_bullish = True
                signals.append("MACD 金叉")
            elif macd['histogram'] < 0 and macd['macd'] < macd['signal']:
                macd_bearish = True
                signals.append("MACD 死叉")
        
        # Bollinger Bands 判斷
        bb_position = 'middle'
        if bollinger['upper'] and bollinger['lower']:
            if price >= bollinger['upper']:
                bb_position = 'upper'
                signals.append("價格觸及布林帶上軌")
            elif price <= bollinger['lower']:
                bb_position = 'lower'
                signals.append("價格觸及布林帶下軌")
        
        # === 綜合入場信號 ===
        if daily_trend == 'Bullish':
            # 日線看漲，找做多入場點
            if oversold and macd_bullish:
                signal = 'Enter'
                signals.append("✓ 回調到位 + MACD 金叉，建議入場做多")
            elif overbought:
                signal = 'Wait_Pullback'
                signals.append("短線超買，等待回調再入場")
            elif macd_bullish:
                signal = 'Enter'
                signals.append("MACD 金叉，可以入場")
            else:
                signal = 'Wait_Pullback'
                signals.append("等待更好的入場點")
        
        elif daily_trend == 'Bearish':
            # 日線看跌，找做空入場點
            if overbought and macd_bearish:
                signal = 'Enter'
                signals.append("✓ 反彈到位 + MACD 死叉，建議入場做空")
            elif oversold:
                signal = 'Wait_Pullback'
                signals.append("短線超賣，等待反彈再入場")
            elif macd_bearish:
                signal = 'Enter'
                signals.append("MACD 死叉，可以入場")
            else:
                signal = 'Wait_Pullback'
                signals.append("等待更好的入場點")
        
        else:
            # 日線中性
            signal = 'Hold'
            signals.append("日線趨勢不明確，建議觀望")
        
        return IntradaySignalResult(
            signal=signal,
            rsi=rsi,
            macd=macd,
            stochastic=stochastic,
            ema=ema,
            bollinger=bollinger,
            price=price,
            signals=signals,
            available=True
        )
    
    def get_combined_direction(self, daily: DailyTrendResult,
                               intraday: IntradaySignalResult) -> tuple:
        """
        綜合方向判斷
        
        返回:
            (direction, confidence, recommendation, entry_timing)
        """
        # 基於日線趨勢確定方向
        if daily.trend == 'Bullish':
            direction = 'Call'
            base_recommendation = "技術面看漲，建議 Call 方向"
        elif daily.trend == 'Bearish':
            direction = 'Put'
            base_recommendation = "技術面看跌，建議 Put 方向"
        else:
            direction = 'Neutral'
            base_recommendation = "技術面中性，建議觀望或中性策略"
        
        # 確定信心度
        if abs(daily.score) >= 40:
            if daily.adx and daily.adx > 25:
                confidence = 'High'
            else:
                confidence = 'Medium'
        elif abs(daily.score) >= 20:
            confidence = 'Medium'
        else:
            confidence = 'Low'
        
        # 入場時機
        if not intraday.available:
            entry_timing = "15分鐘數據不可用，請自行判斷入場時機"
        elif intraday.signal == 'Enter':
            entry_timing = "技術指標顯示可以入場"
        elif intraday.signal == 'Wait_Pullback':
            entry_timing = "建議等待回調後再入場"
        elif intraday.signal == 'Wait_Breakout':
            entry_timing = "建議等待突破後再入場"
        else:
            entry_timing = "建議觀望，等待更明確的信號"
        
        # 完整建議
        recommendation = f"{base_recommendation}。{entry_timing}"
        
        return direction, confidence, recommendation, entry_timing


# 使用示例
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 創建測試數據
    dates = pd.date_range('2024-01-01', periods=200, freq='D')
    np.random.seed(42)
    
    # 模擬上升趨勢
    prices = 100 * np.exp(np.linspace(0, 0.3, 200) + np.random.randn(200) * 0.02)
    
    daily_data = pd.DataFrame({
        'Open': prices * 0.99,
        'High': prices * 1.02,
        'Low': prices * 0.98,
        'Close': prices,
        'Volume': np.random.randint(1000000, 5000000, 200)
    }, index=dates)
    
    # 測試
    analyzer = TechnicalDirectionAnalyzer()
    result = analyzer.analyze('TEST', daily_data)
    
    print("\n" + "=" * 70)
    print("技術方向分析測試結果")
    print("=" * 70)
    print(f"日線趨勢: {result.daily_trend.trend}")
    print(f"綜合方向: {result.combined_direction}")
    print(f"信心度: {result.confidence}")
    print(f"建議: {result.recommendation}")
    print("=" * 70)
