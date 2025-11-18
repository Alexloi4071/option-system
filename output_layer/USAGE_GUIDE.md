# 輸出層使用指南

## 📋 概述

輸出層已經完全優化，支持：
- ✅ 所有 19 個模塊的友好格式化
- ✅ Web 界面集成
- ✅ Telegram Bot 集成
- ✅ 結構化數據輸出

---

## 🎯 主要改進

### 1. 友好的文本格式

**Module 15-19** 現在有專門的格式化：

```
┌─ Module 15: Black-Scholes 期權定價 ─────────┐
│
│ 參數設置:
│   股價: $150.25
│   行使價: $155.00
│   無風險利率: 4.50%
│   到期時間: 0.2500年
│   波動率: 25.00%
│
│ 📈 Call 期權:
│   理論價格: $10.50
│   d1: 0.123456
│   d2: 0.098765
│
│ 📉 Put 期權:
│   理論價格: $8.20
│   d1: 0.123456
│   d2: 0.098765
│
│ 💡 說明: Black-Scholes 模型計算的理論價格
└────────────────────────────────────────────┘
```

**Module 7-10** 策略損益表格化：

```
┌─ 📈 Long Call 策略損益分析 ────────────────────┐
│
│ 到期股價 | 行使價  | 權利金  | 損益    | 收益率
│ ─────────┼─────────┼─────────┼─────────┼────────
│ $135.23 | $150.00 | $  5.50 | -$ 5.50 |  -100.0%
│ $150.25 | $150.00 | $  5.50 | -$ 5.50 |  -100.0%
│ $165.28 | $150.00 | $  5.50 | +$ 9.78 |  +177.8%
│
│ 💡 說明: 不同到期股價下的損益情況
└────────────────────────────────────────────────┘
```

---

## 🌐 Web 界面集成

### 基本使用

```python
from main import OptionsAnalysisSystem
from output_layer.report_generator import ReportGenerator
from output_layer.web_telegram_formatter import WebFormatter

# 1. 運行分析
system = OptionsAnalysisSystem(use_ibkr=False)
results = system.run_complete_analysis(ticker='AAPL')

# 2. 獲取結構化數據
generator = ReportGenerator()
structured_data = generator.get_structured_output(results['calculations'])

# 3. 轉換為 Web 格式
web_data = WebFormatter.format_for_html(structured_data)

# 4. 在 Web 模板中使用
# web_data 包含所有模塊的 HTML 友好格式
```

### Web 數據結構

```python
{
    'module15_black_scholes': {
        'title': 'Black-Scholes 期權定價',
        'call_price': '$10.50',
        'put_price': '$8.20',
        'parameters': {...}
    },
    'module16_greeks': {
        'title': 'Greeks 風險指標',
        'call': {
            'delta': '0.5234',
            'gamma': '0.012345',
            'theta': '-0.0234',
            'vega': '0.1234',
            'rho': '0.0567'
        },
        'put': {...}
    },
    ...
}
```

### Flask 示例

```python
from flask import Flask, render_template, jsonify
from main import OptionsAnalysisSystem
from output_layer.report_generator import ReportGenerator
from output_layer.web_telegram_formatter import WebFormatter

app = Flask(__name__)

@app.route('/analyze/<ticker>')
def analyze(ticker):
    # 運行分析
    system = OptionsAnalysisSystem(use_ibkr=False)
    results = system.run_complete_analysis(ticker=ticker)
    
    # 獲取結構化數據
    generator = ReportGenerator()
    structured_data = generator.get_structured_output(results['calculations'])
    
    # 轉換為 Web 格式
    web_data = WebFormatter.format_for_html(structured_data)
    
    return render_template('analysis.html', 
                         ticker=ticker, 
                         data=web_data)

@app.route('/api/analyze/<ticker>')
def api_analyze(ticker):
    # API 端點返回 JSON
    system = OptionsAnalysisSystem(use_ibkr=False)
    results = system.run_complete_analysis(ticker=ticker)
    
    generator = ReportGenerator()
    structured_data = generator.get_structured_output(results['calculations'])
    
    return jsonify(structured_data)
```

