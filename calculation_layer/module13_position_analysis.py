from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class PositionAnalysisResult:
    """倉位分析結果
    
    Requirements: 2.1, 2.2, 2.3 - 支持 Call/Put 分離顯示
    """
    volume: int
    open_interest: int
    price_change: float
    volume_oi_ratio: float
    market_sentiment: str
    position_strength: str
    trend_analysis: str
    calculation_date: str
    # 新增 Call/Put 分離字段 (Requirements: 2.1, 2.2)
    call_volume: Optional[int] = None
    call_open_interest: Optional[int] = None
    put_volume: Optional[int] = None
    put_open_interest: Optional[int] = None
    # 新增 Put/Call 比率 (Requirements: 2.3)
    put_call_ratio: Optional[float] = None
    
    def to_dict(self) -> Dict:
        result = {
            'volume': self.volume,
            'open_interest': self.open_interest,
            'price_change': round(self.price_change, 2),
            'volume_oi_ratio': round(self.volume_oi_ratio, 4),
            'market_sentiment': self.market_sentiment,
            'position_strength': self.position_strength,
            'trend_analysis': self.trend_analysis,
            'calculation_date': self.calculation_date,
            # Call/Put 分離數據
            'call_volume': self.call_volume,
            'call_open_interest': self.call_open_interest,
            'put_volume': self.put_volume,
            'put_open_interest': self.put_open_interest,
            'put_call_ratio': round(self.put_call_ratio, 4) if self.put_call_ratio is not None else None
        }
        return result


