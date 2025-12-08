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
    
    def __init__(self, output_dir='output/', output_manager: OutputPathManager = None):
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
                data_fetcher=None) -> dict:
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
                ticker, analysis_date, raw_data, calculation_results, text_path, api_status
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
            logger.error(f"x 報告生成失敗: {e}")
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
        
        # 確保目錄存在
        self.output_manager.ensure_directory_exists(os.path.dirname(filepath))
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
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
                            if 'volatility_smile' in strategy_data:
                                smile = strategy_data['volatility_smile']
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
                            if 'parity_validation' in strategy_data:
                                parity = strategy_data['parity_validation']
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
                                      calculation_results, filepath: str, api_status=None):
        """
        生成純文本報告到指定路徑（使用 OutputPathManager）
        
        Requirements: 15.5
        """
        import os
        
        # 確保目錄存在
        self.output_manager.ensure_directory_exists(os.path.dirname(filepath))
        self._write_text_report(filepath, ticker, analysis_date, raw_data, calculation_results, api_status)
    
    def _write_text_report(self, filepath, ticker, analysis_date, raw_data, 
                          calculation_results, api_status=None):
        """寫入純文本報告內容"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("期權交易分析系統 - 完整分析報告\n")
            f.write("=" * 70 + "\n\n")
            
            # 基本信息
            f.write(f"股票代碼: {ticker}\n")
            f.write(f"分析日期: {analysis_date}\n")
            f.write(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
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
            
            # 原始數據摘要
            f.write("=" * 70 + "\n")
            f.write("原始市場數據\n")
            f.write("=" * 70 + "\n")
            
            if raw_data:
                # 安全格式化函數，處理 None 值
                def safe_format(value, fmt=".2f", prefix="", suffix=""):
                    if value is None:
                        return "N/A"
                    try:
                        return f"{prefix}{value:{fmt}}{suffix}"
                    except (ValueError, TypeError):
                        return str(value)
                
                f.write(f"當前股價: {safe_format(raw_data.get('current_price'), prefix='$')}\n")
                f.write(f"隱含波動率: {safe_format(raw_data.get('implied_volatility'), suffix='%')}\n")
                f.write(f"EPS: {safe_format(raw_data.get('eps'), prefix='$')}\n")
                f.write(f"派息: {safe_format(raw_data.get('annual_dividend'), prefix='$')}\n")
                f.write(f"無風險利率: {safe_format(raw_data.get('risk_free_rate'), suffix='%')}\n")
                f.write(f"VIX: {safe_format(raw_data.get('vix'))}\n")
                
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
            
            for module_name, module_data in calculation_results.items():
                # 跳過已處理的多信心度結果
                if module_name == 'module1_support_resistance_multi':
                    continue
                
                # 使用專門的格式化函數
                if module_name == 'module3_arbitrage_spread':
                    f.write(self._format_module3_arbitrage_spread(module_data))
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
                    f.write(self._format_module23_dynamic_iv_threshold(module_data))
                elif module_name == 'strike_selection':
                    # 顯示行使價選擇說明
                    f.write(self._format_strike_selection(module_data))
                elif module_name in ['module7_long_call', 'module8_long_put', 'module9_short_call', 'module10_short_put']:
                    f.write(self._format_strategy_results(module_name, module_data))
                elif module_name == 'strategy_recommendations':
                    f.write(self._format_strategy_recommendations(module_data))
                else:
                    # 通用格式
                    f.write(f"\n{module_name}:\n")
                    if isinstance(module_data, dict):
                        for key, value in module_data.items():
                            f.write(f"  {key}: {value}\n")
                    elif isinstance(module_data, list):
                        for i, item in enumerate(module_data, 1):
                            f.write(f"  場景 {i}: {item}\n")
            
            # 添加數據來源摘要
            f.write(self._format_data_source_summary(raw_data, calculation_results))
        
        logger.info(f"* 文本報告已保存: {filepath}")
    
    def _format_module1_multi_confidence(self, ticker: str, results: dict) -> str:
        """格式化Module 1多信心度結果"""
        
        report = "┌─ Module 1: IV價格區間預測 (多信心度) ────────┐\n"
        report += "│\n"
        report += f"│ 股票: {ticker}\n"
        report += f"│ 當前價格: ${results['stock_price']:.2f}\n"
        report += f"│ 隱含波動率: {results['implied_volatility']:.1f}%\n"
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
        """格式化 Black-Scholes 定價結果"""
        report = "\n┌─ Module 15: Black-Scholes 期權定價 ─────────┐\n"
        report += "│\n"
        
        if 'parameters' in results:
            params = results['parameters']
            report += f"│ 參數設置:\n"
            report += f"│   股價: ${params.get('stock_price', 0):.2f}\n"
            report += f"│   行使價: ${params.get('strike_price', 0):.2f}\n"
            report += f"│   無風險利率: {params.get('risk_free_rate', 0)*100:.2f}%\n"
            report += f"│   到期時間: {params.get('time_to_expiration', 0):.4f}年\n"
            report += f"│   波動率: {params.get('volatility', 0)*100:.2f}%\n"
            report += "│\n"
        
        if 'call' in results:
            call = results['call']
            report += f"│ 📈 Call 期權:\n"
            report += f"│   理論價格: ${call.get('option_price', 0):.2f}\n"
            report += f"│   d1: {call.get('d1', 0):.6f}\n"
            report += f"│   d2: {call.get('d2', 0):.6f}\n"
            report += "│\n"
        
        if 'put' in results:
            put = results['put']
            report += f"│ 📉 Put 期權:\n"
            report += f"│   理論價格: ${put.get('option_price', 0):.2f}\n"
            report += f"│   d1: {put.get('d1', 0):.6f}\n"
            report += f"│   d2: {put.get('d2', 0):.6f}\n"
        
        report += "│\n"
        report += "│ 💡 說明: Black-Scholes 模型計算的理論價格\n"
        report += "└────────────────────────────────────────────┘\n"
        return report
    
    def _format_module16_greeks(self, results: dict) -> str:
        """格式化 Greeks 結果"""
        report = "\n┌─ Module 16: Greeks 風險指標 ─────────────────┐\n"
        report += "│\n"
        
        if 'call' in results:
            call = results['call']
            report += f"│ 📈 Call Greeks:\n"
            report += f"│   Delta:  {call.get('delta', 0):8.4f}  (股價變動敏感度)\n"
            report += f"│   Gamma:  {call.get('gamma', 0):8.6f}  (Delta 變化率)\n"
            report += f"│   Theta:  {call.get('theta', 0):8.4f}  ($/天 時間衰減)\n"
            report += f"│   Vega:   {call.get('vega', 0):8.4f}  (波動率敏感度)\n"
            report += f"│   Rho:    {call.get('rho', 0):8.4f}  (利率敏感度)\n"
            report += "│\n"
        
        if 'put' in results:
            put = results['put']
            report += f"│ 📉 Put Greeks:\n"
            report += f"│   Delta:  {put.get('delta', 0):8.4f}\n"
            report += f"│   Gamma:  {put.get('gamma', 0):8.6f}\n"
            report += f"│   Theta:  {put.get('theta', 0):8.4f}  ($/天)\n"
            report += f"│   Vega:   {put.get('vega', 0):8.4f}\n"
            report += f"│   Rho:    {put.get('rho', 0):8.4f}\n"
        
        report += "│\n"
        report += "│ 💡 解讀:\n"
        report += "│   Delta: 股價每變動$1，期權價格變動\n"
        report += "│   Gamma: Delta 的變化速度\n"
        report += "│   Theta: 每天時間衰減的價值 ($/天)\n"
        report += "│   Vega: 波動率每變動1%，期權價格變動\n"
        report += "│   Rho: 利率每變動1%，期權價格變動\n"
        report += "└────────────────────────────────────────────┘\n"
        return report
    
    def _format_module17_implied_volatility(self, results: dict) -> str:
        """格式化隱含波動率結果"""
        report = "\n┌─ Module 17: 隱含波動率計算 ──────────────────┐\n"
        report += "│\n"
        
        if 'call' in results:
            call = results['call']
            converged = call.get('converged', False)
            report += f"│ 📈 Call IV:\n"
            report += f"│   隱含波動率: {call.get('implied_volatility', 0)*100:.2f}%\n"
            report += f"│   收斂狀態: {'* 成功' if converged else 'x 失敗'}\n"
            report += f"│   迭代次數: {call.get('iterations', 0)}\n"
            report += f"│   市場價格: ${call.get('market_price', 0):.2f}\n"
            report += "│\n"
        
        if 'put' in results:
            put = results['put']
            converged = put.get('converged', False)
            report += f"│ 📉 Put IV:\n"
            report += f"│   隱含波動率: {put.get('implied_volatility', 0)*100:.2f}%\n"
            report += f"│   收斂狀態: {'* 成功' if converged else 'x 失敗'}\n"
            report += f"│   迭代次數: {put.get('iterations', 0)}\n"
            report += f"│   市場價格: ${put.get('market_price', 0):.2f}\n"
        
        report += "│\n"
        report += "│ 💡 說明: 從市場價格反推的隱含波動率\n"
        report += "│   用於判斷市場對未來波動的預期\n"
        report += "└────────────────────────────────────────────┘\n"
        return report
    
    def _format_module18_historical_volatility(self, results: dict) -> str:
        """格式化歷史波動率結果"""
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
        """格式化 Module 3 套戥水位結果"""
        report = "\n┌─ Module 3: 套戥水位 ─────────────────────────┐\n"
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
        report += f"│   套戥價差: ${spread:.2f} ({spread_pct:+.2f}%)\n"
        report += "│\n"
        
        # 數據來源標註
        source = results.get('theoretical_price_source', 'N/A')
        note = results.get('note', '')
        report += f"│ 📊 數據來源:\n"
        report += f"│   理論價來源: {source}\n"
        if note:
            report += f"│   說明: {note}\n"
        report += "│\n"
        
        # IV 來源和值顯示（Requirements 4.3）
        iv_used = results.get('iv_used')
        iv_used_percent = results.get('iv_used_percent')
        iv_source = results.get('iv_source')
        iv_warning = results.get('iv_warning')
        
        if iv_used is not None or iv_source is not None:
            report += f"│ 📈 波動率 (IV) 信息:\n"
            if iv_used_percent is not None:
                report += f"│   使用的 IV: {iv_used_percent:.2f}%\n"
            elif iv_used is not None:
                report += f"│   使用的 IV: {iv_used*100:.2f}%\n"
            if iv_source:
                report += f"│   IV 來源: {iv_source}\n"
            report += "│\n"
        
        # IV 不一致警告顯示（Requirements 4.4）
        if iv_warning:
            report += f"│ ⚠️ IV 警告:\n"
            # 處理多個警告（用分號分隔）
            warnings = iv_warning.split("; ")
            for warning in warnings:
                report += f"│   {warning}\n"
            report += "│\n"
        
        # 套利機會評估
        if abs(spread_pct) > 5:
            report += f"│ ! 套利機會: 價差超過 5%，可能存在套利機會\n"
        elif abs(spread_pct) > 2:
            report += f"│ * 套利機會: 價差在 2-5%，需進一步評估\n"
        else:
            report += f"│ * 套利機會: 價差小於 2%，市場定價合理\n"
        
        report += "│\n"
        report += "│ 💡 解讀: 使用 Black-Scholes 期權理論價計算\n"
        report += "│   正價差: 市場價 > 理論價（期權可能高估）\n"
        report += "│   負價差: 市場價 < 理論價（期權可能低估）\n"
        report += "└────────────────────────────────────────────┘\n"
        return report
    
    def _format_module13_position_analysis(self, results: dict) -> str:
        """格式化 Module 13 倉位分析結果"""
        report = "\n┌─ Module 13: 倉位分析（含所有權結構）────────┐\n"
        report += "│\n"
        
        # 基本倉位信息
        report += f"│ 📊 倉位數據:\n"
        if 'volume' in results:
            report += f"│   成交量: {results.get('volume', 0):,}\n"
        if 'open_interest' in results:
            report += f"│   未平倉量: {results.get('open_interest', 0):,}\n"
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
    
    def _format_module14_monitoring_posts(self, results: dict) -> str:
        """格式化 Module 14 監察崗位結果"""
        report = "\n┌─ Module 14: 12監察崗位（含 RSI/Beta）────────┐\n"
        report += "│\n"
        
        # 基本監察數據
        report += f"│ 🔍 監察指標:\n"
        if 'delta' in results:
            report += f"│   Delta: {results.get('delta', 0):.4f}\n"
        if 'iv' in results:
            report += f"│   隱含波動率: {results.get('iv', 0):.2f}%\n"
        if 'atr' in results:
            report += f"│   ATR: ${results.get('atr', 0):.2f}\n"
        if 'bid_ask_spread' in results:
            report += f"│   買賣價差: ${results.get('bid_ask_spread', 0):.2f}\n"
        report += "│\n"
        
        # Finviz RSI 和 Beta 數據
        has_finviz_data = False
        if 'rsi' in results or 'beta' in results:
            has_finviz_data = True
            report += f"│ 📊 技術指標 (Finviz):\n"
            
            if 'rsi' in results:
                rsi = results.get('rsi', 0)
                rsi_status = results.get('rsi_status', '')
                report += f"│   RSI: {rsi:.2f}\n"
                if rsi_status:
                    report += f"│   {rsi_status}\n"
            
            if 'beta' in results:
                beta = results.get('beta', 0)
                beta_status = results.get('beta_status', '')
                report += f"│   Beta: {beta:.2f}\n"
                if beta_status:
                    report += f"│   {beta_status}\n"
            
            report += "│\n"
        
        # 風險評估
        if 'risk_level' in results:
            report += f"│ ! 風險等級: {results.get('risk_level', 'N/A')}\n"
        
        if 'monitoring_alerts' in results:
            alerts = results.get('monitoring_alerts', [])
            if alerts:
                report += f"│ 🚨 監察警報:\n"
                for alert in alerts:
                    report += f"│   • {alert}\n"
        
        if has_finviz_data:
            report += "│\n"
            report += "│ 📌 數據來源: Finviz (RSI/Beta 數據)\n"
        
        report += "│\n"
        report += "│ 💡 解讀:\n"
        report += "│   RSI > 70: 超買，可能回調\n"
        report += "│   RSI < 30: 超賣，可能反彈\n"
        report += "│   Beta > 1: 波動性高於市場\n"
        report += "│   Beta < 1: 波動性低於市場\n"
        report += "└────────────────────────────────────────────┘\n"
        return report
    
    def _format_module20_fundamental_health(self, results: dict) -> str:
        """格式化 Module 20 基本面健康檢查結果"""
        report = "\n┌─ Module 20: 基本面健康檢查 ──────────────────┐\n"
        report += "│\n"
        
        # 檢查是否跳過
        if results.get('status') == 'skipped':
            report += f"│ ! 狀態: 跳過執行\n"
            report += f"│ 原因: {results.get('reason', 'N/A')}\n"
            available = results.get('available_metrics', 0)
            required = results.get('required_metrics', 3)
            report += f"│ 可用指標: {available}/{required}\n"
            report += "│\n"
            report += "│ 💡 說明: 需要至少 3 個基本面指標才能執行分析\n"
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
        
        # 各項指標
        report += f"│ 📊 基本面指標:\n"
        if 'peg_ratio' in results:
            peg = results.get('peg_ratio', 0)
            report += f"│   PEG 比率: {peg:.2f}\n"
        if 'roe' in results:
            roe = results.get('roe', 0)
            report += f"│   ROE: {roe:.2f}%\n"
        if 'profit_margin' in results:
            margin = results.get('profit_margin', 0)
            report += f"│   淨利潤率: {margin:.2f}%\n"
        if 'debt_eq' in results:
            debt = results.get('debt_eq', 0)
            report += f"│   負債/股本: {debt:.2f}\n"
        if 'inst_own' in results:
            inst = results.get('inst_own', 0)
            report += f"│   機構持股: {inst:.2f}%\n"
        report += "│\n"
        
        # 數據來源
        report += f"│ 📌 數據來源: {data_source}\n"
        if available_metrics < 5:
            report += f"│ ! 注意: 僅使用 {available_metrics}/5 個指標\n"
        report += "│\n"
        
        # 等級解讀
        report += f"│ 💡 等級解讀:\n"
        report += f"│   A (90-100): 優秀，基本面非常健康\n"
        report += f"│   B (80-89): 良好，基本面健康\n"
        report += f"│   C (70-79): 中等，基本面一般\n"
        report += f"│   D (60-69): 較差，需謹慎\n"
        report += f"│   F (<60): 差，基本面存在問題\n"
        report += "└────────────────────────────────────────────┘\n"
        return report
    
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
        """格式化 Module 22 最佳行使價分析結果"""
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
        
        # 顯示分析範圍（從任一策略獲取）
        for strategy_key in ['long_call', 'long_put', 'short_call', 'short_put']:
            if strategy_key in results:
                strategy_data = results[strategy_key]
                if 'strike_range' in strategy_data:
                    sr = strategy_data['strike_range']
                    report += f"│ 📊 分析範圍: ${sr.get('min', 0):.2f} - ${sr.get('max', 0):.2f} (ATM ±{sr.get('range_pct', 20):.0f}%)\n"
                if 'total_analyzed' in strategy_data:
                    report += f"│ 📈 分析行使價數量: {strategy_data.get('total_analyzed', 0)}\n"
                report += "│\n"
                break
        
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
            
            # 顯示 Top 3 推薦
            if 'top_recommendations' in strategy_data and strategy_data['top_recommendations']:
                for i, rec in enumerate(strategy_data['top_recommendations'][:3]):
                    strike = rec.get('strike', 0)
                    score = rec.get('composite_score', 0)
                    delta = rec.get('delta', 0)
                    theta = rec.get('theta', 0)
                    gamma = rec.get('gamma', 0)
                    vega = rec.get('vega', 0)
                    reason = rec.get('reason', '')
                    
                    if i == 0:
                        stars = '★' * int(score / 20) + '☆' * (5 - int(score / 20))
                        report += f"│   🥇 推薦 #1: ${strike:.2f} ({stars} {score:.1f}分)\n"
                    elif i == 1:
                        report += f"│   🥈 推薦 #2: ${strike:.2f} ({score:.1f}分)\n"
                    else:
                        report += f"│   🥉 推薦 #3: ${strike:.2f} ({score:.1f}分)\n"
                    
                    # 顯示完整 Greeks
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
            else:
                report += f"│   ! 無推薦（數據不足）\n"
            
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
        report += "└────────────────────────────────────────────────┘\n"
        
        # 添加波動率微笑分析（如果存在）
        # 從任一策略中獲取波動率微笑數據
        smile_data = None
        for strategy_key in ['long_call', 'long_put', 'short_call', 'short_put']:
            if strategy_key in results and 'volatility_smile' in results[strategy_key]:
                smile_data = results[strategy_key]['volatility_smile']
                break
        
        if smile_data:
            report += self._format_volatility_smile(smile_data)
        
        # 添加 Put-Call Parity 驗證（如果存在）
        parity_data = None
        for strategy_key in ['long_call', 'long_put', 'short_call', 'short_put']:
            if strategy_key in results and 'parity_validation' in results[strategy_key]:
                parity_data = results[strategy_key]['parity_validation']
                break
        
        if parity_data:
            report += self._format_parity_validation(parity_data)
        
        return report
    
    def _format_volatility_smile(self, smile_data: dict) -> str:
        """格式化波動率微笑分析結果"""
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
        
        # 微笑形狀解讀
        report += f"│ 💡 形狀解讀:\n"
        if smile_shape == 'put_skew':
            report += "│   Put Skew: OTM Put IV > OTM Call IV\n"
            report += "│   市場預期下跌風險較大（股票期權常見）\n"
        elif smile_shape == 'call_skew':
            report += "│   Call Skew: OTM Call IV > OTM Put IV\n"
            report += "│   市場預期上漲風險較大（商品期權常見）\n"
        else:
            report += "│   Symmetric: OTM Put IV ≈ OTM Call IV\n"
            report += "│   市場對上下風險預期相近\n"
        
        report += "└────────────────────────────────────────────────┘\n"
        return report
    
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
    
    def _format_module23_dynamic_iv_threshold(self, results: dict) -> str:
        """格式化 Module 23 動態IV閾值結果"""
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
        
        # 數據質量和可靠性 (Requirements 5.2, 5.3)
        historical_days = results.get('historical_days', 0)
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
        report += "│ 📖 解讀:\n"
        report += "│   🔴 HIGH: IV 偏高，考慮賣出期權\n"
        report += "│   🟢 NORMAL: IV 合理，等待機會\n"
        report += "│   🔵 LOW: IV 偏低，考慮買入期權\n"
        report += "└────────────────────────────────────────────────┘\n"
        return report
    
    def _format_data_source_summary(self, raw_data: dict, calculation_results: dict) -> str:
        """格式化數據來源摘要"""
        report = "\n" + "=" * 70 + "\n"
        report += "數據來源摘要\n"
        report += "=" * 70 + "\n\n"
        
        # Finviz 數據可用性
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
    
    def _format_strategy_results(self, module_name: str, results: list) -> str:
        """格式化策略損益結果（Module 7-10）- 增強版"""
        strategy_names = {
            'module7_long_call': ('Long Call', '📈'),
            'module8_long_put': ('Long Put', '📉'),
            'module9_short_call': ('Short Call', '📊'),
            'module10_short_put': ('Short Put', '💼')
        }
        
        name, emoji = strategy_names.get(module_name, (module_name, '📋'))
        
        report = f"\n┌─ {emoji} {name} 策略損益分析 ────────────────────┐\n"
        report += "│\n"
        
        # 添加策略基本信息（從第一個結果提取）
        if isinstance(results, list) and len(results) > 0:
            first_result = results[0]
            strike = first_result.get('strike_price', 0)
            premium = first_result.get('option_premium', 0)
            breakeven = first_result.get('breakeven_price', 0)
            
            report += f"│ 行使價: ${strike:.2f}\n"
            report += f"│ 權利金: ${premium:.2f}\n"
            if breakeven > 0:
                report += f"│ 盈虧平衡點: ${breakeven:.2f}\n"
            report += "│\n"
        
        report += "│ 到期股價 | 行使價  | 權利金  | 損益    | 收益率\n"
        report += "│ ─────────┼─────────┼─────────┼─────────┼────────\n"
        
        if isinstance(results, list) and len(results) > 0:
            for i, result in enumerate(results):
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
                
                report += f"│ ${stock_price:7.2f} | "
                report += f"${strike:7.2f} | "
                report += f"${premium:7.2f} | "
                report += f"{profit_symbol}${profit:6.2f} | "
                report += f"{return_symbol}{return_pct:6.1f}%\n"
        else:
            report += "│ （無數據）\n"
        
        report += "│\n"
        report += "│ 💡 說明:\n"
        report += "│   - 場景 1: 股價下跌 10%\n"
        report += "│   - 場景 2: 股價維持不變\n"
        report += "│   - 場景 3: 股價上漲 10%\n"
        report += "└────────────────────────────────────────────────┘\n"
        return report
    
    def _format_strategy_recommendations(self, recommendations: list) -> str:
        """格式化策略推薦結果（含信心度）"""
        report = "\n" + "=" * 70 + "\n"
        report += "策略推薦分析 (含信心度)\n"
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
            else:
                strategy_name = getattr(rec, 'strategy_name', 'N/A')
                direction = getattr(rec, 'direction', 'N/A')
                confidence = getattr(rec, 'confidence', 'N/A')
                reasoning = getattr(rec, 'reasoning', [])
                suggested_strike = getattr(rec, 'suggested_strike', None)
                key_levels = getattr(rec, 'key_levels', {})
            
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
