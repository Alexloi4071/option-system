# main.py
"""
主程序入口 - 期權分析系統第1階段
"""

import logging
import argparse
from datetime import datetime
import sys
import os

# 配置日誌（使用 UTF-8 編碼）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/main_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# 設置 StreamHandler 使用 UTF-8
for handler in logging.root.handlers:
    if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
        handler.stream = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

logger = logging.getLogger(__name__)

# 導入模塊
from config.settings import settings
from data_layer.data_fetcher import DataFetcher
from data_layer.data_validator import DataValidator
from calculation_layer.module1_support_resistance import SupportResistanceCalculator
from calculation_layer.module2_fair_value import FairValueCalculator
from calculation_layer.module3_arbitrage_spread import ArbitrageSpreadCalculator
from calculation_layer.module4_pe_valuation import PEValuationCalculator
from calculation_layer.module5_rate_pe_relation import RatePERelationCalculator
from calculation_layer.module6_hedge_quantity import HedgeQuantityCalculator
from calculation_layer.module7_long_call import LongCallCalculator
from calculation_layer.module8_long_put import LongPutCalculator
from calculation_layer.module9_short_call import ShortCallCalculator
from calculation_layer.module10_short_put import ShortPutCalculator
from calculation_layer.module11_synthetic_stock import SyntheticStockCalculator
from calculation_layer.module12_annual_yield import AnnualYieldCalculator
from calculation_layer.module13_position_analysis import PositionAnalysisCalculator
from calculation_layer.module14_monitoring_posts import MonitoringPostsCalculator
# 新增模塊 (Module 15-19)
from calculation_layer.module15_black_scholes import BlackScholesCalculator
from calculation_layer.module16_greeks import GreeksCalculator
from calculation_layer.module17_implied_volatility import ImpliedVolatilityCalculator
from calculation_layer.module18_historical_volatility import HistoricalVolatilityCalculator
from calculation_layer.module19_put_call_parity import PutCallParityValidator
from output_layer.report_generator import ReportGenerator


