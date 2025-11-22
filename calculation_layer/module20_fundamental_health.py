# calculation_layer/module20_fundamental_health.py
"""
模塊20: 基本面健康檢查
數據來源: Finviz
"""

import logging
from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class FundamentalHealthResult:
    """基本面健康檢查結果"""
    ticker: str
    health_score: int
    max_score: int
    grade: str
    warnings: List[str]
    strengths: List[str]
    calculation_date: str
    
    # 詳細指標
    peg_ratio: float
    roe: float
    profit_margin: float
    debt_eq: float
    inst_own: float
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        return {
            'ticker': self.ticker,
            'health_score': self.health_score,
            'max_score': self.max_score,
            'grade': self.grade,
            'score_percentage': round((self.health_score / self.max_score) * 100, 1),
            'warnings': self.warnings,
            'strengths': self.strengths,
            'calculation_date': self.calculation_date,
            'details': {
                'peg_ratio': round(self.peg_ratio, 2) if self.peg_ratio else None,
                'roe': round(self.roe, 2) if self.roe else None,
                'profit_margin': round(self.profit_margin, 2) if self.profit_margin else None,
                'debt_eq': round(self.debt_eq, 2) if self.debt_eq else None,
                'institutional_ownership': round(self.inst_own, 2) if self.inst_own else None
            }
        }


class FundamentalHealthCalculator:
    """
    基本面健康檢查計算器
    
    數據來源: Finviz
    
    評分標準 (總分100分):
    ────────────────────────────────
    1. 估值健康 (20分)
       - PEG < 1.0: 20分 (低估)
       - PEG 1.0-2.0: 15分 (合理)
       - PEG 2.0-3.0: 10分 (略高)
       - PEG > 3.0: 5分 (高估)
    
    2. 盈利能力 (20分)
       - ROE > 20%: 20分 (優秀)
       - ROE 15-20%: 15分 (良好)
       - ROE 10-15%: 10分 (一般)
       - ROE < 10%: 5分 (偏低)
    
    3. 利潤率 (20分)
       - Profit Margin > 20%: 20分 (優秀)
       - Profit Margin 10-20%: 15分 (良好)
       - Profit Margin 5-10%: 10分 (一般)
       - Profit Margin < 5%: 5分 (偏低)
    
    4. 財務健康 (20分)
       - Debt/Equity < 0.5: 20分 (優秀)
       - Debt/Equity 0.5-1.0: 15分 (良好)
       - Debt/Equity 1.0-2.0: 10分 (一般)
       - Debt/Equity > 2.0: 5分 (高負債)
    
    5. 市場認可度 (20分)
       - 機構持股 > 60%: 20分 (高認可)
       - 機構持股 40-60%: 15分 (正常)
       - 機構持股 20-40%: 10分 (偏低)
       - 機構持股 < 20%: 5分 (低認可)
    
    等級劃分:
    - A (80-100分): 優秀
    - B (60-79分): 良好
    - C (40-59分): 一般
    - D (0-39分): 需警惕
    ────────────────────────────────
    """
    
    def __init__(self):
        """初始化計算器"""
        logger.info("✓ 基本面健康檢查計算器已初始化")
    
    def calculate(self,
                  ticker: str,
                  peg_ratio: float = None,
                  roe: float = None,
                  profit_margin: float = None,
                  debt_eq: float = None,
                  inst_own: float = None,
                  calculation_date: str = None) -> FundamentalHealthResult:
        """
        計算基本面健康分數
        
        參數:
            ticker: 股票代碼
            peg_ratio: PEG 比率
            roe: 股本回報率 (%)
            profit_margin: 淨利潤率 (%)
            debt_eq: 負債/股本比
            inst_own: 機構持股 (%)
            calculation_date: 計算日期
        
        返回:
            FundamentalHealthResult: 完整健康檢查結果
        """
        try:
            logger.info(f"開始基本面健康檢查: {ticker}")
            
            if calculation_date is None:
                calculation_date = datetime.now().strftime('%Y-%m-%d')
            
            health_score = 0
            max_score = 100
            warnings = []
            strengths = []
            
            # 1. 估值健康 (20分)
            if peg_ratio is not None:
                if peg_ratio < 1.0:
                    health_score += 20
                    strengths.append(f"估值低估（PEG {peg_ratio:.2f} < 1）")
                elif peg_ratio < 2.0:
                    health_score += 15
                    strengths.append(f"估值合理（PEG {peg_ratio:.2f}）")
                elif peg_ratio < 3.0:
                    health_score += 10
                    warnings.append(f"估值略高（PEG {peg_ratio:.2f}）")
                else:
                    health_score += 5
                    warnings.append(f"估值過高（PEG {peg_ratio:.2f} > 3）")
            else:
                logger.warning("⚠ 缺少 PEG 數據")
            
            # 2. 盈利能力 (20分)
            if roe is not None:
                if roe > 20:
                    health_score += 20
                    strengths.append(f"ROE 優秀（{roe:.1f}% > 20%）")
                elif roe > 15:
                    health_score += 15
                    strengths.append(f"ROE 良好（{roe:.1f}%）")
                elif roe > 10:
                    health_score += 10
                else:
                    health_score += 5
                    warnings.append(f"ROE 偏低（{roe:.1f}% < 10%）")
            else:
                logger.warning("⚠ 缺少 ROE 數據")
            
            # 3. 利潤率 (20分)
            if profit_margin is not None:
                if profit_margin > 20:
                    health_score += 20
                    strengths.append(f"利潤率優秀（{profit_margin:.1f}% > 20%）")
                elif profit_margin > 10:
                    health_score += 15
                    strengths.append(f"利潤率良好（{profit_margin:.1f}%）")
                elif profit_margin > 5:
                    health_score += 10
                else:
                    health_score += 5
                    warnings.append(f"利潤率偏低（{profit_margin:.1f}% < 5%）")
            else:
                logger.warning("⚠ 缺少利潤率數據")
            
            # 4. 財務健康 (20分)
            if debt_eq is not None:
                if debt_eq < 0.5:
                    health_score += 20
                    strengths.append(f"財務健康優秀（Debt/Eq {debt_eq:.2f} < 0.5）")
                elif debt_eq < 1.0:
                    health_score += 15
                    strengths.append(f"財務健康良好（Debt/Eq {debt_eq:.2f}）")
                elif debt_eq < 2.0:
                    health_score += 10
                else:
                    health_score += 5
                    warnings.append(f"負債過高（Debt/Eq {debt_eq:.2f} > 2）")
            else:
                logger.warning("⚠ 缺少負債數據")
            
            # 5. 市場認可度 (20分)
            if inst_own is not None:
                if inst_own > 60:
                    health_score += 20
                    strengths.append(f"機構高度認可（{inst_own:.1f}% > 60%）")
                elif inst_own > 40:
                    health_score += 15
                    strengths.append(f"機構持股正常（{inst_own:.1f}%）")
                elif inst_own > 20:
                    health_score += 10
                else:
                    health_score += 5
                    warnings.append(f"機構持股偏低（{inst_own:.1f}% < 20%）")
            else:
                logger.warning("⚠ 缺少機構持股數據")
            
            # 判斷等級
            if health_score >= 80:
                grade = "A - 優秀"
            elif health_score >= 60:
                grade = "B - 良好"
            elif health_score >= 40:
                grade = "C - 一般"
            else:
                grade = "D - 需警惕"
            
            logger.info(f"  健康分數: {health_score}/{max_score} ({grade})")
            logger.info(f"  優勢: {len(strengths)} 項")
            logger.info(f"  警告: {len(warnings)} 項")
            
            result = FundamentalHealthResult(
                ticker=ticker,
                health_score=health_score,
                max_score=max_score,
                grade=grade,
                warnings=warnings,
                strengths=strengths,
                calculation_date=calculation_date,
                peg_ratio=peg_ratio,
                roe=roe,
                profit_margin=profit_margin,
                debt_eq=debt_eq,
                inst_own=inst_own
            )
            
            logger.info(f"✓ 基本面健康檢查完成: {ticker}")
            return result
            
        except Exception as e:
            logger.error(f"✗ 基本面健康檢查失敗: {e}")
            raise


