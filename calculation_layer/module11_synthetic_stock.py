import logging
from dataclasses import dataclass
from typing import Dict
from datetime import datetime
import math

logger = logging.getLogger(__name__)


@dataclass
class SyntheticStockResult:
    """合成正股計算結果"""
    strike_price: float
    call_premium: float
    put_premium: float
    synthetic_price: float
    current_stock_price: float
    difference: float
    arbitrage_opportunity: bool
    strategy: str
    calculation_date: str
    # 新增字段：股息和折現信息
    pv_strike: float = 0.0
    pv_dividend: float = 0.0
    expected_dividend: float = 0.0
    
    def to_dict(self) -> Dict:
        result = {
            'strike_price': round(self.strike_price, 2),
            'call_premium': round(self.call_premium, 2),
            'put_premium': round(self.put_premium, 2),
            'synthetic_price': round(self.synthetic_price, 2),
            'current_stock_price': round(self.current_stock_price, 2),
            'difference': round(self.difference, 2),
            'arbitrage_opportunity': self.arbitrage_opportunity,
            'strategy': self.strategy,
            'calculation_date': self.calculation_date
        }
        # 添加詳細折現信息
        if self.pv_strike > 0:
            result['pv_strike'] = round(self.pv_strike, 2)
        if self.pv_dividend > 0:
            result['pv_dividend'] = round(self.pv_dividend, 2)
            result['expected_dividend'] = round(self.expected_dividend, 2)
        return result


