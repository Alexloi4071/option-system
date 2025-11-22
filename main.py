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
# Module 20: 基本面健康檢查
from calculation_layer.module20_fundamental_health import FundamentalHealthCalculator
# 新增: 策略推薦
from calculation_layer.strategy_recommendation import StrategyRecommender
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
    
    def __init__(self, use_ibkr: bool = None):
        """
        初始化系統
        
        參數:
            use_ibkr: 是否使用 IBKR（None 時從 settings 讀取）
        """
        logger.info("=" * 70)
        logger.info("期權分析系統啟動")
        logger.info(f"系統版本: {settings.VERSION}")
        logger.info(f"當前時間: {datetime.now()}")
        logger.info("=" * 70)
        
        self.fetcher = DataFetcher(use_ibkr=use_ibkr)
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
            
            logger.info("* 模塊1完成: 多信心度計算 + 單一信心度 (90%)")
            
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
            logger.info("* 模塊2完成: 公允值計算")
            
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
            
            # 記錄行使價選擇信息（用於報告）
            if strike_price:
                diff = current_price - strike_price
                if abs(diff) < 2.5:
                    moneyness = "ATM（平價）"
                elif diff > 0:
                    moneyness = f"ITM（價內 ${diff:.2f}）"
                else:
                    moneyness = f"OTM（價外 ${-diff:.2f}）"
                
                self.analysis_results['strike_selection'] = {
                    'strike_price': strike_price,
                    'current_price': current_price,
                    'difference': diff,
                    'moneyness': moneyness,
                    'note': f"選擇最接近當前股價的行使價"
                }
                logger.info(f"* 行使價選擇: ${strike_price:.2f} ({moneyness})")
                logger.info(f"  當前股價: ${current_price:.2f}")
            
            # ! 模塊3 已移至 Module 15 之後執行（需要使用期權理論價而非股票遠期價）
            # 原位置的 Module 3 調用已註釋，請參見 Module 19 之後的新實現
            
            # 模塊4: PE估值（使用真實 PE，優先 Forward PE）
            try:
                eps = analysis_data.get('eps')
                # ✅ 優先使用 Forward PE（更準確），否則使用 TTM PE
                pe_multiple = analysis_data.get('forward_pe') or analysis_data.get('pe_ratio')
                
                # 如果沒有真實 PE，才使用默認值（並記錄警告）
                if not pe_multiple or pe_multiple <= 0:
                    pe_multiple = settings.PE_NORMAL
                    logger.warning(f"! 未獲取到真實 PE，使用默認值 {settings.PE_NORMAL}")
                
                if eps and pe_multiple and eps > 0 and pe_multiple > 0:
                    pe_calc = PEValuationCalculator()
                    pe_result = pe_calc.calculate(
                        eps=eps,
                        pe_multiple=pe_multiple,
                        current_price=current_price,
                        calculation_date=analysis_date_str
                    )
                    
                    # 添加 PEG 分析（如果有）
                    result_dict = pe_result.to_dict()
                    peg_ratio = analysis_data.get('peg_ratio')
                    if peg_ratio:
                        result_dict['peg_ratio'] = round(peg_ratio, 2)
                        # 使用 PEG 判斷估值
                        if peg_ratio < 1.0:
                            result_dict['peg_valuation'] = "低估（PEG < 1）"
                        elif peg_ratio < 2.0:
                            result_dict['peg_valuation'] = "合理（PEG 1-2）"
                        else:
                            result_dict['peg_valuation'] = "高估（PEG > 2）"
                    
                    self.analysis_results['module4_pe_valuation'] = result_dict
                    logger.info("* 模塊4完成: PE估值（使用真實 PE）")
            except Exception as exc:
                logger.warning("! 模塊4執行失敗: %s", exc)
            
            # 模塊5: 利率與PE關係（使用真實 PE）
            try:
                long_term_rate = analysis_data.get('risk_free_rate')
                # ✅ 優先使用 Forward PE
                current_pe = analysis_data.get('forward_pe') or analysis_data.get('pe_ratio')
                
                if long_term_rate and current_pe and long_term_rate > 0 and current_pe > 0:
                    rate_pe_calc = RatePERelationCalculator()
                    rate_pe_result = rate_pe_calc.calculate(
                        long_term_rate=long_term_rate,
                        current_pe=current_pe,
                        calculation_date=analysis_date_str
                    )
                    
                    # 添加 PEG 和行業分析（美國市場標準）
                    result_dict = rate_pe_result.to_dict()
                    peg_ratio = analysis_data.get('peg_ratio')
                    sector = analysis_data.get('sector', 'Unknown')
                    
                    # 美國市場行業 PE 範圍
                    sector_pe_ranges = {
                        'Technology': (25, 40),
                        'Communication Services': (15, 25),
                        'Consumer Discretionary': (20, 30),
                        'Consumer Staples': (18, 25),
                        'Healthcare': (20, 30),
                        'Financials': (10, 15),
                        'Industrials': (15, 25),
                        'Energy': (10, 20),
                        'Utilities': (15, 20),
                        'Real Estate': (20, 30),
                        'Materials': (12, 18)
                    }
                    
                    # 行業 PE 分析
                    if sector and sector in sector_pe_ranges:
                        pe_min, pe_max = sector_pe_ranges[sector]
                        result_dict['行業'] = sector
                        result_dict['行業PE範圍'] = f"{pe_min}-{pe_max}"
                        
                        if current_pe < pe_min:
                            result_dict['行業比較'] = f"* PE {current_pe:.1f} 低於行業範圍（{pe_min}-{pe_max}）"
                        elif current_pe > pe_max:
                            result_dict['行業比較'] = f"! PE {current_pe:.1f} 高於行業範圍（{pe_min}-{pe_max}）"
                        else:
                            result_dict['行業比較'] = f"* PE {current_pe:.1f} 在行業範圍內（{pe_min}-{pe_max}）"
                    else:
                        result_dict['行業'] = sector or 'Unknown'
                        result_dict['行業比較'] = "無行業數據"
                    
                    # PEG 分析（美國市場標準）
                    if peg_ratio:
                        result_dict['peg_ratio'] = round(peg_ratio, 2)
                        
                        if peg_ratio < 1.0:
                            peg_評估 = f"* PEG={peg_ratio:.1f}<1.0，估值吸引"
                        elif peg_ratio < 1.5:
                            peg_評估 = f"* PEG={peg_ratio:.1f}<1.5，估值合理"
                        elif peg_ratio < 2.0:
                            peg_評估 = f"! PEG={peg_ratio:.1f}<2.0，估值略高"
                        else:
                            peg_評估 = f"! PEG={peg_ratio:.1f}>2.0，估值偏高"
                        
                        result_dict['PEG評估'] = peg_評估
                    else:
                        result_dict['PEG評估'] = "無 PEG 數據"
                    
                    # 綜合評估（三層分析）
                    評估要點 = []
                    評估要點.append(f"利率基準 PE={result_dict['reasonable_pe']:.1f}")
                    
                    if '行業PE範圍' in result_dict:
                        評估要點.append(f"行業範圍={result_dict['行業PE範圍']}")
                    
                    if peg_ratio:
                        評估要點.append(f"PEG={peg_ratio:.1f}")
                    
                    result_dict['評估框架'] = " | ".join(評估要點)
                    result_dict['說明'] = (
                        "基於美國市場標準：1) 利率基準 PE（理論最低），"
                        "2) 行業平均 PE（同業比較），3) PEG 比率（增長調整）"
                    )
                    
                    self.analysis_results['module5_rate_pe_relation'] = result_dict
                    logger.info("* 模塊5完成: 利率與PE關係（含 PEG 綜合分析）")
            except Exception as exc:
                logger.warning("! 模塊5執行失敗: %s", exc)
            
            # 模塊6: 對沖量
            try:
                hedge_calc = HedgeQuantityCalculator()
                hedge_result = hedge_calc.calculate(
                    stock_quantity=default_stock_quantity,
                    stock_price=current_price,
                    calculation_date=analysis_date_str
                )
                self.analysis_results['module6_hedge_quantity'] = hedge_result.to_dict()
                logger.info("* 模塊6完成: 對沖量")
            except Exception as exc:
                logger.warning("! 模塊6執行失敗: %s", exc)
            
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
                        logger.info("* 模塊7完成: Long Call 損益")
                except Exception as exc:
                    logger.warning("! 模塊7執行失敗: %s", exc)
                
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
                        logger.info("* 模塊8完成: Long Put 損益")
                except Exception as exc:
                    logger.warning("! 模塊8執行失敗: %s", exc)
                
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
                        logger.info("* 模塊9完成: Short Call 損益")
                except Exception as exc:
                    logger.warning("! 模塊9執行失敗: %s", exc)
                
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
                        logger.info("* 模塊10完成: Short Put 損益")
                except Exception as exc:
                    logger.warning("! 模塊10執行失敗: %s", exc)
            
            # 模塊11: 合成正股
            try:
                if strike_price and call_last_price >= 0 and put_last_price >= 0:
                    synthetic_calc = SyntheticStockCalculator()
                    synthetic_result = synthetic_calc.calculate(
                        strike_price=strike_price,
                        call_premium=call_last_price,
                        put_premium=put_last_price,
                        current_stock_price=current_price,
                        risk_free_rate=risk_free_rate,
                        time_to_expiration=time_to_expiration_years,
                        calculation_date=analysis_date_str
                    )
                    self.analysis_results['module11_synthetic_stock'] = synthetic_result.to_dict()
                    logger.info("* 模塊11完成: 合成正股")
            except Exception as exc:
                logger.warning("! 模塊11執行失敗: %s", exc)
            
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
                    logger.info("* 模塊12完成: 年息收益率")
            except Exception as exc:
                logger.warning("! 模塊12執行失敗: %s", exc)
            
            # 模塊13: 倉位分析（增強版 - 包含 Finviz 數據）
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
                    
                    result_dict = position_result.to_dict()
                    
                    # ✅ 添加 Finviz 所有權結構數據
                    insider_own = analysis_data.get('insider_own')
                    inst_own = analysis_data.get('inst_own')
                    short_float = analysis_data.get('short_float')
                    avg_volume = analysis_data.get('avg_volume')
                    
                    if insider_own is not None:
                        result_dict['insider_ownership'] = round(insider_own, 2)
                        if insider_own > 10:
                            result_dict['insider_note'] = "⚠️ 內部人持股高（>10%），可能有重大消息"
                        elif insider_own > 5:
                            result_dict['insider_note'] = "✓ 內部人持股正常（5-10%）"
                        else:
                            result_dict['insider_note'] = "內部人持股低（<5%）"
                    
                    if inst_own is not None:
                        result_dict['institutional_ownership'] = round(inst_own, 2)
                        if inst_own > 70:
                            result_dict['inst_note'] = "✓ 機構持股高（>70%），股票穩定"
                        elif inst_own > 40:
                            result_dict['inst_note'] = "✓ 機構持股正常（40-70%）"
                        else:
                            result_dict['inst_note'] = "⚠️ 機構持股低（<40%），流動性可能較差"
                    
                    if short_float is not None:
                        result_dict['short_float'] = round(short_float, 2)
                        if short_float > 10:
                            result_dict['short_note'] = "⚠️ 做空比例高（>10%），可能有軋空風險"
                        elif short_float > 5:
                            result_dict['short_note'] = "做空比例中等（5-10%）"
                        else:
                            result_dict['short_note'] = "✓ 做空比例低（<5%）"
                    
                    if avg_volume and call_volume:
                        volume_ratio = call_volume / avg_volume
                        result_dict['volume_vs_avg'] = round(volume_ratio, 2)
                        if volume_ratio > 2.0:
                            result_dict['volume_note'] = "⚠️ 成交量異常放大（>2倍平均）"
                        elif volume_ratio > 1.5:
                            result_dict['volume_note'] = "成交量放大（1.5-2倍平均）"
                        elif volume_ratio < 0.5:
                            result_dict['volume_note'] = "⚠️ 成交量萎縮（<0.5倍平均）"
                        else:
                            result_dict['volume_note'] = "✓ 成交量正常"
                    
                    self.analysis_results['module13_position_analysis'] = result_dict
                    logger.info("✓ 模塊13完成: 倉位分析（含所有權結構）")
            except Exception as exc:
                logger.warning("⚠ 模塊13執行失敗: %s", exc)
            
            # 模塊14: 12監察崗位（增強版 - 使用 Finviz ATR/RSI）
            try:
                # ✅ 確保 Delta 有值 (默認 0.5 ATM)
                delta_value = call_delta if call_delta is not None else 0.5
                
                # ✅ 確保 VIX 有值 (默認 20.0)
                vix_value = analysis_data.get('vix')
                if vix_value is None:
                    vix_value = 20.0
                    logger.warning("! 未獲取到 VIX，使用默認值 20.0")
                
                # ✅ 優先使用 Finviz 的標準 ATR
                atr_value = analysis_data.get('atr')
                if not atr_value or atr_value <= 0:
                    # 降級：使用 High-Low 估算
                    stock_high = analysis_data.get('stock_high')
                    stock_low = analysis_data.get('stock_low')
                    if stock_high is not None and stock_low is not None:
                        atr_value = max(0.0, float(stock_high) - float(stock_low))
                        logger.info(f"  使用 High-Low 估算 ATR: {atr_value:.2f}")
                    else:
                        atr_value = current_price * 0.02 # 默認 2%
                        logger.info(f"  使用默認 ATR (2%): {atr_value:.2f}")
                else:
                    logger.info(f"  使用 Finviz ATR: {atr_value:.2f}")
                
                # 寬鬆的執行條件
                if call_volume >= 0 and call_open_interest >= 0:
                    monitoring_calc = MonitoringPostsCalculator()
                    monitoring_result = monitoring_calc.calculate(
                        stock_price=current_price,
                        option_premium=call_last_price,
                        iv=analysis_data['implied_volatility'],
                        delta=delta_value,
                        open_interest=call_open_interest,
                        volume=call_volume,
                        bid_ask_spread=bid_ask_spread,
                        atr=atr_value,  # ✅ 使用 Finviz ATR
                        vix=vix_value,
                        dividend_date=analysis_data.get('ex_dividend_date', ''),
                        earnings_date=analysis_data.get('next_earnings_date', ''),
                        expiration_date=analysis_data.get('expiration_date', ''),
                        calculation_date=analysis_date_str
                    )
                    
                    result_dict = monitoring_result.to_dict()
                    
                    self.analysis_results['module14_monitoring_posts'] = result_dict
                    logger.info("* 模塊14完成: 12監察崗位")
                else:
                    logger.warning("! 模塊14跳過: 缺少成交量或持倉量數據")
            except Exception as exc:
                logger.warning("! 模塊14執行失敗: %s", exc)
            
            # ========== 新增模塊 (Module 15-19) ==========
            logger.info("\n→ 運行新增模塊 (Module 15-19)...")
            
            # 準備新模塊所需的共同參數
            # 📍 FIX: DataFetcher 返回的是百分比形式,需轉換為小數
            risk_free_rate_raw = analysis_data.get('risk_free_rate', 4.5) or 4.5
            risk_free_rate = risk_free_rate_raw / 100.0  # 轉換: 4.35% → 0.0435
            
            # 根據天數類型計算年化時間
            # 如果 DataFetcher 使用了交易日計算器，則 days_to_expiration 為交易日，應除以 252
            # 否則為日曆日，應除以 365
            if getattr(self.fetcher, 'trading_days_calc', None):
                time_to_expiration_years = days_to_expiration / 252.0 if days_to_expiration else 0.004 # 1/252
                logger.info(f"  時間計算: 使用交易日標準 ({days_to_expiration}/252 = {time_to_expiration_years:.4f}年)")
            else:
                time_to_expiration_years = days_to_expiration / 365.0 if days_to_expiration else 0.003 # 1/365
                logger.info(f"  時間計算: 使用日曆日標準 ({days_to_expiration}/365 = {time_to_expiration_years:.4f}年)")
            
            volatility_raw = analysis_data.get('implied_volatility', 25.0) or 25.0
            volatility_estimate = volatility_raw / 100.0  # 轉換: 25.5% → 0.255
            
            logger.info(f"共同參數: risk_free_rate={risk_free_rate:.4f}, "
                       f"time_to_expiration={time_to_expiration_years:.4f}年, "
                       f"volatility={volatility_estimate:.4f}")
            
            # 模塊15: Black-Scholes 期權定價（優先使用 API，失敗時降級到自主計算）
            try:
                if strike_price and strike_price > 0:
                    # 嘗試從 API 獲取理論價格
                    api_call_price = None
                    api_put_price = None
                    data_source = "API"
                    
                    try:
                        # 方案1: 嘗試從 API 獲取
                        api_result = self.fetcher.get_option_theoretical_price(
                            ticker=ticker,
                            strike=strike_price,
                            expiration=analysis_data.get('expiration_date'),
                            stock_price=current_price,
                            risk_free_rate=risk_free_rate,
                            time_to_expiration=time_to_expiration_years,
                            volatility=volatility_estimate
                        )
                        
                        if api_result:
                            api_call_price = api_result.get('call_price')
                            api_put_price = api_result.get('put_price')
                            
                            # 檢查 API 數據是否有效
                            if api_call_price and api_call_price > 0 and api_put_price and api_put_price > 0:
                                logger.info(f"  使用 API 提供的理論價格")
                            else:
                                api_call_price = None
                                api_put_price = None
                    except Exception as e:
                        logger.debug(f"  API 獲取失敗: {e}，降級到自主計算")
                    
                    # 方案2: 如果 API 失敗或數據無效，使用自主計算
                    if not api_call_price or not api_put_price:
                        logger.info(f"  使用自主計算 (Black-Scholes 模型)")
                        data_source = "Self-Calculated"
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
                            },
                            'data_source': data_source
                        }
                        logger.info(f"* 模塊15完成: Black-Scholes 定價 (Call=${bs_call_result.option_price:.2f}, Put=${bs_put_result.option_price:.2f}) [{data_source}]")
                    else:
                        # 使用 API 數據
                        self.analysis_results['module15_black_scholes'] = {
                            'call': {
                                'option_price': api_call_price,
                                'stock_price': current_price,
                                'strike_price': strike_price,
                                'model': 'Black-Scholes'
                            },
                            'put': {
                                'option_price': api_put_price,
                                'stock_price': current_price,
                                'strike_price': strike_price,
                                'model': 'Black-Scholes'
                            },
                            'parameters': {
                                'stock_price': current_price,
                                'strike_price': strike_price,
                                'risk_free_rate': risk_free_rate,
                                'time_to_expiration': time_to_expiration_years,
                                'volatility': volatility_estimate
                            },
                            'data_source': data_source
                        }
                        logger.info(f"* 模塊15完成: Black-Scholes 定價 (Call=${api_call_price:.2f}, Put=${api_put_price:.2f}) [{data_source}]")
            except Exception as exc:
                logger.warning("! 模塊15執行失敗: %s", exc)
            
            # 模塊16: Greeks 計算（優先使用 API，失敗時降級到自主計算）
            try:
                if strike_price and strike_price > 0:
                    # 嘗試從 API 獲取 Greeks
                    api_call_greeks = None
                    api_put_greeks = None
                    data_source = "API"
                    
                    try:
                        # 方案1: 嘗試從 API 獲取 Call Greeks
                        api_call_greeks = self.fetcher.get_option_greeks(
                            ticker=ticker,
                            strike=strike_price,
                            expiration=analysis_data.get('expiration_date'),
                            option_type='C',
                            stock_price=current_price,
                            iv=volatility_estimate
                        )
                        
                        # 嘗試從 API 獲取 Put Greeks
                        api_put_greeks = self.fetcher.get_option_greeks(
                            ticker=ticker,
                            strike=strike_price,
                            expiration=analysis_data.get('expiration_date'),
                            option_type='P',
                            stock_price=current_price,
                            iv=volatility_estimate
                        )
                        
                        # 檢查 API 數據是否有效（至少要有 Delta）
                        if api_call_greeks and api_call_greeks.get('delta') is not None and \
                           api_put_greeks and api_put_greeks.get('delta') is not None:
                            logger.info(f"  使用 API 提供的 Greeks")
                        else:
                            api_call_greeks = None
                            api_put_greeks = None
                    except Exception as e:
                        logger.debug(f"  API 獲取失敗: {e}，降級到自主計算")
                    
                    # 方案2: 如果 API 失敗或數據無效，使用自主計算
                    if not api_call_greeks or not api_put_greeks:
                        logger.info(f"  使用自主計算 (Greeks 公式)")
                        data_source = "Self-Calculated"
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
                            'put': put_greeks.to_dict(),
                            'data_source': data_source
                        }
                        logger.info(f"* 模塊16完成: Greeks 計算 (Call Delta={call_greeks.delta:.4f}, Gamma={call_greeks.gamma:.6f}) [{data_source}]")
                    else:
                        # 使用 API 數據
                        self.analysis_results['module16_greeks'] = {
                            'call': api_call_greeks,
                            'put': api_put_greeks,
                            'data_source': data_source
                        }
                        logger.info(f"* 模塊16完成: Greeks 計算 (Call Delta={api_call_greeks.get('delta', 0):.4f}) [{data_source}]")
            except Exception as exc:
                logger.warning("! 模塊16執行失敗: %s", exc)
            
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
                        logger.info(f"* 模塊17完成: 隱含波動率計算 (Call IV={call_iv_result.implied_volatility*100:.2f}%, {call_iv_result.iterations}次迭代)")
                    else:
                        logger.warning(f"! 模塊17: Call IV 未收斂 ({call_iv_result.iterations}次迭代)")
            except Exception as exc:
                logger.warning("! 模塊17執行失敗: %s", exc)
            
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
                        logger.info(f"* 模塊18完成: 歷史波動率計算 (HV30={hv_30.historical_volatility*100:.2f}%, IV/HV={iv_hv_ratio.iv_hv_ratio:.2f})")
                    else:
                        self.analysis_results['module18_historical_volatility'] = {
                            'hv_results': {k: v.to_dict() for k, v in hv_results.items()}
                        }
                        logger.info("* 模塊18完成: 歷史波動率計算")
                else:
                    logger.info("! 模塊18跳過: 歷史數據不足")
            except Exception as exc:
                logger.warning("! 模塊18執行失敗: %s", exc)
            
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
                        logger.info(f"* 模塊19完成: Put-Call Parity 驗證 (發現套利機會! 偏離=${parity_result.deviation:.4f})")
                    else:
                        logger.info(f"* 模塊19完成: Put-Call Parity 驗證 (無套利機會, 偏離=${parity_result.deviation:.4f})")
            except Exception as exc:
                logger.warning("! 模塊19執行失敗: %s", exc)
            
            # ========== 模塊3: 套戥水位 (使用期權理論價) ==========
            # 注意: Module 3 必須在 Module 15 (Black-Scholes) 之後執行
            # 原因: 需要使用期權理論價而非股票遠期價來計算套戥水位
            logger.info("\n→ 運行 Module 3: 套戥水位計算（使用期權理論價）...")
            try:
                # ✅ Task 6: 增強無期權理論價處理
                # 從 Module 15 獲取期權理論價
                bs_results = self.analysis_results.get('module15_black_scholes')
                
                # 詳細檢查前置條件
                logger.info("  檢查前置條件:")
                logger.info(f"    市場期權價格: ${call_last_price:.2f}" if call_last_price > 0 else "    x 市場期權價格不可用")
                logger.info(f"    Module 15 結果: {'* 可用' if bs_results else 'x 不可用'}")
                
                if call_last_price > 0 and bs_results:
                    # 獲取 Call 期權理論價
                    call_theoretical_price = bs_results.get('call', {}).get('option_price')
                    
                    if call_theoretical_price and call_theoretical_price > 0:
                        logger.info(f"    期權理論價: ${call_theoretical_price:.2f}")
                        logger.info("  * 所有前置條件滿足，執行套戥水位計算...")
                        
                        arb_calc = ArbitrageSpreadCalculator()
                        arb_result = arb_calc.calculate(
                            market_option_price=call_last_price,
                            fair_value=call_theoretical_price,  # ✅ 使用期權理論價
                            bid_price=call_bid,
                            ask_price=call_ask,
                            calculation_date=analysis_date_str
                        )
                        
                        # 在結果中添加數據來源標註
                        result_dict = arb_result.to_dict()
                        result_dict['note'] = '使用 Black-Scholes 期權理論價（非股票遠期價）'
                        result_dict['theoretical_price_source'] = 'Module 15 (Black-Scholes)'
                        result_dict['theoretical_price'] = round(call_theoretical_price, 2)
                        result_dict['market_price'] = round(call_last_price, 2)
                        
                        self.analysis_results['module3_arbitrage_spread'] = result_dict
                        logger.info(f"* 模塊3完成: 套戥水位")
                        logger.info(f"  市場價: ${call_last_price:.2f}")
                        logger.info(f"  理論價: ${call_theoretical_price:.2f}")
                        logger.info(f"  價差: ${arb_result.arbitrage_spread:.2f} ({arb_result.spread_percentage:.2f}%)")
                        logger.info(f"  建議: {arb_result.recommendation}")
                    else:
                        # ✅ Task 6: 詳細記錄無期權理論價的情況
                        logger.warning("! 模塊3跳過: 無法獲取期權理論價")
                        logger.warning("  原因: Module 15 未返回有效的期權理論價")
                        logger.warning("  可能原因:")
                        logger.warning("    1. Module 15 計算失敗")
                        logger.warning("    2. 期權理論價為 0 或負數")
                        logger.warning("    3. 數據格式錯誤")
                        logger.warning("  建議: 檢查 Module 15 的執行日誌")
                        
                        self.analysis_results['module3_arbitrage_spread'] = {
                            'status': 'skipped',
                            'reason': '無法獲取期權理論價',
                            'module15_status': 'available' if bs_results else 'unavailable',
                            'theoretical_price': call_theoretical_price,
                            'degradation_note': '! 降級: 需要 Module 15 提供有效的期權理論價'
                        }
                else:
                    # ✅ Task 6: 詳細記錄缺少前置條件的情況
                    missing_conditions = []
                    if call_last_price <= 0:
                        missing_conditions.append('市場期權價格')
                    if not bs_results:
                        missing_conditions.append('Module 15 結果')
                    
                    logger.warning(f"! 模塊3跳過: 缺少前置條件")
                    logger.warning(f"  缺少: {', '.join(missing_conditions)}")
                    logger.warning(f"  說明:")
                    if call_last_price <= 0:
                        logger.warning(f"    - 市場期權價格無效 (${call_last_price:.2f})")
                    if not bs_results:
                        logger.warning(f"    - Module 15 未執行或執行失敗")
                    logger.warning(f"  建議: 確保期權鏈數據可用且 Module 15 成功執行")
                    
                    self.analysis_results['module3_arbitrage_spread'] = {
                        'status': 'skipped',
                        'reason': f'缺少前置條件: {", ".join(missing_conditions)}',
                        'market_price': call_last_price,
                        'module15_available': bs_results is not None,
                        'degradation_note': '! 降級: 套戥水位計算需要市場價格和期權理論價'
                    }
            except Exception as exc:
                # ✅ Task 6: 增強錯誤處理
                logger.error(f"x 模塊3執行失敗: {exc}")
                logger.error(f"  錯誤類型: {type(exc).__name__}")
                logger.error(f"  建議: 檢查數據格式或聯繫技術支持")
                
                self.analysis_results['module3_arbitrage_spread'] = {
                    'status': 'error',
                    'reason': str(exc),
                    'error_type': type(exc).__name__,
                    'degradation_note': '! 降級: 模塊執行失敗，請檢查日誌'
                }
            
            # ========== Module 20: 基本面健康檢查 (使用 Finviz 數據) ==========
            logger.info("\n→ 運行 Module 20: 基本面健康檢查...")
            try:
                # ✅ Task 6: 增強數據不足處理
                # 從 analysis_data 獲取 Finviz 數據
                peg_ratio = analysis_data.get('peg_ratio')
                roe = analysis_data.get('roe')
                profit_margin = analysis_data.get('profit_margin')
                debt_eq = analysis_data.get('debt_eq')
                inst_own = analysis_data.get('inst_own')
                
                # 詳細記錄每個指標的狀態
                logger.info("  檢查基本面數據可用性:")
                metrics_status = {
                    'peg_ratio': peg_ratio,
                    'roe': roe,
                    'profit_margin': profit_margin,
                    'debt_eq': debt_eq,
                    'inst_own': inst_own
                }
                
                for metric_name, metric_value in metrics_status.items():
                    if metric_value is not None:
                        logger.info(f"    * {metric_name}: {metric_value}")
                    else:
                        logger.warning(f"    x {metric_name}: 數據不可用")
                
                # 計算可用指標數量
                available_metrics = sum([v is not None for v in metrics_status.values()])
                
                # 如果 >= 3 個指標，執行計算
                if available_metrics >= 3:
                    logger.info(f"  * 數據充足 ({available_metrics}/5 個指標)，執行基本面健康檢查...")
                    
                    health_calc = FundamentalHealthCalculator()
                    health_result = health_calc.calculate(
                        ticker=ticker,
                        peg_ratio=peg_ratio,
                        roe=roe,
                        profit_margin=profit_margin,
                        debt_eq=debt_eq,
                        inst_own=inst_own,
                        calculation_date=analysis_date_str
                    )
                    
                    # 在結果中標註使用的指標數量和數據來源
                    result_dict = health_result.to_dict()
                    result_dict['data_source'] = 'Finviz'
                    result_dict['available_metrics'] = available_metrics
                    result_dict['required_metrics'] = 3
                    result_dict['missing_metrics'] = [k for k, v in metrics_status.items() if v is None]
                    
                    self.analysis_results['module20_fundamental_health'] = result_dict
                    logger.info(f"* 模塊20完成: 基本面健康檢查 (使用 {available_metrics}/5 個指標)")
                    logger.info(f"  健康分數: {health_result.health_score}/100, 等級: {health_result.grade}")
                else:
                    # ✅ Task 6: 增強降級處理 - 如果 < 3 個指標，跳過執行並詳細記錄原因
                    missing_metrics = [k for k, v in metrics_status.items() if v is None]
                    logger.warning(f"! 模塊20跳過: 基本面數據不足")
                    logger.warning(f"  需要: 至少 3/5 個指標")
                    logger.warning(f"  實際: {available_metrics}/5 個指標")
                    logger.warning(f"  缺失指標: {', '.join(missing_metrics)}")
                    logger.warning(f"  建議: 檢查 Finviz 數據源或使用其他股票")
                    
                    self.analysis_results['module20_fundamental_health'] = {
                        'status': 'skipped',
                        'reason': f'數據不足 (僅 {available_metrics}/5 個指標)',
                        'available_metrics': available_metrics,
                        'required_metrics': 3,
                        'missing_metrics': missing_metrics,
                        'available_data': {k: v for k, v in metrics_status.items() if v is not None},
                        'degradation_note': '! 降級: 基本面健康檢查需要至少3個指標才能執行'
                    }
            except Exception as exc:
                # ✅ Task 6: 增強錯誤處理
                logger.error(f"x 模塊20執行失敗: {exc}")
                logger.error(f"  錯誤類型: {type(exc).__name__}")
                logger.error(f"  建議: 檢查數據格式或聯繫技術支持")
                
                self.analysis_results['module20_fundamental_health'] = {
                    'status': 'error',
                    'reason': str(exc),
                    'error_type': type(exc).__name__,
                    'degradation_note': '! 降級: 模塊執行失敗，請檢查日誌'
                }
            
            # 新增: 策略推薦引擎
            logger.info("\n→ 運行策略推薦引擎...")
            try:
                # 準備輸入數據
                # 1. 趨勢判斷 (簡單版: 價格 > MA20 > MA50)
                # 由於沒有 MA 數據，暫時使用價格與支持/阻力位關係
                sr_data = self.analysis_results.get('module1_support_resistance')
                trend = 'Sideways'
                support = 0
                resistance = 0
                
                if sr_data:
                    support = sr_data.get('support_level', 0)
                    resistance = sr_data.get('resistance_level', 0)
                    mid_point = (support + resistance) / 2
                    if current_price > mid_point * 1.05:
                        trend = 'Up'
                    elif current_price < mid_point * 0.95:
                        trend = 'Down'
                
                # 2. 估值判斷
                pe_data = self.analysis_results.get('module4_pe_valuation')
                valuation = 'Fair'
                if pe_data:
                    peg_val = pe_data.get('peg_valuation', '')
                    if '低估' in peg_val: valuation = 'Undervalued'
                    elif '高估' in peg_val: valuation = 'Overvalued'
                
                # 3. 波動率分析
                hv_data = self.analysis_results.get('module18_historical_volatility')
                iv_hv_ratio = 1.0
                if hv_data and 'iv_hv_comparison' in hv_data:
                    iv_hv_ratio = hv_data['iv_hv_comparison'].get('ratio', 1.0)
                
                # 執行推薦
                recommender = StrategyRecommender()
                recommendations = recommender.recommend(
                    current_price=current_price,
                    iv_rank=50.0, # 暫時使用中位數，後續可從 API 獲取
                    iv_percentile=50.0,
                    iv_hv_ratio=iv_hv_ratio,
                    support_level=support,
                    resistance_level=resistance,
                    trend=trend,
                    valuation=valuation,
                    days_to_expiry=int(days_to_expiration) if days_to_expiration else 30
                )
                
                self.analysis_results['strategy_recommendations'] = [r.to_dict() for r in recommendations]
                logger.info(f"* 策略推薦完成: 生成 {len(recommendations)} 個建議")
                
            except Exception as exc:
                logger.warning("! 策略推薦執行失敗: %s", exc)

            # 第4步: 生成報告
            logger.info("\n→ 第4步: 生成分析報告...")
            report = self.report_generator.generate(
                ticker=ticker,
                analysis_date=analysis_data['analysis_date'],
                raw_data=analysis_data,
                calculation_results=self.analysis_results,
                data_fetcher=self.fetcher  # 傳遞 data_fetcher 以獲取 API 狀態
            )
            
            logger.info(f"\n* 分析完成！結果已生成")
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
            logger.error(f"\nx 分析失敗: {e}")
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
            # 處理列表類型的數據（如 module7_long_call）
            if isinstance(data, list):
                for i, item in enumerate(data):
                    print(f"  場景 {i+1}:")
                    if isinstance(item, dict):
                        for key, value in item.items():
                            print(f"    {key}: {value}")
                    else:
                        print(f"    {item}")
            # 處理字典類型的數據
            elif isinstance(data, dict):
                for key, value in data.items():
                    print(f"  {key}: {value}")
            # 處理其他類型
            else:
                print(f"  {data}")
        
        print(f"\n報告文件:")
        for file_type, file_path in results['report'].items():
            if file_type != 'timestamp':
                print(f"  {file_type}: {file_path}")
        
        print("=" * 70)
    else:
        print(f"\n x 分析失敗: {results['message']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
