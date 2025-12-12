# utils/validation.py
"""
數據驗證工具

提供 Greeks、IV、期權數據的驗證功能
"""

import logging
import math
from typing import Dict, Tuple, Any, Optional

logger = logging.getLogger(__name__)


class GreeksValidator:
    """
    Greeks 驗證器
    
    驗證 Delta, Gamma, Theta, Vega, Rho 是否在合理範圍內
    """
    
    # Greeks 合理範圍定義
    VALID_RANGES = {
        'delta': (-1.0, 1.0),           # Delta 必須在 [-1, 1]
        'gamma': (0.0, 1.0),            # Gamma 必須 >= 0，通常 < 1
        'theta': (-100.0, 100.0),       # Theta 可正可負，但不應太極端
        'vega': (0.0, 10.0),            # Vega 必須 >= 0（修復後的正確範圍）
        'rho': (-50.0, 50.0),           # Rho 可正可負
    }
    
    # 警告閾值（超過這些值會發出警告但不視為無效）
    WARNING_THRESHOLDS = {
        'gamma': 0.5,                   # Gamma > 0.5 可能是極端情況
        'theta': 50.0,                  # |Theta| > 50 可能是極端情況
        'vega': 5.0,                    # Vega > 5 可能是極端情況
    }
    
    @classmethod
    def validate_greek(cls, value: float, greek_name: str) -> Tuple[bool, str]:
        """
        驗證單個 Greek 值
        
        參數:
            value: Greek 值
            greek_name: Greek 名稱 ('delta', 'gamma', 'theta', 'vega', 'rho')
        
        返回:
            Tuple[bool, str]: (是否有效, 訊息)
        """
        greek_name = greek_name.lower()
        
        # 檢查是否為有效數值
        if value is None:
            return False, f"{greek_name} 為 None"
        
        if math.isnan(value) or math.isinf(value):
            return False, f"{greek_name} 為 NaN 或 Inf: {value}"
        
        # 檢查範圍
        if greek_name not in cls.VALID_RANGES:
            return True, f"未知的 Greek: {greek_name}，跳過驗證"
        
        min_val, max_val = cls.VALID_RANGES[greek_name]
        
        if not (min_val <= value <= max_val):
            return False, f"{greek_name} = {value:.6f} 超出合理範圍 [{min_val}, {max_val}]"
        
        # 檢查警告閾值
        if greek_name in cls.WARNING_THRESHOLDS:
            threshold = cls.WARNING_THRESHOLDS[greek_name]
            if abs(value) > threshold:
                logger.warning(f"⚠ {greek_name} = {value:.6f} 超過警告閾值 {threshold}")
        
        return True, "OK"
    
    @classmethod
    def validate_greeks(cls, greeks: Dict[str, float]) -> Dict[str, Any]:
        """
        驗證所有 Greeks
        
        參數:
            greeks: {'delta': float, 'gamma': float, 'theta': float, 'vega': float, 'rho': float}
        
        返回:
            dict: {
                'is_valid': bool,
                'invalid_greeks': list,
                'warnings': list,
                'details': dict
            }
        """
        result = {
            'is_valid': True,
            'invalid_greeks': [],
            'warnings': [],
            'details': {}
        }
        
        for greek_name, value in greeks.items():
            is_valid, msg = cls.validate_greek(value, greek_name)
            result['details'][greek_name] = {'value': value, 'valid': is_valid, 'message': msg}
            
            if not is_valid:
                result['is_valid'] = False
                result['invalid_greeks'].append(greek_name)
                logger.error(f"✗ Greeks 驗證失敗: {msg}")
            elif msg != "OK":
                result['warnings'].append(msg)
        
        return result


