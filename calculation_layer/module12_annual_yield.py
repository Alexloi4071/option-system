@dataclass
class AnnualYieldResult:
    """年息收益率計算結果"""
    cost_basis: float
    annual_dividend: float
    annual_option_income: float
    total_annual_income: float
    annual_yield: float
    dividend_yield: float
    option_yield: float
    calculation_date: str
    
    def to_dict(self) -> Dict:
        return {
            'cost_basis': round(self.cost_basis, 2),
            'annual_dividend': round(self.annual_dividend, 2),
            'annual_option_income': round(self.annual_option_income, 2),
            'total_annual_income': round(self.total_annual_income, 2),
            'annual_yield': round(self.annual_yield, 2),
            'dividend_yield': round(self.dividend_yield, 2),
            'option_yield': round(self.option_yield, 2),
            'calculation_date': self.calculation_date
        }


class AnnualYieldCalculator:
    """
    年息收益率計算器
    
    書籍來源: 《期權制勝》第十二課
    
    公式 (100%書籍):
    ────────────────────────────────
    年息收益率 = [(年派息 + 年期權金收入) / 持倉成本] × 100%
    
    派息收益率 = 年派息 / 持倉成本 × 100%
    期權收益率 = 年期權金收入 / 持倉成本 × 100%
    
    理論:
    持有正股+沽出Call的組合稱為"覆蓋性看漲期權"
    年收益率包括派息收益和期權收益
    ────────────────────────────────
    """
    
    def __init__(self):
        logger.info("✓ 年息收益率計算器已初始化")
    
    def calculate(self,
                  cost_basis: float,
                  annual_dividend: float,
                  annual_option_income: float,
                  calculation_date: str = None) -> AnnualYieldResult:
        try:
            logger.info(f"開始計算年息收益率...")
            logger.info(f"  持倉成本: ${cost_basis:.2f}")
            logger.info(f"  年派息: ${annual_dividend:.2f}")
            logger.info(f"  年期權金收入: ${annual_option_income:.2f}")
            
            if not self._validate_inputs(cost_basis, annual_dividend, annual_option_income):
                raise ValueError("輸入參數無效")
            
            if calculation_date is None:
                calculation_date = datetime.now().strftime('%Y-%m-%d')
            
            # 計算總年收入
            total_annual_income = annual_dividend + annual_option_income
            
            # 計算各項收益率
            annual_yield = (total_annual_income / cost_basis) * 100 if cost_basis > 0 else 0
            dividend_yield = (annual_dividend / cost_basis) * 100 if cost_basis > 0 else 0
            option_yield = (annual_option_income / cost_basis) * 100 if cost_basis > 0 else 0
            
            logger.info(f"  計算結果:")
            logger.info(f"    年收入: ${total_annual_income:.2f}")
            logger.info(f"    年收益率: {annual_yield:.2f}%")
            logger.info(f"    派息收益率: {dividend_yield:.2f}%")
            logger.info(f"    期權收益率: {option_yield:.2f}%")
            
            result = AnnualYieldResult(
                cost_basis=cost_basis,
                annual_dividend=annual_dividend,
                annual_option_income=annual_option_income,
                total_annual_income=total_annual_income,
                annual_yield=annual_yield,
                dividend_yield=dividend_yield,
                option_yield=option_yield,
                calculation_date=calculation_date
            )
            
            logger.info(f"✓ 年息收益率計算完成")
            return result
            
        except Exception as e:
            logger.error(f"✗ 年息收益率計算失敗: {e}")
            raise
    
    @staticmethod
    def _validate_inputs(cost_basis: float, annual_dividend: float, annual_option_income: float) -> bool:
        logger.info("驗證輸入參數...")
        
        if not all(isinstance(x, (int, float)) for x in [cost_basis, annual_dividend, annual_option_income]):
            return False
        
        if cost_basis <= 0:
            logger.error("✗ 持倉成本必須大於0")
            return False
        
        if annual_dividend < 0 or annual_option_income < 0:
            logger.error("✗ 收入不能為負")
            return False
        
        logger.info("✓ 輸入參數驗證通過")
        return True