# 使用示例
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    calculator = FundamentalHealthCalculator()
    
    print("\n" + "=" * 70)
    print("模塊20: 基本面健康檢查")
    print("=" * 70)
    
    # 例子1: AAPL (優秀公司)
    print("\n【例子1】AAPL - 優秀公司")
    print("-" * 70)
    
    result1 = calculator.calculate(
        ticker='AAPL',
        peg_ratio=3.60,
        roe=147.0,
        profit_margin=25.3,
        debt_eq=1.50,
        inst_own=60.5
    )
    
    print(f"\n健康檢查結果:")
    print(f"  股票: {result1.ticker}")
    print(f"  健康分數: {result1.health_score}/{result1.max_score}")
    print(f"  等級: {result1.grade}")
    print(f"\n優勢:")
    for strength in result1.strengths:
        print(f"    - {strength}")
    print(f"\n警告:")
    for warning in result1.warnings:
        print(f"    ! {warning}")
    
    # 例子2: 高負債公司
    print("\n【例子2】高負債公司")
    print("-" * 70)
    
    result2 = calculator.calculate(
        ticker='XYZ',
        peg_ratio=4.5,
        roe=8.0,
        profit_margin=4.0,
        debt_eq=3.0,
        inst_own=15.0
    )
    
    print(f"\n健康檢查結果:")
    print(f"  健康分數: {result2.health_score}/{result2.max_score}")
    print(f"  等級: {result2.grade}")
    print(f"  警告數: {len(result2.warnings)}")
    
    print("\n" + "=" * 70)