class BidAskEstimator:
    """
    Bid/Ask 估算器
    
    當期權缺失 bid/ask 數據時，根據市場價格和流動性進行估算
    """
    
    # 基礎價差比例（根據期權價格）
    BASE_SPREAD_RATIOS = {
        'low_price': 0.05,      # 期權價 < $1: 5% 價差
        'medium_price': 0.02,   # 期權價 $1-$10: 2% 價差
        'high_price': 0.01,     # 期權價 > $10: 1% 價差
    }
    
    # 流動性調整因子
    LIQUIDITY_ADJUSTMENTS = {
        'high': 0.5,            # 高流動性：價差 × 0.5
        'medium': 1.0,          # 中等流動性：價差 × 1.0
        'low': 2.0,             # 低流動性：價差 × 2.0
        'very_low': 3.0,        # 極低流動性：價差 × 3.0
    }
    
    @classmethod
    def estimate_bid_ask(
        cls,
        market_price: Optional[float],
        open_interest: int = 0,
        volume: int = 0,
        option_type: str = 'call'
    ) -> Optional[Dict[str, Any]]:
        """
        估算 bid/ask 價格
        
        參數:
            market_price: 市場價格（last price 或理論價格）
            open_interest: 未平倉量
            volume: 成交量
            option_type: 'call' 或 'put'
        
        返回:
            dict: {
                'bid': float,
                'ask': float,
                'spread': float,
                'spread_pct': float,
                'is_estimated': True,
                'liquidity_level': str
            }
        """
        if market_price is None or market_price <= 0:
            return None
        
        # 1. 確定基礎價差比例
        if market_price < 1.0:
            base_spread_ratio = cls.BASE_SPREAD_RATIOS['low_price']
        elif market_price < 10.0:
            base_spread_ratio = cls.BASE_SPREAD_RATIOS['medium_price']
        else:
            base_spread_ratio = cls.BASE_SPREAD_RATIOS['high_price']
        
        # 2. 計算流動性指標
        liquidity_score = cls._calculate_liquidity_score(open_interest, volume)
        liquidity_level, liquidity_adjustment = cls._get_liquidity_adjustment(liquidity_score)
        
        # 3. 計算調整後的價差
        spread = market_price * base_spread_ratio * liquidity_adjustment
        spread = max(0.01, spread)  # 最小價差 $0.01
        
        # 4. 計算 bid/ask
        half_spread = spread / 2
        bid = max(0.01, round(market_price - half_spread, 2))
        ask = max(bid + 0.01, round(market_price + half_spread, 2))
        
        # 5. 重新計算實際價差
        actual_spread = ask - bid
        spread_pct = (actual_spread / market_price) * 100 if market_price > 0 else 0
        
        result = {
            'bid': bid,
            'ask': ask,
            'mid': round((bid + ask) / 2, 2),
            'spread': round(actual_spread, 2),
            'spread_pct': round(spread_pct, 2),
            'is_estimated': True,
            'liquidity_level': liquidity_level,
            'liquidity_score': round(liquidity_score, 2)
        }
        
        logger.debug(f"  估算 bid/ask: ${bid:.2f}/${ask:.2f} (價差 {spread_pct:.1f}%, 流動性: {liquidity_level})")
        
        return result
    
    @classmethod
    def _calculate_liquidity_score(cls, open_interest: int, volume: int) -> float:
        """
        計算流動性分數 (0-1)
        
        基於未平倉量和成交量
        """
        # 未平倉量分數 (0-0.6)
        if open_interest >= 10000:
            oi_score = 0.6
        elif open_interest >= 1000:
            oi_score = 0.4
        elif open_interest >= 100:
            oi_score = 0.2
        else:
            oi_score = 0.1
        
        # 成交量分數 (0-0.4)
        if volume >= 1000:
            vol_score = 0.4
        elif volume >= 100:
            vol_score = 0.3
        elif volume >= 10:
            vol_score = 0.2
        else:
            vol_score = 0.1
        
        return oi_score + vol_score
    
    @classmethod
    def _get_liquidity_adjustment(cls, liquidity_score: float) -> Tuple[str, float]:
        """
        根據流動性分數獲取調整因子
        """
        if liquidity_score >= 0.8:
            return 'high', cls.LIQUIDITY_ADJUSTMENTS['high']
        elif liquidity_score >= 0.5:
            return 'medium', cls.LIQUIDITY_ADJUSTMENTS['medium']
        elif liquidity_score >= 0.3:
            return 'low', cls.LIQUIDITY_ADJUSTMENTS['low']
        else:
            return 'very_low', cls.LIQUIDITY_ADJUSTMENTS['very_low']


