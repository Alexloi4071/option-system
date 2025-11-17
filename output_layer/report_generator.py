# output_layer/report_generator.py
"""
報告生成系統 (第1階段)
"""

import json
import csv
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ReportGenerator:
    """專業報告生成器"""
    
    def __init__(self, output_dir='output/'):
        """初始化報告生成器"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        logger.info(f"✓ 報告輸出目錄: {self.output_dir}")
    
    def generate(self, 
                ticker: str,
                analysis_date: str,
                raw_data: dict,
                calculation_results: dict,
                data_fetcher=None) -> dict:
        """
        生成完整分析報告
        
        參數:
            ticker: 股票代碼
            analysis_date: 分析日期
            raw_data: 原始數據
            calculation_results: 計算結果
            data_fetcher: DataFetcher 實例（用於獲取 API 狀態）
        
        返回: dict (報告文件位置)
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
                    logger.warning(f"⚠ 無法獲取 API 狀態: {e}")
            
            # 1. 生成JSON報告
            json_report = self._generate_json_report(
                ticker, analysis_date, raw_data, calculation_results, api_status
            )
            json_filename = f"report_{ticker}_{timestamp}.json"
            self._save_json(json_report, json_filename)
            
            # 2. 生成CSV報告
            csv_filename = f"report_{ticker}_{timestamp}.csv"
            self._generate_csv_report(calculation_results, csv_filename, api_status)
            
            # 3. 生成純文本報告
            text_filename = f"report_{ticker}_{timestamp}.txt"
            self._generate_text_report(
                ticker, analysis_date, raw_data, calculation_results, text_filename, api_status
            )
            
            logger.info(f"✓ 報告已生成")
            logger.info(f"  JSON: {json_filename}")
            logger.info(f"  CSV: {csv_filename}")
            logger.info(f"  TXT: {text_filename}")
            
            return {
                'json_file': str(self.output_dir / json_filename),
                'csv_file': str(self.output_dir / csv_filename),
                'text_file': str(self.output_dir / text_filename),
                'timestamp': timestamp
            }
            
        except Exception as e:
            logger.error(f"✗ 報告生成失敗: {e}")
            raise
    
    def _generate_json_report(self, ticker, analysis_date, raw_data, calculation_results, api_status=None):
        """生成JSON報告"""
        report = {
            'metadata': {
                'system': 'Options Trading Analysis System',
                'version': '1.0',
                'generated_at': datetime.now().isoformat(),
                'ticker': ticker,
                'analysis_date': analysis_date
            },
            'raw_data': raw_data,
            'calculations': calculation_results
        }
        
        # 添加 API 狀態信息
        if api_status:
            report['api_status'] = api_status
        
        return report
    
    def _save_json(self, data, filename):
        """保存JSON文件"""
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"✓ JSON報告已保存: {filepath}")
    
    def _generate_csv_report(self, calculation_results, filename, api_status=None):
        """生成CSV報告"""
        filepath = self.output_dir / filename
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['模塊', '指標', '數值'])
            
            for module_name, module_data in calculation_results.items():
                if isinstance(module_data, dict):
                    for key, value in module_data.items():
                        writer.writerow([module_name, key, value])
            
            # 添加 API 狀態信息
            if api_status:
                writer.writerow(['', '', ''])
                writer.writerow(['API狀態', '數據源', ''])
                writer.writerow(['API狀態', 'IBKR啟用', api_status.get('ibkr_enabled', False)])
                writer.writerow(['API狀態', 'IBKR連接', api_status.get('ibkr_connected', False)])
                if api_status.get('fallback_used'):
                    for data_type, sources in api_status['fallback_used'].items():
                        writer.writerow(['API狀態', f'降級使用-{data_type}', ', '.join(sources)])
        
        logger.info(f"✓ CSV報告已保存: {filepath}")
    
    def _generate_text_report(self, ticker, analysis_date, raw_data, 
                             calculation_results, filename, api_status=None):
        """生成純文本報告"""
        filepath = self.output_dir / filename
        
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
                f.write(f"當前股價: ${raw_data.get('current_price', 'N/A'):.2f}\n")
                f.write(f"隱含波動率: {raw_data.get('implied_volatility', 'N/A'):.2f}%\n")
                f.write(f"EPS: ${raw_data.get('eps', 'N/A'):.2f}\n")
                f.write(f"派息: ${raw_data.get('annual_dividend', 'N/A'):.2f}\n")
                f.write(f"無風險利率: {raw_data.get('risk_free_rate', 'N/A'):.2f}%\n")
                f.write(f"VIX: {raw_data.get('vix', 'N/A'):.2f}\n\n")
            
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
                    
                f.write(f"\n{module_name}:\n")
                if isinstance(module_data, dict):
                    for key, value in module_data.items():
                        f.write(f"  {key}: {value}\n")
        
        logger.info(f"✓ 文本報告已保存: {filepath}")
    
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