---

## 📱 Telegram Bot 集成

### 基本使用

```python
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from main import OptionsAnalysisSystem
from output_layer.report_generator import ReportGenerator
from output_layer.web_telegram_formatter import TelegramFormatter

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理 /analyze 命令"""
    
    # 獲取股票代碼
    if not context.args:
        await update.message.reply_text("請提供股票代碼，例如: /analyze AAPL")
        return
    
    ticker = context.args[0].upper()
    
    # 發送處理中消息
    await update.message.reply_text(f"正在分析 {ticker}，請稍候...")
    
    try:
        # 運行分析
        system = OptionsAnalysisSystem(use_ibkr=False)
        results = system.run_complete_analysis(ticker=ticker)
        
        # 獲取結構化數據
        generator = ReportGenerator()
        structured_data = generator.get_structured_output(results['calculations'])
        
        # 轉換為 Telegram 格式
        messages = TelegramFormatter.format_for_telegram(structured_data, ticker)
        
        # 發送消息（分批發送，避免超過字符限制）
        for msg in messages:
            await update.message.reply_text(
                msg, 
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
    
    except Exception as e:
        await update.message.reply_text(f"分析失敗: {str(e)}")

# 創建 Bot
def main():
    application = Application.builder().token("YOUR_BOT_TOKEN").build()
    
    # 添加命令處理器
    application.add_handler(CommandHandler("analyze", analyze_command))
    
    # 啟動 Bot
    application.run_polling()

if __name__ == '__main__':
    main()
```

### Telegram 消息格式

```
📊 *AAPL 期權分析報告*
━━━━━━━━━━━━━━━━━━━━

📍 *支撐/阻力位分析*

當前股價: `$150.25`
隱含波動率: `25.0%`

*68% 信心度*
  支撐位: `$145.20`
  阻力位: `$155.30`
  波動: `±3.4%`

*90% 信心度*
  支撐位: `$140.15`
  阻力位: `$160.35`
  波動: `±6.7%`

🎯 *Black-Scholes 期權定價*

📈 Call 期權: `$10.50`
📉 Put 期權: `$8.20`

📊 *Greeks 風險指標*

*Call Greeks:*
  Delta: `0.5234`
  Gamma: `0.012345`
  Theta: `-0.0234`
  Vega: `0.1234`
  Rho: `0.0567`
```

---

## 📊 結構化數據格式

### get_structured_output() 返回格式

```python
{
    'module1_support_resistance_multi': {
        'type': 'support_resistance',
        'stock_price': 150.25,
        'implied_volatility': 25.0,
        'days_to_expiration': 30,
        'confidence_levels': [
            {
                'level': '68%',
                'z_score': 1.0,
                'support': 145.20,
                'resistance': 155.30,
                'move_percentage': 3.4
            },
            ...
        ]
    },
    'module15_black_scholes': {
        'type': 'black_scholes',
        'call': {
            'price': 10.50,
            'd1': 0.123456,
            'd2': 0.098765
        },
        'put': {
            'price': 8.20,
            'd1': 0.123456,
            'd2': 0.098765
        },
        'parameters': {...}
    },
    'module16_greeks': {
        'type': 'greeks',
        'call': {
            'delta': 0.5234,
            'gamma': 0.012345,
            'theta': -0.0234,
            'vega': 0.1234,
            'rho': 0.0567
        },
        'put': {...}
    },
    ...
}
```

---

## 🎨 自定義格式化

### 添加自定義格式化器

