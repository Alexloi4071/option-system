# calculation_layer/module14_monitoring_posts.py
"""
模塊14: 12監察崗位分析
書籍來源: 《期權制勝》第十四課
"""

import logging
from dataclasses import dataclass, field
from typing import Dict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MonitoringPostsResult:
    """12監察崗位分析結果"""
    stock_price: float
    option_premium: float
    iv: float
    delta: float
    open_interest: int
    volume: int
    bid_ask_spread: float
    atr: float
    dividend_date: str
    earnings_date: str
    expiration_date: str
    vix: float
    total_alerts: int
    risk_level: str
    calculation_date: str
    
    # 12個崗位狀態字段
    post1_stock_price_status: str = ""
    post2_option_premium_status: str = ""
    post3_iv_status: str = ""
    post4_delta_status: str = ""
    post5_open_interest_status: str = ""
    post6_volume_status: str = ""
    post7_bid_ask_spread_status: str = ""
    post8_atr_status: str = ""
    post9_dividend_date_status: str = ""
    post10_earnings_date_status: str = ""
    post11_expiration_date_status: str = ""
    post12_vix_status: str = ""
    
    # 崗位13: IV Rank 歷史判斷（美股市場增強）
    post13_iv_rank_status: str = ""
    
    # 詳細崗位信息
    post_details: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        result = {
            'stock_price': round(self.stock_price, 2),
            'option_premium': round(self.option_premium, 2),
            'iv': round(self.iv, 2),
            'delta': round(self.delta, 4),
            'open_interest': self.open_interest,
            'volume': self.volume,
            'bid_ask_spread': round(self.bid_ask_spread, 2),
            'atr': round(self.atr, 2),
            'total_alerts': self.total_alerts,
            'risk_level': self.risk_level,
            'calculation_date': self.calculation_date,
            # 12個崗位狀態
            'post1_stock_price_status': self.post1_stock_price_status,
            'post2_option_premium_status': self.post2_option_premium_status,
            'post3_iv_status': self.post3_iv_status,
            'post4_delta_status': self.post4_delta_status,
            'post5_open_interest_status': self.post5_open_interest_status,
            'post6_volume_status': self.post6_volume_status,
            'post7_bid_ask_spread_status': self.post7_bid_ask_spread_status,
            'post8_atr_status': self.post8_atr_status,
            'post9_dividend_date_status': self.post9_dividend_date_status,
            'post10_earnings_date_status': self.post10_earnings_date_status,
            'post11_expiration_date_status': self.post11_expiration_date_status,
            'post12_vix_status': self.post12_vix_status,
            # 崗位13: IV Rank 歷史判斷
            'post13_iv_rank_status': self.post13_iv_rank_status,
        }
        if self.post_details:
            result['post_details'] = self.post_details
        return result


