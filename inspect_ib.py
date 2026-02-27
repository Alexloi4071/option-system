"""
IBKR 數據調試腳本
用於檢查盤外時段 IBKR 返回的原始數據
"""
from ib_insync import IB, Option, Stock
import time
import math

def inspect_ticker_object(t, label=""):
    """詳細檢查 Ticker 對象的所有屬性"""
    print(f"\n{'='*60}")
    print(f"🔍 {label}")
    print(f"{'='*60}")
    
    # 基本報價
    print("\n📊 基本報價:")
    print(f"  bid      = {t.bid} (type: {type(t.bid).__name__})")
    print(f"  ask      = {t.ask} (type: {type(t.ask).__name__})")
    print(f"  last     = {t.last} (type: {type(t.last).__name__})")
    print(f"  close    = {t.close} (type: {type(t.close).__name__})")
    
    # 檢查是否是 NaN
    for name, val in [('bid', t.bid), ('ask', t.ask), ('last', t.last), ('close', t.close)]:
        if val is not None:
            try:
                is_nan = math.isnan(val)
                print(f"    {name} is NaN? {is_nan}")
            except TypeError:
                print(f"    {name} cannot check NaN (not a float)")
    
    # Volume 和 Open Interest
    print("\n📈 Volume / Open Interest:")
    print(f"  volume   = {t.volume} (type: {type(t.volume).__name__ if t.volume is not None else 'None'})")
    
    # 檢查各種 OI 屬性
    oi_attrs = ['openInterest', 'callOpenInterest', 'putOpenInterest']
    for attr in oi_attrs:
        val = getattr(t, attr, 'NOT_EXIST')
        if val != 'NOT_EXIST':
            print(f"  {attr} = {val} (type: {type(val).__name__ if val is not None else 'None'})")
        else:
            print(f"  {attr} = ❌ 屬性不存在")
    
    # Volume 是否是 NaN
    if t.volume is not None:
        try:
            is_nan = math.isnan(t.volume)
            print(f"  volume is NaN? {is_nan}")
        except TypeError:
            print(f"  volume cannot check NaN")
    
    # Greeks
    print("\n📐 Greeks (modelGreeks):")
    if t.modelGreeks:
        g = t.modelGreeks
        print(f"  delta      = {g.delta}")
        print(f"  gamma      = {g.gamma}")
        print(f"  theta      = {g.theta}")
        print(f"  vega       = {g.vega}")
        print(f"  impliedVol = {g.impliedVol}")
        print(f"  undPrice   = {g.undPrice}")
        print(f"  optPrice   = {g.optPrice}")
    else:
        print("  ❌ modelGreeks 為 None (數據未收到或盤外時段不可用)")
    
    # 列出所有可用屬性
    print("\n📋 所有 Ticker 屬性:")
    for attr in dir(t):
        if not attr.startswith('_'):
            try:
                val = getattr(t, attr)
                if not callable(val) and val is not None:
                    # 只顯示有值的屬性
                    val_str = str(val)[:50]
                    print(f"  {attr}: {val_str}")
            except:
                pass

def main():
    ib = IB()
    
    print("🔌 連接到 IBKR TWS...")
    try:
        ib.connect('127.0.0.1', 7497, clientId=99)  # 使用不同的 clientId 避免衝突
        print("✅ 連接成功!")
    except Exception as e:
        print(f"❌ 連接失敗: {e}")
        return
    
    # 設置 Market Data Type
    ib.reqMarketDataType(2)  # Frozen
    print(f"\n📡 Market Data Type 設置為: 2 (Frozen)")
    
    # 測試股票
    print("\n" + "="*60)
    print("測試 1: 股票數據 (FIVN)")
    print("="*60)
    
    stock = Stock('FIVN', 'SMART', 'USD')
    ib.qualifyContracts(stock)
    ib.reqMktData(stock, '', False, False)
    time.sleep(3)
    
    stock_ticker = ib.ticker(stock)
    inspect_ticker_object(stock_ticker, "FIVN 股票 Ticker")
    
    # 測試期權
    print("\n" + "="*60)
    print("測試 2: 期權數據 (FIVN 17.5 Call 2026-02-20)")
    print("="*60)
    
    option = Option('FIVN', '20260220', 17.5, 'C', 'SMART', 'USD')
    ib.qualifyContracts(option)
    
    # 使用完整的 Generic Tick Tags
    tick_tags = '100,101,104,105,106,165,225,232,233,236'
    print(f"📊 請求 Generic Tick Tags: {tick_tags}")
    
    ib.reqMktData(option, tick_tags, False, False)
    
    # 等待數據
    print("⏳ 等待數據 (10秒)...")
    for i in range(10):
        time.sleep(1)
        t = ib.ticker(option)
        has_greeks = t.modelGreeks is not None
        has_bid = t.bid is not None and not (isinstance(t.bid, float) and math.isnan(t.bid))
        print(f"  {i+1}秒: Greeks={has_greeks}, Bid={has_bid}")
        if has_greeks:
            print("  ✅ Greeks 已收到!")
            break
    
    option_ticker = ib.ticker(option)
    inspect_ticker_object(option_ticker, "FIVN 17.5 Call 期權 Ticker")
    
    # 清理
    ib.cancelMktData(stock)
    ib.cancelMktData(option)
    ib.disconnect()
    print("\n✅ 測試完成，已斷開連接")

if __name__ == "__main__":
    main()
