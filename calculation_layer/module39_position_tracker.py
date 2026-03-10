# calculation_layer/module39_position_tracker.py
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PositionTracker:
    """
    Phase 5: Position Tracker (VZ Long Put 追蹤)
    專門用來計算已建倉期權的 Hold, Roll, Close 建議
    """
    def __init__(self):
        pass

    def evaluate_position(
        self,
        ticker: str,
        current_price: float,
        strike: float,
        option_type: str,
        days_to_expiry: int,
        premium: float,
        greeks: Dict[str, float],
        dark_pool_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Evaluate an existing position and provide actionable advice.
        """
        logger.info(f"[Phase 5] 評估現有部位: {ticker} {strike} {option_type}")
        
        # 1. 計算盈虧平衡點
        if option_type == 'C':
            breakeven = strike + premium
            is_otm = current_price < strike
            distance_to_strike = (strike - current_price) / current_price * 100
        else:
            breakeven = strike - premium
            is_otm = current_price > strike
            distance_to_strike = (current_price - strike) / current_price * 100
            
        # 2. 獲取 Greeks 和 暗池數據
        delta = greeks.get('delta', 0.0)
        theta = greeks.get('theta', 0.0)
        gamma = greeks.get('gamma', 0.0)
        
        dp_ratio = 0.0
        if dark_pool_data:
            dp_ratio = dark_pool_data.get('dp_ratio', 0.0)
            
        # 3. 核心決策邏輯 (針對 Long Put / Long Call)
        recommendation = "Hold (繼續持有)"
        reasoning = []
        
        # 情境 A: Theta 衰減過大，且勝率渺茫 (Close)
        if days_to_expiry < 30 and distance_to_strike > 10:
            recommendation = "Close (平倉止損)"
            reasoning.append(f"到期日不足 30 天 ({days_to_expiry}天)，且距離行使價過遠 ({distance_to_strike:.1f}%)。Theta 衰減將會加速侵蝕剩餘價值。")
            
        # 情境 B: 已經獲利，可以考慮 Roll (轉倉) 或 Close
        elif not is_otm:
            if option_type == 'P' and dp_ratio > 45:
                # Long Put 已經 ITM，但暗池顯示大量買盤 (機構看漲)
                recommendation = "Close (獲利了結)"
                reasoning.append(f"部位已進入價內，但暗池買盤強勁 (DP Ratio: {dp_ratio}%)，暗示可能會有反彈，建議獲利了結。")
            elif option_type == 'C' and dp_ratio < 35 and dp_ratio > 0:
                recommendation = "Close (獲利了結)"
                reasoning.append(f"部位已進入價內，但暗池買盤疲弱 (DP Ratio: {dp_ratio}%)，暗示上漲動能不足，建議獲利了結。")
            else:
                recommendation = "Roll (向上/向下轉倉)"
                reasoning.append(f"部位已進入價內。為了鎖定利潤並釋放保證金/資金，建議將此倉位平掉，轉倉至更遠端的新行使價。")

        # 情境 C: 剩餘時間充足 (Hold)
        elif days_to_expiry >= 30:
            # 觀察暗池數據是否支持
            if option_type == 'P':
                if dp_ratio > 50:
                    recommendation = "Close (平倉止損)"
                    reasoning.append(f"雖然距離到期還有 {days_to_expiry} 天，但暗池買盤極強 (DP Ratio: {dp_ratio}%)，機構正在大量建倉看漲，對您的 Long Put 極為不利。建議提早止損。")
                else:
                    recommendation = "Hold (繼續持有)"
                    reasoning.append(f"時間充裕 ({days_to_expiry}天)，可以繼續等待趨勢發酵。")
            elif option_type == 'C':
                if dp_ratio < 40 and dp_ratio > 0:
                    recommendation = "Close (平倉止損)"
                    reasoning.append(f"雖然距離到期還有 {days_to_expiry} 天，但暗池買盤極低 (DP Ratio: {dp_ratio}%)，機構正在出貨，對您的 Long Call 極為不利。建議提早止損。")
                else:
                    recommendation = "Hold (繼續持有)"
                    reasoning.append(f"時間充裕 ({days_to_expiry}天)，可以繼續等待趨勢發酵。")
                    
        return {
            'ticker': ticker,
            'strike': strike,
            'option_type': option_type,
            'days_to_expiry': days_to_expiry,
            'current_price': current_price,
            'premium': premium,
            'breakeven': breakeven,
            'distance_to_strike_pct': distance_to_strike,
            'greeks': {
                'delta': delta,
                'gamma': gamma,
                'theta': theta
            },
            'dark_pool_ratio': dp_ratio,
            'recommendation': recommendation,
            'reasoning': reasoning
        }
