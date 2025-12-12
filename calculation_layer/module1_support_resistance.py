# calculation_layer/module1_support_resistance.py
"""
模塊1: 支持位/阻力位計算 (引伸波幅法) - 修正版
書籍來源: 《期權制勝》第六課 (核心思想)
"""

import logging
import math
from dataclasses import dataclass
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SupportResistanceResult:
    """支持/阻力位計算結果"""
    stock_price: float
    implied_volatility: float
    days_to_expiration: int
    z_score: float
    confidence_level: str
    price_move: float
    support_level: float
    resistance_level: float
    volatility_percentage: float
    calculation_date: str
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        return {
            'stock_price': round(self.stock_price, 2),
            'implied_volatility': round(self.implied_volatility, 2),
            'days_to_expiration': self.days_to_expiration,
            'z_score': round(self.z_score, 4),
            'confidence_level': self.confidence_level,
            'price_move': round(self.price_move, 2),
            'support_level': round(self.support_level, 2),
            'resistance_level': round(self.resistance_level, 2),
            'volatility_percentage': round(self.volatility_percentage, 2),
            'calculation_date': self.calculation_date
        }


class SupportResistanceCalculator:
    """
    支持/阻力位計算器 (IV 區間預測法)
    
    核心公式:
    ─────────────────────────────────────
    Price Move = 股價 × (IV/100) × sqrt(Days/252) × Z值
    支持位 = 股價 - Price Move
    阻力位 = 股價 + Price Move
    
    注: 使用252交易日標準（美股市場標準）
    
    Z值 (信心度):
    - 68% 信心度: Z ≈ 1.0
    - 80% 信心度: Z ≈ 1.28
    - 90% 信心度: Z ≈ 1.645
    ─────────────────────────────────────
    """
    
    # 標準信心度配置 (基於用戶Excel設計)
    CONFIDENCE_LEVELS = {
        # 用戶Excel已有
        '68%': 1.00,     # 1σ - 68.27%信心度
        '80%': 1.28,     # 80%信心度
        '90%': 1.645,    # 90%信心度 (用戶Excel為1.64,使用精確值1.645)
        '95%': 1.96,     # 2σ - 95.45%信心度
        '99%': 2.58,     # 99%信心度
        
        # 可選補充 (用戶可按需啟用)
        '50%': 0.67,     # 中位數
        '75%': 1.15,     # 四分位數
        '85%': 1.44,     # 85%信心度
        '99.7%': 3.00,   # 3σ - 99.73%信心度
    }
    
    # 交易日常量 (美股標準: 252個交易日/年)
    TRADING_DAYS_PER_YEAR = 252
    
    def __init__(self):
        """初始化計算器"""
        logger.info("* 支持/阻力位計算器已初始化")
    
    def calculate(self, 
                  stock_price: float, 
                  implied_volatility: float,
                  days_to_expiration: int,
                  z_score: float = 1.0,
                  calculation_date: str = None,
                  is_calendar_days: bool = True) -> SupportResistanceResult:
        """
        計算支持位和阻力位
        
        參數:
            stock_price: 當前股票價格 (美元)
            implied_volatility: 隱含波動率 (百分比 0-100)
            days_to_expiration: 到期天數
            z_score: 信心度 Z 值 (1.0, 1.28, 1.645等)
            calculation_date: 計算日期 (格式 YYYY-MM-DD)
            is_calendar_days: 是否為日曆日 (默認 True)
                - True: 輸入為日曆日，內部自動轉換為交易日 (× 252/365)
                - False: 輸入已經是交易日，直接使用
        
        返回:
            SupportResistanceResult: 包含完整結果的對象
        
        注意:
            時間因子計算使用交易日標準 (252天/年)
            如果輸入日曆日，會自動轉換: trading_days = calendar_days × (252/365)
        """
        try:
            logger.info(f"開始計算支持/阻力位...")
            logger.info(
                "  股價: $%.2f, IV: %.2f%%, 天數: %d, Z值: %.4f",
                stock_price,
                implied_volatility,
                days_to_expiration,
                z_score
            )
            
            # 第1步: 輸入驗證
            if not self._validate_inputs(stock_price, implied_volatility, days_to_expiration, z_score):
                raise ValueError("輸入參數無效")
            
            # 第2步: 獲取計算日期
            if calculation_date is None:
                calculation_date = datetime.now().strftime('%Y-%m-%d')
            
            # 第3步: 轉換IV為小數形式
            iv_decimal = implied_volatility / 100
            
            # 第4步: 計算時間因子 (Time Factor) - 使用交易日標準
            # 如果輸入是日曆日，先轉換為交易日
            if is_calendar_days:
                trading_days = days_to_expiration * (self.TRADING_DAYS_PER_YEAR / 365.0)
                logger.info(f"    日曆日轉交易日: {days_to_expiration} → {trading_days:.1f}")
            else:
                trading_days = days_to_expiration
            
            time_factor = math.sqrt(trading_days / self.TRADING_DAYS_PER_YEAR)
            
            # 第5步: 計算價格波動幅度
            price_move = stock_price * iv_decimal * time_factor * z_score
            
            logger.info("  計算結果:")
            logger.info("    時間因子: %.4f", time_factor)
            logger.info("    波動幅度: $%.2f", price_move)
            
            # 第6步: 計算支持位和阻力位
            support_level = stock_price - price_move
            resistance_level = stock_price + price_move
            
            # 第7步: 計算波幅百分比
            volatility_percentage = (price_move / stock_price) * 100
            
            # 第8步: 確定信心度描述
            if abs(z_score - 1.0) < 0.01:
                confidence_level = "68% (1.0 σ)"
            elif abs(z_score - 1.28) < 0.01:
                confidence_level = "80% (1.28 σ)"
            elif abs(z_score - 1.645) < 0.01:
                confidence_level = "90% (1.645 σ)"
            elif abs(z_score - 2.0) < 0.01:
                confidence_level = "95% (2.0 σ)"
            else:
                confidence_level = f"{z_score} σ"
            
            logger.info("    支持位: $%.2f", support_level)
            logger.info("    阻力位: $%.2f", resistance_level)
            logger.info("    信心度: %s", confidence_level)
            
            # 第9步: 建立結果對象
            result = SupportResistanceResult(
                stock_price=stock_price,
                implied_volatility=implied_volatility,
                days_to_expiration=days_to_expiration,
                z_score=z_score,
                confidence_level=confidence_level,
                price_move=price_move,
                support_level=support_level,
                resistance_level=resistance_level,
                volatility_percentage=volatility_percentage,
                calculation_date=calculation_date
            )
            
            logger.info("  支持/阻力位計算完成")
            
            return result
            
        except Exception as e:
            logger.error(f"✗ 支持/阻力位計算失敗: {e}")
            raise
    
    def calculate_multi_confidence(
        self,
        stock_price: float,
        implied_volatility: float,
        days_to_expiration: int,
        confidence_levels: Optional[List[str]] = None,
        calculation_date: Optional[str] = None
    ) -> Dict:
        """
        計算多個信心度的IV區間
        
        參數:
            stock_price: 當前股價
            implied_volatility: 隱含波動率 (百分比, 0-100)
            days_to_expiration: 到期天數 (交易日)
            confidence_levels: 信心度列表 (默認: ['68%', '80%', '90%', '95%', '99%'])
            calculation_date: 計算日期
        
        返回:
            dict: {
                'stock_price': 180.50,
                'implied_volatility': 22.0,
                'days_to_expiration': 37,
                'time_factor': 0.3848,
                'results': {
                    '68%': {
                        'z_score': 1.00,
                        'price_move': 8.50,
                        'support': 172.00,
                        'resistance': 189.00,
                        'move_percentage': 4.7
                    },
                    '80%': {...},
                    '90%': {...},
                    '95%': {...},
                    '99%': {...}
                },
                'calculation_date': '2025-11-14'
            }
        
        示例:
            >>> calc = SupportResistanceCalculator()
            >>> results = calc.calculate_multi_confidence(
            ...     stock_price=180.50,
            ...     implied_volatility=22.0,
            ...     days_to_expiration=37,
            ...     confidence_levels=['68%', '80%', '90%', '95%', '99%']
            ... )
            >>> print(results['results']['90%'])
            {'z_score': 1.645, 'price_move': 13.99, 'support': 166.51, ...}
        """
        try:
            # 默認使用用戶Excel的5個信心度
            if confidence_levels is None:
                confidence_levels = ['68%', '80%', '90%', '95%', '99%']
            
            # 驗證輸入
            if stock_price <= 0:
                raise ValueError(f"股價必須大於0: {stock_price}")
            if implied_volatility <= 0 or implied_volatility > 200:
                raise ValueError(f"IV必須在0-200之間: {implied_volatility}")
            if days_to_expiration <= 0:
                raise ValueError(f"到期天數必須大於0: {days_to_expiration}")
            
            # 轉換IV為小數
            iv_decimal = implied_volatility / 100.0
            
            # 計算時間因子 (使用交易日標準)
            time_factor = math.sqrt(days_to_expiration / self.TRADING_DAYS_PER_YEAR)
            
            logger.info(f"開始多信心度計算: 股價=${stock_price}, IV={implied_volatility}%, "
                        f"天數={days_to_expiration}, 時間因子={time_factor:.4f}")
            
            # 計算每個信心度的結果
            results = {}
            for conf_level in confidence_levels:
                # 驗證信心度是否在配置中
                if conf_level not in self.CONFIDENCE_LEVELS:
                    logger.warning(f"⚠️ 未知信心度: {conf_level}, 跳過")
                    continue
                
                z_score = self.CONFIDENCE_LEVELS[conf_level]
                
                # 計算價格波動
                # Formula: price_move = S × σ × √(T) × Z
                price_move = stock_price * iv_decimal * time_factor * z_score
                
                # 計算支持/阻力位
                support = stock_price - price_move
                resistance = stock_price + price_move
                
                # 計算百分比波動
                move_percentage = (price_move / stock_price) * 100
                
                # 保存結果
                results[conf_level] = {
                    'z_score': round(z_score, 4),
                    'price_move': round(price_move, 2),
                    'support': round(support, 2),
                    'resistance': round(resistance, 2),
                    'move_percentage': round(move_percentage, 2)
                }
                
                logger.debug(f"  {conf_level}: 支持${support:.2f} - 阻力${resistance:.2f} "
                            f"(波動±{move_percentage:.1f}%)")
            
            # 生成計算日期
            calc_date = calculation_date or datetime.now().strftime('%Y-%m-%d')
            
            logger.info(f"  多信心度計算完成: {len(results)}個信心度")
            
            return {
                'stock_price': stock_price,
                'implied_volatility': implied_volatility,
                'days_to_expiration': days_to_expiration,
                'time_factor': round(time_factor, 4),
                'results': results,
                'calculation_date': calc_date
            }
            
        except Exception as e:
            logger.error(f"✗ 多信心度計算失敗: {e}")
            raise
    
    @staticmethod
    def _validate_inputs(stock_price: float, 
                         implied_volatility: float,
                         days_to_expiration: int,
                         z_score: float) -> bool:
        """驗證輸入參數"""
        logger.info("驗證輸入參數...")
        
        if not all(isinstance(x, (int, float)) for x in [stock_price, implied_volatility, z_score]):
            logger.error("✗ 股價、IV、Z值必須是數字")
            return False
        
        if not isinstance(days_to_expiration, int) or days_to_expiration <= 0:
            logger.error("✗ 到期天數必須是正整數")
            return False
        
        if stock_price <= 0 or implied_volatility <= 0 or z_score <= 0:
            logger.error("✗ 股價、IV、Z值必須大於0")
            return False
        
        if implied_volatility > 500:
            logger.error("✗ IV超過合理範圍: %.2f%%", implied_volatility)
            return False
        
        if z_score > 5:
            logger.error("✗ Z值過大，請確認輸入: %.4f", z_score)
            return False
        
        logger.info("  輸入參數驗證通過")
        return True


