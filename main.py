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
# 新增模塊 (Module 21 - 動量過濾器)
from calculation_layer.module21_momentum_filter import MomentumFilter
from calculation_layer.module18_historical_volatility import HistoricalVolatilityCalculator
from calculation_layer.module19_put_call_parity import PutCallParityValidator
# Module 20: 基本面健康檢查
from calculation_layer.module20_fundamental_health import FundamentalHealthCalculator
# Module 22: 最佳行使價分析
from calculation_layer.module22_optimal_strike import OptimalStrikeCalculator
# Module 23: 動態IV閾值
from calculation_layer.module23_dynamic_iv_threshold import DynamicIVThresholdCalculator
# Module 24: 技術方向分析
from calculation_layer.module24_technical_direction import TechnicalDirectionAnalyzer
# Module 25: 波動率微笑分析
from calculation_layer.module25_volatility_smile import VolatilitySmileAnalyzer
# Module 26: Long 期權成本效益分析
from calculation_layer.module26_long_option_analysis import LongOptionAnalyzer
# 新增: 策略推薦
from calculation_layer.strategy_recommendation import StrategyRecommender
from output_layer.report_generator import ReportGenerator
from output_layer.output_manager import OutputPathManager
from output_layer.strategy_scenario_generator import StrategyScenarioGenerator


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
        
        # 初始化 OutputPathManager 用於按股票代號分類存儲
        self.output_manager = OutputPathManager(base_output_dir="output")
        self.report_generator = ReportGenerator(output_manager=self.output_manager)
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
            
            # 檢查是否需要重新初始化 DataFetcher
            # 只有當 use_ibkr 設置與現有 fetcher 不同時才重新初始化
            need_reinit = False
            if use_ibkr is not None:
                current_use_ibkr = getattr(self.fetcher, 'use_ibkr', None)
                if current_use_ibkr != use_ibkr:
                    need_reinit = True
            
            if need_reinit:
                # 先斷開舊的 IBKR 連接，避免 Client ID 衝突
                if hasattr(self, 'fetcher') and self.fetcher and hasattr(self.fetcher, 'ibkr_client'):
                    if self.fetcher.ibkr_client:
                        try:
                            self.fetcher.ibkr_client.disconnect()
                            logger.info("已斷開舊的 IBKR 連接")
                        except Exception as e:
                            logger.warning(f"斷開舊 IBKR 連接時出錯: {e}")
                
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
            # 注意: days_to_expiration 來自 DataFetcher，可能是交易日或日曆日
            # 如果使用了交易日計算器，則為交易日；否則為日曆日
            is_calendar_days = not getattr(self.fetcher, 'trading_days_calc', None)
            
            sr_results_multi = sr_calc.calculate_multi_confidence(
                stock_price=analysis_data['current_price'],
                implied_volatility=analysis_data['implied_volatility'],
                days_to_expiration=int(days_to_expiration),
                confidence_levels=['68%', '80%', '90%', '95%', '99%']  # 用戶Excel的5個信心度
            )
            
            # 保存多信心度結果
            self.analysis_results['module1_support_resistance_multi'] = sr_results_multi
            
            # 兼容性: 保留單一信心度計算 (使用90%作為默認)
            # 新增: is_calendar_days 參數，自動將日曆日轉換為交易日
            sr_result_single = sr_calc.calculate(
                stock_price=analysis_data['current_price'],
                implied_volatility=analysis_data['implied_volatility'],
                days_to_expiration=int(days_to_expiration),
                z_score=1.645,  # 90%信心度
                is_calendar_days=is_calendar_days  # 新增: 日曆日/交易日標識
            )
            self.analysis_results['module1_support_resistance'] = sr_result_single.to_dict()
            
            logger.info(f"* 模塊1完成: 多信心度計算 + 單一信心度 (90%), 日曆日模式: {is_calendar_days}")
            
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
            put_bid = float(atm_put.get('bid', 0) or 0)
            put_ask = float(atm_put.get('ask', 0) or 0)
            
            # 使用 mid price（bid/ask 中間價）代替 lastPrice
            # 原因：lastPrice 可能是舊的成交價，而 IV 是用 bid/ask 計算的
            # 使用 mid price 可以確保期權價格與 IV 一致
            call_last_price_raw = float(atm_call.get('lastPrice', 0) or 0)
            put_last_price_raw = float(atm_put.get('lastPrice', 0) or 0)
            
            # 計算 mid price
            if call_bid > 0 and call_ask > 0:
                call_mid_price = (call_bid + call_ask) / 2
                # 如果 mid price 與 lastPrice 差異超過 20%，使用 mid price
                if call_last_price_raw > 0 and abs(call_mid_price - call_last_price_raw) / call_last_price_raw > 0.2:
                    logger.info(f"  Call: 使用 mid price ${call_mid_price:.2f} (lastPrice ${call_last_price_raw:.2f} 差異過大)")
                    call_last_price = call_mid_price
                else:
                    call_last_price = call_last_price_raw
            else:
                call_last_price = call_last_price_raw
            
            if put_bid > 0 and put_ask > 0:
                put_mid_price = (put_bid + put_ask) / 2
                if put_last_price_raw > 0 and abs(put_mid_price - put_last_price_raw) / put_last_price_raw > 0.2:
                    logger.info(f"  Put: 使用 mid price ${put_mid_price:.2f} (lastPrice ${put_last_price_raw:.2f} 差異過大)")
                    put_last_price = put_mid_price
                else:
                    put_last_price = put_last_price_raw
            else:
                put_last_price = put_last_price_raw
            call_volume = int(atm_call.get('volume', 0) or 0)
            call_open_interest = int(atm_call.get('openInterest', 0) or 0)
            # 新增 Put 成交量和未平倉量 (Requirements: 2.1, 2.2)
            put_volume = int(atm_put.get('volume', 0) or 0)
            put_open_interest = int(atm_put.get('openInterest', 0) or 0)
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
            
            # 模塊5: 利率與PE關係（使用真實 PE + 行業分析）
            try:
                long_term_rate = analysis_data.get('risk_free_rate')
                # ✅ 優先使用 Forward PE
                current_pe = analysis_data.get('forward_pe') or analysis_data.get('pe_ratio')
                # 新增: 獲取行業信息用於行業PE範圍判斷
                sector = analysis_data.get('sector')
                
                if long_term_rate and current_pe and long_term_rate > 0 and current_pe > 0:
                    rate_pe_calc = RatePERelationCalculator()
                    # 新增: 傳遞 sector 參數進行行業PE範圍判斷
                    rate_pe_result = rate_pe_calc.calculate(
                        long_term_rate=long_term_rate,
                        current_pe=current_pe,
                        sector=sector,  # 新增: 行業參數
                        calculation_date=analysis_date_str
                    )
                    
                    # 添加 PEG 和行業分析（美國市場標準）
                    result_dict = rate_pe_result.to_dict()
                    peg_ratio = analysis_data.get('peg_ratio')
                    sector_raw = analysis_data.get('sector', 'Unknown')
                    
                    # 行業映射表：將 Finviz/Finnhub 返回的行業名稱映射到標準 GICS 分類
                    # 這樣可以處理不同 API 返回的不同行業名稱
                    sector_mapping = {
                        # Finviz 返回的行業 -> 標準分類
                        'Media': 'Communication Services',
                        'Internet Content & Information': 'Communication Services',
                        'Interactive Media & Services': 'Communication Services',
                        'Entertainment': 'Communication Services',
                        'Telecom Services': 'Communication Services',
                        'Software': 'Technology',
                        'Software - Infrastructure': 'Technology',
                        'Software - Application': 'Technology',
                        'Semiconductors': 'Technology',
                        'Semiconductor Equipment & Materials': 'Technology',
                        'Computer Hardware': 'Technology',
                        'Electronic Components': 'Technology',
                        'Information Technology Services': 'Technology',
                        'Consumer Electronics': 'Technology',
                        'Banks': 'Financials',
                        'Banks - Regional': 'Financials',
                        'Insurance': 'Financials',
                        'Asset Management': 'Financials',
                        'Financial Services': 'Financials',
                        'Credit Services': 'Financials',
                        'Capital Markets': 'Financials',
                        'Biotechnology': 'Healthcare',
                        'Drug Manufacturers': 'Healthcare',
                        'Medical Devices': 'Healthcare',
                        'Healthcare Plans': 'Healthcare',
                        'Retail - Cyclical': 'Consumer Discretionary',
                        'Auto Manufacturers': 'Consumer Discretionary',
                        'Restaurants': 'Consumer Discretionary',
                        'Apparel Retail': 'Consumer Discretionary',
                        'Consumer Cyclical': 'Consumer Discretionary',
                        'Beverages': 'Consumer Staples',
                        'Food Products': 'Consumer Staples',
                        'Household Products': 'Consumer Staples',
                        'Tobacco': 'Consumer Staples',
                        'Oil & Gas': 'Energy',
                        'Oil & Gas E&P': 'Energy',
                        'Oil & Gas Integrated': 'Energy',
                        'Aerospace & Defense': 'Industrials',
                        'Airlines': 'Industrials',
                        'Railroads': 'Industrials',
                        'Trucking': 'Industrials',
                        'REITs': 'Real Estate',
                        'Real Estate Services': 'Real Estate',
                        'Utilities - Regulated': 'Utilities',
                        'Utilities - Diversified': 'Utilities',
                        'Chemicals': 'Materials',
                        'Steel': 'Materials',
                        'Gold': 'Materials',
                    }
                    
                    # 嘗試映射行業，如果沒有映射則使用原始值
                    sector = sector_mapping.get(sector_raw, sector_raw)
                    
                    # 美國市場行業 PE 範圍（基於 GICS 標準分類）
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
                        'Materials': (12, 18),
                    }
                    
                    # 行業 PE 分析
                    if sector and sector in sector_pe_ranges:
                        pe_min, pe_max = sector_pe_ranges[sector]
                        # 顯示原始行業和映射後的標準分類
                        if sector_raw != sector:
                            result_dict['行業'] = f"{sector_raw} → {sector}"
                        else:
                            result_dict['行業'] = sector
                        result_dict['行業PE範圍'] = f"{pe_min}-{pe_max}"
                        
                        if current_pe < pe_min:
                            result_dict['行業比較'] = f"* PE {current_pe:.1f} 低於行業範圍（{pe_min}-{pe_max}）"
                        elif current_pe > pe_max:
                            result_dict['行業比較'] = f"! PE {current_pe:.1f} 高於行業範圍（{pe_min}-{pe_max}）"
                        else:
                            result_dict['行業比較'] = f"* PE {current_pe:.1f} 在行業範圍內（{pe_min}-{pe_max}）"
                    else:
                        result_dict['行業'] = sector_raw or 'Unknown'
                        result_dict['行業比較'] = f"無行業數據（{sector_raw} 未在映射表中）"
                        # 記錄未知行業，方便以後添加到映射表
                        if sector_raw and sector_raw != 'Unknown':
                            logger.warning(f"! 未知行業分類: '{sector_raw}'，請考慮添加到 sector_mapping")
                    
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
            
            # 模塊6: 對沖量（支持 Delta 對沖）
            try:
                hedge_calc = HedgeQuantityCalculator()
                
                # 基本對沖計算
                hedge_result = hedge_calc.calculate(
                    stock_quantity=default_stock_quantity,
                    stock_price=current_price,
                    calculation_date=analysis_date_str
                )
                hedge_result_dict = hedge_result.to_dict()
                
                # 新增: 如果有 Delta 值，計算 Delta 對沖
                if call_delta is not None and call_delta > 0:
                    hedge_result_delta = hedge_calc.calculate_with_delta(
                        stock_quantity=default_stock_quantity,
                        stock_price=current_price,
                        option_delta=abs(call_delta),  # 使用絕對值
                        calculation_date=analysis_date_str
                    )
                    hedge_result_dict['delta_hedge'] = {
                        'delta_used': round(abs(call_delta), 4),
                        'hedge_contracts': hedge_result_delta.hedge_contracts,
                        'coverage_percentage': round(hedge_result_delta.coverage_percentage, 2),
                        'note': f'使用 Delta={abs(call_delta):.4f} 計算對沖量'
                    }
                    logger.info(f"  Delta 對沖: {hedge_result_delta.hedge_contracts}張 (Delta={abs(call_delta):.4f})")
                
                self.analysis_results['module6_hedge_quantity'] = hedge_result_dict
                logger.info("* 模塊6完成: 對沖量")
            except Exception as exc:
                logger.warning("! 模塊6執行失敗: %s", exc)
            
            # 模塊7-10: 單腿策略損益（支持多張合約和持倉期損益）
            # 使用 StrategyScenarioGenerator 為每個策略生成正確的場景
            # Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
            
            # 默認合約數量（可從用戶輸入獲取）
            default_num_contracts = 1
            
            if strike_price and strike_price > 0:
                # 模塊7: Long Call
                # 場景: 下跌10%, 維持不變, 上漲10%, 上漲20%
                try:
                    if call_last_price > 0:
                        long_call_calc = LongCallCalculator()
                        # 使用 StrategyScenarioGenerator 獲取正確的場景價格
                        long_call_scenarios = StrategyScenarioGenerator.get_scenario_prices('long_call', current_price)
                        # 基本損益計算（到期情境）
                        long_call_results = [
                            long_call_calc.calculate(
                                strike_price=strike_price,
                                option_premium=call_last_price,
                                stock_price_at_expiry=price,
                                calculation_date=analysis_date_str
                            ).to_dict()
                            for price in long_call_scenarios
                        ]
                        
                        # 新增: 多張合約損益計算
                        long_call_multi = long_call_calc.calculate_with_contracts(
                            strike_price=strike_price,
                            option_premium=call_last_price,
                            stock_price_at_expiry=current_price,
                            num_contracts=default_num_contracts,
                            calculation_date=analysis_date_str
                        )
                        
                        # 新增: 當前持倉損益（假設當前期權價格 = 市場價格）
                        long_call_current_pnl = long_call_calc.calculate_current_pnl(
                            strike_price=strike_price,
                            option_premium=call_last_price,
                            current_stock_price=current_price,
                            current_option_price=call_last_price,  # 使用當前市場價
                            num_contracts=default_num_contracts,
                            calculation_date=analysis_date_str
                        )
                        
                        self.analysis_results['module7_long_call'] = {
                            'scenarios': long_call_results,
                            'multi_contract': long_call_multi,
                            'current_pnl': long_call_current_pnl
                        }
                        logger.info("* 模塊7完成: Long Call 損益（含多合約和持倉期損益）")
                except Exception as exc:
                    logger.warning("! 模塊7執行失敗: %s", exc)
                
                # 模塊8: Long Put
                # 場景: 下跌20%, 下跌10%, 維持不變, 上漲10%
                try:
                    if put_last_price > 0:
                        long_put_calc = LongPutCalculator()
                        # 使用 StrategyScenarioGenerator 獲取正確的場景價格
                        long_put_scenarios = StrategyScenarioGenerator.get_scenario_prices('long_put', current_price)
                        long_put_results = [
                            long_put_calc.calculate(
                                strike_price=strike_price,
                                option_premium=put_last_price,
                                stock_price_at_expiry=price,
                                calculation_date=analysis_date_str
                            ).to_dict()
                            for price in long_put_scenarios
                        ]
                        
                        # 新增: 多張合約損益計算
                        long_put_multi = long_put_calc.calculate_with_contracts(
                            strike_price=strike_price,
                            option_premium=put_last_price,
                            stock_price_at_expiry=current_price,
                            num_contracts=default_num_contracts,
                            calculation_date=analysis_date_str
                        )
                        
                        # 新增: 當前持倉損益
                        long_put_current_pnl = long_put_calc.calculate_current_pnl(
                            strike_price=strike_price,
                            option_premium=put_last_price,
                            current_stock_price=current_price,
                            current_option_price=put_last_price,
                            num_contracts=default_num_contracts,
                            calculation_date=analysis_date_str
                        )
                        
                        self.analysis_results['module8_long_put'] = {
                            'scenarios': long_put_results,
                            'multi_contract': long_put_multi,
                            'current_pnl': long_put_current_pnl
                        }
                        logger.info("* 模塊8完成: Long Put 損益（含多合約和持倉期損益）")
                except Exception as exc:
                    logger.warning("! 模塊8執行失敗: %s", exc)
                
                # 模塊9: Short Call
                # 場景: 維持不變, 上漲5%, 上漲10%, 上漲20%
                try:
                    if call_last_price > 0:
                        short_call_calc = ShortCallCalculator()
                        # 使用 StrategyScenarioGenerator 獲取正確的場景價格
                        short_call_scenarios = StrategyScenarioGenerator.get_scenario_prices('short_call', current_price)
                        short_call_results = [
                            short_call_calc.calculate(
                                strike_price=strike_price,
                                option_premium=call_last_price,
                                stock_price_at_expiry=price,
                                calculation_date=analysis_date_str
                            ).to_dict()
                            for price in short_call_scenarios
                        ]
                        
                        # 新增: 多張合約損益計算
                        short_call_multi = short_call_calc.calculate_with_contracts(
                            strike_price=strike_price,
                            option_premium=call_last_price,
                            stock_price_at_expiry=current_price,
                            num_contracts=default_num_contracts,
                            calculation_date=analysis_date_str
                        )
                        
                        # 新增: 當前持倉損益
                        short_call_current_pnl = short_call_calc.calculate_current_pnl(
                            strike_price=strike_price,
                            option_premium=call_last_price,
                            current_stock_price=current_price,
                            current_option_price=call_last_price,
                            num_contracts=default_num_contracts,
                            calculation_date=analysis_date_str
                        )
                        
                        self.analysis_results['module9_short_call'] = {
                            'scenarios': short_call_results,
                            'multi_contract': short_call_multi,
                            'current_pnl': short_call_current_pnl
                        }
                        logger.info("* 模塊9完成: Short Call 損益（含多合約和持倉期損益）")
                except Exception as exc:
                    logger.warning("! 模塊9執行失敗: %s", exc)
                
                # 模塊10: Short Put
                # 場景: 下跌20%, 下跌10%, 下跌5%, 維持不變
                try:
                    if put_last_price > 0:
                        short_put_calc = ShortPutCalculator()
                        # 使用 StrategyScenarioGenerator 獲取正確的場景價格
                        short_put_scenarios = StrategyScenarioGenerator.get_scenario_prices('short_put', current_price)
                        short_put_results = [
                            short_put_calc.calculate(
                                strike_price=strike_price,
                                option_premium=put_last_price,
                                stock_price_at_expiry=price,
                                calculation_date=analysis_date_str
                            ).to_dict()
                            for price in short_put_scenarios
                        ]
                        
                        # 新增: 多張合約損益計算
                        short_put_multi = short_put_calc.calculate_with_contracts(
                            strike_price=strike_price,
                            option_premium=put_last_price,
                            stock_price_at_expiry=current_price,
                            num_contracts=default_num_contracts,
                            calculation_date=analysis_date_str
                        )
                        
                        # 新增: 當前持倉損益
                        short_put_current_pnl = short_put_calc.calculate_current_pnl(
                            strike_price=strike_price,
                            option_premium=put_last_price,
                            current_stock_price=current_price,
                            current_option_price=put_last_price,
                            num_contracts=default_num_contracts,
                            calculation_date=analysis_date_str
                        )
                        
                        self.analysis_results['module10_short_put'] = {
                            'scenarios': short_put_results,
                            'multi_contract': short_put_multi,
                            'current_pnl': short_put_current_pnl
                        }
                        logger.info("* 模塊10完成: Short Put 損益（含多合約和持倉期損益）")
                except Exception as exc:
                    logger.warning("! 模塊10執行失敗: %s", exc)
            
            # 模塊11: 合成正股（支持股息調整）
            try:
                if strike_price and call_last_price >= 0 and put_last_price >= 0:
                    # 獲取無風險利率和到期時間
                    m11_risk_free_rate_raw = analysis_data.get('risk_free_rate', 4.5) or 4.5
                    m11_risk_free_rate = m11_risk_free_rate_raw / 100.0  # 轉換: 4.35% → 0.0435
                    m11_days_to_exp = analysis_data.get('days_to_expiration', 30) or 30
                    m11_time_to_expiration = m11_days_to_exp / 252  # 使用交易日標準
                    
                    synthetic_calc = SyntheticStockCalculator()
                    
                    # 新增: 獲取股息收益率（從 Finviz/Yahoo Finance 降級獲取）
                    # 數據來源優先級: Finviz → Alpha Vantage → Massive API → Yahoo Finance
                    dividend_yield = analysis_data.get('dividend_yield', 0) or 0
                    
                    if dividend_yield and dividend_yield > 0:
                        # 使用股息收益率計算合成正股
                        logger.info(f"  使用股息收益率: {dividend_yield:.2f}%")
                        synthetic_result = synthetic_calc.calculate_with_dividend_yield(
                            strike_price=strike_price,
                            call_premium=call_last_price,
                            put_premium=put_last_price,
                            current_stock_price=current_price,
                            risk_free_rate=m11_risk_free_rate,
                            time_to_expiration=m11_time_to_expiration,
                            dividend_yield=dividend_yield,  # 新增: 股息收益率
                            calculation_date=analysis_date_str
                        )
                    else:
                        # 無股息數據，使用基本計算
                        logger.info("  無股息數據，使用基本計算")
                        synthetic_result = synthetic_calc.calculate(
                            strike_price=strike_price,
                            call_premium=call_last_price,
                            put_premium=put_last_price,
                            current_stock_price=current_price,
                            risk_free_rate=m11_risk_free_rate,
                            time_to_expiration=m11_time_to_expiration,
                            calculation_date=analysis_date_str
                        )
                    
                    result_dict = synthetic_result.to_dict()
                    result_dict['dividend_yield_used'] = dividend_yield if dividend_yield else 0
                    result_dict['data_source'] = 'Finviz/Yahoo Finance (降級模式)'
                    
                    self.analysis_results['module11_synthetic_stock'] = result_dict
                    logger.info("* 模塊11完成: 合成正股（含股息調整）")
            except Exception as exc:
                logger.warning("! 模塊11執行失敗: %s", exc)
            
            # 模塊12: 年息收益率（Covered Call 策略）
            # 計算賣出 Call 期權的年化收益率
            try:
                if strike_price and strike_price > 0 and call_last_price > 0 and days_to_expiration > 0:
                    # 計算年化收益率
                    # 公式: (期權金 / 股價) * (365 / 到期天數) * 100
                    annualized_return = (call_last_price / current_price) * (365 / days_to_expiration) * 100
                    
                    # 含股票增值的年化收益率（假設股票漲到行使價被行使）
                    stock_gain = max(0, strike_price - current_price)
                    total_return = call_last_price + stock_gain
                    annualized_return_with_stock = (total_return / current_price) * (365 / days_to_expiration) * 100
                    
                    # 保本價格（收到期權金後的成本）
                    break_even_price = current_price - call_last_price
                    
                    # 最大利潤（期權金 + 股票漲到行使價的收益）
                    max_profit = call_last_price + max(0, strike_price - current_price)
                    
                    # 最大損失（股票跌到 0，但收到期權金）
                    max_loss = current_price - call_last_price
                    
                    module12_result = {
                        'initial_premium': call_last_price,
                        'strike_price': strike_price,
                        'stock_price': current_price,
                        'days_to_expiration': int(days_to_expiration),
                        'annualized_return': round(annualized_return, 2),
                        'annualized_return_with_stock': round(annualized_return_with_stock, 2),
                        'break_even_price': round(break_even_price, 2),
                        'max_profit': round(max_profit, 2),
                        'max_loss': round(max_loss, 2),
                        'calculation_date': analysis_date_str
                    }
                    
                    self.analysis_results['module12_annual_yield'] = module12_result
                    logger.info(f"* 模塊12完成: 年化收益率 {annualized_return:.2f}%")
                else:
                    # 數據不足，記錄跳過原因
                    self.analysis_results['module12_annual_yield'] = {
                        'status': 'skipped',
                        'reason': f'數據不足: strike={strike_price}, premium={call_last_price}, days={days_to_expiration}'
                    }
                    logger.warning("! 模塊12跳過: 數據不足")
            except Exception as exc:
                logger.warning("! 模塊12執行失敗: %s", exc)
                self.analysis_results['module12_annual_yield'] = {
                    'status': 'error',
                    'reason': str(exc)
                }
            
            # 模塊13: 倉位分析（增強版 - 包含 Finviz 數據和 Call/Put 分離）
            # Requirements: 2.1, 2.2, 2.3 - 分別顯示 Call 和 Put 的成交量和未平倉量
            try:
                if call_volume >= 0 and call_open_interest >= 0:
                    price_change_pct = 0.0
                    stock_open = analysis_data.get('stock_open')
                    if stock_open and stock_open > 0:
                        price_change_pct = ((current_price - stock_open) / stock_open) * 100
                    
                    # 計算總成交量和總未平倉量
                    total_volume = call_volume + put_volume
                    total_open_interest = call_open_interest + put_open_interest
                    
                    position_calc = PositionAnalysisCalculator()
                    position_result = position_calc.calculate(
                        volume=total_volume,
                        open_interest=total_open_interest,
                        price_change=price_change_pct,
                        calculation_date=analysis_date_str,
                        # 傳遞 Call/Put 分離數據 (Requirements: 2.1, 2.2)
                        call_volume=call_volume if call_volume > 0 else None,
                        call_open_interest=call_open_interest if call_open_interest > 0 else None,
                        put_volume=put_volume if put_volume > 0 else None,
                        put_open_interest=put_open_interest if put_open_interest > 0 else None
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
                    
                    # 修復 (2025-12-07): 使用股票成交量與平均成交量比較
                    # 原問題: call_volume 是期權成交量，avg_volume 是股票平均成交量，不應直接比較
                    stock_volume = analysis_data.get('volume')  # 當日股票成交量
                    if avg_volume and stock_volume and avg_volume > 0:
                        volume_ratio = stock_volume / avg_volume
                        result_dict['volume_vs_avg'] = round(volume_ratio, 2)
                        if volume_ratio > 2.0:
                            result_dict['volume_note'] = "⚠️ 成交量異常放大（>2倍平均）"
                        elif volume_ratio > 1.5:
                            result_dict['volume_note'] = "成交量放大（1.5-2倍平均）"
                        elif volume_ratio < 0.5:
                            result_dict['volume_note'] = "⚠️ 成交量萎縮（<0.5倍平均）"
                        else:
                            result_dict['volume_note'] = "✓ 成交量正常"
                    elif call_volume and call_open_interest and call_open_interest > 0:
                        # 降級: 如果沒有股票成交量，使用期權成交量/未平倉量比率
                        vol_oi_ratio = call_volume / call_open_interest
                        result_dict['volume_vs_avg'] = round(vol_oi_ratio, 2)
                        result_dict['volume_note'] = f"期權成交量/未平倉量比: {vol_oi_ratio:.2f}x"
                    
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
            
            # IV 來源追蹤變量（初始使用 Market IV）
            atm_iv_available = False
            iv_source = "Market IV (initial)"
            
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
            # 修復：優先使用 Yahoo Finance 提供的 IV，而非自己計算
            # 原因：Newton-Raphson 在市場價格與理論價差距大時會失敗
            try:
                if strike_price and strike_price > 0:
                    # 優先從 ATM 期權數據獲取 Yahoo Finance 的 IV
                    yahoo_call_iv = atm_call.get('impliedVolatility')  # Yahoo Finance 提供的 IV
                    yahoo_put_iv = atm_put.get('impliedVolatility')
                    
                    iv_results = {}
                    use_yahoo_iv = False
                    
                    # 如果 Yahoo Finance 有提供 IV，直接使用
                    if yahoo_call_iv and yahoo_call_iv > 0:
                        iv_results['call'] = {
                            'implied_volatility': yahoo_call_iv,
                            'converged': True,
                            'iterations': 0,
                            'market_price': call_last_price,
                            'source': 'Yahoo Finance (直接提供)',
                            'note': '使用 Yahoo Finance 提供的 IV，基於 bid/ask mid price 計算'
                        }
                        use_yahoo_iv = True
                        logger.info(f"  Call IV: {yahoo_call_iv*100:.2f}% (Yahoo Finance 直接提供)")
                    
                    if yahoo_put_iv and yahoo_put_iv > 0:
                        iv_results['put'] = {
                            'implied_volatility': yahoo_put_iv,
                            'converged': True,
                            'iterations': 0,
                            'market_price': put_last_price,
                            'source': 'Yahoo Finance (直接提供)',
                            'note': '使用 Yahoo Finance 提供的 IV，基於 bid/ask mid price 計算'
                        }
                        use_yahoo_iv = True
                        logger.info(f"  Put IV: {yahoo_put_iv*100:.2f}% (Yahoo Finance 直接提供)")
                    
                    # 如果 Yahoo Finance 沒有提供 IV，使用 Market IV（從 Finnhub 獲取）
                    # 修復：不再嘗試 Newton-Raphson 計算，因為當市場價格與理論價差距大時會失敗
                    if not use_yahoo_iv:
                        # 使用 Market IV 作為備選（已經在 volatility_estimate 中）
                        market_iv = volatility_estimate  # 這是從 Finnhub 獲取的 Market IV
                        
                        if market_iv and market_iv > 0:
                            logger.info(f"  Yahoo Finance 未提供 IV，使用 Market IV: {market_iv*100:.2f}%")
                            iv_results['call'] = {
                                'implied_volatility': market_iv,
                                'converged': True,
                                'iterations': 0,
                                'market_price': call_last_price,
                                'source': 'Market IV (Finnhub)',
                                'note': '使用 Finnhub 提供的 Market IV，因為 Yahoo Finance 未提供期權 IV'
                            }
                            use_yahoo_iv = True  # 標記為已獲取 IV
                            
                            if put_last_price > 0:
                                iv_results['put'] = {
                                    'implied_volatility': market_iv,
                                    'converged': True,
                                    'iterations': 0,
                                    'market_price': put_last_price,
                                    'source': 'Market IV (Finnhub)',
                                    'note': '使用 Finnhub 提供的 Market IV'
                                }
                        else:
                            # 最後備選：嘗試 Newton-Raphson 計算
                            logger.info("  Market IV 不可用，嘗試 Newton-Raphson 計算...")
                            iv_calc = ImpliedVolatilityCalculator()
                            
                            call_iv_result = iv_calc.calculate_implied_volatility(
                                market_price=call_last_price,
                                stock_price=current_price,
                                strike_price=strike_price,
                                risk_free_rate=risk_free_rate,
                                time_to_expiration=time_to_expiration_years,
                                option_type='call'
                            )
                            
                            iv_results['call'] = call_iv_result.to_dict()
                            iv_results['call']['source'] = '自行計算 (Newton-Raphson)'
                            
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
                                iv_results['put']['source'] = '自行計算 (Newton-Raphson)'
                    
                    self.analysis_results['module17_implied_volatility'] = iv_results
                    
                    # 判斷 IV 是否成功獲取（Yahoo IV 或自行計算）
                    call_iv_converged = iv_results.get('call', {}).get('converged', False)
                    call_iv_value = iv_results.get('call', {}).get('implied_volatility', 0)
                    iv_source_type = iv_results.get('call', {}).get('source', 'unknown')
                    
                    if call_iv_converged and call_iv_value > 0:
                        logger.info(f"* 模塊17完成: 隱含波動率計算 (Call IV={call_iv_value*100:.2f}%, 來源: {iv_source_type})")
                        
                        # ========== 核心修復: 更新 volatility_estimate 為 ATM IV ==========
                        # Requirements 1.1, 6.2: Module 17 成功後更新 volatility_estimate
                        atm_iv = call_iv_value  # 從 Module 17 提取 ATM IV
                        
                        # ★ 核心修復：更新 volatility_estimate 為 ATM IV
                        volatility_estimate = atm_iv
                        atm_iv_available = True
                        iv_source = "ATM IV (Module 17)"
                        
                        # 記錄 ATM IV 與 Market IV 的差異百分比
                        iv_diff_pct = abs(atm_iv * 100 - volatility_raw) / volatility_raw * 100 if volatility_raw > 0 else 0
                        logger.info(f"  ★ volatility_estimate 已更新為 ATM IV: {atm_iv*100:.2f}%")
                        logger.info(f"    原始 Market IV: {volatility_raw:.2f}%")
                        logger.info(f"    差異: {iv_diff_pct:.1f}%")
                        
                        # ========== Requirements 5.1: IV 差異警告邏輯 ==========
                        # 如果 ATM IV 與 Market IV 差異超過 20%，記錄警告日誌並添加 iv_warning 字段
                        iv_warning = None
                        if iv_diff_pct > 20:
                            iv_warning = f"ATM IV ({atm_iv*100:.2f}%) 與 Market IV ({volatility_raw:.2f}%) 差異 {iv_diff_pct:.1f}%，超過 20% 閾值"
                            logger.warning(f"  ⚠️ IV 差異警告: {iv_warning}")
                            logger.warning(f"    可能原因: 數據源問題、市場異常波動或波動率微笑/偏斜")
                        
                        # 將 IV 警告添加到 analysis_results 中
                        self.analysis_results['iv_warning'] = iv_warning
                        self.analysis_results['iv_comparison'] = {
                            'market_iv': round(volatility_raw, 2),
                            'atm_iv': round(atm_iv * 100, 2),
                            'difference_pct': round(iv_diff_pct, 1),
                            'warning_threshold': 20,
                            'has_warning': iv_diff_pct > 20
                        }
                        # ========== IV 差異警告邏輯結束 ==========
                        
                        # ========== ATM IV 集成: 更新 Module 15 使用 ATM IV ==========
                        # Requirements 3.1, 3.2, 3.3: 使用 ATM IV 優先計算期權理論價格
                        logger.info(f"\n→ ATM IV 集成: 使用 ATM IV ({atm_iv*100:.2f}%) 更新 Module 15 計算...")
                        
                        try:
                            bs_calc_atm = BlackScholesCalculator()
                            
                            # 使用 ATM IV 重新計算 Call 期權理論價格
                            bs_call_atm = bs_calc_atm.calculate_option_price_with_atm_iv(
                                stock_price=current_price,
                                strike_price=strike_price,
                                risk_free_rate=risk_free_rate,
                                time_to_expiration=time_to_expiration_years,
                                market_iv=volatility_estimate,
                                atm_iv=atm_iv,
                                option_type='call'
                            )
                            
                            # 使用 ATM IV 重新計算 Put 期權理論價格
                            bs_put_atm = bs_calc_atm.calculate_option_price_with_atm_iv(
                                stock_price=current_price,
                                strike_price=strike_price,
                                risk_free_rate=risk_free_rate,
                                time_to_expiration=time_to_expiration_years,
                                market_iv=volatility_estimate,
                                atm_iv=atm_iv,
                                option_type='put'
                            )
                            
                            # 更新 Module 15 結果，添加 ATM IV 信息
                            if 'module15_black_scholes' in self.analysis_results:
                                self.analysis_results['module15_black_scholes']['call_atm_iv'] = bs_call_atm.to_dict()
                                self.analysis_results['module15_black_scholes']['put_atm_iv'] = bs_put_atm.to_dict()
                                self.analysis_results['module15_black_scholes']['atm_iv_used'] = round(atm_iv, 4)
                                self.analysis_results['module15_black_scholes']['atm_iv_source'] = 'Module 17 (ATM Call IV)'
                                
                                # 更新主要的 call/put 結果為 ATM IV 版本
                                self.analysis_results['module15_black_scholes']['call'] = bs_call_atm.to_dict()
                                self.analysis_results['module15_black_scholes']['put'] = bs_put_atm.to_dict()
                            
                            logger.info(f"  * ATM IV 更新完成:")
                            logger.info(f"    Call 理論價: ${bs_call_atm.option_price:.2f} (IV來源: {bs_call_atm.iv_source})")
                            logger.info(f"    Put 理論價: ${bs_put_atm.option_price:.2f} (IV來源: {bs_put_atm.iv_source})")
                        except Exception as atm_exc:
                            logger.warning(f"! ATM IV 更新失敗: {atm_exc}，保留原始 Module 15 結果")
                        # ========== ATM IV 集成結束 ==========
                        
                        # ========== Module 16 ATM IV 更新: 使用 ATM IV 重新計算 Greeks ==========
                        # Requirements 2.1, 2.3: 使用 ATM IV 更新 Greeks 計算並添加 IV 來源標記
                        try:
                            logger.info(f"\n→ Module 16 ATM IV 更新: 使用 ATM IV ({atm_iv*100:.2f}%) 重新計算 Greeks...")
                            
                            greeks_calc_atm = GreeksCalculator()
                            
                            # 使用 ATM IV 重新計算 Call Greeks
                            call_greeks_atm = greeks_calc_atm.calculate_all_greeks(
                                stock_price=current_price,
                                strike_price=strike_price,
                                risk_free_rate=risk_free_rate,
                                time_to_expiration=time_to_expiration_years,
                                volatility=atm_iv,  # 使用 ATM IV
                                option_type='call'
                            )
                            
                            # 使用 ATM IV 重新計算 Put Greeks
                            put_greeks_atm = greeks_calc_atm.calculate_all_greeks(
                                stock_price=current_price,
                                strike_price=strike_price,
                                risk_free_rate=risk_free_rate,
                                time_to_expiration=time_to_expiration_years,
                                volatility=atm_iv,  # 使用 ATM IV
                                option_type='put'
                            )
                            
                            # 更新 Module 16 結果，添加 IV 來源標記
                            if 'module16_greeks' in self.analysis_results:
                                self.analysis_results['module16_greeks']['call'] = call_greeks_atm.to_dict()
                                self.analysis_results['module16_greeks']['put'] = put_greeks_atm.to_dict()
                                self.analysis_results['module16_greeks']['iv_source'] = iv_source
                                self.analysis_results['module16_greeks']['iv_used'] = round(atm_iv, 6)
                                self.analysis_results['module16_greeks']['iv_used_pct'] = round(atm_iv * 100, 2)
                                self.analysis_results['module16_greeks']['market_iv'] = round(volatility_raw / 100, 6)
                                self.analysis_results['module16_greeks']['market_iv_pct'] = round(volatility_raw, 2)
                                self.analysis_results['module16_greeks']['data_source'] = 'Self-Calculated (ATM IV)'
                            
                            logger.info(f"  * Module 16 ATM IV 更新完成:")
                            logger.info(f"    Call Delta: {call_greeks_atm.delta:.4f}, Gamma: {call_greeks_atm.gamma:.6f}")
                            logger.info(f"    Put Delta: {put_greeks_atm.delta:.4f}, Gamma: {put_greeks_atm.gamma:.6f}")
                            logger.info(f"    IV 來源: {iv_source}, IV 使用: {atm_iv*100:.2f}%")
                        except Exception as m16_exc:
                            logger.warning(f"! Module 16 ATM IV 更新失敗: {m16_exc}，保留原始結果")
                            # 即使更新失敗，也添加 IV 來源標記（使用原始 Market IV）
                            if 'module16_greeks' in self.analysis_results:
                                self.analysis_results['module16_greeks']['iv_source'] = "Market IV (ATM IV update failed)"
                                self.analysis_results['module16_greeks']['iv_used'] = round(volatility_estimate, 6)
                                self.analysis_results['module16_greeks']['iv_used_pct'] = round(volatility_estimate * 100, 2)
                        # ========== Module 16 ATM IV 更新結束 ==========
                        
                        # ========== Module 1 ATM IV 更新: 使用 ATM IV 重新計算支持/阻力位 ==========
                        # 優先使用 Module 17 計算的 ATM IV，而非 Yahoo Finance 的市場 IV
                        try:
                            atm_iv_pct = atm_iv * 100  # 轉換為百分比格式
                            market_iv_pct = analysis_data['implied_volatility']
                            
                            # 只有當 ATM IV 與市場 IV 差異超過 10% 時才更新
                            iv_diff_pct = abs(atm_iv_pct - market_iv_pct) / market_iv_pct * 100 if market_iv_pct > 0 else 0
                            
                            if iv_diff_pct > 10:
                                logger.info(f"\n→ Module 1 ATM IV 更新: ATM IV ({atm_iv_pct:.2f}%) vs 市場 IV ({market_iv_pct:.2f}%), 差異 {iv_diff_pct:.1f}%")
                                
                                # 使用 ATM IV 重新計算多信心度支持/阻力位
                                sr_results_multi_atm = sr_calc.calculate_multi_confidence(
                                    stock_price=analysis_data['current_price'],
                                    implied_volatility=atm_iv_pct,  # 使用 ATM IV
                                    days_to_expiration=int(days_to_expiration),
                                    confidence_levels=['68%', '80%', '90%', '95%', '99%']
                                )
                                
                                # 使用 ATM IV 重新計算單一信心度 (90%)
                                sr_result_single_atm = sr_calc.calculate(
                                    stock_price=analysis_data['current_price'],
                                    implied_volatility=atm_iv_pct,  # 使用 ATM IV
                                    days_to_expiration=int(days_to_expiration),
                                    z_score=1.645  # 90%信心度
                                )
                                
                                # 更新 Module 1 結果
                                self.analysis_results['module1_support_resistance_multi'] = sr_results_multi_atm
                                self.analysis_results['module1_support_resistance'] = sr_result_single_atm.to_dict()
                                
                                # 添加 IV 來源標記
                                self.analysis_results['module1_support_resistance']['iv_source'] = 'ATM IV (Module 17)'
                                self.analysis_results['module1_support_resistance']['market_iv'] = market_iv_pct
                                self.analysis_results['module1_support_resistance']['atm_iv'] = atm_iv_pct
                                
                                logger.info(f"  * Module 1 已更新: 使用 ATM IV ({atm_iv_pct:.2f}%) 替代市場 IV ({market_iv_pct:.2f}%)")
                                logger.info(f"    90% 信心度區間: ${sr_result_single_atm.support_level:.2f} - ${sr_result_single_atm.resistance_level:.2f}")
                            else:
                                logger.info(f"  Module 1 保持不變: ATM IV ({atm_iv_pct:.2f}%) 與市場 IV ({market_iv_pct:.2f}%) 差異小於 10%")
                        except Exception as m1_exc:
                            logger.warning(f"! Module 1 ATM IV 更新失敗: {m1_exc}，保留原始結果")
                        # ========== Module 1 ATM IV 更新結束 ==========
                        
                    else:
                        # Requirements 1.2: Module 17 不收斂時的回退邏輯
                        atm_iv_available = False
                        iv_source = "Market IV (fallback)"
                        logger.warning(f"! 模塊17: Call IV 未收斂 ({call_iv_result.iterations}次迭代)")
                        logger.warning(f"  保持使用 Market IV: {volatility_raw:.2f}%")
                        
                        # Requirements 2.3: 在 Module 16 結果中添加 IV 來源標記（回退情況）
                        if 'module16_greeks' in self.analysis_results:
                            self.analysis_results['module16_greeks']['iv_source'] = iv_source
                            self.analysis_results['module16_greeks']['iv_used'] = round(volatility_estimate, 6)
                            self.analysis_results['module16_greeks']['iv_used_pct'] = round(volatility_estimate * 100, 2)
            except Exception as exc:
                # Module 17 執行失敗時也設置回退狀態
                atm_iv_available = False
                iv_source = "Market IV (fallback - Module 17 error)"
                logger.warning("! 模塊17執行失敗: %s", exc)
                
                # Requirements 2.3: 在 Module 16 結果中添加 IV 來源標記（錯誤情況）
                if 'module16_greeks' in self.analysis_results:
                    self.analysis_results['module16_greeks']['iv_source'] = iv_source
                    self.analysis_results['module16_greeks']['iv_used'] = round(volatility_estimate, 6)
                    self.analysis_results['module16_greeks']['iv_used_pct'] = round(volatility_estimate * 100, 2)
            
            # 模塊18: 歷史波動率計算 + IV Rank/Percentile（增強版）
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
                        
                        result_dict = {
                            'hv_results': {k: v.to_dict() for k, v in hv_results.items()},
                            'iv_hv_comparison': iv_hv_ratio.to_dict()
                        }
                        
                        # ★ Requirements 3.1, 3.2, 3.3: 添加 IV 來源追蹤到 iv_hv_comparison
                        result_dict['iv_hv_comparison']['iv_source'] = iv_source
                        result_dict['iv_hv_comparison']['iv_used'] = round(volatility_estimate, 6)
                        result_dict['iv_hv_comparison']['iv_used_pct'] = round(volatility_estimate * 100, 2)
                        
                        # ✅ 新增: IV Rank 和 IV Percentile 計算（如果有足夠的歷史數據）
                        # 需要至少 200 天數據（約 10 個月），理想是 252 天（1年）
                        # Requirements 7.1: 使用 ATM IV 而非 Market IV 計算 IV Rank
                        if len(historical_data) >= 200:
                            logger.info("  計算 IV Rank 和 IV Percentile (52週基準)...")
                            
                            # 嘗試獲取歷史IV數據（如果data_fetcher支持）
                            try:
                                historical_iv = self.fetcher.get_historical_iv(ticker, days=252)
                                
                                # 接受至少 200 天的數據
                                if historical_iv is not None and len(historical_iv) >= 200:
                                    # Requirements 7.1: 優先使用 ATM IV（來自 Module 17）
                                    # 如果 ATM IV 不可用，則使用 Market IV 作為備選
                                    atm_iv_for_rank = None
                                    iv_source_for_rank = 'Market IV'
                                    
                                    # 嘗試從 Module 17 結果獲取 ATM IV
                                    if 'module17_implied_volatility' in self.analysis_results:
                                        m17_result = self.analysis_results['module17_implied_volatility']
                                        if m17_result.get('call', {}).get('converged', False):
                                            atm_iv_for_rank = m17_result['call'].get('implied_volatility')
                                            iv_source_for_rank = 'ATM IV (Module 17)'
                                            logger.info(f"  使用 ATM IV ({atm_iv_for_rank*100:.2f}%) 計算 IV Rank")
                                    
                                    # 如果 ATM IV 不可用，使用 Market IV
                                    if atm_iv_for_rank is None:
                                        atm_iv_for_rank = volatility_estimate
                                        iv_source_for_rank = 'Market IV (備選)'
                                        logger.info(f"  ATM IV 不可用，使用 Market IV ({atm_iv_for_rank*100:.2f}%) 計算 IV Rank")
                                    
                                    # 計算 IV Rank
                                    iv_rank = hv_calc.calculate_iv_rank(
                                        current_iv=atm_iv_for_rank,
                                        historical_iv_series=historical_iv
                                    )
                                    
                                    # 計算 IV Percentile
                                    iv_percentile = hv_calc.calculate_iv_percentile(
                                        current_iv=atm_iv_for_rank,
                                        historical_iv_series=historical_iv
                                    )
                                    
                                    # Requirements 7.3: 計算歷史 IV 範圍
                                    iv_min = float(historical_iv.min())
                                    iv_max = float(historical_iv.max())
                                    
                                    # Requirements 7.2: IV Rank 為 0% 時的數據驗證
                                    iv_rank_validation = {
                                        'is_valid': True,
                                        'warnings': []
                                    }
                                    
                                    if iv_rank == 0.0:
                                        # 檢查當前 IV 是否真的等於歷史最低
                                        if abs(atm_iv_for_rank - iv_min) > 0.001:
                                            iv_rank_validation['is_valid'] = False
                                            iv_rank_validation['warnings'].append(
                                                f"IV Rank 為 0% 但當前 IV ({atm_iv_for_rank*100:.2f}%) 不等於歷史最低 ({iv_min*100:.2f}%)"
                                            )
                                        # 檢查歷史數據是否有足夠變化
                                        if iv_max - iv_min < 0.01:  # 歷史範圍小於 1%
                                            iv_rank_validation['is_valid'] = False
                                            iv_rank_validation['warnings'].append(
                                                f"歷史 IV 範圍過小 ({iv_min*100:.2f}% - {iv_max*100:.2f}%)，數據可能不準確"
                                            )
                                        logger.warning(f"  ! IV Rank 為 0%，進行數據驗證...")
                                        for warning in iv_rank_validation['warnings']:
                                            logger.warning(f"    {warning}")
                                    
                                    # 獲取交易建議
                                    iv_recommendation = hv_calc.get_iv_recommendation(iv_rank, iv_percentile)
                                    
                                    result_dict['iv_rank'] = iv_rank
                                    result_dict['iv_percentile'] = iv_percentile
                                    result_dict['iv_recommendation'] = iv_recommendation
                                    result_dict['note'] = '基於252個交易日(52週)的歷史IV數據'
                                    # 修復 (2025-12-07): 保存 historical_iv 供 Module 23 使用
                                    result_dict['historical_iv'] = historical_iv
                                    
                                    # Requirements 7.1, 7.3: 記錄 IV 來源和歷史範圍
                                    result_dict['iv_rank_details'] = {
                                        'current_iv': round(atm_iv_for_rank, 6),
                                        'current_iv_percent': round(atm_iv_for_rank * 100, 2),
                                        'iv_source': iv_source_for_rank,
                                        'historical_iv_min': round(iv_min, 6),
                                        'historical_iv_max': round(iv_max, 6),
                                        'historical_iv_min_percent': round(iv_min * 100, 2),
                                        'historical_iv_max_percent': round(iv_max * 100, 2),
                                        'historical_data_points': len(historical_iv),
                                        'validation': iv_rank_validation
                                    }
                                    
                                    logger.info(f"  IV Rank: {iv_rank:.2f}%, IV Percentile: {iv_percentile:.2f}%")
                                    logger.info(f"  IV 來源: {iv_source_for_rank}, 當前 IV: {atm_iv_for_rank*100:.2f}%")
                                    logger.info(f"  歷史 IV 範圍: {iv_min*100:.2f}% - {iv_max*100:.2f}%")
                                    logger.info(f"  建議: {iv_recommendation['action']} - {iv_recommendation['reason']}")
                                else:
                                    logger.info("  ! 無法獲取歷史IV數據，跳過IV Rank/Percentile計算")
                                    result_dict['iv_rank_details'] = {
                                        'error': '歷史 IV 數據不足',
                                        'data_points_available': len(historical_iv) if historical_iv is not None else 0,
                                        'data_points_required': 200
                                    }
                            except Exception as e:
                                logger.debug(f"  ! 獲取歷史IV失敗: {e}")
                                result_dict['iv_rank_details'] = {
                                    'error': f'獲取歷史 IV 失敗: {str(e)}'
                                }
                        
                        self.analysis_results['module18_historical_volatility'] = result_dict
                        logger.info(f"* 模塊18完成: 歷史波動率計算 (HV30={hv_30.historical_volatility*100:.2f}%, IV/HV={iv_hv_ratio.iv_hv_ratio:.2f})")
                        
                        # ========== 崗位13: IV Rank 整合到 Module 14 ==========
                        # 將 Module 18 計算的 IV Rank 傳入 Module 14 作為崗位13
                        try:
                            if 'module14_monitoring_posts' in self.analysis_results:
                                iv_rank_value = result_dict.get('iv_rank')
                                
                                # 調用 check_iv_rank_post 方法
                                iv_rank_result = monitoring_calc.check_iv_rank_post(iv_rank_value)
                                
                                # 更新 Module 14 結果
                                module14_result = self.analysis_results['module14_monitoring_posts']
                                module14_result['post13_iv_rank_status'] = iv_rank_result['status']
                                module14_result['post_details']['post13'] = iv_rank_result
                                
                                # 如果 IV Rank 觸發警告，更新警報計數
                                if iv_rank_value is not None and (iv_rank_value > 70 or iv_rank_value < 30):
                                    module14_result['total_alerts'] = module14_result.get('total_alerts', 0) + 1
                                    # 重新計算風險等級
                                    alerts = module14_result['total_alerts']
                                    if alerts >= 4:
                                        module14_result['risk_level'] = "高風險"
                                    elif alerts >= 2:
                                        module14_result['risk_level'] = "中風險"
                                    else:
                                        module14_result['risk_level'] = "低風險"
                                
                                logger.info(f"  崗位13整合完成: IV Rank {iv_rank_value}% - {iv_rank_result['status']}")
                        except Exception as e:
                            logger.warning(f"  ! 崗位13整合失敗: {e}")
                        
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
            
            # ========== 模塊21: 動量過濾器 (新增) ==========
            logger.info("\n→ 運行 Module 21: 動量過濾器...")
            momentum_score = 0.5  # 默認中性動量
            try:
                # 嘗試獲取歷史數據
                historical_data = analysis_data.get('historical_data')
                if historical_data is not None and len(historical_data) >= 30:
                    logger.info("  計算動量得分...")
                    
                    momentum_filter = MomentumFilter(data_fetcher=self.fetcher)
                    momentum_result = momentum_filter.calculate(
                        ticker=ticker,
                        historical_data=historical_data,
                        calculation_date=analysis_date_str
                    )
                    
                    momentum_score = momentum_result.momentum_score
                    self.analysis_results['module21_momentum_filter'] = momentum_result.to_dict()
                    
                    logger.info(f"* 模塊21完成: 動量過濾器")
                    logger.info(f"  動量得分: {momentum_score:.4f}")
                    logger.info(f"  建議: {momentum_result.recommendation}")
                else:
                    logger.info("! 模塊21跳過: 歷史數據不足（需要至少30天數據）")
                    self.analysis_results['module21_momentum_filter'] = {
                        'status': 'skipped',
                        'reason': '歷史數據不足',
                        'momentum_score': momentum_score,
                        'note': '使用默認中性動量 (0.5)'
                    }
            except Exception as exc:
                logger.warning(f"! 模塊21執行失敗: {exc}")
                self.analysis_results['module21_momentum_filter'] = {
                    'status': 'error',
                    'reason': str(exc),
                    'momentum_score': momentum_score,
                    'note': '使用默認中性動量 (0.5)'
                }
            
            # ========== 模塊3: 套戥水位 (使用 ATM IV + 動量整合) ==========
            # 注意: Module 3 必須在 Module 15, Module 17 和 Module 21 之後執行
            # 原因: 需要使用 ATM IV 計算期權理論價，並整合動量因素
            # Requirements: 4.1, 4.2, 4.3, 4.4 - 使用 ATM IV 計算套戥水位
            logger.info("\n→ 運行 Module 3: 套戥水位計算（使用 ATM IV + 動量整合）...")
            try:
                # 從 Module 15 獲取期權理論價和 ATM IV 信息
                bs_results = self.analysis_results.get('module15_black_scholes')
                iv17_results = self.analysis_results.get('module17_implied_volatility')
                
                # 提取 ATM IV（來自 Module 17）
                atm_iv_for_arb = None
                if iv17_results and 'call' in iv17_results:
                    call_iv_data = iv17_results['call']
                    if call_iv_data.get('converged', False):
                        atm_iv_for_arb = call_iv_data.get('implied_volatility')
                
                # 詳細檢查前置條件
                logger.info("  檢查前置條件:")
                logger.info(f"    市場期權價格: ${call_last_price:.2f}" if call_last_price > 0 else "    x 市場期權價格不可用")
                logger.info(f"    Module 15 結果: {'* 可用' if bs_results else 'x 不可用'}")
                logger.info(f"    ATM IV (Module 17): {atm_iv_for_arb*100:.2f}%" if atm_iv_for_arb else "    x ATM IV 不可用")
                logger.info(f"    動量得分: {momentum_score:.4f}")
                
                if call_last_price > 0 and bs_results:
                    # 獲取 Call 期權理論價（已使用 ATM IV 計算）
                    call_theoretical_price = bs_results.get('call', {}).get('option_price')
                    iv_source = bs_results.get('atm_iv_source', 'Market IV')
                    
                    if call_theoretical_price and call_theoretical_price > 0:
                        logger.info(f"    期權理論價: ${call_theoretical_price:.2f} (IV來源: {iv_source})")
                        logger.info("  * 所有前置條件滿足，執行套戥水位計算（ATM IV + 動量整合）...")
                        
                        arb_calc = ArbitrageSpreadCalculator()
                        
                        # ✅ Requirements 4.1, 4.2: 使用 ATM IV 計算套戥水位
                        # 如果有 ATM IV，使用 calculate_with_atm_iv 方法
                        if atm_iv_for_arb and atm_iv_for_arb > 0:
                            arb_result = arb_calc.calculate_with_atm_iv(
                                market_option_price=call_last_price,
                                stock_price=current_price,
                                strike_price=strike_price,
                                risk_free_rate=risk_free_rate,
                                time_to_expiration=time_to_expiration_years,
                                market_iv=volatility_estimate,
                                atm_iv=atm_iv_for_arb,
                                option_type='call',
                                bid_price=call_bid,
                                ask_price=call_ask,
                                calculation_date=analysis_date_str
                            )
                            iv_method = 'ATM IV (Module 17)'
                        else:
                            # 回退到使用已計算的理論價（可能已使用 ATM IV）
                            arb_result = arb_calc.calculate(
                                market_option_price=call_last_price,
                                fair_value=call_theoretical_price,
                                bid_price=call_bid,
                                ask_price=call_ask,
                                calculation_date=analysis_date_str
                            )
                            iv_method = iv_source
                        
                        # 應用動量調整到建議
                        original_recommendation = arb_result.recommendation
                        adjusted_recommendation = original_recommendation
                        momentum_note = ""
                        spread_pct = arb_result.spread_percentage
                        
                        # 動量調整邏輯（與 calculate_with_momentum 相同）
                        if spread_pct >= 2.0:  # 高估
                            if momentum_score >= 0.7:
                                adjusted_recommendation = f"⚠️ 觀望 - 雖然高估{spread_pct:.1f}%，但動量強勁（{momentum_score:.2f}），不建議逆勢做空"
                                momentum_note = "強動量警告：避免在上漲趨勢中做空"
                            elif momentum_score >= 0.4:
                                adjusted_recommendation = f"⚠️ 謹慎Short - 高估{spread_pct:.1f}%，但動量中等（{momentum_score:.2f}）"
                                momentum_note = "中等動量：建議等待動量轉弱"
                            else:
                                adjusted_recommendation = f"✓ Short - 高估{spread_pct:.1f}%且動量轉弱（{momentum_score:.2f}）"
                                momentum_note = "弱動量確認：做空時機成熟"
                        elif spread_pct <= -2.0:  # 低估
                            if momentum_score >= 0.7:
                                adjusted_recommendation = f"✓✓ 強烈Long - 低估{abs(spread_pct):.1f}%且動量強勁（{momentum_score:.2f}）"
                                momentum_note = "強動量+低估：最佳買入機會"
                            else:
                                adjusted_recommendation = f"✓ Long - 低估{abs(spread_pct):.1f}%，動量{momentum_score:.2f}"
                                momentum_note = "低估確認：適合買入"
                        else:
                            momentum_note = f"估值合理，動量{momentum_score:.2f}"
                        
                        # 在結果中添加數據來源標註（Requirements 4.3）
                        result_dict = arb_result.to_dict()
                        result_dict['note'] = f'使用 {iv_method} 計算期權理論價 + 動量過濾器'
                        result_dict['theoretical_price_source'] = f'Module 15 (Black-Scholes with {iv_method})'
                        result_dict['momentum_source'] = 'Module 21 (Momentum Filter)'
                        result_dict['theoretical_price'] = round(arb_result.fair_value, 2)
                        result_dict['market_price'] = round(call_last_price, 2)
                        result_dict['momentum_score'] = round(momentum_score, 4)
                        result_dict['momentum_note'] = momentum_note
                        result_dict['original_recommendation'] = original_recommendation
                        result_dict['recommendation'] = adjusted_recommendation
                        result_dict['momentum_adjusted'] = (adjusted_recommendation != original_recommendation)
                        
                        self.analysis_results['module3_arbitrage_spread'] = result_dict
                        logger.info(f"* 模塊3完成: 套戥水位（ATM IV + 動量整合）")
                        logger.info(f"  市場價: ${call_last_price:.2f}")
                        logger.info(f"  理論價: ${arb_result.fair_value:.2f} (IV來源: {iv_method})")
                        logger.info(f"  價差: ${arb_result.arbitrage_spread:.2f} ({arb_result.spread_percentage:.2f}%)")
                        logger.info(f"  動量得分: {momentum_score:.4f}")
                        logger.info(f"  建議: {adjusted_recommendation}")
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
            
            # ========== 模塊23: 動態IV閾值 (移到 Module 22 之前) ==========
            # 原因: Module 22 需要 Module 23 的 IV 環境信息來調整推薦策略
            logger.info("\n→ 運行 Module 23: 動態IV閾值計算...")
            iv_environment = 'neutral'  # 默認中性
            iv_trading_suggestion = None
            try:
                dynamic_iv_calc = DynamicIVThresholdCalculator()
                
                # 獲取歷史IV數據
                historical_iv = None
                hv_data = self.analysis_results.get('module18_historical_volatility', {})
                if 'historical_iv' in hv_data:
                    historical_iv = hv_data['historical_iv']
                
                # ★ 修復 (Requirements 4.1, 4.2, 4.3): 使用 ATM IV (volatility_estimate) 而非 Market IV
                # volatility_estimate 在 Module 17 成功後已更新為 ATM IV
                current_iv_for_threshold = volatility_estimate * 100  # 轉換為百分比格式
                
                # 計算動態閾值
                iv_threshold_result = dynamic_iv_calc.calculate_thresholds(
                    current_iv=current_iv_for_threshold,  # 使用 ATM IV (如果可用)
                    historical_iv=historical_iv,
                    vix=vix_value
                )
                
                self.analysis_results['module23_dynamic_iv_threshold'] = iv_threshold_result.to_dict()
                
                # ★ 添加 IV 來源標記 (Requirements 4.3)
                self.analysis_results['module23_dynamic_iv_threshold']['iv_source'] = iv_source
                self.analysis_results['module23_dynamic_iv_threshold']['iv_used'] = round(current_iv_for_threshold, 2)
                self.analysis_results['module23_dynamic_iv_threshold']['iv_used_decimal'] = round(volatility_estimate, 6)
                self.analysis_results['module23_dynamic_iv_threshold']['market_iv'] = analysis_data.get('implied_volatility', 25.0)
                self.analysis_results['module23_dynamic_iv_threshold']['atm_iv_available'] = atm_iv_available
                
                # 獲取交易建議
                trading_suggestion = dynamic_iv_calc.get_trading_suggestion(iv_threshold_result)
                self.analysis_results['module23_dynamic_iv_threshold']['trading_suggestion'] = trading_suggestion
                iv_trading_suggestion = trading_suggestion
                
                # 確定 IV 環境（用於 Module 22 整合）
                if iv_threshold_result.current_iv > iv_threshold_result.high_threshold:
                    iv_environment = 'high'
                elif iv_threshold_result.current_iv < iv_threshold_result.low_threshold:
                    iv_environment = 'low'
                else:
                    iv_environment = 'neutral'
                
                logger.info(f"* 模塊23完成: 動態IV閾值計算")
                logger.info(f"  當前IV: {iv_threshold_result.current_iv:.2f}% (來源: {iv_source})")
                logger.info(f"  高閾值: {iv_threshold_result.high_threshold:.2f}%")
                logger.info(f"  低閾值: {iv_threshold_result.low_threshold:.2f}%")
                logger.info(f"  狀態: {iv_threshold_result.status}")
                logger.info(f"  IV環境: {iv_environment}")
                logger.info(f"  數據質量: {iv_threshold_result.data_quality}")
                logger.info(f"  歷史數據: {iv_threshold_result.historical_days} 天")
                logger.info(f"  可靠性: {iv_threshold_result.reliability}")
                # 顯示 Market IV 與 ATM IV 的差異（如果 ATM IV 可用）
                if atm_iv_available:
                    market_iv_val = analysis_data.get('implied_volatility', 25.0)
                    logger.info(f"  Market IV: {market_iv_val:.2f}% (ATM IV 差異: {abs(current_iv_for_threshold - market_iv_val):.2f}%)")
                if iv_threshold_result.warning:
                    logger.warning(f"  ⚠️ {iv_threshold_result.warning}")
            except Exception as exc:
                logger.warning(f"! 模塊23執行失敗: {exc}")
                self.analysis_results['module23_dynamic_iv_threshold'] = {
                    'status': 'error',
                    'reason': str(exc)
                }
            
            # ========== 模塊22: 最佳行使價分析 (整合 Module 23 IV 環境) ==========
            logger.info("\n→ 運行 Module 22: 最佳行使價分析...")
            try:
                # 獲取期權鏈數據
                option_chain_raw = analysis_data.get('option_chain', {})
                iv_rank_value = self.analysis_results.get('module18_historical_volatility', {}).get('iv_rank', 50.0)
                
                # 轉換 DataFrame 為 list of dicts（Module 22 期望的格式）
                option_chain_converted = {}
                calls_data = option_chain_raw.get('calls')
                puts_data = option_chain_raw.get('puts')
                
                # 檢查並轉換 calls
                if calls_data is not None:
                    import pandas as pd
                    if isinstance(calls_data, pd.DataFrame) and not calls_data.empty:
                        option_chain_converted['calls'] = calls_data.to_dict('records')
                        logger.info(f"  轉換 calls DataFrame: {len(option_chain_converted['calls'])} 個行使價")
                    elif isinstance(calls_data, list):
                        option_chain_converted['calls'] = calls_data
                    else:
                        option_chain_converted['calls'] = []
                else:
                    option_chain_converted['calls'] = []
                
                # 檢查並轉換 puts
                if puts_data is not None:
                    import pandas as pd
                    if isinstance(puts_data, pd.DataFrame) and not puts_data.empty:
                        option_chain_converted['puts'] = puts_data.to_dict('records')
                        logger.info(f"  轉換 puts DataFrame: {len(option_chain_converted['puts'])} 個行使價")
                    elif isinstance(puts_data, list):
                        option_chain_converted['puts'] = puts_data
                    else:
                        option_chain_converted['puts'] = []
                else:
                    option_chain_converted['puts'] = []
                
                if option_chain_converted['calls'] or option_chain_converted['puts']:
                    optimal_strike_calc = OptimalStrikeCalculator()
                    
                    # 分析四種策略的最佳行使價
                    strategies = ['long_call', 'long_put', 'short_call', 'short_put']
                    optimal_results = {}
                    
                    # Task 14.1: 獲取 Module 1 支持阻力位數據用於 Long/Short 策略增強
                    sr_data = self.analysis_results.get('module1_support_resistance', {})
                    support_resistance_data = None
                    if sr_data:
                        support_resistance_data = {
                            'support_level': sr_data.get('support_level'),
                            'resistance_level': sr_data.get('resistance_level')
                        }
                        logger.info(f"  使用 Module 1 支持阻力位: 支持 ${support_resistance_data.get('support_level', 0):.2f}, 阻力 ${support_resistance_data.get('resistance_level', 0):.2f}")
                    
                    for strategy in strategies:
                        # Task 14.1: 傳入 support_resistance_data 和啟用 enable_max_profit_analysis
                        result = optimal_strike_calc.analyze_strikes(
                            current_price=current_price,
                            option_chain=option_chain_converted,
                            strategy_type=strategy,
                            days_to_expiration=int(days_to_expiration) if days_to_expiration else 30,
                            iv_rank=iv_rank_value,
                            support_resistance_data=support_resistance_data,  # 新增: 支持阻力位數據
                            enable_max_profit_analysis=True  # 新增: 啟用 Long/Short 策略增強
                        )
                        
                        # 整合 Module 23 IV 環境信息
                        result['iv_environment'] = iv_environment
                        result['iv_trading_suggestion'] = iv_trading_suggestion
                        
                        optimal_results[strategy] = result
                        
                        # Task 14.2: 更新日誌輸出，包含新的分析結果
                        if result.get('best_strike'):
                            best_rec = result['top_recommendations'][0] if result['top_recommendations'] else {}
                            composite_score = best_rec.get('composite_score', 0)
                            max_profit_score = best_rec.get('max_profit_score', 0)
                            
                            # 根據策略類型顯示不同信息
                            if strategy in ['long_call', 'long_put']:
                                # Long 策略: 顯示期望收益和建議持倉天數
                                multi_scenario = best_rec.get('multi_scenario_profit', {})
                                optimal_exit = best_rec.get('optimal_exit_timing', {})
                                expected_pct = multi_scenario.get('expected_profit_pct', 0) if multi_scenario else 0
                                exit_day = optimal_exit.get('recommended_exit_day', 0) if optimal_exit else 0
                                logger.info(f"  {strategy}: 最佳行使價 ${result['best_strike']:.2f}, 評分 {composite_score:.1f}, 期望收益 {expected_pct:.0f}%, 建議持倉 {exit_day} 天")
                            else:
                                # Short 策略: 顯示安全概率和年化收益
                                premium_analysis = best_rec.get('premium_analysis', {})
                                safe_prob = premium_analysis.get('safe_probability', 0) if premium_analysis else 0
                                annualized = premium_analysis.get('annualized_yield_pct', 0) if premium_analysis else 0
                                logger.info(f"  {strategy}: 最佳行使價 ${result['best_strike']:.2f}, 評分 {composite_score:.1f}, 安全概率 {safe_prob*100:.0f}%, 年化 {annualized:.0f}%")
                    
                    self.analysis_results['module22_optimal_strike'] = optimal_results
                    logger.info("* 模塊22完成: 最佳行使價分析")
                    logger.info(f"  IV環境整合: {iv_environment}")
                else:
                    logger.info("! 模塊22跳過: 期權鏈數據不足")
                    self.analysis_results['module22_optimal_strike'] = {
                        'status': 'skipped',
                        'reason': '期權鏈數據不足'
                    }
            except Exception as exc:
                logger.warning(f"! 模塊22執行失敗: {exc}")
                self.analysis_results['module22_optimal_strike'] = {
                    'status': 'error',
                    'reason': str(exc)
                }
            
            # ========== 模塊24: 技術方向分析 ==========
            logger.info("\n→ 運行 Module 24: 技術方向分析...")
            technical_direction = None
            try:
                # 獲取日線數據
                daily_data = self.fetcher.get_daily_candles(ticker, days=200)
                
                # 獲取 15 分鐘數據
                intraday_data = self.fetcher.get_intraday_candles(ticker, resolution='15', days=5)
                
                if daily_data is not None and len(daily_data) >= 50:
                    tech_analyzer = TechnicalDirectionAnalyzer()
                    tech_result = tech_analyzer.analyze(
                        ticker=ticker,
                        daily_data=daily_data,
                        intraday_data=intraday_data,
                        current_price=current_price
                    )
                    
                    self.analysis_results['module24_technical_direction'] = tech_result.to_dict()
                    technical_direction = tech_result
                    
                    logger.info(f"  日線趨勢: {tech_result.daily_trend.trend}")
                    logger.info(f"  綜合方向: {tech_result.combined_direction} ({tech_result.confidence})")
                    logger.info("* 模塊24完成: 技術方向分析")
                else:
                    logger.warning("! 模塊24跳過: 日線數據不足")
                    self.analysis_results['module24_technical_direction'] = {
                        'status': 'skipped',
                        'reason': '日線數據不足'
                    }
            except Exception as exc:
                logger.warning(f"! 模塊24執行失敗: {exc}")
                import traceback
                traceback.print_exc()
                self.analysis_results['module24_technical_direction'] = {
                    'status': 'error',
                    'reason': str(exc)
                }
            
            # Module 25: 波動率微笑分析
            logger.info("\n→ 運行 Module 25: 波動率微笑分析...")
            try:
                if option_chain and 'calls' in option_chain and 'puts' in option_chain:
                    # 準備期權鏈數據
                    calls_list = option_chain['calls'].to_dict('records') if hasattr(option_chain['calls'], 'to_dict') else option_chain['calls']
                    puts_list = option_chain['puts'].to_dict('records') if hasattr(option_chain['puts'], 'to_dict') else option_chain['puts']
                    
                    smile_analyzer = VolatilitySmileAnalyzer()
                    smile_result = smile_analyzer.analyze_smile(
                        option_chain={'calls': calls_list, 'puts': puts_list},
                        current_price=current_price,
                        time_to_expiration=days_to_expiration / 365.0 if days_to_expiration else 0.05,
                        risk_free_rate=analysis_data.get('risk_free_rate', 0.045)
                    )
                    
                    self.analysis_results['module25_volatility_smile'] = smile_result.to_dict()
                    
                    logger.info(f"  ATM IV: {smile_result.atm_iv*100:.2f}%")
                    logger.info(f"  Skew: {smile_result.skew*100:.2f}% ({smile_result.skew_type})")
                    logger.info(f"  微笑形狀: {smile_result.smile_shape}")
                    logger.info(f"  IV 環境: {smile_result.iv_environment}")
                    if smile_result.anomaly_count > 0:
                        logger.warning(f"  定價異常: {smile_result.anomaly_count} 個")
                    logger.info("* 模塊25完成: 波動率微笑分析")
                else:
                    logger.warning("! 模塊25跳過: 期權鏈數據不完整")
                    self.analysis_results['module25_volatility_smile'] = {
                        'status': 'skipped',
                        'reason': '期權鏈數據不完整'
                    }
            except Exception as exc:
                logger.warning(f"! 模塊25執行失敗: {exc}")
                import traceback
                traceback.print_exc()
                self.analysis_results['module25_volatility_smile'] = {
                    'status': 'error',
                    'reason': str(exc)
                }
            
            # Module 26: Long 期權成本效益分析
            logger.info("\n→ 運行 Module 26: Long 期權成本效益分析...")
            try:
                long_analyzer = LongOptionAnalyzer()
                
                # 獲取 ATM 期權數據
                atm_call = None
                atm_put = None
                
                if option_chain and 'calls' in option_chain and 'puts' in option_chain:
                    calls_df = option_chain['calls']
                    puts_df = option_chain['puts']
                    
                    # 找到最接近 ATM 的期權
                    if hasattr(calls_df, 'iloc') and len(calls_df) > 0:
                        calls_df['distance'] = abs(calls_df['strike'] - current_price)
                        atm_idx = calls_df['distance'].idxmin()
                        atm_call = calls_df.loc[atm_idx].to_dict()
                    
                    if hasattr(puts_df, 'iloc') and len(puts_df) > 0:
                        puts_df['distance'] = abs(puts_df['strike'] - current_price)
                        atm_idx = puts_df['distance'].idxmin()
                        atm_put = puts_df.loc[atm_idx].to_dict()
                
                if atm_call and atm_put:
                    # 獲取權利金（優先使用 lastPrice，否則用 mid price）
                    call_premium = atm_call.get('lastPrice') or atm_call.get('last') or \
                                   ((atm_call.get('bid', 0) + atm_call.get('ask', 0)) / 2)
                    put_premium = atm_put.get('lastPrice') or atm_put.get('last') or \
                                  ((atm_put.get('bid', 0) + atm_put.get('ask', 0)) / 2)
                    
                    # 獲取 Greeks
                    call_delta = atm_call.get('delta', 0.5)
                    put_delta = atm_put.get('delta', -0.5)
                    call_theta = atm_call.get('theta', 0)
                    put_theta = atm_put.get('theta', 0)
                    
                    # 獲取 IV
                    iv = analysis_data.get('implied_volatility', 30)
                    
                    # 分析 Long Call 和 Long Put
                    module26_result = long_analyzer.analyze_both(
                        stock_price=current_price,
                        call_strike=atm_call.get('strike', current_price),
                        call_premium=call_premium if call_premium else 1.0,
                        put_strike=atm_put.get('strike', current_price),
                        put_premium=put_premium if put_premium else 1.0,
                        days_to_expiration=int(days_to_expiration) if days_to_expiration else 30,
                        call_delta=call_delta if call_delta else 0.5,
                        put_delta=put_delta if put_delta else -0.5,
                        call_theta=call_theta if call_theta else 0,
                        put_theta=put_theta if put_theta else 0,
                        iv=iv
                    )
                    
                    self.analysis_results['module26_long_option_analysis'] = module26_result
                    
                    # 輸出摘要
                    call_score = module26_result['long_call']['score']['total_score']
                    put_score = module26_result['long_put']['score']['total_score']
                    better = module26_result['comparison']['better_choice']
                    
                    logger.info(f"  Long Call 評分: {call_score} ({module26_result['long_call']['score']['grade']})")
                    logger.info(f"  Long Put 評分: {put_score} ({module26_result['long_put']['score']['grade']})")
                    logger.info(f"  推薦: {better}")
                    logger.info("* 模塊26完成: Long 期權成本效益分析")
                else:
                    logger.warning("! 模塊26跳過: 無法獲取 ATM 期權數據")
                    self.analysis_results['module26_long_option_analysis'] = {
                        'status': 'skipped',
                        'reason': '無法獲取 ATM 期權數據'
                    }
            except Exception as exc:
                logger.warning(f"! 模塊26執行失敗: {exc}")
                import traceback
                traceback.print_exc()
                self.analysis_results['module26_long_option_analysis'] = {
                    'status': 'error',
                    'reason': str(exc)
                }
            
            # 新增: 策略推薦引擎（整合 Module 24 技術方向）
            logger.info("\n→ 運行策略推薦引擎...")
            try:
                # 準備輸入數據
                # 1. 趨勢判斷 - 優先使用 Module 24 技術方向
                sr_data = self.analysis_results.get('module1_support_resistance')
                trend = 'Sideways'
                support = 0
                resistance = 0
                
                # 始終從 Module 1 獲取支持/阻力位（用於策略推薦）
                if sr_data:
                    support = sr_data.get('support_level', 0)
                    resistance = sr_data.get('resistance_level', 0)
                
                # 使用 Module 24 技術方向（如果可用）
                if technical_direction and technical_direction.daily_trend:
                    if technical_direction.daily_trend.trend == 'Bullish':
                        trend = 'Up'
                    elif technical_direction.daily_trend.trend == 'Bearish':
                        trend = 'Down'
                    logger.info(f"  趨勢來源: Module 24 技術分析 ({trend})")
                elif sr_data and support > 0 and resistance > 0:
                    # 降級: 使用支持/阻力位判斷
                    mid_point = (support + resistance) / 2
                    if current_price > mid_point * 1.05:
                        trend = 'Up'
                    elif current_price < mid_point * 0.95:
                        trend = 'Down'
                    logger.info(f"  趨勢來源: 支持/阻力位分析 ({trend})")
                
                # 2. 估值判斷
                pe_data = self.analysis_results.get('module4_pe_valuation')
                valuation = 'Fair'
                if pe_data:
                    peg_val = pe_data.get('peg_valuation', '')
                    if '低估' in peg_val: valuation = 'Undervalued'
                    elif '高估' in peg_val: valuation = 'Overvalued'
                
                # 3. 波動率分析 - 使用真實 IV Rank 和 IV/HV 比率
                hv_data = self.analysis_results.get('module18_historical_volatility')
                iv_hv_ratio = 1.0
                iv_rank_value = 50.0  # 默認中位數
                iv_percentile_value = 50.0
                
                if hv_data:
                    # 獲取 IV/HV 比率
                    if 'iv_hv_comparison' in hv_data:
                        iv_hv_ratio = hv_data['iv_hv_comparison'].get('ratio', 1.0)
                    # 獲取真實 IV Rank
                    if 'iv_rank' in hv_data:
                        iv_rank_value = hv_data.get('iv_rank', 50.0)
                    # 獲取 IV Percentile
                    if 'iv_percentile' in hv_data:
                        iv_percentile_value = hv_data.get('iv_percentile', 50.0)
                
                logger.info(f"  IV Rank: {iv_rank_value:.1f}%, IV/HV: {iv_hv_ratio:.2f}, 估值: {valuation}")
                logger.info(f"  支持位: ${support:.2f}, 阻力位: ${resistance:.2f}")
                
                # 執行推薦
                recommender = StrategyRecommender()
                recommendations = recommender.recommend(
                    current_price=current_price,
                    iv_rank=iv_rank_value,
                    iv_percentile=iv_percentile_value,
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
    
    def run_manual_analysis(self, ticker: str, manual_data: dict, confidence: float = 1.0):
        """
        手動輸入模式分析 - 繞過 API，使用用戶提供的數據
        
        參數:
            ticker: 股票代碼
            manual_data: 手動輸入的數據字典，包含:
                - stock_price: 當前股價 (必填)
                - strike: 行使價 (必填)
                - expiration: 到期日 YYYY-MM-DD (必填)
                - premium: 期權價格
                - option_type: 'C' 或 'P'
                - iv: 隱含波動率 (%)
                - bid/ask: 買賣價
                - delta/gamma/theta: Greeks
                - open_interest/volume: 持倉量/成交量
            confidence: IV 信心度 Z 值
        
        返回:
            dict: 分析結果
        """
        try:
            logger.info(f"\n開始手動模式分析 {ticker}")
            self.analysis_results = {}
            
            # 提取手動數據
            stock_price = manual_data['stock_price']
            strike = manual_data['strike']
            expiration = manual_data['expiration']
            premium = manual_data.get('premium', 0)
            option_type = manual_data.get('option_type', 'C')
            iv = manual_data.get('iv', 30.0)  # 默認 30%
            bid = manual_data.get('bid', 0)
            ask = manual_data.get('ask', 0)
            delta = manual_data.get('delta')
            gamma = manual_data.get('gamma')
            theta = manual_data.get('theta')
            open_interest = manual_data.get('open_interest', 0)
            volume = manual_data.get('volume', 0)
            
            # 計算到期天數
            from datetime import datetime
            exp_date = datetime.strptime(expiration, '%Y-%m-%d')
            days_to_expiration = max(1, (exp_date - datetime.now()).days)
            
            # 使用交易日計算器（如果可用）
            if hasattr(self.fetcher, 'trading_days_calc') and self.fetcher.trading_days_calc:
                days_to_expiration = self.fetcher.trading_days_calc.calculate_trading_days(
                    datetime.now(), exp_date
                )
            
            logger.info(f"  股價: ${stock_price:.2f}")
            logger.info(f"  行使價: ${strike:.2f}")
            logger.info(f"  到期日: {expiration} ({days_to_expiration} 天)")
            logger.info(f"  期權類型: {'Call' if option_type == 'C' else 'Put'}")
            logger.info(f"  期權價格: ${premium:.2f}")
            logger.info(f"  IV: {iv:.1f}%")
            
            # 模塊1: 支持/阻力位 (IV法)
            sr_calc = SupportResistanceCalculator()
            sr_results_multi = sr_calc.calculate_multi_confidence(
                stock_price=stock_price,
                implied_volatility=iv,
                days_to_expiration=int(days_to_expiration),
                confidence_levels=['68%', '80%', '90%', '95%', '99%']
            )
            self.analysis_results['module1_support_resistance_multi'] = sr_results_multi
            logger.info("* 模塊1完成: 支持/阻力位")
            
            # 模塊2: 公允值
            analysis_date_str = datetime.now().strftime('%Y-%m-%d')
            fv_calc = FairValueCalculator()
            fv_result = fv_calc.calculate(
                stock_price=stock_price,
                risk_free_rate=4.5,  # 默認無風險利率
                expiration_date=expiration,
                expected_dividend=0,
                calculation_date=analysis_date_str,
                days_to_expiration=days_to_expiration
            )
            self.analysis_results['module2_fair_value'] = fv_result.to_dict()
            logger.info("* 模塊2完成: 公允值")
            
            # 模塊7-10: 單腿策略損益
            price_scenarios = [
                round(stock_price * 0.9, 2),
                round(stock_price, 2),
                round(stock_price * 1.1, 2)
            ]
            
            if option_type == 'C':
                # Long Call
                long_call_calc = LongCallCalculator()
                long_call_results = [
                    long_call_calc.calculate(
                        strike_price=strike,
                        option_premium=premium,
                        stock_price_at_expiry=price,
                        calculation_date=analysis_date_str
                    ).to_dict()
                    for price in price_scenarios
                ]
                self.analysis_results['module7_long_call'] = long_call_results
                logger.info("* 模塊7完成: Long Call 損益")
                
                # Short Call
                short_call_calc = ShortCallCalculator()
                short_call_results = [
                    short_call_calc.calculate(
                        strike_price=strike,
                        option_premium=premium,
                        stock_price_at_expiry=price,
                        calculation_date=analysis_date_str
                    ).to_dict()
                    for price in price_scenarios
                ]
                self.analysis_results['module9_short_call'] = short_call_results
                logger.info("* 模塊9完成: Short Call 損益")
            else:
                # Long Put
                long_put_calc = LongPutCalculator()
                long_put_results = [
                    long_put_calc.calculate(
                        strike_price=strike,
                        option_premium=premium,
                        stock_price_at_expiry=price,
                        calculation_date=analysis_date_str
                    ).to_dict()
                    for price in price_scenarios
                ]
                self.analysis_results['module8_long_put'] = long_put_results
                logger.info("* 模塊8完成: Long Put 損益")
                
                # Short Put
                short_put_calc = ShortPutCalculator()
                short_put_results = [
                    short_put_calc.calculate(
                        strike_price=strike,
                        option_premium=premium,
                        stock_price_at_expiry=price,
                        calculation_date=analysis_date_str
                    ).to_dict()
                    for price in price_scenarios
                ]
                self.analysis_results['module10_short_put'] = short_put_results
                logger.info("* 模塊10完成: Short Put 損益")
            
            # 模塊15: Black-Scholes 理論價
            bs_calc = BlackScholesCalculator()
            time_to_expiry = days_to_expiration / 365.0
            bs_result = bs_calc.calculate_option_price(
                stock_price=stock_price,
                strike_price=strike,
                time_to_expiration=time_to_expiry,
                risk_free_rate=0.045,
                volatility=iv / 100.0,
                option_type=option_type
            )
            self.analysis_results['module15_black_scholes'] = bs_result.to_dict()
            logger.info("* 模塊15完成: Black-Scholes 理論價")
            
            # 模塊16: Greeks（如果用戶沒提供，使用計算值）
            greeks_calc = GreeksCalculator()
            greeks_result = greeks_calc.calculate_all_greeks(
                stock_price=stock_price,
                strike_price=strike,
                time_to_expiration=time_to_expiry,
                risk_free_rate=0.045,
                volatility=iv / 100.0,
                option_type=option_type
            )
            
            # 如果用戶提供了 Greeks，使用用戶的值
            greeks_dict = greeks_result.to_dict()
            if delta is not None:
                greeks_dict['delta'] = delta
                greeks_dict['delta_source'] = 'manual'
            if gamma is not None:
                greeks_dict['gamma'] = gamma
                greeks_dict['gamma_source'] = 'manual'
            if theta is not None:
                greeks_dict['theta'] = theta
                greeks_dict['theta_source'] = 'manual'
            
            self.analysis_results['module16_greeks'] = greeks_dict
            logger.info("* 模塊16完成: Greeks")
            
            # 記錄手動輸入的數據
            self.analysis_results['manual_input'] = {
                'stock_price': stock_price,
                'strike': strike,
                'expiration': expiration,
                'days_to_expiration': days_to_expiration,
                'premium': premium,
                'option_type': option_type,
                'iv': iv,
                'bid': bid,
                'ask': ask,
                'bid_ask_spread': ask - bid if bid and ask else None,
                'delta': delta,
                'gamma': gamma,
                'theta': theta,
                'open_interest': open_interest,
                'volume': volume
            }
            
            # 生成報告
            logger.info("\n→ 生成分析報告...")
            
            # 構建簡化的 analysis_data 用於報告
            analysis_data = {
                'ticker': ticker,
                'current_price': stock_price,
                'implied_volatility': iv,
                'expiration_date': expiration,
                'days_to_expiration': days_to_expiration,
                'analysis_date': analysis_date_str,
                'atm_option': {
                    'strike': strike,
                    'call' if option_type == 'C' else 'put': {
                        'bid': bid,
                        'ask': ask,
                        'lastPrice': premium,
                        'volume': volume,
                        'openInterest': open_interest,
                        'delta': delta,
                        'gamma': gamma,
                        'theta': theta
                    }
                },
                'data_source': 'manual_input'
            }
            
            report = self.report_generator.generate_complete_report(
                ticker=ticker,
                analysis_data=analysis_data,
                calculation_results=self.analysis_results
            )
            
            logger.info("=" * 70)
            logger.info("手動模式分析完成！")
            logger.info("=" * 70)
            
            return {
                'status': 'success',
                'ticker': ticker,
                'timestamp': datetime.now(),
                'raw_data': analysis_data,
                'calculations': self.analysis_results,
                'report': report,
                'mode': 'manual'
            }
            
        except Exception as e:
            logger.error(f"\nx 手動模式分析失敗: {e}")
            import traceback
            traceback.print_exc()
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def run_hybrid_analysis(self, ticker: str, expiration: str, 
                           user_overrides: dict, confidence: float = 1.0):
        """
        混合模式分析 - 從 API 獲取股票數據，用戶補充期權數據
        
        參數:
            ticker: 股票代碼
            expiration: 到期日 YYYY-MM-DD
            user_overrides: 用戶覆蓋的數據，可包含:
                - strike: 行使價 (必填)
                - premium: 期權價格
                - option_type: 'C' 或 'P'
                - iv: 隱含波動率 (%)
                - bid/ask: 買賣價
                - delta/gamma/theta/vega/rho: Greeks
                - open_interest/volume: 持倉量/成交量
                - stock_price: 覆蓋 API 股價
                - eps/pe/dividend: 覆蓋基本面數據
            confidence: IV 信心度 Z 值
        
        返回:
            dict: 分析結果
        """
        try:
            logger.info(f"\n開始混合模式分析 {ticker}")
            self.analysis_results = {}
            
            # 第1步: 從 API 獲取股票基本數據
            logger.info("→ 從 API 獲取股票基本數據...")
            
            stock_info = self.fetcher.get_stock_info(ticker)
            if not stock_info:
                logger.warning("! API 無法獲取股票數據，使用用戶提供的數據")
                stock_info = {}
            
            # 獲取無風險利率
            risk_free_rate = user_overrides.get('risk_free_rate')
            if not risk_free_rate:
                try:
                    risk_free_rate = self.fetcher.get_risk_free_rate()
                except:
                    risk_free_rate = 4.5
            
            # 合併數據：API 數據 + 用戶覆蓋
            stock_price = user_overrides.get('stock_price') or stock_info.get('current_price') or stock_info.get('price')
            if not stock_price:
                raise ValueError("無法獲取股價，請使用 --stock-price 參數提供")
            
            strike = user_overrides.get('strike')
            if not strike:
                raise ValueError("請使用 --strike 參數提供行使價")
            
            option_type = user_overrides.get('option_type', 'C')
            premium = user_overrides.get('premium', 0)
            iv = user_overrides.get('iv', 30.0)  # 默認 30%
            bid = user_overrides.get('bid', 0)
            ask = user_overrides.get('ask', 0)
            delta = user_overrides.get('delta')
            gamma = user_overrides.get('gamma')
            theta = user_overrides.get('theta')
            vega = user_overrides.get('vega')
            rho = user_overrides.get('rho')
            open_interest = user_overrides.get('open_interest', 0)
            volume = user_overrides.get('volume', 0)
            
            # 基本面數據
            eps = user_overrides.get('eps') or stock_info.get('eps') or stock_info.get('eps_ttm')
            pe = user_overrides.get('pe') or stock_info.get('pe_ratio') or stock_info.get('pe')
            dividend = user_overrides.get('dividend') or stock_info.get('annual_dividend', 0)
            
            # 計算到期天數
            from datetime import datetime
            exp_date = datetime.strptime(expiration, '%Y-%m-%d')
            days_to_expiration = max(1, (exp_date - datetime.now()).days)
            
            if hasattr(self.fetcher, 'trading_days_calc') and self.fetcher.trading_days_calc:
                days_to_expiration = self.fetcher.trading_days_calc.calculate_trading_days(
                    datetime.now(), exp_date
                )
            
            logger.info(f"\n=== 數據來源摘要 ===")
            logger.info(f"  股價: ${stock_price:.2f} {'(API)' if not user_overrides.get('stock_price') else '(手動)'}")
            logger.info(f"  行使價: ${strike:.2f} (手動)")
            logger.info(f"  到期日: {expiration} ({days_to_expiration} 天)")
            logger.info(f"  期權類型: {'Call' if option_type == 'C' else 'Put'}")
            logger.info(f"  期權價格: ${premium:.2f} (手動)")
            logger.info(f"  IV: {iv:.1f}% (手動)")
            logger.info(f"  無風險利率: {risk_free_rate:.2f}%")
            if eps:
                logger.info(f"  EPS: ${eps:.2f} {'(API)' if not user_overrides.get('eps') else '(手動)'}")
            if pe:
                logger.info(f"  P/E: {pe:.2f} {'(API)' if not user_overrides.get('pe') else '(手動)'}")
            
            # 構建 analysis_data
            analysis_date_str = datetime.now().strftime('%Y-%m-%d')
            analysis_data = {
                'ticker': ticker,
                'current_price': stock_price,
                'implied_volatility': iv,
                'expiration_date': expiration,
                'days_to_expiration': days_to_expiration,
                'analysis_date': analysis_date_str,
                'risk_free_rate': risk_free_rate,
                'eps': eps,
                'pe_ratio': pe,
                'annual_dividend': dividend,
                'atm_option': {
                    'strike': strike,
                    'call' if option_type == 'C' else 'put': {
                        'bid': bid,
                        'ask': ask,
                        'lastPrice': premium,
                        'volume': volume,
                        'openInterest': open_interest,
                        'delta': delta,
                        'gamma': gamma,
                        'theta': theta
                    }
                },
                'data_source': 'hybrid (API + manual)'
            }
            
            # 運行計算模塊
            logger.info("\n→ 運行計算模塊...")
            
            # 模塊1: 支持/阻力位
            sr_calc = SupportResistanceCalculator()
            sr_results_multi = sr_calc.calculate_multi_confidence(
                stock_price=stock_price,
                implied_volatility=iv,
                days_to_expiration=int(days_to_expiration),
                confidence_levels=['68%', '80%', '90%', '95%', '99%']
            )
            self.analysis_results['module1_support_resistance_multi'] = sr_results_multi
            logger.info("* 模塊1完成: 支持/阻力位")
            
            # 模塊2: 公允值
            fv_calc = FairValueCalculator()
            fv_result = fv_calc.calculate(
                stock_price=stock_price,
                risk_free_rate=risk_free_rate,
                expiration_date=expiration,
                expected_dividend=dividend or 0,
                calculation_date=analysis_date_str,
                days_to_expiration=days_to_expiration
            )
            self.analysis_results['module2_fair_value'] = fv_result.to_dict()
            logger.info("* 模塊2完成: 公允值")
            
            # 模塊4: PE估值（如果有數據）
            if eps and pe and eps > 0 and pe > 0:
                pe_calc = PEValuationCalculator()
                pe_result = pe_calc.calculate(
                    eps=eps,
                    pe_multiple=pe,
                    current_price=stock_price,
                    calculation_date=analysis_date_str
                )
                self.analysis_results['module4_pe_valuation'] = pe_result.to_dict()
                logger.info("* 模塊4完成: PE估值")
            
            # 模塊7-10: 單腿策略損益
            price_scenarios = [
                round(stock_price * 0.9, 2),
                round(stock_price, 2),
                round(stock_price * 1.1, 2)
            ]
            
            if option_type == 'C':
                long_call_calc = LongCallCalculator()
                long_call_results = [
                    long_call_calc.calculate(
                        strike_price=strike,
                        option_premium=premium,
                        stock_price_at_expiry=price,
                        calculation_date=analysis_date_str
                    ).to_dict()
                    for price in price_scenarios
                ]
                self.analysis_results['module7_long_call'] = long_call_results
                logger.info("* 模塊7完成: Long Call 損益")
                
                short_call_calc = ShortCallCalculator()
                short_call_results = [
                    short_call_calc.calculate(
                        strike_price=strike,
                        option_premium=premium,
                        stock_price_at_expiry=price,
                        calculation_date=analysis_date_str
                    ).to_dict()
                    for price in price_scenarios
                ]
                self.analysis_results['module9_short_call'] = short_call_results
                logger.info("* 模塊9完成: Short Call 損益")
            else:
                long_put_calc = LongPutCalculator()
                long_put_results = [
                    long_put_calc.calculate(
                        strike_price=strike,
                        option_premium=premium,
                        stock_price_at_expiry=price,
                        calculation_date=analysis_date_str
                    ).to_dict()
                    for price in price_scenarios
                ]
                self.analysis_results['module8_long_put'] = long_put_results
                logger.info("* 模塊8完成: Long Put 損益")
                
                short_put_calc = ShortPutCalculator()
                short_put_results = [
                    short_put_calc.calculate(
                        strike_price=strike,
                        option_premium=premium,
                        stock_price_at_expiry=price,
                        calculation_date=analysis_date_str
                    ).to_dict()
                    for price in price_scenarios
                ]
                self.analysis_results['module10_short_put'] = short_put_results
                logger.info("* 模塊10完成: Short Put 損益")
            
            # 模塊15: Black-Scholes 理論價
            bs_calc = BlackScholesCalculator()
            time_to_expiry = days_to_expiration / 365.0
            bs_result = bs_calc.calculate_option_price(
                stock_price=stock_price,
                strike_price=strike,
                time_to_expiration=time_to_expiry,
                risk_free_rate=risk_free_rate / 100.0,
                volatility=iv / 100.0,
                option_type=option_type
            )
            self.analysis_results['module15_black_scholes'] = bs_result.to_dict()
            logger.info("* 模塊15完成: Black-Scholes 理論價")
            
            # 模塊16: Greeks
            greeks_calc = GreeksCalculator()
            greeks_result = greeks_calc.calculate_all_greeks(
                stock_price=stock_price,
                strike_price=strike,
                time_to_expiration=time_to_expiry,
                risk_free_rate=risk_free_rate / 100.0,
                volatility=iv / 100.0,
                option_type=option_type
            )
            
            greeks_dict = greeks_result.to_dict()
            # 用戶提供的 Greeks 覆蓋計算值
            if delta is not None:
                greeks_dict['delta'] = delta
                greeks_dict['delta_source'] = 'manual (IBKR)'
            if gamma is not None:
                greeks_dict['gamma'] = gamma
                greeks_dict['gamma_source'] = 'manual (IBKR)'
            if theta is not None:
                greeks_dict['theta'] = theta
                greeks_dict['theta_source'] = 'manual (IBKR)'
            if vega is not None:
                greeks_dict['vega'] = vega
                greeks_dict['vega_source'] = 'manual (IBKR)'
            if rho is not None:
                greeks_dict['rho'] = rho
                greeks_dict['rho_source'] = 'manual (IBKR)'
            
            self.analysis_results['module16_greeks'] = greeks_dict
            logger.info("* 模塊16完成: Greeks")
            
            # 記錄數據來源
            self.analysis_results['data_sources'] = {
                'mode': 'hybrid',
                'api_data': ['stock_price', 'eps', 'pe', 'risk_free_rate'] if not user_overrides.get('stock_price') else [],
                'manual_data': list(user_overrides.keys())
            }
            
            # 生成報告
            logger.info("\n→ 生成分析報告...")
            report = self.report_generator.generate_complete_report(
                ticker=ticker,
                analysis_data=analysis_data,
                calculation_results=self.analysis_results
            )
            
            logger.info("=" * 70)
            logger.info("混合模式分析完成！")
            logger.info("=" * 70)
            
            return {
                'status': 'success',
                'ticker': ticker,
                'timestamp': datetime.now(),
                'raw_data': analysis_data,
                'calculations': self.analysis_results,
                'report': report,
                'mode': 'hybrid'
            }
            
        except Exception as e:
            logger.error(f"\nx 混合模式分析失敗: {e}")
            import traceback
            traceback.print_exc()
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
    
    # 手動輸入模式參數（繞過 API）
    parser.add_argument('--manual', action='store_true', default=False,
                       help='完全手動模式，繞過所有 API')
    parser.add_argument('--hybrid', action='store_true', default=False,
                       help='混合模式：API 獲取股票數據 + 手動輸入期權數據')
    
    # 可手動覆蓋的參數（混合模式或手動模式使用）
    parser.add_argument('--stock-price', type=float, default=None,
                       help='當前股價 (手動模式必填，混合模式可選)')
    parser.add_argument('--iv', type=float, default=None,
                       help='隱含波動率 %% (例: 68.6 表示 68.6%%)')
    parser.add_argument('--bid', type=float, default=None,
                       help='期權買價 Bid')
    parser.add_argument('--ask', type=float, default=None,
                       help='期權賣價 Ask')
    parser.add_argument('--delta', type=float, default=None,
                       help='Delta 值')
    parser.add_argument('--gamma', type=float, default=None,
                       help='Gamma 值')
    parser.add_argument('--theta', type=float, default=None,
                       help='Theta 值')
    parser.add_argument('--vega', type=float, default=None,
                       help='Vega 值')
    parser.add_argument('--rho', type=float, default=None,
                       help='Rho 值')
    parser.add_argument('--open-interest', type=int, default=None,
                       help='未平倉合約數')
    parser.add_argument('--volume', type=int, default=None,
                       help='成交量')
    
    # 額外的股票/基本面參數
    parser.add_argument('--eps', type=float, default=None,
                       help='每股盈利 EPS')
    parser.add_argument('--pe', type=float, default=None,
                       help='市盈率 P/E')
    parser.add_argument('--dividend', type=float, default=None,
                       help='年度股息')
    parser.add_argument('--risk-free-rate', type=float, default=None,
                       help='無風險利率 %% (默認 4.5)')
    
    args = parser.parse_args()
    
    # 構建用戶覆蓋數據（適用於所有模式）
    user_overrides = {
        'stock_price': args.stock_price,
        'strike': args.strike,
        'expiration': args.expiration,
        'premium': args.premium,
        'option_type': (args.type or 'C').upper() if args.type else None,
        'iv': args.iv,
        'bid': args.bid,
        'ask': args.ask,
        'delta': args.delta,
        'gamma': args.gamma,
        'theta': args.theta,
        'vega': args.vega,
        'rho': args.rho,
        'open_interest': args.open_interest,
        'volume': args.volume,
        'eps': args.eps,
        'pe': args.pe,
        'dividend': args.dividend,
        'risk_free_rate': args.risk_free_rate
    }
    # 移除 None 值
    user_overrides = {k: v for k, v in user_overrides.items() if v is not None}
    
    # 完全手動模式
    if args.manual:
        # 驗證必填參數
        if not args.stock_price:
            print("錯誤: 手動模式需要 --stock-price 參數")
            return
        if not args.strike:
            print("錯誤: 手動模式需要 --strike 參數")
            return
        if not args.expiration:
            print("錯誤: 手動模式需要 --expiration 參數")
            return
        
        # 構建手動數據
        manual_data = {
            'stock_price': args.stock_price,
            'strike': args.strike,
            'expiration': args.expiration,
            'premium': args.premium or ((args.bid + args.ask) / 2 if args.bid and args.ask else 0),
            'option_type': (args.type or 'C').upper(),
            'iv': args.iv,
            'bid': args.bid,
            'ask': args.ask,
            'delta': args.delta,
            'gamma': args.gamma,
            'theta': args.theta,
            'vega': args.vega,
            'rho': args.rho,
            'open_interest': args.open_interest,
            'volume': args.volume,
            'eps': args.eps,
            'pe': args.pe,
            'dividend': args.dividend,
            'risk_free_rate': args.risk_free_rate or 4.5
        }
        
        print("\n" + "=" * 70)
        print("完全手動模式 - 期權分析")
        print("=" * 70)
        
        # 啟動系統（手動模式）
        system = OptionsAnalysisSystem(use_ibkr=False)
        results = system.run_manual_analysis(
            ticker=args.ticker,
            manual_data=manual_data,
            confidence=args.confidence
        )
    
    # 混合模式：API 獲取股票數據 + 手動輸入期權數據
    elif args.hybrid:
        if not args.strike:
            print("錯誤: 混合模式需要 --strike 參數")
            return
        if not args.expiration:
            print("錯誤: 混合模式需要 --expiration 參數")
            return
        
        print("\n" + "=" * 70)
        print("混合模式 - API + 手動輸入")
        print("=" * 70)
        print("從 API 獲取: 股價、EPS、PE、無風險利率等")
        print("手動輸入: 期權價格、IV、Greeks 等")
        print("=" * 70)
        
        # 啟動系統（混合模式）
        system = OptionsAnalysisSystem(use_ibkr=args.use_ibkr)
        results = system.run_hybrid_analysis(
            ticker=args.ticker,
            expiration=args.expiration,
            user_overrides=user_overrides,
            confidence=args.confidence
        )
    
    else:
        # 正常模式：從 API 獲取數據（但仍可使用 user_overrides 覆蓋）
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
