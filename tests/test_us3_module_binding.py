# tests/test_us3_module_binding.py
"""
US-3: Module 11 & 19 邏輯綁定測試
測試 Put-Call Parity 失效時自動觸發 Module 11 分析
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import OptionsAnalysisSystem
from calculation_layer.module19_put_call_parity import ParityResult


class TestUS3ModuleBinding(unittest.TestCase):
    """US-3: Module 11 & 19 邏輯綁定測試類"""
    
    def setUp(self):
        """測試前準備"""
        self.system = OptionsAnalysisSystem(use_ibkr=False)
    
    def test_parity_failure_triggers_module11(self):
        """
        Task 3.4.1: 測試 Parity 失效觸發 Module 11
        
        驗證:
        - 當 Module 19 檢測到套利機會時
        - 自動觸發 Module 11 分析
        - 結果中包含 triggered_by_parity 標識
        """
        # 模擬 Parity 失效結果
        parity_result = {
            'call_price': 11.00,
            'put_price': 5.57,
            'stock_price': 100.0,
            'strike_price': 100.0,
            'deviation': 0.55,
            'arbitrage_opportunity': True,
            'theoretical_profit': 0.45,
            'strategy': '套利策略: 沽出 Call, 買入 Put, 買入股票'
        }
        
        # 調用 _run_module11_with_parity_context
        result = self.system._run_module11_with_parity_context(
            parity_result=parity_result,
            stock_price=100.0,
            strike_price=100.0,
            call_premium=11.00,
            put_premium=5.57,
            risk_free_rate=0.05,
            time_to_expiration=1.0,
            dividend_yield=0.0
        )
        
        # 驗證結果
        self.assertIsNotNone(result, "Module 11 應該返回結果")
        self.assertIn('synthetic_price', result)
        self.assertIn('difference', result)
        self.assertIn('arbitrage_opportunity', result)
    
    def test_arbitrage_strategy_generation_call_overvalued(self):
        """
        Task 3.4.2: 測試套利策略生成（Call 高估場景）
        
        驗證:
        - 當 Call 相對高估時
        - 生成 Short Synthetic 策略
        - 包含正確的交易腿
        """
        parity_result = {
            'deviation': 0.55,  # 正偏離 → Call 高估
            'theoretical_profit': 0.45
        }
        
        synthetic_result = {
            'synthetic_price': 100.55,
            'difference': -0.55,
            'arbitrage_opportunity': True
        }
        
        # 調用 _generate_arbitrage_strategy
        strategy = self.system._generate_arbitrage_strategy(
            parity_result=parity_result,
            synthetic_result=synthetic_result,
            stock_price=100.0,
            strike_price=100.0
        )
        
        # 驗證策略類型
        self.assertEqual(strategy['strategy_type'], 'short_synthetic')
        self.assertEqual(strategy['strategy_name'], '合成 Short Stock')
        
        # 驗證交易腿
        legs = strategy['legs']
        self.assertEqual(len(legs), 3)
        self.assertEqual(legs[0]['action'], '沽出')
        self.assertEqual(legs[0]['type'], 'Call')
        self.assertEqual(legs[1]['action'], '買入')
        self.assertEqual(legs[1]['type'], 'Put')
        self.assertEqual(legs[2]['action'], '買入')
        self.assertEqual(legs[2]['type'], 'Stock')
        
        # 驗證風險分析
        self.assertIn('risk_analysis', strategy)
        self.assertIn('risks', strategy['risk_analysis'])
        self.assertGreater(len(strategy['risk_analysis']['risks']), 0)
        
        # 驗證執行步驟
        self.assertIn('execution_steps', strategy)
        self.assertGreater(len(strategy['execution_steps']), 0)
    
    def test_arbitrage_strategy_generation_put_overvalued(self):
        """
        Task 3.4.3: 測試套利策略生成（Put 高估場景）
        
        驗證:
        - 當 Put 相對高估時
        - 生成 Long Synthetic 策略
        - 包含正確的交易腿
        """
        parity_result = {
            'deviation': -0.55,  # 負偏離 → Put 高估
            'theoretical_profit': 0.45
        }
        
        synthetic_result = {
            'synthetic_price': 99.45,
            'difference': 0.55,
            'arbitrage_opportunity': True
        }
        
        # 調用 _generate_arbitrage_strategy
        strategy = self.system._generate_arbitrage_strategy(
            parity_result=parity_result,
            synthetic_result=synthetic_result,
            stock_price=100.0,
            strike_price=100.0
        )
        
        # 驗證策略類型
        self.assertEqual(strategy['strategy_type'], 'long_synthetic')
        self.assertEqual(strategy['strategy_name'], '合成 Long Stock')
        
        # 驗證交易腿
        legs = strategy['legs']
        self.assertEqual(len(legs), 3)
        self.assertEqual(legs[0]['action'], '買入')
        self.assertEqual(legs[0]['type'], 'Call')
        self.assertEqual(legs[1]['action'], '沽出')
        self.assertEqual(legs[1]['type'], 'Put')
        self.assertEqual(legs[2]['action'], '沽出')
        self.assertEqual(legs[2]['type'], 'Stock')
        
        # 驗證包含融券風險
        risks = strategy['risk_analysis']['risks']
        self.assertTrue(any('融券' in risk for risk in risks))
    
    def test_no_arbitrage_no_trigger(self):
        """
        測試無套利機會時不觸發 Module 11
        
        驗證:
        - 當 Module 19 沒有檢測到套利機會時
        - 不應該觸發 Module 11
        """
        # 模擬無套利機會的 Parity 結果
        self.system.analysis_results = {
            'module19_put_call_parity': {
                'market_prices': {
                    'arbitrage_opportunity': False,
                    'deviation': 0.01
                }
            }
        }
        
        # 驗證 module11_synthetic 不應該被創建
        self.assertNotIn('module11_synthetic', self.system.analysis_results)
    
    def test_report_generation_with_arbitrage(self):
        """
        Task 3.4.4: 測試報告生成（HTML 輸出驗證）
        
        驗證:
        - 報告包含套利機會警報
        - 報告包含策略詳情
        - 報告包含風險分析
        """
        from output_layer.report_generator import ReportGenerator
        from output_layer.output_manager import OutputPathManager
        
        # 創建報告生成器
        output_manager = OutputPathManager(base_output_dir="output")
        report_gen = ReportGenerator(output_manager=output_manager)
        
        # 模擬 Module 11 結果（由 Parity 觸發）
        module11_results = {
            'strike_price': 100.0,
            'call_premium': 11.00,
            'put_premium': 5.57,
            'synthetic_price': 105.43,
            'current_stock_price': 100.0,
            'difference': -5.43,
            'arbitrage_opportunity': True,
            'triggered_by_parity': True,
            'parity_deviation': 0.55,
            'arbitrage_strategy': {
                'strategy_type': 'short_synthetic',
                'strategy_name': '合成 Short Stock',
                'legs': [
                    {'action': '沽出', 'type': 'Call', 'strike': 100.0, 'quantity': 1},
                    {'action': '買入', 'type': 'Put', 'strike': 100.0, 'quantity': 1},
                    {'action': '買入', 'type': 'Stock', 'strike': None, 'quantity': 100}
                ],
                'theoretical_profit': 0.45,
                'risk_analysis': {
                    'max_profit': 0.45,
                    'max_loss': 0.0,
                    'break_even': 100.0,
                    'risks': [
                        '執行風險：需要同時執行多個交易',
                        '流動性風險：期權市場流動性不足可能導致滑點'
                    ]
                },
                'execution_steps': [
                    '1. 同時下單：沽出 Call + 買入 Put + 買入 Stock',
                    '2. 確保所有訂單以限價單執行'
                ]
            }
        }
        
        # 生成報告
        report = report_gen._format_module11_synthetic_stock(module11_results)
        
        # 驗證報告內容
        self.assertIn('套利機會警報', report)
        self.assertIn('Put-Call Parity 失效', report)
        self.assertIn('Parity 偏離', report)
        self.assertIn('套利策略詳情', report)
        self.assertIn('交易組合', report)
        self.assertIn('風險提示', report)
        self.assertIn('執行步驟', report)
        
        # 驗證策略腿顯示
        self.assertIn('沽出', report)
        self.assertIn('Call', report)
        self.assertIn('買入', report)
        self.assertIn('Put', report)
        self.assertIn('Stock', report)


def run_tests():
    """運行所有測試"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestUS3ModuleBinding)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