```python
from output_layer.web_telegram_formatter import WebFormatter

class CustomFormatter(WebFormatter):
    """自定義格式化器"""
    
    @staticmethod
    def format_for_mobile(structured_data: dict) -> dict:
        """為移動端優化的格式"""
        mobile_output = {}
        
        for module_name, data in structured_data.items():
            # 自定義格式化邏輯
            mobile_output[module_name] = {
                'title': data.get('title', module_name),
                'summary': CustomFormatter._create_summary(data),
                'details': data
            }
        
        return mobile_output
    
    @staticmethod
    def _create_summary(data: dict) -> str:
        """創建摘要"""
        # 根據數據類型創建簡短摘要
        data_type = data.get('type')
        
        if data_type == 'black_scholes':
            return f"Call: ${data['call']['price']:.2f}, Put: ${data['put']['price']:.2f}"
        elif data_type == 'greeks':
            return f"Delta: {data['call']['delta']:.4f}"
        # ... 其他類型
        
        return "查看詳情"
```

---

## 📝 完整示例

### 命令行使用

```bash
# 運行分析並生成所有格式的報告
python main.py --ticker AAPL

# 輸出文件：
# - output/report_AAPL_20241118_123456.json  (JSON 格式)
# - output/report_AAPL_20241118_123456.csv   (CSV 格式)
# - output/report_AAPL_20241118_123456.txt   (友好的文本格式)
```

### Python 腳本使用

```python
from main import OptionsAnalysisSystem
from output_layer.report_generator import ReportGenerator
from output_layer.web_telegram_formatter import WebFormatter, TelegramFormatter

# 1. 運行分析
system = OptionsAnalysisSystem(use_ibkr=False)
results = system.run_complete_analysis(ticker='AAPL')

# 2. 獲取結構化數據
generator = ReportGenerator()
structured_data = generator.get_structured_output(results['calculations'])

# 3. 根據需要選擇格式

# 3a. Web 格式
web_data = WebFormatter.format_for_html(structured_data)
print("Web 數據已準備好")

# 3b. Telegram 格式
telegram_messages = TelegramFormatter.format_for_telegram(structured_data, 'AAPL')
for msg in telegram_messages:
    print(msg)
    print("---")

# 3c. 直接使用結構化數據（API）
import json
print(json.dumps(structured_data, indent=2, ensure_ascii=False))
```

---

## 🔧 故障排除

### 問題 1: 某些模塊沒有輸出

**原因**: 模塊可能因為數據不足而跳過

**解決**: 檢查日誌文件，查看哪些模塊被跳過以及原因

```python
# 查看日誌
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 問題 2: Telegram 消息太長

**原因**: Telegram 有 4096 字符限制

**解決**: 消息已經自動分批，但可以進一步優化

```python
# 自定義消息分批
messages = TelegramFormatter.format_for_telegram(structured_data, 'AAPL')

# 合併短消息
combined_messages = []
current_msg = ""

for msg in messages:
    if len(current_msg) + len(msg) < 4000:
        current_msg += msg
    else:
        combined_messages.append(current_msg)
        current_msg = msg

if current_msg:
    combined_messages.append(current_msg)
```

### 問題 3: Web 格式不符合需求

**解決**: 創建自定義格式化器（見上面的示例）

---

## 📚 API 參考

### ReportGenerator

```python
class ReportGenerator:
    def generate(ticker, analysis_date, raw_data, calculation_results, data_fetcher=None) -> dict
    def get_structured_output(calculation_results: dict) -> dict
```

### WebFormatter

```python
class WebFormatter:
    @staticmethod
    def format_for_html(structured_data: dict) -> dict
```

### TelegramFormatter

```python
class TelegramFormatter:
    @staticmethod
    def format_for_telegram(structured_data: dict, ticker: str) -> List[str]
```

---

## 🎉 總結

輸出層現在完全支持：

✅ **所有 19 個模塊** - 無遺漏  
✅ **友好格式** - 易讀的表格和框架  
✅ **Web 集成** - HTML 友好的數據結構  
✅ **Telegram 集成** - Markdown 格式的消息  
✅ **結構化數據** - 易於處理的 JSON 格式  
✅ **可擴展** - 易於添加自定義格式化器

**準備好用於生產環境！** 🚀
