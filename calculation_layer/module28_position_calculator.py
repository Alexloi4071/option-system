"""
Module 28: 資金倉位計算器
根據總資金計算期權倉位大小和風險控制

功能：
1. 根據總資金計算單筆最大投入
2. 計算可買期權張數
3. 最大虧損金額計算
4. 風險比例建議
5. 多幣種支持 (HKD/USD)
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class PositionCalculator:
    """資金倉位計算器"""
    
    # 匯率（可配置）
    EXCHANGE_RATES = {
        'HKD_USD': 0.128,  # 1 HKD = 0.128 USD
        'USD_HKD': 7.8,    # 1 USD = 7.8 HKD
    }
    
    # 風險管理參數
    DEFAULT_RISK_PARAMS = {
        'max_single_trade_pct': 10,      # 單筆最大投入比例 (%)
        'recommended_trade_pct': 5,       # 建議單筆投入比例 (%)
        'max_total_option_pct': 30,       # 期權總倉位最大比例 (%)
        'stop_loss_pct': 50,              # 止損比例 (%)
        'contract_size': 100,             # 期權合約乘數
    }
    
    def __init__(self, total_capital: float, currency: str = 'HKD'):
        """
        初始化計算器
        
        Args:
            total_capital: 總資金
            currency: 貨幣類型 (HKD/USD)
        """
        self.total_capital = total_capital
        self.currency = currency.upper()
        self.capital_usd = self._convert_to_usd(total_capital, currency)
        self.analysis_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _convert_to_usd(self, amount: float, currency: str) -> float:
        """轉換為美元"""
        if currency.upper() == 'USD':
            return amount
        elif currency.upper() == 'HKD':
            return amount * self.EXCHANGE_RATES['HKD_USD']
        else:
            logger.warning(f"未知貨幣 {currency}，假設為 USD")
            return amount
    
    def _convert_from_usd(self, amount_usd: float) -> float:
        """從美元轉換為用戶貨幣"""
        if self.currency == 'USD':
            return amount_usd
        elif self.currency == 'HKD':
            return amount_usd * self.EXCHANGE_RATES['USD_HKD']
        return amount_usd
    
    def calculate_position(
        self,
        option_premium: float,
        risk_level: str = 'moderate',  # conservative, moderate, aggressive
        strategy_type: str = 'long'     # long, short
    ) -> Dict[str, Any]:
        """
        計算建議倉位
        
        Args:
            option_premium: 期權權利金（每股，USD）
            risk_level: 風險偏好
            strategy_type: 策略類型
        
        Returns:
            Dict: 倉位計算結果
        """
        try:
            # 根據風險偏好設定參數
            risk_params = self._get_risk_params(risk_level)
            
            # 計算單筆最大投入（USD）
            max_single_trade_usd = self.capital_usd * (risk_params['max_single_trade_pct'] / 100)
            recommended_trade_usd = self.capital_usd * (risk_params['recommended_trade_pct'] / 100)
            
            # 計算每張合約成本
            contract_cost = option_premium * self.DEFAULT_RISK_PARAMS['contract_size']
            
            if contract_cost <= 0:
                return {
                    'status': 'error',
                    'reason': '期權權利金無效'
                }
            
            # 計算可買張數
            max_contracts = int(max_single_trade_usd / contract_cost)
            recommended_contracts = int(recommended_trade_usd / contract_cost)
            
            # 確保至少 1 張
            recommended_contracts = max(1, recommended_contracts)
            max_contracts = max(1, max_contracts)
            
            # 計算實際投入和風險
            if strategy_type == 'long':
                # Long 策略：最大虧損 = 權利金
                actual_cost = recommended_contracts * contract_cost
                max_loss = actual_cost  # 100% 虧損
                max_loss_pct = (max_loss / self.capital_usd) * 100
            else:
                # Short 策略：需要保證金，風險更大
                actual_cost = recommended_contracts * contract_cost
                # 假設最大虧損為權利金的 5 倍（裸賣風險）
                max_loss = actual_cost * 5
                max_loss_pct = (max_loss / self.capital_usd) * 100
            
            result = {
                'status': 'success',
                'analysis_date': self.analysis_date,
                'capital_info': {
                    'total_capital': self.total_capital,
                    'currency': self.currency,
                    'total_capital_usd': round(self.capital_usd, 2),
                },
                'risk_level': risk_level,
                'risk_params': risk_params,
                'option_info': {
                    'premium_per_share': option_premium,
                    'contract_size': self.DEFAULT_RISK_PARAMS['contract_size'],
                    'cost_per_contract': round(contract_cost, 2),
                },
                'position_recommendation': {
                    'recommended_contracts': recommended_contracts,
                    'max_contracts': max_contracts,
                    'actual_investment_usd': round(recommended_contracts * contract_cost, 2),
                    'actual_investment_local': round(self._convert_from_usd(recommended_contracts * contract_cost), 2),
                    'investment_pct': round((recommended_contracts * contract_cost / self.capital_usd) * 100, 2),
                },
                'risk_analysis': {
                    'strategy_type': strategy_type,
                    'max_loss_usd': round(max_loss, 2),
                    'max_loss_local': round(self._convert_from_usd(max_loss), 2),
                    'max_loss_pct': round(max_loss_pct, 2),
                    'risk_rating': self._rate_risk(max_loss_pct),
                },
                'stop_loss': {
                    'suggested_stop_loss_pct': risk_params['stop_loss_pct'],
                    'stop_loss_price': round(option_premium * (1 - risk_params['stop_loss_pct'] / 100), 2),
                    'stop_loss_amount_usd': round(recommended_contracts * contract_cost * (risk_params['stop_loss_pct'] / 100), 2),
                },
                'warnings': self._generate_warnings(max_loss_pct, recommended_contracts, contract_cost)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"倉位計算錯誤: {e}")
            return {
                'status': 'error',
                'reason': str(e)
            }
    
    def _get_risk_params(self, risk_level: str) -> Dict[str, float]:
        """根據風險偏好獲取參數"""
        if risk_level == 'conservative':
            return {
                'max_single_trade_pct': 5,
                'recommended_trade_pct': 3,
                'max_total_option_pct': 15,
                'stop_loss_pct': 30,
            }
        elif risk_level == 'aggressive':
            return {
                'max_single_trade_pct': 15,
                'recommended_trade_pct': 10,
                'max_total_option_pct': 50,
                'stop_loss_pct': 70,
            }
        else:  # moderate
            return {
                'max_single_trade_pct': 10,
                'recommended_trade_pct': 5,
                'max_total_option_pct': 30,
                'stop_loss_pct': 50,
            }
    
    def _rate_risk(self, max_loss_pct: float) -> str:
        """評估風險等級"""
        if max_loss_pct <= 3:
            return "🟢 低風險"
        elif max_loss_pct <= 5:
            return "🟡 中等風險"
        elif max_loss_pct <= 10:
            return "🟠 較高風險"
        else:
            return "🔴 高風險"
    
    def _generate_warnings(
        self,
        max_loss_pct: float,
        contracts: int,
        contract_cost: float
    ) -> List[str]:
        """生成風險警告"""
        warnings = []
        
        if max_loss_pct > 10:
            warnings.append(f"⚠️ 最大虧損 {max_loss_pct:.1f}% 超過 10%，建議減少倉位")
        
        if contracts >= 5:
            warnings.append(f"⚠️ 建議張數 {contracts} 張較多，注意分散風險")
        
        if contract_cost > self.capital_usd * 0.1:
            warnings.append("⚠️ 單張合約成本較高，注意資金管理")
        
        if self.capital_usd < 5000:
            warnings.append("💡 資金較少，建議每次只交易 1 張期權")
        
        return warnings

    
    def calculate_multiple_positions(
        self,
        options: List[Dict[str, Any]],
        risk_level: str = 'moderate'
    ) -> Dict[str, Any]:
        """
        計算多個期權的倉位分配
        
        Args:
            options: 期權列表 [{'ticker': 'ORCL', 'premium': 5.45, 'strategy': 'long_call'}, ...]
            risk_level: 風險偏好
        """
        try:
            risk_params = self._get_risk_params(risk_level)
            max_total_pct = risk_params['max_total_option_pct']
            
            # 計算總期權預算
            total_option_budget_usd = self.capital_usd * (max_total_pct / 100)
            
            results = {
                'status': 'success',
                'analysis_date': self.analysis_date,
                'capital_info': {
                    'total_capital': self.total_capital,
                    'currency': self.currency,
                    'total_capital_usd': round(self.capital_usd, 2),
                    'option_budget_usd': round(total_option_budget_usd, 2),
                    'option_budget_local': round(self._convert_from_usd(total_option_budget_usd), 2),
                    'option_budget_pct': max_total_pct,
                },
                'positions': [],
                'summary': {
                    'total_positions': 0,
                    'total_investment_usd': 0,
                    'total_max_loss_usd': 0,
                    'remaining_budget_usd': total_option_budget_usd,
                }
            }
            
            remaining_budget = total_option_budget_usd
            
            for opt in options:
                premium = opt.get('premium', 0)
                strategy = opt.get('strategy', 'long')
                ticker = opt.get('ticker', 'N/A')
                
                if premium <= 0:
                    continue
                
                contract_cost = premium * self.DEFAULT_RISK_PARAMS['contract_size']
                
                # 計算該期權可分配的張數
                # 每個期權最多用總預算的 1/3
                single_option_budget = min(remaining_budget, total_option_budget_usd / 3)
                contracts = max(1, int(single_option_budget / contract_cost))
                
                actual_cost = contracts * contract_cost
                
                if actual_cost > remaining_budget:
                    contracts = max(1, int(remaining_budget / contract_cost))
                    actual_cost = contracts * contract_cost
                
                if strategy.startswith('long'):
                    max_loss = actual_cost
                else:
                    max_loss = actual_cost * 3  # Short 策略風險更高
                
                position = {
                    'ticker': ticker,
                    'strategy': strategy,
                    'premium': premium,
                    'contracts': contracts,
                    'investment_usd': round(actual_cost, 2),
                    'max_loss_usd': round(max_loss, 2),
                    'pct_of_capital': round((actual_cost / self.capital_usd) * 100, 2),
                }
                
                results['positions'].append(position)
                results['summary']['total_positions'] += 1
                results['summary']['total_investment_usd'] += actual_cost
                results['summary']['total_max_loss_usd'] += max_loss
                
                remaining_budget -= actual_cost
            
            results['summary']['total_investment_usd'] = round(results['summary']['total_investment_usd'], 2)
            results['summary']['total_max_loss_usd'] = round(results['summary']['total_max_loss_usd'], 2)
            results['summary']['remaining_budget_usd'] = round(remaining_budget, 2)
            results['summary']['total_investment_pct'] = round(
                (results['summary']['total_investment_usd'] / self.capital_usd) * 100, 2
            )
            
            return results
            
        except Exception as e:
            logger.error(f"多倉位計算錯誤: {e}")
            return {
                'status': 'error',
                'reason': str(e)
            }
    
    def get_position_summary(self) -> Dict[str, Any]:
        """獲取資金概況"""
        return {
            'total_capital': self.total_capital,
            'currency': self.currency,
            'total_capital_usd': round(self.capital_usd, 2),
            'exchange_rate': self.EXCHANGE_RATES.get(f'{self.currency}_USD', 1),
            'risk_budgets': {
                'conservative': {
                    'single_trade_usd': round(self.capital_usd * 0.03, 2),
                    'single_trade_local': round(self._convert_from_usd(self.capital_usd * 0.03), 2),
                    'total_option_usd': round(self.capital_usd * 0.15, 2),
                },
                'moderate': {
                    'single_trade_usd': round(self.capital_usd * 0.05, 2),
                    'single_trade_local': round(self._convert_from_usd(self.capital_usd * 0.05), 2),
                    'total_option_usd': round(self.capital_usd * 0.30, 2),
                },
                'aggressive': {
                    'single_trade_usd': round(self.capital_usd * 0.10, 2),
                    'single_trade_local': round(self._convert_from_usd(self.capital_usd * 0.10), 2),
                    'total_option_usd': round(self.capital_usd * 0.50, 2),
                },
            },
            'recommendations': self._generate_capital_recommendations()
        }
    
    def _generate_capital_recommendations(self) -> List[str]:
        """生成資金管理建議"""
        recommendations = []
        
        if self.capital_usd < 5000:
            recommendations.append("💡 資金 < $5,000：建議每次只交易 1 張期權，專注學習")
            recommendations.append("💡 優先選擇低價股期權（股價 < $50）")
        elif self.capital_usd < 15000:
            recommendations.append("💡 資金 $5,000-$15,000：可同時持有 2-3 個期權倉位")
            recommendations.append("💡 單筆投入建議 $500-$1,500")
        elif self.capital_usd < 50000:
            recommendations.append("💡 資金 $15,000-$50,000：可考慮多元化策略")
            recommendations.append("💡 可開始嘗試 Short Put 接貨策略")
        else:
            recommendations.append("💡 資金 > $50,000：可執行完整的期權策略組合")
            recommendations.append("💡 建議分散到 5-10 個不同標的")
        
        recommendations.append(f"📊 當前資金: {self.currency} {self.total_capital:,.0f} (≈ USD {self.capital_usd:,.0f})")
        
        return recommendations


# 測試代碼
if __name__ == "__main__":
    # 測試：13萬 HKD
    calc = PositionCalculator(total_capital=130000, currency='HKD')
    
    print("=== 資金概況 ===")
    summary = calc.get_position_summary()
    print(f"總資金: {summary['currency']} {summary['total_capital']:,}")
    print(f"USD 等值: ${summary['total_capital_usd']:,}")
    print(f"\n建議:")
    for rec in summary['recommendations']:
        print(f"  {rec}")
    
    print("\n=== 單筆倉位計算 ===")
    result = calc.calculate_position(
        option_premium=5.45,
        risk_level='moderate',
        strategy_type='long'
    )
    
    if result['status'] == 'success':
        pos = result['position_recommendation']
        print(f"建議張數: {pos['recommended_contracts']} 張")
        print(f"投入金額: ${pos['actual_investment_usd']}")
        print(f"佔總資金: {pos['investment_pct']}%")
        
        risk = result['risk_analysis']
        print(f"最大虧損: ${risk['max_loss_usd']} ({risk['max_loss_pct']}%)")
        print(f"風險評級: {risk['risk_rating']}")