class PositionAnalysisCalculator:
    """
    倉位分析計算器
    
    書籍來源: 《期權制勝》第十三課
    
    分析要素 (100%書籍):
    ────────────────────────────────
    1. 成交量 (Volume): 市場參與程度
    2. 未平倉 (Open Interest): 持倉規模
    3. 成交量/未平倉比率: 市場活躍度
    4. 價格變化方向: 趨勢判斷
    
    理論:
    成交量高且未平倉增加 → 新投資者進場 → 趨勢開始
    成交量低且未平倉增加 → 舊持倉換手 → 趨勢鞏固
    成交量高且未平倉下降 → 投資者退場 → 趨勢終結
    ────────────────────────────────
    """
    
    def __init__(self):
        logger.info("* 倉位分析計算器已初始化")
    
    def calculate(self,
                  volume: int,
                  open_interest: int,
                  price_change: float,
                  calculation_date: str = None,
                  call_volume: Optional[int] = None,
                  call_open_interest: Optional[int] = None,
                  put_volume: Optional[int] = None,
                  put_open_interest: Optional[int] = None) -> PositionAnalysisResult:
        """
        計算倉位分析
        
        參數:
            volume: 總成交量（向後兼容）
            open_interest: 總未平倉量（向後兼容）
            price_change: 價格變化百分比
            calculation_date: 計算日期
            call_volume: Call 期權成交量 (Requirements: 2.1)
            call_open_interest: Call 期權未平倉量 (Requirements: 2.2)
            put_volume: Put 期權成交量 (Requirements: 2.1)
            put_open_interest: Put 期權未平倉量 (Requirements: 2.2)
        
        返回:
            PositionAnalysisResult: 包含 Call/Put 分離數據和 Put/Call 比率
        """
        try:
            logger.info(f"開始倉位分析...")
            logger.info(f"  成交量: {volume:,}")
            logger.info(f"  未平倉: {open_interest:,}")
            logger.info(f"  價格變化: {price_change:.2f}%")
            
            # 記錄 Call/Put 分離數據
            if call_volume is not None:
                logger.info(f"  Call 成交量: {call_volume:,}")
            if call_open_interest is not None:
                logger.info(f"  Call 未平倉量: {call_open_interest:,}")
            if put_volume is not None:
                logger.info(f"  Put 成交量: {put_volume:,}")
            if put_open_interest is not None:
                logger.info(f"  Put 未平倉量: {put_open_interest:,}")
            
            if not self._validate_inputs(volume, open_interest, price_change):
                raise ValueError("輸入參數無效")
            
            if calculation_date is None:
                calculation_date = datetime.now().strftime('%Y-%m-%d')
            
            # 計算成交量/未平倉比率
            volume_oi_ratio = volume / open_interest if open_interest > 0 else 0
            
            # 計算 Put/Call 比率 (Requirements: 2.3)
            put_call_ratio = self._calculate_put_call_ratio(
                call_open_interest, put_open_interest
            )
            if put_call_ratio is not None:
                logger.info(f"  Put/Call 比率: {put_call_ratio:.4f}")
            
            # 分析市場情緒
            if volume > 100000 and price_change > 0:
                market_sentiment = "看漲 (高成交量，上升)"
            elif volume > 100000 and price_change < 0:
                market_sentiment = "看跌 (高成交量，下降)"
            elif volume < 50000 and price_change > 0:
                market_sentiment = "弱漲 (低成交量，上升)"
            elif volume < 50000 and price_change < 0:
                market_sentiment = "弱跌 (低成交量，下降)"
            else:
                market_sentiment = "中性 (中等成交量)"
            
            # 倉位強度
            if volume_oi_ratio > 0.5:
                position_strength = "強 (高成交/未平倉比)"
            elif volume_oi_ratio > 0.2:
                position_strength = "中 (中等成交/未平倉比)"
            else:
                position_strength = "弱 (低成交/未平倉比)"
            
            # 趨勢分析
            if price_change > 2 and volume > 100000:
                trend_analysis = "強上升趨勢 - 新投資者積極建倉"
            elif price_change < -2 and volume > 100000:
                trend_analysis = "強下降趨勢 - 投資者積極平倉"
            else:
                trend_analysis = "趨勢中等 - 需等待突破信號"
            
            logger.info(f"  分析結果:")
            logger.info(f"    成交量/未平倉比: {volume_oi_ratio:.4f}")
            logger.info(f"    市場情緒: {market_sentiment}")
            logger.info(f"    倉位強度: {position_strength}")
            logger.info(f"    趨勢分析: {trend_analysis}")
            
            result = PositionAnalysisResult(
                volume=volume,
                open_interest=open_interest,
                price_change=price_change,
                volume_oi_ratio=volume_oi_ratio,
                market_sentiment=market_sentiment,
                position_strength=position_strength,
                trend_analysis=trend_analysis,
                calculation_date=calculation_date,
                # Call/Put 分離數據
                call_volume=call_volume,
                call_open_interest=call_open_interest,
                put_volume=put_volume,
                put_open_interest=put_open_interest,
                put_call_ratio=put_call_ratio
            )
            
            logger.info(f"* 倉位分析完成")
            return result
            
        except Exception as e:
            logger.error(f"x 倉位分析失敗: {e}")
            raise
    
    def _calculate_put_call_ratio(self, 
                                   call_open_interest: Optional[int], 
                                   put_open_interest: Optional[int]) -> Optional[float]:
        """
        計算 Put/Call 未平倉量比率
        
        Requirements: 2.3 - WHEN 未平倉量數據可用 THEN Report_Generator SHALL 
                           計算並顯示 Put/Call 未平倉量比率
        
        返回:
            Put/Call 比率，如果數據不可用則返回 None
        """
        if call_open_interest is None or put_open_interest is None:
            return None
        if call_open_interest <= 0:
            return None
        return put_open_interest / call_open_interest
    
    @staticmethod
    def _validate_inputs(volume: int, open_interest: int, price_change: float) -> bool:
        logger.info("驗證輸入參數...")
        
        if not isinstance(volume, int) or not isinstance(open_interest, int):
            logger.error("x 成交量和未平倉必須是整數")
            return False
        
        if volume < 0 or open_interest < 0:
            logger.error("x 成交量和未平倉不能為負")
            return False
        
        if not isinstance(price_change, (int, float)):
            logger.error("x 價格變化必須是數字")
            return False
        
        logger.info("* 輸入參數驗證通過")
        return True