# calculation_layer/module5_rate_pe_relation.py
"""
模塊5: 利率與PE關係 (Rate-PE Relationship)
書籍來源: 《期權制勝》第十課
"""

import logging
from dataclasses import dataclass
from typing import Dict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class RatePERelationResult:
    """利率與PE關係計算結果"""
    long_term_rate: float
    reasonable_pe: float
    current_pe: float
    pe_difference: float
    valuation: str
    rate_change_impact: str
    calculation_date: str
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        return {
            'long_term_rate': round(self.long_term_rate, 4),
            'reasonable_pe': round(self.reasonable_pe, 2),
            'current_pe': round(self.current_pe, 2),
            'pe_difference': round(self.pe_difference, 2),
            'valuation': self.valuation,
            'rate_change_impact': self.rate_change_impact,
            'calculation_date': self.calculation_date
        }


class RatePERelationCalculator:
    """
    利率與PE關係計算器
    
    書籍來源: 《期權制勝》第十課（核心思想）
    市場標準: 美國市場行業 PE/PEG 基準
    
    核心思想 (來自書籍):
    ────────────────────────────────
    合理PE = 100 / 長期債息
    
    原理:
    長期債息是無風險收益率的代表
    PE倍數與無風險利率呈反向關係
    當利率上升時，PE應該下降
    當利率下降時，PE應該上升
    ────────────────────────────────
    
    美國市場行業 PE 基準 (2024-2025):
    ────────────────────────────────
    科技股 (Technology):        25-40
    通訊服務 (Communication):   15-25
    消費品 (Consumer):          20-30
    醫療保健 (Healthcare):      20-30
    金融 (Financials):          10-15
    工業 (Industrials):         15-25
    能源 (Energy):              10-20
    公用事業 (Utilities):       15-20
    房地產 (Real Estate):       20-30
    材料 (Materials):           12-18
    ────────────────────────────────
    
    PEG 評估標準 (美國市場):
    ────────────────────────────────
    PEG < 1.0:   估值吸引（增長支撐高 PE）
    PEG 1.0-1.5: 估值合理
    PEG 1.5-2.0: 估值略高
    PEG > 2.0:   估值偏高
    ────────────────────────────────
    """
    
    # 美國市場行業 PE 範圍（2024-2025 標準）
    US_SECTOR_PE_RANGES = {
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
        'Unknown': (15, 25)  # 默認範圍
    }
    
    def __init__(self):
        """初始化計算器"""
        logger.info("* 利率與PE關係計算器已初始化（美國市場標準）")
    
    def calculate(self,
                  long_term_rate: float,
                  current_pe: float,
                  sector: str = None,
                  calculation_date: str = None) -> RatePERelationResult:
        """
        計算合理PE和估值
        
        參數:
            long_term_rate: 長期債息 (百分比 0-20)
            current_pe: 當前PE倍數
            sector: 行業類別 (可選，用於行業PE範圍判斷)
                    可選值: Technology, Communication Services, Consumer Discretionary,
                           Consumer Staples, Healthcare, Financials, Industrials,
                           Energy, Utilities, Real Estate, Materials
            calculation_date: 計算日期
        
        返回:
            RatePERelationResult: 完整計算結果
        """
        try:
            logger.info(f"開始計算利率與PE關係...")
            logger.info(f"  長期債息: {long_term_rate:.2f}%")
            logger.info(f"  當前PE: {current_pe:.2f}倍")
            
            # 驗證輸入
            if not self._validate_inputs(long_term_rate, current_pe):
                raise ValueError("輸入參數無效")
            
            if calculation_date is None:
                calculation_date = datetime.now().strftime('%Y-%m-%d')
            
            # 第1步: 轉換利率為小數
            rate_decimal = long_term_rate / 100
            
            # 第2步: 計算合理PE
            # 公式: 合理PE = 100 / 長期債息
            reasonable_pe = 100 / long_term_rate if long_term_rate > 0 else 0
            
            logger.info(f"  計算結果:")
            logger.info(f"    利率小數: {rate_decimal:.4f}")
            logger.info(f"    合理PE: {reasonable_pe:.2f}倍")
            
            # 第3步: 計算PE差異
            pe_difference = current_pe - reasonable_pe
            
            # 第4步: 確定估值（基於利率推算的基準 PE）
            # 注意：這是基於利率的理論 PE，不考慮行業和增長率
            if pe_difference > 2:
                valuation = "高於利率基準 (>2倍)"
            elif pe_difference > 1:
                valuation = "略高於利率基準 (1-2倍)"
            elif pe_difference > -1:
                valuation = "符合利率基準 (±1倍)"
            elif pe_difference > -2:
                valuation = "略低於利率基準 (-2至-1倍)"
            else:
                valuation = "低於利率基準 (<-2倍)"
            
            # 第4.5步: 如果提供了行業，進行行業PE範圍判斷
            sector_analysis = None
            if sector:
                sector_analysis = self._analyze_sector_pe(current_pe, sector)
                if sector_analysis:
                    valuation = f"{valuation}; {sector_analysis}"
                    logger.info(f"    行業分析: {sector_analysis}")
            
            # 第5步: 分析利率變化影響
            rate_change_impact = self._analyze_rate_impact(long_term_rate)
            
            logger.info(f"    PE差異: {pe_difference:.2f}倍")
            logger.info(f"    估值: {valuation}")
            logger.info(f"    利率影響: {rate_change_impact}")
            
            result = RatePERelationResult(
                long_term_rate=long_term_rate,
                reasonable_pe=reasonable_pe,
                current_pe=current_pe,
                pe_difference=pe_difference,
                valuation=valuation,
                rate_change_impact=rate_change_impact,
                calculation_date=calculation_date
            )
            
            logger.info(f"* 利率與PE關係計算完成")
            return result
            
        except Exception as e:
            logger.error(f"x 利率與PE關係計算失敗: {e}")
            raise
    
    @staticmethod
    def _analyze_rate_impact(long_term_rate: float) -> str:
        """分析利率變化的影響"""
        if long_term_rate < 2:
            return "利率極低，PE應明顯上升"
        elif long_term_rate < 4:
            return "利率較低，PE應該上升"
        elif long_term_rate < 6:
            return "利率正常，PE處於合理水平"
        elif long_term_rate < 8:
            return "利率上升，PE應該下降"
        else:
            return "利率較高，PE應明顯下降"
    
    def _analyze_sector_pe(self, current_pe: float, sector: str) -> str:
        """
        分析當前PE是否在行業合理範圍內
        
        參數:
            current_pe: 當前PE倍數
            sector: 行業類別
        
        返回:
            str: 行業PE分析結果
        """
        # 獲取行業PE範圍
        sector_range = self.US_SECTOR_PE_RANGES.get(sector)
        
        if sector_range is None:
            # 嘗試模糊匹配
            sector_lower = sector.lower()
            for key in self.US_SECTOR_PE_RANGES:
                if sector_lower in key.lower() or key.lower() in sector_lower:
                    sector_range = self.US_SECTOR_PE_RANGES[key]
                    sector = key  # 使用標準名稱
                    break
        
        if sector_range is None:
            sector_range = self.US_SECTOR_PE_RANGES['Unknown']
            logger.warning(f"⚠️ 未知行業 '{sector}'，使用默認PE範圍 {sector_range}")
        
        sector_min, sector_max = sector_range
        
        if current_pe > sector_max:
            return f"高於{sector}行業範圍 (>{sector_max}倍，當前{current_pe:.1f}倍)"
        elif current_pe < sector_min:
            return f"低於{sector}行業範圍 (<{sector_min}倍，當前{current_pe:.1f}倍)"
        else:
            return f"符合{sector}行業範圍 ({sector_min}-{sector_max}倍)"
    
    @staticmethod
    def _validate_inputs(long_term_rate: float, current_pe: float) -> bool:
        """驗證輸入參數"""
        logger.info("驗證輸入參數...")
        
        if not isinstance(long_term_rate, (int, float)):
            logger.error(f"x 長期債息必須是數字")
            return False
        
        if long_term_rate <= 0 or long_term_rate > 20:
            logger.error(f"x 長期債息必須在0-20%之間")
            return False
        
        if not isinstance(current_pe, (int, float)):
            logger.error(f"x 當前PE必須是數字")
            return False
        
        if current_pe <= 0:
            logger.error(f"x 當前PE必須大於0")
            return False
        
        logger.info("* 輸入參數驗證通過")
        return True