class OptionsAnalysisSystem:
    """
    完整期權分析系統 (第1階段)
    
    流程:
    1. 獲取數據 (數據層)
    2. 驗證數據 (驗證層)
    3. 運行計算模塊 (計算層)
    4. 生成報告 (輸出層)
    """
    
    def __init__(self):
        """初始化系統"""
        logger.info("=" * 70)
        logger.info("期權分析系統啟動")
        logger.info(f"系統版本: {settings.VERSION}")
        logger.info(f"當前時間: {datetime.now()}")
        logger.info("=" * 70)
        
        self.fetcher = DataFetcher()
        self.validator = DataValidator()
        self.report_generator = ReportGenerator()
        self.analysis_results = {}
    
    def run_complete_analysis(self, ticker: str, expiration: str = None, 
                             confidence: float = 1.0, use_ibkr: bool = None,
                             strike: float = None, premium: float = None, 
                             option_type: str = None):
        """
        運行完整分析
        
        參數:
            ticker: 股票代碼
            expiration: 期權到期日 (可選)
            confidence: IV 信心度 Z 值 (默認 1.0)
            use_ibkr: 是否使用 IBKR 數據源 (None 時從 settings 讀取)
            strike: 期權行使價 (可選)
            premium: 期權價格 (可選)
            option_type: 期權類型 'C' (Call) 或 'P' (Put) (可選)
        
        返回:
            dict: 完整分析結果
        """
        try:
            logger.info(f"\n開始分析 {ticker}")
            # 清空上一輪結果
            self.analysis_results = {}
            
            # 初始化 DataFetcher（如果指定了 use_ibkr）
            if use_ibkr is not None:
                self.fetcher = DataFetcher(use_ibkr=use_ibkr)
                logger.info(f"數據源設置: IBKR={'啟用' if use_ibkr else '禁用'}")
            
            # 第1步: 獲取數據
            logger.info("→ 第1步: 獲取市場數據...")
            analysis_data = self.fetcher.get_complete_analysis_data(ticker, expiration)
            if not analysis_data:
                raise ValueError(f"無法獲取 {ticker} 數據")
            
            # 如果提供了 strike/premium/type，更新 analysis_data
            if strike is not None:
                analysis_data['strike'] = strike
            if premium is not None:
                analysis_data['option_premium'] = premium
            if option_type is not None:
                analysis_data['option_type'] = option_type.upper()
            
            # 第2步: 驗證數據
            logger.info("\n→ 第2步: 驗證數據完整性...")
            if not self.validator.validate_stock_data(analysis_data):
                raise ValueError("數據驗證失敗")
            
            # 第3步: 運行計算模塊
            logger.info("\n→ 第3步: 運行計算模塊...")
            
            # 模塊1: 支持/阻力位 (IV法) - 多信心度計算
            sr_calc = SupportResistanceCalculator()
            days_to_expiration = analysis_data.get('days_to_expiration')
            if days_to_expiration is None:
                expiration_date = analysis_data.get('expiration_date')
                if expiration_date:
                    exp_dt = datetime.strptime(expiration_date, '%Y-%m-%d')
                    trading_calc = getattr(self.fetcher, 'trading_days_calc', None)
                    if trading_calc:
                        days_to_expiration = trading_calc.calculate_trading_days(
                            datetime.now(),
                            exp_dt
                        )
                    else:
                        days_to_expiration = max(0, (exp_dt - datetime.now()).days)
                else:
                    raise ValueError("缺少到期天數資訊")
            
            # 新增: 使用多信心度計算
            sr_results_multi = sr_calc.calculate_multi_confidence(
                stock_price=analysis_data['current_price'],
                implied_volatility=analysis_data['implied_volatility'],
                days_to_expiration=int(days_to_expiration),
                confidence_levels=['68%', '80%', '90%', '95%', '99%']  # 用戶Excel的5個信心度
            )
            
            # 保存多信心度結果
            self.analysis_results['module1_support_resistance_multi'] = sr_results_multi
            
            # 兼容性: 保留單一信心度計算 (使用90%作為默認)
            sr_result_single = sr_calc.calculate(
                stock_price=analysis_data['current_price'],
                implied_volatility=analysis_data['implied_volatility'],
                days_to_expiration=int(days_to_expiration),
                z_score=1.645  # 90%信心度
            )
            self.analysis_results['module1_support_resistance'] = sr_result_single.to_dict()
            
            logger.info("✓ 模塊1完成: 多信心度計算 + 單一信心度 (90%)")
            
            # 模塊2: 公允值 / 遠期理論價
            analysis_date_str = analysis_data.get('analysis_date')
            days_to_expiration = analysis_data.get('days_to_expiration')  # 從 data_fetcher 獲取交易日數
            fv_calc = FairValueCalculator()
            fv_result = fv_calc.calculate(
                stock_price=analysis_data['current_price'],
                risk_free_rate=analysis_data.get('risk_free_rate', 0) or 0,
                expiration_date=analysis_data.get('expiration_date', analysis_date_str),
                expected_dividend=analysis_data.get('annual_dividend', 0) or 0,
                calculation_date=analysis_date_str,
                days_to_expiration=days_to_expiration  # 優先使用交易日數
            )
            fv_result_dict = fv_result.to_dict()
            self.analysis_results['module2_fair_value'] = fv_result_dict
            logger.info("✓ 模塊2完成: 公允值計算")
            
            # 共享數據準備
            atm_option = analysis_data.get('atm_option', {}) or {}
            atm_strike = atm_option.get('strike')
            atm_call = atm_option.get('call', {}) or {}
            atm_put = atm_option.get('put', {}) or {}
            option_chain = analysis_data.get('option_chain', {})
            calls_df = option_chain.get('calls')
            puts_df = option_chain.get('puts')
            call_bid = float(atm_call.get('bid', 0) or 0)
            call_ask = float(atm_call.get('ask', 0) or 0)
            call_last_price = float(atm_call.get('lastPrice', 0) or 0)
            put_last_price = float(atm_put.get('lastPrice', 0) or 0)
            call_volume = int(atm_call.get('volume', 0) or 0)
            call_open_interest = int(atm_call.get('openInterest', 0) or 0)
            call_delta = atm_call.get('delta')
            if call_delta is not None:
                try:
                    call_delta = float(call_delta)
                except (TypeError, ValueError):
                    call_delta = None
            bid_ask_spread = max(0.0, call_ask - call_bid)
            strike_price = float(atm_strike) if atm_strike is not None else None
            default_stock_quantity = 1000
            option_multiplier = settings.OPTION_MULTIPLIER
            current_price = analysis_data['current_price']
            
            # 模塊3: 套戥水位 (若有市場價格與理論價)
            try:
                if call_last_price > 0 and fv_result.fair_value > 0:
                    arb_calc = ArbitrageSpreadCalculator()
                    arb_result = arb_calc.calculate(
                        market_option_price=call_last_price,
                        fair_value=fv_result.fair_value,
                        calculation_date=analysis_date_str
                    )
                    self.analysis_results['module3_arbitrage_spread'] = arb_result.to_dict()
                    logger.info("✓ 模塊3完成: 套戥水位")
            except Exception as exc:
                logger.warning("⚠ 模塊3執行失敗: %s", exc)
            
            # 模塊4: PE估值
            try:
                eps = analysis_data.get('eps')
                pe_multiple = analysis_data.get('pe_ratio') or settings.PE_NORMAL
                if eps and pe_multiple and eps > 0 and pe_multiple > 0:
                    pe_calc = PEValuationCalculator()
                    pe_result = pe_calc.calculate(
                        eps=eps,
                        pe_multiple=pe_multiple,
                        current_price=current_price,
                        calculation_date=analysis_date_str
                    )
                    self.analysis_results['module4_pe_valuation'] = pe_result.to_dict()
                    logger.info("✓ 模塊4完成: PE估值")
            except Exception as exc:
                logger.warning("⚠ 模塊4執行失敗: %s", exc)
            
            # 模塊5: 利率與PE關係
            try:
                long_term_rate = analysis_data.get('risk_free_rate')
                current_pe = analysis_data.get('pe_ratio')
                if long_term_rate and current_pe and long_term_rate > 0 and current_pe > 0:
                    rate_pe_calc = RatePERelationCalculator()
                    rate_pe_result = rate_pe_calc.calculate(
                        long_term_rate=long_term_rate,
                        current_pe=current_pe,
                        calculation_date=analysis_date_str
                    )
                    self.analysis_results['module5_rate_pe_relation'] = rate_pe_result.to_dict()
                    logger.info("✓ 模塊5完成: 利率與PE關係")
            except Exception as exc:
                logger.warning("⚠ 模塊5執行失敗: %s", exc)
            
            # 模塊6: 對沖量
            try:
                hedge_calc = HedgeQuantityCalculator()
                hedge_result = hedge_calc.calculate(
                    stock_quantity=default_stock_quantity,
                    stock_price=current_price,
                    calculation_date=analysis_date_str
                )
                self.analysis_results['module6_hedge_quantity'] = hedge_result.to_dict()
                logger.info("✓ 模塊6完成: 對沖量")
            except Exception as exc:
                logger.warning("⚠ 模塊6執行失敗: %s", exc)
            
            # 模塊7-10: 單腿策略損益
            price_scenarios = [
                round(current_price * 0.9, 2),
                round(current_price, 2),
                round(current_price * 1.1, 2)
            ]
            
            if strike_price and strike_price > 0:
                # 模塊7: Long Call
                try:
                    if call_last_price > 0:
                        long_call_calc = LongCallCalculator()
                        long_call_results = [
                            long_call_calc.calculate(
                                strike_price=strike_price,
                                option_premium=call_last_price,
                                stock_price_at_expiry=price,
                                calculation_date=analysis_date_str
                            ).to_dict()
                            for price in price_scenarios
                        ]
                        self.analysis_results['module7_long_call'] = long_call_results
                        logger.info("✓ 模塊7完成: Long Call 損益")
                except Exception as exc:
                    logger.warning("⚠ 模塊7執行失敗: %s", exc)
                
                # 模塊8: Long Put
                try:
                    if put_last_price > 0:
                        long_put_calc = LongPutCalculator()
                        long_put_results = [
                            long_put_calc.calculate(
                                strike_price=strike_price,
                                option_premium=put_last_price,
                                stock_price_at_expiry=price,
                                calculation_date=analysis_date_str
                            ).to_dict()
                            for price in price_scenarios
                        ]
                        self.analysis_results['module8_long_put'] = long_put_results
                        logger.info("✓ 模塊8完成: Long Put 損益")
                except Exception as exc:
                    logger.warning("⚠ 模塊8執行失敗: %s", exc)
                
                # 模塊9: Short Call
                try:
                    if call_last_price > 0:
                        short_call_calc = ShortCallCalculator()
                        short_call_results = [
                            short_call_calc.calculate(
                                strike_price=strike_price,
                                option_premium=call_last_price,
                                stock_price_at_expiry=price,
                                calculation_date=analysis_date_str
                            ).to_dict()
                            for price in price_scenarios
                        ]
                        self.analysis_results['module9_short_call'] = short_call_results
                        logger.info("✓ 模塊9完成: Short Call 損益")
                except Exception as exc:
                    logger.warning("⚠ 模塊9執行失敗: %s", exc)
                
                # 模塊10: Short Put
                try:
                    if put_last_price > 0:
                        short_put_calc = ShortPutCalculator()
                        short_put_results = [
                            short_put_calc.calculate(
                                strike_price=strike_price,
                                option_premium=put_last_price,
                                stock_price_at_expiry=price,
                                calculation_date=analysis_date_str
                            ).to_dict()
                            for price in price_scenarios
                        ]
                        self.analysis_results['module10_short_put'] = short_put_results
                        logger.info("✓ 模塊10完成: Short Put 損益")
                except Exception as exc:
                    logger.warning("⚠ 模塊10執行失敗: %s", exc)
            
            # 模塊11: 合成正股
            try:
                if strike_price and call_last_price >= 0 and put_last_price >= 0:
                    synthetic_calc = SyntheticStockCalculator()
                    synthetic_result = synthetic_calc.calculate(
                        strike_price=strike_price,
                        call_premium=call_last_price,
                        put_premium=put_last_price,
                        current_stock_price=current_price,
                        calculation_date=analysis_date_str
                    )
                    self.analysis_results['module11_synthetic_stock'] = synthetic_result.to_dict()
                    logger.info("✓ 模塊11完成: 合成正股")
            except Exception as exc:
                logger.warning("⚠ 模塊11執行失敗: %s", exc)
            
            # 模塊12: 年息收益率
            try:
                cost_basis = current_price * default_stock_quantity
                annual_dividend_per_share = analysis_data.get('annual_dividend', 0) or 0
                annual_dividend_total = annual_dividend_per_share * default_stock_quantity
                annual_option_income = call_last_price * option_multiplier * 12 if call_last_price > 0 else 0
                if cost_basis > 0:
                    annual_yield_calc = AnnualYieldCalculator()
                    annual_yield_result = annual_yield_calc.calculate(
                        cost_basis=cost_basis,
                        annual_dividend=annual_dividend_total,
                        annual_option_income=annual_option_income,
                        calculation_date=analysis_date_str
                    )
                    self.analysis_results['module12_annual_yield'] = annual_yield_result.to_dict()
                    logger.info("✓ 模塊12完成: 年息收益率")
            except Exception as exc:
                logger.warning("⚠ 模塊12執行失敗: %s", exc)
            
            # 模塊13: 倉位分析
            try:
                if call_volume >= 0 and call_open_interest >= 0:
                    price_change_pct = 0.0
                    stock_open = analysis_data.get('stock_open')
                    if stock_open and stock_open > 0:
                        price_change_pct = ((current_price - stock_open) / stock_open) * 100
                    position_calc = PositionAnalysisCalculator()
                    position_result = position_calc.calculate(
                        volume=call_volume,
                        open_interest=call_open_interest,
                        price_change=price_change_pct,
                        calculation_date=analysis_date_str
                    )
                    self.analysis_results['module13_position_analysis'] = position_result.to_dict()
                    logger.info("✓ 模塊13完成: 倉位分析")
            except Exception as exc:
                logger.warning("⚠ 模塊13執行失敗: %s", exc)
            
            # 模塊14: 12監察崗位 (需要完整指標)
            try:
                delta_value = call_delta
                atr_estimate = 0.0
                stock_high = analysis_data.get('stock_high')
                stock_low = analysis_data.get('stock_low')
                if stock_high is not None and stock_low is not None:
                    atr_estimate = max(0.0, float(stock_high) - float(stock_low))
                if delta_value is not None and analysis_data.get('vix') is not None and call_volume >= 0 and call_open_interest >= 0:
                    monitoring_calc = MonitoringPostsCalculator()
                    monitoring_result = monitoring_calc.calculate(
                        stock_price=current_price,
                        option_premium=call_last_price,
                        iv=analysis_data['implied_volatility'],
                        delta=delta_value,
                        open_interest=call_open_interest,
                        volume=call_volume,
                        bid_ask_spread=bid_ask_spread,
                        atr=atr_estimate,
                        vix=analysis_data.get('vix', 0) or 0,
                        dividend_date=analysis_data.get('ex_dividend_date', ''),
                        earnings_date=analysis_data.get('next_earnings_date', ''),
                        expiration_date=analysis_data.get('expiration_date', ''),
                        calculation_date=analysis_date_str
                    )
                    self.analysis_results['module14_monitoring_posts'] = monitoring_result.to_dict()
                    logger.info("✓ 模塊14完成: 12監察崗位")
            except Exception as exc:
                logger.warning("⚠ 模塊14執行失敗: %s", exc)
            
            # ========== 新增模塊 (Module 15-19) ==========
            logger.info("\n→ 運行新增模塊 (Module 15-19)...")
            
            # 準備新模塊所需的共同參數
            risk_free_rate = analysis_data.get('risk_free_rate', 0.045) or 0.045
            time_to_expiration_years = days_to_expiration / 365.0 if days_to_expiration else 0.1
            volatility_estimate = analysis_data.get('implied_volatility', 0.25) or 0.25
            
            logger.info(f"共同參數: risk_free_rate={risk_free_rate:.4f}, "
                       f"time_to_expiration={time_to_expiration_years:.4f}年, "
                       f"volatility={volatility_estimate:.4f}")
            
            # 模塊15: Black-Scholes 期權定價
            try:
                if strike_price and strike_price > 0:
                    bs_calc = BlackScholesCalculator()
                    
                    # 計算 Call 期權理論價格
                    bs_call_result = bs_calc.calculate_option_price(
                        stock_price=current_price,
                        strike_price=strike_price,
                        risk_free_rate=risk_free_rate,
                        time_to_expiration=time_to_expiration_years,
                        volatility=volatility_estimate,
                        option_type='call'
                    )
                    
                    # 計算 Put 期權理論價格
                    bs_put_result = bs_calc.calculate_option_price(
                        stock_price=current_price,
                        strike_price=strike_price,
                        risk_free_rate=risk_free_rate,
                        time_to_expiration=time_to_expiration_years,
                        volatility=volatility_estimate,
                        option_type='put'
                    )
                    
                    self.analysis_results['module15_black_scholes'] = {
                        'call': bs_call_result.to_dict(),
                        'put': bs_put_result.to_dict(),
                        'parameters': {
                            'stock_price': current_price,
                            'strike_price': strike_price,
                            'risk_free_rate': risk_free_rate,
                            'time_to_expiration': time_to_expiration_years,
                            'volatility': volatility_estimate
                        }
                    }
                    logger.info(f"✓ 模塊15完成: Black-Scholes 定價 (Call=${bs_call_result.option_price:.2f}, Put=${bs_put_result.option_price:.2f})")
            except Exception as exc:
                logger.warning("⚠ 模塊15執行失敗: %s", exc)
            
            # 模塊16: Greeks 計算
            try:
                if strike_price and strike_price > 0:
                    greeks_calc = GreeksCalculator()
                    
                    # 計算 Call Greeks
                    call_greeks = greeks_calc.calculate_all_greeks(
                        stock_price=current_price,
                        strike_price=strike_price,
                        risk_free_rate=risk_free_rate,
                        time_to_expiration=time_to_expiration_years,
                        volatility=volatility_estimate,
                        option_type='call'
                    )
                    
                    # 計算 Put Greeks
                    put_greeks = greeks_calc.calculate_all_greeks(
                        stock_price=current_price,
                        strike_price=strike_price,
                        risk_free_rate=risk_free_rate,
                        time_to_expiration=time_to_expiration_years,
                        volatility=volatility_estimate,
                        option_type='put'
                    )
                    
                    self.analysis_results['module16_greeks'] = {
                        'call': call_greeks.to_dict(),
                        'put': put_greeks.to_dict()
                    }
                    logger.info(f"✓ 模塊16完成: Greeks 計算 (Call Delta={call_greeks.delta:.4f}, Gamma={call_greeks.gamma:.6f})")
            except Exception as exc:
                logger.warning("⚠ 模塊16執行失敗: %s", exc)
            
            # 模塊17: 隱含波動率計算
            try:
                if strike_price and strike_price > 0 and call_last_price > 0:
                    iv_calc = ImpliedVolatilityCalculator()
                    
                    # 從 Call 價格反推 IV
                    call_iv_result = iv_calc.calculate_implied_volatility(
                        market_price=call_last_price,
                        stock_price=current_price,
                        strike_price=strike_price,
                        risk_free_rate=risk_free_rate,
                        time_to_expiration=time_to_expiration_years,
                        option_type='call'
                    )
                    
                    iv_results = {'call': call_iv_result.to_dict()}
                    
                    # 如果有 Put 價格，也計算 Put IV
                    if put_last_price > 0:
                        put_iv_result = iv_calc.calculate_implied_volatility(
                            market_price=put_last_price,
                            stock_price=current_price,
                            strike_price=strike_price,
                            risk_free_rate=risk_free_rate,
                            time_to_expiration=time_to_expiration_years,
                            option_type='put'
                        )
                        iv_results['put'] = put_iv_result.to_dict()
                    
                    self.analysis_results['module17_implied_volatility'] = iv_results
                    
                    if call_iv_result.converged:
                        logger.info(f"✓ 模塊17完成: 隱含波動率計算 (Call IV={call_iv_result.implied_volatility*100:.2f}%, {call_iv_result.iterations}次迭代)")
                    else:
                        logger.warning(f"⚠ 模塊17: Call IV 未收斂 ({call_iv_result.iterations}次迭代)")
            except Exception as exc:
                logger.warning("⚠ 模塊17執行失敗: %s", exc)
            
            # 模塊18: 歷史波動率計算
            try:
                # 嘗試獲取歷史價格數據
                historical_data = analysis_data.get('historical_data')
                if historical_data is not None and len(historical_data) > 30:
                    hv_calc = HistoricalVolatilityCalculator()
                    
                    # 計算多個窗口期的歷史波動率
                    hv_results = hv_calc.calculate_multiple_windows(
                        historical_data['Close'],
                        windows=[10, 20, 30]
                    )
                    
                    # 使用 30 天 HV 與 IV 比較
                    hv_30 = hv_results.get(30)
                    if hv_30 and volatility_estimate:
                        iv_hv_ratio = hv_calc.calculate_iv_hv_ratio(
                            implied_volatility=volatility_estimate,
                            historical_volatility=hv_30.historical_volatility
                        )
                        
                        self.analysis_results['module18_historical_volatility'] = {
                            'hv_results': {k: v.to_dict() for k, v in hv_results.items()},
                            'iv_hv_comparison': iv_hv_ratio.to_dict()
                        }
                        logger.info(f"✓ 模塊18完成: 歷史波動率計算 (HV30={hv_30.historical_volatility*100:.2f}%, IV/HV={iv_hv_ratio.ratio:.2f})")
                    else:
                        self.analysis_results['module18_historical_volatility'] = {
                            'hv_results': {k: v.to_dict() for k, v in hv_results.items()}
                        }
                        logger.info("✓ 模塊18完成: 歷史波動率計算")
                else:
                    logger.info("⚠ 模塊18跳過: 歷史數據不足")
            except Exception as exc:
                logger.warning("⚠ 模塊18執行失敗: %s", exc)
            
            # 模塊19: Put-Call Parity 驗證
            try:
                if strike_price and strike_price > 0 and call_last_price > 0 and put_last_price > 0:
                    parity_validator = PutCallParityValidator()
                    
                    # 驗證市場價格的 Parity
                    parity_result = parity_validator.validate_parity(
                        call_price=call_last_price,
                        put_price=put_last_price,
                        stock_price=current_price,
                        strike_price=strike_price,
                        risk_free_rate=risk_free_rate,
                        time_to_expiration=time_to_expiration_years,
                        transaction_cost=0.10  # 假設交易成本 $0.10
                    )
                    
                    # 也計算理論價格的 Parity（用於驗證）
                    theoretical_parity = parity_validator.validate_with_theoretical_prices(
                        stock_price=current_price,
                        strike_price=strike_price,
                        risk_free_rate=risk_free_rate,
                        time_to_expiration=time_to_expiration_years,
                        volatility=volatility_estimate
                    )
                    
                    self.analysis_results['module19_put_call_parity'] = {
                        'market_prices': parity_result.to_dict(),
                        'theoretical_prices': theoretical_parity.to_dict()
                    }
                    
                    if parity_result.arbitrage_opportunity:
                        logger.info(f"✓ 模塊19完成: Put-Call Parity 驗證 (發現套利機會! 偏離=${parity_result.deviation:.4f})")
                    else:
                        logger.info(f"✓ 模塊19完成: Put-Call Parity 驗證 (無套利機會, 偏離=${parity_result.deviation:.4f})")
            except Exception as exc:
                logger.warning("⚠ 模塊19執行失敗: %s", exc)
            
            # 第4步: 生成報告
            logger.info("\n→ 第4步: 生成分析報告...")
            report = self.report_generator.generate(
                ticker=ticker,
                analysis_date=analysis_data['analysis_date'],
                raw_data=analysis_data,
                calculation_results=self.analysis_results,
                data_fetcher=self.fetcher  # 傳遞 data_fetcher 以獲取 API 狀態
            )
            
            logger.info(f"\n✓ 分析完成！結果已生成")
            logger.info("=" * 70)
            
            return {
                'status': 'success',
                'ticker': ticker,
                'timestamp': datetime.now(),
                'raw_data': analysis_data,
                'calculations': self.analysis_results,
                'report': report
            }
            
        except Exception as e:
            logger.error(f"\n✗ 分析失敗: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }


def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description='美股期權分析系統 - 基於《期權制勝》書籍'
    )
    parser.add_argument('--ticker', type=str, required=True,
                       help='股票代碼 (例: AAPL, MSFT)')
    parser.add_argument('--expiration', type=str, default=None,
                       help='期權到期日期 (格式: YYYY-MM-DD, 可選)')
    parser.add_argument('--confidence', type=float, default=1.0,
                       choices=[1.0, 1.28, 1.645, 2.0],
                       help='IV 信心度 Z 值 (1.0=68%%, 1.28=80%%, 1.645=90%%, 2.0=95%%)')
    parser.add_argument('--strike', type=float, default=None,
                       help='期權行使價 (美元, 可選)')
    parser.add_argument('--premium', type=float, default=None,
                       help='期權價格 (美元, 可選)')
    parser.add_argument('--type', type=str, default=None, choices=['C', 'P', 'c', 'p'],
                       help='期權類型: C (Call) 或 P (Put)')
    parser.add_argument('--use-ibkr', action='store_true', default=None,
                       help='使用 IBKR 數據源 (需要 TWS/Gateway 運行)')
    
    args = parser.parse_args()
    
    # 啟動系統
    system = OptionsAnalysisSystem()
    results = system.run_complete_analysis(
        ticker=args.ticker,
        expiration=args.expiration,
        confidence=args.confidence,
        use_ibkr=args.use_ibkr,
        strike=args.strike,
        premium=args.premium,
        option_type=args.type
    )
    
    # 輸出結果
    if results['status'] == 'success':
        print("\n" + "=" * 70)
        print("分析成功！")
        print("=" * 70)
        print(f"股票: {results['ticker']}")
        print(f"\n計算結果:")
        
        for module, data in results['calculations'].items():
            print(f"\n{module}:")
            for key, value in data.items():
                print(f"  {key}: {value}")
        
        print(f"\n報告文件:")
        for file_type, file_path in results['report'].items():
            if file_type != 'timestamp':
                print(f"  {file_type}: {file_path}")
        
        print("=" * 70)
    else:
        print(f"\n✗ 分析失敗: {results['message']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