def process_option_with_fallback(
    option_data: Dict[str, Any],
    theoretical_price: Optional[float] = None
) -> Dict[str, Any]:
    """
    處理期權數據，包含 bid/ask 容錯
    
    如果 bid/ask 缺失，使用估算值填補
    
    參數:
        option_data: 原始期權數據
        theoretical_price: 理論價格（用於估算）
    
    返回:
        dict: 處理後的期權數據
    """
    result = option_data.copy()
    
    bid = option_data.get('bid')
    ask = option_data.get('ask')
    
    # 檢查是否需要估算
    needs_estimation = (
        bid is None or ask is None or
        bid <= 0 or ask <= 0 or
        (isinstance(bid, float) and math.isnan(bid)) or
        (isinstance(ask, float) and math.isnan(ask))
    )
    
    if needs_estimation:
        # 確定市場價格
        market_price = (
            option_data.get('lastPrice') or
            option_data.get('last') or
            theoretical_price
        )
        
        if market_price and market_price > 0:
            estimated = BidAskEstimator.estimate_bid_ask(
                market_price=market_price,
                open_interest=option_data.get('openInterest', 0) or 0,
                volume=option_data.get('volume', 0) or 0,
                option_type=option_data.get('option_type', 'call')
            )
            
            if estimated:
                result['bid'] = estimated['bid']
                result['ask'] = estimated['ask']
                result['spread'] = estimated['spread']
                result['bid_ask_estimated'] = True
                result['liquidity_level'] = estimated['liquidity_level']
                
                strike = option_data.get('strike', 'N/A')
                logger.info(f"  Strike ${strike}: 使用估算 bid/ask (${estimated['bid']:.2f}/${estimated['ask']:.2f})")
    
    return result


# 測試代碼
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    print("=" * 60)
    print("Greeks 驗證測試")
    print("=" * 60)
    
    # 測試 Greeks 驗證
    test_greeks = {
        'delta': 0.5,
        'gamma': 0.02,
        'theta': -0.28,
        'vega': 0.25,
        'rho': 5.0
    }
    
    result = GreeksValidator.validate_greeks(test_greeks)
    print(f"驗證結果: {result['is_valid']}")
    print(f"詳情: {result['details']}")
    
    # 測試無效 Greeks
    invalid_greeks = {
        'delta': 1.5,  # 超出範圍
        'gamma': -0.1,  # 負數
        'vega': 100.0,  # 太大
    }
    
    result = GreeksValidator.validate_greeks(invalid_greeks)
    print(f"\n無效 Greeks 驗證: {result['is_valid']}")
    print(f"無效項: {result['invalid_greeks']}")
    
    print("\n" + "=" * 60)
    print("Bid/Ask 估算測試")
    print("=" * 60)
    
    # 測試 bid/ask 估算
    test_cases = [
        {'market_price': 7.06, 'open_interest': 1138, 'volume': 41},
        {'market_price': 0.50, 'open_interest': 50, 'volume': 5},
        {'market_price': 25.00, 'open_interest': 5000, 'volume': 500},
    ]
    
    for case in test_cases:
        result = BidAskEstimator.estimate_bid_ask(**case)
        print(f"\n市場價 ${case['market_price']:.2f}, OI={case['open_interest']}, Vol={case['volume']}")
        print(f"  估算: bid=${result['bid']:.2f}, ask=${result['ask']:.2f}, 價差={result['spread_pct']:.1f}%")
        print(f"  流動性: {result['liquidity_level']}")