class SyntheticStockCalculator:
    """
    合成正股計算器
    
    書籍來源: 《期權制勝2》第二課
    
    公式 (100%書籍):
    ────────────────────────────────
    Long Call + Short Put = 合成Long Stock
    合成價格 = Call金 - Put金 + 行使價
    
    Short Call + Long Put = 合成Short Stock
    合成價格 = 行使價 - (Call金 - Put金)
    
    注意:
    - 本模塊採用書中到期日的簡化平價關係，忽略了利率折現因子 e^(-rT)。
    - 若需更嚴謹的理論價，可在外部加入利率與剩餘天數的折現調整。
    
    理論:
    期權組合可以複製正股的損益特徵
    當合成價格與實際股價有差異時
    存在套戥機會
    ────────────────────────────────
    """
    
    def __init__(self):
        logger.info("* 合成正股計算器已初始化")
    
    def calculate(self,
                  strike_price: float,
                  call_premium: float,
                  put_premium: float,
                  current_stock_price: float,
                  risk_free_rate: float = 0.0,
                  time_to_expiration: float = 0.0,
                  expected_dividend: float = 0.0,
                  dividend_time: float = None,
                  calculation_date: str = None) -> SyntheticStockResult:
        """
        計算合成正股價格（支持股息調整）
        
        參數:
            strike_price: 行使價
            call_premium: Call期權金
            put_premium: Put期權金
            current_stock_price: 當前股價
            risk_free_rate: 無風險利率 (小數, e.g. 0.045)
            time_to_expiration: 到期時間 (年)
            expected_dividend: 到期前預期股息 (美元, 默認 0)
                - 可從 Finviz 的 dividend_yield 計算
                - 公式: expected_dividend = stock_price × dividend_yield% × time_to_expiration
            dividend_time: 股息支付時間 (年, 默認為 time_to_expiration/2)
            calculation_date: 計算日期
        
        返回:
            SyntheticStockResult: 完整計算結果
        
        完整 Put-Call Parity 公式:
            C - P = S - K×e^(-r×T) + D×e^(-r×t_d)
            合成價格 = (C - P) + K×e^(-r×T) - D×e^(-r×t_d)
        
        股息數據來源:
            - Finviz: dividend_yield (年化百分比)
            - Yahoo Finance: dividendRate (每股年度股息)
            - Massive API: dividendYield
        """
        try:
            logger.info(f"開始計算合成正股...")
            logger.info(f"  行使價: ${strike_price:.2f}")
            logger.info(f"  Call金: ${call_premium:.2f}")
            logger.info(f"  Put金: ${put_premium:.2f}")
            logger.info(f"  當前股價: ${current_stock_price:.2f}")
            logger.info(f"  利率: {risk_free_rate:.4f}, 時間: {time_to_expiration:.4f}年")
            
            if not self._validate_inputs(strike_price, call_premium, put_premium, current_stock_price):
                raise ValueError("輸入參數無效")
            
            if calculation_date is None:
                calculation_date = datetime.now().strftime('%Y-%m-%d')
            
            # 計算行使價現值
            # PV(K) = K × e^(-r×T)
            pv_strike = strike_price * math.exp(-risk_free_rate * time_to_expiration)
            
            # 計算股息現值 (如果有)
            pv_dividend = 0.0
            if expected_dividend > 0:
                # 如果未指定股息支付時間，假設在到期時間的一半
                if dividend_time is None:
                    dividend_time = time_to_expiration / 2.0
                pv_dividend = expected_dividend * math.exp(-risk_free_rate * dividend_time)
                logger.info(f"  預期股息: ${expected_dividend:.2f}")
                logger.info(f"  股息現值: ${pv_dividend:.2f}")
            
            # 計算合成價格 (考慮利率和股息)
            # 公式: 合成價 = (C - P) + PV(K) - PV(D)
            synthetic_price = call_premium - put_premium + pv_strike - pv_dividend
            
            logger.info(f"  PV(行使價): ${pv_strike:.2f}")
            
            # 計算差異
            difference = current_stock_price - synthetic_price
            
            # 判斷套戥機會
            arbitrage_opportunity = abs(difference) > 0.10
            
            # 確定策略
            if arbitrage_opportunity:
                if difference > 0:
                    strategy = "沽出實股，買入合成空"
                else:
                    strategy = "買入實股，沽出合成多"
            else:
                strategy = "無明顯套戥機會"
            
            logger.info(f"  計算結果:")
            logger.info(f"    合成價格: ${synthetic_price:.2f}")
            logger.info(f"    差異: ${difference:.2f}")
            logger.info(f"    套戥機會: {arbitrage_opportunity}")
            logger.info(f"    策略: {strategy}")
            
            result = SyntheticStockResult(
                strike_price=strike_price,
                call_premium=call_premium,
                put_premium=put_premium,
                synthetic_price=synthetic_price,
                current_stock_price=current_stock_price,
                difference=difference,
                arbitrage_opportunity=arbitrage_opportunity,
                strategy=strategy,
                calculation_date=calculation_date,
                pv_strike=pv_strike,
                pv_dividend=pv_dividend,
                expected_dividend=expected_dividend
            )
            
            logger.info(f"* 合成正股計算完成")
            return result
            
        except Exception as e:
            logger.error(f"x 合成正股計算失敗: {e}")
            raise
    
    def calculate_with_dividend_yield(
        self,
        strike_price: float,
        call_premium: float,
        put_premium: float,
        current_stock_price: float,
        risk_free_rate: float,
        time_to_expiration: float,
        dividend_yield: float,
        calculation_date: str = None
    ) -> SyntheticStockResult:
        """
        使用股息收益率計算合成正股價格
        
        此方法直接使用 Finviz/Yahoo Finance 提供的 dividend_yield 百分比，
        自動計算到期前的預期股息。
        
        參數:
            strike_price: 行使價
            call_premium: Call期權金
            put_premium: Put期權金
            current_stock_price: 當前股價
            risk_free_rate: 無風險利率 (小數, e.g. 0.045)
            time_to_expiration: 到期時間 (年)
            dividend_yield: 年化股息收益率 (百分比, e.g. 0.5 表示 0.5%)
                - Finviz: data['dividend_yield']
                - Yahoo Finance: info['dividendYield'] * 100
            calculation_date: 計算日期
        
        返回:
            SyntheticStockResult: 完整計算結果
        
        示例:
            >>> calc = SyntheticStockCalculator()
            >>> # 使用 Finviz 數據
            >>> finviz_data = finviz_scraper.get_stock_fundamentals('AAPL')
            >>> result = calc.calculate_with_dividend_yield(
            ...     strike_price=180.0,
            ...     call_premium=8.0,
            ...     put_premium=6.5,
            ...     current_stock_price=181.0,
            ...     risk_free_rate=0.045,
            ...     time_to_expiration=0.25,  # 3個月
            ...     dividend_yield=finviz_data['dividend_yield'] or 0  # 0.5%
            ... )
        """
        # 計算到期前預期股息
        # 公式: expected_dividend = stock_price × (dividend_yield/100) × time_to_expiration
        if dividend_yield and dividend_yield > 0:
            expected_dividend = current_stock_price * (dividend_yield / 100) * time_to_expiration
            logger.info(f"  股息收益率: {dividend_yield:.2f}%")
            logger.info(f"  計算預期股息: ${expected_dividend:.4f}")
        else:
            expected_dividend = 0.0
        
        return self.calculate(
            strike_price=strike_price,
            call_premium=call_premium,
            put_premium=put_premium,
            current_stock_price=current_stock_price,
            risk_free_rate=risk_free_rate,
            time_to_expiration=time_to_expiration,
            expected_dividend=expected_dividend,
            dividend_time=time_to_expiration / 2.0,  # 假設股息在中間支付
            calculation_date=calculation_date
        )
    
    @staticmethod
    def _validate_inputs(strike_price: float, call_premium: float, 
                        put_premium: float, current_stock_price: float) -> bool:
        logger.info("驗證輸入參數...")
        
        if not all(isinstance(x, (int, float)) for x in [strike_price, call_premium, put_premium, current_stock_price]):
            logger.error("x 所有參數必須是數字")
            return False
        
        if strike_price <= 0 or current_stock_price <= 0:
            logger.error("x 股價和行使價必須大於0")
            return False
        
        if call_premium < 0 or put_premium < 0:
            logger.error("x 期權金不能為負")
            return False
        
        logger.info("* 輸入參數驗證通過")
        return True