# 使用示例和測試
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    calculator = SupportResistanceCalculator()
    
    print("\n" + "=" * 70)
    print("模塊1: 支持位/阻力位計算 (引伸波幅法)")
    print("=" * 70)
    
    # 例子1: AAPL股價 $180, IV 22%
    print("\n【例子1】AAPL")
    print("-" * 70)
    
    result1 = calculator.calculate(
        stock_price=180.50,
        implied_volatility=22.0,
        days_to_expiration=30,
        z_score=1.0
    )
    
    print(f"\n計算結果:")
    print(f"  股價: ${result1.stock_price:.2f}")
    print(f"  隱含波動率: {result1.implied_volatility:.2f}%")
    print(f"  到期天數: {result1.days_to_expiration} 天")
    print(f"  Z值: {result1.z_score:.2f} ({result1.confidence_level})")
    print(f"  波動幅度: ${result1.price_move:.2f}")
    print(f"  支持位: ${result1.support_level:.2f}")
    print(f"  阻力位: ${result1.resistance_level:.2f}")
    print(f"  波幅百分比: {result1.volatility_percentage:.2f}%")
    print(f"  計算日期: {result1.calculation_date}")
    
    # 例子2: 高波動率
    print("\n【例子2】高波動率場景 (IV 35%)")
    print("-" * 70)
    
    result2 = calculator.calculate(
        stock_price=100.0,
        implied_volatility=35.0,
        days_to_expiration=45,
        z_score=1.28
    )
    
    print(f"\n計算結果:")
    print(f"  股價: ${result2.stock_price:.2f}")
    print(f"  到期天數: {result2.days_to_expiration} 天")
    print(f"  信心度: {result2.confidence_level}")
    print(f"  支持位: ${result2.support_level:.2f}")
    print(f"  阻力位: ${result2.resistance_level:.2f}")
    print(f"  波幅範圍: ${result2.support_level:.2f} ~ ${result2.resistance_level:.2f}")
    
    # 例子3: 低波動率
    print("\n【例子3】低波動率場景 (IV 10%)")
    print("-" * 70)
    
    result3 = calculator.calculate(
        stock_price=100.0,
        implied_volatility=10.0,
        days_to_expiration=14,
        z_score=1.645
    )
    
    print(f"\n計算結果:")
    print(f"  股價: ${result3.stock_price:.2f}")
    print(f"  信心度: {result3.confidence_level}")
    print(f"  支持位: ${result3.support_level:.2f}")
    print(f"  阻力位: ${result3.resistance_level:.2f}")
    print(f"  波幅範圍: ${result3.support_level:.2f} ~ ${result3.resistance_level:.2f}")
    
    print("\n" + "=" * 70)
    print("注: 波幅範圍內80%概率期權不會執行 (書籍理論)")
    print("=" * 70)