# 使用示例
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    calculator = RatePERelationCalculator()
    
    print("\n" + "=" * 70)
    print("模塊5: 利率與PE關係")
    print("=" * 70)
    
    # 例子1: 利率4%
    print("\n【例子1】利率4%（低利率環境）")
    print("-" * 70)
    
    result1 = calculator.calculate(
        long_term_rate=4.0,
        current_pe=25.0
    )
    
    print(f"\n計算結果:")
    print(f"  長期債息: {result1.long_term_rate:.2f}%")
    print(f"  合理PE: {result1.reasonable_pe:.2f}倍")
    print(f"  當前PE: {result1.current_pe:.2f}倍")
    print(f"  PE差異: {result1.pe_difference:.2f}倍")
    print(f"  估值: {result1.valuation}")
    print(f"  利率影響: {result1.rate_change_impact}")
    
    # 例子2: 利率6%
    print("\n【例子2】利率6%（正常利率環境）")
    print("-" * 70)
    
    result2 = calculator.calculate(
        long_term_rate=6.0,
        current_pe=16.0
    )
    
    print(f"\n計算結果:")
    print(f"  長期債息: {result2.long_term_rate:.2f}%")
    print(f"  合理PE: {result2.reasonable_pe:.2f}倍")
    print(f"  當前PE: {result2.current_pe:.2f}倍")
    print(f"  估值: {result2.valuation}")
    
    # 例子3: 利率10%
    print("\n【例子3】利率10%（高利率環境）")
    print("-" * 70)
    
    result3 = calculator.calculate(
        long_term_rate=10.0,
        current_pe=8.0
    )
    
    print(f"\n計算結果:")
    print(f"  長期債息: {result3.long_term_rate:.2f}%")
    print(f"  合理PE: {result3.reasonable_pe:.2f}倍")
    print(f"  當前PE: {result3.current_pe:.2f}倍")
    print(f"  估值: {result3.valuation}")
    
    # 例子4: 帶行業分析
    print("\n【例子4】科技股行業分析")
    print("-" * 70)
    
    result4 = calculator.calculate(
        long_term_rate=4.5,
        current_pe=35.0,
        sector='Technology'
    )
    
    print(f"\n計算結果:")
    print(f"  長期債息: {result4.long_term_rate:.2f}%")
    print(f"  合理PE (利率基準): {result4.reasonable_pe:.2f}倍")
    print(f"  當前PE: {result4.current_pe:.2f}倍")
    print(f"  估值: {result4.valuation}")
    
    # 例子5: 金融股行業分析
    print("\n【例子5】金融股行業分析")
    print("-" * 70)
    
    result5 = calculator.calculate(
        long_term_rate=4.5,
        current_pe=12.0,
        sector='Financials'
    )
    
    print(f"\n計算結果:")
    print(f"  當前PE: {result5.current_pe:.2f}倍")
    print(f"  估值: {result5.valuation}")
    
    print("\n" + "=" * 70)
    print("注: PE與利率呈反向關係 (書籍理論)")
    print("    行業PE範圍提供額外參考 (美國市場2024-2025標準)")
    print("=" * 70)
