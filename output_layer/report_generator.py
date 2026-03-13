# output_layer/report_generator.py
"""
報告生成系統 (重構版 - 整合 CSV/JSON 導出器)

Requirements: 15.1, 15.3, 15.4, 15.5
"""

from datetime import datetime
from pathlib import Path
import logging

# 導入專門的導出器
from output_layer.csv_exporter import CSVExporter
from output_layer.json_exporter import JSONExporter
from output_layer.output_manager import OutputPathManager
from output_layer.strategy_scenario_generator import StrategyScenarioGenerator
from output_layer.module_consistency_checker import ModuleConsistencyChecker

# 導入序列化工具（修復 NaN/Inf 處理問題）
from utils.serialization import CustomJSONEncoder

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    專業報告生成器
    
    功能:
    1. 整合 CSV 和 JSON 導出器
    2. 支持所有 19 個模塊的格式化
    3. 提供結構化數據用於 Web/Telegram
    4. 生成純文本報告
    """
    
    def __init__(self, output_dir='output/',         output_manager = None):
        """
        初始化報告生成器
        
        參數:
            output_dir: 輸出目錄路徑
            output_manager: OutputPathManager 實例（用於按股票代號分類存儲）
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 使用 OutputPathManager 進行路徑管理
        self.output_manager = output_manager or OutputPathManager(str(output_dir))
        
        # 初始化 CSV 和 JSON 導出器（舊結構，保留向後兼容）
        self.csv_exporter = CSVExporter(str(self.output_dir / 'csv'))
        self.json_exporter = JSONExporter(str(self.output_dir / 'json'))
        
        # 初始化模塊一致性檢查器 (Requirements: 8.1, 8.2, 8.3, 8.4)
        self.consistency_checker = ModuleConsistencyChecker()
        
        logger.info(f"* 報告生成器初始化完成")
        logger.info(f"  主輸出目錄: {self.output_dir}")
        logger.info(f"  使用 OutputPathManager: 按股票代號分類存儲")
    
    def get_structured_output(self, calculation_results: dict) -> dict:
        """
        獲取結構化輸出（用於 Web/Telegram）
        
        返回格式化好的、易於顯示的結構化數據
        """
        structured = {}
        
        for module_name, module_data in calculation_results.items():
            if module_name == 'module1_support_resistance_multi':
                structured[module_name] = self._structure_module1(module_data)
            elif module_name == 'module15_black_scholes':
                structured[module_name] = self._structure_module15(module_data)
            elif module_name == 'module16_greeks':
                structured[module_name] = self._structure_module16(module_data)
            elif module_name == 'module17_implied_volatility':
                structured[module_name] = self._structure_module17(module_data)
            elif module_name == 'module18_historical_volatility':
                structured[module_name] = self._structure_module18(module_data)
            elif module_name == 'module19_put_call_parity':
                structured[module_name] = self._structure_module19(module_data)
            elif module_name in ['module7_long_call', 'module8_long_put', 'module9_short_call', 'module10_short_put']:
                structured[module_name] = self._structure_strategy(module_name, module_data)
            else:
                structured[module_name] = module_data
        
        return structured
    
    def _structure_module1(self, data: dict) -> dict:
        """結構化 Module 1 數據"""
        return {
            'type': 'support_resistance',
            'stock_price': data.get('stock_price'),
            'implied_volatility': data.get('implied_volatility'),
            'days_to_expiration': data.get('days_to_expiration'),
            'confidence_levels': [
                {
                    'level': level,
                    'z_score': info.get('z_score'),
                    'support': info.get('support'),
                    'resistance': info.get('resistance'),
                    'move_percentage': info.get('move_percentage')
                }
                for level, info in data.get('results', {}).items()
            ]
        }
    
    def _structure_module15(self, data: dict) -> dict:
        """結構化 Module 15 數據"""
        return {
            'type': 'black_scholes',
            'call': {
                'price': data.get('call', {}).get('option_price'),
                'd1': data.get('call', {}).get('d1'),
                'd2': data.get('call', {}).get('d2')
            },
            'put': {
                'price': data.get('put', {}).get('option_price'),
                'd1': data.get('put', {}).get('d1'),
                'd2': data.get('put', {}).get('d2')
            },
            'parameters': data.get('parameters', {})
        }
    
    def _structure_module16(self, data: dict) -> dict:
        """結構化 Module 16 數據"""
        result = {
            'type': 'greeks',
            'call': {
                'delta': data.get('call', {}).get('delta'),
                'gamma': data.get('call', {}).get('gamma'),
                'theta': data.get('call', {}).get('theta'),
                'vega': data.get('call', {}).get('vega'),
                'rho': data.get('call', {}).get('rho')
            } if data.get('call') else None
        }
        
        # 只有當 put 數據存在時才添加
        if data.get('put'):
            result['put'] = {
                'delta': data.get('put', {}).get('delta'),
                'gamma': data.get('put', {}).get('gamma'),
                'theta': data.get('put', {}).get('theta'),
                'vega': data.get('put', {}).get('vega'),
                'rho': data.get('put', {}).get('rho')
            }
        
        return result
    
    def _structure_module17(self, data: dict) -> dict:
        """結構化 Module 17 數據"""
        return {
            'type': 'implied_volatility',
            'call': {
                'iv': data.get('call', {}).get('implied_volatility'),
                'converged': data.get('call', {}).get('converged'),
                'iterations': data.get('call', {}).get('iterations')
            },
            'put': {
                'iv': data.get('put', {}).get('implied_volatility'),
                'converged': data.get('put', {}).get('converged'),
                'iterations': data.get('put', {}).get('iterations')
            } if 'put' in data else None
        }
    
    def _structure_module18(self, data: dict) -> dict:
        """結構化 Module 18 數據"""
        return {
            'type': 'historical_volatility',
            'hv_windows': {
                str(window): info.get('hv') if isinstance(info, dict) else info.get('historical_volatility')
                for window, info in data.get('hv_results', {}).items()
            },
            'iv_hv_comparison': data.get('iv_hv_comparison', {})
        }
    
    def _structure_module19(self, data: dict) -> dict:
        """結構化 Module 19 數據"""
        return {
            'type': 'put_call_parity',
            'market': {
                'deviation': data.get('market_prices', {}).get('deviation'),
                'has_arbitrage': data.get('market_prices', {}).get('arbitrage_opportunity'),
                'profit': data.get('market_prices', {}).get('theoretical_profit')
            },
            'theoretical': {
                'deviation': data.get('theoretical_prices', {}).get('deviation'),
                'has_arbitrage': data.get('theoretical_prices', {}).get('arbitrage_opportunity')
            }
        }
    
    def _structure_strategy(self, module_name: str, data: list) -> dict:
        """結構化策略數據"""
        return {
            'type': 'strategy',
            'scenarios': [
                {
                    'stock_price': item.get('stock_price_at_expiry'),
                    'profit_loss': item.get('profit_loss'),
                    'return_percentage': item.get('return_percentage')
                }
                for item in (data if isinstance(data, list) else [])
            ]
        }
    
    def generate(self, 
                ticker: str,
                analysis_date: str,
                raw_data: dict,
                calculation_results: dict,
                data_fetcher=None,
                delta_report=None) -> dict:
        """
        生成完整分析報告（按股票代號分類存儲）
        
        參數:
            ticker: 股票代碼
            analysis_date: 分析日期
            raw_data: 原始數據
            calculation_results: 計算結果
            data_fetcher: DataFetcher 實例（用於獲取 API 狀態）
        
        返回: dict (報告文件位置)
        
        Requirements: 15.1, 15.3, 15.4, 15.5
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            logger.info("開始生成報告...")
            
            # 獲取 API 狀態報告（如果提供了 data_fetcher）
            api_status = None
            if data_fetcher and hasattr(data_fetcher, 'get_api_status_report'):
                try:
                    api_status = data_fetcher.get_api_status_report()
                except Exception as e:
                    logger.warning(f"! 無法獲取 API 狀態: {e}")
            
            # 使用 OutputPathManager 獲取正確的輸出路徑
            json_filename = f"report_{ticker}_{timestamp}.json"
            csv_filename = f"report_{ticker}_{timestamp}.csv"
            text_filename = f"report_{ticker}_{timestamp}.txt"
            
            # 獲取按股票代號分類的路徑
            json_path = self.output_manager.get_output_path(ticker, 'json', json_filename)
            csv_path = self.output_manager.get_output_path(ticker, 'csv', csv_filename)
            text_path = self.output_manager.get_output_path(ticker, 'txt', text_filename)
            
            # 1. 生成JSON報告
            json_report = self._generate_json_report(
                ticker, analysis_date, raw_data, calculation_results, api_status
            )
            self._save_json_to_path(json_report, json_path)
            
            # 2. 生成CSV報告
            self._generate_csv_report_to_path(calculation_results, csv_path, api_status)
            
            # 3. 生成純文本報告
            self._generate_text_report_to_path(
                ticker, analysis_date, raw_data, calculation_results, text_path, api_status, delta_report
            )
            
            logger.info(f"* 報告已生成 (按股票代號分類)")
            logger.info(f"  JSON: {json_path}")
            logger.info(f"  CSV: {csv_path}")
            logger.info(f"  TXT: {text_path}")
            
            return {
                'json_file': json_path,
                'csv_file': csv_path,
                'text_file': text_path,
                'timestamp': timestamp,
                'structured_data': self.get_structured_output(calculation_results)
            }
            
        except Exception as e:
            import traceback
            logger.error(f"x 報告生成失敗: {e}")
            logger.error(f"  詳細錯誤:\n{traceback.format_exc()}")
            raise
    
    def _generate_json_report(self, ticker, analysis_date, raw_data, calculation_results, api_status=None):
        """
        生成JSON報告（使用 JSONExporter）
        """
        report_data = {
            'metadata': {
                'system': 'Options Trading Analysis System',
                'version': '2.0',
                'generated_at': datetime.now().isoformat(),
                'ticker': ticker,
                'analysis_date': analysis_date
            },
            'raw_data': raw_data,
            'calculations': calculation_results,
            'structured_output': self.get_structured_output(calculation_results)
        }
        
        # 添加 API 狀態信息
        if api_status:
            report_data['api_status'] = api_status
        
        return report_data
    
    def _save_json(self, data, filename):
        """
        保存JSON文件（使用 JSONExporter）- 舊方法，保留向後兼容
        """
        # 使用 JSONExporter 導出
        success = self.json_exporter.export_results(
            [data],  # JSONExporter 期望列表格式
            filename=filename,
            pretty=True,
            add_metadata=False  # 我們已經有自己的 metadata
        )
        
        if success:
            logger.info(f"* JSON報告已保存: {self.json_exporter.output_dir / filename}")
        else:
            logger.error(f"x JSON報告保存失敗: {filename}")
    
    def _save_json_to_path(self, data, filepath: str):
        """
        保存JSON文件到指定路徑（使用 OutputPathManager）
        
        Requirements: 15.4
        """
        import json
        import os
        from utils.serialization import convert_to_serializable, CustomJSONEncoder
        
        # 確保目錄存在
        self.output_manager.ensure_directory_exists(os.path.dirname(filepath))
        
        try:
            # 先預處理數據，將所有 Timestamp 鍵轉換為字符串
            serializable_data = convert_to_serializable(data)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                # 使用 CustomJSONEncoder 正確處理 NaN/Inf 值（轉為 null 而非 "nan" 字符串）
                json.dump(serializable_data, f, ensure_ascii=False, indent=2, cls=CustomJSONEncoder)
            logger.info(f"* JSON報告已保存: {filepath}")
        except Exception as e:
            logger.error(f"x JSON報告保存失敗: {filepath} - {e}")
            raise
    
    def _prepare_csv_rows(self, calculation_results, api_status=None):
        """準備 CSV 數據行（增強版 - 支持深度嵌套）"""
        csv_rows = []
        
        def flatten_dict(data, prefix=''):
            """遞歸展平嵌套字典"""
            rows = []
            if isinstance(data, dict):
                for key, value in data.items():
                    new_prefix = f"{prefix}.{key}" if prefix else key
                    if isinstance(value, dict):
                        # 對於特定的大型嵌套結構，只提取關鍵信息
                        if key in ['analyzed_strikes', 'call_ivs', 'put_ivs', 'visualization']:
                            # 跳過詳細的行使價列表，只記錄數量
                            if isinstance(value, list):
                                rows.append((new_prefix + '_count', len(value)))
                            continue
                        rows.extend(flatten_dict(value, new_prefix))
                    elif isinstance(value, list):
                        if len(value) > 0 and isinstance(value[0], dict):
                            # 對於字典列表，只記錄數量和第一個元素的關鍵信息
                            rows.append((new_prefix + '_count', len(value)))
                            if key == 'top_recommendations' and len(value) > 0:
                                # 記錄最佳推薦
                                best = value[0]
                                rows.append((new_prefix + '_best_strike', best.get('strike', 'N/A')))
                                rows.append((new_prefix + '_best_score', best.get('composite_score', 'N/A')))
                        else:
                            rows.append((new_prefix, str(value)[:200]))  # 限制長度
                    else:
                        rows.append((new_prefix, value))
            return rows
        
        for module_name, module_data in calculation_results.items():
            if isinstance(module_data, dict):
                # 特殊處理 module22（最佳行使價分析）
                if module_name == 'module22_optimal_strike':
                    for strategy_key in ['long_call', 'long_put', 'short_call', 'short_put']:
                        if strategy_key in module_data:
                            strategy_data = module_data[strategy_key]
                            # 提取關鍵信息
                            csv_rows.append({
                                '模塊': f"{module_name}_{strategy_key}",
                                '指標': 'best_strike',
                                '數值': str(strategy_data.get('best_strike', 'N/A'))
                            })
                            csv_rows.append({
                                '模塊': f"{module_name}_{strategy_key}",
                                '指標': 'total_analyzed',
                                '數值': str(strategy_data.get('total_analyzed', 0))
                            })
                            csv_rows.append({
                                '模塊': f"{module_name}_{strategy_key}",
                                '指標': 'analysis_summary',
                                '數值': str(strategy_data.get('analysis_summary', 'N/A'))
                            })
                            
                            # 波動率微笑關鍵數據
                            smile = strategy_data.get('volatility_smile')
                            if smile is not None and isinstance(smile, dict):
                                csv_rows.append({
                                    '模塊': f"{module_name}_{strategy_key}_smile",
                                    '指標': 'atm_iv',
                                    '數值': str(smile.get('atm_iv', 'N/A'))
                                })
                                csv_rows.append({
                                    '模塊': f"{module_name}_{strategy_key}_smile",
                                    '指標': 'skew',
                                    '數值': str(smile.get('skew', 'N/A'))
                                })
                                csv_rows.append({
                                    '模塊': f"{module_name}_{strategy_key}_smile",
                                    '指標': 'smile_shape',
                                    '數值': str(smile.get('smile_shape', 'N/A'))
                                })
                            
                            # Parity 驗證關鍵數據
                            parity = strategy_data.get('parity_validation')
                            if parity is not None and isinstance(parity, dict):
                                csv_rows.append({
                                    '模塊': f"{module_name}_{strategy_key}_parity",
                                    '指標': 'deviation_pct',
                                    '數值': str(parity.get('deviation_pct', 'N/A'))
                                })
                                csv_rows.append({
                                    '模塊': f"{module_name}_{strategy_key}_parity",
                                    '指標': 'arbitrage_opportunity',
                                    '數值': str(parity.get('arbitrage_opportunity', False))
                                })
                else:
                    # 一般模塊處理
                    flattened = flatten_dict(module_data)
                    for key, value in flattened:
                        csv_rows.append({
                            '模塊': module_name,
                            '指標': key,
                            '數值': str(value)
                        })
            elif isinstance(module_data, list):
                for i, item in enumerate(module_data, 1):
                    if isinstance(item, dict):
                        for key, value in item.items():
                            csv_rows.append({
                                '模塊': f"{module_name}_場景{i}",
                                '指標': key,
                                '數值': str(value)
                            })
        
        # 添加 IV Rank 和 IV Percentile 到 CSV（如果存在）
        module18_data = calculation_results.get('module18_historical_volatility', {})
        if module18_data.get('iv_rank') is not None:
            csv_rows.append({
                '模塊': 'IV_Analysis',
                '指標': 'iv_rank',
                '數值': str(module18_data.get('iv_rank'))
            })
        if module18_data.get('iv_percentile') is not None:
            csv_rows.append({
                '模塊': 'IV_Analysis',
                '指標': 'iv_percentile',
                '數值': str(module18_data.get('iv_percentile'))
            })
        if module18_data.get('iv_recommendation'):
            rec = module18_data['iv_recommendation']
            csv_rows.append({
                '模塊': 'IV_Analysis',
                '指標': 'iv_recommendation_action',
                '數值': str(rec.get('action', 'N/A'))
            })
            csv_rows.append({
                '模塊': 'IV_Analysis',
                '指標': 'iv_recommendation_reason',
                '數值': str(rec.get('reason', 'N/A'))
            })
        
        if api_status:
            csv_rows.append({'模塊': '', '指標': '', '數值': ''})
            csv_rows.append({'模塊': 'API狀態', '指標': '數據源', '數值': ''})
            csv_rows.append({'模塊': 'API狀態', '指標': 'IBKR啟用', '數值': str(api_status.get('ibkr_enabled', False))})
            csv_rows.append({'模塊': 'API狀態', '指標': 'IBKR連接', '數值': str(api_status.get('ibkr_connected', False))})
            
            if api_status.get('fallback_used'):
                for data_type, sources in api_status['fallback_used'].items():
                    csv_rows.append({
                        '模塊': 'API狀態',
                        '指標': f'降級使用-{data_type}',
                        '數值': ', '.join(sources)
                    })
        
        return csv_rows
    
    def _generate_csv_report(self, calculation_results, filename, api_status=None):
        """
        生成CSV報告（使用 CSVExporter）- 舊方法，保留向後兼容
        """
        csv_rows = self._prepare_csv_rows(calculation_results, api_status)
        
        # 使用 CSVExporter 導出
        success = self.csv_exporter.export_results(
            csv_rows,
            filename=filename
        )
        
        if success:
            logger.info(f"* CSV報告已保存: {self.csv_exporter.output_dir / filename}")
        else:
            logger.error(f"x CSV報告保存失敗: {filename}")
    
    def _generate_csv_report_to_path(self, calculation_results, filepath: str, api_status=None):
        """
        生成CSV報告到指定路徑（使用 OutputPathManager）
        
        Requirements: 15.3
        """
        import csv
        import os
        
        csv_rows = self._prepare_csv_rows(calculation_results, api_status)
        
        # 確保目錄存在
        self.output_manager.ensure_directory_exists(os.path.dirname(filepath))
        
        try:
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                if csv_rows:
                    writer = csv.DictWriter(f, fieldnames=['模塊', '指標', '數值'])
                    writer.writeheader()
                    writer.writerows(csv_rows)
            logger.info(f"* CSV報告已保存: {filepath}")
        except Exception as e:
            logger.error(f"x CSV報告保存失敗: {filepath} - {e}")
            raise
    
    def _generate_text_report(self, ticker, analysis_date, raw_data, 
                             calculation_results, filename, api_status=None):
        """生成純文本報告 - 舊方法，保留向後兼容"""
        filepath = self.output_dir / filename
        self._write_text_report(filepath, ticker, analysis_date, raw_data, calculation_results, api_status)
    
    def _generate_text_report_to_path(self, ticker, analysis_date, raw_data, 
                                      calculation_results, filepath: str, api_status=None, delta_report=None):
        """
        生成純文本報告到指定路徑（使用 OutputPathManager）
        
        Requirements: 15.5
        """
        import os
        
        # 確保目錄存在
        self.output_manager.ensure_directory_exists(os.path.dirname(filepath))
        self._write_text_report(filepath, ticker, analysis_date, raw_data, calculation_results, api_status, delta_report)
    
    def _safe_format(self, value, fmt=".2f", prefix="", suffix=""):
        """安全格式化函數，處理 None 值"""
        if value is None or (isinstance(value, float) and (value != value)): # check for NaN
            return "N/A"
        try:
            return f"{prefix}{value:{fmt}}{suffix}"
        except (ValueError, TypeError):
            return str(value)

    def _write_text_report(self, filepath, ticker, analysis_date, raw_data, 
                          calculation_results, api_status=None, delta_report=None):
        """寫入純文本報告內容 - 使用流式處理以減少內存使用"""
        from datetime import datetime
        import gc
        
        with open(filepath, 'w', encoding='utf-8') as f:
            # 報告標題
            f.write("=" * 70 + "\n")
            f.write(f"期權合約深度分析報告 - {ticker}\n")
            f.write(f"分析日期: {analysis_date}\n")
            f.write("=" * 70 + "\n\n")
            
            # 決策摘要 (Requirements: 8.1, 8.2, 8.3, 8.4)
            f.write(self._format_decision_summary(ticker, raw_data, calculation_results))
            f.write("\n")
            
            # 原始數據摘要
            f.write("=" * 70 + "\n")
            f.write("原始市場數據\n")
            f.write("=" * 70 + "\n")
            
            if raw_data:
                f.write(f"當前股價: {self._safe_format(raw_data.get('current_price'), prefix='$')}\n")
                f.write(f"隱含波動率: {self._safe_format(raw_data.get('implied_volatility'), suffix='%')}\n")
                f.write(f"EPS: {self._safe_format(raw_data.get('eps'), prefix='$')}\n")
                f.write(f"派息: {self._safe_format(raw_data.get('annual_dividend'), prefix='$')}\n")
                f.write(f"無風險利率: {self._safe_format(raw_data.get('risk_free_rate'), suffix='%')}\n")
                f.write(f"VIX: {self._safe_format(raw_data.get('vix'))}\n")
                
                # 從計算結果中獲取 IV Rank 和 IV Percentile
                module18_data = calculation_results.get('module18_historical_volatility', {})
                iv_rank = module18_data.get('iv_rank')
                iv_percentile = module18_data.get('iv_percentile')
                
                if iv_rank is not None:
                    f.write(f"IV Rank: {iv_rank:.2f}%")
                    if iv_rank < 30:
                        f.write(" (低IV環境)")
                    elif iv_rank > 70:
                        f.write(" (高IV環境)")
                    else:
                        f.write(" (正常)")
                    f.write("\n")
                
                if iv_percentile is not None:
                    f.write(f"IV Percentile: {iv_percentile:.2f}%\n")
                
                f.write("\n")
            
            # API 狀態信息
            if api_status:
                f.write("=" * 70 + "\n")
                f.write("數據源狀態\n")
                f.write("=" * 70 + "\n")
                f.write(f"IBKR 啟用: {'是' if api_status.get('ibkr_enabled') else '否'}\n")
                f.write(f"IBKR 連接: {'是' if api_status.get('ibkr_connected') else '否'}\n")
                if api_status.get('fallback_used'):
                    f.write("\n降級數據源使用情況:\n")
                    for data_type, sources in api_status['fallback_used'].items():
                        f.write(f"  {data_type}: {', '.join(sources)}\n")
                if api_status.get('api_failures'):
                    f.write("\nAPI 故障記錄:\n")
                    for api_name, failures in api_status['api_failures'].items():
                        f.write(f"  {api_name}: {len(failures)} 次故障\n")
                f.write("\n")
            
            # 異動分析報告 (新增)
            if delta_report:
                f.write("=" * 70 + "\n")
                f.write("異動分析 (Changes vs Last Run)\n")
                f.write("=" * 70 + "\n")
                
                # 顯示警報
                if delta_report.get('opportunity_alert'):
                    for alert in delta_report['opportunity_alert']:
                        f.write(f"{alert}\n")
                    f.write("\n")
                else:
                    f.write("無顯著異動\n\n")
                    
                # 詳細對比
                px = delta_report.get('price_change', {})
                if px:
                    prev_px = px.get('previous') or 0
                    curr_px = px.get('current') or 0
                    pct_px = px.get('pct') or 0
                    f.write(f"價格變化: ${prev_px:.2f} -> ${curr_px:.2f} ({pct_px:+.2f}%)\n")
                    
                iv = delta_report.get('iv_change', {})
                if iv:
                    prev_rank = iv.get('previous_rank') or 0
                    curr_rank = iv.get('current_rank') or 0
                    rank_diff = iv.get('rank_diff') or 0
                    f.write(f"IV Rank: {prev_rank:.0f} -> {curr_rank:.0f} (變化 {rank_diff:+.0f})\n")

                
                strat = delta_report.get('strategy_change', {})
                if strat.get('changed'):
                    f.write(f"策略變化: {strat.get('previous_top')} -> {strat.get('current_top')}\n")
                
                f.write("\n")
            
                f.write("\n")
            
            # 計算結果
            f.write("=" * 70 + "\n")
            f.write("計算結果詳解\n")
            f.write("=" * 70 + "\n")
            
            # 特殊處理: Module 1 多信心度報告
            if 'module1_support_resistance_multi' in calculation_results:
                f.write("\n")
                f.write(self._format_module1_multi_confidence(
                    ticker, calculation_results['module1_support_resistance_multi']
                ))
                f.write("\n")
            
            # 按模塊編號排序輸出
            def get_module_number(module_name):
                """提取模塊編號用於排序"""
                import re
                match = re.search(r'module(\d+)', module_name)
                if match:
                    return int(match.group(1))
                # 非模塊項目放在最後
                return 999
            
            sorted_modules = sorted(calculation_results.items(), key=lambda x: get_module_number(x[0]))
            
            for module_name, module_data in sorted_modules:
                # 跳過已處理的多信心度結果
                if module_name == 'module1_support_resistance_multi':
                    continue
                
                # 使用專門的格式化函數
                if module_name == 'module2_fair_value':
                    f.write(self._format_module2_fair_value(module_data))
                elif module_name == 'module3_arbitrage_spread':
                    f.write(self._format_module3_arbitrage_spread(module_data))
                elif module_name == 'module4_pe_valuation':
                    f.write(self._format_module4_pe_valuation(module_data))
                elif module_name == 'module5_rate_pe_relation':
                    f.write(self._format_module5_rate_pe_relation(module_data))
                elif module_name == 'module6_hedge_quantity':
                    f.write(self._format_module6_hedge_quantity(module_data))
                elif module_name == 'module11_synthetic_stock':
                    f.write(self._format_module11_synthetic_stock(module_data))
                elif module_name == 'module12_annual_yield':
                    f.write(self._format_module12_annual_yield(module_data))
                elif module_name == 'module13_position_analysis':
                    f.write(self._format_module13_position_analysis(module_data))
                elif module_name == 'module14_monitoring_posts':
                    f.write(self._format_module14_monitoring_posts(module_data))
                elif module_name == 'module15_black_scholes':
                    f.write(self._format_module15_black_scholes(module_data))
                elif module_name == 'module16_greeks':
                    f.write(self._format_module16_greeks(module_data))
                elif module_name == 'module17_implied_volatility':
                    f.write(self._format_module17_implied_volatility(module_data))
                elif module_name == 'module18_historical_volatility':
                    f.write(self._format_module18_historical_volatility(module_data))
                elif module_name == 'module19_put_call_parity':
                    f.write(self._format_module19_put_call_parity(module_data))
                elif module_name == 'module20_fundamental_health':
                    f.write(self._format_module20_fundamental_health(module_data))
                elif module_name == 'module21_momentum_filter':
                    f.write(self._format_module21_momentum_filter(module_data))
                elif module_name == 'module22_optimal_strike':
                    f.write(self._format_module22_optimal_strike(module_data))
                elif module_name == 'module23_dynamic_iv_threshold':
                    # Requirement 11.4: 傳遞 Module 18 IV Rank 數據進行交叉驗證
                    iv_rank_data = calculation_results.get('module18_historical_volatility', {})
                    f.write(self._format_module23_dynamic_iv_threshold(module_data, iv_rank_data))
                elif module_name == 'module24_technical_direction':
                    f.write(self._format_module24_technical_direction(module_data))
                elif module_name == 'module25_volatility_smile':
                    f.write(self._format_module25_volatility_smile(module_data))
                elif module_name == 'module26_long_option_analysis':
                    f.write(self._format_module26_long_option_analysis(module_data))
                elif module_name == 'module27_multi_expiry_comparison':
                    f.write(self._format_module27_multi_expiry_comparison(module_data))
                elif module_name == 'module28_position_calculator':
                    f.write(self._format_module28_position_calculator(module_data))
                elif module_name == 'module30_unusual_activity':
                    f.write(self._format_module30_unusual_activity(module_data))
                elif module_name == 'module31_advanced_metrics':
                    f.write(self._format_module31_advanced_metrics(module_data))
                elif module_name == 'module32_complex_strategies':
                    f.write(self._format_complex_strategies(module_data))
                elif module_name == 'module33_wolfram_verification':
                    f.write(self._format_module33_wolfram_verification(module_data))
                elif module_name == 'strike_selection':
                    # 顯示行使價選擇說明
                    f.write(self._format_strike_selection(module_data))
                elif module_name in ['module7_long_call', 'module8_long_put', 'module9_short_call', 'module10_short_put']:
                    f.write(self._format_strategy_results(module_name, module_data))
                elif module_name == 'strategy_recommendations':
                    f.write(self._format_strategy_recommendations(module_data))
                # Phase 8: 日內交易模組
                elif module_name == 'module_vwap':
                    f.write(self._format_module_vwap(module_data))
                elif module_name == 'module_orb':
                    f.write(self._format_module_orb(module_data))
                elif module_name == 'module_0dte':
                    f.write(self._format_module_0dte(module_data))
                else:
                    # 通用格式
                    f.write(f"\n{module_name}:\n")
                    if isinstance(module_data, dict):
                        for key, value in module_data.items():
                            f.write(f"  {key}: {value}\n")
                    elif isinstance(module_data, list):
                        for i, item in enumerate(module_data, 1):
                            f.write(f"  場景 {i}: {item}\n")
                
                # 每處理完一個模塊後清理內存
                gc.collect()
            
            # 添加綜合建議區塊 (Requirements: 8.1, 8.2, 8.3, 8.4)
            f.write(self._format_consolidated_recommendation(calculation_results))
            gc.collect()
            
            # 添加數據來源摘要 (Requirements: 14.1, 14.2, 14.3, 14.4, 14.5)
            f.write(self._format_data_source_summary(raw_data, calculation_results, api_status))
            gc.collect()
        
        logger.info(f"* 文本報告已保存: {filepath}")
    
    def _format_decision_summary(self, ticker: str, raw_data: dict, calculation_results: dict) -> str:
        """
        格式化決策摘要 - 放在報告最前面幫助用戶快速做出交易決策
        
        包含:
        - 方向判斷 (看漲/看跌/中性)
        - IV 環境 (高/低/正常)
        - 推薦策略
        - 推薦行使價
        - 最大風險
        - 盈虧平衡點
        - 是否建議交易
        """
        report = "=" * 70 + "\n"
        report += "📋 決策摘要 (Quick Decision Summary)\n"
        report += "=" * 70 + "\n\n"
        
        # 確保 raw_data 不為 None
        if raw_data is None:
            raw_data = {}
        
        try:
            # ===== 1. 方向判斷 =====
            direction, direction_confidence, direction_reason = self._get_direction_judgment(calculation_results)
            
            direction_emoji = {'Bullish': '📈 看漲', 'Bearish': '📉 看跌', 'Neutral': '➖ 中性'}
            confidence_emoji = {'High': '🟢 高', 'Medium': '🟡 中', 'Low': '🔴 低'}
            
            report += f"🎯 方向判斷: {direction_emoji.get(direction, direction)}\n"
            report += f"   信心度: {confidence_emoji.get(direction_confidence, direction_confidence)}\n"
            report += f"   依據: {direction_reason}\n\n"
            
            # ===== 2. IV 環境 =====
            iv_env, iv_recommendation = self._get_iv_environment(calculation_results)
            
            iv_emoji = {'HIGH': '🔴 高IV環境', 'LOW': '🔵 低IV環境', 'NORMAL': '🟢 正常IV環境'}
            report += f"📊 IV 環境: {iv_emoji.get(iv_env, iv_env)}\n"
            report += f"   建議: {iv_recommendation}\n\n"
            
            # ===== 3. 推薦策略 =====
            recommended_strategy, strategy_reason = self._get_recommended_strategy(
                direction, direction_confidence, iv_env, calculation_results
            )
            
            report += f"💡 推薦策略: {recommended_strategy}\n"
            report += f"   理由: {strategy_reason}\n\n"
            
            # ===== 4. 推薦行使價 =====
            strike_info = self._get_recommended_strike(recommended_strategy, calculation_results)
            
            if strike_info:
                report += f"🎯 推薦行使價: ${strike_info['strike']:.2f}\n"
                if strike_info.get('score'):
                    report += f"   評分: {strike_info['score']:.1f}/100\n"
                if strike_info.get('reason'):
                    report += f"   理由: {strike_info['reason']}\n"
                report += "\n"
            
            # ===== 5. 風險分析 =====
            risk_info = self._get_risk_analysis(recommended_strategy, calculation_results, raw_data)
            
            if risk_info:
                report += f"⚠️ 風險分析:\n"
                if risk_info.get('max_loss'):
                    report += f"   最大風險: {risk_info['max_loss']}\n"
                if risk_info.get('breakeven'):
                    report += f"   盈虧平衡點: ${risk_info['breakeven']:.2f}\n"
                if risk_info.get('probability'):
                    report += f"   獲利概率: {risk_info['probability']}\n"
                report += "\n"
            
            # ===== 6. 交易建議 =====
            trade_recommendation, trade_reason = self._get_trade_recommendation(
                direction, direction_confidence, iv_env, calculation_results
            )
            
            if trade_recommendation == 'NO_TRADE':
                report += "🚫 交易建議: 【不建議交易】\n"
                report += f"   原因: {trade_reason}\n\n"
            elif trade_recommendation == 'CAUTION':
                report += "⚠️ 交易建議: 【謹慎交易】\n"
                report += f"   原因: {trade_reason}\n\n"
            else:
                report += "✅ 交易建議: 【可以交易】\n"
                report += f"   說明: {trade_reason}\n\n"
            
            # ===== 7. 快速參考 =====
            report += "─" * 70 + "\n"
            report += "📌 快速參考:\n"
            
            current_price = raw_data.get('current_price', 0)
            iv = raw_data.get('implied_volatility', 0)
            
            report += f"   當前股價: ${current_price:.2f}\n"
            report += f"   當前 IV: {iv:.2f}%\n"
            
            # 支撐阻力位 - 使用68%信心度（1個標準差，最佳風險/收益平衡）
            module1 = calculation_results.get('module1_support_resistance_multi', {})
            if module1 and module1.get('results', {}).get('68%'):
                r68 = module1['results']['68%']
                report += f"   68%信心區間: ${r68['support']:.2f} - ${r68['resistance']:.2f}\n"
            
            # 到期天數
            days = raw_data.get('days_to_expiration') or module1.get('days_to_expiration', 'N/A')
            report += f"   到期天數: {days}\n"
            
            report += "\n"
            
        except Exception as e:
            logger.warning(f"! 決策摘要生成失敗: {e}")
            report += f"⚠️ 無法生成完整決策摘要: {str(e)}\n\n"
        
        return report
    
    def _get_direction_judgment(self, calculation_results: dict) -> tuple:
        """
        獲取方向判斷
        
        返回: (direction, confidence, reason)
        """
        # 使用一致性檢查器獲取綜合方向
        try:
            consistency_result = self.consistency_checker.check_consistency(calculation_results)
            direction = consistency_result.consolidated_direction
            confidence = consistency_result.confidence
            
            # 生成原因說明
            adopted = consistency_result.adopted_modules
            if adopted:
                reason = f"基於 {', '.join(adopted)} 的綜合分析"
            else:
                reason = consistency_result.adoption_reason
            
            return direction, confidence, reason
        except Exception as e:
            logger.warning(f"方向判斷失敗: {e}")
            return 'Neutral', 'Low', '無法獲取方向判斷'
    
    def _get_iv_environment(self, calculation_results: dict) -> tuple:
        """
        獲取 IV 環境
        
        返回: (iv_status, recommendation)
        """
        # 優先使用 Module 23 動態 IV 閾值
        module23 = calculation_results.get('module23_dynamic_iv_threshold', {})
        if module23 and module23.get('iv_status'):
            iv_status = module23.get('iv_status', 'NORMAL')
            
            if iv_status == 'HIGH':
                recommendation = "考慮賣出期權策略 (Short Call/Put, Credit Spread)"
            elif iv_status == 'LOW':
                recommendation = "考慮買入期權策略 (Long Call/Put, Debit Spread)"
            else:
                recommendation = "可根據方向判斷選擇策略"
            
            return iv_status, recommendation
        
        # 備選: 使用 Module 18 IV Rank
        module18 = calculation_results.get('module18_historical_volatility', {})
        iv_rank = module18.get('iv_rank')
        
        if iv_rank is not None:
            if iv_rank > 70:
                return 'HIGH', "IV Rank 高，考慮賣出期權策略"
            elif iv_rank < 30:
                return 'LOW', "IV Rank 低，考慮買入期權策略"
            else:
                return 'NORMAL', "IV Rank 正常，可根據方向選擇策略"
        
        return 'NORMAL', "無 IV 數據，建議謹慎"
    
    def _get_recommended_strategy(self, direction: str, confidence: str, 
                                   iv_env: str, calculation_results: dict) -> tuple:
        """
        根據方向和 IV 環境推薦策略
        
        返回: (strategy_name, reason)
        """
        # 策略推薦矩陣
        strategy_matrix = {
            ('Bullish', 'HIGH'): ('Short Put', '看漲 + 高IV = 賣出 Put 收取高權利金'),
            ('Bullish', 'LOW'): ('Long Call', '看漲 + 低IV = 買入便宜的 Call'),
            ('Bullish', 'NORMAL'): ('Bull Call Spread', '看漲 + 正常IV = 牛市價差控制成本'),
            ('Bearish', 'HIGH'): ('Short Call', '看跌 + 高IV = 賣出 Call 收取高權利金'),
            ('Bearish', 'LOW'): ('Long Put', '看跌 + 低IV = 買入便宜的 Put'),
            ('Bearish', 'NORMAL'): ('Bear Put Spread', '看跌 + 正常IV = 熊市價差控制成本'),
            ('Neutral', 'HIGH'): ('Iron Condor / Short Straddle', '中性 + 高IV = 賣出波動率'),
            ('Neutral', 'LOW'): ('Long Straddle / Calendar Spread', '中性 + 低IV = 買入波動率'),
            ('Neutral', 'NORMAL'): ('觀望或 Calendar Spread', '方向不明確，等待更好機會'),
        }
        
        key = (direction, iv_env)
        if key in strategy_matrix:
            strategy, reason = strategy_matrix[key]
            
            # 如果信心度低，調整建議
            if confidence == 'Low':
                return f"{strategy} (小倉位)", f"{reason}；信心度低，建議小倉位試探"
            
            return strategy, reason
        
        return '觀望', '條件不明確，建議等待更好機會'
    
    def _get_recommended_strike(self, strategy: str, calculation_results: dict) -> dict:
        """
        獲取推薦行使價
        
        返回: {'strike': float, 'score': float, 'reason': str}
        """
        module22 = calculation_results.get('module22_optimal_strike', {})
        
        if not module22:
            return None
        
        # 根據策略選擇對應的行使價推薦
        strategy_mapping = {
            'Long Call': 'long_call',
            'Bull Call Spread': 'long_call',
            'Long Put': 'long_put',
            'Bear Put Spread': 'long_put',
            'Short Put': 'short_put',
            'Short Call': 'short_call',
        }
        
        # 找到匹配的策略類型
        strategy_key = None
        for key, value in strategy_mapping.items():
            if key in strategy:
                strategy_key = value
                break
        
        if not strategy_key:
            # 默認使用 ATM
            strike_selection = calculation_results.get('strike_selection', {})
            if strike_selection:
                return {
                    'strike': strike_selection.get('strike_price', 0),
                    'reason': 'ATM 行使價'
                }
            return None
        
        # 從 Module 22 獲取推薦
        strategy_data = module22.get(strategy_key, {})
        top_recommendations = strategy_data.get('top_recommendations', [])
        
        if top_recommendations:
            best = top_recommendations[0]
            return {
                'strike': best.get('strike', 0),
                'score': best.get('composite_score', 0),
                'reason': best.get('reason', 'Module 22 最佳推薦')
            }
        
        return None
    
    def _get_risk_analysis(self, strategy: str, calculation_results: dict, raw_data: dict) -> dict:
        """
        獲取風險分析
        
        返回: {'max_loss': str, 'breakeven': float, 'probability': str}
        """
        result = {}
        
        # 從策略模塊獲取風險數據
        if 'Long Call' in strategy:
            module7 = calculation_results.get('module7_long_call', {})
            if module7:
                scenarios = module7.get('scenarios', [])
                if scenarios:
                    # 最大損失 = 權利金
                    premium = scenarios[0].get('option_premium', 0)
                    result['max_loss'] = f"${premium * 100:.2f} (權利金)"
                    
                    # 盈虧平衡點
                    strike = scenarios[0].get('strike_price', 0)
                    result['breakeven'] = strike + premium
        
        elif 'Long Put' in strategy:
            module8 = calculation_results.get('module8_long_put', {})
            if module8:
                scenarios = module8.get('scenarios', [])
                if scenarios:
                    premium = scenarios[0].get('option_premium', 0)
                    result['max_loss'] = f"${premium * 100:.2f} (權利金)"
                    
                    strike = scenarios[0].get('strike_price', 0)
                    result['breakeven'] = strike - premium
        
        elif 'Short Put' in strategy:
            module10 = calculation_results.get('module10_short_put', {})
            if module10:
                scenarios = module10.get('scenarios', [])
                if scenarios:
                    strike = scenarios[0].get('strike_price', 0)
                    premium = scenarios[0].get('option_premium', 0)
                    result['max_loss'] = f"${(strike - premium) * 100:.2f} (股價歸零)"
                    result['breakeven'] = strike - premium
                    
                    # 獲取安全概率
                    module22 = calculation_results.get('module22_optimal_strike', {})
                    short_put_data = module22.get('short_put', {})
                    top_recs = short_put_data.get('top_recommendations', [])
                    if top_recs:
                        safety_prob = top_recs[0].get('safety_probability')
                        if safety_prob:
                            result['probability'] = f"{safety_prob:.1f}% 安全概率"
        
        elif 'Short Call' in strategy:
            module9 = calculation_results.get('module9_short_call', {})
            if module9:
                scenarios = module9.get('scenarios', [])
                if scenarios:
                    premium = scenarios[0].get('option_premium', 0)
                    strike = scenarios[0].get('strike_price', 0)
                    result['max_loss'] = "無限 (裸賣 Call)"
                    result['breakeven'] = strike + premium
        
        return result
    
    def _get_trade_recommendation(self, direction: str, confidence: str, 
                                   iv_env: str, calculation_results: dict) -> tuple:
        """
        獲取交易建議
        
        返回: ('TRADE'/'NO_TRADE'/'CAUTION', reason)
        """
        reasons_no_trade = []
        reasons_caution = []
        
        # 1. 檢查方向信心度
        if confidence == 'Low' and direction == 'Neutral':
            reasons_no_trade.append("方向不明確且信心度低")
        elif confidence == 'Low':
            reasons_caution.append("方向信心度低")
        
        # 2. 檢查模塊矛盾
        try:
            consistency_result = self.consistency_checker.check_consistency(calculation_results)
            if consistency_result.conflicts:
                reasons_caution.append(f"存在 {len(consistency_result.conflicts)} 個模塊信號矛盾")
        except:
            pass
        
        # 3. 檢查基本面
        module20 = calculation_results.get('module20_fundamental_health', {})
        health_score = module20.get('health_score', 100)
        if health_score < 40:
            reasons_no_trade.append(f"基本面健康分數過低 ({health_score}/100)")
        elif health_score < 60:
            reasons_caution.append(f"基本面健康分數偏低 ({health_score}/100)")
        
        # 4. 檢查動量
        module21 = calculation_results.get('module21_momentum_filter', {})
        momentum_score = module21.get('momentum_score', 0.5)
        
        # 如果方向與動量不一致
        if direction == 'Bullish' and momentum_score < 0.3:
            reasons_caution.append("看漲但動量轉弱")
        elif direction == 'Bearish' and momentum_score > 0.7:
            reasons_caution.append("看跌但動量強勁")
        
        # 5. 檢查 IV 環境與策略匹配
        # (已在策略推薦中考慮)
        
        # 生成最終建議
        if reasons_no_trade:
            return 'NO_TRADE', '；'.join(reasons_no_trade)
        elif reasons_caution:
            return 'CAUTION', '；'.join(reasons_caution)
        else:
            return 'TRADE', "各項指標正常，可根據推薦策略進行交易"
    
    def _format_module1_multi_confidence(self, ticker: str, results: dict) -> str:
        """格式化Module 1多信心度結果"""
        
        report = "┌─ Module 1: IV價格區間預測 (多信心度) ────────┐\n"
        report += "│\n"
        report += f"│ 股票: {ticker}\n"
        report += f"│ 當前價格: ${results['stock_price']:.2f}\n"
        
        # 顯示 IV 來源信息
        iv_value = results['implied_volatility']
        iv_source = results.get('iv_source', 'Market IV')
        if 'ATM IV' in iv_source:
            report += f"│ 隱含波動率: {iv_value:.1f}% (ATM IV - Module 17)\n"
        else:
            report += f"│ 隱含波動率: {iv_value:.1f}%\n"
        
        report += f"│ 到期天數: {results['days_to_expiration']}個交易日\n"
        report += "│\n"
        report += "│ 信心度 | Z值  | 波動幅度  | 支持位    | 阻力位    | 波動%\n"
        report += "│ ───────┼──────┼──────────┼──────────┼──────────┼──────\n"
        
        # 遍歷每個信心度
        for conf_level in ['68%', '80%', '90%', '95%', '99%']:
            if conf_level in results['results']:
                r = results['results'][conf_level]
                report += f"│ {conf_level:6} | {r['z_score']:.2f} | "
                report += f"±${r['price_move']:6.2f} | "
                report += f"${r['support']:7.2f} | "
                report += f"${r['resistance']:7.2f} | "
                report += f"±{r['move_percentage']:4.1f}%\n"
        
        report += "│\n"
        report += "│ 💡 解讀:\n"
        
        # 添加解讀說明
        if '68%' in results['results']:
            r68 = results['results']['68%']
            report += f"│ - 68%機率股價在 ${r68['support']:.2f}-${r68['resistance']:.2f} 範圍內\n"
        if '90%' in results['results']:
            r90 = results['results']['90%']
            report += f"│ - 90%機率股價在 ${r90['support']:.2f}-${r90['resistance']:.2f} 範圍內\n"
        if '99%' in results['results']:
            r99 = results['results']['99%']
            report += f"│ - 99%機率股價在 ${r99['support']:.2f}-${r99['resistance']:.2f} 範圍內\n"
        
        report += "│\n"
        report += "└────────────────────────────────────────────┘\n"
        
        return report
    
    def _format_module15_black_scholes(self, results: dict) -> str:
        """格式化 Black-Scholes 定價結果
        
        改進:
        - 到期時間以天數格式顯示（同時保留年化）
        - 短期期權警告（< 7 天）
        Requirements: 4.1, 4.2, 4.3
        """
        report = "\n┌─ Module 15: Black-Scholes 期權定價 ─────────┐\n"
        report += "│\n"
        
        days_to_expiry = None
        if 'parameters' in results:
            params = results['parameters']
            time_to_expiry_years = params.get('time_to_expiration', 0)
            # 將年化時間轉換為天數 (1年 = 365天)
            days_to_expiry = time_to_expiry_years * 365
            
            report += f"│ 參數設置:\n"
            report += f"│   股價: ${params.get('stock_price', 0):.2f}\n"
            report += f"│   行使價: ${params.get('strike_price', 0):.2f}\n"
            report += f"│   無風險利率: {params.get('risk_free_rate', 0)*100:.2f}%\n"
            # 同時顯示天數和年化格式 (Requirements 4.1, 4.2)
            report += f"│   到期時間: {days_to_expiry:.0f} 天 ({time_to_expiry_years:.4f} 年)\n"
            report += f"│   波動率: {params.get('volatility', 0)*100:.2f}%\n"
            
            # 短期期權警告 (Requirement 4.3)
            if days_to_expiry is not None and days_to_expiry < 7:
                report += "│\n"
                report += "│ ⚠️ 短期期權警告:\n"
                report += f"│   距到期僅 {days_to_expiry:.0f} 天，時間價值衰減加速\n"
                report += "│   Theta 影響顯著，請謹慎操作\n"
            report += "│\n"
        
        if 'call' in results:
            call = results['call']
            report += f"│ 📈 Call 期權:\n"
            report += f"│   理論價格: ${call.get('option_price', 0):.2f}\n"
            if 'd1' in call and float(call.get('d1', 0)) != 0.0:
                report += f"│   d1: {call.get('d1', 0):.6f}\n"
            if 'd2' in call and float(call.get('d2', 0)) != 0.0:
                report += f"│   d2: {call.get('d2', 0):.6f}\n"
            report += "│\n"
        
        if 'put' in results:
            put = results['put']
            report += f"│ 📉 Put 期權:\n"
            report += f"│   理論價格: ${put.get('option_price', 0):.2f}\n"
            if 'd1' in put and float(put.get('d1', 0)) != 0.0:
                report += f"│   d1: {put.get('d1', 0):.6f}\n"
            if 'd2' in put and float(put.get('d2', 0)) != 0.0:
                report += f"│   d2: {put.get('d2', 0):.6f}\n"
        
        report += "│\n"
        report += "│ 💡 說明: Black-Scholes 模型計算的理論價格\n"
        report += "└────────────────────────────────────────────┘\n"
        return report
    
    def _format_module16_greeks(self, results: dict) -> str:
        """
        格式化 Greeks 結果
        
        Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
        - 添加 Delta 方向性解讀
        - 添加 Theta 時間衰減總結
        - 添加 Vega 波動率敏感度總結
        - 添加 Gamma 高值警告
        - 添加整體風險評估
        """
        report = "\n┌─ Module 16: Greeks 風險指標 ─────────────────┐\n"
        report += "│\n"
        
        call_greeks = results.get('call', {})
        put_greeks = results.get('put', {})
        
        # Call Greeks 數據和解讀
        if call_greeks:
            call_delta = call_greeks.get('delta', 0)
            call_gamma = call_greeks.get('gamma', 0)
            call_theta = call_greeks.get('theta', 0)
            call_vega = call_greeks.get('vega', 0)
            call_rho = call_greeks.get('rho', 0)
            
            report += f"│ 📈 Call Greeks:\n"
            report += f"│   Delta:  {call_delta:8.4f}  (股價變動敏感度)\n"
            report += f"│   Gamma:  {call_gamma:8.6f}  (Delta 變化率)\n"
            report += f"│   Theta:  {call_theta:8.4f}  ($/天 時間衰減)\n"
            report += f"│   Vega:   {call_vega:8.4f}  (波動率敏感度)\n"
            report += f"│   Rho:    {call_rho:8.4f}  (利率敏感度)\n"
            report += "│\n"
            
            # Delta 解讀 (Requirements: 5.1)
            delta_interp = self._get_delta_interpretation(call_delta, 'call')
            report += f"│   📊 Delta 解讀:\n"
            report += f"│     方向: {delta_interp['direction']}\n"
            report += f"│     {delta_interp['probability_hint']}\n"
            report += f"│     {delta_interp['sensitivity']}\n"
            report += "│\n"
            
            # Theta 解讀 (Requirements: 5.2)
            theta_interp = self._get_theta_interpretation(call_theta)
            report += f"│   ⏱️ Theta 解讀:\n"
            report += f"│     每日衰減: {theta_interp['daily_decay']}\n"
            report += f"│     每週衰減: {theta_interp['weekly_decay']}\n"
            report += f"│     {theta_interp['decay_rate']}\n"
            report += f"│     建議: {theta_interp['strategy_hint']}\n"
            report += "│\n"
            
            # Vega 解讀 (Requirements: 5.3)
            vega_interp = self._get_vega_interpretation(call_vega)
            report += f"│   📈 Vega 解讀:\n"
            report += f"│     {vega_interp['sensitivity']}\n"
            report += f"│     {vega_interp['iv_impact']}\n"
            report += f"│     {vega_interp['risk_level']}\n"
            report += "│\n"
            
            # Gamma 警告 (Requirements: 5.4)
            gamma_warning = self._get_gamma_warning(call_gamma, call_delta)
            if gamma_warning['warning_level'] != '低':
                report += f"│   ⚡ Gamma 警告: {gamma_warning['warning_level']}\n"
                report += f"│     {gamma_warning['delta_change_hint']}\n"
                report += f"│     {gamma_warning['risk_description']}\n"
                report += f"│     建議: {gamma_warning['action_hint']}\n"
                report += "│\n"
        
        # Put Greeks 數據和解讀
        if put_greeks:
            put_delta = put_greeks.get('delta', 0)
            put_gamma = put_greeks.get('gamma', 0)
            put_theta = put_greeks.get('theta', 0)
            put_vega = put_greeks.get('vega', 0)
            put_rho = put_greeks.get('rho', 0)
            
            report += f"│ 📉 Put Greeks:\n"
            report += f"│   Delta:  {put_delta:8.4f}\n"
            report += f"│   Gamma:  {put_gamma:8.6f}\n"
            report += f"│   Theta:  {put_theta:8.4f}  ($/天)\n"
            report += f"│   Vega:   {put_vega:8.4f}\n"
            report += f"│   Rho:    {put_rho:8.4f}\n"
            report += "│\n"
            
            # Delta 解讀 (Requirements: 5.1)
            delta_interp = self._get_delta_interpretation(put_delta, 'put')
            report += f"│   📊 Delta 解讀:\n"
            report += f"│     方向: {delta_interp['direction']}\n"
            report += f"│     {delta_interp['probability_hint']}\n"
            report += f"│     {delta_interp['sensitivity']}\n"
            report += "│\n"
            
            # Theta 解讀 (Requirements: 5.2)
            theta_interp = self._get_theta_interpretation(put_theta)
            report += f"│   ⏱️ Theta 解讀:\n"
            report += f"│     每日衰減: {theta_interp['daily_decay']}\n"
            report += f"│     每週衰減: {theta_interp['weekly_decay']}\n"
            report += f"│     {theta_interp['decay_rate']}\n"
            report += "│\n"
            
            # Gamma 警告 (Requirements: 5.4)
            gamma_warning = self._get_gamma_warning(put_gamma, put_delta)
            if gamma_warning['warning_level'] != '低':
                report += f"│   ⚡ Gamma 警告: {gamma_warning['warning_level']}\n"
                report += f"│     {gamma_warning['delta_change_hint']}\n"
                report += f"│     建議: {gamma_warning['action_hint']}\n"
                report += "│\n"
        
        # 整體風險評估 (Requirements: 5.5)
        overall_assessment = self._get_overall_greeks_assessment(call_greeks, put_greeks)
        report += f"│ 🎯 整體風險評估:\n"
        report += f"│   風險等級: {overall_assessment['overall_risk']}\n"
        report += f"│\n"
        report += f"│   主要風險:\n"
        for risk in overall_assessment['key_risks']:
            report += f"│     • {risk}\n"
        report += f"│\n"
        report += f"│   建議:\n"
        for rec in overall_assessment['recommendations']:
            report += f"│     • {rec}\n"
        
        report += "│\n"
        report += "│ 💡 Greeks 快速參考:\n"
        report += "│   Delta: 股價每變動$1，期權價格變動\n"
        report += "│   Gamma: Delta 的變化速度\n"
        report += "│   Theta: 每天時間衰減的價值 ($/天)\n"
        report += "│   Vega: 波動率每變動1%，期權價格變動\n"
        report += "│   Rho: 利率每變動1%，期權價格變動\n"
        report += "└────────────────────────────────────────────┘\n"
        return report
    
    def _format_module17_implied_volatility(self, results: dict, historical_iv: float = None) -> str:
        """
        格式化隱含波動率結果
        
        增強功能:
        - Call/Put IV 比較分析
        - IV 偏斜警告（差異 > 5%）
        - 與歷史 IV 比較
        - 策略建議
        
        Requirements: 6.1, 6.2, 6.3, 6.4
        """
        report = "\n┌─ Module 17: 隱含波動率計算 ──────────────────┐\n"
        report += "│\n"
        
        call_iv = None
        put_iv = None
        
        if 'call' in results:
            call = results['call']
            converged = call.get('converged', False)
            call_iv = call.get('implied_volatility', 0)
            report += f"│ 📈 Call IV:\n"
            report += f"│   隱含波動率: {call_iv*100:.2f}%\n" if call_iv is not None else "│   隱含波動率: N/A\n"
            report += f"│   收斂狀態: {'* 成功' if converged else 'x 失敗'}\n"
            report += f"│   迭代次數: {call.get('iterations', 0)}\n"
            report += f"│   市場價格: ${call.get('market_price', 0):.2f}\n"
            report += "│\n"
        
        if 'put' in results:
            put = results['put']
            converged = put.get('converged', False)
            put_iv = put.get('implied_volatility', 0)
            report += f"│ 📉 Put IV:\n"
            report += f"│   隱含波動率: {put_iv*100:.2f}%\n" if put_iv is not None else "│   隱含波動率: N/A\n"
            report += f"│   收斂狀態: {'* 成功' if converged else 'x 失敗'}\n"
            report += f"│   迭代次數: {put.get('iterations', 0)}\n"
            report += f"│   市場價格: ${put.get('market_price', 0):.2f}\n"
            report += "│\n"
        
        # 添加 Call/Put IV 比較分析 (Requirements 6.1, 6.2)
        iv_comparison = self._get_iv_comparison_analysis(call_iv or 0, put_iv or 0)
        if iv_comparison:
            report += "│ 📊 Call/Put IV 比較分析:\n"
            report += f"│   {iv_comparison['comparison_text']}\n"
            if iv_comparison.get('has_skew'):
                report += f"│   ⚠️ IV 偏斜警告: {iv_comparison['skew_warning']}\n"
                report += f"│   可能原因: {iv_comparison['skew_reason']}\n"
            report += "│\n"
        
        # 添加與歷史 IV 比較 (Requirement 6.3)
        if historical_iv is not None and historical_iv > 0:
            current_iv = call_iv if call_iv is not None else put_iv
            if current_iv:
                historical_comparison = self._get_historical_iv_comparison(current_iv, historical_iv)
                report += "│ 📈 與歷史 IV 比較:\n"
                report += f"│   當前 IV: {current_iv*100:.2f}%\n" if current_iv is not None else "│   當前 IV: N/A\n"
                report += f"│   歷史 IV: {historical_iv*100:.2f}%\n" if historical_iv is not None else "│   歷史 IV: N/A\n"
                report += f"│   狀態: {historical_comparison['status']}\n"
                report += "│\n"
        
        # 添加策略建議 (Requirement 6.4)
        strategy_suggestion = self._get_iv_strategy_suggestion(call_iv, put_iv, historical_iv)
        if strategy_suggestion:
            report += "│ 💡 策略建議:\n"
            report += f"│   {strategy_suggestion['recommendation']}\n"
            report += f"│   原因: {strategy_suggestion['reason']}\n"
            report += "│\n"
        
        report += "│ 📝 說明: 從市場價格反推的隱含波動率\n"
        report += "│   用於判斷市場對未來波動的預期\n"
        report += "└────────────────────────────────────────────┘\n"
        return report
    
    def _get_iv_comparison_analysis(self, call_iv: float, put_iv: float) -> dict:
        """
        獲取 Call/Put IV 比較分析
        
        Requirements: 6.1, 6.2
        
        參數:
            call_iv: Call 期權隱含波動率（小數形式）
            put_iv: Put 期權隱含波動率（小數形式）
        
        返回:
            dict: 包含比較分析結果
        """
        if call_iv is None or put_iv is None or call_iv <= 0 or put_iv <= 0:
            return None
        
        # 計算差異百分比
        max_iv = max(call_iv, put_iv)
        diff_pct = abs(call_iv - put_iv) / max_iv * 100
        
        result = {
            'call_iv': call_iv,
            'put_iv': put_iv,
            'diff_pct': diff_pct,
            'has_skew': diff_pct > 5.0,
            'comparison_text': f"Call IV: {call_iv*100:.2f}% vs Put IV: {put_iv*100:.2f}% (差異: {diff_pct:.1f}%)"
        }
        
        # 判斷偏斜方向和原因
        if diff_pct > 5.0:
            if put_iv > call_iv:
                result['skew_warning'] = f"Put IV 高於 Call IV {diff_pct:.1f}%"
                result['skew_reason'] = "市場對下跌風險的擔憂較大，可能存在避險需求"
                result['skew_direction'] = 'put_premium'
            else:
                result['skew_warning'] = f"Call IV 高於 Put IV {diff_pct:.1f}%"
                result['skew_reason'] = "市場對上漲的預期較強，可能存在投機需求"
                result['skew_direction'] = 'call_premium'
        else:
            result['skew_warning'] = None
            result['skew_reason'] = None
            result['skew_direction'] = 'neutral'
        
        return result
    
    def _get_historical_iv_comparison(self, current_iv: float, historical_iv: float) -> dict:
        """
        獲取與歷史 IV 的比較
        
        Requirement: 6.3
        
        參數:
            current_iv: 當前 IV（小數形式）
            historical_iv: 歷史 IV（小數形式）
        
        返回:
            dict: 包含比較結果
        """
        if current_iv <= 0 or historical_iv <= 0:
            return {'status': '數據不可用', 'level': 'unknown'}
        
        ratio = current_iv / historical_iv
        
        if ratio > 1.2:
            return {
                'status': f'🔴 高於歷史 ({ratio:.2f}x) - IV 偏高',
                'level': 'high',
                'ratio': ratio
            }
        elif ratio < 0.8:
            return {
                'status': f'🔵 低於歷史 ({ratio:.2f}x) - IV 偏低',
                'level': 'low',
                'ratio': ratio
            }
        else:
            return {
                'status': f'🟢 接近歷史 ({ratio:.2f}x) - IV 正常',
                'level': 'normal',
                'ratio': ratio
            }
    
    def _get_iv_strategy_suggestion(self, call_iv: float, put_iv: float, historical_iv: float = None) -> dict:
        """
        根據 IV 水平提供策略建議
        
        Requirement: 6.4
        
        參數:
            call_iv: Call IV（小數形式）
            put_iv: Put IV（小數形式）
            historical_iv: 歷史 IV（小數形式，可選）
        
        返回:
            dict: 包含策略建議
        """
        current_iv = call_iv if call_iv and call_iv > 0 else put_iv
        if not current_iv or current_iv <= 0:
            return None
        
        # 基於 IV 水平的基本建議
        if current_iv > 0.5:  # IV > 50%
            base_suggestion = {
                'recommendation': '考慮賣出期權策略（如 Covered Call、Credit Spread）',
                'reason': f'當前 IV ({current_iv*100:.1f}%) 較高，期權權金豐厚'
            }
        elif current_iv < 0.2:  # IV < 20%
            base_suggestion = {
                'recommendation': '考慮買入期權策略（如 Long Call/Put、Debit Spread）',
                'reason': f'當前 IV ({current_iv*100:.1f}%) 較低，期權價格便宜'
            }
        else:
            base_suggestion = {
                'recommendation': '可根據方向性判斷選擇策略',
                'reason': f'當前 IV ({current_iv*100:.1f}%) 處於中性區間'
            }
        
        # 如果有歷史 IV，進一步調整建議
        if historical_iv and historical_iv > 0:
            ratio = current_iv / historical_iv
            if ratio > 1.2:
                base_suggestion['recommendation'] = '強烈建議賣出期權策略'
                base_suggestion['reason'] = f'當前 IV 高於歷史 {(ratio-1)*100:.0f}%，適合收取高額權金'
            elif ratio < 0.8:
                base_suggestion['recommendation'] = '強烈建議買入期權策略'
                base_suggestion['reason'] = f'當前 IV 低於歷史 {(1-ratio)*100:.0f}%，期權價格被低估'
        
        # 考慮 Call/Put IV 偏斜
        if call_iv and put_iv and call_iv > 0 and put_iv > 0:
            max_iv = max(call_iv, put_iv)
            diff_pct = abs(call_iv - put_iv) / max_iv * 100
            if diff_pct > 10:
                if put_iv > call_iv:
                    base_suggestion['recommendation'] += '；Put IV 偏高，可考慮賣出 Put'
                else:
                    base_suggestion['recommendation'] += '；Call IV 偏高，可考慮賣出 Call'
        
        return base_suggestion
    
    def _format_module18_historical_volatility(self, results: dict) -> str:
        """
        格式化歷史波動率結果
        
        Requirements 7.3, 7.4: 添加數據來源說明和數據不足警告
        """
        report = "\n┌─ Module 18: 歷史波動率分析 ──────────────────┐\n"
        report += "│\n"
        
        if 'hv_results' in results:
            report += "│ 📊 歷史波動率 (HV):\n"
            for window, data in sorted(results['hv_results'].items()):
                # 優先使用百分比形式，否則使用小數形式並轉換
                if isinstance(data, dict):
                    hv_percent = data.get('historical_volatility_percent', 0)
                    if hv_percent == 0:
                        hv = data.get('historical_volatility', 0)
                        hv_percent = hv * 100 if hv else 0
                else:
                    hv_percent = 0
                report += f"│   {window}天窗口: {hv_percent:6.2f}%\n"
            report += "│\n"
        
        if 'iv_hv_comparison' in results:
            comp = results['iv_hv_comparison']
            ratio = comp.get('iv_hv_ratio', comp.get('ratio', 0))
            assessment = comp.get('assessment', 'N/A')
            recommendation = comp.get('recommendation', 'N/A')
            
            report += f"│ 🔍 IV/HV 比率分析:\n"
            report += f"│   比率: {ratio:.2f}\n"
            report += f"│   評估: {assessment}\n"
            report += f"│   建議: {recommendation}\n"
            report += "│\n"
        
        # 新增: IV Rank 和 IV Percentile 顯示
        iv_rank = results.get('iv_rank')
        iv_percentile = results.get('iv_percentile')
        iv_recommendation = results.get('iv_recommendation', {})
        iv_rank_details = results.get('iv_rank_details', {})
        
        if iv_rank is not None or iv_percentile is not None:
            report += "│ 📈 IV Rank / IV Percentile 分析:\n"
            if iv_rank is not None:
                # IV Rank 可視化
                rank_bar = self._create_progress_bar(iv_rank, 100, 20)
                report += f"│   IV Rank: {iv_rank:.2f}%\n"
                report += f"│   {rank_bar}\n"
                
                # IV Rank 狀態判斷
                if iv_rank < 30:
                    rank_status = "🔵 低IV環境 - 適合買入期權"
                elif iv_rank > 70:
                    rank_status = "🔴 高IV環境 - 適合賣出期權"
                else:
                    rank_status = "🟢 正常IV環境 - 觀望"
                report += f"│   狀態: {rank_status}\n"
            
            if iv_percentile is not None:
                report += f"│   IV Percentile: {iv_percentile:.2f}%\n"
            report += "│\n"
            
            # Requirements 7.3: 顯示計算所用的 IV 數值和歷史範圍
            if iv_rank_details and not iv_rank_details.get('error'):
                report += "│ 📋 IV Rank 計算詳情:\n"
                iv_source = iv_rank_details.get('iv_source', 'N/A')
                current_iv_pct = iv_rank_details.get('current_iv_percent', 0)
                iv_min_pct = iv_rank_details.get('historical_iv_min_percent', 0)
                iv_max_pct = iv_rank_details.get('historical_iv_max_percent', 0)
                data_points = iv_rank_details.get('historical_data_points', 0)
                
                report += f"│   數據來源: {iv_source}\n"
                report += f"│   當前 IV: {current_iv_pct:.2f}%\n"
                report += f"│   52週 IV 範圍: {iv_min_pct:.2f}% - {iv_max_pct:.2f}%\n"
                report += f"│   歷史數據點: {data_points} 天\n"
                
                # Requirements 7.2: IV Rank 為 0% 時的數據驗證警告
                validation = iv_rank_details.get('validation', {})
                if not validation.get('is_valid', True):
                    report += "│\n"
                    report += "│ ⚠️ 數據驗證警告:\n"
                    for warning in validation.get('warnings', []):
                        report += f"│   ! {warning}\n"
                report += "│\n"
            
            # Requirements 7.4: 數據不足警告
            elif iv_rank_details and iv_rank_details.get('error'):
                report += "│ ⚠️ 數據不足警告:\n"
                error_msg = iv_rank_details.get('error', '未知錯誤')
                report += f"│   {error_msg}\n"
                if 'data_points_available' in iv_rank_details:
                    available = iv_rank_details.get('data_points_available', 0)
                    required = iv_rank_details.get('data_points_required', 200)
                    report += f"│   可用數據: {available} 天 (需要 {required} 天)\n"
                report += "│\n"
            
            # IV 交易建議
            if iv_recommendation:
                action = iv_recommendation.get('action', 'N/A')
                reason = iv_recommendation.get('reason', 'N/A')
                confidence = iv_recommendation.get('confidence', 'N/A')
                report += f"│ 💡 IV 交易建議:\n"
                report += f"│   建議: {action}\n"
                report += f"│   原因: {reason}\n"
                report += f"│   信心度: {confidence}\n"
                report += "│\n"
        else:
            # Requirements 7.4: 當 IV Rank 數據完全不可用時的警告
            report += "│ ⚠️ IV Rank 數據不可用:\n"
            if iv_rank_details and iv_rank_details.get('error'):
                report += f"│   原因: {iv_rank_details.get('error')}\n"
            else:
                report += "│   原因: 歷史 IV 數據不足，無法計算 IV Rank\n"
            report += "│   建議: 請確保有至少 200 天的歷史 IV 數據\n"
            report += "│\n"
        
        report += "│ 📖 解讀:\n"
        report += "│   IV Rank < 30%: IV 偏低，考慮買入期權\n"
        report += "│   IV Rank > 70%: IV 偏高，考慮賣出期權\n"
        report += "│   IV/HV > 1.2: IV 高估 | IV/HV < 0.8: IV 低估\n"
        report += "└────────────────────────────────────────────┘\n"
        return report
    
    def _create_progress_bar(self, value: float, max_value: float, width: int = 20) -> str:
        """創建進度條可視化"""
        if max_value <= 0:
            return "[" + "░" * width + "]"
        
        filled = int((value / max_value) * width)
        filled = max(0, min(filled, width))
        empty = width - filled
        
        return f"[{'█' * filled}{'░' * empty}] {value:.1f}%"
    
    def _format_module19_put_call_parity(self, results: dict) -> str:
        """格式化 Put-Call Parity 結果"""
        report = "\n┌─ Module 19: Put-Call Parity 驗證 ────────────┐\n"
        report += "│\n"
        
        if 'market_prices' in results:
            market = results['market_prices']
            deviation = market.get('deviation', 0)
            has_arb = market.get('arbitrage_opportunity', False)
            
            report += f"│ 📊 市場價格驗證:\n"
            report += f"│   偏離: ${abs(deviation):.4f}\n"
            report += f"│   套利機會: {'* 存在' if has_arb else 'x 不存在'}\n"
            
            if has_arb:
                profit = market.get('theoretical_profit', 0)
                strategy = market.get('strategy_recommendation', 'N/A')
                report += f"│   理論利潤: ${profit:.2f}\n"
                report += f"│   建議策略: {strategy}\n"
            report += "│\n"
        
        if 'theoretical_prices' in results:
            theory = results['theoretical_prices']
            deviation = theory.get('deviation', 0)
            has_arb = theory.get('arbitrage_opportunity', False)
            
            report += f"│ 🧮 理論價格驗證:\n"
            report += f"│   偏離: ${abs(deviation):.4f}\n"
            report += f"│   套利機會: {'* 存在' if has_arb else 'x 不存在'}\n"
        
        report += "│\n"
        report += "│ 💡 Put-Call Parity 公式:\n"
        report += "│   C - P = S - K×e^(-r×T)\n"
        report += "│   偏離過大表示存在套利機會\n"
        report += "└────────────────────────────────────────────┘\n"
        return report
    
    def _format_module3_arbitrage_spread(self, results: dict) -> str:
        """
        格式化 Module 3 定價偏離分析結果
        
        注意：這是「定價偏離分析」而非真正的套利機會判斷
        真正的套利需要同一時刻不同市場的價差，且會被高頻交易者瞬間抹平
        
        Requirements: 9.1, 9.2, 9.3, 9.4
        - 9.1: 清楚標示 IV 來源
        - 9.2: 添加 ATM IV 與 Market IV 差異解釋
        - 9.3: 提供明確的定價偏離結論
        - 9.4: 存在顯著偏離時提供交易策略建議
        """
        report = "\n┌─ Module 3: 定價偏離分析 ─────────────────────┐\n"
        report += "│\n"
        report += "│ ⚠️ 重要說明：\n"
        report += "│ 這是「定價偏離分析」，比較市場價與理論價的差異\n"
        report += "│ 不代表真正的套利機會（真正套利會被瞬間抹平）\n"
        report += "│\n"
        
        # 檢查是否跳過或錯誤
        if results.get('status') == 'skipped':
            report += f"│ ! 狀態: 跳過執行\n"
            report += f"│ 原因: {results.get('reason', 'N/A')}\n"
            report += "│\n"
            report += "└────────────────────────────────────────────┘\n"
            return report
        
        if results.get('status') == 'error':
            report += f"│ x 狀態: 執行錯誤\n"
            report += f"│ 原因: {results.get('reason', 'N/A')}\n"
            report += "│\n"
            report += "└────────────────────────────────────────────┘\n"
            return report
        
        # 正常結果
        market_price = results.get('market_price', 0)
        theoretical_price = results.get('theoretical_price', 0)
        spread = results.get('arbitrage_spread', 0)
        spread_pct = results.get('spread_percentage', 0)
        
        report += f"│ 💰 價格比較:\n"
        report += f"│   市場價格: ${market_price:.2f}\n"
        report += f"│   理論價格: ${theoretical_price:.2f}\n"
        report += f"│   理論偏離: ${spread:.2f} ({spread_pct:+.2f}%)\n"
        report += "│\n"
        
        # IV 來源和值顯示（Requirements 9.1 - 清楚標示 IV 來源）
        iv_used = results.get('iv_used')
        iv_used_percent = results.get('iv_used_percent')
        iv_source = results.get('iv_source')
        market_iv = results.get('market_iv')  # 整體市場 IV
        atm_iv = results.get('atm_iv')  # ATM IV
        
        report += f"│ 📈 波動率 (IV) 來源說明:\n"
        
        # 顯示使用的 IV（Requirements 9.1）
        if iv_used_percent is not None:
            report += f"│   ✓ 計算使用的 IV: {iv_used_percent:.2f}%\n"
        elif iv_used is not None:
            report += f"│   ✓ 計算使用的 IV: {iv_used*100:.2f}%\n"
        
        # 顯示 IV 來源（Requirements 9.1）
        if iv_source:
            iv_source_explanation = self._get_iv_source_explanation(iv_source)
            report += f"│   ✓ IV 來源: {iv_source}\n"
            if iv_source_explanation:
                report += f"│     {iv_source_explanation}\n"
        
        # 顯示 ATM IV 與 Market IV 的比較（Requirements 9.2）
        if atm_iv is not None and market_iv is not None:
            atm_iv_pct = atm_iv * 100 if atm_iv < 1 else atm_iv
            market_iv_pct = market_iv * 100 if market_iv < 1 else market_iv
            iv_diff = abs(atm_iv_pct - market_iv_pct)
            iv_diff_pct = (iv_diff / market_iv_pct * 100) if market_iv_pct > 0 else 0
            
            report += "│\n"
            report += f"│ 📊 ATM IV vs Market IV 比較:\n"
            report += f"│   ATM IV (Module 17): {atm_iv_pct:.2f}%\n"
            report += f"│   Market IV (整體): {market_iv_pct:.2f}%\n"
            report += f"│   差異: {iv_diff:.2f}% ({iv_diff_pct:.1f}%)\n"
            
            # 差異解釋（Requirements 9.2）
            if iv_diff_pct > 30:
                report += "│\n"
                report += "│   ⚠️ 差異解釋 (差異 > 30%):\n"
                report += "│   ATM IV 與 Market IV 差異較大，可能原因:\n"
                report += "│   1. 市場對近期事件（財報、重大消息）有預期\n"
                report += "│   2. 期權鏈流動性不均，ATM 期權定價更準確\n"
                report += "│   3. Market IV 可能包含 OTM 期權的偏斜影響\n"
                report += "│   → 建議以 ATM IV 為主要參考\n"
            elif iv_diff_pct > 10:
                report += "│\n"
                report += "│   ℹ️ 差異解釋 (差異 10-30%):\n"
                report += "│   ATM IV 與 Market IV 存在一定差異\n"
                report += "│   可能因波動率微笑/偏斜導致\n"
                report += "│   → ATM IV 通常更能反映真實市場預期\n"
        
        report += "│\n"
        
        # 數據來源標註
        source = results.get('theoretical_price_source', 'N/A')
        note = results.get('note', '')
        report += f"│ 📋 理論價計算來源:\n"
        report += f"│   {source}\n"
        if note:
            report += f"│   說明: {note}\n"
        report += "│\n"
        
        # IV 不一致警告顯示
        iv_warning = results.get('iv_warning')
        if iv_warning:
            report += f"│ ⚠️ IV 警告:\n"
            # 處理多個警告（用分號分隔）
            warnings = iv_warning.split("; ")
            for warning in warnings:
                report += f"│   {warning}\n"
            report += "│\n"
        
        # 明確的套利結論（Requirements 9.3）
        report += "│ ═══════════════════════════════════════════\n"
        report += "│ 📌 套利結論:\n"
        
        arbitrage_conclusion = self._get_arbitrage_conclusion(spread_pct, spread, market_price, theoretical_price)
        report += arbitrage_conclusion
        
        # 套利策略建議（Requirements 9.4）
        if abs(spread_pct) > 2:
            report += "│\n"
            report += "│ 💡 套利策略建議:\n"
            strategy_suggestion = self._get_arbitrage_strategy_suggestion(spread_pct, spread)
            report += strategy_suggestion
        
        report += "│\n"
        report += "│ ═══════════════════════════════════════════\n"
        report += "│ 📖 解讀說明:\n"
        report += "│   • 理論價使用 Black-Scholes 模型計算\n"
        report += "│   • 正價差: 市場價 > 理論價（期權可能高估）\n"
        report += "│   • 負價差: 市場價 < 理論價（期權可能低估）\n"
        report += "│   • 價差 < 2%: 市場定價合理，無套利空間\n"
        report += "│   • 價差 2-5%: 輕微偏離，需考慮交易成本\n"
        report += "│   • 價差 > 5%: 顯著偏離，可能存在套利機會\n"
        report += "└────────────────────────────────────────────┘\n"
        return report
    
    def _get_iv_source_explanation(self, iv_source: str) -> str:
        """
        獲取 IV 來源的解釋說明
        
        Requirements: 9.1 - 清楚標示 IV 來源
        """
        if not iv_source:
            return ""
        
        iv_source_lower = iv_source.lower()
        
        if 'atm' in iv_source_lower and 'module 17' in iv_source_lower:
            return "(從 ATM 期權市場價格反推的隱含波動率)"
        elif 'atm' in iv_source_lower:
            return "(平價期權的隱含波動率，最能反映市場預期)"
        elif 'market' in iv_source_lower:
            return "(整體市場隱含波動率，可能包含偏斜影響)"
        elif 'historical' in iv_source_lower or 'hv' in iv_source_lower:
            return "(基於歷史價格計算的波動率)"
        else:
            return ""
    
    def _get_arbitrage_conclusion(self, spread_pct: float, spread: float, 
                                   market_price: float, theoretical_price: float) -> str:
        """
        生成明確的套利結論
        
        Requirements: 9.3 - 提供明確的套利結論
        """
        conclusion = ""
        
        if abs(spread_pct) < 2:
            conclusion += "│   ✅ 結論: 【無套利機會】\n"
            conclusion += f"│   價差 {spread_pct:+.2f}% 在合理範圍內 (±2%)\n"
            conclusion += "│   市場定價合理，期權價格反映真實價值\n"
        elif abs(spread_pct) < 5:
            if spread_pct > 0:
                conclusion += "│   ⚠️ 結論: 【輕微高估，需評估】\n"
                conclusion += f"│   市場價 ${market_price:.2f} 高於理論價 ${theoretical_price:.2f}\n"
                conclusion += f"│   價差 {spread_pct:+.2f}%，扣除交易成本後可能無利可圖\n"
            else:
                conclusion += "│   ⚠️ 結論: 【輕微低估，需評估】\n"
                conclusion += f"│   市場價 ${market_price:.2f} 低於理論價 ${theoretical_price:.2f}\n"
                conclusion += f"│   價差 {spread_pct:+.2f}%，扣除交易成本後可能無利可圖\n"
        else:
            if spread_pct > 0:
                conclusion += "│   🔴 結論: 【有套利機會 - 期權高估】\n"
                conclusion += f"│   市場價 ${market_price:.2f} 顯著高於理論價 ${theoretical_price:.2f}\n"
                conclusion += f"│   價差 {spread_pct:+.2f}%，存在賣出套利空間\n"
            else:
                conclusion += "│   🟢 結論: 【有套利機會 - 期權低估】\n"
                conclusion += f"│   市場價 ${market_price:.2f} 顯著低於理論價 ${theoretical_price:.2f}\n"
                conclusion += f"│   價差 {spread_pct:+.2f}%，存在買入套利空間\n"
        
        return conclusion
    
    def _get_arbitrage_strategy_suggestion(self, spread_pct: float, spread: float) -> str:
        """
        生成具體的套利策略建議
        
        Requirements: 9.4 - 存在套利機會時提供具體的套利策略建議
        """
        suggestion = ""
        
        if spread_pct > 5:
            # 期權高估，建議賣出策略
            suggestion += "│   【期權高估策略】\n"
            suggestion += "│   1. 賣出 Call (Sell Call):\n"
            suggestion += "│      - 收取權利金，等待期權價值回歸\n"
            suggestion += "│      - 風險: 股價大漲時虧損無限\n"
            suggestion += "│   2. Bear Call Spread (熊市看漲價差):\n"
            suggestion += "│      - 賣出較低行使價 Call + 買入較高行使價 Call\n"
            suggestion += "│      - 限制最大虧損，適合風險控制\n"
            suggestion += "│   3. 合成空頭 + 買入正股:\n"
            suggestion += "│      - 如果合成空頭價格 > 正股，可套利\n"
        elif spread_pct > 2:
            suggestion += "│   【輕微高估策略】\n"
            suggestion += "│   1. 觀望為主，等待更好機會\n"
            suggestion += "│   2. 如要操作，建議使用價差策略限制風險\n"
            suggestion += "│   3. 注意交易成本可能吃掉利潤\n"
        elif spread_pct < -5:
            # 期權低估，建議買入策略
            suggestion += "│   【期權低估策略】\n"
            suggestion += "│   1. 買入 Call (Long Call):\n"
            suggestion += "│      - 以低於理論價買入，等待價值回歸\n"
            suggestion += "│      - 風險: 最大虧損為權利金\n"
            suggestion += "│   2. Bull Call Spread (牛市看漲價差):\n"
            suggestion += "│      - 買入較低行使價 Call + 賣出較高行使價 Call\n"
            suggestion += "│      - 降低成本，限制最大利潤\n"
            suggestion += "│   3. 合成多頭 vs 正股:\n"
            suggestion += "│      - 如果合成多頭價格 < 正股，可套利\n"
        elif spread_pct < -2:
            suggestion += "│   【輕微低估策略】\n"
            suggestion += "│   1. 可考慮小倉位買入\n"
            suggestion += "│   2. 使用價差策略降低成本\n"
            suggestion += "│   3. 注意交易成本可能吃掉利潤\n"
        
        # 通用風險提示
        suggestion += "│\n"
        suggestion += "│   ⚠️ 風險提示:\n"
        suggestion += "│   • 套利機會可能因市場變化快速消失\n"
        suggestion += "│   • 需考慮買賣價差、佣金等交易成本\n"
        suggestion += "│   • 理論價基於模型假設，實際可能有偏差\n"
        
        return suggestion
    
    def _format_module13_position_analysis(self, results: dict) -> str:
        """
        格式化 Module 13 倉位分析結果
        
        Requirements: 2.1, 2.2, 2.3, 2.4 - 分別顯示 Call 和 Put 數據，
        顯示 Put/Call 比率，處理數據不可用情況
        """
        report = "\n┌─ Module 13: 倉位分析（含所有權結構）────────┐\n"
        report += "│\n"
        
        # Call/Put 分離倉位數據 (Requirements: 2.1, 2.2)
        report += f"│ 📊 期權倉位數據:\n"
        
        # Call 數據
        call_volume = results.get('call_volume')
        call_oi = results.get('call_open_interest')
        report += f"│   📈 Call 期權:\n"
        report += f"│      成交量: {self._format_position_value(call_volume)}\n"
        report += f"│      未平倉量: {self._format_position_value(call_oi)}\n"
        
        # Put 數據
        put_volume = results.get('put_volume')
        put_oi = results.get('put_open_interest')
        report += f"│   📉 Put 期權:\n"
        report += f"│      成交量: {self._format_position_value(put_volume)}\n"
        report += f"│      未平倉量: {self._format_position_value(put_oi)}\n"
        
        # Put/Call 比率 (Requirements: 2.3)
        put_call_ratio = results.get('put_call_ratio')
        if put_call_ratio is not None:
            report += f"│   📊 Put/Call 比率: {put_call_ratio:.4f}\n"
            # 添加 Put/Call 比率解讀
            if put_call_ratio > 1.0:
                report += f"│      ⚠️ 看跌傾向（Put > Call）\n"
            elif put_call_ratio < 0.7:
                report += f"│      ✓ 看漲傾向（Call > Put）\n"
            else:
                report += f"│      中性（Put/Call 接近平衡）\n"
        else:
            report += f"│   📊 Put/Call 比率: 數據不可用\n"
        
        report += "│\n"
        
        # 總計數據
        report += f"│ 📋 總計:\n"
        if 'volume' in results:
            report += f"│   總成交量: {results.get('volume', 0):,}\n"
        if 'open_interest' in results:
            report += f"│   總未平倉量: {results.get('open_interest', 0):,}\n"
        if 'volume_oi_ratio' in results:
            report += f"│   成交量/未平倉比: {results.get('volume_oi_ratio', 0):.2f}\n"
        report += "│\n"
        
        # Finviz 所有權結構數據
        has_finviz_data = False
        if 'insider_ownership' in results or 'institutional_ownership' in results or 'short_float' in results:
            has_finviz_data = True
            report += f"│ 🏢 所有權結構 (Finviz):\n"
            
            if 'insider_ownership' in results:
                insider = results.get('insider_ownership', 0)
                insider_note = results.get('insider_note', '')
                report += f"│   內部人持股: {insider:.2f}%\n"
                if insider_note:
                    report += f"│   {insider_note}\n"
            
            if 'institutional_ownership' in results:
                inst = results.get('institutional_ownership', 0)
                inst_note = results.get('inst_note', '')
                report += f"│   機構持股: {inst:.2f}%\n"
                if inst_note:
                    report += f"│   {inst_note}\n"
            
            if 'short_float' in results:
                short = results.get('short_float', 0)
                short_note = results.get('short_note', '')
                report += f"│   做空比例: {short:.2f}%\n"
                if short_note:
                    report += f"│   {short_note}\n"
            
            report += "│\n"
        
        # 成交量分析
        if 'volume_vs_avg' in results:
            vol_ratio = results.get('volume_vs_avg', 0)
            vol_note = results.get('volume_note', '')
            report += f"│ 📈 成交量分析:\n"
            report += f"│   成交量/平均比: {vol_ratio:.2f}x\n"
            if vol_note:
                report += f"│   {vol_note}\n"
            report += "│\n"
        
        # 倉位評估
        if 'position_assessment' in results:
            report += f"│ 💡 倉位評估: {results.get('position_assessment', 'N/A')}\n"
        
        if has_finviz_data:
            report += "│\n"
            report += "│ 📌 數據來源: Finviz (所有權結構數據)\n"
        
        report += "└────────────────────────────────────────────┘\n"
        return report
    
    def _format_position_value(self, value) -> str:
        """
        格式化倉位數值，處理數據不可用情況
        
        Requirements: 2.4 - WHEN 未平倉量數據不可用 THEN Report_Generator 
                           SHALL 明確標示「數據不可用」而非顯示 0
        """
        if value is None:
            return "數據不可用"
        return f"{value:,}"
    
    def _get_rsi_interpretation(self, rsi: float) -> dict:
        """
        獲取 RSI 解讀
        
        Requirements: 3.2, 3.3, 3.4
        
        返回:
            dict: {
                'status': str,  # '超買', '超賣', '中性'
                'description': str,  # 詳細描述
                'action_hint': str  # 操作提示
            }
        """
        if rsi is None:
            return {
                'status': '數據不可用',
                'description': 'RSI 數據不可用',
                'action_hint': '無法提供建議'
            }
        
        if rsi > 70:
            return {
                'status': '超買',
                'description': f'RSI {rsi:.2f} > 70，股票處於超買狀態',
                'action_hint': '可能回調，謹慎追高，考慮獲利了結或等待回調'
            }
        elif rsi < 30:
            return {
                'status': '超賣',
                'description': f'RSI {rsi:.2f} < 30，股票處於超賣狀態',
                'action_hint': '可能反彈，關注買入機會，但需確認底部信號'
            }
        else:
            return {
                'status': '中性',
                'description': f'RSI {rsi:.2f} 在 30-70 範圍內，動量正常',
                'action_hint': '無明顯超買超賣信號，可根據其他指標判斷'
            }
    
    def _get_atr_interpretation(self, atr: float, stock_price: float) -> dict:
        """
        獲取 ATR 實際應用解讀（止損距離建議）
        
        Requirements: 3.5
        
        返回:
            dict: {
                'atr_percentage': float,  # ATR 佔股價百分比
                'stop_loss_suggestion': str,  # 止損建議
                'position_sizing_hint': str  # 倉位建議
            }
        """
        if atr is None or stock_price is None or stock_price <= 0:
            return {
                'atr_percentage': None,
                'stop_loss_suggestion': '數據不可用',
                'position_sizing_hint': '無法計算'
            }
        
        atr_percentage = (atr / stock_price) * 100
        
        # 止損距離建議（通常使用 1.5-2 倍 ATR）
        stop_loss_1x = atr
        stop_loss_1_5x = atr * 1.5
        stop_loss_2x = atr * 2.0
        
        # 根據 ATR 百分比判斷波動性
        if atr_percentage > 5:
            volatility_level = '高波動'
            position_hint = '建議減少倉位，波動較大'
        elif atr_percentage > 2:
            volatility_level = '中等波動'
            position_hint = '正常倉位，注意風險管理'
        else:
            volatility_level = '低波動'
            position_hint = '可適當增加倉位，波動較小'
        
        return {
            'atr_percentage': atr_percentage,
            'stop_loss_1x': stop_loss_1x,
            'stop_loss_1_5x': stop_loss_1_5x,
            'stop_loss_2x': stop_loss_2x,
            'volatility_level': volatility_level,
            'stop_loss_suggestion': f'建議止損距離: ${stop_loss_1_5x:.2f}-${stop_loss_2x:.2f} (1.5-2倍ATR)',
            'position_sizing_hint': position_hint
        }
    
    def _get_delta_interpretation(self, delta: float, option_type: str = 'call') -> dict:
        """
        獲取 Delta 方向性解讀
        
        Requirements: 5.1
        
        參數:
            delta: Delta 值
            option_type: 'call' 或 'put'
        
        返回:
            dict: {
                'direction': str,  # 方向性描述
                'probability_hint': str,  # 到期價內概率提示
                'hedge_ratio': str,  # 對沖比率說明
                'sensitivity': str  # 敏感度說明
            }
        """
        if delta is None:
            return {
                'direction': '數據不可用',
                'probability_hint': '無法計算',
                'hedge_ratio': '無法計算',
                'sensitivity': '無法計算'
            }
        
        abs_delta = abs(delta)
        
        # 方向性解讀
        if option_type.lower() == 'call':
            if delta > 0.7:
                direction = '強看漲 - 深度價內'
                probability_hint = f'約 {abs_delta*100:.0f}% 概率到期價內'
            elif delta > 0.5:
                direction = '看漲 - 價內或接近平價'
                probability_hint = f'約 {abs_delta*100:.0f}% 概率到期價內'
            elif delta > 0.3:
                direction = '輕微看漲 - 接近平價'
                probability_hint = f'約 {abs_delta*100:.0f}% 概率到期價內'
            else:
                direction = '弱看漲 - 價外'
                probability_hint = f'約 {abs_delta*100:.0f}% 概率到期價內'
        else:  # put
            if delta < -0.7:
                direction = '強看跌 - 深度價內'
                probability_hint = f'約 {abs_delta*100:.0f}% 概率到期價內'
            elif delta < -0.5:
                direction = '看跌 - 價內或接近平價'
                probability_hint = f'約 {abs_delta*100:.0f}% 概率到期價內'
            elif delta < -0.3:
                direction = '輕微看跌 - 接近平價'
                probability_hint = f'約 {abs_delta*100:.0f}% 概率到期價內'
            else:
                direction = '弱看跌 - 價外'
                probability_hint = f'約 {abs_delta*100:.0f}% 概率到期價內'
        
        # 對沖比率
        hedge_shares = int(abs_delta * 100)
        hedge_ratio = f'每 1 份期權需 {hedge_shares} 股對沖'
        
        # 敏感度說明
        sensitivity = f'股價每變動 $1，期權價格變動約 ${abs_delta:.2f}'
        
        return {
            'direction': direction,
            'probability_hint': probability_hint,
            'hedge_ratio': hedge_ratio,
            'sensitivity': sensitivity
        }
    
    def _get_theta_interpretation(self, theta: float, option_price: float = None) -> dict:
        """
        獲取 Theta 時間衰減影響總結
        
        Requirements: 5.2
        
        參數:
            theta: Theta 值（每天損失的美元數）
            option_price: 期權價格（用於計算衰減百分比）
        
        返回:
            dict: {
                'daily_decay': str,  # 每日衰減
                'weekly_decay': str,  # 每週衰減
                'decay_rate': str,  # 衰減速度評估
                'strategy_hint': str  # 策略建議
            }
        """
        if theta is None:
            return {
                'daily_decay': '數據不可用',
                'weekly_decay': '數據不可用',
                'decay_rate': '無法評估',
                'strategy_hint': '無法提供建議'
            }
        
        # 計算每日和每週衰減
        daily_decay = abs(theta)
        weekly_decay = daily_decay * 5  # 交易日
        
        # 計算衰減百分比（如果有期權價格）
        if option_price and option_price > 0:
            daily_pct = (daily_decay / option_price) * 100
            if daily_pct > 2:
                decay_rate = '快速衰減 - 時間價值流失嚴重'
                strategy_hint = '買方不利，考慮賣出或選擇更長期限'
            elif daily_pct > 1:
                decay_rate = '中等衰減 - 需注意時間價值'
                strategy_hint = '關注到期時間，避免持有過久'
            else:
                decay_rate = '緩慢衰減 - 時間價值相對穩定'
                strategy_hint = '時間壓力較小，可持有觀察'
        else:
            if daily_decay > 0.5:
                decay_rate = '高衰減 - 每日損失較大'
                strategy_hint = '買方需謹慎，賣方有利'
            elif daily_decay > 0.1:
                decay_rate = '中等衰減'
                strategy_hint = '正常時間衰減範圍'
            else:
                decay_rate = '低衰減'
                strategy_hint = '時間價值損失較小'
        
        return {
            'daily_decay': f'${daily_decay:.4f}/天',
            'weekly_decay': f'${weekly_decay:.4f}/週',
            'decay_rate': decay_rate,
            'strategy_hint': strategy_hint
        }
    
    def _get_vega_interpretation(self, vega: float, current_iv: float = None) -> dict:
        """
        獲取 Vega 波動率敏感度總結
        
        Requirements: 5.3
        
        參數:
            vega: Vega 值
            current_iv: 當前隱含波動率（用於評估）
        
        返回:
            dict: {
                'sensitivity': str,  # 敏感度說明
                'iv_impact': str,  # IV 變化影響
                'risk_level': str,  # 波動率風險等級
                'strategy_hint': str  # 策略建議
            }
        """
        if vega is None:
            return {
                'sensitivity': '數據不可用',
                'iv_impact': '無法計算',
                'risk_level': '無法評估',
                'strategy_hint': '無法提供建議'
            }
        
        # 敏感度說明
        sensitivity = f'IV 每變動 1%，期權價格變動約 ${vega:.4f}'
        
        # IV 變化影響
        iv_up_5 = vega * 5
        iv_down_5 = -vega * 5
        iv_impact = f'IV +5%: +${iv_up_5:.2f} | IV -5%: ${iv_down_5:.2f}'
        
        # 風險等級評估
        if vega > 0.5:
            risk_level = '高波動率敏感 - IV 變化影響大'
            if current_iv and current_iv > 0.4:  # 40%
                strategy_hint = '當前 IV 較高，買入期權需謹慎 IV 回落風險'
            elif current_iv and current_iv < 0.2:  # 20%
                strategy_hint = '當前 IV 較低，買入期權可能受益於 IV 上升'
            else:
                strategy_hint = '關注 IV 變化，可能顯著影響期權價值'
        elif vega > 0.2:
            risk_level = '中等波動率敏感'
            strategy_hint = 'IV 變化有一定影響，需持續關注'
        else:
            risk_level = '低波動率敏感'
            strategy_hint = 'IV 變化影響較小，可專注於方向性判斷'
        
        return {
            'sensitivity': sensitivity,
            'iv_impact': iv_impact,
            'risk_level': risk_level,
            'strategy_hint': strategy_hint
        }
    
    def _get_gamma_warning(self, gamma: float, delta: float = None) -> dict:
        """
        獲取 Gamma 警告（當 Gamma 較高時警告 Delta 可能快速變化）
        
        Requirements: 5.4
        
        參數:
            gamma: Gamma 值
            delta: 當前 Delta 值（用於評估變化幅度）
        
        返回:
            dict: {
                'warning_level': str,  # 警告等級
                'delta_change_hint': str,  # Delta 變化提示
                'risk_description': str,  # 風險描述
                'action_hint': str  # 操作建議
            }
        """
        if gamma is None:
            return {
                'warning_level': '無',
                'delta_change_hint': '數據不可用',
                'risk_description': '無法評估',
                'action_hint': '無法提供建議'
            }
        
        # Gamma 閾值判斷
        # 一般來說，ATM 期權的 Gamma 最高，約 0.01-0.05
        if gamma > 0.05:
            warning_level = '⚠️ 高'
            delta_change_hint = f'股價每變動 $1，Delta 變化約 {gamma:.4f}'
            risk_description = 'Delta 可能快速變化，期權價格波動加劇'
            action_hint = '需頻繁調整對沖，或考慮減少倉位'
        elif gamma > 0.02:
            warning_level = '中等'
            delta_change_hint = f'股價每變動 $1，Delta 變化約 {gamma:.4f}'
            risk_description = 'Delta 變化速度適中'
            action_hint = '定期檢查對沖比率'
        else:
            warning_level = '低'
            delta_change_hint = f'股價每變動 $1，Delta 變化約 {gamma:.4f}'
            risk_description = 'Delta 相對穩定'
            action_hint = '對沖調整頻率可較低'
        
        # 如果提供了 Delta，計算股價變動 $5 後的 Delta 變化
        if delta is not None:
            delta_after_5up = delta + (gamma * 5)
            delta_after_5down = delta - (gamma * 5)
            delta_change_hint += f'\n│     股價 +$5: Delta → {delta_after_5up:.4f}'
            delta_change_hint += f'\n│     股價 -$5: Delta → {delta_after_5down:.4f}'
        
        return {
            'warning_level': warning_level,
            'delta_change_hint': delta_change_hint,
            'risk_description': risk_description,
            'action_hint': action_hint
        }
    
    def _get_overall_greeks_assessment(self, call_greeks: dict = None, put_greeks: dict = None) -> dict:
        """
        獲取整體 Greeks 風險評估總結
        
        Requirements: 5.5
        
        參數:
            call_greeks: Call 期權的 Greeks 字典
            put_greeks: Put 期權的 Greeks 字典
        
        返回:
            dict: {
                'overall_risk': str,  # 整體風險等級
                'key_risks': list,  # 主要風險點
                'recommendations': list  # 建議
            }
        """
        key_risks = []
        recommendations = []
        risk_score = 0  # 0-10 分
        
        # 分析 Call Greeks
        if call_greeks:
            delta = call_greeks.get('delta', 0)
            gamma = call_greeks.get('gamma', 0)
            theta = call_greeks.get('theta', 0)
            vega = call_greeks.get('vega', 0)
            
            # Delta 風險
            if abs(delta) > 0.8:
                key_risks.append('Call Delta 極高，方向性風險大')
                risk_score += 2
            
            # Gamma 風險
            if gamma > 0.05:
                key_risks.append('Call Gamma 高，Delta 可能快速變化')
                risk_score += 2
            
            # Theta 風險
            if theta < -0.5:
                key_risks.append('Call Theta 衰減快，時間價值流失嚴重')
                risk_score += 1
            
            # Vega 風險
            if vega > 0.5:
                key_risks.append('Call Vega 高，對 IV 變化敏感')
                risk_score += 1
        
        # 分析 Put Greeks
        if put_greeks:
            delta = put_greeks.get('delta', 0)
            gamma = put_greeks.get('gamma', 0)
            theta = put_greeks.get('theta', 0)
            vega = put_greeks.get('vega', 0)
            
            # Delta 風險
            if abs(delta) > 0.8:
                key_risks.append('Put Delta 極高，方向性風險大')
                risk_score += 2
            
            # Gamma 風險
            if gamma > 0.05:
                key_risks.append('Put Gamma 高，Delta 可能快速變化')
                risk_score += 2
            
            # Theta 風險
            if theta < -0.5:
                key_risks.append('Put Theta 衰減快，時間價值流失嚴重')
                risk_score += 1
            
            # Vega 風險
            if vega > 0.5:
                key_risks.append('Put Vega 高，對 IV 變化敏感')
                risk_score += 1
        
        # 生成建議
        if risk_score >= 6:
            overall_risk = '⚠️ 高風險'
            recommendations.append('建議減少倉位或增加對沖')
            recommendations.append('密切監控市場變化')
        elif risk_score >= 3:
            overall_risk = '中等風險'
            recommendations.append('定期檢查倉位和對沖比率')
            recommendations.append('關注 IV 和時間衰減')
        else:
            overall_risk = '低風險'
            recommendations.append('風險可控，可維持現有策略')
        
        if not key_risks:
            key_risks.append('無明顯風險警告')
        
        return {
            'overall_risk': overall_risk,
            'risk_score': risk_score,
            'key_risks': key_risks,
            'recommendations': recommendations
        }
    
    def _format_module14_monitoring_posts(self, results: dict) -> str:
        """
        格式化 Module 14 監察崗位結果
        
        Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
        - 添加 RSI 數值顯示
        - 添加 RSI 解讀（超買/超賣/中性）
        - 添加 ATR 實際應用解讀（止損距離建議）
        """
        report = "\n┌─ Module 14: 12監察崗位（含 RSI/Beta）────────┐\n"
        report += "│\n"
        
        # 獲取股價用於 ATR 計算
        stock_price = results.get('stock_price', 0)
        
        # 基本監察數據
        report += f"│ 🔍 監察指標:\n"
        if 'delta' in results:
            report += f"│   Delta: {results.get('delta', 0):.4f}\n"
        if 'iv' in results:
            report += f"│   隱含波動率: {results.get('iv', 0):.2f}%\n"
        if 'atr' in results:
            atr = results.get('atr', 0)
            report += f"│   ATR: ${atr:.2f}\n"
        if 'bid_ask_spread' in results:
            report += f"│   買賣價差: ${results.get('bid_ask_spread', 0):.2f}\n"
        report += "│\n"
        
        # RSI 數值和解讀 (Requirements: 3.1, 3.2, 3.3, 3.4)
        rsi = results.get('rsi')
        if rsi is not None:
            rsi_interp = self._get_rsi_interpretation(rsi)
            report += f"│ 📊 RSI 分析:\n"
            report += f"│   RSI 數值: {rsi:.2f}\n"
            report += f"│   狀態: {rsi_interp['status']}\n"
            report += f"│   解讀: {rsi_interp['description']}\n"
            report += f"│   建議: {rsi_interp['action_hint']}\n"
            report += "│\n"
        else:
            # 檢查是否有 rsi_status（舊格式兼容）
            rsi_status = results.get('rsi_status', '')
            if rsi_status:
                report += f"│ 📊 RSI 分析:\n"
                report += f"│   {rsi_status}\n"
                report += "│\n"
        
        # ATR 實際應用解讀 (Requirements: 3.5)
        atr = results.get('atr')
        if atr is not None and stock_price > 0:
            atr_interp = self._get_atr_interpretation(atr, stock_price)
            report += f"│ 📏 ATR 止損建議:\n"
            report += f"│   ATR: ${atr:.2f} ({atr_interp['atr_percentage']:.2f}% 股價)\n"
            report += f"│   波動性: {atr_interp['volatility_level']}\n"
            report += f"│   1倍ATR止損: ${atr_interp['stop_loss_1x']:.2f}\n"
            report += f"│   1.5倍ATR止損: ${atr_interp['stop_loss_1_5x']:.2f}\n"
            report += f"│   2倍ATR止損: ${atr_interp['stop_loss_2x']:.2f}\n"
            report += f"│   {atr_interp['stop_loss_suggestion']}\n"
            report += f"│   倉位建議: {atr_interp['position_sizing_hint']}\n"
            report += "│\n"
        
        # Beta 數據
        if 'beta' in results:
            beta = results.get('beta', 0)
            beta_status = results.get('beta_status', '')
            report += f"│ 📈 Beta 分析:\n"
            report += f"│   Beta: {beta:.2f}\n"
            if beta > 1:
                report += f"│   解讀: 波動性高於市場，風險較大\n"
            elif beta < 1:
                report += f"│   解讀: 波動性低於市場，相對穩定\n"
            else:
                report += f"│   解讀: 波動性與市場同步\n"
            if beta_status:
                report += f"│   {beta_status}\n"
            report += "│\n"
        
        # 風險評估
        if 'risk_level' in results:
            report += f"│ ⚠️ 風險等級: {results.get('risk_level', 'N/A')}\n"
        
        if 'monitoring_alerts' in results:
            alerts = results.get('monitoring_alerts', [])
            if alerts:
                report += f"│ 🚨 監察警報:\n"
                for alert in alerts:
                    report += f"│   • {alert}\n"
        
        # 數據來源
        report += "│\n"
        report += "│ 📌 數據來源: Finviz (RSI/Beta 數據)\n"
        
        # 簡化的解讀說明
        report += "│\n"
        report += "│ 💡 快速參考:\n"
        report += "│   RSI > 70: 超買區域 | RSI < 30: 超賣區域\n"
        report += "│   Beta > 1: 高波動 | Beta < 1: 低波動\n"
        report += "│   止損建議: 使用 1.5-2 倍 ATR 設置止損點\n"
        report += "└────────────────────────────────────────────┘\n"
        return report
    
    def _format_module20_fundamental_health(self, results: dict) -> str:
        """格式化 Module 20 基本面健康檢查結果
        
        改進內容 (Requirements 10.2, 10.3, 10.4):
        - 明確列出缺失的具體指標
        - 基於可用數據提供有限度分析
        - 添加手動查詢建議
        """
        report = "\n┌─ Module 20: 基本面健康檢查 ──────────────────┐\n"
        report += "│\n"
        
        # 定義所有指標及其名稱
        ALL_METRICS = {
            'peg_ratio': 'PEG 比率',
            'roe': 'ROE (股本回報率)',
            'profit_margin': '淨利潤率',
            'debt_eq': '負債/股本比',
            'inst_own': '機構持股比例'
        }
        
        # 檢查是否跳過
        if results.get('status') == 'skipped':
            report += f"│ ⚠ 狀態: 跳過執行\n"
            report += f"│ 原因: {results.get('reason', 'N/A')}\n"
            available = results.get('available_metrics', 0)
            required = results.get('required_metrics', 3)
            report += f"│ 可用指標: {available}/{required}\n"
            report += "│\n"
            
            # 列出缺失的具體指標 (Requirement 10.2)
            report += "│ 📋 缺失指標詳情:\n"
            missing_metrics = results.get('missing_metrics', [])
            if missing_metrics:
                for metric in missing_metrics:
                    metric_name = ALL_METRICS.get(metric, metric)
                    report += f"│   ✗ {metric_name}\n"
            else:
                # 如果沒有明確的缺失列表，列出所有指標
                for key, name in ALL_METRICS.items():
                    report += f"│   ✗ {name}\n"
            report += "│\n"
            
            # 手動查詢建議 (Requirement 10.4)
            report += "│ 🔍 手動查詢建議:\n"
            report += "│   • Finviz: https://finviz.com/quote.ashx?t=TICKER\n"
            report += "│   • Yahoo Finance: https://finance.yahoo.com/quote/TICKER\n"
            report += "│   • MarketWatch: https://www.marketwatch.com/investing/stock/TICKER\n"
            report += "│\n"
            report += "│ 💡 說明: 需要至少 3 個基本面指標才能執行分析\n"
            report += "│   請手動查詢上述網站獲取基本面數據\n"
            report += "└────────────────────────────────────────────┘\n"
            return report
        
        # 正常結果
        health_score = results.get('health_score', 0)
        grade = results.get('grade', 'N/A')
        available_metrics = results.get('available_metrics', 0)
        data_source = results.get('data_source', 'N/A')
        
        report += f"│ 🏥 健康評分:\n"
        report += f"│   分數: {health_score}/100\n"
        report += f"│   等級: {grade}\n"
        report += f"│   使用指標: {available_metrics}/5\n"
        report += "│\n"
        
        # 各項指標 - 顯示可用和缺失的指標
        report += f"│ 📊 基本面指標:\n"
        
        # 追蹤可用和缺失的指標
        available_list = []
        missing_list = []
        
        # PEG 比率
        if results.get('peg_ratio') is not None:
            peg = results.get('peg_ratio', 0)
            peg_analysis = self._get_peg_analysis(peg)
            report += f"│   ✓ PEG 比率: {peg:.2f} {peg_analysis}\n"
            available_list.append('peg_ratio')
        else:
            missing_list.append('peg_ratio')
        
        # ROE
        if results.get('roe') is not None:
            roe = results.get('roe', 0)
            roe_analysis = self._get_roe_analysis(roe)
            report += f"│   ✓ ROE: {roe:.2f}% {roe_analysis}\n"
            available_list.append('roe')
        else:
            missing_list.append('roe')
        
        # 淨利潤率
        if results.get('profit_margin') is not None:
            margin = results.get('profit_margin', 0)
            margin_analysis = self._get_profit_margin_analysis(margin)
            report += f"│   ✓ 淨利潤率: {margin:.2f}% {margin_analysis}\n"
            available_list.append('profit_margin')
        else:
            missing_list.append('profit_margin')
        
        # 負債/股本
        if results.get('debt_eq') is not None:
            debt = results.get('debt_eq', 0)
            debt_analysis = self._get_debt_analysis(debt)
            report += f"│   ✓ 負債/股本: {debt:.2f} {debt_analysis}\n"
            available_list.append('debt_eq')
        else:
            missing_list.append('debt_eq')
        
        # 機構持股
        if results.get('inst_own') is not None:
            inst = results.get('inst_own', 0)
            inst_analysis = self._get_inst_own_analysis(inst)
            report += f"│   ✓ 機構持股: {inst:.2f}% {inst_analysis}\n"
            available_list.append('inst_own')
        else:
            missing_list.append('inst_own')
        
        report += "│\n"
        
        # 列出缺失的指標 (Requirement 10.2)
        if missing_list:
            report += "│ ⚠ 缺失指標:\n"
            for metric in missing_list:
                metric_name = ALL_METRICS.get(metric, metric)
                report += f"│   ✗ {metric_name}\n"
            report += "│\n"
        
        # 基於可用數據提供有限度分析 (Requirement 10.3)
        if available_metrics < 5:
            report += "│ 📈 有限度分析:\n"
            limited_analysis = self._get_limited_fundamental_analysis(results, available_list)
            for line in limited_analysis:
                report += f"│   {line}\n"
            report += "│\n"
            
            # 信心等級
            confidence = self._get_fundamental_confidence(available_metrics)
            report += f"│ 📊 分析信心: {confidence}\n"
            report += "│\n"
        
        # 數據來源
        report += f"│ 📌 數據來源: {data_source}\n"
        if available_metrics < 5:
            report += f"│ ⚠ 注意: 僅使用 {available_metrics}/5 個指標，分析可能不完整\n"
        report += "│\n"
        
        # 手動查詢建議 (Requirement 10.4) - 當數據不完整時顯示
        if missing_list:
            ticker = results.get('ticker', 'TICKER')
            report += "│ 🔍 補充數據建議:\n"
            report += f"│   • Finviz: https://finviz.com/quote.ashx?t={ticker}\n"
            report += f"│   • Yahoo Finance: https://finance.yahoo.com/quote/{ticker}\n"
            report += "│\n"
        
        # 等級解讀
        report += f"│ 💡 等級解讀:\n"
        report += f"│   A (80-100): 優秀，基本面非常健康\n"
        report += f"│   B (60-79): 良好，基本面健康\n"
        report += f"│   C (40-59): 中等，基本面一般\n"
        report += f"│   D (<40): 需警惕，基本面存在問題\n"
        report += "└────────────────────────────────────────────┘\n"
        return report
    
    def _get_peg_analysis(self, peg: float) -> str:
        """獲取 PEG 比率分析"""
        if peg < 1.0:
            return "(低估)"
        elif peg < 2.0:
            return "(合理)"
        elif peg < 3.0:
            return "(略高)"
        else:
            return "(高估)"
    
    def _get_roe_analysis(self, roe: float) -> str:
        """獲取 ROE 分析"""
        if roe > 20:
            return "(優秀)"
        elif roe > 15:
            return "(良好)"
        elif roe > 10:
            return "(一般)"
        else:
            return "(偏低)"
    
    def _get_profit_margin_analysis(self, margin: float) -> str:
        """獲取淨利潤率分析"""
        if margin > 20:
            return "(優秀)"
        elif margin > 10:
            return "(良好)"
        elif margin > 5:
            return "(一般)"
        else:
            return "(偏低)"
    
    def _get_debt_analysis(self, debt: float) -> str:
        """獲取負債/股本分析"""
        if debt < 0.5:
            return "(優秀)"
        elif debt < 1.0:
            return "(良好)"
        elif debt < 2.0:
            return "(一般)"
        else:
            return "(高負債)"
    
    def _get_inst_own_analysis(self, inst: float) -> str:
        """獲取機構持股分析"""
        if inst > 60:
            return "(高認可)"
        elif inst > 40:
            return "(正常)"
        elif inst > 20:
            return "(偏低)"
        else:
            return "(低認可)"
    
    def _get_limited_fundamental_analysis(self, results: dict, available_list: list) -> list:
        """基於可用數據提供有限度分析 (Requirement 10.3)"""
        analysis = []
        
        # 估值分析
        if 'peg_ratio' in available_list:
            peg = results.get('peg_ratio', 0)
            if peg < 1.0:
                analysis.append("• 估值: 股票可能被低估，具有投資價值")
            elif peg < 2.0:
                analysis.append("• 估值: 股票估值合理")
            else:
                analysis.append("• 估值: 股票可能被高估，需謹慎")
        
        # 盈利能力分析
        if 'roe' in available_list or 'profit_margin' in available_list:
            roe = results.get('roe')
            margin = results.get('profit_margin')
            if roe and roe > 15:
                analysis.append("• 盈利: 公司盈利能力強")
            elif margin and margin > 10:
                analysis.append("• 盈利: 公司利潤率健康")
            elif roe or margin:
                analysis.append("• 盈利: 公司盈利能力一般")
        
        # 財務健康分析
        if 'debt_eq' in available_list:
            debt = results.get('debt_eq', 0)
            if debt < 1.0:
                analysis.append("• 財務: 負債水平健康")
            else:
                analysis.append("• 財務: 負債水平較高，需關注")
        
        # 市場認可度分析
        if 'inst_own' in available_list:
            inst = results.get('inst_own', 0)
            if inst > 50:
                analysis.append("• 市場: 機構投資者認可度高")
            elif inst > 30:
                analysis.append("• 市場: 機構投資者持股正常")
            else:
                analysis.append("• 市場: 機構投資者持股偏低")
        
        if not analysis:
            analysis.append("• 可用數據不足，無法提供有效分析")
        
        return analysis
    
    def _get_fundamental_confidence(self, available_metrics: int) -> str:
        """獲取基本面分析信心等級"""
        if available_metrics >= 5:
            return "高 (5/5 指標完整)"
        elif available_metrics >= 4:
            return "中高 (4/5 指標可用)"
        elif available_metrics >= 3:
            return "中等 (3/5 指標可用)"
        elif available_metrics >= 2:
            return "低 (2/5 指標可用，分析參考價值有限)"
        else:
            return "極低 (1/5 指標可用，建議手動查詢補充數據)"
    
    def _format_module21_momentum_filter(self, results: dict) -> str:
        """格式化 Module 21 動量過濾器結果"""
        report = "\n┌─ Module 21: 動量過濾器 ───────────────────────┐\n"
        report += "│\n"
        
        # 檢查是否跳過
        if results.get('status') == 'skipped':
            report += f"│ ! 狀態: 跳過執行\n"
            report += f"│ 原因: {results.get('reason', 'N/A')}\n"
            report += f"│ 動量得分: {results.get('momentum_score', 0.5):.4f} (默認中性)\n"
            report += "│\n"
            if 'note' in results:
                report += f"│ 💡 {results.get('note', '')}\n"
            report += "└────────────────────────────────────────────────┘\n"
            return report
        
        # 檢查是否錯誤
        if results.get('status') == 'error':
            report += f"│ x 狀態: 執行錯誤\n"
            report += f"│ 原因: {results.get('reason', 'N/A')}\n"
            report += "│\n"
            report += "└────────────────────────────────────────────────┘\n"
            return report
        
        # 正常結果
        momentum_score = results.get('momentum_score', 0)
        recommendation = results.get('recommendation', 'N/A')
        
        # 動量得分可視化（進度條）
        bar_length = int(momentum_score * 20)
        bar = '█' * bar_length + '░' * (20 - bar_length)
        
        report += f"│ 📈 動量得分: {momentum_score:.4f}\n"
        report += f"│ [{bar}] {momentum_score*100:.1f}%\n"
        report += "│\n"
        
        # 動量等級
        if momentum_score > 0.7:
            momentum_level = "🔥 強勢上漲"
            momentum_note = "不建議逆勢Short"
        elif momentum_score > 0.4:
            momentum_level = "➡️ 中性"
            momentum_note = "可謹慎操作"
        else:
            momentum_level = "❄️ 動量轉弱"
            momentum_note = "可考慮Short"
        
        report += f"│ 動量等級: {momentum_level}\n"
        report += f"│ 策略建議: {momentum_note}\n"
        report += "│\n"
        
        # 組成部分（如果有）
        if 'price_momentum' in results or 'volume_momentum' in results or 'relative_strength' in results:
            report += f"│ 📊 動量組成:\n"
            
            if 'price_momentum' in results:
                price_mom = results.get('price_momentum', 0)
                report += f"│   價格動量 (50%): {price_mom:.4f}\n"
                if 'price_change_1m' in results:
                    change_1m = results.get('price_change_1m', 0)
                    if change_1m is not None:
                        report += f"│     1個月變化: {change_1m:+.2f}%\n"
                if 'price_change_3m' in results:
                    change_3m = results.get('price_change_3m', 0)
                    if change_3m is not None:
                        report += f"│     3個月變化: {change_3m:+.2f}%\n"
            
            if 'volume_momentum' in results:
                vol_mom = results.get('volume_momentum', 0)
                report += f"│   成交量動量 (30%): {vol_mom:.4f}\n"
            
            if 'relative_strength' in results:
                rs = results.get('relative_strength', 0)
                report += f"│   相對強度 (20%): {rs:.4f}\n"
            
            report += "│\n"
        
        # 策略建議
        report += f"│ 💡 系統建議: {recommendation}\n"
        report += "│\n"
        report += "│ 📌 動量閾值解讀:\n"
        report += "│   > 0.7: 強勢，避免逆勢Short\n"
        report += "│   0.4-0.7: 中性，謹慎操作\n"
        report += "│   < 0.4: 轉弱，可以Short\n"
        report += "│\n"
        report += "│ ⚠️ 注意: 與 Module 3 套戥水位配合使用\n"
        report += "└────────────────────────────────────────────────┘\n"
        return report
    
    def _format_module22_optimal_strike(self, results: dict) -> str:
        """
        格式化 Module 22 最佳行使價分析結果
        
        增強功能 (Requirements 12.1, 12.2, 12.3, 12.4):
        - 12.1: 顯示數據完整度
        - 12.2: 流動性得分低於 50 時警告推薦可能不可靠
        - 12.3: 說明評分主要影響因素
        - 12.4: 數據不足時降低信心等級
        """
        report = "\n┌─ Module 22: 最佳行使價分析 ───────────────────┐\n"
        report += "│\n"
        
        # 檢查是否跳過
        if results.get('status') == 'skipped':
            report += f"│ ! 狀態: 跳過執行\n"
            report += f"│ 原因: {results.get('reason', 'N/A')}\n"
            report += "│\n"
            report += "└────────────────────────────────────────────────┘\n"
            return report
        
        # 檢查是否錯誤
        if results.get('status') == 'error':
            report += f"│ x 狀態: 執行錯誤\n"
            report += f"│ 原因: {results.get('reason', 'N/A')}\n"
            report += "│\n"
            report += "└────────────────────────────────────────────────┘\n"
            return report
        
        # Requirements 12.1: 計算數據完整度
        data_completeness = self._calculate_module22_data_completeness(results)
        confidence_level = self._get_module22_confidence_level(data_completeness, results)
        
        # 顯示分析範圍和數據完整度（從任一策略獲取）
        for strategy_key in ['long_call', 'long_put', 'short_call', 'short_put']:
            if strategy_key in results:
                strategy_data = results[strategy_key]
                if 'strike_range' in strategy_data:
                    sr = strategy_data['strike_range']
                    max_each_side = sr.get('max_strikes_each_side', 20)
                    total_selected = sr.get('total_selected', 0)
                    report += f"│ 📊 分析範圍: ${sr.get('min', 0):.2f} - ${sr.get('max', 0):.2f} (ATM 上下各最多 {max_each_side} 個，實際選取 {total_selected} 個)\n"
                if 'total_analyzed' in strategy_data:
                    total_analyzed = strategy_data.get('total_analyzed', 0)
                    report += f"│ 📈 分析行使價數量: {total_analyzed}\n"
                
                # Requirements 12.1: 顯示數據完整度
                report += f"│ 📋 數據完整度: {data_completeness:.0f}%\n"
                
                # Requirements 12.4: 顯示信心等級
                confidence_emoji = {'高': '🟢', '中': '🟡', '低': '🔴'}.get(confidence_level, '⚪')
                report += f"│ 🎯 推薦信心等級: {confidence_emoji} {confidence_level}\n"
                
                # Requirements 12.4: 數據不足時說明原因
                if confidence_level == '低':
                    report += "│   ⚠️ 信心等級較低原因:\n"
                    if total_analyzed < 3:
                        report += "│      - 可分析行使價數量不足 (< 3)\n"
                    if data_completeness < 50:
                        report += "│      - 數據完整度不足 (< 50%)\n"
                elif confidence_level == '中':
                    report += "│   ℹ️ 建議結合其他模塊綜合判斷\n"
                
                report += "│\n"
                break
        
        # Requirements 12.3: 說明評分主要影響因素
        report += "│ 📊 評分權重說明:\n"
        report += "│   • 流動性 (30%): 成交量、未平倉量、買賣價差\n"
        report += "│   • Greeks (30%): Delta、Theta、Vega 適合度\n"
        report += "│   • IV (20%): IV Rank、IV Skew\n"
        report += "│   • 風險回報 (20%): 最大損失、盈虧平衡點\n"
        report += "│\n"
        
        # 遍歷四種策略
        strategies = {
            'long_call': ('📈 Long Call', '看漲買入'),
            'long_put': ('📉 Long Put', '看跌買入'),
            'short_call': ('📊 Short Call', '看跌賣出'),
            'short_put': ('💼 Short Put', '看漲賣出')
        }
        
        for strategy_key, (emoji_name, desc) in strategies.items():
            if strategy_key not in results:
                continue
            
            strategy_data = results[strategy_key]
            
            report += f"│ {emoji_name} ({desc}):\n"
            
            # 顯示 Top 10 推薦（優化內存使用）
            if 'top_recommendations' in strategy_data and strategy_data['top_recommendations']:
                top_recs = strategy_data['top_recommendations']
                total_recs = len(top_recs)
                
                # 只顯示前 10 個推薦
                for i, rec in enumerate(top_recs[:10]):
                    strike = rec.get('strike', 0)
                    score = rec.get('composite_score', 0)
                    delta = rec.get('delta', 0)
                    theta = rec.get('theta', 0)
                    gamma = rec.get('gamma', 0)
                    vega = rec.get('vega', 0)
                    reason = rec.get('reason', '')
                    liq_score = rec.get('liquidity_score', 0)
                    
                    if i == 0:
                        stars = '★' * int(score / 20) + '☆' * (5 - int(score / 20))
                        report += f"│   🥇 推薦 #1: ${strike:.2f} ({stars} {score:.1f}分)\n"
                    elif i == 1:
                        report += f"│   🥈 推薦 #2: ${strike:.2f} ({score:.1f}分)\n"
                    elif i == 2:
                        report += f"│   🥉 推薦 #3: ${strike:.2f} ({score:.1f}分)\n"
                    else:
                        report += f"│   推薦 #{i+1}: ${strike:.2f} ({score:.1f}分)\n"
                    
                    # Requirements 12.2: 流動性警告（得分 < 50）
                    if liq_score < 50:
                        report += f"│      ⚠️ 流動性警告: 得分 {liq_score:.0f} < 50，推薦可能不可靠\n"
                    
                    # 顯示完整 Greeks（僅前3名顯示詳細信息）
                    if i < 3:
                        report += f"│      Greeks: Δ={delta:.4f} Γ={gamma:.4f} Θ={theta:.4f} ν={vega:.2f}\n"
                        
                        # 顯示推薦理由
                        if reason:
                            report += f"│      理由: {reason}\n"
                        
                        # 顯示評分細節（僅第一名）
                        if i == 0:
                            liq = rec.get('liquidity_score', 0)
                            grk = rec.get('greeks_score', 0)
                            ivs = rec.get('iv_score', 0)
                            rrs = rec.get('risk_reward_score', 0)
                            report += f"│      評分: 流動性={liq:.0f} Greeks={grk:.0f} IV={ivs:.0f} 風險回報={rrs:.0f}\n"
                            
                            # Requirements 12.3: 說明主要影響因素
                            main_factor = self._get_main_scoring_factor(liq, grk, ivs, rrs)
                            report += f"│      主要影響因素: {main_factor}\n"
                
                # 如果有超過 10 個推薦，顯示摘要統計
                if total_recs > 10:
                    remaining = top_recs[10:]
                    avg_score = sum(r.get('composite_score', 0) for r in remaining) / len(remaining)
                    strike_range = f"${min(r.get('strike', 0) for r in remaining):.2f} - ${max(r.get('strike', 0) for r in remaining):.2f}"
                    report += f"│   ... 另有 {total_recs - 10} 個行使價 (平均得分: {avg_score:.1f}, 範圍: {strike_range})\n"
            else:
                report += f"│   ! 無推薦（數據不足）\n"
                # Requirements 12.4: 數據不足時的說明
                report += f"│   ℹ️ 可能原因: 流動性不足或無符合條件的行使價\n"
            
            report += "│\n"
        
        # 顯示 IV 環境建議（從 Module 23 整合）
        iv_environment = None
        iv_suggestion = None
        for strategy_key in ['long_call', 'long_put', 'short_call', 'short_put']:
            if strategy_key in results:
                iv_environment = results[strategy_key].get('iv_environment')
                iv_suggestion = results[strategy_key].get('iv_trading_suggestion')
                if iv_environment:
                    break
        
        if iv_environment:
            report += "│ 📊 IV 環境分析 (來自 Module 23):\n"
            if iv_environment == 'high':
                report += "│   🔴 IV 偏高 - 建議 Short 策略 (賣出期權)\n"
                report += "│   推薦: Short Call, Short Put, Iron Condor\n"
            elif iv_environment == 'low':
                report += "│   🔵 IV 偏低 - 建議 Long 策略 (買入期權)\n"
                report += "│   推薦: Long Call, Long Put, Debit Spread\n"
            else:
                report += "│   🟢 IV 中性 - 可根據方向判斷選擇策略\n"
                report += "│   推薦: Calendar Spread, Butterfly\n"
            report += "│\n"
        
        report += "│ 💡 使用建議:\n"
        report += "│   1. 優先選擇流動性得分 > 70 的行使價\n"
        report += "│   2. Long策略選擇 Delta 0.30-0.70 範圍\n"
        report += "│   3. Short策略選擇 Delta 0.10-0.30 範圍\n"
        report += "│   4. 結合 Module 14 監察崗位和 Module 23 IV 環境綜合判斷\n"
        
        # Requirements 12.2: 流動性警告提示
        report += "│   5. ⚠️ 流動性得分 < 50 時，建議謹慎交易或選擇其他行使價\n"
        report += "└────────────────────────────────────────────────┘\n"
        
        # 添加波動率微笑分析（如果存在）
        # 從任一策略中獲取波動率微笑數據
        smile_data = None
        for strategy_key in ['long_call', 'long_put', 'short_call', 'short_put']:
            if strategy_key in results:
                smile = results[strategy_key].get('volatility_smile')
                if smile is not None and isinstance(smile, dict):
                    smile_data = smile
                    break
        
        if smile_data:
            report += self._format_volatility_smile(smile_data)
        
        # 添加 Put-Call Parity 驗證（如果存在）
        parity_data = None
        for strategy_key in ['long_call', 'long_put', 'short_call', 'short_put']:
            if strategy_key in results:
                parity = results[strategy_key].get('parity_validation')
                if parity is not None and isinstance(parity, dict):
                    parity_data = parity
                    break
        
        if parity_data:
            report += self._format_parity_validation(parity_data)
            
        # 添加高級指標分析（如果存在）
        # Requirements: 6.1 (Advanced Metrics) - 優先顯示
        advanced_metrics = None
        for strategy_key in ['long_call', 'long_put', 'short_call', 'short_put']:
            if strategy_key in results:
                am = results[strategy_key].get('advanced_metrics')
                if am is not None and isinstance(am, dict):
                    advanced_metrics = am
                    break
        
        if advanced_metrics:
            report += self._format_advanced_metrics(advanced_metrics)
            
        # 添加高級組合策略分析（如果存在）
        # Requirements: Phase 3
        complex_strategies = results.get('module32_complex_strategies')
        # Compatibility check: ensure it's not the old module22 results
        # In main.py we store it in module22 for now? NO, stored in module32_complex_strategies
        # But here we are inside _format_module22_optimal_strike... 
        # Wait, I should not add it inside module22 formatter. 
        # I should add it as a separate section in the main generation loop.
        
        return report
    
    def _calculate_module22_data_completeness(self, results: dict) -> float:
        """
        計算 Module 22 數據完整度
        
        Requirements 12.1: 顯示數據完整度
        
        計算方式:
        - 有效策略數量 (25%)
        - 每個策略的推薦數量 (25%)
        - Greeks 數據完整性 (25%)
        - 流動性數據完整性 (25%)
        
        返回:
            float: 數據完整度百分比 (0-100)
        """
        total_score = 0.0
        strategy_keys = ['long_call', 'long_put', 'short_call', 'short_put']
        
        # 1. 有效策略數量 (25%)
        valid_strategies = sum(1 for key in strategy_keys if key in results)
        strategy_score = (valid_strategies / 4.0) * 25.0
        total_score += strategy_score
        
        # 2. 推薦數量完整性 (25%)
        total_recommendations = 0
        max_recommendations = 0
        for key in strategy_keys:
            if key in results:
                recs = results[key].get('top_recommendations', [])
                total_recommendations += len(recs)
                max_recommendations += 3  # 每個策略最多 3 個推薦
        
        if max_recommendations > 0:
            rec_score = (total_recommendations / max_recommendations) * 25.0
        else:
            rec_score = 0.0
        total_score += rec_score
        
        # 3. Greeks 數據完整性 (25%)
        greeks_complete = 0
        greeks_total = 0
        for key in strategy_keys:
            if key in results:
                recs = results[key].get('top_recommendations', [])
                for rec in recs:
                    greeks_total += 4  # delta, gamma, theta, vega
                    if rec.get('delta', 0) != 0:
                        greeks_complete += 1
                    if rec.get('gamma', 0) != 0:
                        greeks_complete += 1
                    if rec.get('theta', 0) != 0:
                        greeks_complete += 1
                    if rec.get('vega', 0) != 0:
                        greeks_complete += 1
        
        if greeks_total > 0:
            greeks_score = (greeks_complete / greeks_total) * 25.0
        else:
            greeks_score = 0.0
        total_score += greeks_score
        
        # 4. 流動性數據完整性 (25%)
        liquidity_complete = 0
        liquidity_total = 0
        for key in strategy_keys:
            if key in results:
                recs = results[key].get('top_recommendations', [])
                for rec in recs:
                    liquidity_total += 3  # volume, open_interest, bid_ask_spread
                    if rec.get('volume', 0) > 0:
                        liquidity_complete += 1
                    if rec.get('open_interest', 0) > 0:
                        liquidity_complete += 1
                    if rec.get('bid_ask_spread_pct', -1) >= 0:
                        liquidity_complete += 1
        
        if liquidity_total > 0:
            liquidity_score = (liquidity_complete / liquidity_total) * 25.0
        else:
            liquidity_score = 0.0
        total_score += liquidity_score
        
        return min(100.0, max(0.0, total_score))
    
    def _get_module22_confidence_level(self, data_completeness: float, results: dict) -> str:
        """
        獲取 Module 22 推薦信心等級
        
        Requirements 12.4: 數據不足時降低信心等級
        
        信心等級判斷:
        - 高: 數據完整度 >= 70% 且有足夠推薦
        - 中: 數據完整度 50-70% 或推薦數量有限
        - 低: 數據完整度 < 50% 或無推薦
        
        返回:
            str: '高', '中', '低'
        """
        # 計算總推薦數量
        total_recommendations = 0
        total_analyzed = 0
        has_low_liquidity = False
        
        for key in ['long_call', 'long_put', 'short_call', 'short_put']:
            if key in results:
                recs = results[key].get('top_recommendations', [])
                total_recommendations += len(recs)
                total_analyzed = max(total_analyzed, results[key].get('total_analyzed', 0))
                
                # 檢查是否有低流動性推薦
                for rec in recs:
                    if rec.get('liquidity_score', 100) < 50:
                        has_low_liquidity = True
        
        # 判斷信心等級
        if data_completeness >= 70 and total_recommendations >= 4 and total_analyzed >= 5 and not has_low_liquidity:
            return '高'
        elif data_completeness >= 50 and total_recommendations >= 2 and total_analyzed >= 3:
            return '中'
        else:
            return '低'
    
    def _get_main_scoring_factor(self, liquidity: float, greeks: float, iv: float, risk_reward: float) -> str:
        """
        獲取主要評分影響因素
        
        Requirements 12.3: 說明評分主要影響因素
        
        返回:
            str: 主要影響因素說明
        """
        scores = {
            '流動性': liquidity,
            'Greeks': greeks,
            'IV': iv,
            '風險回報': risk_reward
        }
        
        # 找出最高和最低分
        max_factor = max(scores, key=scores.get)
        min_factor = min(scores, key=scores.get)
        max_score = scores[max_factor]
        min_score = scores[min_factor]
        
        # 生成說明
        if max_score - min_score > 30:
            return f"{max_factor}表現優異 ({max_score:.0f}分)，{min_factor}相對較弱 ({min_score:.0f}分)"
        elif max_score >= 70:
            return f"{max_factor}為主要優勢 ({max_score:.0f}分)"
        elif min_score < 40:
            return f"⚠️ {min_factor}得分偏低 ({min_score:.0f}分)，需注意"
        else:
            return "各項評分均衡"
            
    def _format_advanced_metrics(self, data: dict) -> str:
        """
        格式化 Module 31 高級指標分析結果
        
        Requirements: 6.1 (Advanced Metrics)
        """
        report = "\n┌─ 高級市場指標 (Advanced Metrics) ────────────┐\n"
        report += "│\n"
        
        pcr_volume = data.get('pcr_volume', 0)
        pcr_oi = data.get('pcr_oi', 0)
        max_pain = data.get('max_pain', 0)
        total_gex = data.get('total_gex', 0)
        
        # 1. PCR 分析
        report += f"│ 📊 Put/Call Ratio (PCR):\n"
        report += f"│   PCR (成交量): {pcr_volume:.2f}"
        if pcr_volume > 1.2:
            report += " (偏空/超賣)\n"
        elif pcr_volume < 0.7:
            report += " (偏多/超買)\n"
        else:
            report += " (中性)\n"
            
        report += f"│   PCR (持倉量): {pcr_oi:.2f}\n"
        report += "│\n"
        
        # 2. Max Pain 分析
        report += f"│ 🎯 最大痛點 (Max Pain):\n"
        report += f"│   價格: ${max_pain:.2f}\n"
        report += "│   (這是做市商最希望結算的價格，股價常向此靠攏)\n"
        report += "│\n"
        
        # 3. GEX 分析
        gex_m = total_gex / 1_000_000
        report += f"│ 🌊 Gamma Exposure (GEX):\n"
        report += f"│   總額: ${total_gex:,.0f} (${gex_m:.1f}M)\n"
        
        if total_gex > 0:
            report += "│   狀態: 正 GEX (做市商抑制波動，市場較穩定)\n"
        else:
            report += "│   狀態: 負 GEX (做市商放大波動，可能暴漲暴跌)\n"
            
        report += "└────────────────────────────────────────────────┘\n"
        return report
    
    def _format_complex_strategies(self, results: dict) -> str:
        """
        格式化 Module 32 高級組合策略分析結果
        """
        report = "\n┌─ Module 32: 高級組合策略 (Complex Strategies) ──┐\n"
        report += "│\n"
        
        if results.get('status') in ['skipped', 'error']:
            report += f"│ ! 狀態: {results.get('status', 'N/A')}\n"
            report += f"│ 原因: {results.get('reason', 'N/A')}\n"
            report += "└────────────────────────────────────────────────┘\n"
            return report
            
        # 1. 垂直價差
        vertical = results.get('vertical', {})
        bull_puts = vertical.get('bull_put', [])
        bear_calls = vertical.get('bear_call', [])
        
        if bull_puts or bear_calls:
            report += "│ 📊 垂直價差 (Vertical Spreads):\n"
            
            if bull_puts:
                best = bull_puts[0]
                report += f"│   📈 Bull Put Spread (看漲 Credit):\n"
                report += f"│      {best.get('description')}\n"
                report += f"│      最大收益: ${best.get('max_profit'):.2f}, 最大風險: ${best.get('max_loss'):.2f}\n"
                report += f"│      勝率: {best.get('win_prob')}%, 回報率: {best.get('risk_reward')*100:.1f}%\n"
                report += f"│      Greeks: Δ={best.get('greeks', {}).get('delta')}\n"
                
            if bear_calls:
                best = bear_calls[0]
                report += f"│   📉 Bear Call Spread (看跌 Credit):\n"
                report += f"│      {best.get('description')}\n"
                report += f"│      最大收益: ${best.get('max_profit'):.2f}, 最大風險: ${best.get('max_loss'):.2f}\n"
                report += f"│      勝率: {best.get('win_prob')}%, 回報率: {best.get('risk_reward')*100:.1f}%\n"
                report += f"│      Greeks: Δ={best.get('greeks', {}).get('delta')}\n"
            report += "│\n"

        # 2. 鐵兀鷹
        condors = results.get('iron_condor', [])
        if condors:
            best = condors[0]
            report += "│ 🦅 鐵兀鷹 (Iron Condor - 區間震盪):\n"
            report += f"│      {best.get('description')}\n"
            report += f"│      最大收益: ${best.get('max_profit'):.2f}, 最大風險: ${best.get('max_loss'):.2f}\n"
            report += f"│      勝率: {best.get('win_prob')}%, 回報率: {best.get('risk_reward')*100:.1f}%\n"
            report += f"│      盈虧平衡: {best.get('breakevens')}\n"
            report += "│\n"
            
        # 3. 跨式/寬跨式
        straddle_strangle = results.get('straddle_strangle', {})
        straddles = straddle_strangle.get('straddle', [])
        strangles = straddle_strangle.get('strangle', [])
        
        if straddles or strangles:
            report += "│ 💥 波動率突破 (Straddle/Strangle):\n"
            if straddles:
                best = straddles[0]
                report += f"│   Long Straddle: {best.get('description')}\n"
                report += f"│   成本: ${abs(best.get('net_premium')):.2f}, 盈虧平衡: {best.get('breakevens')}\n"
            if strangles:
                best = strangles[0]
                report += f"│   Long Strangle: {best.get('description')}\n"
                report += f"│   成本: ${abs(best.get('net_premium')):.2f}, 盈虧平衡: {best.get('breakevens')}\n"
                
        report += "└────────────────────────────────────────────────┘\n"
        return report

    def _format_volatility_smile(self, smile_data: dict) -> str:
        """
        格式化波動率微笑分析結果
        
        增強功能 (Requirements 13.1, 13.2, 13.3, 13.4):
        - 13.1: 提供市場情緒總結（看漲/看跌/中性）
        - 13.2: 解釋 Skew 負值的含義（市場預期下跌風險較大）
        - 13.3: 解釋 Skew 正值的含義（市場預期上漲風險較大）
        - 13.4: 提供微笑形狀的交易含義
        """
        report = "\n┌─ 波動率微笑分析 (Volatility Smile) ──────────┐\n"
        report += "│\n"
        
        atm_iv = smile_data.get('atm_iv', 0)
        atm_strike = smile_data.get('atm_strike', 0)
        skew = smile_data.get('skew', 0)
        smile_shape = smile_data.get('smile_shape', 'N/A')
        skew_25delta = smile_data.get('skew_25delta', 0)
        current_price = smile_data.get('current_price', 0)
        
        report += f"│ 📊 基本指標:\n"
        report += f"│   當前股價: ${current_price:.2f}\n"
        report += f"│   ATM 行使價: ${atm_strike:.2f}\n"
        report += f"│   ATM IV: {atm_iv:.2f}%\n"
        report += "│\n"
        
        report += f"│ 📈 偏斜分析:\n"
        report += f"│   Skew (OTM Put - OTM Call): {skew:.2f}%\n"
        report += f"│   25-Delta Skew: {skew_25delta:.2f}%\n"
        report += f"│   微笑形狀: {smile_shape}\n"
        report += "│\n"
        
        # Requirements 13.1: 市場情緒總結
        market_sentiment = self._get_volatility_smile_sentiment(skew, smile_shape)
        report += f"│ 🎯 市場情緒總結:\n"
        report += f"│   情緒判斷: {market_sentiment['sentiment']}\n"
        report += f"│   信心程度: {market_sentiment['confidence']}\n"
        report += "│\n"
        
        # Requirements 13.2, 13.3: Skew 正負值含義解釋
        report += f"│ 📖 Skew 解讀:\n"
        skew_interpretation = self._get_skew_interpretation(skew)
        for line in skew_interpretation:
            report += f"│   {line}\n"
        report += "│\n"
        
        # 微笑形狀解讀
        report += f"│ 💡 形狀解讀:\n"
        if smile_shape == 'put_skew':
            report += "│   Put Skew: OTM Put IV > OTM Call IV\n"
            report += "│   市場預期下跌風險較大（股票期權常見）\n"
        elif smile_shape == 'call_skew':
            report += "│   Call Skew: OTM Call IV > OTM Put IV\n"
            report += "│   市場預期上漲風險較大（商品期權常見）\n"
        elif smile_shape == 'symmetric':
            report += "│   Symmetric: OTM Put IV ≈ OTM Call IV\n"
            report += "│   市場對上下風險預期相近\n"
        else:
            report += "│   Unknown: 無法判斷微笑形狀\n"
            report += "│   可能數據不足或市場異常\n"
        report += "│\n"
        
        # Requirements 13.4: 微笑形狀的交易含義
        report += f"│ 💰 交易含義:\n"
        trading_implications = self._get_smile_trading_implications(smile_shape, skew, atm_iv)
        for line in trading_implications:
            report += f"│   {line}\n"
        
        report += "└────────────────────────────────────────────────┘\n"
        return report
    
    def _get_volatility_smile_sentiment(self, skew: float, smile_shape: str) -> dict:
        """
        根據 Skew 和微笑形狀判斷市場情緒
        
        Requirements 13.1: 提供市場情緒總結（看漲/看跌/中性）
        
        參數:
            skew: Skew 值（百分比形式，如 2.5 表示 2.5%）
            smile_shape: 微笑形狀 ('put_skew', 'call_skew', 'symmetric', 'unknown')
        
        返回:
            dict: {'sentiment': str, 'confidence': str}
        """
        # Skew > 0 表示 OTM Put IV > OTM Call IV，市場擔心下跌 -> 看跌傾向
        # Skew < 0 表示 OTM Call IV > OTM Put IV，市場擔心上漲 -> 看漲傾向
        
        if smile_shape == 'unknown':
            return {'sentiment': '中性（數據不足）', 'confidence': '低'}
        
        # 使用 Skew 絕對值判斷信心程度
        abs_skew = abs(skew)
        if abs_skew < 1.0:  # < 1%
            confidence = '低'
        elif abs_skew < 3.0:  # 1-3%
            confidence = '中'
        else:  # > 3%
            confidence = '高'
        
        # 判斷情緒方向
        if skew > 1.0:  # Skew > 1%，看跌傾向
            sentiment = '看跌'
        elif skew < -1.0:  # Skew < -1%，看漲傾向
            sentiment = '看漲'
        else:  # -1% <= Skew <= 1%
            sentiment = '中性'
        
        return {'sentiment': sentiment, 'confidence': confidence}
    
    def _get_skew_interpretation(self, skew: float) -> list:
        """
        解釋 Skew 正負值的含義
        
        Requirements 13.2, 13.3:
        - 13.2: Skew 為負值時解釋市場預期下跌風險較大
        - 13.3: Skew 為正值時解釋市場預期上漲風險較大
        
        注意: Skew = OTM Put IV - OTM Call IV
        - Skew > 0: OTM Put 更貴，市場擔心下跌
        - Skew < 0: OTM Call 更貴，市場擔心上漲
        
        參數:
            skew: Skew 值（百分比形式）
        
        返回:
            list: 解釋文字列表
        """
        interpretation = []
        
        if skew > 1.0:  # 正 Skew > 1%
            interpretation.append(f"Skew 為正值 ({skew:.2f}%):")
            interpretation.append("• OTM Put 期權的 IV 高於 OTM Call")
            interpretation.append("• 市場預期下跌風險較大")
            interpretation.append("• 投資者願意支付更高溢價購買下跌保護")
            if skew > 5.0:
                interpretation.append("⚠️ Skew 較大，市場恐慌情緒明顯")
        elif skew < -1.0:  # 負 Skew < -1%
            interpretation.append(f"Skew 為負值 ({skew:.2f}%):")
            interpretation.append("• OTM Call 期權的 IV 高於 OTM Put")
            interpretation.append("• 市場預期上漲風險較大")
            interpretation.append("• 投資者願意支付更高溢價購買上漲機會")
            if skew < -5.0:
                interpretation.append("⚠️ Skew 較大，市場樂觀情緒明顯")
        else:  # -1% <= Skew <= 1%
            interpretation.append(f"Skew 接近零 ({skew:.2f}%):")
            interpretation.append("• OTM Put 和 OTM Call 的 IV 相近")
            interpretation.append("• 市場對上漲和下跌風險預期相近")
            interpretation.append("• 無明顯方向性偏好")
        
        return interpretation
    
    def _get_smile_trading_implications(self, smile_shape: str, skew: float, atm_iv: float) -> list:
        """
        提供微笑形狀的交易含義
        
        Requirements 13.4: 提供形狀的交易含義
        
        參數:
            smile_shape: 微笑形狀
            skew: Skew 值（百分比形式）
            atm_iv: ATM IV（百分比形式）
        
        返回:
            list: 交易建議列表
        """
        implications = []
        
        if smile_shape == 'put_skew':
            implications.append("【Put Skew 交易策略】")
            implications.append("• 賣出 OTM Put 可獲得較高權利金")
            implications.append("• 買入 Put Spread 比單腿 Put 更划算")
            implications.append("• 考慮 Put Ratio Spread 利用 IV 差異")
            if skew > 5.0:
                implications.append("⚠️ 高 Skew 環境，謹慎賣出裸 Put")
        elif smile_shape == 'call_skew':
            implications.append("【Call Skew 交易策略】")
            implications.append("• 賣出 OTM Call 可獲得較高權利金")
            implications.append("• 買入 Call Spread 比單腿 Call 更划算")
            implications.append("• 考慮 Call Ratio Spread 利用 IV 差異")
            if skew < -5.0:
                implications.append("⚠️ 高 Skew 環境，謹慎賣出裸 Call")
        elif smile_shape == 'symmetric':
            implications.append("【對稱微笑交易策略】")
            implications.append("• 適合使用 Straddle/Strangle 策略")
            implications.append("• Iron Condor 兩側風險相近")
            implications.append("• 可根據方向判斷選擇單邊策略")
        else:
            implications.append("【數據不足】")
            implications.append("• 無法提供具體交易建議")
            implications.append("• 建議等待更多市場數據")
        
        # 根據 ATM IV 水平添加額外建議
        if atm_iv > 50:
            implications.append(f"📊 ATM IV ({atm_iv:.1f}%) 較高，賣方策略可能更有利")
        elif atm_iv < 20:
            implications.append(f"📊 ATM IV ({atm_iv:.1f}%) 較低，買方策略可能更有利")
        
        return implications
    
    def _format_parity_validation(self, parity_data: dict) -> str:
        """格式化 Put-Call Parity 驗證結果"""
        report = "\n┌─ Put-Call Parity 驗證 ────────────────────────┐\n"
        report += "│\n"
        
        valid = parity_data.get('valid', False)
        deviation_pct = parity_data.get('deviation_pct', 0)
        arbitrage_opportunity = parity_data.get('arbitrage_opportunity', False)
        strategy = parity_data.get('strategy', 'N/A')
        atm_strike = parity_data.get('atm_strike', 0)
        call_price = parity_data.get('call_price', 0)
        put_price = parity_data.get('put_price', 0)
        
        report += f"│ 📊 ATM 期權價格:\n"
        report += f"│   行使價: ${atm_strike:.2f}\n"
        report += f"│   Call 價格: ${call_price:.2f}\n"
        report += f"│   Put 價格: ${put_price:.2f}\n"
        report += "│\n"
        
        report += f"│ 🔍 Parity 驗證:\n"
        report += f"│   偏差: {deviation_pct:.2f}%\n"
        report += f"│   狀態: {'✓ 通過' if valid else '⚠️ 偏差較大'}\n"
        report += f"│   套利機會: {'存在' if arbitrage_opportunity else '不存在'}\n"
        
        if arbitrage_opportunity:
            theoretical_profit = parity_data.get('theoretical_profit', 0)
            report += f"│   理論利潤: ${theoretical_profit:.2f}\n"
            report += f"│   建議策略: {strategy}\n"
        
        report += "│\n"
        report += "│ 💡 說明:\n"
        report += "│   偏差 < 2%: Parity 成立，無套利機會\n"
        report += "│   偏差 > 2%: 可能存在定價異常\n"
        report += "└────────────────────────────────────────────────┘\n"
        return report
    
    def _format_module23_dynamic_iv_threshold(self, results: dict, iv_rank_data: dict = None) -> str:
        """
        格式化 Module 23 動態IV閾值結果
        
        增強功能 (Requirements 11.1, 11.2, 11.3, 11.4):
        - 11.1: 解釋動態 IV 與 Module 17 隱含波動率的區別
        - 11.2: 說明閾值計算方法（基於歷史百分位）
        - 11.3: 添加邊界預警（當前 IV 接近閾值邊界）
        - 11.4: 與 Module 18 IV Rank 交叉驗證
        
        參數:
            results: Module 23 計算結果
            iv_rank_data: Module 18 IV Rank 數據（用於交叉驗證）
        """
        report = "\n┌─ Module 23: 動態IV閾值計算 ───────────────────┐\n"
        report += "│\n"
        
        # 檢查是否錯誤
        if results.get('status') == 'error':
            report += f"│ x 狀態: 執行錯誤\n"
            report += f"│ 原因: {results.get('reason', 'N/A')}\n"
            report += "│\n"
            report += "└────────────────────────────────────────────────┘\n"
            return report
        
        # 正常結果
        current_iv = results.get('current_iv', 0)
        high_threshold = results.get('high_threshold', 0)
        low_threshold = results.get('low_threshold', 0)
        # 兼容兩種字段名: 'status' (IVThresholdResult) 和 'iv_status' (舊版)
        iv_status = results.get('status', results.get('iv_status', 'N/A'))
        data_quality = results.get('data_quality', 'N/A')
        
        report += f"│ 📊 當前IV狀態:\n"
        report += f"│   當前IV: {current_iv:.2f}%\n"
        report += f"│   高閾值: {high_threshold:.2f}%\n"
        report += f"│   低閾值: {low_threshold:.2f}%\n"
        report += "│\n"
        
        # IV範圍可視化
        range_width = high_threshold - low_threshold
        if range_width > 0:
            current_position = (current_iv - low_threshold) / range_width
            current_position = max(0, min(1, current_position))
            
            bar_pos = int(current_position * 20)
            bar = '░' * bar_pos + '█' + '░' * (20 - bar_pos - 1)
            
            report += f"│ IV範圍可視化:\n"
            report += f"│ 低 [{bar}] 高\n"
            report += f"│ {low_threshold:.1f}%         {current_iv:.1f}%         {high_threshold:.1f}%\n"
            report += "│\n"
        
        # 狀態解讀 - 改進邏輯
        status_lower = iv_status.lower() if isinstance(iv_status, str) else ''
        
        if 'high' in status_lower or current_iv > high_threshold:
            emoji = '🔴'
            display_status = 'HIGH (IV偏高)'
        elif 'low' in status_lower or current_iv < low_threshold:
            emoji = '🔵'
            display_status = 'LOW (IV偏低)'
        elif 'normal' in status_lower or (low_threshold <= current_iv <= high_threshold):
            emoji = '🟢'
            display_status = 'NORMAL (IV合理)'
        else:
            emoji = '⚪'
            display_status = iv_status
        
        report += f"│ {emoji} IV狀態: {display_status}\n"
        
        # Requirement 11.3: 添加邊界預警
        boundary_warning = self._get_iv_boundary_warning(current_iv, high_threshold, low_threshold)
        if boundary_warning:
            report += f"│ ⚠️ 邊界預警: {boundary_warning}\n"
        
        # 交易建議
        if 'trading_suggestion' in results:
            suggestion = results['trading_suggestion']
            if isinstance(suggestion, dict):
                report += f"│ 💡 交易建議: {suggestion.get('action', 'N/A')}\n"
                if 'reason' in suggestion:
                    report += f"│    理由: {suggestion.get('reason', 'N/A')}\n"
            else:
                report += f"│ 💡 交易建議: {suggestion}\n"
        else:
            # 如果沒有交易建議，根據狀態生成
            if current_iv > high_threshold:
                report += f"│ 💡 交易建議: Short\n"
                report += f"│    理由: 當前IV {current_iv:.1f}% 高於閾值 {high_threshold:.1f}%\n"
            elif current_iv < low_threshold:
                report += f"│ 💡 交易建議: Long\n"
                report += f"│    理由: 當前IV {current_iv:.1f}% 低於閾值 {low_threshold:.1f}%\n"
            else:
                report += f"│ 💡 交易建議: 觀望\n"
                report += f"│    理由: 當前IV {current_iv:.1f}% 在合理範圍內\n"
        
        report += "│\n"
        
        # Requirement 11.2: 說明閾值計算方法
        report += "│ 📐 閾值計算方法:\n"
        percentile_75 = results.get('percentile_75', high_threshold)
        percentile_25 = results.get('percentile_25', low_threshold)
        historical_days = results.get('historical_days', 0)
        
        if data_quality == 'sufficient' or data_quality == 'limited':
            report += f"│   方法: 基於 {historical_days} 天歷史 IV 數據的百分位計算\n"
            report += f"│   高閾值: 75th 百分位 = {percentile_75:.2f}%\n"
            report += f"│   低閾值: 25th 百分位 = {percentile_25:.2f}%\n"
            median_iv = results.get('median_iv', 0)
            if median_iv > 0:
                report += f"│   中位數: {median_iv:.2f}%\n"
        else:
            report += f"│   方法: VIX 靜態閾值（歷史數據不足）\n"
            report += f"│   高閾值: 基準 IV × 1.25\n"
            report += f"│   低閾值: 基準 IV × 0.75\n"
        report += "│\n"
        
        # Requirement 11.4: 與 Module 18 IV Rank 交叉驗證
        if iv_rank_data:
            cross_validation = self._cross_validate_iv_with_rank(
                current_iv, high_threshold, low_threshold, iv_rank_data
            )
            report += "│ 🔄 與 Module 18 IV Rank 交叉驗證:\n"
            report += f"│   Module 18 IV Rank: {cross_validation['iv_rank']:.2f}%\n"
            report += f"│   Module 23 IV 狀態: {display_status}\n"
            report += f"│   一致性: {cross_validation['consistency_emoji']} {cross_validation['consistency']}\n"
            if cross_validation.get('explanation'):
                report += f"│   說明: {cross_validation['explanation']}\n"
            report += "│\n"
        
        # 數據質量和可靠性 (Requirements 5.2, 5.3)
        reliability = results.get('reliability', 'unknown')
        warning = results.get('warning', None)
        
        # 可靠性圖標
        reliability_emoji = {
            'reliable': '✅',
            'moderate': '⚠️',
            'unreliable': '❌',
            'unknown': '❓'
        }.get(reliability, '❓')
        
        # 數據質量圖標
        quality_emoji = {
            'sufficient': '✅',
            'limited': '⚠️',
            'insufficient': '❌'
        }.get(data_quality, '❓')
        
        report += f"│ 📌 數據質量: {quality_emoji} {data_quality}\n"
        report += f"│    歷史數據: {historical_days} 天\n"
        report += f"│    可靠性: {reliability_emoji} {reliability}\n"
        
        # 顯示警告 (Requirements 5.2, 5.3)
        if warning:
            report += f"│\n"
            report += f"│ ⚠️ 警告: {warning}\n"
        elif historical_days < 252 and historical_days > 0:
            report += f"│\n"
            report += f"│ ⚠️ 警告: 歷史數據少於 252 天，建議謹慎參考\n"
        
        # 數據質量說明
        if data_quality == 'insufficient':
            report += f"│    說明: 歷史IV數據不足，使用VIX靜態閾值\n"
        elif data_quality == 'limited':
            report += f"│    說明: 歷史數據有限，結果需謹慎參考\n"
        
        report += "│\n"
        
        # Requirement 11.1: 解釋動態 IV 與 Module 17 隱含波動率的區別
        report += "│ 📖 動態 IV 閾值 vs Module 17 隱含波動率:\n"
        report += "│   ┌────────────────────────────────────────────┐\n"
        report += "│   │ Module 17 (隱含波動率):                    │\n"
        report += "│   │   - 從期權市場價格反推的「當前」波動率     │\n"
        report += "│   │   - 反映市場對未來波動的即時預期           │\n"
        report += "│   │   - 用於期權定價和 Greeks 計算             │\n"
        report += "│   ├────────────────────────────────────────────┤\n"
        report += "│   │ Module 23 (動態 IV 閾值):                  │\n"
        report += "│   │   - 基於歷史 IV 數據計算的「相對」位置     │\n"
        report += "│   │   - 判斷當前 IV 是否偏高/偏低              │\n"
        report += "│   │   - 用於決定買入或賣出期權策略             │\n"
        report += "│   └────────────────────────────────────────────┘\n"
        report += "│\n"
        report += "│ 📖 解讀:\n"
        report += "│   🔴 HIGH: IV 偏高，考慮賣出期權\n"
        report += "│   🟢 NORMAL: IV 合理，等待機會\n"
        report += "│   🔵 LOW: IV 偏低，考慮買入期權\n"
        report += "└────────────────────────────────────────────────┘\n"
        return report
    
    def _get_iv_boundary_warning(self, current_iv: float, high_threshold: float, low_threshold: float) -> str:
        """
        獲取 IV 邊界預警
        
        Requirement 11.3: 當前 IV 接近閾值邊界時提供預警
        
        參數:
            current_iv: 當前 IV
            high_threshold: 高閾值
            low_threshold: 低閾值
        
        返回:
            str: 邊界預警信息，如果不需要預警則返回空字符串
        """
        if high_threshold <= low_threshold:
            return ""
        
        range_width = high_threshold - low_threshold
        # 定義邊界區域為閾值範圍的 10%
        boundary_margin = range_width * 0.10
        
        # 檢查是否接近高閾值
        if current_iv < high_threshold and current_iv >= (high_threshold - boundary_margin):
            distance_pct = ((high_threshold - current_iv) / range_width) * 100
            return f"當前 IV 接近高閾值（距離 {distance_pct:.1f}%），可能即將進入高 IV 區域"
        
        # 檢查是否接近低閾值
        if current_iv > low_threshold and current_iv <= (low_threshold + boundary_margin):
            distance_pct = ((current_iv - low_threshold) / range_width) * 100
            return f"當前 IV 接近低閾值（距離 {distance_pct:.1f}%），可能即將進入低 IV 區域"
        
        return ""
    
    def _cross_validate_iv_with_rank(self, current_iv: float, high_threshold: float, 
                                      low_threshold: float, iv_rank_data: dict) -> dict:
        """
        與 Module 18 IV Rank 進行交叉驗證
        
        Requirement 11.4: 與 Module 18 IV Rank 交叉驗證
        
        參數:
            current_iv: 當前 IV
            high_threshold: 高閾值
            low_threshold: 低閾值
            iv_rank_data: Module 18 IV Rank 數據
        
        返回:
            dict: 交叉驗證結果
        """
        iv_rank = iv_rank_data.get('iv_rank', 0)
        
        # 判斷 Module 23 的狀態
        if current_iv > high_threshold:
            module23_status = 'high'
        elif current_iv < low_threshold:
            module23_status = 'low'
        else:
            module23_status = 'normal'
        
        # 判斷 Module 18 IV Rank 的狀態
        if iv_rank > 70:
            module18_status = 'high'
        elif iv_rank < 30:
            module18_status = 'low'
        else:
            module18_status = 'normal'
        
        # 判斷一致性
        if module23_status == module18_status:
            consistency = '一致'
            consistency_emoji = '✅'
            if module23_status == 'high':
                explanation = "兩個模塊均顯示 IV 偏高，建議賣出期權策略"
            elif module23_status == 'low':
                explanation = "兩個模塊均顯示 IV 偏低，建議買入期權策略"
            else:
                explanation = "兩個模塊均顯示 IV 正常，建議觀望"
        else:
            consistency = '不一致'
            consistency_emoji = '⚠️'
            # 提供不一致的解釋
            if module23_status == 'low' and module18_status == 'normal':
                explanation = "Module 23 顯示低於閾值，但 IV Rank 在正常範圍，可能是閾值設定較寬"
            elif module23_status == 'normal' and module18_status == 'low':
                explanation = "IV Rank 偏低但在動態閾值範圍內，建議參考 IV Rank 的買入信號"
            elif module23_status == 'high' and module18_status == 'normal':
                explanation = "Module 23 顯示高於閾值，但 IV Rank 在正常範圍，可能是閾值設定較窄"
            elif module23_status == 'normal' and module18_status == 'high':
                explanation = "IV Rank 偏高但在動態閾值範圍內，建議參考 IV Rank 的賣出信號"
            else:
                explanation = "兩個模塊判斷不同，建議綜合考慮其他因素"
        
        return {
            'iv_rank': iv_rank,
            'module23_status': module23_status,
            'module18_status': module18_status,
            'consistency': consistency,
            'consistency_emoji': consistency_emoji,
            'explanation': explanation
        }
    
    def _format_module24_technical_direction(self, results: dict) -> str:
        """格式化 Module 24 技術方向分析結果"""
        report = "\n┌─ Module 24: 技術方向分析 ─────────────────────┐\n"
        report += "│\n"
        
        # 檢查是否錯誤或跳過
        if results.get('status') in ['error', 'skipped']:
            report += f"│ x 狀態: {results.get('status')}\n"
            report += f"│ 原因: {results.get('reason', 'N/A')}\n"
            report += "│\n"
            report += "└────────────────────────────────────────────────┘\n"
            return report
        
        # 日線趨勢
        daily = results.get('daily_trend', {})
        trend = daily.get('trend', 'N/A')
        trend_emoji = {'Bullish': '🟢 看漲', 'Bearish': '🔴 看跌', 'Neutral': '🟡 中性'}.get(trend, trend)
        
        report += "│ 📈 日線趨勢分析:\n"
        report += f"│   趨勢方向: {trend_emoji}\n"
        report += f"│   趨勢得分: {daily.get('score', 0):.1f} (-100 到 +100)\n"
        report += "│\n"
        
        # 均線系統
        sma = daily.get('sma', {})
        price = daily.get('price', 0)
        price_vs_sma = daily.get('price_vs_sma', {})
        
        if sma:
            report += "│   均線系統:\n"
            for key, value in sma.items():
                if value:
                    above = '✓' if price_vs_sma.get(f'above_{key}', False) else '✗'
                    report += f"│     {key.upper()}: ${value:.2f} ({above} 價格{'在上' if price_vs_sma.get(f'above_{key}', False) else '在下'})\n"
        
        # MACD
        macd = daily.get('macd', {})
        if macd.get('macd') is not None:
            report += "│\n"
            report += f"│   MACD: {macd.get('macd', 0):.4f}\n"
            report += f"│   Signal: {macd.get('signal', 0):.4f}\n"
            report += f"│   Histogram: {macd.get('histogram', 0):.4f}"
            if macd.get('histogram', 0) > 0:
                report += " (金叉)\n"
            else:
                report += " (死叉)\n"
        
        # RSI
        rsi = daily.get('rsi')
        if rsi:
            report += f"│   RSI (14): {rsi:.1f}"
            if rsi > 70:
                report += " (超買)\n"
            elif rsi < 30:
                report += " (超賣)\n"
            else:
                report += "\n"
        
        # ADX
        adx = daily.get('adx')
        if adx:
            report += f"│   ADX: {adx:.1f}"
            if adx > 25:
                report += " (趨勢明確)\n"
            else:
                report += " (趨勢不明確)\n"
        
        # 日線信號
        signals = daily.get('signals', [])
        if signals:
            report += "│\n"
            report += "│   📋 日線信號:\n"
            for sig in signals[:5]:  # 最多顯示5個
                report += f"│     • {sig}\n"
        
        # 15分鐘入場信號
        intraday = results.get('intraday_signal', {})
        if intraday.get('available', False):
            report += "│\n"
            report += "│ 🎯 15分鐘入場信號:\n"
            
            signal = intraday.get('signal', 'N/A')
            signal_emoji = {
                'Enter': '✅ 可以入場',
                'Wait_Pullback': '⏳ 等待回調',
                'Wait_Breakout': '⏳ 等待突破',
                'Hold': '⏸️ 觀望'
            }.get(signal, signal)
            
            report += f"│   入場信號: {signal_emoji}\n"
            
            # 15分鐘指標
            intraday_rsi = intraday.get('rsi')
            if intraday_rsi:
                report += f"│   RSI (9): {intraday_rsi:.1f}"
                if intraday_rsi > 70:
                    report += " (短線超買)\n"
                elif intraday_rsi < 30:
                    report += " (短線超賣)\n"
                else:
                    report += "\n"
            
            stoch = intraday.get('stochastic', {})
            if stoch.get('k'):
                report += f"│   Stochastic: K={stoch.get('k', 0):.1f}, D={stoch.get('d', 0):.1f}\n"
            
            # 15分鐘信號
            intraday_signals = intraday.get('signals', [])
            if intraday_signals:
                report += "│\n"
                report += "│   📋 15分鐘信號:\n"
                for sig in intraday_signals[:3]:
                    report += f"│     • {sig}\n"
        else:
            report += "│\n"
            report += "│ 🎯 15分鐘入場信號: 數據不可用\n"
        
        # 綜合方向
        report += "│\n"
        report += "│ ═══════════════════════════════════════════════\n"
        
        direction = results.get('combined_direction', 'N/A')
        confidence = results.get('confidence', 'N/A')
        direction_emoji = {'Call': '📈 Call (看漲)', 'Put': '📉 Put (看跌)', 'Neutral': '➖ 中性'}.get(direction, direction)
        confidence_emoji = {'High': '🟢', 'Medium': '🟡', 'Low': '🔴'}.get(confidence, '')
        
        report += f"│ 🎯 綜合方向: {direction_emoji}\n"
        report += f"│ 📊 信心度: {confidence_emoji} {confidence}\n"
        
        entry_timing = results.get('entry_timing', '')
        if entry_timing:
            report += f"│ ⏰ 入場時機: {entry_timing}\n"
        
        recommendation = results.get('recommendation', '')
        if recommendation:
            report += "│\n"
            report += f"│ 💡 建議: {recommendation}\n"
        
        report += "│\n"
        report += f"│ 📌 數據來源: {results.get('data_source', 'N/A')}\n"
        report += "└────────────────────────────────────────────────┘\n"
        return report
    
    def _format_module25_volatility_smile(self, results: dict) -> str:
        """格式化 Module 25 波動率微笑分析結果"""
        report = "\n┌─ Module 25: 波動率微笑分析 ───────────────────┐\n"
        report += "│\n"
        
        # 檢查是否錯誤或跳過
        if results.get('status') in ['error', 'skipped']:
            report += f"│ x 狀態: {results.get('status')}\n"
            report += f"│ 原因: {results.get('reason', 'N/A')}\n"
            report += "│\n"
            report += "└────────────────────────────────────────────────┘\n"
            return report
        
        # 基本指標
        report += "│ 📊 基本指標:\n"
        report += f"│   當前股價: ${results.get('current_price', 0):.2f}\n"
        report += f"│   ATM 行使價: ${results.get('atm_strike', 0):.2f}\n"
        report += f"│   ATM IV: {results.get('atm_iv', 0):.2f}%\n"
        report += "│\n"
        
        # IV Skew 分析
        skew = results.get('skew', 0)
        skew_type = results.get('skew_type', 'neutral')
        skew_25delta = results.get('skew_25delta', 0)
        
        report += "│ 📈 偏斜分析:\n"
        report += f"│   Skew (OTM Put - OTM Call): {skew:.2f}%\n"
        report += f"│   25-Delta Skew: {skew_25delta:.2f}%\n"
        
        # Skew 類型解讀
        skew_emoji = {'put_skew': '📉 看跌傾斜', 'call_skew': '📈 看漲傾斜', 'neutral': '➖ 中性'}.get(skew_type, skew_type)
        report += f"│   傾斜類型: {skew_emoji}\n"
        report += "│\n"
        
        # IV Smile 分析
        smile_curve = results.get('smile_curve', 0)
        smile_shape = results.get('smile_shape', 'neutral')
        smile_steepness = results.get('smile_steepness', 0)
        
        report += "│ 😊 微笑分析:\n"
        report += f"│   微笑曲線: {smile_curve:.2f}%\n"
        
        shape_emoji = {
            'smile': '😊 U形微笑',
            'smirk': '😏 微笑+傾斜',
            'skew': '📐 傾斜',
            'flat': '➖ 平坦',
            'neutral': '➖ 中性'
        }.get(smile_shape, smile_shape)
        report += f"│   形狀: {shape_emoji}\n"
        report += f"│   陡峭度: {smile_steepness:.3f} (0-1)\n"
        report += "│\n"
        
        # IV 環境
        iv_env = results.get('iv_environment', 'neutral')
        env_emoji = {
            'steep_smile': '📈 陡峭微笑',
            'gentle_smile': '😊 溫和微笑',
            'put_skew': '📉 看跌傾斜',
            'call_skew': '📈 看漲傾斜',
            'flat_iv': '➖ 平坦'
        }.get(iv_env, iv_env)
        
        report += f"│ 🌡️ IV 環境: {env_emoji}\n"
        report += "│\n"
        
        # IV 統計
        report += "│ 📊 IV 統計:\n"
        report += f"│   Call IV: {results.get('call_iv_mean', 0):.2f}% ± {results.get('call_iv_std', 0):.2f}%\n"
        report += f"│   Put IV: {results.get('put_iv_mean', 0):.2f}% ± {results.get('put_iv_std', 0):.2f}%\n"
        report += "│\n"
        
        # 定價異常
        anomaly_count = results.get('anomaly_count', 0)
        if anomaly_count > 0:
            report += f"│ ⚠️ 定價異常: 發現 {anomaly_count} 個\n"
            anomalies = results.get('pricing_anomalies', [])
            for a in anomalies[:3]:  # 最多顯示3個
                report += f"│   • {a.get('type', 'N/A').upper()} ${a.get('strike', 0):.2f}: IV={a.get('iv', 0):.2f}% ({a.get('severity', 'N/A')})\n"
            report += "│\n"
        
        # 交易建議
        recommendations = results.get('trading_recommendations', [])
        confidence = results.get('recommendation_confidence', 0)
        
        if recommendations:
            report += "│ 💡 交易建議:\n"
            for rec in recommendations[:3]:
                report += f"│   • {rec}\n"
            report += f"│   信心度: {confidence*100:.0f}%\n"
        
        report += "│\n"
        report += f"│ 📌 計算時間: {results.get('calculation_date', 'N/A')}\n"
        report += "└────────────────────────────────────────────────┘\n"
        return report
    
    def _format_module26_long_option_analysis(self, results: dict) -> str:
        """格式化 Module 26 Long 期權成本效益分析結果"""
        report = "\n┌─ Module 26: Long 期權成本效益分析 ─────────────┐\n"
        report += "│\n"
        
        # 檢查是否錯誤或跳過
        if results.get('status') in ['error', 'skipped']:
            report += f"│ x 狀態: {results.get('status')}\n"
            report += f"│ 原因: {results.get('reason', 'N/A')}\n"
            report += "│\n"
            report += "└────────────────────────────────────────────────┘\n"
            return report
        
        # Long Call 分析
        long_call = results.get('long_call', {})
        if long_call.get('status') == 'success':
            report += "│ 📈 Long Call 分析:\n"
            
            # 基本信息
            inp = long_call.get('input', {})
            report += f"│   行使價: ${inp.get('strike_price', 0):.2f}\n"
            report += f"│   權利金: ${inp.get('premium', 0):.2f}/股\n"
            
            # 成本
            cost = long_call.get('cost_analysis', {})
            report += f"│   總成本: ${cost.get('total_cost', 0):.2f}\n"
            report += f"│   最大虧損: ${cost.get('max_loss', 0):.2f} (100%)\n"
            
            # 盈虧平衡點
            be = long_call.get('breakeven', {})
            report += f"│   盈虧平衡點: ${be.get('price', 0):.2f} ({be.get('distance_pct', 0):+.1f}%)\n"
            report += f"│   {be.get('interpretation', '')}\n"
            
            # 槓桿
            lev = long_call.get('leverage', {})
            report += f"│   槓桿倍數: {lev.get('effective_leverage', 0):.1f}x {lev.get('rating', '')}\n"
            report += f"│   {lev.get('explanation', '')}\n"
            
            # 評分
            score = long_call.get('score', {})
            report += f"│   📊 評分: {score.get('total_score', 0)}/100 ({score.get('grade', 'N/A')}) - {score.get('grade_description', '')}\n"
            
            # Theta
            theta = long_call.get('theta_analysis', {})
            report += f"│   ⏱️ Theta: ${theta.get('daily_decay_dollar', 0):.2f}/天 {theta.get('risk_level', '')}\n"
            
            report += "│\n"
        
        # Long Put 分析
        long_put = results.get('long_put', {})
        if long_put.get('status') == 'success':
            report += "│ 📉 Long Put 分析:\n"
            
            # 基本信息
            inp = long_put.get('input', {})
            report += f"│   行使價: ${inp.get('strike_price', 0):.2f}\n"
            report += f"│   權利金: ${inp.get('premium', 0):.2f}/股\n"
            
            # 成本
            cost = long_put.get('cost_analysis', {})
            report += f"│   總成本: ${cost.get('total_cost', 0):.2f}\n"
            report += f"│   最大虧損: ${cost.get('max_loss', 0):.2f} (100%)\n"
            
            # 盈虧平衡點
            be = long_put.get('breakeven', {})
            report += f"│   盈虧平衡點: ${be.get('price', 0):.2f} ({be.get('distance_pct', 0):+.1f}%)\n"
            report += f"│   {be.get('interpretation', '')}\n"
            
            # 槓桿
            lev = long_put.get('leverage', {})
            report += f"│   槓桿倍數: {lev.get('effective_leverage', 0):.1f}x {lev.get('rating', '')}\n"
            report += f"│   {lev.get('explanation', '')}\n"
            
            # 評分
            score = long_put.get('score', {})
            report += f"│   📊 評分: {score.get('total_score', 0)}/100 ({score.get('grade', 'N/A')}) - {score.get('grade_description', '')}\n"
            
            # Theta
            theta = long_put.get('theta_analysis', {})
            report += f"│   ⏱️ Theta: ${theta.get('daily_decay_dollar', 0):.2f}/天 {theta.get('risk_level', '')}\n"
            
            report += "│\n"
        
        # 比較結果
        comparison = results.get('comparison', {})
        if comparison:
            report += "│ ═══════════════════════════════════════════════\n"
            report += "│ 🎯 Long 期權比較:\n"
            report += f"│   Long Call 評分: {comparison.get('call_score', 0)}\n"
            report += f"│   Long Put 評分: {comparison.get('put_score', 0)}\n"
            report += f"│   推薦: {comparison.get('better_choice', 'N/A')}\n"
            report += f"│   原因: {comparison.get('reason', '')}\n"
            report += "│\n"
        
        # 情境分析表（只顯示 Long Call 的關鍵情境）
        if long_call.get('status') == 'success':
            scenarios = long_call.get('scenarios', [])
            if scenarios:
                report += "│ 📊 Long Call 情境分析:\n"
                report += "│   股價變動 | 到期股價  | 損益      | 收益率\n"
                report += "│   ─────────┼──────────┼──────────┼────────\n"
                for s in scenarios:
                    if s['stock_change_pct'] in [-10, 0, 10, 20]:  # 只顯示關鍵情境
                        report += f"│   {s['stock_change_pct']:+4d}%    | ${s['stock_price']:>7.2f} | ${s['profit_loss']:>+8.2f} | {s['profit_loss_pct']:>+6.1f}%\n"
                report += "│\n"
        
        # 交易建議
        rec = long_call.get('recommendation', {}) if long_call.get('status') == 'success' else {}
        if rec:
            report += "│ 💡 交易建議:\n"
            for r in rec.get('recommendations', []):
                report += f"│   {r}\n"
            for w in rec.get('warnings', []):
                report += f"│   {w}\n"
            report += f"│   {rec.get('position_suggestion', '')}\n"
        
        report += "│\n"
        report += f"│ 📌 分析時間: {results.get('analysis_time', 'N/A')}\n"
        report += "└────────────────────────────────────────────────┘\n"
        return report
    
    def _format_module27_multi_expiry_comparison(self, results: dict) -> str:
        """格式化 Module 27 多到期日比較分析結果（增強版 - 四種策略）"""
        report = "\n┌─ Module 27: 多到期日比較分析（增強版）─────────────┐\n"
        report += "│\n"
        
        # 檢查是否錯誤或跳過
        if results.get('status') in ['error', 'skipped']:
            report += f"│ x 狀態: {results.get('status')}\n"
            report += f"│ 原因: {results.get('reason', 'N/A')}\n"
            report += "│\n"
            report += "└────────────────────────────────────────────────┘\n"
            return report
        
        # 基本信息
        report += f"│ 📊 股票: {results.get('ticker', 'N/A')}\n"
        report += f"│ 💵 當前股價: ${results.get('current_price', 0):.2f}\n"
        report += f"│ 📅 可用到期日總數: {results.get('total_expirations_available', 0)}\n"
        report += f"│ 📅 ≤90天到期日: {results.get('expirations_within_90_days', 0)}\n"
        report += f"│ 📅 成功分析到期日: {results.get('expirations_analyzed', 0)}\n"
        report += "│\n"
        
        # 到期日列表
        exp_list = results.get('expiration_list', [])
        if exp_list:
            report += "│ 📋 分析的到期日:\n"
            for i, exp in enumerate(exp_list[:8], 1):  # 最多顯示8個
                report += f"│   {i}. {exp}\n"
            if len(exp_list) > 8:
                report += f"│   ... 還有 {len(exp_list) - 8} 個\n"
            report += "│\n"
        
        # 四種策略結果
        strategy_results = results.get('strategy_results', {})
        strategy_names = {
            'long_call': '📈 Long Call（看漲買權）',
            'long_put': '📉 Long Put（看跌買權）',
            'short_call': '📊 Short Call（看漲賣權）',
            'short_put': '📊 Short Put（看跌賣權）'
        }
        
        for strategy_type, strategy_name in strategy_names.items():
            strategy_data = strategy_results.get(strategy_type, {})
            if not strategy_data or strategy_data.get('status') != 'success':
                continue
            
            report += f"│ {strategy_name}\n"
            report += "│ ─────────────────────────────────────────────\n"
            
            # 比較表格
            comparison = strategy_data.get('comparison_table', [])
            if comparison:
                report += "│ ┌──────────────┬──────┬────────┬───────┬───────┬───────┐\n"
                report += "│ │ 到期日       │ 天數 │ 權利金 │ IV%   │ Theta │ 評分  │\n"
                report += "│ ├──────────────┼──────┼────────┼───────┼───────┼───────┤\n"
                
                for exp in comparison[:5]:  # 最多顯示5個
                    expiry = str(exp.get('expiration', 'N/A'))[:10]
                    days = exp.get('days', 0) or 0
                    premium = exp.get('premium', 0) or 0.0
                    iv = exp.get('iv', 0) or 0.0
                    theta_pct = exp.get('theta_pct', 0) or 0.0
                    score = exp.get('score', 0) or 0
                    grade = exp.get('grade', '-') or '-'
                    
                    report += f"│ │ {expiry:12} │ {days:4} │ ${premium:5.2f} │ {iv:5.1f} │ {theta_pct:5.2f} │ {score:3}({grade}) │\n"
                
                report += "│ └──────────────┴──────┴────────┴───────┴───────┴───────┘\n"
            
            # 推薦
            rec = strategy_data.get('recommendation', {})
            if rec and rec.get('best_expiration'):
                report += f"│ 🎯 最佳: {rec.get('best_expiration')} ({rec.get('best_days')}天)\n"
                report += f"│    評分: {rec.get('best_score')} ({rec.get('best_grade')}) | 權利金: ${rec.get('best_premium', 0):.2f}\n"
                
                # 推薦理由（簡化）
                reasons = rec.get('reasons', [])
                if reasons:
                    report += f"│    理由: {reasons[0]}\n"
            
            report += "│\n"
        
        # 綜合建議
        report += "│ 💡 綜合建議:\n"
        
        # 找出各策略的最佳到期日
        best_picks = []
        for strategy_type in ['long_call', 'long_put', 'short_call', 'short_put']:
            strategy_data = strategy_results.get(strategy_type, {})
            if strategy_data.get('status') == 'success':
                rec = strategy_data.get('recommendation', {})
                if rec.get('best_expiration'):
                    best_picks.append({
                        'strategy': strategy_type,
                        'expiration': rec.get('best_expiration'),
                        'days': rec.get('best_days'),
                        'score': rec.get('best_score'),
                        'grade': rec.get('best_grade')
                    })
        
        if best_picks:
            # 按評分排序
            best_picks.sort(key=lambda x: x.get('score', 0), reverse=True)
            top_pick = best_picks[0]
            
            strategy_display = {
                'long_call': 'Long Call',
                'long_put': 'Long Put',
                'short_call': 'Short Call',
                'short_put': 'Short Put'
            }
            
            report += f"│   最高評分策略: {strategy_display.get(top_pick['strategy'], top_pick['strategy'])}\n"
            report += f"│   最佳到期日: {top_pick['expiration']} ({top_pick['days']}天)\n"
            report += f"│   評分: {top_pick['score']} ({top_pick['grade']})\n"
        
        report += "│\n"
        report += f"│ 📌 分析時間: {results.get('analysis_date', 'N/A')}\n"
        report += "└────────────────────────────────────────────────┘\n"
        return report
    
    def _format_module28_position_calculator(self, results: dict) -> str:
        """格式化 Module 28 資金倉位計算器結果"""
        report = "\n┌─ Module 28: 資金倉位計算器 ─────────────────────┐\n"
        report += "│\n"
        
        # 檢查是否錯誤或跳過
        if results.get('status') in ['error', 'skipped']:
            report += f"│ x 狀態: {results.get('status')}\n"
            report += f"│ 原因: {results.get('reason', 'N/A')}\n"
            report += "│\n"
            report += "└────────────────────────────────────────────────┘\n"
            return report
        
        # 資金信息
        capital = results.get('capital_info', {})
        report += "│ 💰 資金概況:\n"
        report += f"│   總資金: {capital.get('currency', 'USD')} {capital.get('total_capital', 0):,.0f}\n"
        report += f"│   USD 等值: ${capital.get('total_capital_usd', 0):,.2f}\n"
        report += "│\n"
        
        # 風險參數
        risk_level = results.get('risk_level', 'moderate')
        risk_emoji = {'conservative': '🟢 保守', 'moderate': '🟡 穩健', 'aggressive': '🔴 積極'}.get(risk_level, risk_level)
        report += f"│ ⚙️ 風險偏好: {risk_emoji}\n"
        report += "│\n"
        
        # 期權信息
        opt_info = results.get('option_info', {})
        report += "│ 📊 期權信息:\n"
        report += f"│   權利金: ${opt_info.get('premium_per_share', 0):.2f}/股\n"
        report += f"│   每張成本: ${opt_info.get('cost_per_contract', 0):.2f}\n"
        report += "│\n"
        
        # 倉位建議
        pos = results.get('position_recommendation', {})
        report += "│ 🎯 倉位建議:\n"
        report += f"│   建議張數: {pos.get('recommended_contracts', 0)} 張\n"
        report += f"│   最大張數: {pos.get('max_contracts', 0)} 張\n"
        report += f"│   投入金額: ${pos.get('actual_investment_usd', 0):.2f}\n"
        report += f"│   佔總資金: {pos.get('investment_pct', 0):.1f}%\n"
        report += "│\n"
        
        # 風險分析
        risk = results.get('risk_analysis', {})
        report += "│ ⚠️ 風險分析:\n"
        report += f"│   策略類型: {risk.get('strategy_type', 'N/A')}\n"
        report += f"│   最大虧損: ${risk.get('max_loss_usd', 0):.2f}\n"
        report += f"│   虧損比例: {risk.get('max_loss_pct', 0):.1f}%\n"
        report += f"│   風險評級: {risk.get('risk_rating', 'N/A')}\n"
        report += "│\n"
        
        # 止損建議
        stop = results.get('stop_loss', {})
        report += "│ 🛑 止損建議:\n"
        report += f"│   止損比例: {stop.get('suggested_stop_loss_pct', 0)}%\n"
        report += f"│   止損價格: ${stop.get('stop_loss_price', 0):.2f}\n"
        report += f"│   止損金額: ${stop.get('stop_loss_amount_usd', 0):.2f}\n"
        report += "│\n"
        
        # 警告
        warnings = results.get('warnings', [])
        if warnings:
            report += "│ 💡 提醒:\n"
            for w in warnings:
                report += f"│   {w}\n"
            report += "│\n"
        
        # 資金管理建議
        summary = results.get('capital_summary', {})
        recommendations = summary.get('recommendations', [])
        if recommendations:
            report += "│ 📋 資金管理建議:\n"
            for rec in recommendations[:3]:  # 最多顯示3條
                report += f"│   {rec}\n"
        
        report += "│\n"
        report += f"│ 📌 分析時間: {results.get('analysis_date', 'N/A')}\n"
        report += "└────────────────────────────────────────────────┘\n"
        return report
    
    def _format_consolidated_recommendation(self, calculation_results: dict) -> str:
        """
        格式化綜合建議區塊
        
        Requirements: 8.1, 8.2, 8.3, 8.4
        - 在報告末尾添加「綜合建議」區塊
        - 標示矛盾並提供解釋
        - 說明採納的建議及原因
        
        參數:
            calculation_results: 所有模塊的計算結果
            
        返回:
            str: 格式化的綜合建議報告
        """
        try:
            # 執行一致性檢查
            consistency_result = self.consistency_checker.check_consistency(calculation_results)
            
            # 使用一致性檢查器的格式化方法生成報告
            return self.consistency_checker.format_consolidated_recommendation(consistency_result)
        except Exception as e:
            logger.warning(f"! 綜合建議生成失敗: {e}")
            # 返回簡單的錯誤提示
            report = "\n" + "=" * 70 + "\n"
            report += "綜合建議\n"
            report += "=" * 70 + "\n\n"
            report += f"⚠️ 無法生成綜合建議: {str(e)}\n\n"
            return report
    
    def _format_data_source_summary(self, raw_data: dict, calculation_results: dict, api_status: dict = None) -> str:
        """
        格式化數據來源摘要（增強版）
        
        Requirements: 14.1, 14.2, 14.3, 14.4, 14.5
        - 14.1: 列出每個模塊使用的實際數據源
        - 14.2: 標示降級原因和影響
        - 14.3: 說明 API 故障對報告的具體影響
        - 14.4: 警告數據一致性問題
        - 14.5: 提供關鍵數據點的來源和時間戳
        """
        from datetime import datetime
        
        # 確保 raw_data 不為 None
        if raw_data is None:
            raw_data = {}
        
        report = "\n" + "=" * 70 + "\n"
        report += "數據來源摘要\n"
        report += "=" * 70 + "\n\n"
        
        # ===== 1. 各模塊實際數據源 (Requirement 14.1) =====
        report += "📊 各模塊數據來源:\n"
        report += "─" * 70 + "\n"
        
        # 定義模塊與數據源的映射
        module_data_sources = self._get_module_data_sources(raw_data, calculation_results, api_status)
        
        for module_name, source_info in module_data_sources.items():
            status_icon = "✓" if source_info.get('available', False) else "✗"
            source = source_info.get('source', 'N/A')
            degraded = source_info.get('degraded', False)
            
            if degraded:
                report += f"  {status_icon} {module_name}: {source} ⚠️ (降級)\n"
            else:
                report += f"  {status_icon} {module_name}: {source}\n"
        
        report += "\n"
        
        # ===== 2. 降級使用情況 (Requirement 14.2) =====
        if api_status and api_status.get('fallback_used'):
            report += "⚠️ 數據源降級記錄:\n"
            report += "─" * 70 + "\n"
            
            fallback_used = api_status.get('fallback_used', {})
            for data_type, sources in fallback_used.items():
                # 獲取降級原因
                reason = self._get_degradation_reason(data_type, api_status)
                impact = self._get_degradation_impact(data_type)
                
                report += f"  • {data_type}:\n"
                report += f"    使用來源: {', '.join(sources) if isinstance(sources, list) else sources}\n"
                report += f"    降級原因: {reason}\n"
                report += f"    影響: {impact}\n"
            
            report += "\n"
        
        # ===== 3. API 故障記錄及影響 (Requirement 14.3) =====
        if api_status and api_status.get('api_failures'):
            report += "❌ API 故障記錄及影響:\n"
            report += "─" * 70 + "\n"
            
            api_failures = api_status.get('api_failures', {})
            for api_name, failures in api_failures.items():
                failure_count = len(failures) if isinstance(failures, list) else failures
                impact = self._get_api_failure_impact(api_name)
                
                report += f"  • {api_name}: {failure_count} 次故障\n"
                report += f"    對報告影響: {impact}\n"
            
            report += "\n"
        
        # ===== 4. 數據一致性檢查 (Requirement 14.4) =====
        consistency_warnings = self._check_data_consistency(raw_data, calculation_results, api_status)
        
        if consistency_warnings:
            report += "⚠️ 數據一致性警告:\n"
            report += "─" * 70 + "\n"
            for warning in consistency_warnings:
                report += f"  • {warning}\n"
            report += "\n"
        else:
            report += "✓ 數據一致性: 無異常\n\n"
        
        # ===== Requirements 5.2, 5.3: IV 差異警告顯示 =====
        iv_comparison = calculation_results.get('iv_comparison', {})
        iv_warning = calculation_results.get('iv_warning')
        
        report += "📊 IV (隱含波動率) 比較:\n"
        report += "─" * 70 + "\n"
        
        if iv_comparison:
            market_iv = iv_comparison.get('market_iv', 0)
            atm_iv = iv_comparison.get('atm_iv', 0)
            diff_pct = iv_comparison.get('difference_pct', 0)
            has_warning = iv_comparison.get('has_warning', False)
            
            report += f"  • Market IV (數據源): {market_iv:.2f}%\n"
            report += f"  • ATM IV (Module 17 計算): {atm_iv:.2f}%\n"
            report += f"  • 差異: {diff_pct:.1f}%\n"
            
            if has_warning:
                report += f"\n  ⚠️ IV 差異警告:\n"
                report += f"    {iv_warning}\n"
                report += f"    可能原因:\n"
                report += f"      - 數據源 IV 可能不準確或過時\n"
                report += f"      - 市場存在異常波動\n"
                report += f"      - 波動率微笑/偏斜效應\n"
                report += f"    建議: 優先使用 ATM IV (Module 17) 進行分析\n"
            else:
                report += f"\n  ✓ IV 一致性: 正常 (差異 < 20%)\n"
        else:
            report += "  • 無 IV 比較數據 (Module 17 可能未執行或未收斂)\n"
        
        report += "\n"
        
        # ===== 5. 關鍵數據點來源和時間戳 (Requirement 14.5) =====
        report += "📋 關鍵數據點來源:\n"
        report += "─" * 70 + "\n"
        
        key_data_points = self._get_key_data_points(raw_data, calculation_results, api_status)
        
        for data_point in key_data_points:
            report += f"  • {data_point['name']}:\n"
            report += f"    數值: {data_point['value']}\n"
            report += f"    來源: {data_point['source']}\n"
            if data_point.get('timestamp'):
                report += f"    時間: {data_point['timestamp']}\n"
        
        report += "\n"
        
        # ===== Finviz 數據可用性 (保留原有功能) =====
        report += "📊 Finviz 數據狀態:\n"
        report += "─" * 70 + "\n"
        
        finviz_fields = {
            'insider_own': '內部人持股',
            'inst_own': '機構持股',
            'short_float': '做空比例',
            'avg_volume': '平均成交量',
            'peg_ratio': 'PEG 比率',
            'roe': 'ROE',
            'profit_margin': '淨利潤率',
            'debt_eq': '負債/股本比',
            'atr': 'ATR',
            'rsi': 'RSI',
            'beta': 'Beta'
        }
        
        available_fields = []
        missing_fields = []
        
        for field_key, field_name in finviz_fields.items():
            if raw_data.get(field_key) is not None:
                available_fields.append(field_name)
            else:
                missing_fields.append(field_name)
        
        report += f"* 可用字段 ({len(available_fields)}/{len(finviz_fields)}):\n"
        if available_fields:
            for field in available_fields:
                report += f"  • {field}\n"
        else:
            report += "  無\n"
        
        report += f"\n! 缺失字段 ({len(missing_fields)}/{len(finviz_fields)}):\n"
        if missing_fields:
            for field in missing_fields:
                report += f"  • {field}\n"
        else:
            report += "  無\n"
        
        report += "\n"
        
        # Module 20 執行狀態
        report += "🏥 Module 20 (基本面健康檢查) 狀態:\n"
        report += "─" * 70 + "\n"
        
        module20 = calculation_results.get('module20_fundamental_health', {})
        if module20.get('status') == 'skipped':
            report += f"狀態: ! 跳過執行\n"
            report += f"原因: {module20.get('reason', 'N/A')}\n"
            report += f"可用指標: {module20.get('available_metrics', 0)}/5\n"
            report += f"需要指標: {module20.get('required_metrics', 3)}/5\n"
        elif 'health_score' in module20:
            report += f"狀態: * 執行成功\n"
            report += f"健康分數: {module20.get('health_score', 0)}/100\n"
            report += f"等級: {module20.get('grade', 'N/A')}\n"
            report += f"使用指標: {module20.get('available_metrics', 0)}/5\n"
            report += f"數據來源: {module20.get('data_source', 'N/A')}\n"
        else:
            report += f"狀態: x 未執行\n"
        
        report += "\n"
        
        # Module 3 價格來源
        report += "💰 Module 3 (套戥水位) 價格來源:\n"
        report += "─" * 70 + "\n"
        
        module3 = calculation_results.get('module3_arbitrage_spread', {})
        if module3.get('status') == 'skipped':
            report += f"狀態: ! 跳過執行\n"
            report += f"原因: {module3.get('reason', 'N/A')}\n"
        elif module3.get('status') == 'error':
            report += f"狀態: x 執行錯誤\n"
            report += f"原因: {module3.get('reason', 'N/A')}\n"
        elif 'theoretical_price_source' in module3:
            report += f"狀態: * 執行成功\n"
            report += f"理論價來源: {module3.get('theoretical_price_source', 'N/A')}\n"
            report += f"市場價格: ${module3.get('market_price', 0):.2f}\n"
            report += f"理論價格: ${module3.get('theoretical_price', 0):.2f}\n"
            report += f"說明: {module3.get('note', 'N/A')}\n"
        else:
            report += f"狀態: x 未執行\n"
        
        report += "\n"
        
        # 數據完整性總結
        report += "📋 數據完整性總結:\n"
        report += "─" * 70 + "\n"
        
        total_modules = len(calculation_results)
        successful_modules = sum(1 for m in calculation_results.values() 
                                if not (isinstance(m, dict) and m.get('status') in ['skipped', 'error']))
        
        report += f"總模塊數: {total_modules}\n"
        report += f"成功執行: {successful_modules}\n"
        report += f"跳過/錯誤: {total_modules - successful_modules}\n"
        report += f"完整性: {(successful_modules/total_modules*100):.1f}%\n"
        
        report += "\n"
        report += "=" * 70 + "\n"
        
        return report
    
    def _get_module_data_sources(self, raw_data: dict, calculation_results: dict, api_status: dict = None) -> dict:
        """
        獲取各模塊的實際數據來源
        
        Requirements: 14.1
        """
        fallback_used = api_status.get('fallback_used', {}) if api_status else {}
        
        # 確保 raw_data 不為 None
        if raw_data is None:
            raw_data = {}
        
        # 定義模塊與數據類型的映射
        module_sources = {
            'Module 1 (支撐阻力)': {
                'source': self._determine_source('stock_info', fallback_used, 'Yahoo Finance'),
                'available': raw_data.get('current_price') is not None,
                'degraded': 'stock_info' in fallback_used
            },
            'Module 3 (套戥水位)': {
                'source': calculation_results.get('module3_arbitrage_spread', {}).get('theoretical_price_source', 'Module 15 (Black-Scholes)'),
                'available': calculation_results.get('module3_arbitrage_spread', {}).get('status') != 'skipped',
                'degraded': False
            },
            'Module 13 (倉位分析)': {
                'source': self._determine_source('option_chain', fallback_used, 'Yahoo Finance'),
                'available': calculation_results.get('module13_position_analysis') is not None,
                'degraded': 'option_chain' in fallback_used
            },
            'Module 14 (監察崗位)': {
                'source': 'Finviz' if raw_data.get('rsi') is not None else 'N/A',
                'available': raw_data.get('rsi') is not None,
                'degraded': False
            },
            'Module 15 (Black-Scholes)': {
                'source': '自主計算 (BS Calculator)',
                'available': calculation_results.get('module15_black_scholes') is not None,
                'degraded': False
            },
            'Module 16 (Greeks)': {
                'source': self._determine_source('option_greeks', fallback_used, '自主計算'),
                'available': calculation_results.get('module16_greeks') is not None,
                'degraded': 'option_greeks' in fallback_used
            },
            'Module 17 (隱含波動率)': {
                'source': '自主計算 (IV Calculator)',
                'available': calculation_results.get('module17_implied_volatility') is not None,
                'degraded': False
            },
            'Module 18 (歷史波動率)': {
                'source': self._determine_source('historical_data', fallback_used, 'yfinance'),
                'available': calculation_results.get('module18_historical_volatility') is not None,
                'degraded': 'historical_data' in fallback_used
            },
            'Module 20 (基本面)': {
                'source': calculation_results.get('module20_fundamental_health', {}).get('data_source', 'Finviz'),
                'available': calculation_results.get('module20_fundamental_health', {}).get('status') != 'skipped',
                'degraded': False
            },
            'Module 21 (動量過濾)': {
                'source': self._determine_source('historical_data', fallback_used, 'yfinance'),
                'available': calculation_results.get('module21_momentum_filter') is not None,
                'degraded': 'historical_data' in fallback_used
            },
            'Module 22 (最佳行使價)': {
                'source': self._determine_source('option_chain', fallback_used, 'Yahoo Finance'),
                'available': calculation_results.get('module22_optimal_strike') is not None,
                'degraded': 'option_chain' in fallback_used
            },
            'Module 24 (技術方向)': {
                'source': self._determine_source('historical_data', fallback_used, 'yfinance'),
                'available': calculation_results.get('module24_technical_direction') is not None,
                'degraded': 'historical_data' in fallback_used
            }
        }
        
        return module_sources
    
    def _determine_source(self, data_type: str, fallback_used: dict, default: str) -> str:
        """確定數據來源"""
        if data_type in fallback_used:
            sources = fallback_used[data_type]
            if isinstance(sources, list) and sources:
                last_source = sources[-1]
                if isinstance(last_source, dict):
                    return str(last_source.get('source', default))
                return str(last_source)
            return str(sources)
        return default
    
    def _get_degradation_reason(self, data_type: str, api_status: dict) -> str:
        """
        獲取降級原因
        
        Requirements: 14.2
        """
        api_failures = api_status.get('api_failures', {})
        
        # 根據數據類型和故障記錄推斷原因
        reason_map = {
            'stock_info': '主要數據源 (IBKR/Yahoo) 無法獲取股票信息',
            'option_chain': '期權鏈數據獲取失敗，使用備用來源',
            'historical_data': '歷史數據 API 響應超時或數據不完整',
            'risk_free_rate': '聯邦儲備數據 API 不可用',
            'vix': 'VIX 數據獲取失敗',
            'option_greeks': 'Greeks 數據不可用，使用自主計算',
            'earnings_calendar': '財報日曆 API 不可用',
            'dividend_calendar': '股息日曆數據獲取失敗'
        }
        
        # 檢查是否有相關 API 故障
        for api_name, failures in api_failures.items():
            api_name = str(api_name)
            data_type = str(data_type)
            if api_name.lower() in data_type.lower() or data_type.lower() in api_name.lower():
                if isinstance(failures, list) and failures:
                    return f"{api_name} 故障: {failures[-1] if isinstance(failures[-1], str) else '連接失敗'}"
        
        return reason_map.get(data_type, '主要數據源不可用')
    
    def _get_degradation_impact(self, data_type: str) -> str:
        """
        獲取降級對報告的影響
        
        Requirements: 14.2
        """
        impact_map = {
            'stock_info': '股價數據可能有延遲，影響即時分析準確性',
            'option_chain': '期權數據可能不完整，影響行使價推薦',
            'historical_data': '歷史波動率計算可能受影響',
            'risk_free_rate': '使用預設利率，可能影響期權定價',
            'vix': 'VIX 數據可能不是最新，影響市場情緒判斷',
            'option_greeks': 'Greeks 為自主計算值，可能與市場報價略有差異',
            'earnings_calendar': '財報日期可能不準確',
            'dividend_calendar': '股息數據可能不完整'
        }
        
        return impact_map.get(data_type, '可能影響相關模塊的分析準確性')
    
    def _get_api_failure_impact(self, api_name: str) -> str:
        """
        獲取 API 故障對報告的具體影響
        
        Requirements: 14.3
        """
        impact_map = {
            'IBKR': '無法獲取即時市場數據，已使用備用數據源',
            'Yahoo Finance': '股票和期權數據可能有延遲',
            'Finnhub': '基本面數據可能不完整',
            'Alpha Vantage': '技術指標數據可能受影響',
            'FRED': '無風險利率使用預設值',
            'Finviz': '基本面健康檢查數據可能不完整',
            'yfinance': '歷史數據和股息信息可能受影響'
        }
        
        return impact_map.get(api_name, '相關數據可能不完整或使用備用來源')
    
    def _check_data_consistency(self, raw_data: dict, calculation_results: dict, api_status: dict = None) -> list:
        """
        檢查數據一致性問題
        
        Requirements: 14.4
        """
        warnings = []
        
        # 確保 raw_data 不為 None
        if raw_data is None:
            raw_data = {}
        
        # 1. 檢查 IV 數據一致性
        market_iv = raw_data.get('implied_volatility')
        module17 = calculation_results.get('module17_implied_volatility', {})
        atm_iv = None
        
        if module17:
            call_iv = module17.get('call', {}).get('implied_volatility')
            put_iv = module17.get('put', {}).get('implied_volatility')
            if call_iv and put_iv:
                atm_iv = (call_iv + put_iv) / 2
        
        if market_iv and atm_iv:
            iv_diff = abs(market_iv - atm_iv * 100) / max(market_iv, 0.01)
            if iv_diff > 0.3:  # 差異超過 30%
                warnings.append(f"Market IV ({market_iv:.1f}%) 與 ATM IV ({atm_iv*100:.1f}%) 差異較大，可能影響分析準確性")
        
        # 2. 檢查多數據源一致性
        if api_status and api_status.get('fallback_used'):
            fallback_count = len(api_status['fallback_used'])
            if fallback_count >= 3:
                warnings.append(f"使用了 {fallback_count} 個降級數據源，數據可能來自不同時間點")
        
        # 3. 檢查 IBKR 連接狀態
        if api_status:
            ibkr_enabled = api_status.get('ibkr_enabled', False)
            ibkr_connected = api_status.get('ibkr_connected', False)
            if ibkr_enabled and not ibkr_connected:
                warnings.append("IBKR 已啟用但未連接，即時數據不可用")
        
        # 4. 檢查關鍵數據缺失
        if raw_data.get('current_price') is None:
            warnings.append("當前股價數據缺失，報告可能不準確")
        
        if raw_data.get('risk_free_rate') is None:
            warnings.append("無風險利率數據缺失，使用預設值")
        
        # 5. 檢查期權數據完整性
        module22 = calculation_results.get('module22_optimal_strike', {})
        for strategy in ['long_call', 'long_put', 'short_call', 'short_put']:
            strategy_data = module22.get(strategy, {})
            if strategy_data.get('total_analyzed', 0) < 5:
                warnings.append(f"{strategy} 分析的行使價數量不足，推薦可能不可靠")
                break  # 只報告一次
        
        return warnings
    
    def _get_key_data_points(self, raw_data: dict, calculation_results: dict, api_status: dict = None) -> list:
        """
        獲取關鍵數據點的來源和時間戳
        
        Requirements: 14.5
        """
        from datetime import datetime
        
        # 確保 raw_data 不為 None
        if raw_data is None:
            raw_data = {}
        
        fallback_used = api_status.get('fallback_used', {}) if api_status else {}
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        key_points = []
        
        # 1. 當前股價
        current_price = raw_data.get('current_price')
        if current_price is not None:
            key_points.append({
                'name': '當前股價',
                'value': f"${current_price:.2f}",
                'source': self._determine_source('stock_info', fallback_used, 'Yahoo Finance'),
                'timestamp': current_time
            })
        
        # 2. 隱含波動率
        iv = raw_data.get('implied_volatility')
        if iv is not None:
            key_points.append({
                'name': '市場隱含波動率',
                'value': f"{iv:.2f}%",
                'source': self._determine_source('stock_info', fallback_used, 'Yahoo Finance'),
                'timestamp': current_time
            })
        
        # 3. ATM IV (Module 17)
        module17 = calculation_results.get('module17_implied_volatility', {})
        call_iv = module17.get('call', {}).get('implied_volatility')
        if call_iv:
            key_points.append({
                'name': 'ATM Call IV',
                'value': f"{call_iv*100:.2f}%",
                'source': '自主計算 (Module 17)',
                'timestamp': current_time
            })
        
        # 4. IV Rank
        module18 = calculation_results.get('module18_historical_volatility', {})
        iv_rank = module18.get('iv_rank')
        if iv_rank is not None:
            key_points.append({
                'name': 'IV Rank',
                'value': f"{iv_rank:.2f}%",
                'source': self._determine_source('historical_data', fallback_used, 'yfinance') + ' + 自主計算',
                'timestamp': current_time
            })
        
        # 5. 無風險利率
        risk_free_rate = raw_data.get('risk_free_rate')
        if risk_free_rate is not None:
            key_points.append({
                'name': '無風險利率',
                'value': f"{risk_free_rate:.2f}%",
                'source': self._determine_source('risk_free_rate', fallback_used, 'FRED'),
                'timestamp': current_time
            })
        
        # 6. VIX
        vix = raw_data.get('vix')
        if vix is not None:
            key_points.append({
                'name': 'VIX',
                'value': f"{vix:.2f}",
                'source': self._determine_source('vix', fallback_used, 'Yahoo Finance'),
                'timestamp': current_time
            })
        
        return key_points
    
    def _format_strike_selection(self, data: dict) -> str:
        """格式化行使價選擇說明"""
        report = "\n" + "=" * 70 + "\n"
        report += "期權策略分析 - 行使價選擇\n"
        report += "=" * 70 + "\n\n"
        
        strike = data.get('strike_price', 0)
        current = data.get('current_price', 0)
        diff = data.get('difference', 0)
        moneyness = data.get('moneyness', '')
        note = data.get('note', '')
        
        report += f"選擇的行使價: ${strike:.2f}\n"
        report += f"當前股價: ${current:.2f}\n"
        report += f"價差: ${diff:+.2f}\n"
        report += f"價內程度: {moneyness}\n"
        if note:
            report += f"選擇邏輯: {note}\n"
        report += "\n"
        report += "💡 說明:\n"
        report += "  - ATM（平價）: 行使價接近當前股價（±$2.50）\n"
        report += "  - ITM（價內）: 行使價低於當前股價（Call 有內在價值）\n"
        report += "  - OTM（價外）: 行使價高於當前股價（Call 無內在價值）\n"
        report += "\n"
        
        return report
    
    def _format_strategy_results(self, module_name: str, results) -> str:
        """
        格式化策略損益結果（Module 7-10）- 增強版
        
        整合 StrategyScenarioGenerator，為每個策略使用不同的場景。
        
        Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
        
        支持兩種數據格式：
        1. 列表格式: [scenario1, scenario2, ...]
        2. 字典格式: {'scenarios': [...], 'multi_contract': {...}, 'current_pnl': {...}}
        """
        strategy_names = {
            'module7_long_call': ('Long Call', '📈'),
            'module8_long_put': ('Long Put', '📉'),
            'module9_short_call': ('Short Call', '📊'),
            'module10_short_put': ('Short Put', '💼')
        }
        
        name, emoji = strategy_names.get(module_name, (module_name, '📋'))
        
        report = f"\n┌─ {emoji} {name} 策略損益分析 ────────────────────┐\n"
        report += "│\n"
        
        # 處理兩種數據格式
        scenarios = []
        multi_contract = None
        current_pnl = None
        
        if isinstance(results, dict):
            # 新格式: {'scenarios': [...], 'multi_contract': {...}, 'current_pnl': {...}}
            scenarios = results.get('scenarios', [])
            multi_contract = results.get('multi_contract')
            current_pnl = results.get('current_pnl')
        elif isinstance(results, list):
            # 舊格式: 直接是列表
            scenarios = results
        
        # 添加策略基本信息（從第一個結果提取）
        if scenarios and len(scenarios) > 0:
            first_result = scenarios[0]
            strike = first_result.get('strike_price', 0)
            premium = first_result.get('option_premium', 0)
            breakeven = first_result.get('breakeven_price', 0)
            
            report += f"│ 行使價: ${strike:.2f}\n"
            report += f"│ 權利金: ${premium:.2f}\n"
            if breakeven > 0:
                report += f"│ 盈虧平衡點: ${breakeven:.2f}\n"
            report += "│\n"
        
        report += "│ 場景       | 到期股價 | 行使價  | 權利金  | 損益    | 收益率\n"
        report += "│ ───────────┼──────────┼─────────┼─────────┼─────────┼────────\n"
        
        # 獲取策略特定的場景標籤
        try:
            scenario_labels = StrategyScenarioGenerator.get_scenario_labels(module_name)
        except ValueError:
            # 如果無法獲取場景標籤，使用默認標籤
            scenario_labels = [f"場景 {i+1}" for i in range(4)]
        
        if scenarios and len(scenarios) > 0:
            for i, result in enumerate(scenarios):
                # 獲取場景標籤
                label = scenario_labels[i] if i < len(scenario_labels) else f"場景 {i+1}"
                
                # ✅ 改進：添加數據驗證和日誌
                stock_price = result.get('stock_price_at_expiry')
                strike = result.get('strike_price')
                premium = result.get('option_premium')
                profit = result.get('profit_loss')
                return_pct = result.get('return_percentage')
                
                # 數據驗證
                if stock_price is None or stock_price == 0:
                    logger.warning(f"! {name} 場景 {i+1}: stock_price_at_expiry 缺失或為 0")
                    logger.debug(f"  完整數據: {result}")
                    stock_price = 0  # 使用 0 作為後備值
                
                if strike is None:
                    strike = 0
                if premium is None:
                    premium = 0
                if profit is None:
                    profit = 0
                if return_pct is None:
                    return_pct = 0
                
                # 根據盈虧添加符號
                profit_symbol = '+' if profit >= 0 else ''
                return_symbol = '+' if return_pct >= 0 else ''
                
                # 格式化場景標籤（固定寬度）
                label_display = f"{label:<8}"
                
                report += f"│ {label_display} | "
                report += f"${stock_price:7.2f} | "
                report += f"${strike:7.2f} | "
                report += f"${premium:7.2f} | "
                report += f"{profit_symbol}${profit:6.2f} | "
                report += f"{return_symbol}{return_pct:6.1f}%\n"
        else:
            report += "│ （無數據）\n"
        
        report += "│\n"
        
        # 添加多合約損益信息（如果有）
        if multi_contract:
            report += "│ 📊 多合約損益:\n"
            num_contracts = multi_contract.get('num_contracts', 1)
            total_cost = multi_contract.get('total_cost', 0)
            total_pnl = multi_contract.get('total_profit_loss', multi_contract.get('total_unrealized_pnl', 0))
            total_return = multi_contract.get('total_return_percentage', 0)
            report += f"│   合約數量: {num_contracts}\n"
            report += f"│   總成本: ${total_cost:.2f}\n"
            report += f"│   總損益: ${total_pnl:+.2f}\n"
            report += f"│   總收益率: {total_return:+.1f}%\n"
            report += "│\n"
        
        # 添加當前持倉損益（如果有）
        if current_pnl:
            report += "│ 💰 當前持倉:\n"
            unrealized_pnl = current_pnl.get('total_unrealized_pnl', 0)
            return_pct = current_pnl.get('return_percentage', 0)
            report += f"│   未實現損益: ${unrealized_pnl:+.2f}\n"
            report += f"│   收益率: {return_pct:+.1f}%\n"
            report += "│\n"
        
        # 使用 StrategyScenarioGenerator 生成策略特定的場景說明
        report += "│ 💡 場景說明:\n"
        for i, label in enumerate(scenario_labels):
            report += f"│   - 場景 {i+1}: {label}\n"
        
        report += "└────────────────────────────────────────────────┘\n"
        return report
    
    def _format_strategy_recommendations(self, recommendations: list) -> str:
        """格式化策略推薦結果（含信心度和風險回報比）"""
        report = "\n" + "=" * 70 + "\n"
        report += "策略推薦分析 (含信心度和風險回報比)\n"
        report += "=" * 70 + "\n"
        
        if not recommendations:
            report += "\n  無明確策略推薦\n"
            return report
        
        for i, rec in enumerate(recommendations, 1):
            # 處理字典或對象
            if isinstance(rec, dict):
                strategy_name = rec.get('strategy_name', 'N/A')
                direction = rec.get('direction', 'N/A')
                confidence = rec.get('confidence', 'N/A')
                reasoning = rec.get('reasoning', [])
                suggested_strike = rec.get('suggested_strike')
                key_levels = rec.get('key_levels', {})
                risk_reward_ratio = rec.get('risk_reward_ratio')
                max_profit = rec.get('max_profit')
                max_loss = rec.get('max_loss')
            else:
                strategy_name = getattr(rec, 'strategy_name', 'N/A')
                direction = getattr(rec, 'direction', 'N/A')
                confidence = getattr(rec, 'confidence', 'N/A')
                reasoning = getattr(rec, 'reasoning', [])
                suggested_strike = getattr(rec, 'suggested_strike', None)
                key_levels = getattr(rec, 'key_levels', {})
                risk_reward_ratio = getattr(rec, 'risk_reward_ratio', None)
                max_profit = getattr(rec, 'max_profit', None)
                max_loss = getattr(rec, 'max_loss', None)
            
            # 信心度 emoji
            confidence_emoji = {
                'High': '🟢',
                'Medium': '🟡',
                'Low': '🔴'
            }.get(confidence, '⚪')
            
            report += f"\n┌─ 推薦 {i}: {strategy_name} ─────────────────────┐\n"
            report += f"│\n"
            report += f"│  方向: {direction}\n"
            report += f"│  信心度: {confidence_emoji} {confidence}\n"
            report += f"│\n"
            
            # 添加風險回報比信息
            if risk_reward_ratio is not None:
                report += f"│  風險回報比: {risk_reward_ratio:.2f}:1\n"
            if max_profit is not None:
                if max_profit == float('inf'):
                    report += f"│  最大利潤: 無限\n"
                else:
                    report += f"│  最大利潤: ${max_profit:.2f}\n"
            if max_loss is not None:
                if max_loss == float('inf'):
                    report += f"│  最大損失: 無限 ⚠️\n"
                else:
                    report += f"│  最大損失: ${max_loss:.2f}\n"
            
            if risk_reward_ratio or max_profit or max_loss:
                report += f"│\n"
            
            report += f"│  推薦理由:\n"
            for reason in reasoning:
                report += f"│    - {reason}\n"
            report += f"│\n"
            if suggested_strike:
                report += f"│  建議行使價: ${suggested_strike:.2f}\n"
            if key_levels:
                report += f"│  關鍵價位: {key_levels}\n"
            report += f"└{'─' * 50}┘\n"
        
        return report
    
    # ========== Web/Telegram 集成方法 ==========
    
    def export_for_web(self, calculation_results: dict, ticker: str) -> dict:
        """
        導出用於 Web GUI 的數據
        
        返回:
            包含結構化數據和 HTML 友好格式的字典
        """
        from output_layer.web_telegram_formatter import WebFormatter
        
        structured_data = self.get_structured_output(calculation_results)
        html_data = WebFormatter.format_for_html(structured_data)
        
        return {
            'ticker': ticker,
            'timestamp': datetime.now().isoformat(),
            'structured_data': structured_data,
            'html_data': html_data
        }
    
    def export_for_telegram(self, calculation_results: dict, ticker: str) -> list:
        """
        導出用於 Telegram 的消息列表
        
        返回:
            Telegram 消息列表（已格式化）
        """
        from output_layer.web_telegram_formatter import TelegramFormatter
        
        structured_data = self.get_structured_output(calculation_results)
        messages = TelegramFormatter.format_for_telegram(structured_data, ticker)
        
        return messages
    
    def export_module_csv(self, module_name: str, module_data: dict, ticker: str = None) -> bool:
        """
        導出單個模塊的 CSV 文件
        
        參數:
            module_name: 模塊名稱
            module_data: 模塊數據
            ticker: 股票代碼（可選）
        
        返回:
            bool: 是否成功
        """
        prefix = f"{ticker}_" if ticker else ""
        filename = f"{prefix}{module_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # 將模塊數據轉換為 CSV 行
        csv_rows = []
        if isinstance(module_data, dict):
            for key, value in module_data.items():
                csv_rows.append({
                    '指標': key,
                    '數值': str(value)
                })
        elif isinstance(module_data, list):
            for i, item in enumerate(module_data, 1):
                if isinstance(item, dict):
                    for key, value in item.items():
                        csv_rows.append({
                            '場景': i,
                            '指標': key,
                            '數值': str(value)
                        })
        
        return self.csv_exporter.export_results(csv_rows, filename)
    
    def export_module_json(self, module_name: str, module_data: dict, ticker: str = None) -> bool:
        """
        導出單個模塊的 JSON 文件
        
        參數:
            module_name: 模塊名稱
            module_data: 模塊數據
            ticker: 股票代碼（可選）
        
        返回:
            bool: 是否成功
        """
        prefix = f"{ticker}_" if ticker else ""
        filename = f"{prefix}{module_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        export_data = {
            'module_name': module_name,
            'ticker': ticker,
            'data': module_data
        }
        
        return self.json_exporter.export_results([export_data], filename)
    
    def get_export_summary(self) -> dict:
        """
        獲取導出器狀態摘要
        
        返回:
            包含導出器信息的字典
        """
        return {
            'main_output_dir': str(self.output_dir),
            'csv_output_dir': str(self.csv_exporter.output_dir),
            'json_output_dir': str(self.json_exporter.output_dir),
            'csv_last_file': str(self.csv_exporter.get_last_file()) if self.csv_exporter.get_last_file() else None,
            'json_last_file': str(self.json_exporter.get_last_file()) if self.json_exporter.get_last_file() else None
        }
    
    # ==================== 新增的 6 個格式化函數 ====================
    
    def _format_module2_fair_value(self, results: dict) -> str:
        """
        格式化 Module 2 (公允價值計算) 結果
        
        Requirements: 2.1, 2.2, 2.3
        
        注意: Module 2 計算的是股票遠期理論價 (Forward Price)，不是期權價格。
        數據結構來自 FairValueResult.to_dict():
        - stock_price: 當前股價（即市場價格）
        - fair_value / forward_price: 遠期理論價
        - difference: 差異
        """
        try:
            if results.get('status') in ['skipped', 'error']:
                report = "\n" + "=" * 70 + "\n"
                report += "模塊2: 公允價值計算\n"
                report += "=" * 70 + "\n"
                report += f"⚠️  計算被跳過或出錯: {results.get('reason', 'N/A')}\n"
                return report
            
            # 修正: 使用正確的字段名
            # stock_price 是當前市場價格，fair_value 是遠期理論價
            market_price = results.get('stock_price', results.get('market_price', 0))
            fair_value = results.get('fair_value', results.get('forward_price', 0))
            difference = results.get('difference', 0)
            
            # 計算差異百分比（如果沒有提供）
            difference_percentage = results.get('difference_percentage', 0)
            if difference_percentage == 0 and market_price > 0:
                difference_percentage = (difference / market_price) * 100
            
            # 根據差異判斷估值
            valuation = results.get('valuation', 'N/A')
            if valuation == 'N/A':
                if abs(difference_percentage) < 2:
                    valuation = "合理估值"
                elif difference_percentage > 0:
                    valuation = "略微低估"
                else:
                    valuation = "略微高估"
            
            report = "\n" + "=" * 70 + "\n"
            report += "模塊2: 公允價值計算\n"
            report += "=" * 70 + "\n"
            
            report += f"市場價格:        ${market_price:>10.2f}\n"
            report += f"理論公允價值:    ${fair_value:>10.2f}\n"
            report += "-" * 70 + "\n"
            report += f"價格差異:        ${difference:>10.2f}  ({difference_percentage:>7.2f}%)\n"
            report += "\n"
            report += f"📊 估值評估: {valuation}\n"
            report += "\n"
            
            # 添加解釋說明
            if difference_percentage > 10:
                report += "💡 分析: 股價相對公允價值被低估,可能存在買入機會\n"
            elif difference_percentage < -10:
                report += "💡 分析: 股價相對公允價值被高估,需要謹慎對待\n"
            else:
                report += "💡 分析: 股價與公允價值基本相符,處於合理範圍\n"
            
            report += "=" * 70 + "\n"
            
            return report
            
        except Exception as e:
            logger.error(f"x Module 2 格式化失敗: {e}")
            return f"❌ Module 2 格式化失敗: {str(e)}\n"
    
    def _format_module4_pe_valuation(self, results: dict) -> str:
        """
        格式化 Module 4 (PE估值) 結果
        
        Requirements: 4.1, 4.2, 4.3
        """
        try:
            if results.get('status') in ['skipped', 'error']:
                report = "\n" + "=" * 70 + "\n"
                report += "模塊4: PE估值分析\n"
                report += "=" * 70 + "\n"
                report += f"⚠️  計算被跳過或出錯: {results.get('reason', 'N/A')}\n"
                return report
            
            eps = results.get('eps', 0)
            pe_multiple = results.get('pe_multiple', 0)
            estimated_price = results.get('estimated_price', 0)
            current_price = results.get('current_price', 0)
            difference = results.get('difference', 0)
            difference_percentage = results.get('difference_percentage', 0)
            valuation = results.get('valuation', 'N/A')
            
            report = "\n" + "=" * 70 + "\n"
            report += "模塊4: PE估值分析\n"
            report += "=" * 70 + "\n"
            
            report += f"每股收益 (EPS):      ${eps:>10.2f}\n"
            report += f"PE倍數:              {pe_multiple:>10.2f}倍\n"
            report += f"合理股價估計:        ${estimated_price:>10.2f}\n"
            report += f"當前股價:            ${current_price:>10.2f}\n"
            report += "-" * 70 + "\n"
            report += f"估值差異:            ${difference:>10.2f}  ({difference_percentage:>7.2f}%)\n"
            report += "\n"
            report += f"📊 估值等級: {valuation}\n"
            
            # PE倍數市場環境解讀
            if pe_multiple >= 25:
                report += "\n💡 分析: PE倍數處於牛市水平(25倍以上)\n"
            elif pe_multiple >= 15:
                report += "\n💡 分析: PE倍數處於正常市場水平(15倍)\n"
            elif pe_multiple >= 8.5:
                report += "\n💡 分析: PE倍數處於熊市水平(8.5倍)\n"
            else:
                report += "\n💡 分析: PE倍數極低,反映極度悲觀情緒\n"
            
            report += "=" * 70 + "\n"
            
            return report
            
        except Exception as e:
            logger.error(f"x Module 4 格式化失敗: {e}")
            return f"❌ Module 4 格式化失敗: {str(e)}\n"
    
    def _format_module5_rate_pe_relation(self, results: dict) -> str:
        """
        格式化 Module 5 (利率與PE關係) 結果
        
        Requirements: 5.1, 5.2, 5.3
        """
        try:
            if results.get('status') in ['skipped', 'error']:
                report = "\n" + "=" * 70 + "\n"
                report += "模塊5: 利率與PE關係分析\n"
                report += "=" * 70 + "\n"
                report += f"⚠️  計算被跳過或出錯: {results.get('reason', 'N/A')}\n"
                return report
            
            long_term_rate = results.get('long_term_rate', 0)
            reasonable_pe = results.get('reasonable_pe', 0)
            current_pe = results.get('current_pe', 0)
            pe_difference = results.get('pe_difference', 0)
            valuation = results.get('valuation', 'N/A')
            rate_change_impact = results.get('rate_change_impact', 'N/A')
            
            report = "\n" + "=" * 70 + "\n"
            report += "模塊5: 利率與PE關係分析\n"
            report += "=" * 70 + "\n"
            
            report += f"長期債券收益率:      {long_term_rate:>10.2f}%\n"
            report += f"基於利率的合理PE:    {reasonable_pe:>10.2f}倍\n"
            report += f"當前股票PE:          {current_pe:>10.2f}倍\n"
            report += "-" * 70 + "\n"
            report += f"PE與基準差異:        {pe_difference:>10.2f}倍\n"
            report += "\n"
            report += f"📊 估值狀態: {valuation}\n"
            report += f"⚠️  利率影響: {rate_change_impact}\n"
            
            # 公式解釋
            report += "\n💡 計算方法: 合理PE = 100 / 長期債息\n"
            report += f"   本例: 100 / {long_term_rate:.2f}% = {reasonable_pe:.2f}倍\n"
            
            # 利率與PE的關係
            report += "\n📌 核心原理:\n"
            report += "   • 利率上升 → PE應下降 (投資風險增加)\n"
            report += "   • 利率下降 → PE應上升 (無風險利率下降)\n"
            
            report += "=" * 70 + "\n"
            
            return report
            
        except Exception as e:
            logger.error(f"x Module 5 格式化失敗: {e}")
            return f"❌ Module 5 格式化失敗: {str(e)}\n"
    
    def _format_module6_hedge_quantity(self, results: dict) -> str:
        """
        格式化 Module 6 (對沖數量) 結果
        
        Requirements: 6.1, 6.2, 6.3
        
        數據結構來自 HedgeQuantityResult.to_dict():
        - stock_quantity: 正股數量
        - stock_price: 股價
        - portfolio_value: 持倉市值
        - option_multiplier: 期權乘數 (100)
        - hedge_contracts: 對沖合約數
        - coverage_percentage: 覆蓋率
        - delta_hedge (可選): Delta 對沖信息
        """
        try:
            if results.get('status') in ['skipped', 'error']:
                report = "\n" + "=" * 70 + "\n"
                report += "模塊6: 投資組合對沖策略\n"
                report += "=" * 70 + "\n"
                report += f"⚠️  計算被跳過或出錯: {results.get('reason', 'N/A')}\n"
                return report
            
            # 使用正確的字段名（來自 HedgeQuantityResult.to_dict()）
            stock_quantity = results.get('stock_quantity', 0)
            stock_price = results.get('stock_price', 0)
            portfolio_value = results.get('portfolio_value', 0)
            option_multiplier = results.get('option_multiplier', 100)
            hedge_contracts = results.get('hedge_contracts', 0)
            coverage_percentage = results.get('coverage_percentage', 0)
            
            # Delta 對沖信息（如果有）
            delta_hedge = results.get('delta_hedge', {})
            
            report = "\n" + "=" * 70 + "\n"
            report += "模塊6: 投資組合對沖策略\n"
            report += "=" * 70 + "\n"
            
            report += f"正股數量:            {stock_quantity:>10}股\n"
            report += f"股價:                ${stock_price:>10.2f}\n"
            report += f"投資組合價值:        ${portfolio_value:>10.2f}\n"
            report += f"期權乘數:            {option_multiplier:>10}\n"
            report += "\n"
            
            report += "📊 基本對沖方案:\n"
            report += "-" * 70 + "\n"
            report += f"所需合約數:          {hedge_contracts:>10}張\n"
            report += f"覆蓋率:              {coverage_percentage:>10.2f}%\n"
            report += "-" * 70 + "\n"
            
            # 對沖效率評估
            report += "\n"
            if coverage_percentage >= 95:
                report += "✅ 對沖覆蓋率高,風險保護充足\n"
            elif coverage_percentage >= 80:
                report += "⚠️  對沖覆蓋率一般,部分風險未覆蓋\n"
            else:
                report += "❌ 對沖覆蓋率低,建議增加對沖數量\n"
            
            # Delta 對沖信息（如果有）
            if delta_hedge:
                report += "\n📈 Delta 對沖方案:\n"
                report += "-" * 70 + "\n"
                delta_used = delta_hedge.get('delta_used', 0)
                delta_contracts = delta_hedge.get('hedge_contracts', 0)
                delta_coverage = delta_hedge.get('coverage_percentage', 0)
                delta_note = delta_hedge.get('note', '')
                report += f"使用 Delta:          {delta_used:>10.4f}\n"
                report += f"所需合約數:          {delta_contracts:>10}張\n"
                report += f"覆蓋率:              {delta_coverage:>10.2f}%\n"
                if delta_note:
                    report += f"說明: {delta_note}\n"
                report += "-" * 70 + "\n"
            
            report += "\n💡 計算說明:\n"
            report += f"   對沖份數 = 正股數量 / 期權乘數\n"
            report += f"   {hedge_contracts} = {stock_quantity} / {option_multiplier}\n"
            report += "=" * 70 + "\n"
            
            return report
            
        except Exception as e:
            logger.error(f"x Module 6 格式化失敗: {e}")
            return f"❌ Module 6 格式化失敗: {str(e)}\n"
    
    def _format_module11_synthetic_stock(self, results: dict) -> str:
        """
        格式化 Module 11 (合成股票) 結果
        
        Requirements: 11.1, 11.2, 11.3
        US-3 Task 3.3: 添加套利機會警報和策略詳情
        """
        try:
            if results.get('status') in ['skipped', 'error']:
                report = "\n" + "=" * 70 + "\n"
                report += "模塊11: 合成股票期權組合\n"
                report += "=" * 70 + "\n"
                report += f"⚠️  計算被跳過或出錯: {results.get('reason', 'N/A')}\n"
                return report
            
            strike_price = results.get('strike_price', 0)
            call_premium = results.get('call_premium', 0)
            put_premium = results.get('put_premium', 0)
            synthetic_price = results.get('synthetic_price', 0)
            current_stock_price = results.get('current_stock_price', 0)
            difference = results.get('difference', 0)
            arbitrage_opportunity = results.get('arbitrage_opportunity', False)
            strategy = results.get('strategy', 'N/A')
            
            # US-3: 檢查是否由 Parity 失效觸發
            triggered_by_parity = results.get('triggered_by_parity', False)
            parity_deviation = results.get('parity_deviation', 0)
            arbitrage_strategy = results.get('arbitrage_strategy', {})
            
            report = "\n" + "=" * 70 + "\n"
            report += "模塊11: 合成股票期權組合\n"
            report += "=" * 70 + "\n"
            
            # US-3 Task 3.3.2: 套利機會警報
            if triggered_by_parity and arbitrage_strategy:
                report += "\n" + "🎯" * 35 + "\n"
                report += "⚠️  套利機會警報！Put-Call Parity 失效\n"
                report += "🎯" * 35 + "\n"
                report += f"Parity 偏離: ${abs(parity_deviation):>10.4f}\n"
                report += f"理論利潤:   ${arbitrage_strategy.get('theoretical_profit', 0):>10.2f}\n"
                report += "\n"
            
            report += f"行使價:              ${strike_price:>10.2f}\n"
            report += "\n📊 期權組合成本:\n"
            report += "-" * 70 + "\n"
            report += f"Call期權金:          ${call_premium:>10.2f}\n"
            report += f"Put期權金:           ${put_premium:>10.2f}\n"
            report += f"合成價格:            ${synthetic_price:>10.2f}\n"
            report += "\n"
            report += f"當前股價:            ${current_stock_price:>10.2f}\n"
            report += "-" * 70 + "\n"
            report += f"價格偏差:            ${difference:>10.2f}\n"
            report += "\n"
            
            # US-3 Task 3.3.3-3.3.5: 顯示套利策略詳情
            if triggered_by_parity and arbitrage_strategy:
                report += self._format_arbitrage_strategy(arbitrage_strategy)
            elif arbitrage_opportunity:
                report += "🚨 發現套利機會!\n"
                report += f"策略: {strategy}\n"
                report += "\n💡 說明:\n"
                report += "   期權組合構造的合成股票價格與實際股價存在\n"
                report += "   有意義的偏差,可能存在無風險套利機會\n"
            else:
                report += "✅ 沒有明顯套利機會\n"
                report += "\n💡 說明:\n"
                report += "   合成股票價格與實際股價基本一致,\n"
                report += "   市場定價相對合理\n"
            
            # Put-Call Parity 解釋
            report += "\n📌 Put-Call Parity 公式:\n"
            report += "   Long Call + Short Put = Long Stock\n"
            report += f"   ${call_premium:.2f} - ${put_premium:.2f} + ${strike_price:.2f} = ${synthetic_price:.2f}\n"
            
            report += "=" * 70 + "\n"
            
            return report
            
        except Exception as e:
            logger.error(f"x Module 11 格式化失敗: {e}")
            return f"❌ Module 11 格式化失敗: {str(e)}\n"
    
    def _format_arbitrage_strategy(self, strategy: dict) -> str:
        """
        US-3 Task 3.3.1: 格式化套利策略詳情
        
        參數:
            strategy: 套利策略字典
        
        返回:
            str: 格式化的策略報告
        """
        try:
            report = "📋 套利策略詳情:\n"
            report += "=" * 70 + "\n"
            
            # 策略類型
            strategy_name = strategy.get('strategy_name', 'N/A')
            report += f"策略名稱: {strategy_name}\n"
            report += "\n"
            
            # Task 3.3.3: 策略腿表格
            legs = strategy.get('legs', [])
            if legs:
                report += "📊 交易組合:\n"
                report += "-" * 70 + "\n"
                report += f"{'動作':<8} {'類型':<10} {'行使價':<12} {'數量':<8}\n"
                report += "-" * 70 + "\n"
                for leg in legs:
                    action = leg.get('action', 'N/A')
                    leg_type = leg.get('type', 'N/A')
                    strike = leg.get('strike')
                    quantity = leg.get('quantity', 1)
                    
                    strike_str = f"${strike:.2f}" if strike else "市價"
                    report += f"{action:<8} {leg_type:<10} {strike_str:<12} {quantity:<8}\n"
                report += "\n"
            
            # 利潤分析
            risk_analysis = strategy.get('risk_analysis', {})
            max_profit = risk_analysis.get('max_profit', 0)
            max_loss = risk_analysis.get('max_loss', 0)
            break_even = risk_analysis.get('break_even', 0)
            
            report += "💰 利潤分析:\n"
            report += "-" * 70 + "\n"
            report += f"最大利潤:            ${max_profit:>10.2f}\n"
            if max_loss == 0:
                report += f"最大損失:            理論無風險\n"
            else:
                report += f"最大損失:            ${max_loss:>10.2f}\n"
            report += f"損益平衡點:          ${break_even:>10.2f}\n"
            report += "\n"
            
            # Task 3.3.4: 風險分析
            risks = risk_analysis.get('risks', [])
            if risks:
                report += "⚠️  風險提示:\n"
                report += "-" * 70 + "\n"
                for i, risk in enumerate(risks, 1):
                    report += f"{i}. {risk}\n"
                report += "\n"
            
            # Task 3.3.5: 執行步驟
            execution_steps = strategy.get('execution_steps', [])
            if execution_steps:
                report += "📝 執行步驟:\n"
                report += "-" * 70 + "\n"
                for step in execution_steps:
                    report += f"{step}\n"
                report += "\n"
            
            # 注意事項
            note = strategy.get('note', '')
            if note:
                report += "💡 重要提示:\n"
                report += f"   {note}\n"
                report += "\n"
            
            report += "=" * 70 + "\n"
            
            return report
            
        except Exception as e:
            logger.error(f"x 套利策略格式化失敗: {e}")
            return f"❌ 套利策略格式化失敗: {str(e)}\n"
    
    def _format_module30_unusual_activity(self, data: dict) -> str:
        """格式化 Module 30: 異動期權分析"""
        try:
            if data.get('status') in ['skipped', 'error']:
                return f"\n⚠️ Module 30 (異動期權分析): {data.get('reason', 'N/A')}\n"
            
            report = "\n┌─ Module 30: 異動期權分析 ───────────────────┐\n│\n"
            
            calls = data.get('calls', [])
            puts = data.get('puts', [])
            total = data.get('total_signals', 0)
            
            report += f"│ 📊 異動信號總數: {total}\n│\n"
            
            if calls:
                report += "│ 📈 Call 異動:\n"
                for c in calls[:5]:  # 只顯示前5個
                    strike = c.get('strike', 'N/A')
                    signal_type = c.get('signal_type', 'N/A')
                    volume = c.get('volume', 'N/A')
                    oi = c.get('open_interest', 'N/A')
                    report += f"│   • ${strike}: {signal_type} (Vol: {volume}, OI: {oi})\n"
                if len(calls) > 5:
                    report += f"│   ... 及其他 {len(calls)-5} 個信號\n"
                report += "│\n"
            
            if puts:
                report += "│ 📉 Put 異動:\n"
                for p in puts[:5]:
                    strike = p.get('strike', 'N/A')
                    signal_type = p.get('signal_type', 'N/A')
                    volume = p.get('volume', 'N/A')
                    oi = p.get('open_interest', 'N/A')
                    report += f"│   • ${strike}: {signal_type} (Vol: {volume}, OI: {oi})\n"
                if len(puts) > 5:
                    report += f"│   ... 及其他 {len(puts)-5} 個信號\n"
                report += "│\n"
            
            if not calls and not puts:
                report += "│ ℹ️ 未發現顯著異動\n│\n"
            
            report += "└────────────────────────────────────────────┘\n"
            return report
            
        except Exception as e:
            return f"\n❌ Module 30 格式化失敗: {str(e)}\n"
    
    def _format_module31_advanced_metrics(self, data: dict) -> str:
        """格式化 Module 31: 高級市場指標"""
        try:
            if data.get('status') in ['skipped', 'error']:
                return f"\n⚠️ Module 31 (高級市場指標): {data.get('reason', 'N/A')}\n"
            
            report = "\n┌─ Module 31: 高級市場指標 ───────────────────┐\n│\n"
            
            # Put/Call Ratio
            pcr = data.get('put_call_ratio', {})
            report += "│ 📊 Put/Call Ratio:\n"
            report += f"│   OI 比率: {pcr.get('oi_ratio', 'N/A')}\n"
            report += f"│   Volume 比率: {pcr.get('volume_ratio', 'N/A')}\n"
            report += f"│   市場情緒: {pcr.get('sentiment', 'N/A')}\n│\n"
            
            # Max Pain
            max_pain = data.get('max_pain', {})
            strike = max_pain.get('max_pain_strike', 'N/A')
            report += "│ 🎯 Max Pain:\n"
            report += f"│   Max Pain 行使價: ${strike}\n"
            report += f"│   總損失: ${max_pain.get('total_pain', 0):,.0f}\n│\n"
            
            # GEX
            gex = data.get('gamma_exposure', {})
            if gex:
                report += "│ ⚡ Gamma Exposure (GEX):\n"
                report += f"│   淨 GEX: {self._safe_format(gex.get('net_gex'), fmt='.2e')}\n"
                report += f"│   零點: {self._safe_format(gex.get('zero_gamma_point'), prefix='$')}\n│\n"
            
            report += "└────────────────────────────────────────────┘\n"
            return report
            
        except Exception as e:
            return f"\n❌ Module 31 格式化失敗: {str(e)}\n"
    
    def _format_complex_strategies(self, data: dict) -> str:
        """格式化 Module 32: 複雜策略分析（增強版）"""
        try:
            if data.get('status') in ['skipped', 'error']:
                return f"\n⚠️ Module 32 (複雜策略分析): {data.get('reason', 'N/A')}\n"
            
            report = "\n┌─ Module 32: 複雜策略分析 ───────────────────┐\n│\n"
            
            # 統計分析的策略數量
            vs = data.get('vertical_spreads', {})
            bull_put = vs.get('bull_put', [])
            bear_call = vs.get('bear_call', [])
            iron_condors = data.get('iron_condors', [])
            straddles = data.get('straddles', [])
            strangles = data.get('strangles', [])
            
            total_strategies = len(bull_put) + len(bear_call) + len(iron_condors) + len(straddles) + len(strangles)
            report += f"│ 📊 分析策略總數: {total_strategies} 個\n│\n"
            
            # 收集所有策略並排序
            all_strategies = []
            for s in bull_put:
                s['type'] = 'Bull Put Spread'
                s['category'] = '看漲/中性'
                all_strategies.append(s)
            for s in bear_call:
                s['type'] = 'Bear Call Spread'
                s['category'] = '看跌/中性'
                all_strategies.append(s)
            for s in iron_condors:
                s['type'] = 'Iron Condor'
                s['category'] = '橫盤收租'
                all_strategies.append(s)
            for s in straddles:
                s['type'] = 'Long Straddle'
                s['category'] = '波動率爆發'
                all_strategies.append(s)
            for s in strangles:
                s['type'] = 'Long Strangle'
                s['category'] = '波動率爆發(低成本)'
                all_strategies.append(s)
            
            # 按評分排序
            all_strategies.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            if all_strategies:
                # 最佳推薦
                best = all_strategies[0]
                report += "│ ═══════════════════════════════════════════\n"
                report += f"│ 🏆 最佳推薦: {best.get('type', 'N/A')}\n"
                report += f"│    適用: {best.get('category', 'N/A')}\n"
                report += f"│    評分: {self._safe_format(best.get('score', 0), fmt='.1f')}/100\n│\n"
                
                # 操作流程
                report += "│ 📋 操作流程:\n"
                desc = best.get('description', '')
                if desc:
                    # 解析 description 字段 (格式: "策略名 (+1C100, -1P95)")
                    if '(' in desc and ')' in desc:
                        legs_str = desc.split('(')[1].split(')')[0]
                        legs = legs_str.split(', ')
                        step = 1
                        for leg in legs:
                            leg = leg.strip()
                            if leg.startswith('+'):
                                action = "買入"
                                leg = leg[1:]
                            elif leg.startswith('-'):
                                action = "賣出"
                                leg = leg[1:]
                            else:
                                action = ""
                            
                            # 解析數量、類型、行使價 (e.g., "1C100")
                            qty = ""
                            opt_type = ""
                            strike = ""
                            for i, c in enumerate(leg):
                                if c.isdigit():
                                    if opt_type:
                                        strike += c
                                    else:
                                        qty += c
                                elif c in ['C', 'P']:
                                    opt_type = "Call" if c == 'C' else "Put"
                            
                            report += f"│   {step}. {action} {qty}張 {opt_type} 行使價 ${strike}\n"
                            step += 1
                    else:
                        report += f"│   {desc}\n"
                else:
                    report += "│   (策略細節不可用)\n"
                
                report += "│\n"
                
                # 風險回報分析
                net_premium = best.get('net_premium', 0)
                max_profit = best.get('max_profit', 0)
                max_loss = best.get('max_loss', 0)
                breakevens = best.get('breakevens', [])
                
                report += "│ 💰 風險回報分析:\n"
                if net_premium > 0:
                    report += f"│   淨權金收入: {self._safe_format(net_premium, prefix='$')}\n"
                else:
                    report += f"│   淨成本: {self._safe_format(abs(net_premium), prefix='$')}\n"
                
                if max_profit == 'Unlimited':
                    report += "│   最大利潤: 無限 🚀\n"
                else:
                    report += f"│   最大利潤: {self._safe_format(max_profit, prefix='$')}\n"
                
                if max_loss == 'Unlimited':
                    report += "│   最大損失: 無限 ⚠️\n"
                else:
                    report += f"│   最大損失: {self._safe_format(max_loss, prefix='$')}\n"
                    
                rr = best.get('risk_reward', 0)
                if rr > 0:
                    report += f"│   風險回報比: {rr:.2f}:1\n"
                
                win_prob = best.get('win_prob', 0)
                if win_prob > 0:
                    report += f"│   勝率估計: {win_prob:.1f}%\n"
                
                report += "│\n"
                
                # 盈虧平衡點（含合理性檢查）
                if breakevens:
                    report += "│ 📈 盈虧平衡點:\n"
                    for be in breakevens:
                        if isinstance(be, (int, float)):
                            if be < 0:
                                report += f"│   ⚠️ ${be:.2f} (不合理 - 成本過高)\n"
                            else:
                                report += f"│   ${be:.2f}\n"
                    report += "│\n"
                
                # Greeks
                greeks = best.get('greeks', {})
                if greeks:
                    report += "│ 📊 組合 Greeks:\n"
                    report += f"│   Delta: {self._safe_format(greeks.get('delta', 0), fmt='.4f')}\n"
                    report += f"│   Gamma: {self._safe_format(greeks.get('gamma', 0), fmt='.4f')}\n"
                    report += f"│   Theta: {self._safe_format(greeks.get('theta', 0), fmt='.4f')}/天\n"
                    report += f"│   Vega: {self._safe_format(greeks.get('vega', 0), fmt='.4f')}\n"
                    report += "│\n"
                
                report += "│ ═══════════════════════════════════════════\n│\n"
                
                # 其他策略比較（如果有）
                if len(all_strategies) > 1:
                    report += "│ 📋 其他備選策略:\n"
                    for s in all_strategies[1:4]:  # 顯示前3個備選
                        s_type = s.get('type', 'N/A')
                        score = s.get('score', 0)
                        net_p = s.get('net_premium', 0)
                        if net_p > 0:
                            cost_str = f"收入 ${net_p:.2f}"
                        else:
                            cost_str = f"成本 ${abs(net_p):.2f}"
                        report += f"│   • {s_type}: 評分 {score:.0f}, {cost_str}\n"
                    report += "│\n"
            else:
                report += "│ ℹ️ 未發現適合的複雜策略\n│\n"
            
            # 適用市場環境說明
            report += "│ 💡 策略適用說明:\n"
            report += "│   • Bull Put Spread / Bear Call Spread: 高IV收租\n"
            report += "│   • Iron Condor: 橫盤震盪，高IV環境\n"
            report += "│   • Long Straddle/Strangle: 波動率爆發預期\n"
            report += "└────────────────────────────────────────────┘\n"
            return report
            
        except Exception as e:
            return f"\n❌ Module 32 格式化失敗: {str(e)}\n"
    
    def _format_module12_annual_yield(self, results: dict) -> str:
        """
        格式化 Module 12 (年化收益率) 結果
        
        Requirements: 12.1, 12.2, 12.3
        """
        try:
            if results.get('status') in ['skipped', 'error']:
                report = "\n" + "=" * 70 + "\n"
                report += "模塊12: 期權策略年化收益率\n"
                report += "=" * 70 + "\n"
                report += f"⚠️  計算被跳過或出錯: {results.get('reason', 'N/A')}\n"
                return report
            
            initial_premium = results.get('initial_premium', 0)
            strike_price = results.get('strike_price', 0)
            stock_price = results.get('stock_price', 0)
            days_to_expiration = results.get('days_to_expiration', 0)
            annualized_return = results.get('annualized_return', 0)
            annualized_return_with_stock = results.get('annualized_return_with_stock', 0)
            break_even_price = results.get('break_even_price', 0)
            max_profit = results.get('max_profit', 0)
            max_loss = results.get('max_loss', 0)
            
            report = "\n" + "=" * 70 + "\n"
            report += "模塊12: 期權策略年化收益率\n"
            report += "=" * 70 + "\n"
            
            report += f"初始收取期權金:      ${initial_premium:>10.2f}\n"
            report += f"行使價:              ${strike_price:>10.2f}\n"
            report += f"當前股價:            ${stock_price:>10.2f}\n"
            report += f"到期天數:            {days_to_expiration:>10}天\n"
            report += "\n"
            
            report += "📊 收益率分析:\n"
            report += "-" * 70 + "\n"
            report += f"年化收益率 (純期權):  {annualized_return:>10.2f}%\n"
            report += f"年化收益率 (含股票):  {annualized_return_with_stock:>10.2f}%\n"
            report += "\n"
            
            report += "🎯 風險分析:\n"
            report += "-" * 70 + "\n"
            report += f"保本股價 (下限):     ${break_even_price:>10.2f}\n"
            report += f"最大利潤:            ${max_profit:>10.2f}\n"
            report += f"最大損失:            ${max_loss:>10.2f}\n"
            report += "\n"
            
            # 年化收益率評估
            if annualized_return > 30:
                report += "🚀 年化收益率很高,需警惕隱藏風險\n"
            elif annualized_return > 15:
                report += "✅ 年化收益率良好,風險收益比合理\n"
            elif annualized_return > 5:
                report += "⚠️  年化收益率一般,需評估風險\n"
            else:
                report += "❌ 年化收益率較低,可能不值得承擔期權風險\n"
            
            report += "\n💡 計算說明:\n"
            if stock_price > 0 and days_to_expiration > 0:
                report += f"   期權金 (${initial_premium:.2f}) / 股價 (${stock_price:.2f}) * (365/{days_to_expiration}) = {annualized_return:.2f}%\n"
            else:
                report += "   年化收益率 = (期權金 / 股價) * (365 / 到期天數)\n"
            
            report += "=" * 70 + "\n"
            
            return report
            
        except Exception as e:
            logger.error(f"x Module 12 格式化失敗: {e}")
            return f"❌ Module 12 格式化失敗: {str(e)}\n"
            
    def _format_module33_wolfram_verification(self, data: dict) -> str:
        """格式化模塊33 (Wolfram 數學驗證)"""
        report = "\n" + "=" * 70 + "\n"
        report += "模塊33: Wolfram 數學交叉驗證\n"
        report += "=" * 70 + "\n"
        
        status = data.get('status', '未知')
        if status == 'disabled':
            report += "狀態: 🟡 未啟用 (未設定 WOLFRAM_APP_ID)\n"
            return report + "=" * 70 + "\n"
        elif status == 'error':
            report += f"狀態: ❌ 錯誤 ({data.get('error', '未知錯誤')})\n"
            return report + "=" * 70 + "\n"
            
        report += "狀態: ✅ 成功\n\n"
        
        math_verify = data.get('math_verification', 'N/A')
        prob_verify = data.get('probability_verification', 'N/A')
        
        report += "🎯 Black-Scholes 理論價驗證:\n"
        # Wrap long text logically
        math_lines = str(math_verify).split('\n') if '\n' in str(math_verify) else [str(math_verify)]
        for line in math_lines:
            report += f"   {line}\n"
            
        report += "\n📈 損益平衡點突破機率 (正態分佈預測):\n"
        prob_lines = str(prob_verify).split('\n') if '\n' in str(prob_verify) else [str(prob_verify)]
        for line in prob_lines:
            report += f"   {line}\n"
            
        report += "=" * 70 + "\n"
        
        return report

    # ==================== Phase 8: 日內交易模組報告格式化 ====================

    def _format_module_vwap(self, data: dict) -> str:
        """格式化 VWAP 日內分析結果"""
        if data.get('status') == 'skipped':
            return f"\n┌─ VWAP 日內分析 ──────────────────────────────┐\n│ ⏸️ 已跳過: {data.get('reason', '數據不可用')}\n└────────────────────────────────────────────────┘\n"

        report = "\n┌─ VWAP 日內分析 (成交量加權平均價) ─────────────┐\n"
        report += "│\n"
        report += f"│ 📊 VWAP: ${data.get('vwap', 0):.2f}\n"
        report += f"│ 現價: ${data.get('current_price', 0):.2f}\n"
        report += f"│ 偏差: {data.get('price_vs_vwap_pct', 0):+.2f}%\n"
        report += f"│ 位置: {data.get('position', 'N/A')}\n"
        report += "│\n"

        bands = data.get('bands', {})
        if bands:
            report += "│ 📐 VWAP Bands:\n"
            report += f"│   Upper Band 2: ${bands.get('upper_2', 0):.2f}\n"
            report += f"│   Upper Band 1: ${bands.get('upper_1', 0):.2f}\n"
            report += f"│   VWAP:         ${bands.get('vwap', 0):.2f}\n"
            report += f"│   Lower Band 1: ${bands.get('lower_1', 0):.2f}\n"
            report += f"│   Lower Band 2: ${bands.get('lower_2', 0):.2f}\n"
            report += "│\n"

        signal = data.get('signal', 'neutral')
        strength = data.get('signal_strength', 'weak')
        signal_emoji = {'bullish': '📈 看漲', 'bearish': '📉 看跌', 'neutral': '➖ 中性'}
        report += f"│ 🎯 信號: {signal_emoji.get(signal, signal)} ({strength})\n"
        report += f"│ 💡 入場條件: {data.get('entry_condition', 'N/A')}\n"
        report += f"│\n"
        report += f"│ 📊 數據點: {data.get('data_points', 0)} | 總成交量: {data.get('total_volume', 0):,}\n"
        report += "└────────────────────────────────────────────────┘\n"
        return report

    def _format_module_orb(self, data: dict) -> str:
        """格式化 ORB 開盤區間突破分析結果"""
        if data.get('status') == 'skipped':
            return f"\n┌─ ORB 開盤區間突破分析 ──────────────────────┐\n│ ⏸️ 已跳過: {data.get('reason', '數據不可用')}\n└────────────────────────────────────────────────┘\n"

        report = "\n┌─ ORB 開盤區間突破分析 ──────────────────────────┐\n"
        report += "│\n"

        orb = data.get('opening_range', {})
        report += f"│ 📊 開盤區間 ({data.get('orb_minutes', 15)} 分鐘):\n"
        report += f"│   High: ${orb.get('high', 0):.2f}\n"
        report += f"│   Low:  ${orb.get('low', 0):.2f}\n"
        report += f"│   範圍: ${orb.get('range', 0):.2f} ({orb.get('range_pct', 0):.2f}%)\n"
        report += "│\n"

        direction = data.get('breakout_direction', 'none')
        dir_emoji = {'bullish': '📈 上突破', 'bearish': '📉 下突破', 'none': '➖ 未突破'}
        report += f"│ 現價: ${data.get('current_price', 0):.2f}\n"
        report += f"│ 狀態: {data.get('status', 'N/A')}\n"
        report += f"│ 方向: {dir_emoji.get(direction, direction)}\n"
        report += "│\n"

        targets = data.get('targets', {})
        if targets:
            report += "│ 🎯 價位目標:\n"
            report += f"│   Target 1: ${targets.get('target_1', 0):.2f}\n"
            report += f"│   Target 2: ${targets.get('target_2', 0):.2f}\n"
            report += f"│   止損:     ${targets.get('stop_loss', 0):.2f}\n"
            report += "│\n"

        signal = data.get('signal', 'wait')
        confidence = data.get('confidence', 'low')
        signal_emoji = {'long_call': '📈 Long Call', 'long_put': '📉 Long Put', 'wait': '⏸️ 等待'}
        report += f"│ 🎯 信號: {signal_emoji.get(signal, signal)} ({confidence})\n"
        report += f"│ 💡 建議: {data.get('option_suggestion', 'N/A')}\n"
        report += "│\n"
        report += f"│ 📖 分析: {data.get('reasoning', 'N/A')}\n"
        report += "└────────────────────────────────────────────────┘\n"
        return report

    def _format_module_0dte(self, data: dict) -> str:
        """格式化 0DTE/1DTE 篩選結果"""
        if data.get('status') == 'skipped':
            return f"\n┌─ 0DTE/1DTE 到期日篩選 ──────────────────────┐\n│ ⏸️ 已跳過: {data.get('reason', '數據不可用')}\n└────────────────────────────────────────────────┘\n"

        report = "\n┌─ 0DTE/1DTE 到期日篩選 ──────────────────────────┐\n"
        report += "│\n"
        report += f"│ 📅 推薦到期日: {data.get('recommended_expiry', 'N/A')}\n"
        report += f"│ 📊 DTE: {data.get('recommended_dte', 'N/A')} 天\n"
        report += f"│ 💡 原因: {data.get('recommendation_reason', 'N/A')}\n"
        report += "│\n"

        report += f"│ ⏰ 時段: {data.get('time_period', 'N/A')}\n"
        report += f"│ 📝 時段建議: {data.get('time_note', 'N/A')}\n"
        report += "│\n"

        combined = data.get('combined_signal', 'neutral')
        signal_emoji = {'bullish': '📈 看漲', 'bearish': '📉 看跌', 'neutral': '➖ 中性'}
        report += f"│ 🎯 綜合信號: {signal_emoji.get(combined, combined)}\n"
        if data.get('vwap_signal'):
            report += f"│   VWAP 信號: {data['vwap_signal']}\n"
        if data.get('orb_signal'):
            report += f"│   ORB 信號: {data['orb_signal']}\n"
        report += "│\n"

        # 到期日評估列表
        expirations = data.get('expirations_assessed', [])
        if expirations:
            report += f"│ 📋 已評估到期日 ({len(expirations)} 個):\n"
            for exp in expirations[:5]:  # 最多顯示5個
                dte = exp.get('dte', '?')
                suit = exp.get('suitability', 'N/A')
                theta = exp.get('theta_risk', 'N/A')
                report += f"│   {exp.get('expiration', 'N/A')} (DTE={dte}) - {suit} | Theta: {theta}\n"

        report += "└────────────────────────────────────────────────┘\n"
        return report