class MonitoringPostsCalculator:
    """
    12監察崗位計算器
    
    書籍來源: 《期權制勝》第十四課
    
    12個監察崗位 (100%書籍):
    ────────────────────────────────
    1. 正股價格監察
    2. 期權金監察
    3. 隱含波動率監察
    4. Delta 0.1-0.15監察 (適用於沽出期權策略)
    5. 未平倉合約監察
    6. 成交量監察
    7. 買賣盤差價監察
    8. ATR波幅監察
    9. 派息日監察
    10. 業績公佈監察
    11. 到期日監察
    12. 市場情緒監察(VIX)
    
    理論:
    完整的期權交易管理需要持續監控
    12個關鍵指標可以全面覆蓋風險點
    ────────────────────────────────
    """
    
    def __init__(self):
        logger.info("* 12監察崗位計算器已初始化")
    
    def calculate(self,
                  stock_price: float,
                  option_premium: float,
                  iv: float,
                  delta: float,
                  open_interest: int,
                  volume: int,
                  bid_ask_spread: float,
                  atr: float,
                  vix: float,
                  dividend_date: str = "",         # 岗位9: 派息日期
                  earnings_date: str = "",         # 岗位10: 業績發布日
                  expiration_date: str = "",       # 岗位11: 到期日
                  calculation_date: str = None) -> MonitoringPostsResult:
        try:
            logger.info(f"開始12監察崗位分析...")
            logger.info(f"  監察10個關鍵指標...")
            
            if not self._validate_inputs(stock_price, option_premium, iv, delta, volume, bid_ask_spread, atr, vix):
                raise ValueError("輸入參數無效")
            
            if calculation_date is None:
                calculation_date = datetime.now().strftime('%Y-%m-%d')
            
            # 監察報警系統
            alerts = 0
            post_details = {}
            
            # ========== 崗位1: 正股價格監察 ==========
            price_change_threshold = 0.05  # 5%變化閾值
            post1_status = "OK 正常"
            post_details['post1'] = {
                'name': '正股價格監察',
                'value': stock_price,
                'threshold': f'±{price_change_threshold*100:.0f}%',
                'status': post1_status
            }
            
            # ========== 崗位2: 期權金監察 ==========
            premium_change_threshold = 0.20  # 20%變化閾值
            post2_status = "OK 正常"
            post_details['post2'] = {
                'name': '期權金監察',
                'value': option_premium,
                'threshold': f'±{premium_change_threshold*100:.0f}%',
                'status': post2_status
            }
            
            # ========== 崗位3: 隱含波動率監察 ==========
            # 動態閾值：VIX + 10%（更適合美國市場）
            # 原因：不同股票的正常IV差異大（科技股30-50%，大盤股20-35%）
            iv_threshold = vix + 10.0 if vix > 0 else 40.0  # 降級到固定40%
            if iv > iv_threshold:
                alerts += 1
                post3_status = "! 警報"
                logger.warning(f"! 崗位3警報: IV過高 ({iv:.2f}% > {iv_threshold:.2f}%)")
            else:
                post3_status = "OK 正常"
            post_details['post3'] = {
                'name': '隱含波動率監察',
                'value': iv,
                'threshold': iv_threshold,
                'status': post3_status,
                'note': f'動態閾值 (VIX {vix:.1f}% + 10%)'
            }
            
            # ========== 崗位4: Delta監察 (適用於沽出期權策略) ==========
            delta_target_min = 0.10
            delta_target_max = 0.15
            delta_otm_threshold = 0.20  # 深度價外閾值（三不買原則）
            
            # 檢查Delta範圍
            if delta > delta_target_max or delta < delta_target_min:
                alerts += 1
                post4_status = "! 警報"
                logger.warning(f"! 崗位4警報: Delta不在目標範圍 ({delta:.4f})")
            else:
                post4_status = "OK 正常"
            
            # 額外檢查：深度價外期權（三不買原則）
            if delta < delta_otm_threshold:
                alerts += 1
                post4_status = "! 警報 - 深度價外"
                logger.warning(f"! 崗位4警報: Delta < {delta_otm_threshold} - 深度價外期權，勝率低（三不買原則）")
            
            post_details['post4'] = {
                'name': 'Delta監察',
                'value': delta,
                'threshold': f'{delta_target_min}-{delta_target_max}',
                'otm_threshold': delta_otm_threshold,
                'status': post4_status,
                'note': 'Delta < 0.20 為深度價外，不建議交易（三不買原則）'
            }
            
            # ========== 崗位5: 未平倉合約監察（三不買原則）==========
            # 美股市場標準：OI ≥ 500（推薦）
            # 最低標準：OI ≥ 100（可接受）
            oi_threshold_recommended = 500
            oi_threshold_minimum = 100
            
            if open_interest < oi_threshold_minimum:
                alerts += 1
                post5_status = "! 嚴重警報"
                logger.warning(f"! 崗位5嚴重警報: 未平倉合約極低 ({open_interest} < {oi_threshold_minimum}) - 不建議交易（三不買原則）")
            elif open_interest < oi_threshold_recommended:
                alerts += 1
                post5_status = "! 警報"
                logger.warning(f"! 崗位5警報: 未平倉合約偏低 ({open_interest} < {oi_threshold_recommended})")
            else:
                post5_status = "OK 正常"
            
            post_details['post5'] = {
                'name': '未平倉合約監察',
                'value': open_interest,
                'threshold_recommended': oi_threshold_recommended,
                'threshold_minimum': oi_threshold_minimum,
                'status': post5_status,
                'note': '美股標準：推薦≥500，最低≥100（三不買原則）'
            }
            
            # ========== 崗位6: 成交量監察（三不買原則）==========
            # 美股市場標準：Volume ≥ 100（推薦）
            # 最低標準：Volume ≥ 10（可接受）
            volume_threshold_recommended = 100
            volume_threshold_minimum = 10
            
            if volume < volume_threshold_minimum:
                alerts += 1
                post6_status = "! 嚴重警報"
                logger.warning(f"! 崗位6嚴重警報: 成交量極低 ({volume} < {volume_threshold_minimum}) - 不建議交易（三不買原則）")
            elif volume < volume_threshold_recommended:
                alerts += 1
                post6_status = "! 警報"
                logger.warning(f"! 崗位6警報: 成交量偏低 ({volume} < {volume_threshold_recommended})")
            else:
                post6_status = "OK 正常"
            
            post_details['post6'] = {
                'name': '成交量監察',
                'value': volume,
                'threshold_recommended': volume_threshold_recommended,
                'threshold_minimum': volume_threshold_minimum,
                'status': post6_status,
                'note': '美股標準：推薦≥100，最低≥10（三不買原則）'
            }
            
            # ========== 崗位7: 買賣盤差價監察（三不買原則）==========
            # 計算價差百分比
            if option_premium > 0:
                spread_percentage = (bid_ask_spread / option_premium) * 100
            else:
                spread_percentage = 0.0
            
            # 美股市場標準：價差 < 5%（推薦），< 10%（可接受）
            spread_pct_threshold_recommended = 5.0
            spread_pct_threshold_maximum = 10.0
            
            if spread_percentage > spread_pct_threshold_maximum:
                alerts += 1
                post7_status = "! 嚴重警報"
                logger.warning(f"! 崗位7嚴重警報: 買賣差價過大 ({spread_percentage:.1f}% > {spread_pct_threshold_maximum}%) - 不建議交易（三不買原則）")
            elif spread_percentage > spread_pct_threshold_recommended:
                alerts += 1
                post7_status = "! 警報"
                logger.warning(f"! 崗位7警報: 買賣差價偏大 ({spread_percentage:.1f}% > {spread_pct_threshold_recommended}%)")
            else:
                post7_status = "OK 正常"
            
            post_details['post7'] = {
                'name': '買賣盤差價監察',
                'value': bid_ask_spread,
                'spread_percentage': round(spread_percentage, 2),
                'threshold_recommended': f'{spread_pct_threshold_recommended}%',
                'threshold_maximum': f'{spread_pct_threshold_maximum}%',
                'status': post7_status,
                'note': '美股標準：推薦<5%，最高<10%（三不買原則）'
            }
            
            # ========== 崗位8: ATR波幅監察 ==========
            atr_threshold = stock_price * 0.05  # 5%股價
            if atr > atr_threshold:
                alerts += 1
                post8_status = "! 警報"
                logger.warning(f"! 崗位8警報: ATR波幅過大 ({atr:.2f})")
            else:
                post8_status = "OK 正常"
            post_details['post8'] = {
                'name': 'ATR波幅監察',
                'value': atr,
                'threshold': atr_threshold,
                'status': post8_status
            }
            
            # ========== 崗位9: 派息日期監察 ==========
            post9_status = "OK 正常"
            days_to_dividend = None
            if dividend_date:
                try:
                    div_date = datetime.strptime(dividend_date, '%Y-%m-%d')
                    days_to_dividend = (div_date - datetime.now()).days
                    
                    if 0 <= days_to_dividend <= 7:
                        alerts += 1
                        post9_status = "! 警報"
                        logger.warning(f"! 崗位9警報: {days_to_dividend}天後派息 ({dividend_date})")
                except:
                    pass
            post_details['post9'] = {
                'name': '派息日監察',
                'value': dividend_date if dividend_date else "N/A",
                'threshold': '7天內',
                'status': post9_status,
                'days_remaining': days_to_dividend if days_to_dividend is not None else None
            }
            
            # ========== 崗位10: 業績發布日監察 ==========
            post10_status = "OK 正常"
            days_to_earnings = None
            if earnings_date:
                try:
                    earn_date = datetime.strptime(earnings_date, '%Y-%m-%d')
                    days_to_earnings = (earn_date - datetime.now()).days
                    
                    if 0 <= days_to_earnings <= 7:
                        alerts += 1
                        post10_status = "! 警報"
                        logger.warning(f"! 崗位10警報: {days_to_earnings}天後業績發布 ({earnings_date})")
                except:
                    pass
            post_details['post10'] = {
                'name': '業績公佈監察',
                'value': earnings_date if earnings_date else "N/A",
                'threshold': '7天內',
                'status': post10_status,
                'days_remaining': days_to_earnings if days_to_earnings is not None else None
            }
            
            # ========== 崗位11: 到期日監察（三不買原則+金曹建議）==========
            post11_status = "OK 正常"
            days_to_expiration = None
            expiration_category = "未知"
            theta_warning = ""
            
            if expiration_date:
                try:
                    exp_date = datetime.strptime(expiration_date, '%Y-%m-%d')
                    days_to_expiration = (exp_date - datetime.now()).days
                    
                    # 根據金曹老師的建議分類
                    if days_to_expiration < 7:
                        # 極短期：Theta衰減極快
                        alerts += 1
                        post11_status = "! 嚴重警報"
                        expiration_category = "極短期（<7天）"
                        theta_warning = "Theta衰減極快，時間價值每天損失巨大（三不買原則）"
                        logger.warning(f"! 崗位11嚴重警報: {days_to_expiration}天後到期 - {theta_warning}")
                    
                    elif 7 <= days_to_expiration < 30:
                        # 短期：可接受但需謹慎
                        post11_status = "⚠️ 注意"
                        expiration_category = "短期（7-30天）"
                        theta_warning = "Theta衰減較快，適合短線交易"
                        logger.info(f"  崗位11注意: {days_to_expiration}天後到期 - {theta_warning}")
                    
                    elif 30 <= days_to_expiration <= 90:
                        # 最佳範圍：金曹推薦
                        post11_status = "✓ 最佳範圍"
                        expiration_category = "最佳範圍（30-90天）"
                        theta_warning = "金曹老師推薦的最佳交易窗口"
                        logger.info(f"  崗位11: {days_to_expiration}天後到期 - {theta_warning}")
                    
                    else:  # > 90天
                        # 長期：時間價值過高
                        alerts += 1
                        post11_status = "! 警報"
                        expiration_category = "長期（>90天）"
                        theta_warning = "時間價值過高，買入成本貴（三不買原則）"
                        logger.warning(f"! 崗位11警報: {days_to_expiration}天後到期 - {theta_warning}")
                    
                except:
                    pass
            
            post_details['post11'] = {
                'name': '到期日監察',
                'value': expiration_date if expiration_date else "N/A",
                'days_remaining': days_to_expiration if days_to_expiration is not None else None,
                'category': expiration_category,
                'status': post11_status,
                'theta_warning': theta_warning,
                'optimal_range': '30-90天（金曹老師推薦）',
                'note': '< 7天：極快衰減 | 7-30天：短線 | 30-90天：最佳 | > 90天：時間價值高'
            }
            
            # ========== 崗位12: 市場情緒監察(VIX) ==========
            vix_threshold = 25.0
            if vix > vix_threshold:
                alerts += 1
                post12_status = "! 警報"
                logger.warning(f"! 崗位12警報: VIX指數過高 ({vix:.2f})")
            else:
                post12_status = "OK 正常"
            post_details['post12'] = {
                'name': '市場情緒監察(VIX)',
                'value': vix,
                'threshold': vix_threshold,
                'status': post12_status
            }
            
            # 判斷風險等級
            if alerts >= 4:
                risk_level = "高風險"
            elif alerts >= 2:
                risk_level = "中風險"
            else:
                risk_level = "低風險"
            
            logger.info(f"  監察結果:")
            logger.info(f"    警報數: {alerts}")
            logger.info(f"    風險級別: {risk_level}")
            
            result = MonitoringPostsResult(
                stock_price=stock_price,
                option_premium=option_premium,
                iv=iv,
                delta=delta,
                open_interest=open_interest,
                volume=volume,
                bid_ask_spread=bid_ask_spread,
                atr=atr,
                dividend_date=dividend_date,
                earnings_date=earnings_date,
                expiration_date=expiration_date,
                vix=vix,
                total_alerts=alerts,
                risk_level=risk_level,
                calculation_date=calculation_date,
                # 12個崗位狀態
                post1_stock_price_status=post1_status,
                post2_option_premium_status=post2_status,
                post3_iv_status=post3_status,
                post4_delta_status=post4_status,
                post5_open_interest_status=post5_status,
                post6_volume_status=post6_status,
                post7_bid_ask_spread_status=post7_status,
                post8_atr_status=post8_status,
                post9_dividend_date_status=post9_status,
                post10_earnings_date_status=post10_status,
                post11_expiration_date_status=post11_status,
                post12_vix_status=post12_status,
                post_details=post_details
            )
            
            logger.info(f"  12監察崗位分析完成")
            return result
            
        except Exception as e:
            logger.error(f"x 12監察崗位分析失敗: {e}")
            raise
    
    @staticmethod
    def _validate_inputs(stock_price: float, option_premium: float, iv: float, 
                        delta: float, volume: int, bid_ask_spread: float, atr: float, vix: float) -> bool:
        logger.info("驗證輸入參數...")
        
        params = [stock_price, option_premium, iv, delta, bid_ask_spread, atr, vix]
        if not all(isinstance(x, (int, float)) for x in params):
            return False
        
        if stock_price <= 0 or option_premium <= 0:
            return False
        
        if iv < 0 or iv > 200:
            return False
        
        if delta < 0 or delta > 1:
            return False
        
        logger.info("  輸入參數驗證通過")
        return True

    def check_iv_rank_post(self, iv_rank: float) -> Dict:
        """
        崗位13: IV Rank 歷史判斷標準（美股市場增強）
        
        基於金曹12監察崗位框架，整合美股市場的 IV Rank 分析。
        
        來源: tastylive、CBOE 美股期權市場標準
        
        判斷標準:
        - IV Rank > 70%: 高IV環境，適合賣期權策略
        - IV Rank < 30%: 低IV環境，適合買期權策略
        - IV Rank 30-70%: 中性IV環境，觀望或中性策略
        
        參數:
            iv_rank: IV Rank 百分比 (0-100)，None 表示數據不足
        
        返回:
            Dict: {
                'name': str,
                'value': float or None,
                'threshold': str,
                'status': str,
                'note': str,
                'strategy_suggestion': str,
                'iv_environment': str
            }
        """
        try:
            # 處理缺失數據
            if iv_rank is None:
                logger.info("  崗位13: IV Rank 數據不足")
                return {
                    'name': 'IV Rank 歷史判斷',
                    'value': None,
                    'threshold': '30%-70%',
                    'status': '! 數據不足',
                    'note': '需要252天歷史IV數據計算IV Rank',
                    'strategy_suggestion': '無法提供策略建議',
                    'iv_environment': '未知'
                }
            
            # 確保 IV Rank 在有效範圍內
            iv_rank = max(0.0, min(100.0, float(iv_rank)))
            
            # 金曹理論 + 美股市場標準的 IV Rank 判斷
            if iv_rank > 70:
                # 高IV環境 - 適合做空波動率
                status = '⚠️ 高IV環境'
                strategy = '適合賣期權策略 (Iron Condor, Short Straddle, Credit Spread)'
                note = f'IV Rank {iv_rank:.1f}% > 70% - 隱含波動率處於歷史高位'
                iv_environment = '高IV環境 - 建議做空波動率策略'
                logger.info(f"  崗位13: {status} - IV Rank {iv_rank:.1f}%")
                
            elif iv_rank < 30:
                # 低IV環境 - 適合做多波動率
                status = '⚠️ 低IV環境'
                strategy = '適合買期權策略 (Long Straddle, Debit Spread, Long Options)'
                note = f'IV Rank {iv_rank:.1f}% < 30% - 隱含波動率處於歷史低位'
                iv_environment = '低IV環境 - 建議做多波動率策略'
                logger.info(f"  崗位13: {status} - IV Rank {iv_rank:.1f}%")
                
            else:
                # 中性IV環境
                status = 'OK 中性IV環境'
                strategy = '中性策略或觀望 (Calendar Spread, Butterfly)'
                note = f'IV Rank {iv_rank:.1f}% 在 30%-70% 範圍內 - 正常水平'
                iv_environment = '中性IV環境 - 無明顯優勢'
                logger.info(f"  崗位13: {status} - IV Rank {iv_rank:.1f}%")
            
            return {
                'name': 'IV Rank 歷史判斷',
                'value': round(iv_rank, 2),
                'threshold': '30%-70%',
                'status': status,
                'note': note,
                'strategy_suggestion': strategy,
                'iv_environment': iv_environment
            }
            
        except Exception as e:
            logger.error(f"x 崗位13 IV Rank 判斷失敗: {e}")
            return {
                'name': 'IV Rank 歷史判斷',
                'value': iv_rank if iv_rank is not None else None,
                'threshold': '30%-70%',
                'status': 'x 錯誤',
                'note': f'計算失敗: {e}',
                'strategy_suggestion': '無法提供建議',
                'iv_environment': '未知'
            }