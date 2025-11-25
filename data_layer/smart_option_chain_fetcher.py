# data_layer/smart_option_chain_fetcher.py
"""
智能期權鏈獲取器 (Smart Option Chain Fetcher)
目的: 根據策略類型智能獲取期權鏈，減少API調用，提高性能

策略類型:
- simple: 簡單策略（Long Call/Put, Short Call/Put）- 只獲取ATM
- spread: 價差策略（Bull/Bear Spread, Iron Condor）- 獲取ATM ± 10%
- advanced: 高級分析（Greeks分析, Option Flow）- 獲取所有流動性好的期權

性能提升:
- simple策略：減少90%的API調用（1個行使價 vs 50個）
- spread策略：減少70%的API調用（5-10個 vs 50個）
- advanced策略：減少30%的API調用（只獲取流動性好的）
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OptionChainConfig:
    """期權鏈獲取配置"""
    strategy_type: str  # 'simple' | 'spread' | 'advanced'
    strikes_to_fetch: List[float]  # 要獲取的行使價列表
    total_available: int  # 總共可用的行使價數量
    reduction_percentage: float  # API調用減少百分比
    
    def to_dict(self) -> Dict:
        return {
            'strategy_type': self.strategy_type,
            'strikes_count': len(self.strikes_to_fetch),
            'strikes_to_fetch': [round(s, 2) for s in self.strikes_to_fetch],
            'total_available': self.total_available,
            'reduction_percentage': round(self.reduction_percentage, 2),
            'note': f'減少{self.reduction_percentage:.0f}%的API調用'
        }


class SmartOptionChainFetcher:
    """
    智能期權鏈獲取器
    
    功能:
    - 根據策略類型智能選擇行使價
    - 大幅減少API調用次數
    - 保持數據質量
    
    使用示例:
    >>> fetcher = SmartOptionChainFetcher()
    >>> config = fetcher.get_strikes_config(
    ...     current_price=175.0,
    ...     all_strikes=[150, 155, ..., 200],
    ...     strategy_type='simple'
    ... )
    >>> print(f"只需獲取 {len(config.strikes_to_fetch)} 個行使價")
    """
    
    # 策略配置
    STRATEGY_CONFIGS = {
        'simple': {
            'description': '簡單策略（Long/Short Call/Put）',
            'method': 'atm_only',
            'range_pct': 0.0,
            'expected_reduction': 90
        },
        'spread': {
            'description': '價差策略（Bull/Bear Spread, Iron Condor）',
            'method': 'atm_range',
            'range_pct': 0.10,  # ATM ± 10%
            'expected_reduction': 70
        },
        'advanced': {
            'description': '高級分析（Greeks, Option Flow）',
            'method': 'liquid_only',
            'min_volume': 10,
            'min_oi': 100,
            'expected_reduction': 30
        }
    }
    
    def __init__(self):
        """初始化智能期權鏈獲取器"""
        logger.info("* 智能期權鏈獲取器已初始化")
    
    def get_strikes_config(
        self,
        current_price: float,
        all_strikes: List[float],
        strategy_type: str = 'simple',
        option_data: Optional[Dict] = None
    ) -> OptionChainConfig:
        """
        獲取期權鏈配置
        
        參數:
            current_price: 當前股價
            all_strikes: 所有可用的行使價列表
            strategy_type: 策略類型（'simple' | 'spread' | 'advanced'）
            option_data: 期權數據（用於advanced策略的流動性篩選）
        
        返回:
            OptionChainConfig: 包含要獲取的行使價列表和統計信息
        """
        try:
            logger.info(f"開始計算期權鏈配置...")
            logger.info(f"  當前股價: ${current_price:.2f}")
            logger.info(f"  可用行使價數量: {len(all_strikes)}")
            logger.info(f"  策略類型: {strategy_type}")
            
            # 驗證策略類型
            if strategy_type not in self.STRATEGY_CONFIGS:
                logger.warning(f"! 未知策略類型: {strategy_type}，使用默認'simple'")
                strategy_type = 'simple'
            
            # 根據策略類型選擇行使價
            if strategy_type == 'simple':
                strikes_to_fetch = self._fetch_atm_only(current_price, all_strikes)
            
            elif strategy_type == 'spread':
                strikes_to_fetch = self._fetch_atm_range(
                    current_price,
                    all_strikes,
                    range_pct=self.STRATEGY_CONFIGS['spread']['range_pct']
                )
            
            elif strategy_type == 'advanced':
                strikes_to_fetch = self._fetch_liquid_only(
                    all_strikes,
                    option_data,
                    min_volume=self.STRATEGY_CONFIGS['advanced']['min_volume'],
                    min_oi=self.STRATEGY_CONFIGS['advanced']['min_oi']
                )
            
            else:
                strikes_to_fetch = self._fetch_atm_only(current_price, all_strikes)
            
            # 計算減少百分比
            if len(all_strikes) > 0:
                reduction_pct = (1 - len(strikes_to_fetch) / len(all_strikes)) * 100
            else:
                reduction_pct = 0.0
            
            logger.info(f"  選擇的行使價數量: {len(strikes_to_fetch)}")
            logger.info(f"  API調用減少: {reduction_pct:.1f}%")
            
            config = OptionChainConfig(
                strategy_type=strategy_type,
                strikes_to_fetch=strikes_to_fetch,
                total_available=len(all_strikes),
                reduction_percentage=reduction_pct
            )
            
            logger.info(f"* 期權鏈配置完成")
            return config
            
        except Exception as e:
            logger.error(f"x 期權鏈配置失敗: {e}")
            # 返回默認配置（ATM only）
            return OptionChainConfig(
                strategy_type='simple',
                strikes_to_fetch=self._fetch_atm_only(current_price, all_strikes),
                total_available=len(all_strikes),
                reduction_percentage=90.0
            )
    
    def _fetch_atm_only(
        self,
        current_price: float,
        all_strikes: List[float]
    ) -> List[float]:
        """
        策略1: 只獲取ATM行使價
        
        適用於: Long Call, Long Put, Short Call, Short Put
        
        返回: 1個行使價（最接近當前價格的）
        """
        if not all_strikes:
            return []
        
        # 找到最接近當前價格的行使價
        atm_strike = min(all_strikes, key=lambda x: abs(x - current_price))
        
        logger.debug(f"  ATM策略: 選擇 ${atm_strike:.2f} (最接近 ${current_price:.2f})")
        
        return [atm_strike]
    
    def _fetch_atm_range(
        self,
        current_price: float,
        all_strikes: List[float],
        range_pct: float = 0.10
    ) -> List[float]:
        """
        策略2: 獲取ATM ± range_pct範圍的行使價
        
        適用於: Bull Spread, Bear Spread, Iron Condor, Butterfly
        
        參數:
            range_pct: 範圍百分比（默認10% = ±10%）
        
        返回: 5-10個行使價
        """
        if not all_strikes:
            return []
        
        # 計算範圍
        min_strike = current_price * (1 - range_pct)
        max_strike = current_price * (1 + range_pct)
        
        # 篩選範圍內的行使價
        strikes_in_range = [
            s for s in all_strikes
            if min_strike <= s <= max_strike
        ]
        
        logger.debug(f"  ATM範圍策略: ${min_strike:.2f} ~ ${max_strike:.2f}")
        logger.debug(f"  選擇 {len(strikes_in_range)} 個行使價")
        
        return sorted(strikes_in_range)
    
    def _fetch_liquid_only(
        self,
        all_strikes: List[float],
        option_data: Optional[Dict],
        min_volume: int = 10,
        min_oi: int = 100
    ) -> List[float]:
        """
        策略3: 只獲取流動性好的行使價
        
        適用於: Greeks分析, Option Flow分析, 機構持倉分析
        
        參數:
            option_data: 期權數據字典 {strike: {'volume': ..., 'oi': ...}}
            min_volume: 最低成交量
            min_oi: 最低未平倉量
        
        返回: 30-50個流動性好的行使價
        """
        if not all_strikes:
            return []
        
        # 如果沒有期權數據，降級到ATM範圍策略
        if option_data is None:
            logger.warning("! 沒有期權數據，降級到ATM範圍策略")
            # 假設當前價格為中間值
            current_price = sum(all_strikes) / len(all_strikes)
            return self._fetch_atm_range(current_price, all_strikes, range_pct=0.15)
        
        # 篩選流動性好的行使價
        liquid_strikes = []
        for strike in all_strikes:
            strike_data = option_data.get(strike, {})
            volume = strike_data.get('volume', 0)
            oi = strike_data.get('open_interest', 0)
            
            if volume >= min_volume and oi >= min_oi:
                liquid_strikes.append(strike)
        
        logger.debug(f"  流動性策略: Volume≥{min_volume}, OI≥{min_oi}")
        logger.debug(f"  選擇 {len(liquid_strikes)} 個流動性好的行使價")
        
        return sorted(liquid_strikes)
    
    def estimate_api_calls(
        self,
        strategy_type: str,
        total_strikes: int
    ) -> Tuple[int, int, float]:
        """
        估算API調用次數
        
        參數:
            strategy_type: 策略類型
            total_strikes: 總行使價數量
        
        返回:
            (before, after, reduction_pct): 優化前、優化後、減少百分比
        """
        # 優化前：獲取所有行使價
        calls_before = total_strikes
        
        # 優化後：根據策略估算
        if strategy_type == 'simple':
            calls_after = 1
        elif strategy_type == 'spread':
            calls_after = max(5, int(total_strikes * 0.3))  # 約30%
        elif strategy_type == 'advanced':
            calls_after = max(30, int(total_strikes * 0.7))  # 約70%
        else:
            calls_after = 1
        
        # 計算減少百分比
        if calls_before > 0:
            reduction_pct = (1 - calls_after / calls_before) * 100
        else:
            reduction_pct = 0.0
        
        return calls_before, calls_after, reduction_pct


# 使用示例
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    fetcher = SmartOptionChainFetcher()
    
    print("\n" + "=" * 70)
    print("智能期權鏈獲取器測試")
    print("=" * 70)
    
    # 模擬AAPL的行使價（$150 ~ $200，間隔$5）
    current_price = 175.0
    all_strikes = [float(i) for i in range(150, 201, 5)]
    
    print(f"\n當前股價: ${current_price:.2f}")
    print(f"可用行使價: {len(all_strikes)} 個")
    print(f"行使價範圍: ${min(all_strikes):.2f} ~ ${max(all_strikes):.2f}")
    
    # 測試3種策略
    for strategy in ['simple', 'spread', 'advanced']:
        print(f"\n【策略: {strategy}】")
        print("-" * 70)
        
        config = fetcher.get_strikes_config(
            current_price=current_price,
            all_strikes=all_strikes,
            strategy_type=strategy
        )
        
        print(f"選擇的行使價數量: {len(config.strikes_to_fetch)}")
        print(f"API調用減少: {config.reduction_percentage:.1f}%")
        print(f"行使價列表: {config.strikes_to_fetch[:5]}..." if len(config.strikes_to_fetch) > 5 else f"行使價列表: {config.strikes_to_fetch}")
    
    print("\n" + "=" * 70)
    print("性能提升總結")
    print("=" * 70)
    
    for strategy in ['simple', 'spread', 'advanced']:
        before, after, reduction = fetcher.estimate_api_calls(strategy, len(all_strikes))
        print(f"{strategy:10s}: {before:3d} → {after:3d} 次調用 (減少 {reduction:.0f}%)")
    
    print("=" * 70)
