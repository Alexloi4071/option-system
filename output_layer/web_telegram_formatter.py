# output_layer/web_telegram_formatter.py
"""
Web 和 Telegram 格式化器
用於將分析結果轉換為適合 Web 界面和 Telegram 消息的格式
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class WebFormatter:
    """Web 界面格式化器"""
    
    @staticmethod
    def format_for_html(structured_data: dict) -> dict:
        """
        將結構化數據轉換為 HTML 友好格式
        
        返回包含 HTML 片段的字典，可直接用於 Web 模板
        """
        html_output = {}
        
        for module_name, data in structured_data.items():
            if not data:
                continue
            
            data_type = data.get('type') if isinstance(data, dict) else None
            
            if data_type == 'support_resistance':
                html_output[module_name] = WebFormatter._html_support_resistance(data)
            elif data_type == 'black_scholes':
                html_output[module_name] = WebFormatter._html_black_scholes(data)
            elif data_type == 'greeks':
                html_output[module_name] = WebFormatter._html_greeks(data)
            elif data_type == 'implied_volatility':
                html_output[module_name] = WebFormatter._html_implied_volatility(data)
            elif data_type == 'historical_volatility':
                html_output[module_name] = WebFormatter._html_historical_volatility(data)
            elif data_type == 'put_call_parity':
                html_output[module_name] = WebFormatter._html_put_call_parity(data)
            elif data_type == 'strategy':
                html_output[module_name] = WebFormatter._html_strategy(data)
            else:
                html_output[module_name] = {'raw': data}
        
        return html_output
    
    @staticmethod
    def _html_support_resistance(data: dict) -> dict:
        """格式化支撐/阻力位為 HTML"""
        return {
            'title': '支撐/阻力位分析',
            'stock_price': data.get('stock_price'),
            'iv': data.get('implied_volatility'),
            'levels': [
                {
                    'confidence': level['level'],
                    'support': f"${level['support']:.2f}",
                    'resistance': f"${level['resistance']:.2f}",
                    'range': f"±{level['move_percentage']:.1f}%"
                }
                for level in data.get('confidence_levels', [])
            ]
        }
    
    @staticmethod
    def _html_black_scholes(data: dict) -> dict:
        """格式化 Black-Scholes 為 HTML"""
        return {
            'title': 'Black-Scholes 期權定價',
            'call_price': f"${data['call']['price']:.2f}" if data.get('call') else 'N/A',
            'put_price': f"${data['put']['price']:.2f}" if data.get('put') else 'N/A',
            'parameters': data.get('parameters', {})
        }
    
    @staticmethod
    def _html_greeks(data: dict) -> dict:
        """格式化 Greeks 為 HTML"""
        return {
            'title': 'Greeks 風險指標',
            'call': {
                'delta': f"{data['call']['delta']:.4f}",
                'gamma': f"{data['call']['gamma']:.6f}",
                'theta': f"{data['call']['theta']:.4f} ($/天)",
                'vega': f"{data['call']['vega']:.4f}",
                'rho': f"{data['call']['rho']:.4f}"
            } if data.get('call') else None,
            'put': {
                'delta': f"{data['put']['delta']:.4f}",
                'gamma': f"{data['put']['gamma']:.6f}",
                'theta': f"{data['put']['theta']:.4f} ($/天)",
                'vega': f"{data['put']['vega']:.4f}",
                'rho': f"{data['put']['rho']:.4f}"
            } if data.get('put') else None
        }
    
    @staticmethod
    def _html_implied_volatility(data: dict) -> dict:
        """格式化隱含波動率為 HTML"""
        return {
            'title': '隱含波動率',
            'call_iv': f"{data['call']['iv']*100:.2f}%" if data.get('call') and data['call'].get('iv') else 'N/A',
            'call_converged': data['call']['converged'] if data.get('call') else False,
            'put_iv': f"{data['put']['iv']*100:.2f}%" if data.get('put') and data['put'] and data['put'].get('iv') else 'N/A',
            'put_converged': data['put']['converged'] if data.get('put') and data['put'] else False
        }
    
    @staticmethod
    def _html_historical_volatility(data: dict) -> dict:
        """格式化歷史波動率為 HTML"""
        return {
            'title': '歷史波動率分析',
            'hv_windows': {
                window: f"{hv*100:.2f}%" if hv else 'N/A'
                for window, hv in data.get('hv_windows', {}).items()
            },
            'iv_hv_ratio': data.get('iv_hv_comparison', {}).get('ratio'),
            'assessment': data.get('iv_hv_comparison', {}).get('assessment')
        }
    
    @staticmethod
    def _html_put_call_parity(data: dict) -> dict:
        """格式化 Put-Call Parity 為 HTML"""
        return {
            'title': 'Put-Call Parity 驗證',
            'market_deviation': f"${abs(data['market']['deviation']):.4f}" if data.get('market') and data['market'].get('deviation') else 'N/A',
            'has_arbitrage': data['market']['has_arbitrage'] if data.get('market') else False,
            'profit': f"${data['market']['profit']:.2f}" if data.get('market') and data['market'].get('profit') else 'N/A'
        }
    
    @staticmethod
    def _html_strategy(data: dict) -> dict:
        """格式化策略為 HTML"""
        return {
            'title': '策略損益分析',
            'scenarios': [
                {
                    'stock_price': f"${scenario['stock_price']:.2f}",
                    'profit_loss': f"${scenario['profit_loss']:.2f}",
                    'return_pct': f"{scenario['return_percentage']:.1f}%",
                    'is_profit': scenario['profit_loss'] >= 0
                }
                for scenario in data.get('scenarios', [])
            ]
        }


class TelegramFormatter:
    """Telegram 消息格式化器"""
    
    @staticmethod
    def format_for_telegram(structured_data: dict, ticker: str) -> List[str]:
        """
        將結構化數據轉換為 Telegram 消息格式
        
        返回消息列表（因為 Telegram 有字符限制，可能需要分多條發送）
        """
        messages = []
        
        # 標題消息
        header = f"📊 *{ticker} 期權分析報告*\n"
        header += f"━━━━━━━━━━━━━━━━━━━━\n\n"
        messages.append(header)
        
        for module_name, data in structured_data.items():
            if not data:
                continue
            
            data_type = data.get('type') if isinstance(data, dict) else None
            
            if data_type == 'support_resistance':
                messages.append(TelegramFormatter._telegram_support_resistance(data))
            elif data_type == 'black_scholes':
                messages.append(TelegramFormatter._telegram_black_scholes(data))
            elif data_type == 'greeks':
                messages.append(TelegramFormatter._telegram_greeks(data))
            elif data_type == 'implied_volatility':
                messages.append(TelegramFormatter._telegram_implied_volatility(data))
            elif data_type == 'historical_volatility':
                messages.append(TelegramFormatter._telegram_historical_volatility(data))
            elif data_type == 'put_call_parity':
                messages.append(TelegramFormatter._telegram_put_call_parity(data))
            elif data_type == 'strategy':
                messages.append(TelegramFormatter._telegram_strategy(module_name, data))
        
        return messages
    
    @staticmethod
    def _telegram_support_resistance(data: dict) -> str:
        """格式化支撐/阻力位為 Telegram 消息"""
        msg = "📍 *支撐/阻力位分析*\n\n"
        msg += f"當前股價: `${data.get('stock_price', 0):.2f}`\n"
        msg += f"隱含波動率: `{data.get('implied_volatility', 0):.1f}%`\n\n"
        
        for level in data.get('confidence_levels', []):
            msg += f"*{level['level']} 信心度*\n"
            msg += f"  支撐位: `${level['support']:.2f}`\n"
            msg += f"  阻力位: `${level['resistance']:.2f}`\n"
            msg += f"  波動: `±{level['move_percentage']:.1f}%`\n\n"
        
        return msg
    
    @staticmethod
    def _telegram_black_scholes(data: dict) -> str:
        """格式化 Black-Scholes 為 Telegram 消息"""
        msg = "🎯 *Black-Scholes 期權定價*\n\n"
        
        if data.get('call'):
            msg += f"📈 Call 期權: `${data['call']['price']:.2f}`\n"
        if data.get('put'):
            msg += f"📉 Put 期權: `${data['put']['price']:.2f}`\n"
        
        msg += "\n"
        return msg
    
    @staticmethod
    def _telegram_greeks(data: dict) -> str:
        """格式化 Greeks 為 Telegram 消息"""
        msg = "📊 *Greeks 風險指標*\n\n"
        
        if data.get('call'):
            call = data['call']
            msg += "*Call Greeks:*\n"
            msg += f"  Delta: `{call.get('delta', 0):.4f}`\n"
            msg += f"  Gamma: `{call.get('gamma', 0):.6f}`\n"
            msg += f"  Theta: `{call.get('theta', 0):.4f}` ($/天)\n"
            msg += f"  Vega: `{call.get('vega', 0):.4f}`\n"
            msg += f"  Rho: `{call.get('rho', 0):.4f}`\n\n"
        
        if data.get('put'):
            put = data['put']
            msg += "*Put Greeks:*\n"
            msg += f"  Delta: `{put.get('delta', 0):.4f}`\n"
            msg += f"  Gamma: `{put.get('gamma', 0):.6f}`\n"
            msg += f"  Theta: `{put.get('theta', 0):.4f}` ($/天)\n"
            msg += f"  Vega: `{put.get('vega', 0):.4f}`\n"
            msg += f"  Rho: `{put.get('rho', 0):.4f}`\n\n"
        
        return msg
    
    @staticmethod
    def _telegram_implied_volatility(data: dict) -> str:
        """格式化隱含波動率為 Telegram 消息"""
        msg = "🔍 *隱含波動率*\n\n"
        
        if data.get('call'):
            call = data['call']
            status = "✅" if call.get('converged') else "❌"
            msg += f"Call IV: `{call['iv']*100:.2f}%` {status}\n"
        
        if data.get('put') and data['put']:
            put = data['put']
            status = "✅" if put.get('converged') else "❌"
            msg += f"Put IV: `{put['iv']*100:.2f}%` {status}\n"
        
        msg += "\n"
        return msg
    
    @staticmethod
    def _telegram_historical_volatility(data: dict) -> str:
        """格式化歷史波動率為 Telegram 消息"""
        msg = "📈 *歷史波動率分析*\n\n"
        
        for window, hv in data.get('hv_windows', {}).items():
            msg += f"{window}天: `{hv*100:.2f}%`\n"
        
        if data.get('iv_hv_comparison'):
            comp = data['iv_hv_comparison']
            msg += f"\nIV/HV 比率: `{comp.get('ratio', 0):.2f}`\n"
            msg += f"評估: {comp.get('assessment', 'N/A')}\n"
        
        msg += "\n"
        return msg
    
    @staticmethod
    def _telegram_put_call_parity(data: dict) -> str:
        """格式化 Put-Call Parity 為 Telegram 消息"""
        msg = "⚖️ *Put-Call Parity 驗證*\n\n"
        
        if data.get('market'):
            market = data['market']
            has_arb = "✅ 存在" if market.get('has_arbitrage') else "❌ 不存在"
            msg += f"市場偏離: `${abs(market.get('deviation', 0)):.4f}`\n"
            msg += f"套利機會: {has_arb}\n"
            
            if market.get('has_arbitrage') and market.get('profit'):
                msg += f"理論利潤: `${market['profit']:.2f}`\n"
        
        msg += "\n"
        return msg
    
    @staticmethod
    def _telegram_strategy(module_name: str, data: dict) -> str:
        """格式化策略為 Telegram 消息"""
        strategy_names = {
            'module7_long_call': '📈 Long Call',
            'module8_long_put': '📉 Long Put',
            'module9_short_call': '📊 Short Call',
            'module10_short_put': '💼 Short Put'
        }
        
        title = strategy_names.get(module_name, '策略分析')
        msg = f"*{title} 策略損益*\n\n"
        
        for i, scenario in enumerate(data.get('scenarios', []), 1):
            profit = scenario['profit_loss']
            symbol = "💰" if profit >= 0 else "📉"
            msg += f"{symbol} 場景 {i}:\n"
            msg += f"  股價: `${scenario['stock_price']:.2f}`\n"
            msg += f"  損益: `${profit:.2f}` ({scenario['return_percentage']:.1f}%)\n\n"
        
        return msg


# 使用示例
if __name__ == "__main__":
    # 示例：如何使用這些格式化器
    
    # 1. 從 ReportGenerator 獲取結構化數據
    from output_layer.report_generator import ReportGenerator
    
    generator = ReportGenerator()
    # structured_data = generator.get_structured_output(calculation_results)
    
    # 2. 轉換為 Web 格式
    # web_data = WebFormatter.format_for_html(structured_data)
    
    # 3. 轉換為 Telegram 格式
    # telegram_messages = TelegramFormatter.format_for_telegram(structured_data, 'AAPL')
    
    print("✓ Web 和 Telegram 格式化器已就緒")
