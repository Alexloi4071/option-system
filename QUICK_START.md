# 🚀 快速開始指南

## 最簡單的運行方式

### 方法 1: 使用測試腳本（推薦新手）

直接運行簡單測試，無需任何配置：

```bash
python test_simple.py
```

這個測試會：
- 使用模擬數據運行完整分析
- 展示所有 19 個模塊的計算結果
- 不需要 API Keys
- 運行時間約 20-30 秒

---

### 方法 2: 分析真實股票（需要 API Keys）

#### 步驟 1: 配置 API Keys

編輯 `.env` 文件，至少配置這兩個（免費）：

```env
# 必需的 API Keys（免費）
FRED_API_KEY=your_fred_api_key_here
FINNHUB_API_KEY=your_finnhub_api_key_here

# API 速率控制（避免限流）
REQUEST_DELAY=2.0
MAX_RETRIES=3
```

**如何獲取 API Keys**:

1. **FRED API** (免費)
   - 訪問: https://fred.stlouisfed.org/
   - 註冊賬號
   - 申請 API Key（即時獲得）

2. **Finnhub API** (免費版 60次/分鐘)
   - 訪問: https://finnhub.io/
   - 註冊賬號
   - 獲取 API Key（即時獲得）

#### 步驟 2: 運行分析

創建一個簡單的 Python 腳本 `my_analysis.py`：

```python
from main import OptionsAnalysisSystem

# 初始化系統（不使用 IBKR）
system = OptionsAnalysisSystem(use_ibkr=False)

# 分析 Apple 股票的期權
# 參數說明：
# - ticker: 股票代碼（如 AAPL, TSLA, MSFT）
# - expiration: 期權到期日（格式 YYYY-MM-DD，可選）
results = system.run_complete_analysis(
    ticker='AAPL',
    expiration=None  # None 表示自動選擇最近的到期日
)

# 查看結果
print("\n" + "="*60)
print("分析完成！")
print("="*60)

# 查看 Black-Scholes 定價結果
if 'module15_black_scholes' in results:
    bs = results['module15_black_scholes']
    print(f"\n📊 Black-Scholes 定價:")
    print(f"  Call 期權價格: ${bs['call']['option_price']:.2f}")
    print(f"  Put 期權價格: ${bs['put']['option_price']:.2f}")

# 查看 Greeks
if 'module16_greeks' in results:
    greeks = results['module16_greeks']
    print(f"\n📈 Greeks 風險指標:")
    print(f"  Call Delta: {greeks['call']['delta']:.4f}")
    print(f"  Call Gamma: {greeks['call']['gamma']:.6f}")
    print(f"  Call Theta: {greeks['call']['theta']:.4f}")

# 查看隱含波動率
if 'module17_implied_volatility' in results:
    iv = results['module17_implied_volatility']
    print(f"\n🔍 隱含波動率:")
    print(f"  Call IV: {iv['call']['implied_volatility']:.2%}")
    print(f"  收斂次數: {iv['call']['iterations']}")

print("\n✅ 分析完成！")
```

然後運行：

```bash
python my_analysis.py
```

---

## 📝 輸入參數說明

### 必需參數

| 參數 | 說明 | 示例 |
|------|------|------|
| `ticker` | 股票代碼 | `'AAPL'`, `'TSLA'`, `'MSFT'` |

### 可選參數

| 參數 | 說明 | 默認值 | 示例 |
|------|------|--------|------|
| `expiration` | 期權到期日 | `None`（自動選擇） | `'2024-12-20'` |
| `use_ibkr` | 是否使用 IBKR | `False` | `True` / `False` |

---

## 🎯 常用股票代碼

### 美股熱門股票

```python
# 科技股
'AAPL'   # Apple
'MSFT'   # Microsoft
'GOOGL'  # Google
'AMZN'   # Amazon
'TSLA'   # Tesla
'NVDA'   # NVIDIA
'META'   # Meta (Facebook)

# 金融股
'JPM'    # JP Morgan
'BAC'    # Bank of America
'GS'     # Goldman Sachs

# 其他
'SPY'    # S&P 500 ETF
'QQQ'    # NASDAQ ETF
```

---

## 📊 輸出結果說明

系統會計算並返回 19 個模塊的結果：

### 基礎分析 (Module 1-7)
- **Module 1**: 支撐/阻力位
- **Module 2**: 股票遠期理論價
- **Module 3**: 套利價差分析
- **Module 4**: PE 估值
- **Module 5**: 利率與 PE 關係
- **Module 6**: 對沖數量
- **Module 7**: Long Call 策略

### 進階策略 (Module 8-14)
- **Module 8**: Long Put 策略
- **Module 9**: Short Call 策略
- **Module 10**: Short Put 策略
- **Module 11**: 合成股票
- **Module 12**: 年息收益
- **Module 13**: 持倉分析
- **Module 14**: 監察崗位

### 自主計算 (Module 15-19) ⭐
- **Module 15**: Black-Scholes 期權定價
- **Module 16**: Greeks 風險指標
- **Module 17**: 隱含波動率
- **Module 18**: 歷史波動率分析
- **Module 19**: Put-Call Parity 驗證

---

## 🔧 常見問題

### Q1: 沒有 API Keys 可以運行嗎？

**可以！** 使用 `test_simple.py` 或 `test_complete_analysis.py`，這些測試使用模擬數據。

```bash
python test_simple.py
```

### Q2: API 請求太快被限流怎麼辦？

在 `.env` 文件中增加延遲：

```env
REQUEST_DELAY=3.0  # 增加到 3 秒
# 或更保守的 5 秒
REQUEST_DELAY=5.0
```

### Q3: 如何查看詳細的計算過程？

設置日誌級別為 DEBUG：

```env
LOG_LEVEL=DEBUG
```

### Q4: 如何選擇特定的到期日？

```python
# 查看所有可用的到期日
from data_layer.data_fetcher import DataFetcher

fetcher = DataFetcher(use_ibkr=False)
expirations = fetcher.get_option_expirations('AAPL')
print("可用的到期日:", expirations)

# 選擇特定日期
results = system.run_complete_analysis(
    ticker='AAPL',
    expiration='2024-12-20'  # 使用特定日期
)
```

### Q5: 如何保存結果？

```python
import json

# 運行分析
results = system.run_complete_analysis(ticker='AAPL')

# 保存為 JSON
with open('analysis_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("結果已保存到 analysis_results.json")
```

---

## 🎓 進階使用

### 使用單個模塊

```python
from calculation_layer.module15_black_scholes import BlackScholesCalculator

# 只使用 Black-Scholes 定價
bs_calc = BlackScholesCalculator()
result = bs_calc.calculate_option_price(
    stock_price=150.0,
    strike_price=155.0,
    risk_free_rate=0.05,
    time_to_expiration=0.25,  # 3個月
    volatility=0.20,
    option_type='call'
)

print(f"Call 期權價格: ${result.option_price:.2f}")
```

### 批量分析多個股票

```python
tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA']

for ticker in tickers:
    print(f"\n分析 {ticker}...")
    try:
        results = system.run_complete_analysis(ticker=ticker)
        print(f"✅ {ticker} 分析完成")
    except Exception as e:
        print(f"❌ {ticker} 分析失敗: {e}")
```

---

## 📚 更多資源

- **完整文檔**: 查看 [README.md](README.md)
- **新模塊指南**: 查看 [docs/new_modules_guide.md](docs/new_modules_guide.md)
- **變更日誌**: 查看 [CHANGELOG.md](CHANGELOG.md)
- **合規性報告**: 查看 [docs/compliance_report.md](docs/compliance_report.md)

---

## 💡 最簡單的開始方式

**只需 3 步**:

1. 運行測試看看效果：
   ```bash
   python test_simple.py
   ```

2. 如果滿意，配置 API Keys（2 個免費的）

3. 分析你感興趣的股票：
   ```python
   from main import OptionsAnalysisSystem
   system = OptionsAnalysisSystem(use_ibkr=False)
   results = system.run_complete_analysis(ticker='AAPL')
   ```

就這麼簡單！🎉

---

**需要幫助？** 查看 [README.md](README.md) 或提交 Issue。
